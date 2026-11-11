"""
backend/security/ecc_hooks.py
=============================
ECC (Epistemic Calibration & Continuous Learning) Hooks for J.A.R.V.I.S.
Manages pre-tool and post-tool lifecycle hooks, enforcing AgentShield security
and logging execution observations to ~/.jarvis/homunculus/observations.jsonl.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from backend.security.agent_shield import AgentShield

logger = logging.getLogger("jarvis.ecc_hooks")


@dataclass
class PreToolHookResult:
    allowed: bool
    reason: str = ""
    scan_result: Optional[Any] = None


@dataclass
class PostToolHookResult:
    recorded: bool
    observation: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class ECCHookDispatcher:
    """Dispatches pre-tool validation and post-tool telemetry observations."""

    def __init__(self, log_path: Optional[Path] = None, shield: Optional[AgentShield] = None):
        self.log_path = log_path or (Path.home() / ".jarvis" / "homunculus" / "observations.jsonl")
        self.shield = shield or AgentShield()
        self._lock = threading.Lock()

    def pre_tool_use(
        self,
        tool_name: str,
        args: Dict[str, Any],
        session_id: str = "default",
    ) -> PreToolHookResult:
        """
        Validates tool execution against AgentShield security rules.
        """
        allowed, reason = self.shield.validate_tool_call(tool_name, args)
        if not allowed:
            logger.warning(
                "Tool execution blocked by AgentShield: tool=%s, session=%s, reason=%s",
                tool_name,
                session_id,
                reason,
            )
            return PreToolHookResult(allowed=False, reason=reason)

        return PreToolHookResult(allowed=True, reason="Validated")

    # Alias for contract test compatibility
    pre_tool_hook = pre_tool_use

    def format_observation(
        self,
        tool_name: str,
        args: Dict[str, Any],
        status: Any = "success",
        duration_ms: float = 0.0,
        session_id: str = "default",
        result: Any = None,
    ) -> Dict[str, Any]:
        """
        Serializes execution event metadata into a standardized observation dictionary.
        """
        # Status might be passed as string or as result
        status_str = "success"
        result_payload = result
        if isinstance(status, str) and status.lower() in ("success", "failed", "error", "blocked", "pending"):
            status_str = status.lower()
        elif result is None:
            result_payload = status
            status_str = "success"

        # Sanitize result summary if string
        sanitized_summary = ""
        if result_payload is not None:
            if isinstance(result_payload, str):
                sanitized_summary = self.shield.sanitize_output(result_payload[:500])
            else:
                try:
                    sanitized_summary = self.shield.sanitize_output(json.dumps(result_payload, default=str)[:500])
                except Exception:
                    sanitized_summary = str(result_payload)[:500]

        # Convert args to JSON-serializable structure
        serializable_args = {}
        for k, v in args.items():
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                serializable_args[k] = v
            else:
                serializable_args[k] = str(v)

        return {
            "timestamp": time.time(),
            "session_id": session_id,
            "tool_name": tool_name,
            "args": serializable_args,
            "status": status_str,
            "duration_ms": duration_ms,
            "result_summary": sanitized_summary,
        }

    def post_tool_use(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        status: str = "success",
        duration_ms: float = 0.0,
        session_id: str = "default",
    ) -> PostToolHookResult:
        """
        Records post-execution telemetry into observations.jsonl.
        """
        try:
            obs = self.format_observation(
                tool_name=tool_name,
                args=args,
                status=status,
                duration_ms=duration_ms,
                session_id=session_id,
                result=result,
            )

            # Ensure parent directories exist
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

            # Append JSON line under thread lock
            line = json.dumps(obs, default=str)
            with self._lock:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")

            return PostToolHookResult(recorded=True, observation=obs)
        except Exception as e:
            logger.error("Failed to append observation log: %s", e)
            return PostToolHookResult(recorded=False, error=str(e))

    # Alias for contract test compatibility
    post_tool_hook = post_tool_use
