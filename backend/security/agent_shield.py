"""
backend/security/agent_shield.py
================================
AgentShield security gateway for J.A.R.V.I.S.
Provides:
  1. 14 secret patterns regex detection and redaction
  2. Destructive terminal/shell command blocking
  3. Config-protection guard and path traversal defense
  4. Prompt injection and jailbreak threat scanning
  5. Tool call risk classification and validation
  6. In-memory audit logging and security scoring for GET /v1/audit
"""

import math
import os
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SecurityScanResult:
    passed: bool
    violation_type: Optional[str] = None
    details: str = ""


@dataclass
class AuditLogEntry:
    id: str
    timestamp: float
    tool: str
    args: Dict[str, Any]
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    outcome: str     # "ALLOWED", "BLOCKED", "WARNED"
    violation_type: Optional[str] = None
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "tool": self.tool,
            "args": self.args,
            "risk_level": self.risk_level,
            "outcome": self.outcome,
            "violation_type": self.violation_type,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# 14 Secret Patterns & Redaction Placeholders
# ---------------------------------------------------------------------------
SECRET_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    # 1. OpenAI API Keys (legacy sk-... and project sk-proj-...)
    (
        "openai_api_key",
        re.compile(r"\b(sk-(?:proj-)?[a-zA-Z0-9_\-]{20,})\b"),
        "[REDACTED_OPENAI_KEY]",
    ),
    # 2. Anthropic API Keys (sk-ant-...)
    (
        "anthropic_api_key",
        re.compile(r"\b(sk-ant-(?:api03-)?[a-zA-Z0-9_\-]{20,})\b"),
        "[REDACTED_ANTHROPIC_KEY]",
    ),
    # 3. AWS Access Key ID & Secret Key
    (
        "aws_access_key",
        re.compile(r"\b(AKIA[0-9A-Z]{16})\b", re.IGNORECASE),
        "[REDACTED_AWS_KEY]",
    ),
    (
        "aws_secret_key",
        re.compile(r"(?i)(?:aws_secret_access_key|aws_secret_key)\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"),
        "[REDACTED_AWS_SECRET]",
    ),
    # 4. GitHub Tokens (ghp_, gho_, github_pat_)
    (
        "github_token",
        re.compile(r"\b(gh[pousr]_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{22,})\b"),
        "[REDACTED_GITHUB_TOKEN]",
    ),
    # 5. Google Cloud / Gemini API Keys (AIza...)
    (
        "google_api_key",
        re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b"),
        "[REDACTED_GEMINI_KEY]",
    ),
    # 6. Private Keys (RSA, EC, OpenSSH, PGP, DSA)
    (
        "private_key",
        re.compile(r"-----BEGIN\s+(?:[A-Z0-9_\-]+\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:[A-Z0-9_\-]+\s+)?PRIVATE\s+KEY-----|-----BEGIN\s+(?:RSA|EC|OPENSSH|PGP|DSA)\s+PRIVATE\s+KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
    # 7. Generic Bearer Tokens & JWTs
    (
        "jwt_token",
        re.compile(r"\b(eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,})\b"),
        "[REDACTED_JWT]",
    ),
    (
        "bearer_token",
        re.compile(r"(?i)\bbearer\s+([a-zA-Z0-9_\-\.]{25,})\b"),
        "Bearer [REDACTED_AUTH_TOKEN]",
    ),
    # 8. Database Connection Strings
    (
        "database_url",
        re.compile(r"\b(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|mssql)://(?:[^\s:]+):(?:[^\s@]+)@[^\s]+\b"),
        "[REDACTED_DATABASE_URL]",
    ),
    # 9. Slack Webhooks & Bot Tokens
    (
        "slack_token",
        re.compile(r"\b(xox[baprs]-[0-9a-zA-Z\-]{10,})\b|https://hooks\.slack\.com/services/T[0-9A-Z]+/B[0-9A-Z]+/[0-9a-zA-Z]+"),
        "[REDACTED_SLACK_CREDENTIAL]",
    ),
    # 10. Discord Bot Tokens & Webhooks
    (
        "discord_token",
        re.compile(r"https://discord(?:app)?\.com/api/webhooks/[0-9]+/[a-zA-Z0-9_\-]+|\b[MN][A-Za-z\d]{23,}\.[\w\-]{6}\.[\w\-]{27,}\b"),
        "[REDACTED_DISCORD_TOKEN]",
    ),
    # 11. Telegram Bot Tokens
    (
        "telegram_token",
        re.compile(r"\b([0-9]{9,10}:[a-zA-Z0-9_\-]{35})\b"),
        "[REDACTED_TELEGRAM_TOKEN]",
    ),
    # 12. Azure Storage Keys & Shared Access Signatures
    (
        "azure_key",
        re.compile(r"(?i)AccountKey\s*=\s*['\"]?[a-zA-Z0-9+/=]{86,88}['\"]?|(?:SharedAccessSignature|sig)\s*=\s*['\"]?[a-zA-Z0-9%]{40,}['\"]?"),
        "[REDACTED_AZURE_KEY]",
    ),
    # 13. Stripe Live Secret Keys
    (
        "stripe_key",
        re.compile(r"\b(sk_live_[0-9a-zA-Z]{24,})\b"),
        "[REDACTED_STRIPE_KEY]",
    ),
    # 14. Explicit Password / Credential assignments
    (
        "credential_assignment",
        re.compile(r"(?i)(?:api_key|apikey|secret|password|client_secret)\s*[:=]\s*['\"]([^'\"]{8,})['\"]"),
        "credential='[REDACTED]'",
    ),
]

# ---------------------------------------------------------------------------
# Destructive Commands Patterns
# ---------------------------------------------------------------------------
DESTRUCTIVE_COMMAND_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\brm\s+(?:-[a-zA-Z0-9_\-]+\s+)+[/\\*~.]", re.IGNORECASE), "Recursive root/current directory deletion"),
    (re.compile(r"\brm\b(?=.*(?:\s-[a-zA-Z]*[rR]|\s--recursive\b))(?=.*(?:\s-[a-zA-Z]*[fF]|\s--force\b))", re.IGNORECASE), "Recursive forced removal"),
    (re.compile(r"\bdel\b(?=.*\/[sS])(?=.*\/[qQ])", re.IGNORECASE), "Windows recursive silent deletion"),
    (re.compile(r"\b(?:rmdir|rd)\b(?=.*\/[sS])(?=.*\/[qQ])", re.IGNORECASE), "Windows silent directory removal"),
    (re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE), "Disk formatting"),
    (re.compile(r"\bformat-volume\b", re.IGNORECASE), "PowerShell disk formatting"),
    (re.compile(r"\bdiskpart\b", re.IGNORECASE), "Disk partition utility"),
    (re.compile(r"\bmkfs(?:\.[a-z0-9]+)?\b", re.IGNORECASE), "Filesystem format"),
    (re.compile(r"\bdd\s+if=", re.IGNORECASE), "Direct block storage overwrite"),
    (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", re.IGNORECASE), "Fork bomb"),
    (re.compile(r"\breg\s+(?:delete|clean)\b", re.IGNORECASE), "Windows Registry deletion"),
    (re.compile(r"\bregedit(?:\.exe)?(?:\s+/[sS])?", re.IGNORECASE), "Silent registry editor invocation"),
    (re.compile(r"\bshutdown\s+/[sSrR]", re.IGNORECASE), "System shutdown/reboot"),
]

