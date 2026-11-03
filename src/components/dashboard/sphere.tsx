import React, { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { jarvisService } from '@/services/jarvis-voice-ai'
import { jarvisRealtimeRef } from '@/services/jarvisBridge'

export type JarvisVisualState =
  | 'IDLE'
  | 'LISTENING'
  | 'THINKING'
  | 'SPEAKING'
  | 'WEB_SEARCH'
  | 'DEEP_RESEARCH'
  | 'CODING'
  | 'VISION_SCAN'
  | 'MEMORY_SYNC'
  | 'EXECUTING_TOOL'
  | 'ALERT'

interface ParticleSphereProps {
  count?: number
}

const BASE_RADIUS = 1.72

const STATE_COLORS: Record<JarvisVisualState, string> = {
  IDLE: '#67e8f9',
  LISTENING: '#00f0ff',
  THINKING: '#fbbf24',
  SPEAKING: '#e0f2fe',
  WEB_SEARCH: '#38bdf8',
  DEEP_RESEARCH: '#818cf8',
  CODING: '#4ade80',
  VISION_SCAN: '#f472b6',
  MEMORY_SYNC: '#2dd4bf',
  EXECUTING_TOOL: '#c084fc',
  ALERT: '#fb7185',
}

const STATE_KEYS = Object.keys(STATE_COLORS) as JarvisVisualState[]

const KEY_STATE_MAP: Record<string, JarvisVisualState> = {
  '1': 'IDLE',
  '2': 'LISTENING',
  '3': 'THINKING',
  '4': 'SPEAKING',
  '5': 'WEB_SEARCH',
  '6': 'DEEP_RESEARCH',
  '7': 'CODING',
  '8': 'VISION_SCAN',
  '9': 'MEMORY_SYNC',
  '0': 'EXECUTING_TOOL',
  '-': 'ALERT',
}

const CustomParticleSphere = React.memo(({ count = 2600 }: ParticleSphereProps) => {
  const mesh = useRef<THREE.Points>(null)
  const coreGlowRef = useRef<THREE.Sprite>(null)
  const ring1Ref = useRef<THREE.Mesh>(null)
  const ring2Ref = useRef<THREE.Mesh>(null)
  const ring3Ref = useRef<THREE.Mesh>(null)

  const dataArray = useMemo(() => new Uint8Array(128), [])

  const palette = useMemo(() => {
    const map = {} as Record<JarvisVisualState, THREE.Color>
    for (const key of STATE_KEYS) {
      map[key] = new THREE.Color(STATE_COLORS[key])
    }
    return map
  }, [])

  const blendedColor = useMemo(() => new THREE.Color('#67e8f9'), [])
  const whiteColor = useMemo(() => new THREE.Color('#ffffff'), [])

  // Procedural glow sprite + dark contrast backdrop (created only once)
  const { glowTexture, backdropTexture } = useMemo(() => {
    const gSize = 64
    const gCanvas = document.createElement('canvas')
    gCanvas.width = gSize
    gCanvas.height = gSize
    const gCtx = gCanvas.getContext('2d')
    if (gCtx) {
      const grad = gCtx.createRadialGradient(gSize / 2, gSize / 2, 0, gSize / 2, gSize / 2, gSize / 2)
      grad.addColorStop(0, 'rgba(255, 255, 255, 1)')
      grad.addColorStop(0.22, 'rgba(255, 255, 255, 0.86)')
      grad.addColorStop(0.55, 'rgba(255, 255, 255, 0.22)')
      grad.addColorStop(1, 'rgba(255, 255, 255, 0)')
      gCtx.fillStyle = grad
      gCtx.fillRect(0, 0, gSize, gSize)
    }
    const glowTex = new THREE.CanvasTexture(gCanvas)

    const bSize = 128
    const bCanvas = document.createElement('canvas')
    bCanvas.width = bSize
    bCanvas.height = bSize
    const bCtx = bCanvas.getContext('2d')
    if (bCtx) {
      const bGrad = bCtx.createRadialGradient(bSize / 2, bSize / 2, 0, bSize / 2, bSize / 2, bSize / 2)
      bGrad.addColorStop(0, 'rgba(2, 8, 22, 0.88)')
      bGrad.addColorStop(0.48, 'rgba(3, 12, 28, 0.70)')
      bGrad.addColorStop(0.76, 'rgba(3, 12, 28, 0.24)')
      bGrad.addColorStop(1, 'rgba(0, 0, 0, 0)')
      bCtx.fillStyle = bGrad
      bCtx.fillRect(0, 0, bSize, bSize)
    }
    const backTex = new THREE.CanvasTexture(bCanvas)

    return { glowTexture: glowTex, backdropTexture: backTex }
  }, [])

  useEffect(() => {
    return () => {
      glowTexture.dispose()
      backdropTexture.dispose()
    }
  }, [glowTexture, backdropTexture])

  // Precompute Fibonacci sphere + Globe wireframe (WEB_SEARCH) + Beveled Cube (CODING)
  const {
    positions,
    colors,
    normals,
    globeNormals,
    cubeNormals,
    thetas,
    phis,
    phases,
    spreads,
    colSeeds,
  } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const norm = new Float32Array(count * 3)
    const globe = new Float32Array(count * 3)
    const cube = new Float32Array(count * 3)
    const thArr = new Float32Array(count)
    const phArr = new Float32Array(count)
    const phaseArr = new Float32Array(count)
    const spreadArr = new Float32Array(count)
    const seedArr = new Float32Array(count)

    const goldenAngle = Math.PI * (3 - Math.sqrt(5))

    for (let i = 0; i < count; i++) {
      const y = 1 - (i / Math.max(1, count - 1)) * 2
      const rAtY = Math.sqrt(Math.max(0, 1 - y * y))
      const th = goldenAngle * i

      let nx = Math.cos(th) * rAtY + (Math.random() - 0.5) * 0.025
      let ny = y + (Math.random() - 0.5) * 0.025
      let nz = Math.sin(th) * rAtY + (Math.random() - 0.5) * 0.025
      const len = Math.hypot(nx, ny, nz) || 1
      nx /= len
      ny /= len
      nz /= len

      const ix = i * 3
      norm[ix] = nx
      norm[ix + 1] = ny
      norm[ix + 2] = nz

      pos[ix] = nx * BASE_RADIUS
      pos[ix + 1] = ny * BASE_RADIUS
      pos[ix + 2] = nz * BASE_RADIUS

      col[ix] = 0.4
      col[ix + 1] = 0.91
      col[ix + 2] = 0.98

      const theta = Math.atan2(nz, nx)
      const phi = Math.acos(Math.max(-1, Math.min(1, ny)))
      thArr[i] = theta
      phArr[i] = phi
      phaseArr[i] = Math.random() * Math.PI * 2
      spreadArr[i] = Math.random()

      // Lat/Lon Hologram Globe target (WEB_SEARCH)
      let gTheta = theta
      let gPhi = phi
      if (i % 2 === 0) {
        const meridians = 12
        gTheta = Math.round(theta / ((Math.PI * 2) / meridians)) * ((Math.PI * 2) / meridians)
      } else {
        const parallels = 8
        gPhi = Math.max(
          0.16,
          Math.min(Math.PI - 0.16, Math.round(phi / (Math.PI / parallels)) * (Math.PI / parallels))
        )
      }
      const gx = Math.sin(gPhi) * Math.cos(gTheta)
      const gy = Math.cos(gPhi)
      const gz = Math.sin(gPhi) * Math.sin(gTheta)
      globe[ix] = nx * 0.18 + gx * 0.82
      globe[ix + 1] = ny * 0.18 + gy * 0.82
      globe[ix + 2] = nz * 0.18 + gz * 0.82

      // Beveled 3D Holo-Cube target (CODING)
      const maxAxis = Math.max(Math.abs(nx), Math.abs(ny), Math.abs(nz)) || 1
      const cx = (nx / maxAxis) * 0.77
      const cy = (ny / maxAxis) * 0.77
      const cz = (nz / maxAxis) * 0.77
      cube[ix] = nx * 0.16 + cx * 0.84
      cube[ix + 1] = ny * 0.16 + cy * 0.84
      cube[ix + 2] = nz * 0.16 + cz * 0.84

      const qx = Math.round(cx * 5) + 10
      const qz = Math.round(cz * 5) + 10
      seedArr[i] = ((qx * 37 + qz * 17) % 19) * 0.55
    }

    return {
      positions: pos,
      colors: col,
      normals: norm,
      globeNormals: globe,
      cubeNormals: cube,
      thetas: thArr,
      phis: phArr,
      phases: phaseArr,
      spreads: spreadArr,
      colSeeds: seedArr,
    }
  }, [count])

  const agentStateRef = useRef<JarvisVisualState>('IDLE')

  useEffect(() => {
    const handleState = (e: Event) => {
      let raw = String((e as CustomEvent).detail || 'IDLE').toUpperCase()
      if (raw === 'LISTEN') raw = 'LISTENING'
      if (raw === 'PROCESSING') raw = 'THINKING'
      agentStateRef.current = (raw in STATE_COLORS ? raw : 'IDLE') as JarvisVisualState
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return
      }

      const nextState = KEY_STATE_MAP[e.key]
      if (nextState) {
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: nextState }))
      }
    }

    window.addEventListener('jarvis-state', handleState)
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('jarvis-state', handleState)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const weights = useRef<Record<JarvisVisualState, number>>({
    IDLE: 1,
    LISTENING: 0,
    THINKING: 0,
    SPEAKING: 0,
    WEB_SEARCH: 0,
    DEEP_RESEARCH: 0,
    CODING: 0,
    VISION_SCAN: 0,
    MEMORY_SYNC: 0,
    EXECUTING_TOOL: 0,
    ALERT: 0,
  })

  const audioBands = useRef({ bass: 0, mid: 0, treble: 0 })

  useFrame((state, delta) => {
    if (!state.clock.running || !mesh.current) return

    const dt = Math.min(0.05, delta)
    const t = state.clock.elapsedTime
    const damp = 1 - Math.exp(-6.2 * dt)
    const audioDamp = 1 - Math.exp(-14 * dt)

    // Direct read from zero-re-render mutable store
    const rtVoiceState = jarvisRealtimeRef.voiceState as JarvisVisualState
    if (rtVoiceState && rtVoiceState in STATE_COLORS && rtVoiceState !== agentStateRef.current) {
      agentStateRef.current = rtVoiceState
    }

    const active = agentStateRef.current
    const w = weights.current
    for (const key of STATE_KEYS) {
      w[key] += ((active === key ? 1 : 0) - w[key]) * damp
    }

    // Multi-band audio extraction + speech cadence synthesizer fallback
    let rawBass = 0
    let rawMid = 0
    let rawTreble = 0

    if (jarvisService?.analyser) {
      try {
        jarvisService.analyser.getByteFrequencyData(dataArray)
        for (let i = 0; i < 16; i++) rawBass += dataArray[i]
        for (let i = 16; i < 56; i++) rawMid += dataArray[i]
        for (let i = 56; i < 112; i++) rawTreble += dataArray[i]
        rawBass /= 16 * 255
        rawMid /= 40 * 255
        rawTreble /= 56 * 255
      } catch {
        // Ignore audio context errors
      }
    }

    // Blend live WebSocket amplitude stream from zero-re-render ref
    const rtAudio = jarvisRealtimeRef.audioLevel
    if (rtAudio > 0) {
      rawBass = Math.max(rawBass, rtAudio * 0.95)
      rawMid = Math.max(rawMid, rtAudio * 0.85)
      rawTreble = Math.max(rawTreble, rtAudio * 0.75)
    }

    const totalRaw = (rawBass + rawMid + rawTreble) / 3
    if (active === 'SPEAKING' && totalRaw < 0.03) {
      const syllable = Math.pow(
        Math.max(0, Math.sin(t * 7.2) * 0.65 + Math.sin(t * 11.7) * 0.35),
        1.4
      )
      const cadence = 0.45 + 0.55 * Math.max(0, Math.sin(t * 2.1 + 0.5))
      rawBass = 0.22 + syllable * cadence * 0.65
      rawMid = 0.18 + Math.abs(Math.sin(t * 9.5)) * cadence * 0.58
      rawTreble = 0.14 + Math.abs(Math.cos(t * 14.3)) * cadence * 0.52
    } else if (active === 'LISTENING') {
      rawBass = Math.min(1, rawBass * 2.2)
      rawMid = Math.min(1, rawMid * 2.2)
      rawTreble = Math.min(1, rawTreble * 2.0)
    }

    audioBands.current.bass += (rawBass - audioBands.current.bass) * audioDamp
    audioBands.current.mid += (rawMid - audioBands.current.mid) * audioDamp
    audioBands.current.treble += (rawTreble - audioBands.current.treble) * audioDamp
    const { bass, mid, treble } = audioBands.current

    blendedColor.lerp(palette[active], damp)
    const sr = blendedColor.r
    const sg = blendedColor.g
    const sb = blendedColor.b

    // State-specific 3D orientation & rotation
    if (active === 'LISTENING' || active === 'VISION_SCAN') {
      mesh.current.rotation.y += dt * 0.18
      mesh.current.rotation.x += (0.08 - mesh.current.rotation.x) * damp
      mesh.current.rotation.z += (0.0 - mesh.current.rotation.z) * damp
    } else if (active === 'WEB_SEARCH') {
      mesh.current.rotation.y += dt * 0.38
      mesh.current.rotation.x += (0.18 - mesh.current.rotation.x) * damp
      mesh.current.rotation.z += (-0.38 - mesh.current.rotation.z) * damp
    } else if (active === 'MEMORY_SYNC') {
      mesh.current.rotation.y += dt * 0.32
      mesh.current.rotation.x += (0.58 - mesh.current.rotation.x) * damp
      mesh.current.rotation.z += (Math.sin(t * 0.6) * 0.12 - mesh.current.rotation.z) * damp
    } else if (active === 'CODING') {
      mesh.current.rotation.y += dt * 0.34
      mesh.current.rotation.x += (0.42 - mesh.current.rotation.x) * damp
      mesh.current.rotation.z += (0.18 - mesh.current.rotation.z) * damp
    } else if (active === 'THINKING') {
      mesh.current.rotation.y += dt * 0.72
      mesh.current.rotation.x += dt * 0.32
      mesh.current.rotation.z += dt * 0.24
    } else if (active === 'SPEAKING') {
      mesh.current.rotation.y += dt * (0.28 + bass * 0.65)
      mesh.current.rotation.x += (Math.sin(t * 1.8) * 0.15 - mesh.current.rotation.x) * damp
      mesh.current.rotation.z += dt * 0.08
    } else if (active === 'EXECUTING_TOOL') {
      mesh.current.rotation.y += dt * 0.95
      mesh.current.rotation.z += dt * 0.45
    } else if (active === 'ALERT') {
      mesh.current.rotation.y += dt * 0.55
      mesh.current.rotation.x += (Math.sin(t * 9.0) * 0.06 - mesh.current.rotation.x) * damp
    } else {
      mesh.current.rotation.y += dt * 0.15
      mesh.current.rotation.x += (Math.sin(t * 0.4) * 0.08 - mesh.current.rotation.x) * damp
      mesh.current.rotation.z += dt * 0.04
    }

    const alertCycle = (t * 1.18) % 1
    const alertBeat =
      Math.exp(-Math.pow((alertCycle - 0.12) * 14, 2)) +
      0.68 * Math.exp(-Math.pow((alertCycle - 0.3) * 16, 2))
    const scanY = Math.sin(t * 2.1) * 0.94
    const radarAngle = ((t * 2.4) % (Math.PI * 2)) - Math.PI

    // Core glow update
    if (coreGlowRef.current) {
      const coreScale =
        2.45 +
        w.IDLE * Math.sin(t * 1.6) * 0.15 +
        w.LISTENING * (0.25 + bass * 0.7) +
        w.THINKING * (0.35 + Math.sin(t * 6.0) * 0.28) +
        w.SPEAKING * (0.45 + bass * 1.15) +
        w.WEB_SEARCH * 0.25 +
        w.DEEP_RESEARCH * (0.35 + Math.sin(t * 3.5) * 0.2) -
        w.MEMORY_SYNC * 0.55 +
        w.ALERT * alertBeat * 0.95
      coreGlowRef.current.scale.set(coreScale, coreScale, 1)
      const coreMat = coreGlowRef.current.material as THREE.SpriteMaterial
      coreMat.color.copy(blendedColor)
      coreMat.opacity =
        0.36 +
        w.SPEAKING * (0.2 + bass * 0.28) +
        w.THINKING * 0.14 +
        w.ALERT * alertBeat * 0.35 -
        w.MEMORY_SYNC * 0.12
    }

    // Gyroscopic & scanner rings update
    if (ring1Ref.current && ring2Ref.current && ring3Ref.current) {
      const r1Mat = ring1Ref.current.material as THREE.MeshBasicMaterial
      const r2Mat = ring2Ref.current.material as THREE.MeshBasicMaterial
      const r3Mat = ring3Ref.current.material as THREE.MeshBasicMaterial
      r1Mat.color.copy(blendedColor)
      r2Mat.color.copy(blendedColor)
      r3Mat.color.copy(whiteColor).lerp(blendedColor, 0.35)

      const baseRingOpacity =
        0.22 * w.IDLE +
        0.5 * w.LISTENING +
        0.65 * w.THINKING +
        0.55 * w.SPEAKING +
        0.62 * w.WEB_SEARCH +
        0.55 * w.DEEP_RESEARCH +
        0.48 * w.CODING +
        0.38 * w.VISION_SCAN +
        0.52 * w.MEMORY_SYNC +
        0.65 * w.EXECUTING_TOOL +
        (0.45 + alertBeat * 0.45) * w.ALERT

      r1Mat.opacity = baseRingOpacity
      r2Mat.opacity = baseRingOpacity * 0.78

      const ringSpeed =
        0.25 * w.IDLE +
        0.6 * w.LISTENING +
        2.4 * w.THINKING +
        0.9 * w.SPEAKING +
        1.15 * w.WEB_SEARCH +
        1.5 * w.DEEP_RESEARCH +
        0.7 * w.CODING +
        0.4 * w.VISION_SCAN +
        1.3 * w.MEMORY_SYNC +
        2.8 * w.EXECUTING_TOOL +
        2.2 * w.ALERT

      ring1Ref.current.rotation.x += dt * ringSpeed
      ring1Ref.current.rotation.y += dt * ringSpeed * 0.6
      ring2Ref.current.rotation.y -= dt * ringSpeed * 0.85
      ring2Ref.current.rotation.z += dt * ringSpeed * 0.55

      ring1Ref.current.scale.setScalar(
        1 + w.SPEAKING * bass * 0.16 + w.LISTENING * bass * 0.08 + w.ALERT * alertBeat * 0.12
      )
      ring2Ref.current.scale.setScalar(1 + w.SPEAKING * mid * 0.14 + w.DEEP_RESEARCH * 0.08)

      if (w.VISION_SCAN > 0.01) {
        r3Mat.opacity = w.VISION_SCAN * 0.82
        const sliceRadius = Math.sqrt(Math.max(0.06, 1 - scanY * scanY))
        ring3Ref.current.position.set(0, scanY * BASE_RADIUS, 0)
        ring3Ref.current.rotation.set(Math.PI / 2, 0, 0)
        ring3Ref.current.scale.setScalar(sliceRadius * 1.05)
      } else if (w.WEB_SEARCH > 0.01) {
        r3Mat.opacity = w.WEB_SEARCH * 0.45
        ring3Ref.current.position.set(0, 0, 0)
        ring3Ref.current.rotation.set(Math.PI * 0.5 + 0.18, 0, -0.38)
        ring3Ref.current.scale.setScalar(1.16)
      } else {
        r3Mat.opacity = 0
      }
    }

    // Per-particle 3D morphing & displacement
    const posArr = mesh.current.geometry.attributes.position.array as Float32Array
    const colArr = mesh.current.geometry.attributes.color.array as Float32Array

    for (let i = 0; i < count; i++) {
      const ix = i * 3
      const iy = ix + 1
      const iz = ix + 2

      const nx = normals[ix]
      const ny = normals[iy]
      const nz = normals[iz]
      const phase = phases[i]
      const spread = spreads[i]
      const theta = thetas[i]
      const phi = phis[i]

      let dx = nx
      let dy = ny
      let dz = nz
      let extraHighlight = 0

      if (w.THINKING > 0.001) {
        const twist =
          w.THINKING * (ny * 2.1 * Math.sin(t * 2.0) + Math.sin(t * 1.6 + phase * 0.4) * 0.55)
        const c = Math.cos(twist)
        const s = Math.sin(twist)
        const rx = dx * c - dz * s
        const rz = dx * s + dz * c
        dx = rx
        dz = rz
      }

      let webDisp = 0
      if (w.WEB_SEARCH > 0.001) {
        dx += (globeNormals[ix] - dx) * w.WEB_SEARCH
        dy += (globeNormals[iy] - dy) * w.WEB_SEARCH
        dz += (globeNormals[iz] - dz) * w.WEB_SEARCH

        let angDiff = Math.abs(theta - radarAngle)
        if (angDiff > Math.PI) angDiff = Math.PI * 2 - angDiff
        const beam = Math.exp(-(angDiff * angDiff) / 0.09)
        const ping = Math.sin(phase * 19.0 + Math.floor(t * 4.5) * 3.7) > 0.965 ? 1.0 : 0.0
        webDisp = beam * 0.14 + ping * 0.22
        extraHighlight += w.WEB_SEARCH * Math.min(1, beam * 0.9 + ping)
      }

      if (w.DEEP_RESEARCH > 0.001) {
        const shell = i % 3
        const shellScale = shell === 0 ? 0.52 : shell === 1 ? 0.88 : 1.2
        const spin = shell === 0 ? t * 1.35 : shell === 1 ? -t * 0.85 : t * 0.42
        const cs = Math.cos(spin)
        const sn = Math.sin(spin)
        let sx = (nx * cs - nz * sn) * shellScale
        let sy = ny * shellScale
        let sz = (nx * sn + nz * cs) * shellScale
        if (shell === 1) {
          const ct = Math.cos(0.48)
          const st = Math.sin(0.48)
          const ty = sy * ct - sz * st
          const tz = sy * st + sz * ct
          sy = ty
          sz = tz
        }
        dx += (sx - dx) * w.DEEP_RESEARCH
        dy += (sy - dy) * w.DEEP_RESEARCH
        dz += (sz - dz) * w.DEEP_RESEARCH
        extraHighlight += w.DEEP_RESEARCH * (shell === 0 ? 0.55 : 0.15)
      }

      let codeDisp = 0
      if (w.CODING > 0.001) {
        dx += (cubeNormals[ix] - dx) * w.CODING
        dy += (cubeNormals[iy] - dy) * w.CODING
        dz += (cubeNormals[iz] - dz) * w.CODING

        const stream = ((1 - ny) * 1.8 + t * 1.55 + colSeeds[i]) % 1.0
        const head = Math.exp(-Math.pow((stream - 0.12) * 9.0, 2))
        codeDisp = head * 0.07
        extraHighlight += w.CODING * head * 0.95
      }

      if (w.MEMORY_SYNC > 0.001) {
        const poloidal = phi * 2.0 - t * 2.6
        const ringR = 0.78 + 0.34 * Math.cos(poloidal)
        const tx = ringR * Math.cos(theta)
        const ty = 0.38 * Math.sin(poloidal)
        const tz = ringR * Math.sin(theta)
        dx += (tx - dx) * w.MEMORY_SYNC
        dy += (ty - dy) * w.MEMORY_SYNC
        dz += (tz - dz) * w.MEMORY_SYNC
        extraHighlight += w.MEMORY_SYNC * Math.max(0, -Math.cos(poloidal) * 0.65)
      }

      const idleDisp =
        Math.sin(t * 1.6) * 0.035 +
        Math.sin(nx * 2.5 + t * 1.1) * Math.cos(ny * 2.5 - t * 0.9) * 0.03

      const listenDisp =
        -0.07 +
        Math.sin(Math.abs(ny) * 10.0 - t * 6.5) * 0.085 +
        bass * 0.24 +
        mid * 0.18 * Math.sin(ny * 14.0 - t * 10.0)

      const thinkDisp =
        Math.sin(dx * 4.0 + t * 4.5) *
          Math.cos(dy * 4.0 - t * 3.8) *
          Math.sin(dz * 4.0 + t * 3.2) *
          0.22 +
        Math.sin(t * 6.0 + phase) * 0.04

      const speakDisp =
        bass * 0.25 +
        Math.sin(nx * 5.0 + t * 11.0) * Math.cos(ny * 5.0 - t * 9.0) * (0.07 + mid * 0.26) +
        spread * treble * 0.44

      const researchDisp = Math.sin(phase * 3.0 + t * 4.2) * 0.035

      let visionDisp = 0
      if (w.VISION_SCAN > 0.001) {
        const distY = ny - scanY
        const band = Math.exp(-(distY * distY) / 0.0075)
        visionDisp = band * 0.22 - 0.03
        extraHighlight += w.VISION_SCAN * band * 1.1
      }

      const toolDisp =
        Math.sin(nx * 7.0 + t * 4.0) * Math.sin(ny * 7.0 - t * 4.0) * Math.sin(nz * 7.0) * 0.16 +
        Math.sin(t * 8.0) * 0.05

      const alertDisp =
        alertBeat * (0.18 + spread * 0.26) +
        Math.sin(nx * 9.0) * Math.cos(ny * 9.0) * alertBeat * 0.12

      const displacement =
        w.IDLE * idleDisp +
        w.LISTENING * listenDisp +
        w.THINKING * thinkDisp +
        w.SPEAKING * speakDisp +
        w.WEB_SEARCH * webDisp +
        w.DEEP_RESEARCH * researchDisp +
        w.CODING * codeDisp +
        w.VISION_SCAN * visionDisp +
        w.EXECUTING_TOOL * toolDisp +
        w.ALERT * alertDisp

      const radius = BASE_RADIUS * (1 + displacement)
      posArr[ix] = dx * radius
      posArr[iy] = dy * radius
      posArr[iz] = dz * radius

      const crest = Math.min(
        1,
        Math.max(
          0,
          displacement * 2.6 +
            extraHighlight +
            w.SPEAKING * bass * 0.45 +
            w.ALERT * alertBeat * 0.55 +
            0.14
        )
      )
      const twinkle = 0.85 + 0.15 * Math.sin(t * 2.6 + phase)
      colArr[ix] = (sr + (1 - sr) * crest) * twinkle
      colArr[iy] = (sg + (1 - sg) * crest) * twinkle
      colArr[iz] = (sb + (1 - sb) * crest) * twinkle
    }

    mesh.current.geometry.attributes.position.needsUpdate = true
    mesh.current.geometry.attributes.color.needsUpdate = true
  })

  return (
    <group>
      {/* Layer 0: Dark contrast halo */}
      <sprite position={[0, 0, -0.3]} scale={[5.15, 5.15, 1]} renderOrder={0}>
        <spriteMaterial
          map={backdropTexture}
          transparent={true}
          depthWrite={false}
          toneMapped={false}
        />
      </sprite>

      {/* Layer 1: Volumetric inner energy core */}
      <sprite ref={coreGlowRef} scale={[2.45, 2.45, 1]} renderOrder={1}>
        <spriteMaterial
          map={glowTexture}
          color="#67e8f9"
          transparent={true}
          opacity={0.38}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </sprite>

      {/* Layer 2: Gyroscopic & scanner rings */}
      <mesh ref={ring1Ref} rotation={[Math.PI * 0.32, 0.2, 0]} renderOrder={2}>
        <torusGeometry args={[2.06, 0.01, 12, 144]} />
        <meshBasicMaterial
          color="#67e8f9"
          transparent={true}
          opacity={0.25}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh ref={ring2Ref} rotation={[-Math.PI * 0.25, 0.5, Math.PI * 0.15]} renderOrder={2}>
        <torusGeometry args={[2.19, 0.007, 12, 144]} />
        <meshBasicMaterial
          color="#67e8f9"
          transparent={true}
          opacity={0.2}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh ref={ring3Ref} renderOrder={2}>
        <torusGeometry args={[1.74, 0.012, 12, 144]} />
        <meshBasicMaterial
          color="#ffffff"
          transparent={true}
          opacity={0}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      {/* Layer 3: Morphing 3D particle cloud */}
      <points ref={mesh} renderOrder={3}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
          <bufferAttribute attach="attributes-color" args={[colors, 3]} />
        </bufferGeometry>
        <pointsMaterial
          map={glowTexture}
          size={0.082}
          vertexColors={true}
          transparent={true}
          opacity={0.96}
          sizeAttenuation={true}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>
    </group>
  )
})

const SphereComponent = ({ count = 2600 }: ParticleSphereProps) => {
  return (
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
  )
}

export const Sphere = React.memo(SphereComponent, () => true)

export default Sphere
