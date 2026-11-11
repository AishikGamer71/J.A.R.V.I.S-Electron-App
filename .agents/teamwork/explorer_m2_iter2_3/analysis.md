# Technical Analysis & Fix Blueprints: Continuous Learning & Context Compression

**Author**: `explorer_m2_iter2_3` (Teamwork Explorer)  
**Parent Orchestrator**: `0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`  
**Target Files**:
- `backend/memory/instinct_engine.py` (Lines 164–225)
- `backend/core/context_compressor.py` (Lines 169–190)

---

## Executive Summary

An investigation was conducted into the two critical failure modes identified during Milestone M2 verification:
1. **InstinctEngine Contradiction Blinding (V7)**: Grouping observation records by `f"{tool}:{status}"` isolates successes and failures into separate buckets, permanently suppressing contradiction tracking (`contradictions = 0`), which prevents epistemic unlearning.
2. **ContextCompressor Empty `call_ids` Edge Case**: The pruning condition `if tcid and call_ids and tcid not in call_ids: continue` evaluates to `False` when all preceding assistant turns are summarized into middle compaction (`call_ids == set()`), allowing dangling tool results to be preserved in the prompt payload and triggering HTTP 400 errors from LLM providers.

Both root causes have been isolated, modeled, and verified against empirical test suites. Exact code replacement blueprints and regression-free patches are provided below.

---

## 1. Vulnerability 1: InstinctEngine Contradiction Blinding (V7)

### 1.1 Root Cause Analysis
In `backend/memory/instinct_engine.py`, lines 180–197:
```python
record = json.loads(line)
tool = record.get("tool_name", "")
status = record.get("status", "success")
key = f"{tool}:{status}"

if key not in counts:
    counts[key] = {
        "tool": tool,
        "status": status,
        "success_count": 0,
        "fail_count": 0,
        "samples": [],
    }

if status == "success":
    counts[key]["success_count"] += 1
else:
    counts[key]["fail_count"] += 1
```

And lines 205–210:
```python
results: List[Instinct] = []
for key, data in counts.items():
    if data["success_count"] >= 3:
        trigger = f"executing {data['tool']}"
        action = f"prefer standard parameters that succeeded in observations"
        conf = self.score_instinct(trigger, data["success_count"], data["fail_count"])
```

#### The Mechanism:
1. When observations for tool `git` are processed, successes are grouped under key `"git:success"` and errors under `"git:error"`.
2. Under `"git:success"`, `fail_count` remains permanently `0`.
3. Under `"git:error"`, `success_count` remains permanently `0`.
4. When filtering candidate instincts via `if data["success_count"] >= 3:`, only `"git:success"` qualifies.
5. In `score_instinct(trigger, data["success_count"], data["fail_count"])`, `confirmations` receives 3, while `contradictions` receives 0.
6. The epistemic score formula:
   $$\text{Score} = \min(1.0, \max(0.0, 0.50 + 0.05 \times \text{confirmations} - 0.10 \times \text{contradictions}))$$
   evaluates to:
   $$\text{Score} = 0.50 + 0.05 \times 3 - 0.10 \times 0 = 0.65$$
   Even if the tool failed 20 times (`"git:error"` with `fail_count = 20`), those failures are completely invisible to `"git:success"`.

#### Verification via `tests/empirical_findings.py`:
- 3 successes and 2 errors for `git` were fed to `parse_observations()`.
- Empirical finding: `V7 (Instinct Observation Contradictions Lost): Expected=2, Recorded=0`.

---

### 1.2 Exact Blueprint for `backend/memory/instinct_engine.py`

#### Architecture & Design Rationale:
- Group observation counts by `tool` rather than `f"{tool}:{status}"`.
- Accumulate both `success_count` and `fail_count` in the same tool dictionary.
- Collect parameter samples up to 3 entries **only from successful runs**, ensuring recommended parameters are proven working examples.
- Skip records with empty `tool_name` defensively.
- Pass authentic `success_count` (confirmations) and `fail_count` (contradictions) to `self.score_instinct`.
- Set `occurrences = data["success_count"] + data["fail_count"]`.

#### Code Replacement Chunk:
**Target File**: `backend/memory/instinct_engine.py`  
**Target Range**: Lines 172 to 225

