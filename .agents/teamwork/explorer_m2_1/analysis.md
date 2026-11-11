# Technical Analysis & Specification Blueprint: Security & Continuous Learning (Milestone 2)

**Author**: `teamwork_spec_miner` (`explorer_m2_1`)  
**Scope**: Milestone 2 Subsystem 1 (`AgentShield`, `ECCHookDispatcher`, `InstinctEngine`)  
**Authoritative Sources**: 
- `c:\Users\utpal\Downloads\jarvis_antigravity_master_prompt.md` (Sections 2.2, 2.3, 3.1, 4.2, 5.3, 6.1)
- `e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.antigravity\rules.md` & `.agent/rules/rules.md`
- `e:\Projects\J.A.R.V.I.S Electron App\backend\agents\security_auditor.md`
- `tests/e2e/test_tier1_features.py` (Tests F07-01 to F07-05, F08-01 to F08-05, F09-01 to F09-05)
- `tests/e2e/test_tier2_boundaries.py` (Tests B01 to B07)
- `tests/e2e/test_tier3_combinations.py` (Tests C01 to C02)
- Git historical implementations (`backend/security/agent_shield.py`, `backend/memory/instinct_learner.py`, `native_core/jarvis_native_fallback.py`)

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Security | 14 Secret Patterns Regex & Redaction | Scans text and redacts 14 credential types (AWS, GitHub, OpenAI, Google, Anthropic, Bearer/JWT, Private Keys, DB strings, Slack, Discord, Telegram, Azure, Stripe, high-entropy passwords) | `text: str` | `SecurityScanResult(passed=bool, violation_type=str, details=str)` or redacted `str` | Flags violation; `passed=False` on leak detection; redacts in `sanitize_output` | `security_auditor.md:22-38`, `master_prompt.md:239`, `test_tier1_features.py:241` |
| 2 | Security | Destructive Command Blocking | Blocks destructive shell/terminal commands (`rm -rf /`, `format`, `del /f /s /q`, registry wipes, fork bombs, disk wipe/dd, mkfs, diskpart) | `cmd: str` | `bool` (`True` if safe, `False` if blocked) | Logs to audit trail as `CRITICAL` risk; returns `False` | `rules.md:39-45`, `master_prompt.md:239`, `test_tier1_features.py:247` |
| 3 | Security | Config & Protected File Guard | Prevents tampering or unauthorized access to `.env`, governance rules (`.antigravity/rules.md`, `.agent/rules/rules.md`), visual UI files (`src/layouts/*`, `src/components/*`), build configs, and system files | `path_str: str`, `write_mode: bool` | `Tuple[bool, str]` | Denies path access, logs violation | `rules.md:12-20`, `security_auditor.md:46-51`, `test_tier1_features.py:272` |
| 4 | Security | Prompt Injection Threat Scanning | Scans untrusted input for jailbreak attacks (DAN mode), system prompt extraction, and rule override attempts | `text: str` | `SecurityScanResult` | Sets `passed=False`, `violation_type="prompt_injection"` | `test_tier1_features.py:252`, `security_auditor.md:18`, `master_prompt.md:239` |
| 5 | Security | Tool Call Risk Classification & Validation | Validates tool invocations against command, file, and injection rules before execution | `tool_name: str`, `args: Dict[str, Any]` | `Tuple[bool, str]` | Blocks invalid/dangerous tool arguments | `agent_shield.py:65`, `test_m2_security.py:30` |
| 6 | Security | Audit Log & Security Scoring | Maintains in-memory audit records of all scans, tool validations, and security verdicts; exposes security grade (`A` to `F`) | None (queried via `GET /v1/audit`) | `audit_logs: List[Dict]`, `score: str` | Degrades grade upon violations (`A` clean -> `F` critical) | `master_prompt.md:364`, `security_auditor.md:58-63` |
| 7 | ECC Hooks | Pre-Tool Execution Hook | Hook executed before any tool runs; invokes `AgentShield.validate_tool_call()` to enforce security barriers | `tool_name: str`, `args: Dict[str, Any]`, `session_id: str` | `PreToolHookResult(allowed=bool, reason=str)` | Blocks execution if security scan fails | `master_prompt.md:240`, `test_tier1_features.py:269-274` |
| 8 | ECC Hooks | Post-Tool Execution Hook | Hook executed after tool completes; sanitizes output and logs invocation metadata to `~/.jarvis/homunculus/observations.jsonl` | `tool_name: str`, `args: Dict`, `result: Any`, `status: str`, `duration_ms: float`, `session_id: str` | `PostToolHookResult(recorded=bool, observation=Dict)` | Fails open with error message if logging fails | `master_prompt.md:240`, `test_tier1_features.py:275-280` |
| 9 | ECC Hooks | Observation Log Serialization | Formats execution event into JSON schema with timestamp, session ID, tool name, arguments, status, and duration | `tool_name: str`, `args: Dict`, `status_or_result: Any`, `duration_ms: float`, `session_id: str` | `Dict[str, Any]` containing `"timestamp"`, `"session_id"`, `"tool_name"`, etc. | Validates JSON serializability, converts non-serializable objects | `test_tier1_features.py:281-286`, `master_prompt.md:240` |
| 10 | Learning | Observation Log Parsing | Ingests `~/.jarvis/homunculus/observations.jsonl` and identifies repeated tool sequences, failures, and user preferences | `observations_path: Optional[Path]` | `List[Instinct]` | Handles missing file or malformed lines gracefully | `master_prompt.md:241`, `test_tier1_features.py:298-303` |
| 11 | Learning | Confidence Scoring Engine | Computes instinct confidence using confirmation count, contradiction count, and occurrence count ($\ge 0.90$ for 10 confirmations, 0 contradictions) | `trigger: str`, `confirmations: int`, `contradictions: int` | `float` (0.0 to 1.0) | Clamps scores between `0.0` and `1.0` | `master_prompt.md:237, 241`, `test_tier1_features.py:304-309` |
| 12 | Learning | Personal Instinct File Storage | Persists atomic YAML/Markdown files in `~/.jarvis/homunculus/instincts/personal/` with schema (`id`, `trigger`, `action`, `confidence`, `domain`, `source`, `scope`, `updated_at`) | `Instinct` object | File path or boolean success | Creates directory tree if absent | `master_prompt.md:241`, `rules.md:73-76` |
| 13 | Learning | Dynamic Prompt Injection Block | Filters active instincts with `confidence >= 0.70` and renders a Markdown block for injection into `HermesBrain` system prompt | `min_confidence: float = 0.70` | `str` (Markdown block) or `List[Dict]` | Returns empty string / empty list if no active instincts | `master_prompt.md:241, 254`, `test_tier1_features.py:310-315` |
| 14 | Learning | Instinct Pruning & Decay | Prunes or archives instincts with confidence below threshold (e.g. `< 0.50`), and applies temporal decay | `min_confidence: float = 0.50` | `int` (count of pruned records) | Non-destructive archiving or removal | `test_tier1_features.py:316-321`, `master_prompt.md:237` |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `scan_input` | Empty string `""` | Returns `SecurityScanResult(passed=True, violation_type=None, details="Empty input")`. Zero false positives or exceptions. |
| 2 | `scan_input` | Whitespace-only string `"   \t\r\n   "` | Returns `SecurityScanResult(passed=True, violation_type=None, details="Whitespace only")`. |
| 3 | `scan_input` | 1 MB payload of repeated text (`"a" * 1048576`) | Completes within < 15ms without catastrophic regex backtracking (ReDoS). Uses pre-compiled atomic/linear regexes. |
| 4 | `validate_command` | Null bytes embedded in command (`"echo hello\x00rm -rf /"`) | Sanitizes/strips null bytes or flags them; detects `"rm -rf"` embedded after null byte and returns `False`. |
| 5 | `scan_input` | Unicode homoglyphs and BiDi override (`"\u202Ereversed_command"`) | Normalizes input (NFKD/NFKC) and strips directional override characters before scanning; detects disguised tokens. |
| 6 | `scan_input` | Case-insensitive secret pattern (`"akiaiosfodnn7example"`) | AWS key regex with case-insensitive matching flags secret; returns `passed=False`. |
| 7 | `validate_command` | Fragmented / chained destructive commands (`"echo a && rm -rf /"`, `"del /f /s /q C:\\"`) | Substring and regex match catches chained operators (`&&`, `;`, `\|`); returns `False`. |
| 8 | `verify_file_path` | Path traversal attacks (`"../../etc/passwd"`, `"..\\.env"`) | Resolves canonical path and checks for `..` tokens; denies access with `(False, "Access denied: Path traversal attempt")`. |
| 9 | `format_observation` | Tool args with non-JSON serializable objects (e.g. `bytes`, `datetime`, `Exception`) | Recursively converts un-serializable objects to strings or base64 representation; prevents `TypeError: Object of type ... is not JSON serializable`. |
| 10 | `parse_observations` | Corrupted / partially written lines in `observations.jsonl` | Ignores invalid lines with a warning and continues parsing valid JSON records; does not crash. |
| 11 | `score_instinct` | High confirmations (`10` confirms, `0` contradicts) | Returns `1.0 >= 0.90` (meets strict assertion in `test_tier1_features.py:308`). |
| 12 | `score_instinct` | Heavy contradiction (`1` confirm, `10` contradicts) | Score drops to `0.0` (clamped); gets excluded from active prompt injection and marked for pruning. |