# ---------------------------------------------------------------------------
# Prompt Injection & Jailbreak Patterns
# ---------------------------------------------------------------------------
PROMPT_INJECTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions", re.IGNORECASE), "Instruction override"),
    (re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions", re.IGNORECASE), "Instruction disregard"),
    (re.compile(r"forget\s+(?:all\s+)?(?:previous|prior)\s+instructions", re.IGNORECASE), "Instruction erasure"),
    (re.compile(r"(?:output|reveal|print|repeat)\s+(?:the\s+)?system\s+prompt", re.IGNORECASE), "System prompt extraction"),
    (re.compile(r"what\s+are\s+your\s+(?:system\s+)?instructions", re.IGNORECASE), "Instruction probing"),
    (re.compile(r"\bDAN\s+mode\b|do\s+anything\s+now", re.IGNORECASE), "DAN jailbreak"),
    (re.compile(r"\bdeveloper\s+mode\s+enabled\b", re.IGNORECASE), "Developer mode jailbreak"),
    (re.compile(r"you\s+are\s+now\s+(?:in\s+)?unfiltered\b", re.IGNORECASE), "Filter bypass"),
    (re.compile(r"override\s+(?:governance|security)\s+rules", re.IGNORECASE), "Rule override"),
    (re.compile(r"new\s+rule:\s*ignore", re.IGNORECASE), "Adversarial rule injection"),
]

