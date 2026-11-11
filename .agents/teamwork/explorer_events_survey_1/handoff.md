# Handoff Report — J.A.R.V.I.S. Visualizer State & Event System Survey

**Investigation Milestone**: Holographic Core Visualizer Event Wiring Survey  
**Agent**: Teamwork Explorer (`explorer_events_survey_1`)  
**Target Path**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_events_survey_1\handoff.md`  
**Date**: 2026-11-11T09:17:00Z  

---

## 1. Observation

1. **Reference 11-State Visualizer HTML Specification**:
   - File: `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`
   - Defines 11 discrete states (Lines 268–360):
     - `IDLE` (`#67e8f9` Ice-Cyan, Key `1`)
     - `LISTENING` (`#00f0ff` Sky-Cyan, Key `2`)
     - `THINKING` (`#fbbf24` Amber-Gold, Key `3`)
     - `SPEAKING` (`#e0f2fe` White-Ice, Key `4`)
     - `WEB_SEARCH` (`#38bdf8` Cyber Azure, Key `5`)
     - `DEEP_RESEARCH` (`#818cf8` Periwinkle, Key `6`)
     - `CODING` (`#4ade80` Matrix Mint, Key `7`)
     - `VISION_SCAN` (`#f472b6` Laser Rose, Key `8`)
     - `MEMORY_SYNC` (`#2dd4bf` Teal-Cyan, Key `9`)
     - `EXECUTING_TOOL` (`#c084fc` Neon Violet, Key `0`)
     - `ALERT` (`#fb7185` Crimson-Coral, Key `-`)
   - Lines 368–760: Provides an embedded React Three Fiber implementation (`sphere.tsx`) designed for Three.js and `@react-three/fiber`.

2. **Frontend Visualizer Component**:
   - File: `src/components/dashboard/sphere.tsx` (Lines 1–761)
   - Currently mounted inside `src/pages/dashboard.tsx` at Line 606 (Focus Mode) and Line 695 (Standard HUD).
   - Ingests state via `window.addEventListener('jarvis-state', handleState)` (Line 255) and reads `jarvisRealtimeRef.voiceState` and `jarvisRealtimeRef.audioLevel` in `useFrame` (Lines 288–324).
   - Color palette in the existing component (Lines 26–38) uses legacy gold/amber `#daa02a` rather than the official 11-state cyan/multicolor palette from the downloaded HTML spec.

3. **Frontend WebSocket Clients & Event Dispatchers**:
   - `src/lib/gateway-client.ts`: Connects to `ws://127.0.0.1:8765/ws/jarvis`. Handles `agent.state` (Line 226), `agent.token` (Line 233), `agent.complete` (Line 243), `tool.start` (Line 260), `tool.result` (Line 268), `tts_playback` (Line 329), and `confirmation_request` (Line 310).
   - `src/services/jarvisBridge.ts`: Connects to `ws://127.0.0.1:8765/ws`. Maintains mutable reference store `jarvisRealtimeRef` (Line 71) for zero-re-render 60 FPS updates.
   - `src/services/jarvis-voice-ai.ts`: Connects Web Audio `AnalyserNode` to user microphone (Line 39) and listens for `wake_word_detected` (Line 95).
   - `src/services/hermes-adapter.ts`: Translates streaming chunks to `SPEAKING`, turns to `LISTEN`, and tool calls to `PROCESSING`.

4. **Backend Event Emission**:
   - `backend/main.py`: FastAPI gateway broadcasting `system.metrics` and `telemetry`, routing user messages, and streaming `hermes_brain.run_turn` events.
   - `backend/core/hermes_brain.py`: Emits `agent.state: 'thinking'` (Line 114), `agent.state: 'compressing'` (Line 137), `agent.token` (Line 169), and `agent.complete` (Line 202).
   - `backend/voice/audio_pipeline.py`: Conversational audio pipeline broadcasting `agent.state: 'listening'` upon sub-32ms barge-in (Line 107) and `speaking` during 24kHz OmniVoice TTS playback (Line 67).
   - `backend/core/tool_dispatcher.py`: Dispatches tools including `crawl4ai_extract`, `browser_use_background`, `gpt_researcher_report`, `delegate_task`, `markitdown_convert`, `agent_s3_visual_task`, `windows_mcp_snapshot`, `memory`, and `session_search`.

---

## 2. Logic Chain

