# Analysis: Milestone M1 Work Item 5 — UI Arc-Reactor & Visualizer Tuning Strategy

## 1. Executive Summary

Milestone M1 Work Item 5 requires tuning the central holographic visualizer and establishing `src/components/widgets/arc-reactor.tsx` with `JARVIS_LIGHTING_CONFIG` and delta-time animation physics, cleanly bridged into `src/components/dashboard/sphere.tsx` while strictly preserving UI immutability across all other components.

Key findings:
1. `src/components/widgets/arc-reactor.tsx` does not currently exist in the repository.
2. The current visualizer in `src/components/dashboard/sphere.tsx` renders a 3D Three.js particle sphere using a cold cyan/teal color palette (`#67e8f9`, `#00f0ff`, and blue backdrop gradient `rgba(2, 8, 22, 0.88)`).
3. Neither `src/layouts/jarvis-layout.tsx` nor `src/services/theme-manager.ts` contain any legacy Ultron controls or upper buttons (verified by exhaustive AST/text scans).
4. `src/pages/dashboard.tsx` mounts `<Sphere />` from `@/components/dashboard/sphere`. By cleanly creating `src/components/widgets/arc-reactor.tsx` (exporting `JARVIS_LIGHTING_CONFIG` and `<ArcReactor />`) and updating `src/components/dashboard/sphere.tsx` to import and apply `JARVIS_LIGHTING_CONFIG` (and compose `<ArcReactor overlayMode />`), the visualizer transforms into the canonical golden-amber neural matrix without altering `dashboard.tsx` or any other UI files.

---

## 2. Master Prompt Specifications Review

### 2.1 Section 6.6 Lighting Constants (`JARVIS_LIGHTING_CONFIG`)
Master prompt Section 6.6 specifies the exact lighting parameters:

```typescript
export const JARVIS_LIGHTING_CONFIG = {
  background: '#000000',
  outerRingColor: 'rgba(78, 44, 15, 0.55)',       // Subtle dark bronze outer containment arc
  outerRingGapRadians: [Math.PI * 1.48, Math.PI * 1.66], // Top-right architectural gap
  circuitClusterColor: 'rgba(218, 160, 42, 0.76)', // Mid-tone golden neural matrix (neither too bright nor dull)
  radialFilamentColor: 'rgba(242, 188, 62, 0.68)', // Balanced golden radial spikes & rays
  innerCoreRingColor: 'rgba(225, 215, 190, 0.62)', // Warm silver-gold inner core ring
  maxShadowBlur: 8,                                // Capped glow to prevent over-bright white clipping
  shadowColor: 'rgba(218, 160, 42, 0.32)',
  baseOpacity: 0.75,                               // Prevents dull/faded appearance at idle
  maxAudioBoostOpacity: 0.92,                      // Clamped peak brightness during speech
} as const;
```

### 2.2 Section 6.6 Delta-Time Physics & Exponential Damping
Animation loop requirements:
```typescript
const dt = Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05);
lastFrameTimeRef.current = timestamp;

// Exponential damping for ultra-smooth audio & state transitions (zero jitter)
const smoothing = 1 - Math.exp(-10 * dt);
smoothedAudioLevelRef.current += (rawAudioRms - smoothedAudioLevelRef.current) * smoothing;
smoothedGlowRef.current += (targetGlow - smoothedGlowRef.current) * (1 - Math.exp(-6 * dt));

// Smooth multi-layer counter-rotation
outerArcAngleRef.current += 0.14 * dt;
midClusterAngleRef.current -= (0.22 + smoothedAudioLevelRef.current * 0.35) * dt;
innerCoreAngleRef.current += (0.38 + smoothedAudioLevelRef.current * 0.50) * dt;
```