# ---------------------------------------------------------------------------
# Protected Config Files & System Directories
# ---------------------------------------------------------------------------
PROTECTED_PATH_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(^|[/\\])\.env(\.[a-zA-Z0-9_\-]+)?$", re.IGNORECASE), ".env secret configuration"),
    (re.compile(r"(^|[/\\])(?:config|credentials|service_account.*)\.json$", re.IGNORECASE), "Service credential files"),
    (re.compile(r"(^|[/\\])\.(?:antigravity|agent)[/\\]rules.*\.md$", re.IGNORECASE), "Governance rules file"),
    (re.compile(r"(^|[/\\])src[/\\]layouts[/\\]jarvis-layout\.tsx$", re.IGNORECASE), "Core UI layout file"),
    (re.compile(r"(^|[/\\])src[/\\]components[/\\]", re.IGNORECASE), "Visual UI component files"),
    (re.compile(r"(^|[/\\])(?:package\.json|tsconfig.*\.json|vite\.config\.ts|\.eslintrc.*|components\.json)$", re.IGNORECASE), "Project build config"),
    (re.compile(r"(^|[/\\])(?:id_rsa|id_ed25519|\.ssh[/\\]authorized_keys)$", re.IGNORECASE), "SSH keys"),
    (re.compile(r"(^|[/\\])(?:etc[/\\](?:passwd|shadow|hosts)|system32(?:[/\\]|$)|win\.ini)", re.IGNORECASE), "Operating system critical files"),
]


def _shannon_entropy(s: str) -> float:
    """Calculates Shannon entropy of a string."""
    if not s:
        return 0.0
    freq: Dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    entropy = 0.0
    length = float(len(s))
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


