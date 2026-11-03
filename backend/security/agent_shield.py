"""
backend/security/agent_shield.py
ECC-Assimilated PreToolUse Command Blocker & Secret Leak Scanner.
Enforces strict security guardrails before tool execution and redacts credentials.
Wired directly to native_core.verify_command_safety.
"""

import re
import logging
from typing import Tuple, Dict, Any, Optional
from native_core import verify_command_safety

logger = logging.getLogger("jarvis.security")

# Known sensitive environment / file targets
FORBIDDEN_FILE_TARGETS = [
    re.compile(r"(\.env|\.git/config|id_rsa|id_ed25519|credentials\.json|service_account.*\.json)", re.IGNORECASE)
]

# Common credential patterns for output redaction
SECRET_REDACTION_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"gho_[A-Za-z0-9]{36}"), "[REDACTED_GITHUB_OAUTH]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"AQ\.[A-Za-z0-9_\-]{30,}"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"bearer\s+[A-Za-z0-9_\-\.]{25,}", re.IGNORECASE), "Bearer [REDACTED_AUTH_TOKEN]"),
    (re.compile(r"(?:api_key|apikey|secret|password|token)\s*[:=]\s*['\"]([^'\"]{8,})['\"]", re.IGNORECASE), "credential='[REDACTED]'")
]


class AgentShield:
    """ECC Security Shield protecting the desktop from destructive actions and secret leaks."""

    @staticmethod
    def verify_command(command: str) -> Tuple[bool, str]:
        """
        Runs native_core regex safety check on shell commands.
        Returns (is_safe, reason).
        """
        is_safe, reason, matched = verify_command_safety(command)
        if not is_safe:
            logger.warning(f"[AgentShield] BLOCKED dangerous command: {reason} | Matched: {matched}")
            return False, reason
        return True, "Command passed security verification"

    @staticmethod
    def verify_file_path(path_str: str, write_mode: bool = False) -> Tuple[bool, str]:
        """
        Ensures tools cannot read or overwrite critical credential files.
        """
        for pat in FORBIDDEN_FILE_TARGETS:
            if pat.search(path_str):
                action = "write to" if write_mode else "read from"
                logger.warning(f"[AgentShield] BLOCKED file access to protected file: {path_str}")
                return False, f"Access denied: Prohibited to {action} protected configuration {path_str}"
        return True, "Path allowed"

    @staticmethod
    def sanitize_output(text: str) -> str:
        """
        Redacts API keys and secrets from output before pushing to TerminalLogs or UI.
        """
        if not text:
            return ""
        sanitized = text
        for pat, replacement in SECRET_REDACTION_PATTERNS:
            sanitized = pat.sub(replacement, sanitized)
        return sanitized

    @classmethod
    def validate_tool_use(cls, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Universal pre-execution check for any registered agent tool.
        """
        if tool_name in ("run_terminal", "run_safe_terminal", "bash", "powershell", "execute_command"):
            cmd = arguments.get("command") or arguments.get("cmd") or ""
            return cls.verify_command(str(cmd))

        elif tool_name in ("read_file", "write_file", "edit_file", "delete_file"):
            target_path = arguments.get("path") or arguments.get("file_path") or ""
            is_write = tool_name in ("write_file", "edit_file", "delete_file")
            return cls.verify_file_path(str(target_path), write_mode=is_write)

        return True, "Tool call validated"
