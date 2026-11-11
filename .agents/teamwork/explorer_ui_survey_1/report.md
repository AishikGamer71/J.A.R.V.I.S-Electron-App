# J.A.R.V.I.S UI Visualizer Survey & 3D Holographic Core Integration Report

**Date**: 2026-11-11  
**Author**: teamwork_explorer (`explorer_ui_survey_1`)  
**Mission**: Investigate the existing visualizer architecture in the J.A.R.V.I.S Electron App UI and establish the integration plan for the 3D Holographic Core Visualizer from `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`.

---

## Executive Summary

1. **Existing Visualizer Components Identified**:
   - `src/components/dashboard/sphere.tsx`: The active 3D particle sphere component utilizing `@react-three/fiber` and Three.js. It implements an earlier 11-state morphing particle engine, but has color overrides (bronze/gold) and diverges from the canonical cyan/ice holographic palette in `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`.
   - `src/components/widgets/arc-reactor.tsx`: A legacy 2D HTML5 Canvas Arc Reactor widget. **It is completely orphaned and unreferenced anywhere in the codebase.**
   - `src/components/dashboard/particle-network.tsx`: A 2D constellation background canvas in `IndexRoot.tsx`, orthogonal to the 3D core.

2. **Render Locations & Call Sites**:
   - `Sphere` is imported and rendered in **exactly one file**: `src/pages/dashboard.tsx`.
   - Call Site 1 (Focus Mode): Fullscreen overlay (`w-[84vmin] h-[84vmin] max-w-[95vw] max-h-[95vh]`) at line 606.
   - Call Site 2 (Normal Dashboard): Center column (`w-[60vh] h-[60vh] max-w-full`) at line 695.
   - Props passed at call sites: None (`<Sphere />` defaults to 2,600 particles).
   - No other tabs (Workspace, Modules, Phone, Task Manager, Apps, Notes, Settings, Gallery, Terminal) import or render the core visualizer.

3. **Dependencies & WebGL Stack**:
   - `three`: `^0.180.0` (installed in `dependencies`)
   - `@react-three/fiber`: `^9.6.1` (installed in `dependencies`)
   - `@react-three/drei`: `^10.7.7` (installed in `dependencies`)
   - `@types/three`: Present in `node_modules/@types/three`
   - `postprocessing`: **Not installed and NOT needed.** The visualizer uses native Three.js materials (`THREE.PointsMaterial`, `THREE.SpriteMaterial`, `THREE.MeshBasicMaterial`) with `THREE.AdditiveBlending`, procedural CanvasTextures, and vertex displacement.
   - Project typecheck (`npx tsc -p . --noEmit`): **100% clean, 0 errors.**
   - **Zero new npm packages required.**

4. **Lifecycle & Sizing Strategy**:
   - Managed via React Three Fiber `<Canvas>`.
   - Auto-resizing via R3F's internal `ResizeObserver`.
   - Explicit cleanup of CanvasTextures (`glowTexture.dispose()`, `backdropTexture.dispose()`) on unmount.
   - Render isolation via `React.memo(SphereComponent, () => true)` ensures parent re-renders (such as 1 Hz telemetry polling) never trigger WebGL context teardown or re-initialization.

5. **Integration Path**:
   - Clean drop-in replacement via `src/components/dashboard/sphere.tsx` (or modular `src/components/dashboard/holographic-core/` re-exported from `sphere.tsx`).
   - Retains exact export signature (`export default Sphere`, `export const Sphere`, `export type JarvisVisualState`, `export interface ParticleSphereProps`).
   - Connects canonical cyan-ice 11-state palette and visual aesthetics from the HTML source while preserving the Electron bridge integrations (`jarvisRealtimeRef` zero-re-render audio stream, `jarvisService?.analyser`, `jarvis-state` custom events, keyboard triggers).
   - **Guarantees zero regressions across the entire application.**

---

## 1. Inventory of Visualizer Components in Codebase

### 1.1 `src/components/dashboard/sphere.tsx` (Active Component)
- **File Length**: 761 lines
- **Framework**: `@react-three/fiber` (R3F) v9.6.1 + `three` v0.180.0
- **Exports**:
  - `export type JarvisVisualState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING' | 'WEB_SEARCH' | 'DEEP_RESEARCH' | 'CODING' | 'VISION_SCAN' | 'MEMORY_SYNC' | 'EXECUTING_TOOL' | 'ALERT'`
  - `export const Sphere = React.memo(SphereComponent, () => true)`
  - `export default Sphere`