class AgentShield:
    """Central Security Barrier for J.A.R.V.I.S."""

    def __init__(self):
        self._audit_logs: List[AuditLogEntry] = []
        self._counter = 0

    @property
    def audit_logs(self) -> List[Dict[str, Any]]:
        return [entry.to_dict() for entry in self._audit_logs]

    def _add_audit_log(
        self,
        tool: str,
        args: Dict[str, Any],
        risk_level: str,
        outcome: str,
        violation_type: Optional[str] = None,
        details: str = "",
    ):
        self._counter += 1
        entry = AuditLogEntry(
            id=f"audit-{self._counter:05d}",
            timestamp=time.time(),
            tool=tool,
            args=args,
            risk_level=risk_level,
            outcome=outcome,
            violation_type=violation_type,
            details=details,
        )
        self._audit_logs.append(entry)
        # Cap audit log to prevent unbounded memory growth
        if len(self._audit_logs) > 1000:
            self._audit_logs = self._audit_logs[-1000:]

    def get_security_score(self) -> str:
        """Returns security grade ('A' clean down to 'F' critical violations)."""
        critical_count = sum(1 for e in self._audit_logs if e.risk_level == "CRITICAL" and e.outcome == "BLOCKED")
        high_count = sum(1 for e in self._audit_logs if e.risk_level == "HIGH" and e.outcome == "BLOCKED")
        if critical_count > 5:
            return "F"
        if critical_count > 0 or high_count > 5:
            return "D"
        if high_count > 0:
            return "C"
        warn_count = sum(1 for e in self._audit_logs if e.outcome == "WARNED")
        if warn_count > 5:
            return "B"
        return "A"

    def scan_input(self, text: str) -> SecurityScanResult:
        """
        Scans untrusted text for:
          - 14 secret patterns
          - Prompt injection and jailbreak threats
        """
        if not text or not text.strip():
            return SecurityScanResult(passed=True, details="Empty or whitespace input")

        # Strip null bytes and normalize Unicode
        normalized = unicodedata.normalize("NFKD", text).replace("\x00", "")
        # Remove bidirectional overrides
        normalized = re.sub(r"[\u202A-\u202E\u2066-\u2069]", "", normalized)

        # 1. Check prompt injection signatures
        for pattern, desc in PROMPT_INJECTION_PATTERNS:
            if pattern.search(normalized):
                self._add_audit_log(
                    tool="input_scanner",
                    args={"preview": text[:80]},
                    risk_level="HIGH",
                    outcome="BLOCKED",
                    violation_type="prompt_injection",
                    details=f"Prompt injection detected: {desc}",
                )
                return SecurityScanResult(
                    passed=False,
                    violation_type="prompt_injection",
                    details=f"Prompt injection pattern detected: {desc}",
                )

        # 2. Check secret patterns
        for secret_name, pattern, _ in SECRET_PATTERNS:
            match = pattern.search(normalized)
            if match:
                self._add_audit_log(
                    tool="input_scanner",
                    args={"preview": "[REDACTED]"},
                    risk_level="HIGH",
                    outcome="BLOCKED",
                    violation_type="secret_leak",
                    details=f"Secret pattern detected: {secret_name}",
                )
                return SecurityScanResult(
                    passed=False,
                    violation_type="secret_leak",
                    details=f"Credential pattern detected: {secret_name}",
                )

        return SecurityScanResult(passed=True, details="Clean input")

    def validate_command(self, cmd: str) -> bool:
        """
        Validates shell / terminal command before execution.
        Returns True if safe, False if blocked.
        """
        if not cmd:
            return True

        # Sanitize null bytes and normalize
        sanitized = cmd.replace("\x00", "").strip()
        sanitized = unicodedata.normalize("NFKD", sanitized)

        # Check against destructive patterns
        for pattern, desc in DESTRUCTIVE_COMMAND_PATTERNS:
            if pattern.search(sanitized):
                self._add_audit_log(
                    tool="execute_command",
                    args={"command": cmd[:120]},
                    risk_level="CRITICAL",
                    outcome="BLOCKED",
                    violation_type="destructive_command",
                    details=f"Destructive command blocked: {desc}",
                )
                return False

        # Additional heuristics for chained commands
        sub_commands = re.split(r"[;&|]+", sanitized)
        for sub in sub_commands:
            sub = sub.strip()
            for pattern, desc in DESTRUCTIVE_COMMAND_PATTERNS:
                if pattern.search(sub):
                    self._add_audit_log(
                        tool="execute_command",
                        args={"command": cmd[:120]},
                        risk_level="CRITICAL",
                        outcome="BLOCKED",
                        violation_type="destructive_command",
                        details=f"Destructive sub-command blocked: {desc}",
                    )
                    return False

        return True

    def sanitize_output(self, text: str) -> str:
        """Redacts all 14 secret patterns from output text."""
        if not text:
            return text

        result = text
        for _, pattern, placeholder in SECRET_PATTERNS:
            result = pattern.sub(placeholder, result)

        return result

    def verify_file_path(self, path_str: str, write_mode: bool = False) -> Tuple[bool, str]:
        """
        Verifies that file access respects config protection and path traversal rules.
        """
        if not path_str or not path_str.strip():
            return False, "Empty file path"

        # Check for null bytes
        if "\x00" in path_str:
            return False, "Access denied: Null byte in path"

        clean_path = path_str.replace("\\", "/")

        # Path traversal checks
        parts = clean_path.split("/")
        if ".." in parts:
            return False, "Access denied: Path traversal attempt ('..')"

        # Check protected patterns
        for pattern, desc in PROTECTED_PATH_PATTERNS:
            if pattern.search(clean_path):
                # If writing to protected path or reading sensitive secret files
                if write_mode or ".env" in clean_path or "credentials" in clean_path or "shadow" in clean_path:
                    self._add_audit_log(
                        tool="file_guard",
                        args={"path": path_str, "write_mode": write_mode},
                        risk_level="HIGH",
                        outcome="BLOCKED",
                        violation_type="protected_file_access",
                        details=f"Access denied to protected file: {desc}",
                    )
                    return False, f"Access denied: {desc}"

        return True, "Path verified"

    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Comprehensive validation of a tool call before invocation.
        Returns (allowed: bool, reason: str).
        """
        tool_lower = (tool_name or "").lower()

        # 1. Command execution tools
        if any(kw in tool_lower for kw in ["command", "bash", "cmd", "powershell", "terminal", "exec"]):
            cmd = arguments.get("command") or arguments.get("cmd") or arguments.get("script") or ""
            if not self.validate_command(str(cmd)):
                return False, f"Blocked: Command violates security policies"

        # 2. File manipulation tools
        if any(kw in tool_lower for kw in ["file", "path", "write", "read", "delete", "create"]):
            path_val = (
                arguments.get("path")
                or arguments.get("file_path")
                or arguments.get("target_path")
                or arguments.get("source_path")
                or ""
            )
            is_write = any(w in tool_lower for w in ["write", "delete", "update", "create", "append", "modify"])
            if path_val:
                allowed, reason = self.verify_file_path(str(path_val), write_mode=is_write)
                if not allowed:
                    return False, reason

        # 3. Check for secrets leaked inside arguments (recursively scanning dicts, lists, and strings)
        def _scan_argument_val(val: Any, path: str) -> Optional[Tuple[bool, str]]:
            if isinstance(val, str):
                scan = self.scan_input(val)
                if not scan.passed:
                    return False, f"Blocked: Argument '{path}' contains prohibited pattern ({scan.violation_type})"
            elif isinstance(val, dict):
                for sub_k, sub_v in val.items():
                    sub_path = f"{path}.{sub_k}" if path else str(sub_k)
                    res = _scan_argument_val(sub_v, sub_path)
                    if res is not None:
                        return res
            elif isinstance(val, (list, tuple, set)):
                for idx, item in enumerate(val):
                    sub_path = f"{path}[{idx}]"
                    res = _scan_argument_val(item, sub_path)
                    if res is not None:
                        return res
            return None

        for k, v in arguments.items():
            violation = _scan_argument_val(v, k)
            if violation is not None:
                return violation

        return True, "Tool call validated"
