# Technical Analysis: Governance Rules & Skill Aliasing Remediation (Milestone M1 Iteration 2)

**Author**: `explorer_m1_iter2_2`  
**Parent Agent**: `0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`  
**Date**: 2026-11-10T09:12:30Z  
**Focus Scope**:
1. Governance rules remediation (`.antigravity/rules.md` and `.agent/rules/rules.md`) incorporating `"ZERO UI DRIFT"` and `"DESKTOP APPLICATION ONLY"` with 100% cryptographic SHA-256 parity.
2. Skill aliasing remediation (`backend/skills/desktop_assistant.md` alongside `desktop_control.md`).

---

## 1. Problem Identification & Root Cause Analysis

### 1.1 Governance Rules Failures
In Milestone M1 Iteration 1, the test suite `python tests/e2e/runner.py --tier 1` failed on two governance assertions in `tests/e2e/test_tier1_features.py`:

```python
# test_f04_03_zero_ui_drift_rule_declared (line 141-144)
def test_f04_03_zero_ui_drift_rule_declared(self):
    rules_path = PROJECT_ROOT / ".antigravity" / "rules.md"
    content = rules_path.read_text(encoding="utf-8")
    self.assertIn("ZERO UI DRIFT", content, "Zero UI drift rule must be declared")

# test_f04_04_desktop_application_scope_rule (line 146-149)
def test_f04_04_desktop_application_scope_rule(self):
    rules_path = PROJECT_ROOT / ".antigravity" / "rules.md"
    content = rules_path.read_text(encoding="utf-8")
    self.assertIn("DESKTOP APPLICATION ONLY", content, "Desktop scope rule must be declared")
```

#### Root Cause:
1. **Title Case vs Upper Case**: In `.antigravity/rules.md` line 5, the rule was written as `1. **Zero UI Drift & Source of Truth**:`. The test asserts exact string `"ZERO UI DRIFT"`.
2. **Missing Scope Clause**: The exact string `"DESKTOP APPLICATION ONLY"` was not present anywhere in `.antigravity/rules.md` or `.agent/rules/rules.md`.
3. **Parity Constraint**: `tests/test_m1_adversarial.py:155-179` (`test_governance_rules_exact_character_parity`) and `scripts/verify-m1.ps1:49-62` require `.antigravity/rules.md` and `.agent/rules/rules.md` to be byte-for-byte identical with matching SHA-256 hashes. Both files currently use UNIX line feeds (`LF` / `\n`) and must not introduce mixed line endings.

### 1.2 Desktop Skill Aliasing
In `tests/e2e/test_tier1_features.py`:
```python
# test_f05_04_desktop_skill_definition (line 176-180)
def test_f05_04_desktop_skill_definition(self):
    skill_file = PROJECT_ROOT / "backend" / "skills" / "desktop_assistant.md"
    legacy_skill = PROJECT_ROOT / "skills"
    self.assertTrue(skill_file.exists() or legacy_skill.exists(), "Desktop skill definition must exist")
```

#### Root Cause:
- `ORIGINAL_REQUEST.md:24` requested `desktop_control.md`. The worker created `backend/skills/desktop_control.md`.
- `tests/test_m1_adversarial.py:44` verifies `backend/skills/desktop_control.md`.
- However, `test_tier1_features.py:177` checks `backend/skills/desktop_assistant.md`. In Iteration 1, this test passed only because of the fallback condition `legacy_skill.exists()`.
- To establish true native compliance independent of the legacy `skills/` folder, `backend/skills/desktop_assistant.md` must be created alongside `desktop_control.md`.

---

## 2. Technical Fix Specifications

### 2.1 Governance Rules (`.antigravity/rules.md` and `.agent/rules/rules.md`)

#### Required Content Structure:
1. Add an explicit application scope section right under the document title:
```markdown
## APPLICATION SCOPE & GOVERNANCE: DESKTOP APPLICATION ONLY

J.A.R.V.I.S. is strictly a unified DESKTOP APPLICATION ONLY. All backend assimilation, automation services, camera/mic sensory pipelines, and UI features are exclusively engineered for the local Windows desktop environment. No mobile or web application conversions are permitted.
```

