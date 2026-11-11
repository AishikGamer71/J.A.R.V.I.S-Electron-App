# Scope: Milestone 2 — Visualizer State & Event Wiring

## Objective
Connect all 11 holographic core states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`) to the Electron application's corresponding runtime states and events where applicable, ensuring smooth transitions between states during app operation.

## Architecture & Integration Points
- **Runtime Bridge & Gateway Ingestion**: `src/services/jarvisBridge.ts`, `src/lib/gateway-client.ts`, agent state listeners, and event hooks.
- **State Arbitration Engine**: Priority hierarchy resolving concurrent states:
  `ALERT > VISION_SCAN > SPEAKING > ACTIVE_TOOL (WEB_SEARCH, DEEP_RESEARCH, CODING, MEMORY_SYNC, EXECUTING_TOOL) > THINKING > LISTENING > IDLE`.
  Fallback timeouts and dwell times returning to IDLE / agent state.
- **Interactive Verification & CustomEvent**:
  - `window.addEventListener('jarvis-state', ...)` CustomEvent support with `{ detail: { state: HolographicState } }` or `{ detail: HolographicState }`.
  - Numeric keyboard shortcuts in `src/pages/dashboard.tsx` (`1`=IDLE, `2`=LISTENING, `3`=THINKING, `4`=SPEAKING, `5`=WEB_SEARCH, `6`=DEEP_RESEARCH, `7`=CODING, `8`=VISION_SCAN, `9`=MEMORY_SYNC, `0`=EXECUTING_TOOL, `-`=ALERT) guarded against input/textarea elements.
- **Audio Streaming Integration**:
  - Mic and TTS audio levels fed into `jarvisRealtimeRef.audioLevel` for dynamic reactivity in `LISTENING` and `SPEAKING` states.
- **Testing & Verification**:
  - Unit/integration tests covering all 11 states, priority arbitration, timeouts, and keyboard listeners.
  - Zero TypeScript errors (`tsc -p . --noEmit`) and clean build (`npx vite build`).

## Iteration Configuration
- Explorer count: 3
- Reviewer count: 2
- Challenger count: 2
- Forensic Auditor: 1