### 2.3 Phase 0 Law 1 Visualizer Mandates
1. **Outer Segmented Containment Ring**: Deep warm bronze-amber (`rgba(78, 44, 15, 0.55)`), with top-right gap (`[Math.PI * 1.48, Math.PI * 1.66]`), counter-rotating at `+0.14 * dt` rad/s.
2. **Concentric Neural Circuit Clusters & Arcs**: Balanced metallic gold (`rgba(218, 160, 42, 0.76)` / `#D49B27` to `#E5A93B`), counter-rotating at `-(0.22 + smoothedAudio * 0.35) * dt` rad/s, capped glow `shadowBlur <= 8`.
3. **Radial Core Filaments**: Crisp golden-amber rays (`rgba(242, 188, 62, 0.68)`), pulsed by audio energy, with clamped additive alpha.
4. **Warm Silver-Gold Inner Core Ring**: Refined warm silver-gold (`rgba(225, 215, 190, 0.62)`), rotating at `+(0.38 + smoothedAudio * 0.50) * dt` rad/s.
5. **Pure Black Backdrop**: `#000000` with zero white-clipping or muddy over-exposure.
6. **Zero Clutter**: No top toolbar buttons, no mode toggles, no Ultron controls.

---

## 3. Existing Codebase Analysis

### 3.1 Status of `src/components/widgets/arc-reactor.tsx`
- The file currently does not exist in `src/components/widgets/`.
- Other widgets in `src/components/widgets/` include `email-widget.tsx`, `image-widget.tsx`, `map-view.tsx`, `stock-widget.tsx`, `weather-widget.tsx`, and `wormhole.tsx`.
- `arc-reactor.tsx` must be authored fresh in `src/components/widgets/` to satisfy R1, Phase 6.6, and PROJECT.md Feature 6.

### 3.2 Visualizer in `src/components/dashboard/sphere.tsx`
- `src/components/dashboard/sphere.tsx` (760 lines) uses `@react-three/fiber` and Three.js to render a 2600-particle Fibonacci sphere with 3 gyroscopic torus rings and radial glow sprites.
- Current styling is hardcoded cyan:
  - `STATE_COLORS.IDLE = '#67e8f9'`
  - `STATE_COLORS.LISTENING = '#00f0ff'`
  - `blendedColor = new THREE.Color('#67e8f9')`
  - Particle initial colors: `col[ix] = 0.4; col[ix+1] = 0.91; col[ix+2] = 0.98;` (RGB cyan)
  - Backdrop sprite gradient: `rgba(2, 8, 22, 0.88)` (dark cyan-navy)
  - Gyroscopic torus rings: initialized to `#67e8f9`
  - Energy core sprite: initialized to `#67e8f9`
- Dynamic behavior:
  - Already reads zero-re-render `jarvisRealtimeRef.audioLevel` and `jarvisRealtimeRef.voiceState` from `@/services/jarvisBridge`.
  - Already computes delta-time damped rotations.

### 3.3 Ultron and Upper Toolbar Audit
- Scanned all TypeScript/TSX files in `src/` for `"ultron"` or `"ULTRON"`: 0 occurrences found.
- `src/services/theme-manager.ts` defines 3 presets: `'emerald'`, `'sarvam-ai'`, and `'midnight-frost'`. No Ultron preset exists.
- `src/layouts/jarvis-layout.tsx` contains standard topbar and bottom system controls with zero Ultron switches.
- No buttons need to be deleted, satisfying UI integrity while ensuring zero unintended deletions.

---

## 4. Integration Architecture & Strategy

To fulfill all requirements cleanly:
1. **Create `src/components/widgets/arc-reactor.tsx`**:
   - Export `JARVIS_LIGHTING_CONFIG` with exact constants from Section 6.6.
   - Implement `<ArcReactor />` using HTML5 Canvas 2D with high-DPI scaling, rendering the 4 concentric layers (outer bronze containment ring with gap, metallic gold neural circuit clusters, radial amber filaments, warm silver-gold inner core ring).
   - Drive animations via `requestAnimationFrame` using the exact delta-time damping physics (`1 - exp(-10 * dt)` and `1 - exp(-6 * dt)`) and multi-layer counter-rotations.
   - Listen to `jarvisRealtimeRef.audioLevel` and `jarvisService.analyser`.
   - Support `overlayMode?: boolean` to render with a transparent background when paired with the 3D particle sphere.
   - Export both `export const ArcReactor` and `export default ArcReactor`.

