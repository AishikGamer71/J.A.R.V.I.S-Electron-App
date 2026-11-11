# Handoff Report: Milestone 2 — Visualizer State & Event Wiring Investigation

**Agent**: Explorer 2 (`explorer_m2_2`)  
**Parent Agent ID**: `6b8fe7dc-259c-49f7-b0b6-2f959f447b00`  
**Milestone**: Milestone 2 (Visualizer State & Event Wiring)  
**Date**: November 11, 2026  
**Type**: Hard Handoff (Investigation Complete)  

---

## 1. Observation

1. **Visualizer Mount Locations in Dashboard**:
   - In `src/pages/dashboard.tsx` line 606:
     ```tsx
     <div className="w-[84vmin] h-[84vmin] max-w-[95vw] max-h-[95vh] flex items-center justify-center pointer-events-none">
       <Sphere />
     </div>
     ```
   - In `src/pages/dashboard.tsx` line 695:
     ```tsx
     <div
       className={`w-[60vh] h-[60vh] max-w-full transition-all duration-1000 ${isSystemActive ? 'opacity-100 scale-100' : 'opacity-85 scale-90 grayscale'} pointer-events-none`}
     >
       <Sphere />
     </div>
     ```
   Both call sites instantiate `<Sphere />` without passing props.

2. **Isolated Tool State in Dashboard**:
   - In `src/pages/dashboard.tsx` lines 375–389:
     ```tsx
     const [activeTool, setActiveTool] = useState<{ tool: string; phase: 'start' | 'result' } | null>(null)
     useEffect(() => {
       const handleTool = (e: any) => {
         if (e.detail) {
           setActiveTool({ tool: e.detail.tool, phase: e.detail.phase })
           if (e.detail.phase === 'result') {
             setTimeout(() => setActiveTool(null), 3000)
           }
         }
       }
       window.addEventListener('jarvis-tool-call', handleTool)
       return () => window.removeEventListener('jarvis-tool-call', handleTool)
     }, [])
     ```
     `activeTool` is tracked locally for chat badges (line 739) but is never passed to `<Sphere />`.
   - In `src/lib/gateway-client.ts` lines 259–274: `tool.start` and `tool.result` dispatch only `CustomEvent('jarvis-tool-call', ...)` and do not dispatch `jarvis-state`.

3. **Current Priority Arbitration Order in Milestone 1**:
   In `src/components/dashboard/holographic-core/state-machine.ts` lines 73–114:
   - Level 1: `props.overrideState ?? props.state`
   - Level 2: `props.error` -> `ALERT`
   - Level 3: `props.activeTool` -> tools (`WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`)
   - Level 4: `props.isSpeaking` -> `SPEAKING`, `props.isThinking` -> `THINKING`, `props.isListening` -> `LISTENING`
   - Level 5: `realtimeVoiceState` -> event bus
   - Level 6: Fallback to `'IDLE'`
   In this implementation, `activeTool` sits above `isSpeaking`, which inverts the required hierarchy where `SPEAKING` must override `ACTIVE_TOOL`.

4. **Keyboard Shortcuts & Guard Gaps**:
   In `src/components/dashboard/holographic-core/holographic-core-scene.tsx` lines 105–120:
   ```tsx
   const handleKeyDown = (e: KeyboardEvent) => {
     if (
       e.target &&
       (e.target instanceof HTMLInputElement ||
         e.target instanceof HTMLTextAreaElement ||
         e.target instanceof HTMLSelectElement)
     ) {
       return
     }
     const mapped = KEY_STATE_MAP[e.key]
     if (mapped) {
       realtimeBusState.current = mapped
       window.dispatchEvent(new CustomEvent('jarvis-state', { detail: mapped }))
     }
   }
   ```
   Directly observed vulnerabilities:
   - Does not guard against `isContentEditable` or `closest('[contenteditable]')`.
   - Does not check `e.ctrlKey`, `e.altKey`, or `e.metaKey`, allowing shortcuts such as `Ctrl+-` (zoom out) or `Ctrl+1` (switch tab) to trigger state transitions.

5. **Audio Reactivity and TTS Gap**:
   - In `src/components/dashboard/holographic-core/audio-bridge.ts` lines 41–58: `jarvisService.analyser` samples live microphone input.
   - In `src/lib/gateway-client.ts` lines 378–404: `playTtsAudio` creates an HTML5 `new Audio(...)` element and plays it directly without connecting to `AudioContext` or updating `jarvisRealtimeRef.audioLevel`.
   - Consequently, during TTS playback, `totalRaw < 0.03` and the visualizer relies entirely on the autonomous harmonic speech cadence simulation fallback (`audio-bridge.ts` line 75).

6. **Test Baseline Status**:
   - Command: `npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`
   - Result: 27 passed out of 27 tests (1668ms).

