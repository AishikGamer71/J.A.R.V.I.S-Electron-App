# Milestone M3 Iteration 2 Review & Adversarial Challenge Report

- **Reviewer**: `reviewer_m3_iter2_2` (Roles: `reviewer`, `critic`)
- **Target**: Milestone M3 Iteration 2 (`backend/engine/model_router.py` & `backend/hardware/power_guardian.py`)
- **Parent Conversation ID**: `0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`
- **Working Directory**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m3_iter2_2\`
- **Date**: 2026-11-10T12:55:00Z
- **Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 `backend/engine/model_router.py`
1. **`TraceDrivenPolicy.get_best_engine_for_bucket` filtering (`lines 417-452`)**:
   ```python
   def get_best_engine_for_bucket(
       self, bucket: str, allowed_engines: Optional[List[str]] = None
   ) -> Optional[Tuple[str, str, float]]:
       """Returns (engine, model, avg_reward) if trace count >= 3, optionally filtered by allowed_engines."""
       with self._lock, sqlite3.connect(self.db_path) as conn:
           cur = conn.cursor()
           if allowed_engines:
               placeholders = ",".join("?" for _ in allowed_engines)
               query = f"""
                   SELECT engine, model, AVG(reward) as avg_reward, COUNT(*) as cnt
                   FROM model_traces
                   WHERE bucket = ? AND success = 1 AND engine IN ({placeholders})
                   GROUP BY engine, model
                   HAVING cnt >= 3
                   ORDER BY avg_reward DESC
                   LIMIT 1
               """
               cur.execute(query, [bucket] + list(allowed_engines))
   ```
   Direct observation: Parameterized SQL interpolation binds `allowed_engines` securely. Parameter bindings are safely separated from query structure.

2. **`route_query` power_mode constraint (`lines 487-509`)**:
   ```python
   decision = self.heuristic.route(query)
   is_power_saver = (self.heuristic.power_mode == "power_saver")

   # In power_saver mode, enforce hard constraint: only local engines permitted.
   allowed = ["ollama", "fallback"] if is_power_saver else None
   best_trace = self.traces.get_best_engine_for_bucket(decision.bucket, allowed_engines=allowed)

   if best_trace:
       best_engine, best_model, avg_reward = best_trace
       if is_power_saver and best_engine == "cloud":
           decision.reason += " (Trace cloud override suppressed by power_saver mode)"
       else:
           decision.engine = best_engine
           decision.model = best_model
           decision.reason += f" (Overridden by trace reward {avg_reward:.2f})"
   elif is_power_saver:
       decision.reason += " (Trace cloud search constrained by power_saver mode)"
   ```
   Direct observation: `power_mode == "power_saver"` enforces local filtering through both query filtering (`allowed_engines=["ollama", "fallback"]`) and an explicit defensive fallback clamp.

3. **`OllamaEngine` TTL caching & background daemon heartbeat (`lines 134-190`)**:
   ```python
   self.cache_ttl_sec = cache_ttl_sec  # default 10.0s
   self._cached_available: Optional[bool] = None
   self._last_check_time: float = 0.0
   self._lock = threading.Lock()
   self._checking: bool = False
   self._trigger_background_probe()
   ```
   Direct observation:
   - Initial probe is triggered as a background daemon thread (`OllamaHealthProbe`) upon initialization.
   - `is_available()` returns cached state in < 0.01ms if `(now - self._last_check_time) < self.cache_ttl_sec`.
   - Stale cache refreshes trigger a non-blocking background probe thread while immediately returning the current known status.
   - Measured cold streaming Time To First Token (TTFT) when Ollama is offline: **1.70 ms** (previously stalled for ~500 ms).

### 1.2 `backend/hardware/power_guardian.py`
1. **`determine_power_profile()` battery 20.0% boundary (`lines 166-181`)**:
   ```python
   def determine_power_profile(self, ac_online: bool, battery_pct: float) -> str:
       if ac_online:
           return "performance"
       if battery_pct <= 20.0:
           return "power_saver"
       if battery_pct <= 40:
           return "conservative"
       return "performance"
   ```
   Direct observation: Strict inequality `< 20` was remediated to `<=` comparison `battery_pct <= 20.0`.
   This matches:
   - `PowerConservationTier.POWER_SAVER` (tier 2: 11-20%)
   - `PowerState.BATTERY_LOW` (`battery_pct <= 20.0`)
   - Low battery transition alert (`new_status.battery_percent <= 20.0`)

2. **Desktop host detection & false unplug alarm immunity (`lines 252-270, 303-317, 391-394`)**:
   ```python
   # Win32 detection:
   battery_flag = sps.BatteryFlag & 0xFF
   has_battery = not bool(battery_flag & 0x80)
   ...
   if not has_battery:
       state = PowerState.AC_DESKTOP
       tier = PowerConservationTier.UNRESTRICTED

   # psutil detection:
   batt = psutil.sensors_battery()
   if batt is None:
       return PowerStatus(
           ac_line_status=1,
           ac_online=True,
           has_battery=False,
           battery_percent=100.0,
           power_state=PowerState.AC_DESKTOP,
           conservation_tier=PowerConservationTier.UNRESTRICTED,
           ...
       )

   # Transition check guard:
   def _check_transitions(self, new_status: PowerStatus):
       if not new_status.has_battery:
           return
   ```
   Direct observation: If `has_battery` is False (AC desktop host), `_check_transitions()` returns immediately on line 392, ensuring 0 false unplug alarms and 0 battery warnings are emitted. Live execution on the host machine confirms `power_state: ac_desktop`, `has_battery: False`, `conservation_tier: 0`, and 0 alarms emitted.

### 1.3 Test & Verification Suite Execution Results
- `python tests/e2e/runner.py --milestone M3`:
  ```
  Total Tests Run : 40
  Passed           : 40
  Skipped (Pending): 0
  Failed           : 0
  Errors           : 0
  Execution completed in 1.481s
  ```
- `python -m unittest tests.test_adversarial_m3`:
  ```
  Ran 37 tests in 5.227s
  OK
  ```
- `python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features`:
  ```
  Ran 40 tests in 1.392s
  OK
  ```
- `python -m unittest tests.e2e.test_tier2_boundaries.TestTier2Milestone3Boundaries`:
  ```
  Ran 10 tests in 0.000s
  OK
  ```
- `python -m unittest tests.e2e.test_tier3_combinations`:
  ```
  Ran 8 tests in 0.000s
  OK
  ```
- `python tests/benchmark_m3_forensics.py`:
  - Barge-in Cold-Start Latency: `0.0113 ms` (strictly <= 32.0 ms bound)
  - Barge-in 50-Iteration Mean: `0.0011 ms`
  - All 50 iterations <= 32ms: `True`
- UI immutability check (`git status --porcelain src/`):
  ```
   M src/components/dashboard/sphere.tsx
  ?? src/components/widgets/arc-reactor.tsx
  ```
  Zero UI drift outside authorized M1 sphere components.

---

## 2. Logic Chain

1. **Routing Tier & Power Mode Safety**:
   - Observations 1.1.1 and 1.1.2 show that `route_query()` checks `is_power_saver = (self.heuristic.power_mode == "power_saver")`.
   - When active, `allowed_engines = ["ollama", "fallback"]` is supplied to `TraceDrivenPolicy.get_best_engine_for_bucket`.
   - The SQL query filters results with `WHERE engine IN (?, ?)`.
   - If historical traces favored `cloud` with high reward (e.g. `gemini-2.5-pro` with reward 0.98), those rows are excluded at the SQL level.
   - If an edge case returned a cloud engine trace, the explicit check `if is_power_saver and best_engine == "cloud":` suppresses it and logs the reason.
   - Empirical test confirmed: injecting 10 cloud traces with high reward in bucket `"long"` under `power_saver` mode routes to `ollama` (`qwen2.5:1.5b`, `tier='local_fast'`, `quantized_or_cpu=True`).

2. **OllamaEngine Non-Blocking Streaming Path**:
   - Observation 1.1.3 shows `is_available()` avoids blocking network I/O.
   - `_cached_available` provides an immediate result within `10.0s` TTL.
   - If stale or uninitialized, a background thread is spawned (`_trigger_background_probe()`) while returning the latest cached state or False immediately.
   - Empirical test confirmed: 100 consecutive calls to `is_available()` with a non-existent port had a mean latency of `0.0010 ms` (max `0.0059 ms`).
   - Cold streaming TTFT to fallback engine was measured at `1.70 ms`, cleanly eliminating the prior 500ms synchronous timeout freeze.

3. **Power Profile Boundary Harmonization**:
   - Observation 1.2.1 shows that at exactly `battery_pct = 20.0%`, `determine_power_profile(False, 20.0)` evaluates `battery_pct <= 20.0` as `True`, returning `"power_saver"`.
   - At `battery_pct = 20.001%`, it returns `"conservative"`.
   - At `battery_pct = 40.0%`, it returns `"conservative"`, and at `40.001%` returns `"performance"`.
   - This aligns with `PowerConservationTier.POWER_SAVER` (tier 2) and `PowerState.BATTERY_LOW`.

4. **Desktop Host Detection & False Alarm Suppression**:
   - Observation 1.2.2 shows both Win32 kernel query and psutil fallback correctly recognize desktop hardware when `sps.BatteryFlag & 0x80` or `sensors_battery() is None`.
   - In either case, `has_battery` is set to `False` and `power_state` is set to `PowerState.AC_DESKTOP`.
   - Line 392 of `power_guardian.py` guards `_check_transitions` with `if not new_status.has_battery: return`.
   - Therefore, desktop systems running on AC without batteries never trigger unplug events or low battery alerts.

5. **Integrity and Anti-Cheating Assessment**:
   - Inspected source code for hardcoded test fixtures, dummy flags, fake delays, or mock bypasses in production code. None found.
   - Traces are stored in genuine SQLite databases with real schema and indices.
   - System power status polls genuine Win32 `kernel32.GetSystemPowerStatus` and `psutil`.
   - All tests pass genuinely under real execution environments.

---

## 3. Caveats & Adversarial Findings

1. **Minor Finding — `TraceDrivenPolicy` with `:memory:` Database**:
   - In `backend/engine/model_router.py:363`, `TraceDrivenPolicy` supports passing a custom `db_path`.
   - However, because methods use `sqlite3.connect(self.db_path)` per call, passing `Path(':memory:')` creates a fresh, empty in-memory database on every call, causing `record_trace` to fail with `no such table: model_traces`.
   - *Impact*: Low. Production uses `~/.jarvis/traces.db` on disk, and unit tests use `NamedTemporaryFile`. If in-memory isolation is desired for tests in the future, `TraceDrivenPolicy` should maintain a persistent connection for `:memory:`, similar to `HybridMemory`.

2. **Minor Finding — Empty `allowed_engines` List Evaluation**:
   - In `TraceDrivenPolicy.get_best_engine_for_bucket`, `if allowed_engines:` evaluates to `False` when `allowed_engines == []`.
   - If an external caller passes an empty list, it defaults to the unfiltered query instead of returning `None`.
   - *Impact*: Low. Internal callers pass `None` or `["ollama", "fallback"]`.

---

## 4. Conclusion

The remediated implementations in `backend/engine/model_router.py` and `backend/hardware/power_guardian.py` are robust, high-performance, and mathematically consistent with all project specifications.

- `allowed_engines` filtering in `TraceDrivenPolicy` operates correctly via SQL parameterization.
- `route_query()` strictly enforces `power_saver` mode, suppressing cloud overrides and ensuring local execution.
- `OllamaEngine` TTL caching reduces availability checks to sub-microsecond latency, eliminating streaming path delays (TTFT = 1.70ms).
- `determine_power_profile()` boundary at 20.0% battery is consistent with `PowerConservationTier.POWER_SAVER`.
- AC desktop host detection is robust with zero false alarms.
- All verification test suites (40/40 E2E, 37/37 Adversarial, 10/10 Boundaries, 8/8 Combinations) pass cleanly with zero UI drift.

**Verdict: APPROVE**.

---

## 5. Verification Method

To independently verify these findings, run:

1. **Milestone M3 Unified E2E Test Suite**:
   ```powershell
   python tests/e2e/runner.py --milestone M3
   ```
   *Expected*: Total Tests Run: 40, Passed: 40, Failed: 0, Errors: 0.

2. **Milestone M3 Adversarial Stress Test Suite**:
   ```powershell
   python -m unittest tests.test_adversarial_m3
   ```
   *Expected*: Ran 37 tests, OK.

3. **UI Preservation Audit**:
   ```powershell
   git status --porcelain src/
   ```
   *Expected*: Only `sphere.tsx` and `arc-reactor.tsx` modified/untracked.

4. **Forensic Barge-in & Audio Benchmark**:
   ```powershell
   python tests/benchmark_m3_forensics.py
   ```
   *Expected*: Cold-start barge-in <= 32ms bound.

### Invalidation Conditions
- Any cloud model selection when `power_mode == "power_saver"`.
- `OllamaEngine.is_available()` taking > 25ms.
- `PowerGuardian.determine_power_profile(False, 20.0)` returning anything other than `"power_saver"`.
- Any false unplug alarm triggered on an AC desktop machine.
- Modifications to any files in `src/` outside the M1 sphere.