2. Update Law 1 Section 1 to:
```markdown
## LAW 1: PURE J.A.R.V.I.S. HOLOGRAPHIC SPHERE UI & STRICT IMMUTABILITY

1. **ZERO UI DRIFT & Source of Truth (DESKTOP APPLICATION ONLY)**:
   The existing React 19 / TypeScript / Electron frontend restored from `https://github.com/AishikGamer71/J.A.R.V.I.S-Electron-App.git` is the absolute visual source of truth. J.A.R.V.I.S. operates strictly as a DESKTOP APPLICATION ONLY. Under no circumstances may an agent delete, rename, move, restyle, or alter existing layout grids, Tailwind/CSS classes, SVGs, buttons, or typography outside of authorized visualizer tuning.
```

3. Retain all remaining text verbatim to preserve existing test contracts:
   - `"Ctrl+Alt+Backspace"` (Emergency kill switch)
   - `"windows_mcp_bridge.py"`
   - `"Single-Producer Multi-Consumer"`
   - `"14 secret patterns"`
   - `"JARVIS_LIGHTING_CONFIG"`
   - `"smoothing = 1 - Math.exp(-10 * dt)"`
   - `"electron.exe"` / `"JARVIS"`
   - `"observations.jsonl"`

4. **Line-Ending and Hash Synchronization**:
   - Write `.antigravity/rules.md` with newline set explicitly to `\n` (UNIX LF).
   - Copy `.antigravity/rules.md` directly to `.agent/rules/rules.md` (or write identical bytes).
   - Verify: `hashlib.sha256(open('.antigravity/rules.md','rb').read()).hexdigest() == hashlib.sha256(open('.agent/rules/rules.md','rb').read()).hexdigest()`.

### 2.2 Skill Definition (`backend/skills/desktop_assistant.md`)

Create `backend/skills/desktop_assistant.md` with:
- YAML Frontmatter:
  ```yaml
  ---
  name: desktop_assistant
  description: Desktop assistant skill for native Windows automation, GUI control, application management, and OSWorld tasks.
  alias_of: desktop_control
  trigger: desktop assistant, control desktop, click button, open window, type into app, automate GUI, native app, manage window
  tools:
    - windows_mcp_snapshot
    - windows_mcp_click
    - windows_mcp_type
    - windows_mcp_app
    - windows_mcp_shortcut
    - agent_s3_visual_task
  ---
  ```
- Detailed Markdown sections matching `desktop_control.md`:
  - Purpose & Overview
  - Tool Routing Hierarchy (Stage 1 Native COM UIAutomation <10ms; Stage 2 Visual Grounding Escalation via OmniParser V2 + Agent-S3)
  - Safety & Deadlock Guardrails (HWND deadlocks, termination validation, emergency abort hotkey `Ctrl+Alt+Backspace`)

---

## 3. Worker Action Plan (Step-by-Step)

The Worker should perform the following sequential steps:

1. **Update `.antigravity/rules.md`**:
   - Replace title and Law 1 section with the updated text incorporating `"ZERO UI DRIFT"` and `"DESKTOP APPLICATION ONLY"`.
   - Ensure the file is saved with LF line endings.

2. **Synchronize `.agent/rules/rules.md`**:
   - Copy `.antigravity/rules.md` to `.agent/rules/rules.md`.
   - Confirm byte-for-byte identity and SHA-256 match.

3. **Create `backend/skills/desktop_assistant.md`**:
   - Write the complete skill profile into `backend/skills/desktop_assistant.md`.
   - Keep `backend/skills/desktop_control.md` intact.

4. **Execute Verification**:
   - Run: `python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone1Features.test_f04_03_zero_ui_drift_rule_declared`
   - Run: `python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone1Features.test_f04_04_desktop_application_scope_rule`
   - Run: `python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone1Features.test_f05_04_desktop_skill_definition`
   - Run: `python tests/test_m1_adversarial.py`
   - Run: `powershell -ExecutionPolicy Bypass -File scripts/verify-m1.ps1`