---

## 2. Logic Chain

1. **State Ingestion Problem**:
   Because both `<Sphere />` instances in `src/pages/dashboard.tsx` (Observation 1) receive no props, the visualizer relies entirely on internal event listeners and `jarvisRealtimeRef` (Observation 1, Observation 2). Therefore, a centralized state engine and hook (`useVisualizerState` or a coordinated event router) must mediate state changes so that tools, agent states, speech, and vision update both instances identically without requiring custom prop wiring at every dashboard call site.

2. **Priority Resolution Inversion**:
   Observation 3 shows that `activeTool` was previously evaluated at Level 3, ahead of `isSpeaking` at Level 4. In production, conversational agents often continue background tool tasks while speaking the response to the user. To present a natural voice interface, `SPEAKING` must override `ACTIVE_TOOL`. Furthermore, visual inspection (`VISION_SCAN`) takes precedence over normal speech and tools, and `ALERT` takes precedence over everything.
   Hence, the revised priority order must strictly follow:
   $$\text{ALERT} > \text{VISION\_SCAN} > \text{SPEAKING} > \text{ACTIVE\_TOOL} > \text{THINKING} > \text{LISTENING} > \text{IDLE}$$

3. **Lifecycle Timing & Dwell Times**:
   Tools emit discrete `start` and `result` events (Observation 2). If the visualizer transitions immediately to `IDLE` upon `tool.result`, the user does not perceive the geometric transformation (globe rotation, shell splitting, matrix rain). Introducing a 2000ms post-result dwell time ensures perceptual clarity. Introducing a 20000ms safety timeout ensures that orphaned tool calls do not leave the core stuck in tool mode.

4. **Hotkey Guard Hardening**:
   Observation 4 shows that pressing `Ctrl+-` or `Cmd+1` fires the hotkey handler because modifier keys are not checked, and rich text editors are not protected. Adding `e.ctrlKey || e.altKey || e.metaKey` and `target.isContentEditable || target.closest('[contenteditable]')` completely eliminates hotkey collision without affecting canvas testing.

5. **Audio Level Reactivity**:
   Observation 5 establishes that `playTtsAudio` does not pipe playback energy into `jarvisRealtimeRef.audioLevel`. By adding an amplitude analysis loop during TTS playback and routing through `jarvisRealtimeRef.audioLevel`, the visualizer core will dynamically expand and pulse to actual assistant speech volume in real time.

---

## 3. Caveats

1. **Web Audio Autoplay Policy**: Modern browsers restrict `AudioContext` until the user performs a user-gesture click. The visualizer contains an autonomous harmonic speech cadence generator fallback that seamlessly activates if `AudioContext` is suspended or inactive.
2. **Concurrent Multi-Tools**: If multiple tools execute concurrently in backend parallel workers (`ToolDispatcher.dispatch_batch`), the arbitrator selects the highest-priority tool or the most recently started tool until all concurrent tools have resolved.
3. **No Direct Source Changes Made**: As an Explorer agent operating in read-only mode, no files outside `.agents/teamwork/explorer_m2_2/` were modified. Complete implementation blueprints and code patches have been delivered in `report.md`.

---

## 4. Conclusion

The investigation is complete and provides an actionable blueprint for Milestone 2:
1. **State Arbitration**: Standardize on the 7-level hierarchy `ALERT > VISION_SCAN > SPEAKING > ACTIVE_TOOL > THINKING > LISTENING > IDLE`.
2. **Lifecycle Timers**: Implement 2000ms tool dwell, 20s hang fallback timeout, 4000ms alert dwell, and 350ms speech decay.
3. **Polymorphic Payloads**: Unify `jarvis-state` handling via `unpackJarvisStateDetail` to support both `{ detail: { state: HolographicState } }` and string primitives.
4. **Guarded Hotkeys**: Enforce modifier key checks (`!e.ctrlKey && !e.altKey && !e.metaKey`) and `contenteditable`/form checks for keys `1`–`0` and `-`.
5. **TTS Audio Piping**: Pipe assistant playback amplitude into `jarvisRealtimeRef.audioLevel` to drive 60 FPS zero-re-render pulsing.

---

## 5. Verification Method

To independently verify the investigation findings and test the blueprints:

1. **Run Existing Holographic Core Lifecycle Tests**:
   ```powershell
   npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts
   ```
   *Expected result*: 27 passed (100%).

2. **Verify TypeScript Workspace Compilation**:
   ```powershell
   npm run typecheck
   ```
   *Expected result*: Exits with code 0 across all tsconfig targets.

3. **Verify Production Build**:
   ```powershell
   npx vite build
   ```
   *Expected result*: Exits with code 0 in ~4-5s.

4. **Inspect Detailed Technical Report**:
   ```powershell
   Get-Content "e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_2\report.md"
   ```