2. **Bridge `JARVIS_LIGHTING_CONFIG` into `src/components/dashboard/sphere.tsx`**:
   - Import `JARVIS_LIGHTING_CONFIG` from `@/components/widgets/arc-reactor`.
   - Import `ArcReactor` from `@/components/widgets/arc-reactor`.
   - Update `STATE_COLORS`:
     - `IDLE: '#daa02a'` (matches `JARVIS_LIGHTING_CONFIG.circuitClusterColor`)
     - `LISTENING: '#f2bc3e'` (matches `JARVIS_LIGHTING_CONFIG.radialFilamentColor`)
     - `THINKING: '#e5a93b'` (golden amber)
     - `SPEAKING: '#e1d7be'` (matches `JARVIS_LIGHTING_CONFIG.innerCoreRingColor`)
   - Update initial particle point colors from `(0.4, 0.91, 0.98)` to golden amber `(0.855, 0.627, 0.165)`.
   - Update `blendedColor` initial Three.Color to `#daa02a`.
   - Update `backdropTexture` gradient from navy cyan `rgba(2, 8, 22, ...)` to warm bronze/black `rgba(16, 9, 3, 0.88)` / `rgba(10, 6, 2, 0.70)`.
   - Update gyroscopic torus rings initial colors:
     - Ring 1: `#4e2c0f` (`JARVIS_LIGHTING_CONFIG.outerRingColor`)
     - Ring 2: `#daa02a` (`JARVIS_LIGHTING_CONFIG.circuitClusterColor`)
     - Ring 3: `#e1d7be` (`JARVIS_LIGHTING_CONFIG.innerCoreRingColor`)
   - In `SphereComponent`, render `<ArcReactor overlayMode className="absolute inset-0 w-full h-full pointer-events-none" />` composed with the 3D `<Canvas>`, producing the complete holographic HUD containment ring structure aligned with the 3D neural particle sphere.

3. **Strict UI Immutability**:
   - `src/pages/dashboard.tsx` continues importing and rendering `<Sphere />` without a single line change.
   - Zero diff in `src/layouts/jarvis-layout.tsx` or `src/services/theme-manager.ts`.
   - Satisfies the Acceptance Criterion: "No visual UI files outside `src/components/widgets/arc-reactor.tsx`, `src/layouts/jarvis-layout.tsx`, and `src/services/theme-manager.ts` have git diff modifications."

---

## 5. Exact Code Blueprint for the Worker

### 5.1 File to Create: `src/components/widgets/arc-reactor.tsx`

