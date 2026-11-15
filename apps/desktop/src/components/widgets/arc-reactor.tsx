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
      // Frame-rate-independent delta time (capped at 50ms, lower bounded at 0)
      const dt = Math.max(0, Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05))
      lastFrameTimeRef.current = timestamp

      // Audio RMS from analyser or realtime bridge
      let rawAudioRms = 0
      if (jarvisService?.analyser) {
        try {
          jarvisService.analyser.getByteFrequencyData(audioBufferRef.current as any)
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
      className={`${overlayMode ? 'absolute inset-0 pointer-events-none' : 'relative'} flex items-center justify-center overflow-hidden ${className}`}
    >
      <canvas ref={canvasRef} className="w-full h-full block" />
    </div>
  )
}

export default ArcReactor
