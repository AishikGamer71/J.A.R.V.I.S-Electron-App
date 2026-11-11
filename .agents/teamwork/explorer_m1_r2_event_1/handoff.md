# Handoff Report: Defect D2 CustomEvent Detail Unpacking Investigation

**Agent**: Explorer M1 R2 Event (`explorer_m1_r2_event_1`)  
**Iteration**: 2 (Milestone 1 Remediation)  
**Parent Orchestrator**: `b204d4ed-af14-4d46-bc7b-8d5d589f3895`  
**Date**: November 11, 2026  
**Artifact Report**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_r2_event_1\report.md`  

---

## 1. Observation

1. **Current Event Listener Code**:
   In `src/components/dashboard/holographic-core/holographic-core-scene.tsx` lines 94–98:
   ```typescript
   const handleJarvisState = (e: Event) => {
     const customDetail = (e as CustomEvent).detail
     if (customDetail) {
       realtimeBusState.current = String(customDetail)
     }
   }
   ```

2. **Runtime Render Loop Consumption**:
   In `src/components/dashboard/holographic-core/holographic-core-scene.tsx` lines 174–177:
   ```typescript
   // 1. Resolve active state using 6-level arbitration
   const realtimeVoice = realtimeBusState.current || jarvisRealtimeRef.voiceState
   const active = resolveActiveState(props, realtimeVoice)
   ```

3. **Specification Interface Contract**:
   In `orchestrator_1/PROJECT.md` line 62:
   ```typescript
   window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: HolographicState } }));
   ```

4. **Codebase Dispatched Event Formats**:
   - `src/lib/gateway-client.ts:228, 230, 238`: `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'IDLE' }))` (string primitive).
   - `src/services/hermes-adapter.ts:60, 65, 71`: `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'LISTEN' }))`, `{ detail: 'PROCESSING' }` (string aliases).
   - `src/services/jarvis-voice-ai.ts:245`: `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'SPEAKING' }))` (string primitive).
   - `src/services/jarvisBridge.ts:169`: `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: state }))` (string primitive).
   - `src/components/dashboard/holographic-core/holographic-core-scene.tsx:113`: `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: mapped }))` (string primitive from key mapping).

5. **State Machine Normalization Capabilities**:
   In `src/components/dashboard/holographic-core/state-machine.ts` lines 8–62:
   `normalizeStateName(raw: string | null | undefined): HolographicState | null` resolves all 11 canonical states, aliases (`LISTEN` $\to$ `LISTENING`, `PROCESSING` $\to$ `THINKING`, `ERROR` $\to$ `ALERT`, `STANDBY` $\to$ `IDLE`), and trims whitespace, but returns `null` if given non-strings or unmapped strings like `"[object Object]"`.

---

## 2. Logic Chain

1. **Object Payload Conversion Defect (Supported by Observations 1 & 3)**:
   - When a caller dispatches `new CustomEvent('jarvis-state', { detail: { state: 'ALERT' } })` per `PROJECT.md` line 62, `customDetail` is `{ state: 'ALERT' }`.
   - Executing `String(customDetail)` converts this object to the string primitive `"[object Object]"`.

2. **Cascading State Shadowing and Lockout (Supported by Observations 2 & 5)**:
   - Because `"[object Object]"` is a non-empty string, it is truthy.
   - At line 175 of `holographic-core-scene.tsx`: `realtimeBusState.current || jarvisRealtimeRef.voiceState` resolves to `"[object Object]"`, permanently shadowing `jarvisRealtimeRef.voiceState`.
   - `resolveActiveState(props, "[object Object]")` calls `normalizeStateName("[object Object]")`, which returns `null`.
   - In the absence of explicit props, priority arbitration drops to Level 6 (`IDLE`).
   - Consequently, dispatching an object event fails to set the desired state and breaks voice telemetry synchronization.

3. **Multi-Format Interoperability Requirement (Supported by Observation 4)**:
   - Several services (`hermes-adapter.ts`, `gateway-client.ts`, `jarvisBridge.ts`) dispatch string primitives and aliases (`PROCESSING`, `LISTEN`), while `PROJECT.md` specifies object payloads `{ state: HolographicState }`.
   - The fix must support both formats without regressing existing string dispatchers.

4. **Safe Unpacking and Immediate Normalization (Supported by Observations 1, 2, & 5)**:
   - Extracting candidates across standard keys (`state`, `voiceState`, `status`, `value`, `name`, `mode`, `payload`, `detail`) and validating them through `normalizeStateName` guarantees that `realtimeBusState.current` is only updated with valid canonical `HolographicState` values.
   - Malformed or unrecognized payloads return `null` and do not overwrite `realtimeBusState.current`, preventing voice ref shadowing.
   - Explicit reset signals (`{ reset: true }` or `{ state: null }`) safely restore `realtimeBusState.current` to `null`.

---

## 3. Caveats

1. **Other Event Listeners in Workspace**:
   `src/components/dashboard/mini-overlay.tsx` line 46 checks `if (e.detail === 'SPEAKING')`. When application dispatchers transition fully to object payloads in Milestone 2, `mini-overlay.tsx` will also need updating. This is documented for Milestone 2.
2. **Key Shortcut Dispatching**:
   Keyboard hotkeys in `holographic-core-scene.tsx` currently dispatch `{ detail: mapped }` (string). With the proposed unpacking logic, this continues to function flawlessly without modification.
3. **No other caveats**.

---

## 4. Conclusion

Defect D2 is caused by blind stringification `String(customDetail)` in `holographic-core-scene.tsx:97`. 

### Remediation Plan:
1. Import `normalizeStateName` from `./state-machine` into `holographic-core-scene.tsx`.
2. Introduce a safe unpacking function `unpackJarvisStateDetail(detail: unknown, depth = 0): HolographicState | null` that inspects strings, `{ state }`, common key aliases, nested wrappers, and cycles up to depth 3.
3. Update `handleJarvisState` in `holographic-core-scene.tsx`:
   ```typescript
   const handleJarvisState = (e: Event) => {
     const customDetail = (e as CustomEvent).detail
     if (!customDetail) return

     if (
       typeof customDetail === 'object' &&
       ('reset' in customDetail || ('state' in customDetail && (customDetail as Record<string, unknown>).state === null))
     ) {
       realtimeBusState.current = null
       return
     }

     const unpacked = unpackJarvisStateDetail(customDetail)
     if (unpacked) {
       realtimeBusState.current = unpacked
     }
   }
   ```
4. Full architectural analysis, code snippets, diffs, and Vitest test cases are documented in `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_r2_event_1\report.md`.

---

## 5. Verification Method

1. **Unit Test Verification**:
   Execute the Vitest lifecycle suite:
   ```powershell
   npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts
   ```
   *Expected Result*: All tests pass (including new unpacking assertions).

2. **TypeScript Typecheck**:
   ```powershell
   npx tsc -p . --noEmit
   ```
   *Expected Result*: Exits with code 0, 0 errors.

3. **Event Payload Simulation**:
   Dispatch the following events in a browser/node test environment:
   ```typescript
   window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'ALERT' } }))
   window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'THINKING' }))
   window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'LISTEN' } }))
   window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { reset: true } }))
   ```
   *Expected Result*: State seamlessly resolves to `ALERT`, `THINKING`, `LISTENING`, and resets to `null`/voice baseline respectively.