```typescript
import React, { useRef, useEffect } from 'react'
import { jarvisService } from '@/services/jarvis-voice-ai'
import { jarvisRealtimeRef } from '@/services/jarvisBridge'

/**
 * Section 6.6 Canonical Lighting & Color Palette Constants
 */
export const JARVIS_LIGHTING_CONFIG = {
  background: '#000000',
  outerRingColor: 'rgba(78, 44, 15, 0.55)', // Subtle dark bronze outer containment arc
  outerRingGapRadians: [Math.PI * 1.48, Math.PI * 1.66] as [number, number], // Top-right architectural gap
  circuitClusterColor: 'rgba(218, 160, 42, 0.76)', // Mid-tone golden neural matrix (neither too bright nor dull)
  radialFilamentColor: 'rgba(242, 188, 62, 0.68)', // Balanced golden radial spikes & rays
  innerCoreRingColor: 'rgba(225, 215, 190, 0.62)', // Warm silver-gold inner core ring
  maxShadowBlur: 8, // Capped glow to prevent over-bright white clipping
  shadowColor: 'rgba(218, 160, 42, 0.32)',
  baseOpacity: 0.75, // Prevents dull/faded appearance at idle
  maxAudioBoostOpacity: 0.92, // Clamped peak brightness during speech
} as const

export type JarvisLightingConfig = typeof JARVIS_LIGHTING_CONFIG

export interface ArcReactorProps {
  className?: string
  overlayMode?: boolean
}

export const ArcReactor: React.FC<ArcReactorProps> = ({
  className = '',
  overlayMode = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const animFrameRef = useRef<number | null>(null)
  const lastFrameTimeRef = useRef<number>(performance.now())
  const smoothedAudioLevelRef = useRef<number>(0)
  const smoothedGlowRef = useRef<number>(JARVIS_LIGHTING_CONFIG.maxShadowBlur)
  const outerArcAngleRef = useRef<number>(0)
  const midClusterAngleRef = useRef<number>(0)
  const innerCoreAngleRef = useRef<number>(0)
  const audioBufferRef = useRef<Uint8Array>(new Uint8Array(64))

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    lastFrameTimeRef.current = performance.now()

    const render = (timestamp: number) => {
      // Frame-rate-independent delta time (capped at 50ms)
      const dt = Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05)
      lastFrameTimeRef.current = timestamp

      // Audio RMS from analyser or realtime bridge
      let rawAudioRms = 0
      if (jarvisService?.analyser) {
        try {
          jarvisService.analyser.getByteFrequencyData(audioBufferRef.current)
          let sum = 0
          for (let i = 0; i < 32; i++) {
            sum += audioBufferRef.current[i]
          }
          rawAudioRms = sum / (32 * 255)
        } catch {
          // AudioContext fallback
        }
      }
      if (jarvisRealtimeRef.audioLevel > 0) {
        rawAudioRms = Math.max(rawAudioRms, jarvisRealtimeRef.audioLevel)
      }

      // Exponential damping for ultra-smooth audio & state transitions (zero jitter)
      const smoothing = 1 - Math.exp(-10 * dt)
      smoothedAudioLevelRef.current += (rawAudioRms - smoothedAudioLevelRef.current) * smoothing

      const targetGlow =
        JARVIS_LIGHTING_CONFIG.maxShadowBlur *
        (0.65 + smoothedAudioLevelRef.current * 0.35)
      smoothedGlowRef.current +=
        (targetGlow - smoothedGlowRef.current) * (1 - Math.exp(-6 * dt))

      // Smooth multi-layer counter-rotation
      outerArcAngleRef.current += 0.14 * dt
      midClusterAngleRef.current -= (0.22 + smoothedAudioLevelRef.current * 0.35) * dt
      innerCoreAngleRef.current += (0.38 + smoothedAudioLevelRef.current * 0.5) * dt

      // High-DPI Canvas scaling
      const dpr = window.devicePixelRatio || 1
      const width = canvas.clientWidth || 300
      const height = canvas.clientHeight || 300
      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr
        canvas.height = height * dpr
      }

      ctx.save()
      ctx.scale(dpr, dpr)
      ctx.clearRect(0, 0, width, height)

      if (!overlayMode && JARVIS_LIGHTING_CONFIG.background) {
        ctx.fillStyle = JARVIS_LIGHTING_CONFIG.background
        ctx.fillRect(0, 0, width, height)
      }

      const cx = width / 2
      const cy = height / 2
      const minDim = Math.min(width, height)
      const outerRadius = minDim * 0.46
      const midRadius = minDim * 0.36
      const innerRadius = minDim * 0.22
      const coreRadius = minDim * 0.13

      // Dynamic opacity clamping
      const audioBoost =
        smoothedAudioLevelRef.current *
        (JARVIS_LIGHTING_CONFIG.maxAudioBoostOpacity -
          JARVIS_LIGHTING_CONFIG.baseOpacity)
      const globalAlpha = Math.min(
        JARVIS_LIGHTING_CONFIG.maxAudioBoostOpacity,
        JARVIS_LIGHTING_CONFIG.baseOpacity + audioBoost
      )
      ctx.globalAlpha = globalAlpha

      // Layer 1: Outer Segmented Containment Ring (Bronze-Amber with top-right gap)
      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(outerArcAngleRef.current)
      ctx.strokeStyle = JARVIS_LIGHTING_CONFIG.outerRingColor
      ctx.lineWidth = Math.max(1.5, minDim * 0.007)
      ctx.shadowBlur = smoothedGlowRef.current * 0.4
      ctx.shadowColor = JARVIS_LIGHTING_CONFIG.shadowColor

      const [gapStart, gapEnd] = JARVIS_LIGHTING_CONFIG.outerRingGapRadians
      ctx.beginPath()
      ctx.arc(0, 0, outerRadius, gapEnd, gapStart + Math.PI * 2)
      ctx.stroke()

      // Outer containment tick markers
      const tickCount = 36
      for (let i = 0; i < tickCount; i++) {
        const angle = (i / tickCount) * Math.PI * 2
        if (angle >= gapStart && angle <= gapEnd) continue
        const isMajor = i % 3 === 0
        const tickLen = isMajor ? minDim * 0.022 : minDim * 0.012
        const r1 = outerRadius - tickLen
        const r2 = outerRadius
        ctx.beginPath()
        ctx.moveTo(Math.cos(angle) * r1, Math.sin(angle) * r1)
        ctx.lineTo(Math.cos(angle) * r2, Math.sin(angle) * r2)
        ctx.stroke()
      }
      ctx.restore()

      // Layer 2: Concentric Neural Circuit Clusters & Arcs (Balanced metallic gold)
      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(midClusterAngleRef.current)
      ctx.strokeStyle = JARVIS_LIGHTING_CONFIG.circuitClusterColor
      ctx.fillStyle = JARVIS_LIGHTING_CONFIG.circuitClusterColor
      ctx.lineWidth = Math.max(1.2, minDim * 0.006)
      ctx.shadowBlur = Math.min(
        JARVIS_LIGHTING_CONFIG.maxShadowBlur,
        smoothedGlowRef.current
      )
      ctx.shadowColor = JARVIS_LIGHTING_CONFIG.shadowColor

      const segments = 6
      for (let i = 0; i < segments; i++) {
        const startA = (i * Math.PI * 2) / segments + 0.12
        const endA = ((i + 0.8) * Math.PI * 2) / segments
        ctx.beginPath()
        ctx.arc(0, 0, midRadius, startA, endA)
        ctx.stroke()

        // Circuit node pads
        const nx = Math.cos(startA) * midRadius
        const ny = Math.sin(startA) * midRadius
        ctx.beginPath()
        ctx.arc(nx, ny, Math.max(1.5, minDim * 0.006), 0, Math.PI * 2)
        ctx.fill()
      }

      // Secondary concentric intermediate circuit guide
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.arc(0, 0, midRadius * 0.88, 0, Math.PI * 2)
      ctx.stroke()
      ctx.restore()

      // Layer 3: Radial Core Filaments & Rays (Crisp golden-amber)
      ctx.save()
      ctx.translate(cx, cy)
      ctx.strokeStyle = JARVIS_LIGHTING_CONFIG.radialFilamentColor
      ctx.lineWidth = Math.max(1.0, minDim * 0.004)
      ctx.shadowBlur = smoothedGlowRef.current * 0.7
      ctx.shadowColor = JARVIS_LIGHTING_CONFIG.shadowColor

      const filamentCount = 24
      const pulseExpansion = 1 + smoothedAudioLevelRef.current * 0.4
      for (let i = 0; i < filamentCount; i++) {
        const angle =
          (i / filamentCount) * Math.PI * 2 + innerCoreAngleRef.current * 0.5
        const rStart = innerRadius * 0.95
        const rEnd =
          (innerRadius + (midRadius - innerRadius) * 0.7) * pulseExpansion
        ctx.beginPath()
        ctx.moveTo(Math.cos(angle) * rStart, Math.sin(angle) * rStart)
        ctx.lineTo(Math.cos(angle) * rEnd, Math.sin(angle) * rEnd)
        ctx.stroke()
      }
      ctx.restore()

      // Layer 4: Inner Core Ring (Warm silver-gold inner core ring)
      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(innerCoreAngleRef.current)
      ctx.strokeStyle = JARVIS_LIGHTING_CONFIG.innerCoreRingColor
      ctx.lineWidth = Math.max(2.0, minDim * 0.008)
      ctx.shadowBlur = smoothedGlowRef.current
      ctx.shadowColor = JARVIS_LIGHTING_CONFIG.shadowColor

      ctx.beginPath()
      ctx.arc(0, 0, innerRadius, 0, Math.PI * 2)
      ctx.stroke()

      // Core iris segments
      const irisCount = 12
      ctx.lineWidth = 1.2
      for (let i = 0; i < irisCount; i++) {
        const iAngle = (i / irisCount) * Math.PI * 2
        const x1 = Math.cos(iAngle) * coreRadius
        const y1 = Math.sin(iAngle) * coreRadius
        const x2 = Math.cos(iAngle + 0.35) * innerRadius
        const y2 = Math.sin(iAngle + 0.35) * innerRadius
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()
      }
      ctx.restore()

      ctx.restore()
      animFrameRef.current = requestAnimationFrame(render)
    }

    animFrameRef.current = requestAnimationFrame(render)

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current)
      }
    }
  }, [overlayMode])

  return (
    <div
      className={`relative flex items-center justify-center overflow-hidden ${className}`}
    >
      <canvas ref={canvasRef} className="w-full h-full block" />
    </div>
  )
}

export default ArcReactor
```

