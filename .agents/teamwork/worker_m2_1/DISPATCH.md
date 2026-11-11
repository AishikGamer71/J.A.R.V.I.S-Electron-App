## 2026-11-11T10:42:51Z

You are the Worker for Milestone 2: Visualizer State & Event Wiring.
Working directory: e:\Projects\J.A.R.V.I.S Electron App
Your state folder: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m2_1\

## MANDATORY INTEGRITY WARNING (VERBATIM)
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Context & Files to Read
- Original Request: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md
- Master Project Spec: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\orchestrator_1\PROJECT.md
- Milestone 2 Scope: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\sub_orch_m2_1\SCOPE.md
- Explorer 1 Report: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_1\report.md
- Explorer 2 Report: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_2\report.md
- Explorer 3 Report: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_3\report.md

## Implementation Objective
Connect all 11 holographic core states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`) to the Electron application's runtime events, priority arbitration, keyboard hotkeys, and live audio levels.

## Files You Own Exclusively
- `src/services/jarvis-voice-ai.ts`
- `src/lib/gateway-client.ts`
- `src/services/jarvisBridge.ts` (if needed)
- `src/components/dashboard/holographic-core/state-machine.ts`
- `src/components/dashboard/holographic-core/constants.ts` (if needed)
- `src/components/dashboard/sphere.tsx`
- `src/pages/dashboard.tsx`
- `src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts`

## Detailed Implementation Tasks
1. **Fix Wake Word Event in `src/services/jarvis-voice-ai.ts`**:
   - In lines 95–98, fix `wake_word_detected` event handler so it dispatches `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'LISTENING' }))` instead of `'SPEAKING'`.

2. **Application Event Ingestion & State Mapping in `src/lib/gateway-client.ts`**:
   - Ensure `agent.state` / `agent_state` transitions map correctly to visualizer states.
   - When `tool.start` arrives with `tool` name: classify tool using `classifyToolState` and emit `jarvis-state` or set active tool.
     - `crawl4ai_*`, `browser_use_*`, `/search` -> `WEB_SEARCH`
     - `gpt_researcher_*`, `delegate_task` -> `DEEP_RESEARCH`
     - `markitdown_*`, `code_*`, terminal execution -> `CODING`
     - `camera_*`, `mediapipe_*`, `deepface_*`, `vision_*`, or vision toggle `isVideoOn` -> `VISION_SCAN`
     - `memory_*`, `state_db_*`, `saveCoreMemory`, `retrieveCoreMemory` -> `MEMORY_SYNC`
     - any other tool -> `EXECUTING_TOOL`
   - When `tool.result` arrives: if `outcome === 'DENIED'` or security violation/AgentShield block detected, emit `ALERT`. Otherwise, clear active tool / dwell fallback.
   - When `confirmation_request` arrives: emit `ALERT`.
   - When `wake_word_detected` arrives: emit `LISTENING`.
   - When TTS playback starts: emit `SPEAKING`. When ended/error: revert to previous agent state or IDLE.
   - Live audio streaming: In `playTtsAudio`, feed audio amplitude levels into `jarvisRealtimeRef.audioLevel` for dynamic reactivity during speech.

3. **State Machine & Priority Arbitration in `src/components/dashboard/holographic-core/state-machine.ts`**:
   - Update `classifyToolState` (or tool regexes) to comprehensively cover:
     - `WEB_SEARCH`: `/search|browse|crawl|google|web/i`
     - `DEEP_RESEARCH`: `/research|delegate|analyze|investigate/i`
     - `CODING`: `/code|terminal|bash|edit|exec|shell|markitdown/i`
     - `VISION_SCAN`: `/vision|camera|scan|face|lidar|mediapipe/i`
     - `MEMORY_SYNC`: `/memory|db|store|sync|recall/i`
     - default: `EXECUTING_TOOL`
   - Update `resolveActiveState()` to enforce the strict 7-level priority hierarchy:
     `ALERT (100) > VISION_SCAN (90) > SPEAKING (80) > ACTIVE_TOOL (70) > THINKING (60) > LISTENING (50) > IDLE (10)`.
     Ensure `SPEAKING` and `VISION_SCAN` take precedence over `ACTIVE_TOOL`!
   - Update `unpackJarvisStateDetail` to handle:
     - `{ detail: { state: HolographicState } }`
     - `{ detail: HolographicState }` (string primitive)
     - Case-insensitive normalization and legacy aliases (`LISTEN` -> `LISTENING`, `PROCESSING` -> `THINKING`).
   - Implement appropriate fallback timeouts and dwell times (e.g. 2000ms tool dwell, 4000ms alert decay, 350ms speech decay).

4. **Props & Sphere Integration**:
   - In `src/components/dashboard/sphere.tsx`: Ensure `SphereProps` accepts `activeTool?: string` and `isVideoOn?: boolean`, and passes them to the state machine / core visualizer hooks.
   - In `src/pages/dashboard.tsx`: Pass `activeTool={activeTool}` and `isVideoOn={isVideoOn}` to `<Sphere />` instances (lines ~606 and ~695).

5. **Interactive Testing Keyboard Shortcuts in `src/pages/dashboard.tsx`**:
   - Add a `keydown` event listener in `src/pages/dashboard.tsx` for keys:
     - `'1'` -> IDLE
     - `'2'` -> LISTENING
     - `'3'` -> THINKING
     - `'4'` -> SPEAKING
     - `'5'` -> WEB_SEARCH
     - `'6'` -> DEEP_RESEARCH
     - `'7'` -> CODING
     - `'8'` -> VISION_SCAN
     - `'9'` -> MEMORY_SYNC
     - `'0'` -> EXECUTING_TOOL
     - `'-'` -> ALERT
   - Guard against typing in forms: ignore if `event.target` is an `<input>`, `<textarea>`, `<select>`, or `isContentEditable`.
   - Guard against modifiers: ignore if `event.ctrlKey || event.altKey || event.metaKey`.
   - Dispatch `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: targetState } }))`.

6. **Comprehensive Unit & Integration Test Suite**:
   - Create `src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts` following Explorer 3's test plan:
     - Test 1: State mapping for all 11 states via `classifyToolState` and event inputs.
     - Test 2: Priority arbitration hierarchy (verifying ALERT > VISION_SCAN > SPEAKING > ACTIVE_TOOL > THINKING > LISTENING > IDLE across conflicting concurrent inputs).
     - Test 3: Fallback and dwell timers (decay to IDLE or base state after tool/speech finishes).
     - Test 4: CustomEvent detail unpacking (handling `{ detail: { state } }`, `{ detail: state }`, legacy aliases, case-insensitivity).
     - Test 5: Keyboard hotkeys & guards (verifying keys 1-0 and -, verifying inputs/contenteditable/modifiers are ignored).
     - Test 6: Audio level streaming (updating `jarvisRealtimeRef.audioLevel` synchronously).

## Verification Requirements
You must run the following commands and include full output in your handoff report:
1. `npm run typecheck` — MUST pass with 0 errors across all tsconfigs.
2. `npx vite build` — MUST pass with exit code 0.
3. `npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts` — MUST pass 27/27.
4. `npx vitest run src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts` — MUST pass 100%.

## Output Requirements
Write your detailed report to `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m2_1\report.md` and write a 5-component `handoff.md` (Observation, Logic Chain, Caveats, Conclusion, Verification Method) in the same directory.
When finished, send a message to the orchestrator summarizing your implementation and test results.