1. **Observation 1 & 2** establish that the 11 visualizer states and their 3D morphing geometries are well-defined and already have an embedded React Three Fiber component template that can directly replace `src/components/dashboard/sphere.tsx`.
2. **Observation 3** establishes that the frontend already contains two WebSocket connections (`gatewayClient` and `jarvisBridge`) and a custom event mechanism (`jarvis-state`), plus a zero-re-render mutable reference (`jarvisRealtimeRef`) read during every animation frame.
3. **Observation 4** establishes that all 11 states have direct, distinct runtime counterparts in the backend:
   - Standby / completed turns → `IDLE`
   - Wake word / live mic / barge-in → `LISTENING`
   - Reasoning / compressing / prompt building → `THINKING`
   - TTS audio / token stream → `SPEAKING`
   - `crawl4ai_extract` / `browser_use_background` / search → `WEB_SEARCH`
   - `gpt_researcher_report` / `delegate_task` / subagents → `DEEP_RESEARCH`
   - `markitdown_convert` / terminal scripts / file modifications → `CODING`
   - Camera vision / `agent_s3_visual_task` / `windows_mcp_snapshot` → `VISION_SCAN`
   - Memory queries / `saveCoreMemory` / `session_search` → `MEMORY_SYNC`
   - OS actions (`windows_mcp_click`/`type`), mobile ADB, `todo` → `EXECUTING_TOOL`
   - Security policy violations (`AgentShield`), critical alerts, errors → `ALERT`
4. **Synthesis**:
   - By creating a centralized state coordinator (e.g. `visualizerManager`) and routing tool names from `tool.start` in `gatewayClient.ts`, updating `gatewayClient` TTS audio triggers, and updating `jarvisRealtimeRef.voiceState`, the visualizer can transition seamlessly across all 11 states without adding overhead or architectural debt.

---

## 3. Caveats

- **No Source Code Modified**: As mandated by the investigator identity, this turn performed read-only survey and architecture design. Source files remain unaltered.
- **Audio Analyser Availability**: If the user does not grant microphone permission or if audio output is muted, the procedural cadence synthesizer fallback within `sphere.tsx` ensures that `SPEAKING` and `LISTENING` animations remain dynamic.
- **Concurrent Events**: In multi-agent or vision-assisted scenarios, multiple activities occur at once (e.g. camera processing while speech is playing). The proposed strict priority hierarchy (`ALERT > VISION_SCAN > SPEAKING > ACTIVE_TOOL > THINKING > LISTENING > IDLE`) prevents visual glitches and ensures the most important user-facing state takes visual precedence.

---

## 4. Conclusion

The application architecture fully supports connecting all 11 holographic core states. The integration requires:
1. Replacing the sphere shaders, geometry precomputations, and color definitions in `src/components/dashboard/sphere.tsx` with the 11-state specification from `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`.
2. Updating `src/lib/gateway-client.ts` to map tool names (`crawl4ai_extract` -> `WEB_SEARCH`, `gpt_researcher_report` -> `DEEP_RESEARCH`, `markitdown_convert` -> `CODING`, `agent_s3_visual_task` -> `VISION_SCAN`, `memory` -> `MEMORY_SYNC`, others -> `EXECUTING_TOOL`) and errors/confirmation requests to `ALERT`.
3. Wiring `jarvisRealtimeRef.voiceState` and `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: state }))` so that state changes take effect instantaneously with exponential dampening in Three.js `useFrame`.
4. Retaining keyboard hotkeys (`1`–`0`, `-`) and adding a HUD manual debug selector for inspection.

---

## 5. Verification Method

To independently verify the investigation findings:
1. **Examine Survey Report**:
   Read `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_events_survey_1\report.md`.
2. **Inspect Core Files**:
   - `src/components/dashboard/sphere.tsx` (current visualizer mounting and event listeners).
   - `src/lib/gateway-client.ts` (tool.start, tool.result, agent.state, tts_playback).
   - `src/services/jarvisBridge.ts` (jarvisRealtimeRef mutable ref store).
   - `backend/core/tool_dispatcher.py` (Phase 6 registered tools).
   - `backend/core/hermes_brain.py` (run_turn event yields).
   - `backend/voice/audio_pipeline.py` (barge-in and voice state broadcasting).
3. **Run Typecheck & Lint Verification**:
   ```powershell
   npm run typecheck
   npm run check:lint
   ```
4. **Invalidation Conditions**:
   The logic would be invalidated if the backend did not emit tool names during execution or if `@react-three/fiber` lacked support for dynamic point cloud attributes, neither of which is the case here.
