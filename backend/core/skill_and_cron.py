"""
backend/core/skill_and_cron.py
Hermes-Assimilated SKILL.md Procedural Loader & Background Cron Scheduler.
Loads custom skills and executes recurring desktop tasks.
"""

import os
import json
import time
import asyncio
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from backend.config import settings

logger = logging.getLogger("jarvis.skills_cron")

class SkillLoader:
    """Parses and manages SKILL.md files defining procedural capabilities."""

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or settings.SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_skills: Dict[str, Dict[str, Any]] = {}
        self.reload_skills()

    def reload_skills(self) -> None:
        self.loaded_skills.clear()
        for root, _, files in os.walk(self.skills_dir):
            for file in files:
                if file.lower().endswith("skill.md") or file.lower() == "skill.md":
                    full_path = Path(root) / file
                    skill = self._parse_skill_file(full_path)
                    if skill:
                        self.loaded_skills[skill["name"]] = skill

        # Add a default desktop skill if empty
        if not self.loaded_skills:
            self._create_default_skills()

    def _create_default_skills(self) -> None:
        default_file = self.skills_dir / "desktop_assistant.md"
        content = """---
name: desktop_assistant
description: Autonomous desktop workflow skill for controlling applications, files, and terminal.
trigger: desktop automation, run commands, open apps
---
# Desktop Assistant Skill
When asked to automate actions:
1. Verify system safety.
2. Use control_desktop or run_safe_terminal.
3. Confirm completion.
"""
        default_file.write_text(content, encoding="utf-8")
        parsed = self._parse_skill_file(default_file)
        if parsed:
            self.loaded_skills[parsed["name"]] = parsed

    def _parse_skill_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            text = file_path.read_text(encoding="utf-8")
            # Parse YAML frontmatter between ---
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
            if match:
                fm_raw, body = match.group(1), match.group(2)
                fm = {}
                for line in fm_raw.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm[k.strip().lower()] = v.strip()
                name = fm.get("name", file_path.stem)
                desc = fm.get("description", "Custom desktop skill")
                return {
                    "name": name,
                    "description": desc,
                    "body": body.strip(),
                    "path": str(file_path)
                }
            return {
                "name": file_path.stem,
                "description": "Procedural skill",
                "body": text.strip(),
                "path": str(file_path)
            }
        except Exception as e:
            logger.error(f"[SkillLoader] Failed to parse {file_path}: {e}")
            return None

    def get_prompt_context(self) -> str:
        """Formats loaded skills for LLM system context."""
        if not self.loaded_skills:
            return ""
        ctx = "Available Skills:\n"
        for name, sk in self.loaded_skills.items():
            ctx += f"- {name}: {sk['description']}\n"
        return ctx


class CronScheduler:
    """Hermes-Assimilated Background Cron Scheduler managing recurring jobs."""

    def __init__(self, jobs_path: Optional[Path] = None):
        self.jobs_path = jobs_path or (settings.STORAGE_DIR / "jobs.json")
        self.jobs_path.parent.mkdir(parents=True, exist_ok=True)
        self.jobs: List[Dict[str, Any]] = []
        self._load_jobs()
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[Dict[str, Any]], Any]] = []

    def _load_jobs(self) -> None:
        if self.jobs_path.exists():
            try:
                self.jobs = json.loads(self.jobs_path.read_text(encoding="utf-8"))
            except Exception:
                self.jobs = []
        else:
            self.jobs = []
            self._save_jobs()

    def _save_jobs(self) -> None:
        self.jobs_path.write_text(json.dumps(self.jobs, indent=2), encoding="utf-8")

    def register_callback(self, cb: Callable[[Dict[str, Any]], Any]) -> None:
        self._callbacks.append(cb)

    def add_job(self, name: str, prompt: str, interval_seconds: int) -> Dict[str, Any]:
        job = {
            "id": str(int(time.time())),
            "name": name,
            "prompt": prompt,
            "interval_seconds": max(10, interval_seconds),
            "last_run": time.time(),
            "enabled": True
        }
        self.jobs.append(job)
        self._save_jobs()
        logger.info(f"[CronScheduler] Added job '{name}' every {interval_seconds}s")
        return job

    def list_jobs(self) -> List[Dict[str, Any]]:
        return self.jobs

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._tick_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _tick_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(5)
                now = time.time()
                for job in self.jobs:
                    if not job.get("enabled", True):
                        continue
                    last_run = job.get("last_run", 0)
                    interval = job.get("interval_seconds", 60)
                    if now - last_run >= interval:
                        job["last_run"] = now
                        self._save_jobs()
                        logger.info(f"[CronScheduler] Triggering job: {job['name']}")
                        for cb in self._callbacks:
                            try:
                                if asyncio.iscoroutinefunction(cb):
                                    await cb(job)
                                else:
                                    cb(job)
                            except Exception as e:
                                logger.error(f"[CronScheduler] Callback error: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[CronScheduler] Loop error: {e}")

skill_loader = SkillLoader()
cron_scheduler = CronScheduler()