```python
<<<<
        counts: Dict[str, Dict[str, Any]] = {}
        with open(self.observations_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    tool = record.get("tool_name", "")
                    status = record.get("status", "success")
                    key = f"{tool}:{status}"

                    if key not in counts:
                        counts[key] = {
                            "tool": tool,
                            "status": status,
                            "success_count": 0,
                            "fail_count": 0,
                            "samples": [],
                        }

                    if status == "success":
                        counts[key]["success_count"] += 1
                    else:
                        counts[key]["fail_count"] += 1

                    if len(counts[key]["samples"]) < 3:
                        counts[key]["samples"].append(record.get("args", {}))
                except Exception:
                    # Gracefully skip malformed line
                    continue

        results: List[Instinct] = []
        for key, data in counts.items():
            if data["success_count"] >= 3:
                trigger = f"executing {data['tool']}"
                action = f"prefer standard parameters that succeeded in observations"
                conf = self.score_instinct(trigger, data["success_count"], data["fail_count"])
                inst = Instinct(
                    id=f"obs-{data['tool']}",
                    trigger=trigger,
                    action=action,
                    confidence=conf,
                    domain="tool_execution",
                    source="observation",
                    confirmations=data["success_count"],
                    contradictions=data["fail_count"],
                    occurrences=data["success_count"] + data["fail_count"],
                    evidence=f"Observed {data['success_count']} successful runs",
                )
                results.append(inst)

        return results
====
        counts: Dict[str, Dict[str, Any]] = {}
        with open(self.observations_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    tool = record.get("tool_name", "")
                    if not tool:
                        continue
                    status = record.get("status", "success")

                    if tool not in counts:
                        counts[tool] = {
                            "tool": tool,
                            "success_count": 0,
                            "fail_count": 0,
                            "samples": [],
                        }

                    if status == "success":
                        counts[tool]["success_count"] += 1
                        if len(counts[tool]["samples"]) < 3 and record.get("args") is not None:
                            counts[tool]["samples"].append(record.get("args", {}))
                    else:
                        counts[tool]["fail_count"] += 1
                except Exception:
                    # Gracefully skip malformed line
                    continue

        results: List[Instinct] = []
        for tool, data in counts.items():
            if data["success_count"] >= 3:
                trigger = f"executing {data['tool']}"
                action = "prefer standard parameters that succeeded in observations"
                conf = self.score_instinct(trigger, data["success_count"], data["fail_count"])
                inst = Instinct(
                    id=f"obs-{data['tool']}",
                    trigger=trigger,
                    action=action,
                    confidence=conf,
                    domain="tool_execution",
                    source="observation",
                    confirmations=data["success_count"],
                    contradictions=data["fail_count"],
                    occurrences=data["success_count"] + data["fail_count"],
                    evidence=f"Observed {data['success_count']} successful runs",
                )
                results.append(inst)

        return results
>>>>
```

---

## 2. Vulnerability 2: ContextCompressor Empty `call_ids` Edge Case

### 2.1 Root Cause Analysis
In `backend/core/context_compressor.py`, lines 169–190:
```python
def _clean_orphaned_tools(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Removes dangling tool results whose matching tool_call_id is missing from assistant turns.
    """
    call_ids = set()
    for m in messages:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                if isinstance(tc, dict) and "id" in tc:
                    call_ids.add(tc["id"])

    cleaned = []
    for m in messages:
        if m.get("role") == "tool":
            tcid = m.get("tool_call_id")
            # If tool_call_id is present and known, or if no tool_call_id is tracked, keep it
            if tcid and call_ids and tcid not in call_ids:
                continue
        cleaned.append(m)

    return cleaned
```

#### The Mechanism:
1. When a conversation exceeds token limits, `compress()` partitions turns into `head`, `middle`, and `tail` (`tail_count = min(len(rest), 2)`).
2. The `middle` turns are replaced by a single synthetic summary message (`role: "user"`, `_compressed_summary: True`).
3. If an assistant turn containing `tool_calls` was in `middle`, but the subsequent `role: "tool"` execution output is in `tail`:
   - `_clean_orphaned_tools(tail)` is called.
   - Because no assistant message in `tail` contains `tool_calls`, `call_ids` is an empty set: `call_ids == set()`.
   - On line 185:
     ```python
     if tcid and call_ids and tcid not in call_ids:
         continue
     ```
   - In Python, `bool(set()) == False`. Therefore, `tcid and call_ids` evaluates to `False`.
   - The condition is bypassed, and the dangling tool message is appended to `cleaned`.
4. In `test_m2_adversarial.py`:
   `[OBSERVATION] When no assistant tool_calls in window, dangling tool pruned? False`