- **Internal Structure**:
  - `CustomParticleSphere` (memoized inner R3F component):
    - **Layer 0**: Dark contrast halo sprite (`scale={[4.2, 4.2, 1]}`) using radial gradient `CanvasTexture`.
    - **Layer 1**: Volumetric inner core glow sprite (`scale={[2.45, 2.45, 1]}`) using `CanvasTexture`.
    - **Layer 2**: Three gyroscopic/scanner rings (`THREE.TorusGeometry`):
      - Ring 1 (`torusGeometry args={[2.06, 0.01, 12, 144]}`)
      - Ring 2 (`torusGeometry args={[2.19, 0.007, 12, 144]}`)
      - Ring 3 (`torusGeometry args={[1.74, 0.012, 12, 144]}`)
    - **Layer 3**: Morphing 3D particle cloud (`THREE.Points`) with 2,600 vertices distributed via golden-ratio Fibonacci sphere algorithm.
- **Runtime State & Audio Reactivity**:
  - Subscribed to `window.addEventListener('jarvis-state', handleState)`
  - Aliases `'LISTEN'` -> `'LISTENING'`, `'PROCESSING'` -> `'THINKING'`
  - Reads mutable 60 FPS bridge `jarvisRealtimeRef` (`audioLevel`, `voiceState`) inside `useFrame`
  - Reads `jarvisService?.analyser` Web Audio FFT bytes (128-bin array)
  - Synthetic speech cadence generator fallback for `SPEAKING` state when audio amplitude is low
  - Keyboard listener for keys `'1'`-`'9'`, `'0'`, `'-'` with input element protection (`INPUT`, `TEXTAREA`, `isContentEditable`)
  - Target morphs: Lat/Lon holographic globe for `WEB_SEARCH`, beveled 3D cube for `CODING`, polar tunnel torus for `MEMORY_SYNC`, nested counter-rotating shells for `DEEP_RESEARCH`, optical planar slice ring for `VISION_SCAN`, twin cardiac shockwaves for `ALERT`.

### 1.2 `src/components/widgets/arc-reactor.tsx` (Legacy / Orphaned)
- **File Length**: 265 lines
- **Framework**: Plain 2D Canvas (`canvas.getContext('2d')`)
- **Exports**: `export const ArcReactor`, `export default ArcReactor`, `export const JARVIS_LIGHTING_CONFIG`
- **Usage**: Grep across entire `src/` directory confirms **0 imports and 0 usages**.
- **Assessment**: Unused legacy widget from early prototyping. Can be left untouched or deprecated without impacting the application.

### 1.3 `src/components/dashboard/particle-network.tsx` (Background Only)
- **File Length**: 155 lines
- **Framework**: Plain 2D Canvas
- **Usage**: Rendered in `IndexRoot.tsx` at line 209 as a static, non-interactive background star/constellation grid behind the UI. Does not represent the J.A.R.V.I.S. core.

---

## 2. Call Sites and Layout Hierarchy

A full codebase search confirms `Sphere` is imported and rendered exclusively in `src/pages/dashboard.tsx`.

```
src/IndexRoot.tsx
 └── src/layouts/jarvis-layout.tsx (Tabs: DASHBOARD, WORKSPACE, MODULES, PHONE, TASK MANAGER, Apps, NOTES, SETTINGS, GALLERY, TERMINAL)
      └── src/pages/dashboard.tsx (DashboardView)
           ├── Line 606: Focus Mode Overlay
           │    └── <div className="w-[84vmin] h-[84vmin] max-w-[95vw] max-h-[95vh] flex items-center justify-center pointer-events-none">
           │         └── <Sphere />
           └── Line 695: Central Dashboard Column
                └── <div className="w-[60vh] h-[60vh] max-w-full transition-all duration-1000 ${isSystemActive ? 'opacity-100 scale-100' : 'opacity-85 scale-90 grayscale'} pointer-events-none">
                     └── <Sphere />
```

