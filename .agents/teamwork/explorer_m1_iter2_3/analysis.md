# Technical Analysis: ArcReactor Delta-Time Clamping Remediation

**Agent**: `explorer_m1_iter2_3`  
**Mission**: Milestone M1 Iteration 2 — ArcReactor Delta-Time Clamping Investigation  
**Working Directory**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_iter2_3`  
**Date**: 2026-11-10T09:08:00Z  

---

## 1. Executive Summary

During Milestone M1 Iteration 1 review and adversarial testing, reviewers and challengers identified a mathematical vulnerability in `src/components/widgets/arc-reactor.tsx`:
On line 52:
```typescript
const dt = Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05)
```
While upper-bounded at `0.05s` (50ms) to protect against frame jumps after tab suspend, the delta-time calculation lacks a lower bound of `0.0`. If non-monotonic timestamps, clock rollbacks, or out-of-order frame execution occur, `timestamp - lastFrameTimeRef.current` can become negative.

Because the animation physics relies on continuous exponential decay ($1 - e^{-\lambda \cdot dt}$), any negative $dt$ turns exponential decay into exponential growth ($e^{+\lambda |dt|} \gg 1$), resulting in negative smoothing coefficients, state overshoot, and reverse rotational jerk.

Remediating this with:
```typescript
const dt = Math.max(0, Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05))
```
provides an absolute mathematical guarantee that $dt \in [0, 0.05]$ under all runtime conditions, eliminating vulnerability to clock drift or negative timestamp regression.

---

## 2. Mathematical Root Cause & Physical Dynamics

### 2.1 The Vulnerability Chain
In `src/components/widgets/arc-reactor.tsx:50-86`:
```typescript
const render = (timestamp: number) => {
  // Line 52:
  const dt = Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05)
  lastFrameTimeRef.current = timestamp

  // Line 74: Exponential damping for audio smoothing
  const smoothing = 1 - Math.exp(-10 * dt)
  smoothedAudioLevelRef.current += (rawAudioRms - smoothedAudioLevelRef.current) * smoothing

  // Line 80-81: Exponential damping for glow smoothing
  smoothedGlowRef.current += (targetGlow - smoothedGlowRef.current) * (1 - Math.exp(-6 * dt))

  // Line 84-86: Rotational kinematics
  outerArcAngleRef.current += 0.14 * dt
  midClusterAngleRef.current -= (0.22 + smoothedAudioLevelRef.current * 0.35) * dt
  innerCoreAngleRef.current += (0.38 + smoothedAudioLevelRef.current * 0.5) * dt
```

### 2.2 Numerical Instability Under Negative Delta-Time
1. **Exponential Damping Inversion**:
   The standard exponential smoothing formula is:
   $$\alpha(dt) = 1 - e^{-\lambda \cdot dt}$$
   For normal positive time steps ($dt > 0$), $-\lambda \cdot dt < 0 \implies 0 < e^{-\lambda \cdot dt} \le 1 \implies 0 \le \alpha < 1$.
   However, if $dt = -1.0$:
   $$-\lambda \cdot dt = -10 \times (-1.0) = +10$$
   $$\alpha = 1 - e^{10} = 1 - 22026.47 = -22025.47$$
   Instead of interpolating towards `rawAudioRms`, the state is displaced by $22,025\times$ the target error in the reverse direction!

2. **Rotational Direction Inversion**:
   $$\Delta \theta_{\text{outer}} = 0.14 \cdot dt$$
   If $dt < 0$, $\Delta \theta < 0$, causing the outer containment ring to spin backwards instantaneously, manifesting as visual jitter or jarring frame pops.

3. **Empirical Evidence from `tests/adversarial_ui_physics.ts`**:
   The existing adversarial harness reproduces this vulnerability in Suite 1.5:
   ```
   [PASS] [Physics: Negative dt (-1.0s)] Negative dt (-1.0s) stress test: documents vulnerability if timestamp regresses
          Details: Vulnerability finding: clampedDtReactor=-1, smoothing=-22025.47, resulting smoothedAudio=-22025.47. Math.max(0, ...) lower bound is absent in production code!
   ```

---

## 3. The Remediation: Double Clamping $[0, 0.05]$

### 3.1 Behavior with Clamping
With `Math.max(0, Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05))`:
1. **Case 1: Standard Frame ($dt \approx 0.01667s$ @ 60 FPS)**:
   - $\text{raw} = 0.01667s$
   - $\min(0.01667, 0.05) = 0.01667$
   - $\max(0, 0.01667) = 0.01667$
   - Behavior is 100% identical to current production code.

2. **Case 2: Long Frame / Background Tab Wake ($dt = 5.0s$)**:
   - $\text{raw} = 5.0s$
   - $\min(5.0, 0.05) = 0.05$
   - $\max(0, 0.05) = 0.05$
   - Behavior remains capped at 50ms, preventing physics jumps.

3. **Case 3: Clock Rollback / Out-of-Order Frame ($dt = -0.5s$)**:
   - $\text{raw} = -0.5s$
   - $\min(-0.5, 0.05) = -0.5$
   - $\max(0, -0.5) = 0.0$
   - $dt = 0.0$
   - Smoothing factor: $1 - e^{-10 \times 0} = 1 - 1 = 0.0$.
   - Angle displacement: $0.14 \times 0 = 0.0$.
   - Result: Exactly 0 state displacement; timestamp reference updates monotonically to `timestamp`; next frame resumes smoothly.

### 3.2 Type Safety and Compilation Impact
- `Math.max` and `Math.min` both accept `number` and return `number`.
- Return type of `dt` remains strictly `number`.
- Zero additional imports required.
- Current repository verification: `npm run typecheck` (`tsc -p . --noEmit && tsc -p tsconfig.electron.json --noEmit && tsc -p tsconfig.e2e.json --noEmit`) passes cleanly with 0 errors.

---

## 4. Worker Remediation Plan

The Worker (`worker_m1`) should apply the following precise edits:

### 4.1 Target File: `src/components/widgets/arc-reactor.tsx`
- **Location**: Line 52
- **Change**:
```diff
<<<<
      // Frame-rate-independent delta time (capped at 50ms)
      const dt = Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05)