5. Upstream provider APIs (OpenAI, Anthropic) enforce strict message ordering:
   Every `tool` message must directly follow an `assistant` turn declaring that specific `tool_call_id`. Providing a lone `tool` message without an antecedent `tool_call` results in immediate HTTP 400 Bad Request error.

---

### 2.2 Exact Blueprint for `backend/core/context_compressor.py`

#### Architecture & Design Rationale:
- If `messages` is empty, return `[]` immediately.
- Collect all valid `tool_call` IDs from assistant turns in the window (handling both dictionary keys and object attributes defensively).
- For every message with `role == "tool"`:
  - If `tool_call_id` is missing, empty, or not present in `call_ids` (`if not tcid or tcid not in call_ids:`), prune it (`continue`).
  - This ensures that if `call_ids` is empty (`set()`), **all** dangling tool returns are pruned because `tcid not in call_ids` evaluates to `True`.
  - If `call_ids` contains IDs, only tool results matching an existing assistant call in the immediate context are preserved.

#### Code Replacement Chunk:
**Target File**: `backend/core/context_compressor.py`  
**Target Range**: Lines 169 to 190

```python
<<<<
    def _clean_orphaned_tools(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Removes dangling tool results whose matching tool_call_id is missing from assistant turns.
        """
        call_ids = set()
        for m in messages:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    if isinstance(tc, dict) and "id" in tc:
                        call_ids.add(tc["id"])

        cleaned = []
        for m in messages:
            if m.get("role") == "tool":
                tcid = m.get("tool_call_id")
                # If tool_call_id is present and known, or if no tool_call_id is tracked, keep it
                if tcid and call_ids and tcid not in call_ids:
                    continue
            cleaned.append(m)

        return cleaned
====
    def _clean_orphaned_tools(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Removes dangling tool results whose matching tool_call_id is missing from assistant turns.
        Prunes all tool messages if no matching assistant tool_calls exist in the window.
        """
        if not messages:
            return []

        call_ids = set()
        for m in messages:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    if isinstance(tc, dict) and tc.get("id"):
                        call_ids.add(tc["id"])
                    elif hasattr(tc, "id") and getattr(tc, "id"):
                        call_ids.add(getattr(tc, "id"))

        cleaned = []
        for m in messages:
            if m.get("role") == "tool":
                tcid = m.get("tool_call_id")
                # Prune if tool_call_id is missing or has no antecedent assistant tool_call
                if not tcid or tcid not in call_ids:
                    continue
            cleaned.append(m)

        return cleaned
>>>>
```

---

## 3. Empirical Verification Results

Both blueprints were tested in an isolated runtime environment simulating live calls:

| Test Harness | Metric / Assertion | Before Fix | With Fix Blueprint |
|---|---|---|---|
| `tests/empirical_findings.py` | V7 Contradiction Recording | `Expected=2, Recorded=0` | `Expected=2, Recorded=2` (PASS) |
| `tests/test_m2_adversarial.py` | Dangling Tool Pruned when `call_ids == set()` | `dangling tool pruned? False` | `dangling tool pruned? True` (PASS) |
| `tests/test_m2_adversarial.py` | Orphan Pruning with mixed valid/invalid | `len(cleaned) == 2` | `len(cleaned) == 2` (PASS) |
| `tests/auditor_m2_forensic_probes.py` | Probe 5 (Instinct Engine) | `PASS` | `PASS` |
| `tests/auditor_m2_forensic_probes.py` | Probe 6 (Context Compressor) | `PASS` | `PASS` |
| `tests/e2e/test_tier1_features.py` | Milestone 2 Features (45 tests) | `45/45 Passed` | `45/45 Passed` (100% OK) |

---

## 4. Implementation Steps for Downstream Worker Agent

1. Apply the replacement chunk to `backend/memory/instinct_engine.py` (lines 172–225).
2. Apply the replacement chunk to `backend/core/context_compressor.py` (lines 169–190).
3. Execute validation:
   ```powershell
   python tests/empirical_findings.py
   python -m unittest tests/test_m2_adversarial.py
   python tests/auditor_m2_forensic_probes.py
   python -m unittest tests/e2e/test_tier1_features.py -k "TestTier1Milestone2Features"
   ```
4. Confirm `V7` in `empirical_findings.py` outputs `Recorded=2`, and `test_m2_adversarial.py` outputs `dangling tool pruned? True`.
