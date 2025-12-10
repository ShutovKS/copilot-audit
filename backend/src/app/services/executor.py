import shutil
import logging
import docker 
from docker.errors import ImageNotFound, BuildError, APIError, NotFound
from pathlib import Path
from typing import Tuple, Optional
from src.app.core.config import get_settings

logger = logging.getLogger(__name__)

class TestExecutorService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            self.docker_client = docker.from_env()
            logger.info("🐳 Docker client connected.")
        except Exception as e:
            logger.error(f"❌ CRITICAL: Docker Daemon unavailable. Error: {e}")
            self.docker_client = None

    def cleanup_all(self):
        if not self.docker_client: return

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

    async def execute_test(self, run_id: int, code: str) -> Tuple[bool, str, Optional[str]]:
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
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(code)
            
            with open(run_dir_abs / "pytest.ini", "w", encoding="utf-8") as f:
                f.write(f"""
[pytest]
addopts = --clean-alluredir --alluredir=/app/allure-results
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

        try:
            logger.info(f"🐳 Starting container for run {run_id}...")
            
            container = self.docker_client.containers.run(
                image="testops-runner:latest",
                command=cmd,
                volumes={str(run_dir_abs): {'bind': '/app', 'mode': 'rw'}},
                working_dir="/app",
                environment={"HEADLESS": "true"},
                shm_size="2g",
                detach=True,
                labels={"created_by": "testops-forge"}
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
                shutil.copytree(run_dir_abs / "report", final_report_dir)
                report_url = f"/static/reports/{run_id}/index.html"
                logger.info(f"📊 Report generated at {report_url}")
            except Exception as e:
                logger.warning(f"Failed to publish report: {e}")
        else:
            logger.warning("⚠️ Allure report missing (tests might have crashed early).")

        return success, logs, report_url