---

## Component Blueprints & Technical Specifications

### 1. `backend/security/agent_shield.py`

#### Interface Contract
```python
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

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

class AgentShield:
    def scan_input(self, text: str) -> SecurityScanResult: ...
    def validate_command(self, cmd: str) -> bool: ...
    def sanitize_output(self, text: str) -> str: ...
    def verify_file_path(self, path_str: str, write_mode: bool = False) -> Tuple[bool, str]: ...
    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]: ...
    @property
    def audit_logs(self) -> List[Dict[str, Any]]: ...
    def get_security_score(self) -> str: ...
```

#### Exact 14 Secret Patterns & Redaction Rules
1. **OpenAI API Key**:
   - Regex: `r"\b(sk-[a-zA-Z0-9]{20,}|sk-proj-[a-zA-Z0-9_-]{20,})\b"`
   - Redaction: `"[REDACTED_OPENAI_KEY]"`
2. **Anthropic API Key**:
   - Regex: `r"\b(sk-ant-(?:api03-)?[a-zA-Z0-9_-]{20,})\b"`
   - Redaction: `"[REDACTED_ANTHROPIC_KEY]"`
3. **AWS Access Key ID & Secret Key**:
   - Regex (Key ID): `r"\b(AKIA[0-9A-Z]{16})\b"` (with case-insensitive pattern matching)
   - Regex (Secret): `r"(?i)(?:aws_secret_access_key|aws_secret_key)\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"`
   - Redaction: `"[REDACTED_AWS_KEY]"`
