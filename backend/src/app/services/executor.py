import logging
import os
import platform
import shutil
from pathlib import Path

import docker
from docker.errors import APIError, BuildError, ImageNotFound, NotFound
from docker.types import LogConfig

from src.app.core.config import get_settings

logger = logging.getLogger(__name__)


class TestExecutorService:
	def __init__(self) -> None:
		self.settings = get_settings()
		self.settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
		self.settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)

		try:
			# Set default DOCKER_HOST based on platform if not set
			if not os.environ.get('DOCKER_HOST'):
				system = platform.system()
				if system == 'Darwin':  # macOS
					possible_sockets = [
						os.path.expanduser("~/.docker/run/docker.sock"),
						"/var/run/docker.sock"
					]
					docker_host = None
					for sock in possible_sockets:
						if os.path.exists(sock):
							docker_host = f'unix://{sock}'
							break
					if not docker_host:
						logger.warning("⚠️ No Docker socket found on macOS. Please ensure Docker Desktop is running.")
				elif system == 'Linux':
					docker_host = 'unix:///var/run/docker.sock'
				elif system == 'Windows':
					docker_host = 'npipe:////./pipe/docker_engine'
				else:
					docker_host = None
				if docker_host:
					os.environ['DOCKER_HOST'] = docker_host
					logger.info(f"🐳 Setting DOCKER_HOST to {docker_host}")
			self.docker_client = docker.from_env()
			logger.info("🐳 Docker client connected.")
		except Exception as e:
			logger.error(f"❌ CRITICAL: Docker Daemon unavailable. Error: {e}")
			self.docker_client = None

	def cleanup_all(self):
		if not self.docker_client:
			return

		try:
			containers = self.docker_client.containers.list(
				all=True,
				filters={"label": "created_by=testops-forge"}
			)
			count = 0
			for container in containers:
				try:
					container.remove(force=True)
					count += 1
				except NotFound:
					pass
			if count > 0:
				logger.info(f"🧹 Cleanup: Removed {count} stale test containers.")
		except Exception as e:
			logger.warning(f"Cleanup warning: {e}")

	def _ensure_runner_image(self) -> bool:
		if not self.docker_client:
			return False
		image_tag = "testops-runner:latest"
		try:
			self.docker_client.images.get(image_tag)
			return True
		except ImageNotFound:
			logger.info(f"⚙️ Runner image '{image_tag}' not found. Building...")
			try:
				build_path = Path("/app")  # In container, backend is mounted at /app
				logger.info(f"Building runner image from path: {build_path}")
				self.docker_client.images.build(
					path=str(build_path),
					dockerfile="Dockerfile.runner",
					tag=image_tag,
					rm=True
				)
				logger.info("✅ Runner image built successfully.")
				return True
			except (BuildError, APIError) as e:
				logger.error(f"❌ Failed to build runner image: {e}")
				return False

	async def execute_test(self, run_id: int, code: str) -> tuple[bool, str, str | None]:
		logger.info(f"▶️ Executing Run ID: {run_id}...")
		if not self.docker_client:
			return False, "Docker is not running.", None
		self.cleanup_all()

		if not self._ensure_runner_image():
			return False, "Failed to prepare Test Runner environment.", None

		run_dir_abs = (self.settings.TEMP_DIR / str(run_id)).resolve()

		if run_dir_abs.exists():
			shutil.rmtree(run_dir_abs, ignore_errors=True)
		run_dir_abs.mkdir(parents=True, exist_ok=True)

		allure_results = run_dir_abs / "allure-results"
		allure_results.mkdir(exist_ok=True)
		allure_report = run_dir_abs / "report"
		allure_report.mkdir(exist_ok=True)

		try:
			test_file = run_dir_abs / f"test_{run_id}.py"
			logger.info(f"📝 Writing test file to: {test_file}")
			with open(test_file, "w", encoding="utf-8") as f:
				f.write(code)
			logger.info(f"✅ Test file written. Size: {test_file.stat().st_size} bytes")

			pytest_ini = run_dir_abs / "pytest.ini"
			logger.info(f"📝 Writing pytest.ini to: {pytest_ini}")
			with open(pytest_ini, "w", encoding="utf-8") as f:
				f.write("""
[pytest]
addopts = --clean-alluredir --alluredir=allure-results --screenshot on --video retain-on-failure --tracing on
python_files = test_*.py
filterwarnings =
    ignore::DeprecationWarning
                """)
			logger.info(f"✅ pytest.ini written. Size: {pytest_ini.stat().st_size} bytes")
		except Exception as e:
			logger.error(f"❌ IO Error preparing run files: {e}")
			return False, f"IO Error: {e}", None

		cmd = f"/bin/sh -c 'cd /host_temp/{run_id} && pytest test_{run_id}.py -v && allure generate allure-results -o report --clean'"

		logs = ""
		success = False
		container = None

		try:
			logger.info(f"🐳 Starting container for run {run_id}...")

			# For DinD: mount the shared volume at the run-specific subpath
			volume_name = "copilot-audit_testops_temp"
			container_path = f"{run_id}"
			
			container = self.docker_client.containers.run(
				image="testops-runner:latest",
				command=cmd,
				volumes={
					f"{volume_name}": {'bind': f'/host_temp', 'mode': 'rw'}
				},
				working_dir=f"/host_temp/{container_path}",
				environment={"HEADLESS": "true"},
				shm_size="2g",
				detach=True,
				labels={"created_by": "testops-forge"},
				log_config=LogConfig(type='json-file')
			)

			result = container.wait()
			exit_code = result.get('StatusCode', 1)

			logs = container.logs().decode("utf-8", errors="replace")
			success = (exit_code == 0)

			logger.info(f"🏁 Run {run_id} finished. Exit Code: {exit_code}. Logs length: {len(logs)} chars.")

		except Exception as e:
			logger.error(f"❌ Docker Execution Error: {e}")
			return False, f"Docker Error: {e}", None
		finally:
			if container:
				try:
					container.remove(force=True)
				except Exception:
					pass

		final_report_dir = self.settings.REPORTS_DIR / str(run_id)
		if final_report_dir.exists():
			shutil.rmtree(final_report_dir, ignore_errors=True)

		report_url = None
		if (run_dir_abs / "report").exists() and any((run_dir_abs / "report").iterdir()):
			try:
				final_report_dir.mkdir(parents=True, exist_ok=True)
				shutil.copytree(run_dir_abs / "report", final_report_dir, dirs_exist_ok=True)
				report_url = f"/static/reports/{run_id}/index.html"
				logger.info(f"📊 Report generated at {report_url}")
			except Exception as e:
				logger.warning(f"Failed to publish report: {e}")
		else:
			logger.warning("⚠️ Allure report missing (tests might have crashed early).")

		return success, logs, report_url
