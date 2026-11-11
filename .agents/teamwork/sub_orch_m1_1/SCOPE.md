# Scope: Milestone 1 - 3D Holographic Core Visualizer Component Replacement

## Architecture
Modular 3D visualization subsystem replacing `src/components/dashboard/sphere.tsx` with a high-fidelity 11-state Three.js engine based on `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`.

### Package & Module Layout:
- `src/components/dashboard/holographic-core/types.ts`: TypeScript definitions for the 11 states, color palettes, layer parameters, audio reactive metrics, component props.
- `src/components/dashboard/holographic-core/constants.ts`: Color definitions, default state configurations, geometry constants, animation constants.
- `src/components/dashboard/holographic-core/procedural-textures.ts`: Procedural canvas generation for halo backdrop and volumetric glow sprites with radial alpha gradients and GPU cleanup.
- `src/components/dashboard/holographic-core/geometries.ts`: Math for 3D Fibonacci sphere (golden spiral, 2600 points), latitude/longitude globe morph targets, beveled holo-cube morph targets, ring geometries.
- `src/components/dashboard/holographic-core/state-machine.ts`: Exponential damping engine (`damp = 1 - Math.exp(-6.2 * dt)`), 6-level priority arbitration, cardiac shockwave engine ($f = 1.18\text{ Hz}$ lub-dub), state transition pulse tracker, toroidal poloidal flow.
- `src/components/dashboard/holographic-core/audio-bridge.ts`: 3-band FFT analyzer integration with zero-re-render bridge via `jarvisRealtimeRef.audioLevel`, direct AudioContext AnalyserNode support, and speech cadence fallback.
- `src/components/dashboard/holographic-core/holographic-core-scene.tsx`: Core Three.js Canvas/WebGL lifecycle manager, 4 visual layers, pointer drag orbit rotation with pitch clamping, animation render loop.
- `src/components/dashboard/holographic-core/index.ts`: Public API export.
- `src/components/dashboard/sphere.tsx`: Drop-in wrapper maintaining full backward compatibility with `src/pages/dashboard.tsx`.

## Feature Inventory
| # | Feature | Description | Milestone | Status |
|---|---------|-------------|-----------|--------|
| 1 | Layer 1: Contrast Backdrop Halo | Procedural dark radial gradient sprite billboard behind core (`z = -0.3`, `renderOrder = 0`) | M1 | DONE |
| 2 | Layer 2: Volumetric Core Glow | Procedural radial gradient glow sprite with breathing and state damping (`renderOrder = 1`) | M1 | DONE |
| 3 | Layer 3: Gyroscopic & Scanner Rings | Ring 1 outer tilted, Ring 2 counter-rotating inner, Ring 3 vision scan laser plane (`renderOrder = 2`) | M1 | DONE |
| 4 | Layer 4: Fibonacci Particle Cloud | 3D Fibonacci golden-spiral particle cloud ($N=2600$) with 3 shells and morph targets (globe, cube) (`renderOrder = 3`) | M1 | DONE |
| 5 | Cardiac Shockwave | Shockwave pulse on state transition and ALERT twin-beat lub-dub ($f = 1.18\text{ Hz}$) | M1 | DONE |
| 6 | Toroidal & Morphing Dynamics | Particle flow along torus in MEMORY_SYNC, globe morph in WEB_SEARCH, cube morph in CODING | M1 | DONE |
| 7 | 11-State Exponential Transition Engine | Smooth damping transition across all 11 states ($damp = 1 - \exp(-6.2 \cdot dt)$) with canonical colors | M1 | DONE |
| 8 | 3-Band Audio Reactivity Bridge | Bass/mid/treble frequency analysis with zero-re-render ref bridge and cadence fallback | M1 | DONE |
| 9 | Interactive Orbit Controls | Pointer drag orbit rotation with pitch clamping (-60° to +60° / $\pm 1.05\text{ rad}$) | M1 | DONE |
| 10 | Drop-in Dashboard Compatibility | Seamless compatibility with `src/pages/dashboard.tsx` props and container | M1 | DONE |
| 11 | TypeScript Cleanliness | Zero `tsc --noEmit` errors across the entire project | M1 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1.1 | Exploration & Architecture | Survey source HTML, map math/shaders/canvas to React Three.js, map dashboard.tsx props | none | DONE |
| 1.2 | Implementation | Implement modular files under `holographic-core/` and update `sphere.tsx` | 1.1 | DONE |
| 1.3 | Review & Verification | Code review, challenger tests, forensic audit, build verification | 1.2 | DONE |

## Interface Contracts
### `src/components/dashboard/sphere.tsx` ↔ `src/pages/dashboard.tsx`
- Preserves all props currently expected by dashboard:
  - `isListening?: boolean`
  - `isSpeaking?: boolean`
  - `isThinking?: boolean`
  - `state?: HolographicState | string` (optional override)
  - `audioLevel?: number`
  - `className?: string`
- Maps legacy state props to the 11 Holographic states cleanly when explicit state is not passed.
