"""
backend/core/cron_scheduler.py
==============================
CronScheduler: Periodic background task scheduler and autonomous ticker for J.A.R.V.I.S.
Maintains 60s cadence, cross-process Windows msvcrt file locking (.tick.lock),
and pushes notifications and alerts to ~/.jarvis/inbox.json.
"""

import json
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("jarvis.cron_scheduler")

# Optional Windows msvcrt for cross-process file locking
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


class WindowsTickLock:
    """Acquires a non-blocking cross-process lock on Windows."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._fd: Optional[int] = None

    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(str(self.lock_path), os.O_RDWR | os.O_CREAT)
            if HAS_MSVCRT:
                msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
            return self
        except (OSError, IOError):
            if self._fd is not None:
                try:
                    os.close(self._fd)
                except Exception:
                    pass
                self._fd = None
            return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd is not None:
            try:
                if HAS_MSVCRT:
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None


@dataclass
class ScheduledTask:
    name: str
    interval_seconds: int
    handler: Callable[[], Any]
    last_run: float = 0.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class CronScheduler:
    """Manages scheduled background jobs with 60-second default cadence."""

    def __init__(
        self,
        tick_interval: int = 60,
        cron_dir: Optional[Path] = None,
        inbox_path: Optional[Path] = None,
    ):
        self.tick_interval: int = tick_interval
        self.cron_dir = cron_dir or (Path.home() / ".jarvis" / "cron")
        self.inbox_path = inbox_path or (Path.home() / ".jarvis" / "inbox.json")
        self.lock_path = self.cron_dir / ".tick.lock"

        self.cron_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_path.parent.mkdir(parents=True, exist_ok=True)

        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_task(
        self,
        name: str,
        interval_seconds: int,
        handler: Callable[[], Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registers a recurring task."""
        self.tasks[name] = ScheduledTask(
            name=name,
            interval_seconds=interval_seconds,
            handler=handler,
            last_run=0.0,
            enabled=True,
            metadata=metadata or {},
        )

    def remove_task(self, name: str) -> bool:
        """Removes a registered task by name."""
        if name in self.tasks:
            del self.tasks[name]
            return True
        return False

    def tick(self, force: bool = False) -> List[str]:
        """
        Executes a scheduler tick. Runs due tasks under cross-process lock.
        Returns list of executed task names.
        """
        executed: List[str] = []
        now = time.time()

        with WindowsTickLock(self.lock_path) as lock:
            if lock is None and not force:
                logger.debug("Another process holds the tick lock. Skipping tick.")
                return []

            for name, task in list(self.tasks.items()):
                if not task.enabled:
                    continue

                is_due = (now - task.last_run) >= task.interval_seconds
                if force or is_due:
                    try:
                        res = task.handler()
                        task.last_run = now
                        executed.append(name)
                        if res:
                            self._push_to_inbox(name, res)
                    except Exception as e:
                        logger.error("Error executing task '%s': %s", name, e)

        return executed

    def _push_to_inbox(self, source: str, content: Any) -> None:
        """Appends a task completion notification to ~/.jarvis/inbox.json."""
        try:
            items: List[Dict[str, Any]] = []
            if self.inbox_path.exists():
                try:
                    with open(self.inbox_path, "r", encoding="utf-8") as f:
                        items = json.load(f)
                    if not isinstance(items, list):
                        items = []
                except Exception:
                    items = []

            item = {
                "id": f"inbox-{time.time():.3f}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "content": content,
                "read": False,
            }
            items.append(item)
            if len(items) > 100:
                items = items[-100:]

            with open(self.inbox_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2)
        except Exception as e:
            logger.debug("Failed to push to inbox: %s", e)

    def get_inbox_items(self) -> List[Dict[str, Any]]:
        """Returns current inbox notifications."""
        if not self.inbox_path.exists():
            return []
        try:
            with open(self.inbox_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def start(self) -> None:
        """Starts the scheduler in a background daemon thread."""
        if self._running:
            return
        self._running = True

        def _loop():
            while self._running:
                try:
                    self.tick(force=False)
                except Exception as e:
                    logger.error("Exception in CronScheduler loop: %s", e)
                time.sleep(self.tick_interval)

        self._thread = threading.Thread(target=_loop, daemon=True, name="jarvis-cron-scheduler")
        self._thread.start()

    def stop(self) -> None:
        """Stops the scheduler thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
