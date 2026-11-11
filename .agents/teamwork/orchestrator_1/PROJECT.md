# Project: 3D Holographic Core Visualizer Integration

## Architecture
- **Target App**: J.A.R.V.I.S Electron App (React 19 + TypeScript + Electron + Vite)
- **Source Specification**: `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`
- **Component Target**: `src/components/dashboard/sphere.tsx` (imported and rendered in `src/pages/dashboard.tsx`)
- **Graphics Pipeline**: Three.js (^0.180.0) + `@react-three/fiber` (^9.6.1) + `@react-three/drei` (^10.7.7)
  - Layer 1: Contrast Backdrop Halo (procedural dark radial gradient billboard)
  - Layer 2: Volumetric Glow Sprite (procedural radial gradient billboard with state-damped scaling and breathing)
  - Layer 3: Gyroscopic / Scanner Rings (Ring 1 outer tilted, Ring 2 counter-rotating inner, Ring 3 vision scan laser plane)
  - Layer 4: 3D Fibonacci Particle Cloud (golden-spiral sphere, lat/lon globe morph target, beveled cube morph target, toroidal flow, 3 concentric shells, cardiac shockwave)
- **State Transition Engine**: Multi-weight exponential damping (`damp = 1 - Math.exp(-6.2 * dt)`) across 11 discrete cognitive states
- **Audio Reactivity Engine**: 3-band FFT spectrum processing (bass/mid/treble) with zero-re-render bridge via `jarvisRealtimeRef.audioLevel`, AnalyserNode support, and autonomous speech cadence simulation fallback
- **Event & State Bus**: Dual WebSocket (`/ws` and `/ws/jarvis`) + Electron IPC + window `jarvis-state` CustomEvent bridge + keyboard testing shortcuts (`1`-`0`, `-`)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 11 Core Holographic States | Complete 11 states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`) with exact hex palettes and visual behaviors | M1 | Survey R1 |
| 2 | Multi-Layer Compositing | 4-layer depth compositing (contrast backdrop, core glow sprite, 3 gyroscopic/scanner rings, Fibonacci particle cloud) | M1 | Survey R1 |
| 3 | Procedural Particle Geometry | Fibonacci sphere particle distribution with theta/phi/normals and custom morph targets (Globe, Cube, Torus) | M1 | Survey R1 |
| 4 | State Displacement & Physics | Mathematical displacement equations for all 11 states (vortex twist, sonar ripple, poloidal flow, lidar scan plane, cardiac shockwave) | M1 | Survey R1 |
| 5 | Damped State Weight Morphing | Concurrent exponential damping of state weights `w[state]` with safe delta clamping | M1 | Survey R1 |
| 6 | Interactive Controls | Orbit rotation pointer drag with damping and pitch clamping | M1 | Survey R1 |
| 7 | Audio Reactivity Pipeline | 3-band FFT bin aggregation, live mic amplification, `jarvisRealtimeRef.audioLevel` zero-re-render bridge, synthetic cadence fallback | M1 | Survey R1 |
| 8 | Drop-in Component Compatibility | Replacement of `src/components/dashboard/sphere.tsx` preserving export contract and props for `src/pages/dashboard.tsx` | M1 | Survey R1 |
| 9 | Application Event Wiring | Ingestion of `agent.state`, `tool.start`, `tool.result`, `tts_playback`, `wake_word_detected`, security alerts, and vision mode into visualizer states | M2 | Survey R2 |
| 10 | State Arbitration & Priority | Hierarchical priority resolution (`ALERT > VISION_SCAN > SPEAKING > EXECUTING_TOOL > THINKING > LISTENING > IDLE`) with dwell times and fallback timeouts | M2 | Survey R2 |
| 11 | Custom Event & Testing Hotkeys | `jarvis-state` Window CustomEvent listener and numeric keyboard shortcuts (`1`-`0`, `-`) for immediate state switching | M2 | Survey R2 |
| 12 | TypeScript Compilation & Clean Build | Complete TypeScript type safety (`tsc --noEmit`), Vite production build verification with zero errors | M3 | Survey AC |
| 13 | Runtime & Shader Clean Launch | Automated verification that Electron application launches and visualizer renders without WebGL/shader errors or console warnings | M3 | Survey AC |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Visualizer Component Replacement | Implement the 3D holographic core visualizer in `src/components/dashboard/sphere.tsx` with all 4 layers, 11 states, morph targets, damping transitions, and audio reactivity | none | DONE |
| M2 | State & Event Wiring | Wire backend/frontend runtime events (`agent.state`, `tool.*`, `tts_playback`, security alarms, vision mode) to visualizer states with arbitration, timeouts, and keyboard hotkeys | M1 | PLANNED |
| M3 | E2E Verification & Clean Runtime | Comprehensive build validation (`tsc --noEmit`), automated test verification, and Electron launch/rendering verification | M2 | PLANNED |

## Interface Contracts
### `src/components/dashboard/sphere.tsx`
- Component Props:
  ```typescript
  export interface SphereProps {
    isListening?: boolean;
    isSpeaking?: boolean;
    isThinking?: boolean;
    activeTool?: string | null;
    error?: string | null;
    overrideState?: HolographicState | null;
    className?: string;
  }
  ```
- Exported Types & Constants:
  - `export type HolographicState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING' | 'WEB_SEARCH' | 'DEEP_RESEARCH' | 'CODING' | 'VISION_SCAN' | 'MEMORY_SYNC' | 'EXECUTING_TOOL' | 'ALERT';`
  - `export const HOLOGRAPHIC_STATES: Record<HolographicState, { name: string; hex: string; description: string }>;`
  - `export default Sphere;` (and `export { Sphere };`)

### Runtime Event Integration
- CustomEvent:
  ```typescript
  window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: HolographicState } }));
  ```
- WebSocket / Bridge mapping:
  - `agent.state` -> `idle` -> `IDLE`, `listening` -> `LISTENING`, `thinking` -> `THINKING`, `speaking` -> `SPEAKING`
  - `tool.start` with tool name -> mapping:
    - `crawl4ai_*`, `browser_use_*` -> `WEB_SEARCH`
    - `gpt_researcher_*`, `delegate_task` -> `DEEP_RESEARCH`
    - `markitdown_*`, `code_*`, terminal -> `CODING`
    - `camera_*`, `mediapipe_*`, `vision_*` -> `VISION_SCAN`
    - `memory_*`, `state_db_*` -> `MEMORY_SYNC`
    - other tools -> `EXECUTING_TOOL`
  - `AgentShield` security block / alert -> `ALERT`

## Code Layout
- `src/components/dashboard/sphere.tsx`: Main component entry point and 3D canvas
- `src/components/dashboard/holographic-core/`:
  - `types.ts`: State definitions, color palettes, interfaces
  - `geometry.ts`: Fibonacci distribution, Globe morph target, Cube morph target
  - `materials.ts`: Procedural canvas textures for backdrop and core glow sprite
  - `audio.ts`: 3-band FFT processing, live mic integration, synthetic cadence fallback
  - `state-manager.ts`: State weight damping, priority arbitration, fallback timers
  - `HolographicCore.tsx`: Three.js scene graph containing backdrop, glow, rings, and particles
- `src/services/jarvisBridge.ts` & `src/lib/gateway-client.ts`: Event listeners dispatching visualizer states
