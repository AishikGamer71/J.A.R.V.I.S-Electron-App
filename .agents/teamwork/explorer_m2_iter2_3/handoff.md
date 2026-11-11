# Handoff Report: Blueprints for Continuous Learning & Context Compression

**Subagent**: `explorer_m2_iter2_3` (teamwork_explorer)  
**Parent Orchestrator Conversation ID**: `0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`  
**Milestone**: M2 (Continuous Learning & Context Compression Hardening)  
**Type**: Hard Handoff (Investigation & Blueprints Complete)  

---

## 1. Observation

### 1.1 InstinctEngine Contradiction Blinding (V7)
- **Target File**: `backend/memory/instinct_engine.py:182-197, 205-224`
- **Observed Source Code**:
  ```python
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
- **Execution Command**:
  ```powershell
  python tests/empirical_findings.py
  ```
- **Verbatim Output**:
  ```
  V7 (Instinct Observation Contradictions Lost): Expected=2, Recorded=0
  ```
- **Line 206 Condition**:
  `if data["success_count"] >= 3:` only evaluates `True` for `"git:success"`. In `"git:success"`, `fail_count` is permanently `0`. Thus `score_instinct` is called with `confirmations=3, contradictions=0`, yielding `confidence=0.65` instead of `0.45`, ignoring all failure records.

---

### 1.2 ContextCompressor Empty `call_ids` Edge Case
- **Target File**: `backend/core/context_compressor.py:182-187`
- **Observed Source Code**:
  ```python
  for m in messages:
      if m.get("role") == "tool":
          tcid = m.get("tool_call_id")
          # If tool_call_id is present and known, or if no tool_call_id is tracked, keep it
          if tcid and call_ids and tcid not in call_ids:
              continue
      cleaned.append(m)
  ```
- **Execution Command**:
  ```powershell
  python -m unittest tests/test_m2_adversarial.py
  ```
- **Verbatim Output**:
  ```
  [PASS] ContextCompressor stress: 101 msgs compacted into 4 active turns; 98 soft-compacted in state_db
  [OBSERVATION] When no assistant tool_calls in window, dangling tool pruned? False
  ```
- **Observation Detail**: When preceding assistant turns with `tool_calls` are compressed into the middle summary, `call_ids` in `_clean_orphaned_tools(tail)` is `set()`. Because `bool(set()) == False`, `tcid and call_ids` evaluates to `False`. Dangling `role: "tool"` messages without an antecedent `tool_calls` turn are kept, violating OpenAI / Anthropic API schemas and triggering HTTP 400 errors.

---

## 2. Logic Chain

1. **Step 1 (Instinct Aggregation Failure)**:
   - In `backend/memory/instinct_engine.py`, records are bucketed by `f"{tool}:{status}"`.
   - Bucketing by status segregates `"tool:success"` and `"tool:error"` into mutually exclusive entries.
   - When candidate instincts are synthesized (`data["success_count"] >= 3`), only the success bucket is inspected.
   - Therefore, `data["fail_count"]` in that bucket is guaranteed to be 0, blinding `score_instinct` to runtime errors.
   - **Remedy**: Grouping by `tool` accumulates both successes and failures under the same key. `score_instinct` receives real confirmation and contradiction counts, calibrating epistemic confidence according to the verified formula:
     $$\text{Score} = \min(1.0, \max(0.0, 0.50 + 0.05 \times \text{confirmations} - 0.10 \times \text{contradictions}))$$

2. **Step 2 (Context Compaction Orphan Leakage)**:
   - In `backend/core/context_compressor.py`, compaction replaces middle turns with a synthetic summary message.
   - If the caller's tail window retains a tool output while its calling assistant turn was summarized into the middle block, `tail` contains a tool message but no assistant `tool_calls`.
   - The boolean check `if tcid and call_ids and tcid not in call_ids:` requires `call_ids` to be non-empty. When `call_ids` is empty, the pruning check fails to activate.
   - **Remedy**: Changing the check to `if not tcid or tcid not in call_ids: continue` ensures that any tool output lacking a matching assistant tool call in the active window is pruned, regardless of whether `call_ids` is empty.

3. **Step 3 (Safety & Non-Regression)**:
   - Both proposed code replacements were simulated via runtime monkey-patching across all 45 Tier 1 M2 unit tests, all 10 forensic probes in `auditor_m2_forensic_probes.py`, and the adversarial suites.
   - Zero tests failed; all 45 feature contract tests and all 10 forensic probes passed cleanly.

---

## 3. Caveats

1. **Read-Only Constraint**: As an explorer subagent, source code was NOT written to `backend/`. The code changes must be applied by a worker or implementer agent following the blueprints in `analysis.md`.
2. **Other Vulnerabilities in `empirical_findings.py`**:
   - `empirical_findings.py` also tests V1 (Azure Key regex), V2 (Command flag permutations), V3 (Null byte splitting), V4 (System32 subpath write), V5 (Nested secrets in tool calls), and V6 (ECC concurrent file locking).
   - Per the dispatch mission, this blueprint specifically addresses V7 (`InstinctEngine`) and the `ContextCompressor` edge case. The remaining items pertain to `AgentShield` and `ECCHookDispatcher`.

---

## 4. Conclusion

The exact blueprints for remediating both issues are finalized:

### 4.1 `backend/memory/instinct_engine.py` Blueprint
Replace lines 172–224 with:
```python
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
```

### 4.2 `backend/core/context_compressor.py` Blueprint
Replace `_clean_orphaned_tools()` (lines 169–190) with:
```python
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
```

---

## 5. Verification Method

To independently verify the implementation after applying the blueprints:

1. **Verify V7 Contradiction Recording in `empirical_findings.py`**:
   ```powershell
   python tests/empirical_findings.py
   ```
   *Expected*: `V7 (Instinct Observation Contradictions Lost): Expected=2, Recorded=2`.

2. **Verify Dangling Tool Pruning in Adversarial Suite**:
   ```powershell
   python -m unittest tests/test_m2_adversarial.py
   ```
   *Expected*: `[OBSERVATION] When no assistant tool_calls in window, dangling tool pruned? True`.

3. **Verify Zero Regressions across Forensic Probes & Tier 1 Feature Contracts**:
   ```powershell
   python tests/auditor_m2_forensic_probes.py
   python -m unittest tests/e2e/test_tier1_features.py -k "TestTier1Milestone2Features"
   ```
   *Expected*: `OVERALL VERDICT: CLEAN` and `Ran 45 tests ... OK`.

### Invalidation Conditions:
- `v7[1] == 0` when running `tests/empirical_findings.py`.
- Any dangling `role: "tool"` message retained when `call_ids` is empty.
- Any regression in `tests/auditor_m2_forensic_probes.py` or `tests/e2e/test_tier1_features.py`.
