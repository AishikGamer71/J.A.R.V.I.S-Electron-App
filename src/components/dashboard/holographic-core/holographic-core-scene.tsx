import React, { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { jarvisRealtimeRef } from '@/services/jarvisBridge'
import {
  BASE_RADIUS,
  CAMERA_FOV,
  CAMERA_POSITION,
  DEFAULT_PARTICLE_COUNT,
  KEY_STATE_MAP,
  MAX_PITCH_ANGLE,
  RING1_CONFIG,
  RING1_INITIAL_ROTATION,
  RING2_CONFIG,
  RING2_INITIAL_ROTATION,
  RING3_CONFIG,
  RING3_INITIAL_ROTATION,
  STATE_COLORS,
  STATE_KEYS,
} from './constants'
import { buildParticleGeometryData } from './geometries'
import { createProceduralTextures, disposeProceduralTextures } from './procedural-textures'
import {
  calculateBaseRingOpacity,
  calculateCardiacBeat,
  calculateCoreOpacity,
  calculateCoreScale,
  calculateRingSpeed,
  createDefaultStateWeights,
  resolveActiveState,
  StateTransitionPulseTracker,
  unpackJarvisStateDetail,
  updateStateWeights,
  VisualizerStateArbitrator,
  ALERT_DWELL_MS,
  TOOL_DWELL_MS,
  TOOL_TIMEOUT_MS,
} from './state-machine'
import { AudioReactivityBridge } from './audio-bridge'
import type { HolographicState, SphereProps } from './types'

interface HolographicCoreInnerProps extends SphereProps {
  particleCount: number
}

const HolographicCoreInner: React.FC<HolographicCoreInnerProps> = (props) => {
  const { particleCount, interactive = true, autoReturn = false } = props

  const rootGroup = useRef<THREE.Group>(null)
  const mesh = useRef<THREE.Points>(null)
  const coreGlowRef = useRef<THREE.Sprite>(null)
  const ring1Ref = useRef<THREE.Mesh>(null)
  const ring2Ref = useRef<THREE.Mesh>(null)
  const ring3Ref = useRef<THREE.Mesh>(null)

  // Drag orbit state
  const isDragging = useRef(false)
  const prevPointer = useRef({ x: 0, y: 0 })
  const targetRotX = useRef(0)
  const targetRotY = useRef(0)

  // Three.js renderer reference for pointer events
  const { gl } = useThree()

  // Procedural CanvasTextures (generated once, disposed on unmount)
  const textures = useMemo(() => createProceduralTextures(), [])
  useEffect(() => {
    return () => {
      disposeProceduralTextures(textures)
    }
  }, [textures])

  // Color palette lookup map
  const palette = useMemo(() => {
    const map = {} as Record<HolographicState, THREE.Color>
    for (let i = 0; i < STATE_KEYS.length; i++) {
      const key = STATE_KEYS[i]
      map[key] = new THREE.Color(STATE_COLORS[key])
    }
    return map
  }, [])

  const blendedColor = useMemo(() => new THREE.Color(STATE_COLORS.IDLE), [])
  const whiteColor = useMemo(() => new THREE.Color('#ffffff'), [])

  // Precomputed geometry buffers
  const particleData = useMemo(() => {
    return buildParticleGeometryData(particleCount, BASE_RADIUS)
  }, [particleCount])

  // Subsystems
  const audioBridge = useMemo(() => new AudioReactivityBridge(), [])
  const pulseTracker = useMemo(() => new StateTransitionPulseTracker(), [])
  const arbitrator = useMemo(() => new VisualizerStateArbitrator(), [])
  const weights = useRef(createDefaultStateWeights())

  // Event bus and keyboard shortcut listener with automatic expiration decay
  const realtimeBusState = useRef<string | null>(null)
  const busTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const setDecayingRealtimeState = (state: string | null) => {
    realtimeBusState.current = state
    if (busTimerRef.current) {
      clearTimeout(busTimerRef.current)
      busTimerRef.current = null
    }
    if (!state || state === 'IDLE') {
      realtimeBusState.current = null
      return
    }
    const dwell = state === 'ALERT'
      ? ALERT_DWELL_MS
      : (state === 'WEB_SEARCH' || state === 'DEEP_RESEARCH' || state === 'CODING' || state === 'MEMORY_SYNC' || state === 'EXECUTING_TOOL')
        ? TOOL_DWELL_MS
        : 3000

    busTimerRef.current = setTimeout(() => {
      realtimeBusState.current = null
      busTimerRef.current = null
    }, dwell)
  }

  useEffect(() => {
    const handleJarvisState = (e: Event) => {
      const unpacked = unpackJarvisStateDetail((e as CustomEvent).detail)
      if (unpacked) {
        if (unpacked === 'ALERT') {
          arbitrator.triggerAlert()
        }
        setDecayingRealtimeState(unpacked)
      }
    }

    const handleToolCall = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail && detail.tool) {
        if (detail.phase === 'start') {
          arbitrator.onToolStart(detail.tool)
        } else if (detail.phase === 'result') {
          arbitrator.onToolResult()
        }
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.altKey || e.metaKey) return
      const target = e.target as HTMLElement | null
      if (!target) return
      const tag = target.tagName?.toUpperCase()
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (target.isContentEditable || (target as any).contentEditable === 'true' || target.getAttribute?.('contenteditable') === 'true') return
      if (target.closest && target.closest('[contenteditable="true"], [contenteditable=""], [contenteditable], .monaco-editor, .xterm, [role="textbox"]')) return

      const mapped = KEY_STATE_MAP[e.key]
      if (mapped) {
        if (mapped === 'ALERT') {
          arbitrator.triggerAlert()
        }
        setDecayingRealtimeState(mapped)
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))
      }
    }

    window.addEventListener('jarvis-state', handleJarvisState)
    window.addEventListener('jarvis-tool-call', handleToolCall)
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      if (busTimerRef.current) {
        clearTimeout(busTimerRef.current)
        busTimerRef.current = null
      }
      window.removeEventListener('jarvis-state', handleJarvisState)
      window.removeEventListener('jarvis-tool-call', handleToolCall)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [arbitrator])

  // Pointer drag orbit event listeners
  useEffect(() => {
    if (!interactive) return

    const dom = gl.domElement

    const onPointerDown = (e: PointerEvent) => {
      isDragging.current = true
      prevPointer.current = { x: e.clientX, y: e.clientY }
    }

    const onPointerMove = (e: PointerEvent) => {
      if (!isDragging.current) return
      const dx = e.clientX - prevPointer.current.x
      const dy = e.clientY - prevPointer.current.y
      prevPointer.current = { x: e.clientX, y: e.clientY }

      targetRotY.current += dx * 0.005
      targetRotX.current = Math.max(
        -MAX_PITCH_ANGLE,
        Math.min(MAX_PITCH_ANGLE, targetRotX.current + dy * 0.005)
      )
    }

    const onPointerUp = () => {
      isDragging.current = false
    }

    dom.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
    window.addEventListener('pointercancel', onPointerUp)

    return () => {
      dom.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerup', onPointerUp)
      window.removeEventListener('pointercancel', onPointerUp)
    }
  }, [gl, interactive])

  // 60 FPS Animation Render Loop
  useFrame((state, delta) => {
    if (!state.clock.running || !mesh.current || !rootGroup.current) return

    const t = state.clock.elapsedTime
    const dt = Math.min(0.05, delta)

    // 1. Resolve active state using 7-level arbitrator with dwell & safety timeouts
    const realtimeVoice = jarvisRealtimeRef.voiceState === 'SPEAKING'
      ? 'SPEAKING'
      : (realtimeBusState.current || jarvisRealtimeRef.voiceState)
    const active = arbitrator.resolve(props, realtimeBusState.current, realtimeVoice)

    // 2. Exponential damping of weights: damp = 1 - Math.exp(-6.2 * dt)
    const { damp } = updateStateWeights(weights.current, active, dt)
    const w = weights.current

    // 3. Audio Reactivity Bridge update
    const { bass, mid, treble } = audioBridge.update(dt, t, active, props.audioLevel)

    // 4. Cardiac shockwave & transition pulse
    const alertBeat = calculateCardiacBeat(t)
    const pulse = pulseTracker.update(active, dt)

    // 5. Blended Color lerp
    blendedColor.lerp(palette[active], damp)
    const sr = blendedColor.r
    const sg = blendedColor.g
    const sb = blendedColor.b

    // 6. User Orbit Drag pitch & yaw damping
    rootGroup.current.rotation.x += (targetRotX.current - rootGroup.current.rotation.x) * 0.15
    rootGroup.current.rotation.y += (targetRotY.current - rootGroup.current.rotation.y) * 0.15

    if (autoReturn && !isDragging.current) {
      targetRotX.current += (0 - targetRotX.current) * (1 - Math.exp(-1.5 * dt))
      targetRotY.current += (0 - targetRotY.current) * (1 - Math.exp(-1.5 * dt))
    }

    // 7. State-specific 3D orientation & angular velocities on particle cloud
    const pointsMesh = mesh.current
    if (active === 'LISTENING' || active === 'VISION_SCAN') {
      pointsMesh.rotation.y += dt * 0.18
      pointsMesh.rotation.x += (0.08 - pointsMesh.rotation.x) * damp
      pointsMesh.rotation.z += (0.0 - pointsMesh.rotation.z) * damp
    } else if (active === 'WEB_SEARCH') {
      pointsMesh.rotation.y += dt * 0.38
      pointsMesh.rotation.x += (0.18 - pointsMesh.rotation.x) * damp
      pointsMesh.rotation.z += (-0.38 - pointsMesh.rotation.z) * damp
    } else if (active === 'MEMORY_SYNC') {
      pointsMesh.rotation.y += dt * 0.32
      pointsMesh.rotation.x += (0.58 - pointsMesh.rotation.x) * damp
      pointsMesh.rotation.z += (Math.sin(t * 0.6) * 0.12 - pointsMesh.rotation.z) * damp
    } else if (active === 'CODING') {
      pointsMesh.rotation.y += dt * 0.34
      pointsMesh.rotation.x += (0.42 - pointsMesh.rotation.x) * damp
      pointsMesh.rotation.z += (0.18 - pointsMesh.rotation.z) * damp
    } else if (active === 'THINKING') {
      pointsMesh.rotation.y += dt * 0.72
      pointsMesh.rotation.x += dt * 0.32
      pointsMesh.rotation.z += dt * 0.24
    } else if (active === 'SPEAKING') {
      pointsMesh.rotation.y += dt * (0.28 + bass * 0.65)
      pointsMesh.rotation.x += (Math.sin(t * 1.8) * 0.15 - pointsMesh.rotation.x) * damp
      pointsMesh.rotation.z += dt * 0.08
    } else if (active === 'EXECUTING_TOOL') {
      pointsMesh.rotation.y += dt * 0.95
      pointsMesh.rotation.z += dt * 0.45
    } else if (active === 'ALERT') {
      pointsMesh.rotation.y += dt * 0.55
      pointsMesh.rotation.x += (Math.sin(t * 9.0) * 0.06 - pointsMesh.rotation.x) * damp
    } else {
      // IDLE and default
      pointsMesh.rotation.y += dt * 0.15
      pointsMesh.rotation.x += (Math.sin(t * 0.4) * 0.08 - pointsMesh.rotation.x) * damp
      pointsMesh.rotation.z += dt * 0.04
    }

    // 8. Update Layer 1: Volumetric Core Glow Sprite
    if (coreGlowRef.current) {
      let coreScale = calculateCoreScale(w, t, bass, alertBeat)
      if (pulse.active) {
        coreScale *= pulse.scale
      }
      coreGlowRef.current.scale.set(coreScale, coreScale, 1)

      const coreMat = coreGlowRef.current.material as THREE.SpriteMaterial
      coreMat.color.copy(blendedColor)
      coreMat.opacity = calculateCoreOpacity(w, bass, alertBeat) + (pulse.active ? pulse.opacity * 0.2 : 0)
    }

    // 9. Update Layer 2: Gyroscopic & Scanner Rings
    const scanY = Math.sin(t * 2.1) * 0.94
    const radarAngle = ((t * 2.4) % (Math.PI * 2)) - Math.PI

    if (ring1Ref.current && ring2Ref.current && ring3Ref.current) {
      const r1Mat = ring1Ref.current.material as THREE.MeshBasicMaterial
      const r2Mat = ring2Ref.current.material as THREE.MeshBasicMaterial
      const r3Mat = ring3Ref.current.material as THREE.MeshBasicMaterial

      r1Mat.color.copy(blendedColor)
      r2Mat.color.copy(blendedColor)
      r3Mat.color.copy(whiteColor).lerp(blendedColor, 0.35)

      const baseRingOpacity = calculateBaseRingOpacity(w, alertBeat)
      r1Mat.opacity = baseRingOpacity
      r2Mat.opacity = baseRingOpacity * 0.78

      const ringSpeed = calculateRingSpeed(w)
      ring1Ref.current.rotation.x += dt * ringSpeed
      ring1Ref.current.rotation.y += dt * ringSpeed * 0.6
      ring2Ref.current.rotation.y -= dt * ringSpeed * 0.85
      ring2Ref.current.rotation.z += dt * ringSpeed * 0.55

      ring1Ref.current.scale.setScalar(
        1 + w.SPEAKING * bass * 0.16 + w.LISTENING * bass * 0.08 + w.ALERT * alertBeat * 0.12
      )
      ring2Ref.current.scale.setScalar(1 + w.SPEAKING * mid * 0.14 + w.DEEP_RESEARCH * 0.08)

      // Ring 3 Mode: VISION_SCAN Lidar Slicing or WEB_SEARCH Radar Reference Plane
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

    // 10. Update Layer 3: Particle Cloud 3D Morphing & Vertex Displacements
    const posArr = pointsMesh.geometry.attributes.position.array as Float32Array
    const colArr = pointsMesh.geometry.attributes.color.array as Float32Array
    const {
      normals,
      globeNormals,
      cubeNormals,
      thetas,
      phis,
      phases,
      spreads,
      colSeeds,
    } = particleData

    for (let i = 0; i < particleCount; i++) {
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

      // THINKING: Hemisphere Vortex Counter-Twist
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

      // WEB_SEARCH: Quantized Lat/Lon Hologram Globe & Radar Beam Sweep
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

      // DEEP_RESEARCH: 3 Nested Concentric Counter-Spinning Knowledge Shells
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

      // CODING: Beveled 3D Holo-Cube & Cascading Digital Code Stream
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

      // MEMORY_SYNC: Arc-Reactor 3D Torus Poloidal Circulation
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

      // State Harmonic & Acoustic Displacements
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

      // Linear RGB vertex color modulation with crest radiance & twinkle
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

    pointsMesh.geometry.attributes.position.needsUpdate = true
    pointsMesh.geometry.attributes.color.needsUpdate = true
  })

  return (
    <group ref={rootGroup}>
      {/* Layer 0: Dark Contrast Backdrop Halo (First in renderOrder) */}
      <sprite position={[0, 0, -0.3]} scale={[5.15, 5.15, 1]} renderOrder={0}>
        <spriteMaterial
          map={textures.backdropTexture}
          transparent={true}
          depthWrite={false}
          toneMapped={false}
        />
      </sprite>

      {/* Layer 1: Volumetric Inner Energy Core (renderOrder 1) */}
      <sprite ref={coreGlowRef} scale={[2.45, 2.45, 1]} renderOrder={1}>
        <spriteMaterial
          map={textures.glowTexture}
          color={STATE_COLORS.IDLE}
          transparent={true}
          opacity={0.38}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </sprite>

      {/* Layer 2: Gyroscopic & Scanner Rings (renderOrder 2) */}
      <mesh ref={ring1Ref} rotation={RING1_INITIAL_ROTATION} renderOrder={2}>
        <torusGeometry
          args={[
            RING1_CONFIG.radius,
            RING1_CONFIG.tube,
            RING1_CONFIG.radialSegments,
            RING1_CONFIG.tubularSegments,
          ]}
        />
        <meshBasicMaterial
          color={STATE_COLORS.IDLE}
          transparent={true}
          opacity={RING1_CONFIG.baseOpacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh ref={ring2Ref} rotation={RING2_INITIAL_ROTATION} renderOrder={2}>
        <torusGeometry
          args={[
            RING2_CONFIG.radius,
            RING2_CONFIG.tube,
            RING2_CONFIG.radialSegments,
            RING2_CONFIG.tubularSegments,
          ]}
        />
        <meshBasicMaterial
          color={STATE_COLORS.IDLE}
          transparent={true}
          opacity={RING2_CONFIG.baseOpacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      <mesh ref={ring3Ref} rotation={RING3_INITIAL_ROTATION} renderOrder={2}>
        <torusGeometry
          args={[
            RING3_CONFIG.radius,
            RING3_CONFIG.tube,
            RING3_CONFIG.radialSegments,
            RING3_CONFIG.tubularSegments,
          ]}
        />
        <meshBasicMaterial
          color="#ffffff"
          transparent={true}
          opacity={RING3_CONFIG.baseOpacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      {/* Layer 3: Morphing 3D Fibonacci Particle Cloud (renderOrder 3) */}
      <points ref={mesh} renderOrder={3}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[particleData.positions, 3]} />
          <bufferAttribute attach="attributes-color" args={[particleData.colors, 3]} />
        </bufferGeometry>
        <pointsMaterial
          map={textures.glowTexture}
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
}

/**
 * 3D Holographic Core Scene.
 * Top-level Canvas wrapper handling WebGL lifecycle and safe Electron rendering.
 */
export const HolographicCoreScene: React.FC<SphereProps> = (props) => {
  const { count = DEFAULT_PARTICLE_COUNT, className = 'w-full h-full' } = props

  return (
    <Canvas
      className={className}
      camera={{ position: CAMERA_POSITION, fov: CAMERA_FOV }}
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
      <HolographicCoreInner {...props} particleCount={count} />
    </Canvas>
  )
}

export default HolographicCoreScene