### Call Site Details:
| File | Line | Mode / Container | Container Constraints | Props |
|---|---|---|---|---|
| `src/pages/dashboard.tsx` | 606 | Focus Mode (`isFocusMode === true`) | `fixed inset-0 z-[9999] bg-[#020611]` -> `w-[84vmin] h-[84vmin] max-w-[95vw] max-h-[95vh]` | None |
| `src/pages/dashboard.tsx` | 695 | Normal Mode (`col-span-12 lg:col-span-6`) | `w-[60vh] h-[60vh] max-w-full transition-all duration-1000` | None |

### Container Constraints & Layout Observations:
- Both containers apply `pointer-events-none` so mouse interactions pass through to underlying UI controls (or the background).
- Both containers enforce square aspect ratios via viewport units (`60vh` and `84vmin`).
- In Normal Mode, `isSystemActive` drives a smooth CSS transition (`duration-1000`):
  - When inactive (`isSystemActive === false`): `opacity-85 scale-90 grayscale`
  - When active (`isSystemActive === true`): `opacity-100 scale-100` (full color)
- In Focus Mode, an "EXIT FOCUS" button is fixed at `top-6 right-6 z-50`.

---

## 3. Package & Dependency Analysis

Inspecting `package.json`:
- `"three": "^0.180.0"` — Already installed.
- `"@react-three/fiber": "^9.6.1"` — Already installed.
- `"@react-three/drei": "^10.7.7"` — Already installed.
- `"@types/three"` — Verified present in `node_modules/@types/three`.
- `postprocessing` / `@react-three/postprocessing` — Not installed.

### Evaluation of `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`:
- The HTML visualizer uses vanilla Three.js r128 via CDN.
- It contains an embedded reference implementation `SPHERE_TSX_SOURCE` designed for `@react-three/fiber`.
- The shader/render pipeline relies exclusively on:
  - `THREE.PointsMaterial` with `THREE.AdditiveBlending`, `vertexColors: true`, `sizeAttenuation: true`, and `depthWrite: false`
  - `THREE.SpriteMaterial` with `THREE.AdditiveBlending`, `toneMapped: false`, and procedural `CanvasTexture`
  - `THREE.MeshBasicMaterial` with `THREE.AdditiveBlending`
  - No postprocessing passes (e.g. UnrealBloomPass or EffectComposer) are used. The glowing holographic aesthetic is achieved entirely through additive particle sprites and procedural halo textures.
- **Conclusion**: **NO new dependencies are required.** All necessary Three.js and R3F packages are present and operational.

---

## 4. Canvas Mounting, Sizing, Resize & WebGL Lifecycle

### 4.1 Mounting & Sizing
In `sphere.tsx`:
```tsx
<Canvas
  className="w-full h-full"
  camera={{ position: [0, 0, 5.1], fov: 58 }}
  dpr={[1, 1.5]}
  flat
  gl={{
    antialias: false,
    alpha: true,
    stencil: false,
    depth: false,
    powerPreference: 'high-performance',
  }}
>
```
- The canvas attaches to the parent DOM element (`w-full h-full`).
- R3F attaches an internal `ResizeObserver` to the container element. Sizing, aspect ratio updates (`camera.aspect = width / height`), and projection matrix recalculations (`camera.updateProjectionMatrix()`) occur automatically without manual window event listeners.
- The `dpr={[1, 1.5]}` clamp avoids performance degradation on high-density Retina/4K displays.

### 4.2 WebGL Context Lifecycle & Isolation
- **Isolation via Memoization**:
  `export const Sphere = React.memo(SphereComponent, () => true)`
  This is a critical architectural pattern in this application. In `src/layouts/jarvis-layout.tsx`, `LiveClock` and `getSystemStatus()` poll system stats every 1 second. Without `React.memo(..., () => true)`, every 1-second state tick would re-render `DashboardView`, which would re-evaluate `<Sphere />`. The memoization ensures the R3F `<Canvas>` and WebGL context remain stable and never remount while navigating or monitoring telemetry.
- **Cleanup & Disposal**:
  Inside the component, `glowTexture` and `backdropTexture` are created using `useMemo` and disposed in a `useEffect` cleanup return:
  ```tsx
  useEffect(() => {
    return () => {
      glowTexture.dispose()
      backdropTexture.dispose()
    }
  }, [glowTexture, backdropTexture])
  ```
  When navigating away from the Dashboard tab (e.g., to Settings or Workspace), `AnimatePresence` unmounts `DashboardView`. R3F automatically disposes the WebGL context and frees GPU memory.

