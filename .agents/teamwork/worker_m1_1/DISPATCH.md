# Worker Task Assignment: 3D Holographic Core Visualizer Implementation

Working directory: e:\Projects\J.A.R.V.I.S Electron App
State folder: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1_1\

## Mandatory Inputs (Read these first)
- Original Request: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Project Specification: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\orchestrator_1\PROJECT.md`
- Sub-Orchestrator Scope: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\sub_orch_m1_1\SCOPE.md`
- Explorer 1 (Layers & Geometry): `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_layers_1\report.md`
- Explorer 2 (State Dynamics & Physics): `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_states_1\report.md`
- Explorer 3 (React Integration & Audio): `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_integration_1\report.md`
- Authoritative Source File: `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`
- Existing File to Replace: `e:\Projects\J.A.R.V.I.S Electron App\src\components\dashboard\sphere.tsx`

## MANDATORY INTEGRITY WARNING (Verbatim)
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You exclusively own and may create/modify:
- `src/components/dashboard/holographic-core/types.ts`
- `src/components/dashboard/holographic-core/constants.ts`
- `src/components/dashboard/holographic-core/procedural-textures.ts`
- `src/components/dashboard/holographic-core/geometries.ts`
- `src/components/dashboard/holographic-core/state-machine.ts`
- `src/components/dashboard/holographic-core/audio-bridge.ts`
- `src/components/dashboard/holographic-core/holographic-core-scene.tsx`
- `src/components/dashboard/holographic-core/index.ts`
- `src/components/dashboard/sphere.tsx`

Do NOT touch any other source files unless strictly required for type exports.

## Your Task
Implement the 3D Holographic Core Visualizer with full modular fidelity:
1. `types.ts`: Define `JarvisVisualState` (11 states: `IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`), `HolographicState`, `SphereProps`, `AudioFrequencyBands`, `ParticleShellConfig`, `RingStateConfig`.
2. `constants.ts`: Color palette matching canonical hex codes (`STATE_COLORS`), state configuration records (speed, breathing, morph weights, glow radius, ring angles).
3. `procedural-textures.ts`: Procedural canvas generation for backdrop halo (`createBackdropHaloTexture()`) and volumetric core glow (`createVolumetricGlowTexture()`), returning Three.js `CanvasTexture` instances with correct wrapping and mipmaps.
4. `geometries.ts`: Analytical math for:
   - Fibonacci golden spiral 3D sphere distribution with 3 concentric shells ($0.52, 0.88, 1.20$).
   - Latitude/Longitude globe morph target (12 meridians, 8 parallels).
   - Beveled holo-cube morph target ($0.77$ extent with smooth rounded corner bevels).
   - Torus geometries for rings.
5. `state-machine.ts`: Exponential damping transition engine ($dt \le 0.05$, $damp = 1 - \exp(-6.2 \cdot dt)$), state weight interpolation, cardiac shockwave equation for ALERT and transitions ($f = 1.18\text{ Hz}$ lub-dub), and poloidal toroidal flow for MEMORY_SYNC.
6. `audio-bridge.ts`: 3-band FFT processing (Bass 0-15, Mid 16-55, Treble 56-111 bins) sampling `jarvisRealtimeRef.audioLevel`, `jarvisService.analyser`, prop audio, and autonomous speech cadence generator fallback ($< 0.03$).
7. `holographic-core-scene.tsx`: R3F / Three.js Canvas scene mounting:
   - Layer 1: Contrast Backdrop Halo (`THREE.Sprite`, $z = -0.3$, `renderOrder = 0`)
   - Layer 2: Volumetric Core Glow (`THREE.Sprite`, $z = 0$, `renderOrder = 1`, dynamic breathing scale & opacity)
   - Layer 3: Gyroscopic Rings (Ring 1 & Ring 2 gimbals, Ring 3 scanner/plane, `renderOrder = 2`)
   - Layer 4: Fibonacci Particle Cloud (`THREE.Points`, 2600 points, golden-spiral base, morph targets, 3 shells, `renderOrder = 3`)
   - Pointer drag orbit controls with pitch clamping to $[-60^\circ, +60^\circ]$ ($\pm 1.05\text{ rad}$) and exponential damping.
   - Proper WebGL cleanup and resource disposal on unmount.
8. `index.ts`: Re-export clean public API.
9. `src/components/dashboard/sphere.tsx`: Drop-in replacement wrapper re-exporting `Sphere` as default and named export, handling legacy props with the 6-level arbitration hierarchy, and preserving `React.memo(..., () => true)` behavior while allowing internal reactive updates.
10. Run build and typecheck verification:
    `npx tsc -p . --noEmit`
    Document commands and output in `handoff.md`.


## 2026-11-11T09:30:51Z
You are the Worker agent responsible for implementing Milestone 1: 3D Holographic Core Visualizer Component Replacement.
Working directory: e:\Projects\J.A.R.V.I.S Electron App
Your state folder: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1_1\
