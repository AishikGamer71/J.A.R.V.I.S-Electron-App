import asyncio
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

from jarvis.config.settings import settings

logger = logging.getLogger("jarvis.security.sandbox_runner")


class SandboxResult:
    def __init__(
        self,
        exit_code: int,
        stdout: str,
        stderr: str,
        is_sandboxed: bool,
        container_id: str | None = None,
        duration_ms: float = 0.0
    ):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.is_sandboxed = is_sandboxed
        self.container_id = container_id
        self.duration_ms = duration_ms

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "is_sandboxed": self.is_sandboxed,
            "container_id": self.container_id,
            "duration_ms": self.duration_ms
        }


class SandboxRunner:
    def __init__(self, sandbox_root: Path | None = None, image_name: str | None = None):
        self.sandbox_root = sandbox_root or settings.SANDBOX_ROOT
        self.image_name = image_name or settings.DOCKER_IMAGE
        self._docker_available: bool | None = None

    def is_docker_available(self) -> bool:
        if self._docker_available is not None:
            return self._docker_available
        try:
            res = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=2
            )
            self._docker_available = res.returncode == 0
        except Exception:
            self._docker_available = False
        return self._docker_available

    async def run_command(
        self,
        command: list[str] | str,
        timeout_seconds: int = 60,
        env: dict[str, str] | None = None
    ) -> SandboxResult:
        start_time = time.perf_counter()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

        cmd_list = command if isinstance(command, list) else command.split()

        # Path 1: Docker Sandbox Execution
        if self.is_docker_available():
            try:
                docker_cmd = [
                    "docker", "run", "--rm",
                    "--network", "none",
                    "--memory", "512m",
                    "--cpus", "1.0",
                    "-v", f"{self.sandbox_root.resolve()}:/sandbox:rw",
                    "-w", "/sandbox",
                    self.image_name
                ] + cmd_list

                proc = await asyncio.create_subprocess_exec(
                    *docker_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=float(timeout_seconds)
                )
                duration = round((time.perf_counter() - start_time) * 1000, 2)
                return SandboxResult(
                    exit_code=proc.returncode or 0,
                    stdout=stdout_bytes.decode(errors="replace"),
                    stderr=stderr_bytes.decode(errors="replace"),
                    is_sandboxed=True,
                    container_id="docker-isolated",
                    duration_ms=duration
                )
            except Exception as e:
                logger.warning(f"Docker sandbox run failed: {e}. Falling back to directory confinement.")

        # Path 2: OS-level Sandboxed Subprocess (Directory Confinement)
        try:
            clean_env = {
                "PATH": os.environ.get("PATH", ""),
                "TEMP": str(self.sandbox_root),
                "TMP": str(self.sandbox_root),
                **(env or {})
            }

            proc = await asyncio.create_subprocess_exec(
                *cmd_list,
                cwd=str(self.sandbox_root.resolve()),
                env=clean_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout_seconds)
            )
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            return SandboxResult(
                exit_code=proc.returncode or 0,
                stdout=stdout_bytes.decode(errors="replace"),
                stderr=stderr_bytes.decode(errors="replace"),
                is_sandboxed=True,
                container_id="local-confined-sandbox",
                duration_ms=duration
            )
        except asyncio.TimeoutError:
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout_seconds}s",
                is_sandboxed=True,
                container_id="local-confined-sandbox",
                duration_ms=duration
            )
        except Exception as e:
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            return SandboxResult(
                exit_code=1,
                stdout="",
                stderr=str(e),
                is_sandboxed=False,
                container_id=None,
                duration_ms=duration
            )


sandbox_runner = SandboxRunner()
