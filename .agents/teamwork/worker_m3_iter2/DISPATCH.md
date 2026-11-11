## 2026-11-10T12:35:44Z
You are worker_m3_iter2, the implementation worker for Milestone M3 Iteration 2 (Hardware Profiling, Routing, Hybrid RAG & Voice Pipeline Remediation).

Your parent orchestrator conversation ID is: 0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4
Your working directory is: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m3_iter2\

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEP:
Read e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md and e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md before doing anything else.

READ THE EXPLORER BLUEPRINTS:
1. `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m3_iter2_1\handoff.md` and `audio_pipeline_remediation.patch`
2. `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m3_iter2_2\handoff.md` and `hybrid_rag.patch`
3. `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m3_iter2_3\handoff.md`

FILES YOU EXCLUSIVELY OWN AND MUST UPDATE:
1. `backend/voice/audio_pipeline.py`:
   - Eagerly, safely import `sounddevice` at module level:
     ```python
     try:
         import sounddevice as sd
         _sd = sd
     except Exception:
         _sd = None
     ```
   - In `AudioPipeline.__init__`, perform pre-warming:
     ```python
     if _sd is not None:
         try:
             _sd.stop()
         except Exception:
             pass
     ```
   - In `trigger_barge_in()`, use pre-imported `_sd`:
     ```python
     if _sd is not None:
         try:
             _sd.stop()
         except Exception as e:
             logger.debug("sounddevice.stop() caught: %s", e)
     ```
     This eliminates the 167ms DLL loading penalty, achieving cold-start latency < 0.05ms (strictly <= 32ms bound).
   - In `on_speaking()`, explicitly clear `self.tts_stop_event`:
     ```python
     def on_speaking(self) -> None:
         self.state = "speaking"
         self.tts_stop_event.clear()
         self.ws_broadcast("jarvis-voice-state", {"state": "speaking", "interrupted": False})
     ```

2. `backend/memory/hybrid_rag.py`:
   - In `compute_rrf_score`:
     ```python
     def compute_rrf_score(rank: int, k: int = 60) -> float:
         if rank <= 0 or (k + rank) <= 0:
             return 0.0
         return 1.0 / (float(k) + float(rank))
     ```
   - In `HybridMemory.__init__`, coerce `db_path`:
     ```python
     if not db_path:
         self.db_path = DEFAULT_MEMORY_DB_PATH
     elif isinstance(db_path, str):
         self.db_path = Path(db_path)
     else:
         self.db_path = db_path
     ```
   - Implement `_db_connection` context manager guaranteeing explicit `conn.close()` on Windows to avoid WinError 32 file locks.
   - In `SearchResult`, delegate `__getitem__` to tuple indexing and add `__iter__` for sequence unpacking and negative indexing (`res[-1]`).

3. `backend/engine/model_router.py`:
   - Add `allowed_engines` parameter to `TraceDrivenPolicy.get_best_engine_for_bucket(bucket, allowed_engines=None)` filtering SQL `WHERE engine IN (...)`.
   - In `ModelRouter.route_query()`, if `self.heuristic.power_mode == "power_saver"`, pass `allowed_engines=["ollama", "fallback"]` or suppress cloud overrides to enforce power preservation.
   - Upgrade `OllamaEngine` with 10s TTL cache and background daemon heartbeat probe so streaming TTFT is instantaneous (< 15ms) on cold turns when Ollama is offline.

4. `backend/hardware/power_guardian.py`:
   - In `determine_power_profile()`, update boundary to `<= 20.0` for consistency with `PowerConservationTier.POWER_SAVER` and transition alerts.

ZERO UI DRIFT MANDATE:
Do NOT touch or modify any UI files in `src/`. `git status --porcelain src/` must only reflect the authorized M1 sphere files.

VERIFICATION REQUIRED:
Execute:
1. `python tests/e2e/runner.py --milestone M3`
2. `python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features`
3. `python -m unittest tests.e2e.test_tier2_boundaries.TestTier2Milestone3Boundaries`
4. `python -m unittest tests.test_adversarial_m3`
5. `python tests/benchmark_m3_forensics.py`
6. `git status --porcelain src/`

OUTPUT REQUIREMENTS:
Write your full implementation and test verification report to:
`e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m3_iter2\handoff.md`
Follow standard Handoff format: Observation, Logic Chain, Caveats, Conclusion, Verification Commands & Output.
Send a message to your parent orchestrator (0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4) when done.