4. **GitHub Personal Access Tokens & OAuth**:
   - Regex: `r"\b(ghp_[0-9a-zA-Z]{36}|gho_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{22,})\b"`
   - Redaction: `"[REDACTED_GITHUB_TOKEN]"`
5. **Google Cloud / Gemini API Key**:
   - Regex: `r"\b(AIza[0-9A-Za-z-_]{35}|AQ\.[0-9A-Za-z-_]{30,})\b"`
   - Redaction: `"[REDACTED_GEMINI_KEY]"`
6. **Private Keys (RSA, EC, OpenSSH, PGP, DSA)**:
   - Regex: `r"-----BEGIN\s+(?:[A-Z0-9_-]+\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:[A-Z0-9_-]+\s+)?PRIVATE\s+KEY-----|-----BEGIN\s+(?:RSA|EC|OPENSSH|PGP|DSA)\s+PRIVATE\s+KEY-----"`
   - Redaction: `"[REDACTED_PRIVATE_KEY]"`
7. **Generic Bearer Tokens & JWTs**:
   - Regex (Bearer): `r"(?i)\bbearer\s+([a-zA-Z0-9_\-\.]{20,})\b"`
   - Regex (JWT): `r"\b(eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})\b"`
   - Redaction: `"Bearer [REDACTED_AUTH_TOKEN]"` / `"[REDACTED_JWT]"`
8. **Database Connection Strings**:
   - Regex: `r"\b(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|mssql)://(?:[^\s:]+):(?:[^\s@]+)@[^\s]+\b"`
   - Redaction: `"[REDACTED_DATABASE_URL]"`
9. **Slack Webhooks & Bot Tokens**:
   - Regex: `r"\b(xox[baprs]-[0-9a-zA-Z-]{10,})\b|https://hooks\.slack\.com/services/T[0-9A-Z]+/B[0-9A-Z]+/[0-9a-zA-Z]+"`
   - Redaction: `"[REDACTED_SLACK_CREDENTIAL]"`
10. **Discord Bot Tokens & Webhooks**:
    - Regex: `r"https://discord(?:app)?\.com/api/webhooks/[0-9]+/[a-zA-Z0-9_-]+|\b[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27,}\b"`
    - Redaction: `"[REDACTED_DISCORD_TOKEN]"`
