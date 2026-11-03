"""
backend/automation/s3/agent_s3.py
Agent-S s3 UIAgent Planner and Action Prediction Loop.
Translates high-level user directives into discrete GUI action tokens.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from backend.automation.s3.grounding import OSWorldACI
from backend.automation.s3.common_utils import call_llm_safe

logger = logging.getLogger("jarvis.automation.s3")

AGENT_S3_SYSTEM_PROMPT = """
You are AgentS3, the autonomous Windows Computer Use Specialist for J.A.R.V.I.S.
You interact directly with the Windows desktop using discrete GUI action tokens.

Available Actions:
- CLICK(element_description) : Click on a button, icon, or menu item
- DOUBLE_CLICK(element_description) : Double click on an item or file
- RIGHT_CLICK(element_description) : Right click to open context menu
- TYPE(text) : Type characters or strings into the focused field
- PRESS(key) : Press a key (Enter, Escape, Tab, Backspace, etc.)
- WAIT(seconds) : Wait for an application to open or render
- DONE : Mark the task as successfully completed
- FAIL : Mark the task as unachievable

Rules:
1. Always output EXACTLY ONE action line per step.
2. When the objective is achieved, output ONLY 'DONE'.
3. Do not include markdown formatting or extra conversational fluff.
"""

class AgentS3:
    """AgentS3 autonomous GUI agent governing desktop observation and action planning."""

    def __init__(self):
        self.aci = OSWorldACI()
        self.history: List[str] = []

    async def predict(self, instruction: str, observation: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """
        Observes desktop and predicts the next GUI action token.
        """
        obs = observation or self.aci.capture_screen()
        history_str = "\n".join(self.history[-5:]) if self.history else "None"

        prompt = (
            f"Instruction: {instruction}\n"
            f"Recent Actions: {history_str}\n"
            f"Predict the next discrete action token:"
        )

        raw_response = await call_llm_safe(
            prompt=prompt,
            system_prompt=AGENT_S3_SYSTEM_PROMPT.strip(),
            temperature=0.0
        )

        cleaned_action = raw_response.strip().splitlines()[0] if raw_response else "DONE"
        # Strip code blocks if present
        if cleaned_action.startswith("```"):
            cleaned_action = cleaned_action.strip("`").strip()

        self.history.append(cleaned_action)
        return ({"observation_hash": obs.get("hash", "")}, [cleaned_action])

    def reset(self) -> None:
        self.history.clear()