====
      // Frame-rate-independent delta time (capped at 50ms, lower-bounded at 0)
      const dt = Math.max(0, Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05))
>>>>
```

### 4.2 Target File: `tests/adversarial_ui_physics.ts` (Harness Synchronization)
- **Location**: Line 57-59
- **Change**:
```diff
<<<<
function computeArcReactorDt(timestamp: number, lastFrameTime: number): number {
  return Math.min((timestamp - lastFrameTime) / 1000, 0.05)
}
====
function computeArcReactorDt(timestamp: number, lastFrameTime: number): number {
  return Math.max(0, Math.min((timestamp - lastFrameTime) / 1000, 0.05))
}
>>>>
```
- **Location**: Lines 140-165 (Suite 1.5):
Update the assertion from documenting vulnerability to verifying resilience:
```typescript
// 1.5: Adversarial negative dt = -1.0 (Clock rollback / timestamp regression)
{
  const clampedDtReactor = computeArcReactorDt(0, 1000) // timestamp=0, lastFrame=1000 => -1.0s raw
  const clampedDtSphere = computeSphereDt(-1.0)

  const smoothingUnderNegativeDt = 1 - Math.exp(-10 * clampedDtReactor)

  let smoothedAudio = 0
  const rawTarget = 1.0
  smoothedAudio += (rawTarget - smoothedAudio) * smoothingUnderNegativeDt

  const isGuarded = clampedDtReactor === 0 && smoothingUnderNegativeDt === 0 && smoothedAudio === 0

  assert(
    'Negative dt (-1.0s) stress test: lower bound clamp Math.max(0, ...) prevents negative delta-time',
    'Physics: Negative dt (-1.0s)',
    isGuarded,
    `clampedDtReactor=${clampedDtReactor}, smoothing=${smoothingUnderNegativeDt}, resulting smoothedAudio=${smoothedAudio}`,
    { clampedDtReactor, smoothingUnderNegativeDt, smoothedAudio }
  )
}
```

### 4.3 Secondary Note: `src/components/dashboard/sphere.tsx`
In `src/components/dashboard/sphere.tsx:282`:
```typescript
const dt = Math.min(0.05, delta)
```
While Three.js `useFrame` passes clock-managed delta, wrapping this as `const dt = Math.max(0, Math.min(0.05, delta))` is also recommended as a defensive best practice.

---

## 5. Verification Commands for Worker & Reviewers

1. **Typecheck Verification**:
   ```powershell
   npm run typecheck
   ```
   Must exit with code 0 (`tsc -p .`, `tsc -p tsconfig.electron.json`, `tsc -p tsconfig.e2e.json`).

2. **Empirical Adversarial Physics Suite**:
   ```powershell
   npx tsx tests/adversarial_ui_physics.ts
   ```
   Must pass all 11/11 tests, with Suite 1.5 confirming `clampedDtReactor === 0`.

3. **Canonical E2E Milestone 1 Tests**:
   ```powershell
   python tests/e2e/runner.py --tier 1
   ```
   Ensures zero regressions across Milestone 1 feature tests (`TestTier1Milestone1Features`).