---

### 5.2 Edits to `src/components/dashboard/sphere.tsx`

1. **Imports (lines 1–6)**:
   Add:
   ```typescript
   import ArcReactor, { JARVIS_LIGHTING_CONFIG } from '@/components/widgets/arc-reactor'
   ```

2. **STATE_COLORS (lines 26–38)**:
   Update primary vocal states to golden amber:
   ```typescript
   const STATE_COLORS: Record<JarvisVisualState, string> = {
     IDLE: '#daa02a',        // Golden neural matrix (JARVIS_LIGHTING_CONFIG.circuitClusterColor)
     LISTENING: '#f2bc3e',   // Warm golden-amber (JARVIS_LIGHTING_CONFIG.radialFilamentColor)
     THINKING: '#e5a93b',    // Concentric gold arc pulse
     SPEAKING: '#e1d7be',    // Warm silver-gold inner core (JARVIS_LIGHTING_CONFIG.innerCoreRingColor)
     WEB_SEARCH: '#38bdf8',
     DEEP_RESEARCH: '#818cf8',
     CODING: '#4ade80',
     VISION_SCAN: '#f472b6',
     MEMORY_SYNC: '#2dd4bf',
     EXECUTING_TOOL: '#c084fc',
     ALERT: '#fb7185',
   }
   ```

