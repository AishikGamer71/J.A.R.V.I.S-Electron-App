# Handoff Report — UI Visualizer Survey & 3D Holographic Core Integration

## 1. Observation
1. **Component Locations**:
   - `src/components/dashboard/sphere.tsx` (lines 1-761): Contains the active React Three Fiber (`@react-three/fiber`) particle sphere visualizer exporting `Sphere` (default and named) and `JarvisVisualState`. It implements 11 visual states with particle displacement morphing (Fibonacci distribution, globe, cube, shells, rings, shockwave), procedural canvas textures, and a `React.memo(SphereComponent, () => true)` wrapper.
   - `src/components/widgets/arc-reactor.tsx` (lines 1-265): Defines a 2D HTML5 canvas `ArcReactor` component. A global search across `src/` for `ArcReactor` and `arc-reactor` confirmed zero imports and zero usages anywhere in the codebase.
   - `src/components/dashboard/particle-network.tsx` (lines 1-155): 2D background canvas used in `src/IndexRoot.tsx:209` as a background layer.

2. **Call Sites in Application**:
   - A recursive search of all `.ts` and `.tsx` files in `src/` revealed that `Sphere` is imported and rendered in **exactly one file**: `src/pages/dashboard.tsx`.
   - In `src/pages/dashboard.tsx`:
     - Line 6: `import Sphere from '@/components/dashboard/sphere'`
     - Line 606 (Focus Mode): `<div className="w-[84vmin] h-[84vmin] max-w-[95vw] max-h-[95vh] flex items-center justify-center pointer-events-none"><Sphere /></div>`
     - Line 695 (Normal Dashboard Mode, center column): `<div className="w-[60vh] h-[60vh] max-w-full transition-all duration-1000 ${isSystemActive ? 'opacity-100 scale-100' : 'opacity-85 scale-90 grayscale'} pointer-events-none"><Sphere /></div>`
   - No other tabs (Workspace, Modules, Phone, Task Manager, Apps, Notes, Settings, Gallery, Terminal) import or render `Sphere`.

3. **Dependencies & Typecheck**:
   - In `package.json`:
     - Line 93: `"@react-three/drei": "^10.7.7"`
     - Line 94: `"@react-three/fiber": "^9.6.1"`
     - Line 166: `"three": "^0.180.0"`
   - `node_modules/@types/three` exists.
   - `npx tsc -p . --noEmit` executed cleanly with exit code 0 and zero errors.
   - `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html` uses native Three.js materials (`THREE.PointsMaterial`, `THREE.SpriteMaterial`, `THREE.MeshBasicMaterial`) with `AdditiveBlending` and canvas textures; no postprocessing libraries are required.

4. **WebGL Lifecycle & Sizing**:
   - Rendered using `@react-three/fiber` `<Canvas className="w-full h-full" camera={{ position: [0, 0, 5.1], fov: 58 }} dpr={[1, 1.5]} ...>`.
   - Sizing is managed automatically by R3F's built-in `ResizeObserver` matching container bounds.
   - Textures (`glowTexture`, `backdropTexture`) are disposed on unmount in `useEffect` cleanup.
   - Parent re-renders (such as 1 Hz stats polling in `jarvis-layout.tsx`) do not trigger canvas re-initialization due to `React.memo(SphereComponent, () => true)`.

5. **State & Event Integration**:
   - `src/services/jarvisBridge.ts:162-170`: Reads `audioLevel` and `voiceState`, updates mutable ref `jarvisRealtimeRef`, and dispatches `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: state }))`.
   - `src/lib/gateway-client.ts:228, 375, 387, 390`: Dispatches `jarvis-state` on `agent.state`, TTS start (`SPEAKING`), TTS completion (`IDLE`), and speech cancellation (`IDLE`).
   - `src/services/hermes-adapter.ts:69, 81, 94`: Dispatches `SPEAKING`, `LISTEN`, and `PROCESSING`.
   - `src/services/jarvis-voice-ai.ts:97`: Dispatches `SPEAKING` on wake word detection.
   - Keyboard hotkeys (`1`-`9`, `0`, `-`) toggle states when not focused in input elements.

---

## 2. Logic Chain
1. **Scope of Visualizer Replacement**:
   - Based on Observation 1 & 2, `src/components/dashboard/sphere.tsx` is the single active core visualizer in the application, and `src/pages/dashboard.tsx` is its only consumer.
   - `src/components/widgets/arc-reactor.tsx` is orphaned and does not require migration or replacement.
   - Therefore, replacing the sphere visualizer requires modifying/replacing `src/components/dashboard/sphere.tsx` and requires zero modifications to navigation or other tabs.

2. **Package Stability**:
   - Based on Observation 3, Three.js and `@react-three/fiber` are already installed and fully typed (`three` ^0.180.0, `@react-three/fiber` ^9.6.1, `@react-three/drei` ^10.7.7).
   - The visualizer code in `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html` does not require external postprocessing packages.
   - Therefore, no packages need to be installed or modified in `package.json`.

3. **Zero-Regression Guarantee**:
   - Based on Observation 2 & 4, `src/pages/dashboard.tsx` passes no props to `<Sphere />` and relies on container sizing (`60vh` and `84vmin`) with `pointer-events-none`.
   - By retaining the export contract (`default`, `Sphere`, `JarvisVisualState`, `ParticleSphereProps`) in `src/components/dashboard/sphere.tsx`, the dashboard layout and behavior remain completely regression-free.
   - By preserving `React.memo(..., () => true)`, parent layout 1 Hz polling ticks will not trigger WebGL context remounts.

4. **Event & Audio Continuity**:
   - Based on Observation 5, application events use `jarvis-state` custom events, `jarvisRealtimeRef` mutable store, and `jarvisService?.analyser`.
   - Retaining these three communication pathways inside the new visualizer ensures smooth transitions between all 11 states and live audio synchronization.

---

## 3. Caveats
- The HTML source file includes pointer drag rotation (`pointerdown`/`pointermove`/`pointerup` on `rootGroup`). In the Electron app, the normal dashboard container applies `pointer-events-none` to allow clicking dashboard controls. Orbit drag should be enabled conditionally (e.g. in Focus Mode or via an `interactive` prop) to avoid capturing clicks intended for dashboard widgets.
- No other visualizer files were identified outside `src/components/dashboard/sphere.tsx` and the orphaned `src/components/widgets/arc-reactor.tsx`.

---

## 4. Conclusion
The existing sphere visualizer in `src/components/dashboard/sphere.tsx` can be cleanly upgraded to the canonical 3D holographic core visualizer from `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`. All required Three.js packages are already installed, layout boundaries are strictly isolated to `src/pages/dashboard.tsx`, and state/audio bridges are thoroughly mapped. The recommended implementation structure is a modular directory `src/components/dashboard/holographic-core/` with `src/components/dashboard/sphere.tsx` as a backwards-compatible export wrapper.

---

## 5. Verification Method
1. **Typecheck Verification**:
   ```powershell
   npx tsc -p . --noEmit
   ```
   Must exit with code 0.
2. **Visualizer Import Verification**:
   ```powershell
   Get-ChildItem -Path src -Recurse -Include *.ts,*.tsx | Select-String -Pattern "components/dashboard/sphere"
   ```
   Confirms only `src/pages/dashboard.tsx` imports the module.
3. **Application Build & Launch**:
   ```powershell
   npm run build
   ```
   Ensure build completes without shader compilation or bundling errors.
4. **State Transition Test**:
   In the running app, press keys `1` through `9`, `0`, and `-` to verify visual transition across all 11 states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`).
