import logging
import os
import shutil
import asyncio
import json
import time

import docker
from docker.errors import APIError, BuildError, ImageNotFound, NotFound

from src.app.core.config import get_settings
from src.app.services.tools.playwright_remote import write_conftest

logger = logging.getLogger(__name__)


class TestExecutorService:
	# Network inside the Docker daemon configured by DOCKER_HOST (DinD)
	EXEC_NETWORK_NAME = "testops-exec-net"

	# Playwright Browser Server (remote browser) runs as a shared container inside the same DinD daemon
	PLAYWRIGHT_SERVER_IMAGE = "mcr.microsoft.com/playwright:v1.49.1-jammy"
	PLAYWRIGHT_SERVER_NAME = "testops-playwright-server"
	PLAYWRIGHT_SERVER_PORT = 4444
	PLAYWRIGHT_SERVER_CMD = "npx playwright run-server --host 0.0.0.0 --port 4444"

	def __init__(self) -> None:
		self.settings = get_settings()
		self.settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
		self.settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)

		try:
			# Explicitly check DOCKER_HOST env var, important for DinD
			if not os.environ.get('DOCKER_HOST'):
				# Fallback for local dev
				if os.path.exists('/var/run/docker.sock'):
					os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
			
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
					# Don't remove shared infra containers (e.g., Playwright Browser Server)
					labels = container.labels or {}
					if labels.get("role") == "playwright-server":
						continue
					container.remove(force=True)
					count += 1
				except NotFound:
					pass
			if count > 0:
				logger.info(f"🧹 Cleanup: Removed {count} stale test containers.")
		except Exception as e:
			logger.warning(f"Cleanup warning: {e}")

	def _ensure_runner_image(self) -> bool:
		image_tag = "testops-runner:latest"
		try:
			self.docker_client.images.get(image_tag)
			return True
		except ImageNotFound:
			logger.info(f"⚙️ Runner image '{image_tag}' not found. Building...")
			try:
				self.docker_client.images.build(
					path=str(self.settings.BASE_DIR),
					dockerfile="Dockerfile.runner",
					tag=image_tag,
					rm=True
				)
				logger.info("✅ Runner image built successfully.")
				return True
			except (BuildError, APIError) as e:
				logger.error(f"❌ Failed to build runner image: {e}")
				return False

	def _is_playwright_remote_enabled(self) -> bool:
		# Prefer Settings, but allow env override.
		val = getattr(self.settings, "PLAYWRIGHT_REMOTE_ENABLED", None)
		if val is None:
			val = os.getenv("PLAYWRIGHT_REMOTE_ENABLED", "0")
		return str(val).strip().lower() in ("1", "true", "yes", "on")

	def _ensure_exec_network(self) -> None:
		"""Ensure a shared docker network exists inside the active Docker daemon (DinD)."""
		if not self.docker_client:
			return
		try:
			self.docker_client.networks.get(self.EXEC_NETWORK_NAME)
		except NotFound:
			self.docker_client.networks.create(self.EXEC_NETWORK_NAME, driver="bridge")
			logger.info(f"🌐 Created DinD network: {self.EXEC_NETWORK_NAME}")
		except Exception as e:
			logger.warning(f"Network ensure warning: {e}")

	def _wait_playwright_server_ready(self, container, timeout_s: int = 25) -> bool:
		"""Wait until Playwright Browser Server port is reachable inside the container."""
		deadline = time.time() + timeout_s
		while time.time() < deadline:
			try:
				container.reload()
				if container.status != "running":
					time.sleep(0.5)
					continue

				exit_code, _ = container.exec_run(
					[
						"bash",
						"-lc",
						(
							f"node -e \"require('net').connect({self.PLAYWRIGHT_SERVER_PORT},'127.0.0.1')"
							".on('connect',()=>process.exit(0)).on('error',()=>process.exit(1))\""
						),
					]
				)
				if exit_code == 0:
					return True
			except Exception:
				pass
			time.sleep(0.5)
		return False

	def _ensure_playwright_server(self) -> str | None:
		"""Start (or reuse) Playwright Browser Server container inside DinD and return its WS endpoint."""
		if not self.docker_client or not self._is_playwright_remote_enabled():
			return None

		self._ensure_exec_network()

		try:
			server = self.docker_client.containers.get(self.PLAYWRIGHT_SERVER_NAME)
			if server.status != "running":
				server.start()
		except NotFound:
			logger.info("🧭 Starting Playwright Browser Server (DinD)...")
			server = self.docker_client.containers.run(
				image=self.PLAYWRIGHT_SERVER_IMAGE,
				name=self.PLAYWRIGHT_SERVER_NAME,
				command=["bash", "-lc", self.PLAYWRIGHT_SERVER_CMD],
				detach=True,
				network=self.EXEC_NETWORK_NAME,
				labels={"created_by": "testops-forge", "role": "playwright-server"},
				restart_policy={"Name": "unless-stopped"},
			)
		except Exception as e:
			logger.warning(f"⚠️ Failed to start/reuse Playwright Browser Server: {e}")
			return None

		if not self._wait_playwright_server_ready(server):
			logger.warning("⚠️ Playwright Browser Server did not become ready in time.")
			return None

		return f"ws://{self.PLAYWRIGHT_SERVER_NAME}:{self.PLAYWRIGHT_SERVER_PORT}/"

	async def execute_test(self, run_id: int, code: str, redis_client=None) -> tuple[bool, str, str | None]:
		logger.info(f"▶️ Executing Run ID: {run_id}...")
		if not self.docker_client:
			return False, "Docker is not running.", None
		
		# Synchronous docker operations must be run in executor to avoid blocking the Event Loop
		loop = asyncio.get_running_loop()
		
		return await loop.run_in_executor(None, self._execute_test_sync, run_id, code, redis_client)

	def _execute_test_sync(self, run_id: int, code: str, redis_client=None) -> tuple[bool, str, str | None]:
		"""Synchronous implementation of test execution"""
		# Helper to publish logs safely from sync code
		def publish_log(message: str):
			if redis_client:
				try:
					# Since we are in a thread, we need to run async publish in a new loop or use sync redis
					# Ideally, we should pass a sync redis client or just handle it differently.
					# For simplicity with redis.asyncio, we can use run_coroutine_threadsafe if we had the loop, 
					# but here we just skip or simplistic print. 
					# BETTER APPROACH: We assume redis_client is passed as an async object, 
					# but we are in a sync function. 
					pass 
				except Exception:
					pass
			logger.info(message)

		self.cleanup_all()

		if not self._ensure_runner_image():
			return False, "Failed to prepare Test Runner environment.", None

		# Runner + remote browser server must be on the same DinD network
		self._ensure_exec_network()

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
			with open(test_file, "w", encoding="utf-8") as f:
				f.write(code)

			# Ensure conftest.py exists to support remote browser (and keep local fallback)
			write_conftest(run_dir_abs)

			with open(run_dir_abs / "pytest.ini", "w", encoding="utf-8") as f:
				f.write("""
[pytest]
addopts = --clean-alluredir --alluredir=/app/allure-results --screenshot on --video retain-on-failure --tracing on
python_files = test_*.py
filterwarnings =
    ignore::DeprecationWarning
                """)
		except Exception as e:
			logger.error(f"❌ IO Error preparing run files: {e}")
			return False, f"IO Error: {e}", None

		cmd = f"/bin/sh -c 'pytest test_{run_id}.py -v && allure generate /app/allure-results -o /app/report --clean'"

		logs = ""
		success = False
		container = None
		ws_endpoint = self._ensure_playwright_server()

		try:
			logger.info(f"🐳 Starting container for run {run_id}...")

			runner_env = {
				"HEADLESS": "true",
				"PLAYWRIGHT_HEADLESS": "1",
			}
			if ws_endpoint:
				runner_env["PLAYWRIGHT_WS_ENDPOINT"] = ws_endpoint
				runner_env["PLAYWRIGHT_BROWSER"] = getattr(self.settings, "PLAYWRIGHT_BROWSER", "chromium")

			container = self.docker_client.containers.run(
				image="testops-runner:latest",
				command=cmd,
				volumes={str(run_dir_abs): {'bind': '/app', 'mode': 'rw'}},
				working_dir="/app",
				environment=runner_env,
				shm_size="2g",
				detach=True,
				labels={"created_by": "testops-forge", "role": "runner"},
				log_config={'type': 'json-file'},
				network=self.EXEC_NETWORK_NAME,
				# Resource limits for safety
				mem_limit="1g",
				cpu_quota=100000,
			)

			# Stream logs from container
			for line in container.logs(stream=True, follow=True):
				decoded_line = line.decode("utf-8", errors="replace").strip()
				if decoded_line:
					logs += decoded_line + "\n"
					# NOTE: Since we cannot easily await here in sync function, 
					# we rely on the task wrapper to publish logs if possible, 
					# OR we just accumulate logs. 
					# Ideally, we should use a shared queue or run this loop in async.
					# For now, we will return the full logs at the end.
					logger.info(f"[Run {run_id}] {decoded_line}")

			result = container.wait()
			exit_code = result.get('StatusCode', 1)
			success = (exit_code == 0)

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
				shutil.copytree(run_dir_abs / "report", final_report_dir, dirs_exist_ok=True)
				report_url = f"/static/reports/{run_id}/index.html"
				logger.info(f"📊 Report generated at {report_url}")
			except Exception as e:
				logger.warning(f"Failed to publish report: {e}")
		else:
			logger.warning("⚠️ Allure report missing (tests might have crashed early).")

		return success, logs, report_url
