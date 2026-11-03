"""
backend/automation/desktop_controller.py
Agent-S s3 Desktop Automation Controller.
Features Upstream Issue #235/236 Fix (exact DONE/FAIL token matching),
Sub-millisecond Ctrl+Alt+Backspace Emergency Kill-Switch, and live TerminalLogs streaming.
"""

import time
import asyncio
import re
import logging
from typing import Dict, Any, List, Optional, Callable
import native_core
from backend.automation.s3.agent_s3 import AgentS3
from backend.automation.s3.grounding import OSWorldACI

logger = logging.getLogger("jarvis.automation.controller")

class DesktopController:
    """Orchestrates autonomous GUI automation with emergency hardware interrupt."""

    def __init__(self):
        self.agent = AgentS3()
        self.aci = OSWorldACI()
        self.is_running: bool = False
        self._log_callbacks: List[Callable[[str, str], Any]] = []

    def add_log_callback(self, cb: Callable[[str, str], Any]) -> None:
        self._log_callbacks.append(cb)

    async def _emit_log(self, level: str, message: str) -> None:
        logger.info(f"[DesktopController] {message}")
        for cb in self._log_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(level, message)
                else:
                    cb(level, message)
            except Exception:
                pass

    async def run_task(self, instruction: str, max_steps: int = 15) -> Dict[str, Any]:
        """
        Executes an autonomous Windows GUI task loop.
        Terminates cleanly on 'DONE', 'FAIL', max_steps, or emergency kill-switch.
        """
        self.is_running = True
        self.agent.reset()
        native_core.reset_emergency_abort()

        await self._emit_log("info", f"Initiating Desktop GUI Task: '{instruction}'")
        step = 0
        outcome = "COMPLETED"

        while step < max_steps and self.is_running:
            step += 1

            # 1. Sub-millisecond Hardware Kill-Switch Check (Ctrl+Alt+Backspace)
            if native_core.check_emergency_abort():
                outcome = "ABORTED_BY_KILL_SWITCH"
                await self._emit_log("error", "EMERGENCY KILL-SWITCH TRIGGERED (Ctrl+Alt+Backspace). Halting immediately.")
                break

            # 2. Capture Screen
            obs = self.aci.capture_screen()

            # 3. Predict Action Token
            await self._emit_log("info", f"Analyzing screen state for step {step}/{max_steps}...")
            info, code = await self.agent.predict(instruction=instruction, observation=obs)

            if not code or not code[0]:
                break

            action_raw = code[0].strip()
            await self._emit_log("agent_step", f"Step {step}: {action_raw}")

            # 4. Mandatory Fix for Upstream Issue #235 / #236:
            # Exact token check prevents premature termination when typing text containing words 'done' or 'fail'
            if action_raw in ("DONE", "FAIL"):
                if action_raw == "FAIL":
                    outcome = "FAILED"
                    await self._emit_log("warn", "Task marked as unachievable by GUI agent.")
                else:
                    outcome = "SUCCESS"
                    await self._emit_log("success", "GUI task marked as DONE successfully.")
                break

            # 5. Execute Action
            await self._execute_action_token(action_raw)
            await asyncio.sleep(0.8)

        self.is_running = False
        return {
            "status": outcome,
            "steps_executed": step,
            "instruction": instruction
        }

    async def _execute_action_token(self, action_token: str) -> None:
        """Parses and executes a discrete action token."""
        # Check abort before moving or typing
        if native_core.check_emergency_abort():
            return

        # CLICK(desc)
        m_click = re.match(r"^CLICK\((.*)\)$", action_token, re.IGNORECASE)
        if m_click:
            target = m_click.group(1).strip("'\"")
            x, y = await self.aci.generate_coords(target)
            self.aci.click(x, y)
            return

        # DOUBLE_CLICK(desc)
        m_dc = re.match(r"^DOUBLE_CLICK\((.*)\)$", action_token, re.IGNORECASE)
        if m_dc:
            target = m_dc.group(1).strip("'\"")
            x, y = await self.aci.generate_coords(target)
            self.aci.double_click(x, y)
            return

        # RIGHT_CLICK(desc)
        m_rc = re.match(r"^RIGHT_CLICK\((.*)\)$", action_token, re.IGNORECASE)
        if m_rc:
            target = m_rc.group(1).strip("'\"")
            x, y = await self.aci.generate_coords(target)
            self.aci.right_click(x, y)
            return

        # TYPE(text)
        m_type = re.match(r"^TYPE\((.*)\)$", action_token, re.IGNORECASE)
        if m_type:
            text = m_type.group(1).strip("'\"")
            self.aci.type_text(text)
            return

        # PRESS(key)
        m_press = re.match(r"^PRESS\((.*)\)$", action_token, re.IGNORECASE)
        if m_press:
            key = m_press.group(1).strip("'\"")
            self.aci.press_key(key)
            return

        # WAIT(sec)
        m_wait = re.match(r"^WAIT\((\d+)\)$", action_token, re.IGNORECASE)
        if m_wait:
            sec = int(m_wait.group(1))
            await asyncio.sleep(sec)
            return

desktop_controller = DesktopController()