---

## 5. Comparative Analysis: HTML Source vs. Existing `sphere.tsx`

The downloaded file `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html` contains the canonical 11-State 3D Holographic Core design. Comparing it to `src/components/dashboard/sphere.tsx`:

| Feature | HTML Visualizer Source | Existing `sphere.tsx` in App | Assessment / Action |
|---|---|---|---|
| **IDLE Palette** | Ice-Cyan (`#67e8f9`) | Bronze (`#daa02a`) | Restore canonical Ice-Cyan `#67e8f9` |
| **LISTENING Palette** | Sky-Cyan (`#00f0ff`) | Golden (`#f2bc3e`) | Restore canonical Sky-Cyan `#00f0ff` |
| **THINKING Palette** | Amber-Gold (`#fbbf24`) | Amber (`#e5a93b`) | Restore canonical Amber-Gold `#fbbf24` |
| **SPEAKING Palette** | White-Ice (`#e0f2fe`) | Warm Silver (`#e1d7be`) | Restore canonical White-Ice `#e0f2fe` |
| **WEB_SEARCH Palette** | Cyber Azure (`#38bdf8`) | Cyber Azure (`#38bdf8`) | Identical |
| **DEEP_RESEARCH Palette**| Periwinkle (`#818cf8`) | Periwinkle (`#818cf8`) | Identical |
| **CODING Palette** | Matrix Mint (`#4ade80`) | Matrix Mint (`#4ade80`) | Identical |
| **VISION_SCAN Palette** | Laser Rose (`#f472b6`) | Laser Rose (`#f472b6`) | Identical |
| **MEMORY_SYNC Palette** | Teal-Cyan (`#2dd4bf`) | Teal-Cyan (`#2dd4bf`) | Identical |
| **EXECUTING_TOOL Palette**| Neon Violet (`#c084fc`) | Neon Violet (`#c084fc`) | Identical |
| **ALERT Palette** | Crimson-Coral (`#fb7185`)| Crimson-Coral (`#fb7185`)| Identical |
| **Backdrop Halo Texture** | Deep blue-cyan `rgba(2, 8, 22, 0.88)` | Brown-amber `rgba(16, 9, 3, 0.55)` | Update to deep cyan halo |
| **Halo Sprite Scale** | `[5.15, 5.15, 1]` | `[4.2, 4.2, 1]` | Update to 5.15 for cinematic presence |
| **Base Particle Color** | `[0.4, 0.91, 0.98]` (Cyan) | `[0.855, 0.627, 0.165]` (Amber) | Update to cyan base |
| **Rings 1, 2, 3 Colors** | `#67e8f9`, `#67e8f9`, `#ffffff` | `#4e2c0f`, `#daa02a`, `#e1d7be` | Update to holographic cyan & white |
| **Interactive Camera Orbit** | Pointer drag rotation on rootGroup | Pointer events disabled | Add optional `interactive` mode (ideal for Focus Mode) |
| **Live Audio Bridge** | None (HTML uses dummy synth) | `jarvisRealtimeRef` & `jarvisService?.analyser` | **MUST PRESERVE** zero-re-render audio bridge |
| **Event Aliasing** | Exact state names | `'LISTEN'` -> `'LISTENING'`, `'PROCESSING'` -> `'THINKING'` | **MUST PRESERVE** for compatibility with `hermes-adapter.ts` |
| **Input Key Filter** | Simple tag check | `INPUT`, `TEXTAREA`, `isContentEditable` checks | **MUST PRESERVE** so typing does not change states |

---

## 6. Application State & Event Wiring Survey

The Electron app has several active sources dispatching and consuming events:

1. **`src/services/jarvisBridge.ts`**:
   - WebSocket connection to Python sidecar (`ws://127.0.0.1:8765/ws`).
   - On `voice_state` or `agent.state` messages:
     - Updates `jarvisRealtimeRef.audioLevel = amp` (0 to 1 float)
     - Updates `jarvisRealtimeRef.voiceState = state`
     - Dispatches `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: state }))`
2. **`src/lib/gateway-client.ts`**:
   - Receives `agent.state` / `agent_state` from Hermes agent gateway.
   - Dispatches `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: stateVal }))`.
   - On TTS audio playback: dispatches `SPEAKING` on start, `IDLE` on finish/error.
   - On speech cancellation: dispatches `IDLE`.