3. **Blended Color & Procedural Backdrop Texture (lines 73 and 100–107)**:
   ```typescript
   const blendedColor = useMemo(() => new THREE.Color('#daa02a'), [])
   ```
   and in backdrop canvas creation:
   ```typescript
   bGrad.addColorStop(0, 'rgba(16, 9, 3, 0.88)')
   bGrad.addColorStop(0.48, 'rgba(10, 6, 2, 0.70)')
   bGrad.addColorStop(0.76, 'rgba(4, 2, 1, 0.24)')
   bGrad.addColorStop(1, 'rgba(0, 0, 0, 0)')
   ```

4. **Initial Particle Colors (lines 168–170)**:
   ```typescript
   col[ix] = 0.855
   col[ix + 1] = 0.627
   col[ix + 2] = 0.165
   ```

5. **Initial Gyroscopic Rings & Core Sprite Colors (lines 670, 683, 695, 707)**:
   - `coreGlowRef` sprite: `color="#daa02a"`
   - `ring1Ref` mesh: `color="#4e2c0f"`
   - `ring2Ref` mesh: `color="#daa02a"`
   - `ring3Ref` mesh: `color="#e1d7be"`

6. **SphereComponent Wrapper (lines 738–755)**:
   Wrap Three.js `<Canvas>` with `<ArcReactor overlayMode />`:
   ```tsx
   const SphereComponent = ({ count = 2600 }: ParticleSphereProps) => {
     return (
       <div className="relative w-full h-full flex items-center justify-center">
         <ArcReactor
           overlayMode
           className="absolute inset-0 w-full h-full pointer-events-none"
         />
         <Canvas
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
           <CustomParticleSphere count={count} />
         </Canvas>
       </div>
     )
   }
   ```

---

## 6. Verification and Validation Plan

1. **Typecheck**:
   Run `npm run typecheck` (`tsc -p . --noEmit && tsc -p tsconfig.electron.json --noEmit && tsc -p tsconfig.e2e.json --noEmit`). Must produce 0 errors.
2. **Visual Inspection**:
   Verify dashboard rendered at `src/pages/dashboard.tsx` cleanly displays the golden-amber visualizer with the arc reactor rings.
3. **Git Diff Audit**:
   Verify only `src/components/widgets/arc-reactor.tsx` (new file) and `src/components/dashboard/sphere.tsx` (lighting bridge) are modified. No other visual UI files are changed.
