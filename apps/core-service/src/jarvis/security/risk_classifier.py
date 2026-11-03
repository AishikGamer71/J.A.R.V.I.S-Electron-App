from enum import Enum
from pathlib import Path
from typing import Any
import re

from jarvis.config.settings import settings


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskClassifier:
    def __init__(self):
        self._tool_risk_map: dict[str, RiskLevel] = {
            "read_file": RiskLevel.LOW,
            "write_file": RiskLevel.MEDIUM,
            "web_search": RiskLevel.LOW,
            "execute_command": RiskLevel.HIGH,
            "system_config": RiskLevel.CRITICAL,
        }

    def register_tool_risk(self, tool_name: str, risk: RiskLevel) -> None:
        self._tool_risk_map[tool_name] = risk

    def get_static_risk(self, tool_name: str) -> RiskLevel:
        return self._tool_risk_map.get(tool_name, RiskLevel.HIGH)

    def classify(self, tool_name: str, args: dict[str, Any] | None = None) -> RiskLevel:
        base_risk = self.get_static_risk(tool_name)
        if not args:
            return base_risk

        # Dynamic Inspection 1: File path checks
        path_str = args.get("path") or args.get("filepath")
        if path_str:
            # Traversal or sensitive path escalation
            normalized = str(path_str).replace("\\", "/")
            if ".." in normalized or any(
                sensitive in normalized.lower()
                for sensitive in [".env", ".ssh", "id_rsa", "windows/system32", "/etc/passwd"]
            ):
                return RiskLevel.CRITICAL

            # Check if outside sandbox root
            try:
                target_path = (settings.SANDBOX_ROOT / path_str).resolve()
                if not target_path.is_relative_to(settings.SANDBOX_ROOT.resolve()):
                    return RiskLevel.CRITICAL
            except Exception:
                return RiskLevel.CRITICAL

        # Dynamic Inspection 2: Shell commands
        command_str = args.get("command") or args.get("cmd")
        if command_str and isinstance(command_str, str):
            destructive_patterns = [
                r"\brm\s+-rf\b",
                r"\bformat\b",
                r"\bdel\s+/[fFqQsS]\b",
                r"\bshutdown\b",
                r"\bmkfs\b",
                r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # forkbomb
            ]
            for pat in destructive_patterns:
                if re.search(pat, command_str, re.IGNORECASE):
                    return RiskLevel.CRITICAL

        return base_risk


risk_classifier = RiskClassifier()