3. **`src/services/hermes-adapter.ts`**:
   - Stream delta events (`agent.message_chunk`, `turn.delta`): dispatches `SPEAKING`.
   - Completion events (`agent.complete`, `turn.complete`): dispatches `LISTEN`.
   - Tool execution (`tool.started`, `agent.tool_call`, `processing`): dispatches `PROCESSING`.
4. **`src/services/jarvis-voice-ai.ts`**:
   - On wake word detection (`wake_word_detected`): dispatches `SPEAKING`.
   - Supplies `jarvisService.analyser` (Web Audio `AnalyserNode`) for live microphone FFT frequency extraction.
5. **Keyboard Hotkeys**:
   - Keys `'1'` through `'9'`, `'0'`, and `'-'` map to all 11 states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`).

---

## 7. Concrete Implementation & Architecture Recommendations

### 7.1 Proposed Modular File Structure
To keep the code clean, testable, and maintainable, we recommend structuring the visualizer under `src/components/dashboard/holographic-core/`:

```
src/components/dashboard/
├── sphere.tsx                          <-- Backwards-compatible export wrapper
└── holographic-core/
    ├── index.ts                        <-- Module entry point
    ├── holographic-core.tsx            <-- R3F Canvas and top-level container
    ├── particle-sphere.tsx             <-- CustomParticleSphere (mesh, rings, sprites, useFrame)
    ├── constants.ts                    <-- JARVIS_STATES, STATE_COLORS, BASE_RADIUS, KEY_MAP
    ├── types.ts                        <-- JarvisVisualState, HolographicCoreProps
    └── utils.ts                        <-- Fibonacci sphere, canvas texture generators, morph geometries
```

### 7.2 Backwards Compatibility Contract
In `src/components/dashboard/sphere.tsx`:
```tsx
import { HolographicCore } from './holographic-core'
export { HolographicCore as default, HolographicCore as Sphere } from './holographic-core'
export * from './holographic-core/types'
export * from './holographic-core/constants'
```
**Benefits**:
- Zero breaking changes to `src/pages/dashboard.tsx` (it continues to `import Sphere from '@/components/dashboard/sphere'`).
- Zero changes to existing types or event handlers.
- Separates math/geometry generation (`utils.ts`) and constants (`constants.ts`) from the Three.js rendering loop (`particle-sphere.tsx`).

### 7.3 Feature Enhancements Enabled by HTML Visualizer
1. **Canonical Cyan-Ice Theme**:
   Restore the iconic Ice-Cyan palette (`#67e8f9`), Sky-Cyan (`#00f0ff`), Amber-Gold (`#fbbf24`), and White-Ice (`#e0f2fe`), matching the canonical design from the HTML visualizer.
2. **Interactive Orbit Drag in Focus Mode**:
   Add an optional `interactive?: boolean` prop. In normal dashboard mode, `pointer-events-none` is preserved. In Focus Mode (`isFocusMode === true`), enabling `interactive={true}` allows the user to rotate and explore the 3D core with mouse drag.
3. **Zero-Re-Render 60 FPS Fidelity**:
   Retain direct reference reads to `jarvisRealtimeRef` inside `useFrame`, preserving ultra-smooth 60 FPS audio reactivity without triggering React re-renders.

---

## 8. Risk Assessment & Verification Plan

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Dashboard layout shift / regression | Low | High | Maintain exact DOM wrapper hierarchy, `w-full h-full`, and `React.memo` isolation |
| WebGL Context Loss / Performance | Low | High | Clamp DPR to `[1, 1.5]`, keep particle count default at 2,600, ensure textures are disposed on unmount |
| Audio Reactivity Stalling | Low | Medium | Keep dual fallback (Web Audio `AnalyserNode` + mutable `jarvisRealtimeRef` + cadence synthesizer) |
| TypeScript compilation failure | Very Low | High | Verify with `npx tsc -p . --noEmit` before and after changes |

---

## Conclusion
The existing visualizer architecture is cleanly isolated to `src/components/dashboard/sphere.tsx` and called only in `src/pages/dashboard.tsx`. Three.js and `@react-three/fiber` are already installed and fully configured. Replacing the current sphere visualizer with the new 3D holographic core visualizer can be achieved cleanly with zero layout regressions, zero new npm dependencies, and full continuity for all application states and events.