11. **Telegram Bot Tokens**:
    - Regex: `r"\b([0-9]{9,10}:[a-zA-Z0-9_-]{35})\b"`
    - Redaction: `"[REDACTED_TELEGRAM_TOKEN]"`
12. **Azure Storage Keys & Shared Access Signatures**:
    - Regex: `r"(?i)AccountKey=[a-zA-Z0-9+/=]{88}|(?:SharedAccessSignature|sig)=[a-zA-Z0-9%]{40,}"`
    - Redaction: `"[REDACTED_AZURE_KEY]"`
13. **Stripe Live Secret Keys**:
    - Regex: `r"\b(sk_live_[0-9a-zA-Z]{24,})\b"`
    - Redaction: `"[REDACTED_STRIPE_KEY]"`
14. **High-Entropy Generic Secrets & Passwords**:
    - Regex: `r"(?i)(?:api_key|apikey|secret|password|access_token|client_secret)\s*[:=]\s*['\"]([^'\"]{8,})['\"]"`
    - Shannon Entropy Filter: for any candidate token > 20 chars with Shannon entropy $> 4.5$.
    - Redaction: `credential='[REDACTED]'`

#### Destructive Command Patterns
```python
DESTRUCTIVE_COMMAND_PATTERNS = [
    (re.compile(r"\brm\s+-rf\s+[/\\*~.]", re.IGNORECASE), "Recursive root/current directory deletion"),
    (re.compile(r"\bdel\s+/[fF]\s+/[sS]\s+/[qQ]", re.IGNORECASE), "Windows recursive silent deletion"),
    (re.compile(r"\brmdir\s+/[sS]\s+/[qQ]", re.IGNORECASE), "Windows silent directory removal"),
    (re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE), "Disk formatting"),
    (re.compile(r"\bformat-volume\b", re.IGNORECASE), "PowerShell disk formatting"),
    (re.compile(r"\bdiskpart\b", re.IGNORECASE), "Disk partition utility"),
    (re.compile(r"\bmkfs(?:\.[a-z0-9]+)?\b", re.IGNORECASE), "Filesystem format"),
    (re.compile(r"\bdd\s+if=", re.IGNORECASE), "Direct block storage overwrite"),
    (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", re.IGNORECASE), "Fork bomb"),
    (re.compile(r"\breg\s+(?:add|delete|import|copy|save|restore)\b", re.IGNORECASE), "Windows Registry modification"),
    (re.compile(r"\bregedit(?:\.exe)?(?:\s+/[sS])?", re.IGNORECASE), "Silent registry editor invocation"),
    (re.compile(r"\bshutdown\s+/[sSrR]", re.IGNORECASE), "System shutdown/reboot"),
]
```

#### Prompt Injection Threat Signatures
```python
PROMPT_INJECTION_PATTERNS = [
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
```

#### Config & Protected Files Guard
```python
PROTECTED_CONFIG_PATTERNS = [
    re.compile(r"(\.env|config\.json|credentials\.json|service_account.*\.json)", re.IGNORECASE),
    re.compile(r"(\.antigravity/rules\.md|\.agent/rules/rules\.md)", re.IGNORECASE),
    re.compile(r"(src/layouts/jarvis-layout\.tsx|src/components/)", re.IGNORECASE),
    re.compile(r"(package\.json|tsconfig.*\.json|vite\.config\.ts|\.eslintrc.*|components\.json)", re.IGNORECASE),
    re.compile(r"(id_rsa|id_ed25519|\.ssh/authorized_keys)", re.IGNORECASE),
    re.compile(r"(/etc/passwd|/etc/shadow|system32|win\.ini)", re.IGNORECASE),
]
```

---

### 2. `backend/security/ecc_hooks.py`

#### Interface Contract
```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional

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
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or Path.home() / ".jarvis" / "homunculus" / "observations.jsonl"
        self.shield = AgentShield()

    def pre_tool_use(self, tool_name: str, args: Dict[str, Any], session_id: str = "default") -> PreToolHookResult: ...
    def pre_tool_hook(self, tool_name: str, args: Dict[str, Any], session_id: str = "default") -> PreToolHookResult: ...
    
    def post_tool_use(self, tool_name: str, args: Dict[str, Any], result: Any, status: str = "success", duration_ms: float = 0.0, session_id: str = "default") -> PostToolHookResult: ...
    def post_tool_hook(self, tool_name: str, args: Dict[str, Any], result: Any, status: str = "success", duration_ms: float = 0.0, session_id: str = "default") -> PostToolHookResult: ...
    
    def format_observation(self, tool_name: str, args: Dict[str, Any], status: Any, duration_ms: float = 0.0, session_id: str = "default", result: Any = None) -> Dict[str, Any]: ...
```

