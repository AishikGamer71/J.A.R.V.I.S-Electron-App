# Explorer Task Assignment: React Integration, Dashboard Bridge & Audio Reactivity

Working directory: e:\Projects\J.A.R.V.I.S Electron App
State folder: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_integration_1\

## Mandatory Inputs (Read these first)
- Original Request: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Project Specification: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\orchestrator_1\PROJECT.md`
- Sub-Orchestrator Scope: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\sub_orch_m1_1\SCOPE.md`
- UI Survey Report: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_ui_survey_1\report.md`
- Existing Component: `e:\Projects\J.A.R.V.I.S Electron App\src\components\dashboard\sphere.tsx`
- Dashboard Consumer: `e:\Projects\J.A.R.V.I.S Electron App\src\pages\dashboard.tsx`
- Realtime Service / Audio sources: `e:\Projects\J.A.R.V.I.S Electron App\src\services\jarvis-realtime.ts` (and related audio hooks)

## Mission
Investigate the React integration, audio reactivity, and backward compatibility requirements:
1. Examine `src/components/dashboard/sphere.tsx` and `src/pages/dashboard.tsx` to document all existing props, parent container styling, size constraints, and lifecycle behavior.
2. Design the drop-in replacement interface for `sphere.tsx` that maps legacy props (`isListening`, `isSpeaking`, `isThinking`, `audioLevel`) to the 11-state model while allowing explicit state overriding.
3. Audio reactivity bridge design:
   - Zero-re-render audio updates (via ref rather than React state to maintain 60 FPS).
   - 3-band FFT processing (bass, mid, treble) or scalar audio level scaling.
   - AnalyserNode direct connection support + fallback autonomous speech cadence generator when speaking without direct audio stream.
4. Pointer interaction: orbit drag rotation with pitch clamping (-60° to +60°) and auto-return or gentle damping.
5. Canvas lifecycle: WebGL context creation, resize observer, cleanup/dispose on unmount (geometries, materials, textures, cancelAnimationFrame) to prevent memory leaks in Electron.
6. Check dependencies in `package.json` (three version, @types/three, etc.).

Write your comprehensive findings and blueprint to `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_integration_1\report.md` and deliver your handoff.
