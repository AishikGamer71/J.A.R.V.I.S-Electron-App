import asyncio
import logging
import subprocess
import sys
import time
from typing import Callable

logger = logging.getLogger("jarvis.supervisor")


class ProcessSupervisor:
    def __init__(
        self,
        command: list[str],
        name: str = "child_service",
        max_restarts: int = 10,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0,
        cwd: str | None = None,
        env: dict[str, str] | None = None
    ):
        self.command = command
        self.name = name
        self.max_restarts = max_restarts
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.cwd = cwd
        self.env = env
        self.process: subprocess.Popen | None = None
        self.restart_count = 0
        self.is_running = False
        self._stop_requested = False

    def start(self) -> None:
        self._stop_requested = False
        self.is_running = True
        self.restart_count = 0
        self._spawn()

    def _spawn(self) -> None:
        logger.info(f"[{self.name}] Spawning process: {' '.join(self.command)}")
        try:
            self.process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        except Exception as e:
            logger.error(f"[{self.name}] Failed to spawn process: {e}")

    def monitor_loop(self) -> None:
        backoff = self.initial_backoff
        while not self._stop_requested and self.restart_count < self.max_restarts:
            if not self.process:
                self._spawn()

            ret = self.process.poll() if self.process else -1
            if ret is not None:
                # Process terminated
                if self._stop_requested:
                    break
                self.restart_count += 1
                logger.warning(
                    f"[{self.name}] Process exited with code {ret}. "
                    f"Restarting ({self.restart_count}/{self.max_restarts}) in {backoff:.1f}s..."
                )
                time.sleep(backoff)
                backoff = min(backoff * 2.0, self.max_backoff)
                self._spawn()
            else:
                time.sleep(1.0)

    def stop(self) -> None:
        self._stop_requested = True
        self.is_running = False
        if self.process:
            logger.info(f"[{self.name}] Terminating process PID {self.process.pid}...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                logger.warning(f"[{self.name}] Force killing process PID {self.process.pid}...")
                self.process.kill()
            self.process = None