#### JSONL Log Entry Schema (`~/.jarvis/homunculus/observations.jsonl`)
```json
{
  "timestamp": 1731234567.891,
  "session_id": "default",
  "tool_name": "read_file",
  "args": {
    "path": "PROJECT.md"
  },
  "status": "success",
  "duration_ms": 14.2,
  "result_summary": "# Project: Unified J.A.R.V.I.S. Desktop System..."
}
```

---

### 3. `backend/memory/instinct_engine.py`

#### Interface Contract
```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

@dataclass
class Instinct:
    id: str
    trigger: str
    action: str
    confidence: float
    domain: str = "general"     # "security", "code", "terminal", "preference"
    source: str = "observation" # "observation", "user_correction", "ecc_rule"
    scope: str = "personal"     # "personal", "global"
    confirmations: int = 1
    contradictions: int = 0
    occurrences: int = 1
    evidence: str = ""
    updated_at: float = field(default_factory=time.time)

class InstinctEngine:
    def __init__(self, instincts_dir: Optional[Path] = None, observations_path: Optional[Path] = None):
        self.instincts_dir = instincts_dir or Path.home() / ".jarvis" / "homunculus" / "instincts" / "personal"
        self.observations_path = observations_path or Path.home() / ".jarvis" / "homunculus" / "observations.jsonl"

    def score_instinct(self, trigger: str, confirmations: int, contradictions: int) -> float: ...
    def parse_observations(self) -> List[Instinct]: ...
    def record_instinct(self, trigger: str, action: str, domain: str = "general", evidence: str = "", confidence_boost: float = 0.05) -> Dict[str, Any]: ...
    def get_active_instincts(self, min_confidence: float = 0.70) -> List[Dict[str, Any]]: ...
    def render_prompt_injection(self, min_confidence: float = 0.70) -> str: ...
    def prune_instincts(self, min_confidence: float = 0.50) -> int: ...
```

#### Confidence Scoring Formula
$$
\text{Score} = \min\left(1.0, \max\left(0.0, 0.50 + 0.05 \cdot \text{confirmations} - 0.10 \cdot \text{contradictions}\right)\right)
$$
* For $\text{confirmations} = 10, \text{contradictions} = 0$: $\text{Score} = \min(1.0, 0.50 + 0.50) = 1.0 \ge 0.90$.
* For base table lookup with zero confirmations/contradictions:
  * 1-2 occurrences: $0.30$
  * 3-5 occurrences: $0.50$
  * 6-10 occurrences: $0.70$
  * 11+ occurrences: $0.85$

#### Dynamic Prompt Injection Markdown Output Format
```markdown
## Active Behavioral Instincts (Confidence >= 0.70)
The following learned behavioral patterns have been verified and MUST be respected:
- [security] When never format drive: do not execute destructive disk commands (confidence: 1.00)
- [preference] When building typescript: check tsconfig.json before compiling (confidence: 0.85)
- [terminal] When powershell script fails: inspect error stream and verify execution policy (confidence: 0.75)
```

---

## Verification Plan & Concrete Test Commands

To verify that the specifications and future implementations are 100% compliant:

1. **Verify Unit & Tier 1 Feature Tests**:
   ```powershell
   python -m unittest tests/e2e/test_tier1_features.py -k "AgentShield or ECCHook or InstinctEngine"
   ```
2. **Verify Tier 2 Boundary Tests**:
   ```powershell
   python -m unittest tests/e2e/test_tier2_boundaries.py -k "Security"
   ```
3. **Verify Tier 3 Multi-Module Pipeline Tests**:
   ```powershell
   python -m unittest tests/e2e/test_tier3_combinations.py -k "security_scan"
   ```
4. **Verify File Existence & Exported Symbols**:
   - `backend/security/agent_shield.py`: exports `AgentShield`, `SecurityScanResult`, `AuditLogEntry`
   - `backend/security/ecc_hooks.py`: exports `ECCHookDispatcher`, `PreToolHookResult`, `PostToolHookResult`
   - `backend/memory/instinct_engine.py`: exports `InstinctEngine`, `Instinct`
