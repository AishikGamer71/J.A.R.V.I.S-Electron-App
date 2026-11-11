# Gate Status

## Gate — Iteration 1
| Agent | Role | Verdict | Source |
|-------|------|---------|--------|
| worker_m2_1 | teamwork_worker | DONE (build passed, 47/47 tests passed) | handoff.md |
| reviewer_m2_1 | teamwork_reviewer | REQUEST_CHANGES | handoff.md |
| reviewer_m2_2 | teamwork_reviewer | APPROVE | handoff.md |
| challenger_m2_1 | teamwork_challenger | REJECT | handoff.md |
| challenger_m2_2 | teamwork_challenger | APPROVE | handoff.md |
| auditor_m2_1 | teamwork_auditor | CLEAN | handoff.md |

Gate Result: **FAIL** (reviewer_m2_1 REQUEST_CHANGES, challenger_m2_1 REJECT)

### Summary of Deficiencies for Iteration 2
1. **Remove `isLegacyTestFixture`**: Remove lines 185–190 in `src/components/dashboard/holographic-core/state-machine.ts` so `SPEAKING (80) > ACTIVE_TOOL (70)` is strictly invariant without test bypasses. In `empirical-lifecycle.test.ts`, update any outdated test assertions expecting ACTIVE_TOOL > SPEAKING to reflect the canonical M2 priority hierarchy.
2. **Wire State Arbitration & Dwell/Timeout into `holographic-core-scene.tsx`**:
   - Instantiate `VisualizerStateArbitrator` (or wire expiration logic) inside `HolographicCoreScene`.
   - Prevent `realtimeBusState.current` from staying stuck permanently in non-idle states (e.g. `ALERT` or tools) upon CustomEvents or hotkeys. Reset to `null`/IDLE after `ALERT_DWELL_MS` (4000ms) or `TOOL_DWELL_MS` (2000ms).
   - Ensure voice state (`jarvisRealtimeRef.voiceState === 'SPEAKING'`) is never shadowed by stale `realtimeBusState.current`.
3. **Respect `TOOL_DWELL_MS` on `tool.result`**:
   - In `src/lib/gateway-client.ts`, do NOT immediately dispatch `jarvis-state: THINKING` on `tool.result` with 0ms delay; wait `TOOL_DWELL_MS` (2000ms) before returning to `THINKING` so users can see the completed tool morph.
4. **Harmonize Dwell Constants**:
   - In `src/pages/dashboard.tsx` line 418, replace hardcoded `3000` with `TOOL_DWELL_MS` (2000ms) from `state-machine.ts`.
5. **Tighten Tool Classification Regexes**:
   - Disambiguate word boundaries in `classifyToolState` so generic terms like `credit_card_charge` or `adb_device` don't collide with `CODING` or `MEMORY_SYNC`.
