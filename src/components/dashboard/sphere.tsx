import { Canvas, useFrame } from '@react-three/fiber'
import { useRef, useMemo, useEffect } from 'react'
import * as THREE from 'three'
import { jarvisService } from '@/services/jarvis-voice-ai'

const CustomParticleSphere = ({ count = 1000 }) => {
  const mesh = useRef<THREE.Points>(null)

  const dataArray = useMemo(() => new Uint8Array(128), [])

  const colorIdle = useMemo(() => new THREE.Color('#10b981'), [])
  const colorListen = useMemo(() => new THREE.Color('#06b6d4'), [])
  const colorThinking = useMemo(() => new THREE.Color('#f59e0b'), [])
  const colorTool = useMemo(() => new THREE.Color('#a855f7'), [])
  const colorSpeaking = useMemo(() => new THREE.Color('#ffffff'), [])
  const colorTarget = useMemo(() => new THREE.Color(), [])

  const { positions, originalPositions, spreadFactors } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const orig = new Float32Array(count * 3)
    const spread = new Float32Array(count)

    for (let i = 0; i < count; i++) {
      const x = Math.random() * 2 - 1
      const y = Math.random() * 2 - 1
      const z = Math.random() * 2 - 1

      const vector = new THREE.Vector3(x, y, z)
      vector.normalize().multiplyScalar(2)

      pos[i * 3] = vector.x
      pos[i * 3 + 1] = vector.y
      pos[i * 3 + 2] = vector.z

      orig[i * 3] = vector.x
      orig[i * 3 + 1] = vector.y
      orig[i * 3 + 2] = vector.z

      spread[i] = Math.random()
    }
    return { positions: pos, originalPositions: orig, spreadFactors: spread }
  }, [count])

  // Track agent state dynamically ('IDLE', 'LISTENING', 'THINKING', 'EXECUTING_TOOL', 'SPEAKING')
  const agentStateRef = useRef<string>('IDLE')
  useEffect(() => {
    const handleState = (e: any) => {
      agentStateRef.current = String(e.detail || 'IDLE').toUpperCase()
    }
    window.addEventListener('jarvis-state', handleState)
    return () => window.removeEventListener('jarvis-state', handleState)
  }, [])

  const currentVolume = useRef(0)

  useFrame((state, delta) => {
    if (!state.clock.running || !mesh.current) return

    const agentState = agentStateRef.current
    const isSpeaking = agentState === 'SPEAKING'
    const isThinking = agentState === 'THINKING'
    const isTool = agentState === 'EXECUTING_TOOL'
    const isListening = agentState === 'LISTENING'

    // Adjust rotation speed depending on state
    const speedMult = isThinking ? 3.0 : isTool ? 4.5 : isSpeaking ? 2.0 : 1.0
    mesh.current.rotation.y += delta * 0.05 * speedMult
    mesh.current.rotation.z += delta * 0.03 * speedMult

    // Measure real audio frequency volume if analyser is active
    let audioVol = 0
    if (jarvisService.analyser) {
      try {
        jarvisService.analyser.getByteFrequencyData(dataArray)
        let sum = 0
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i]
        }
        audioVol = sum / (dataArray.length * 255)
      } catch {
        // ignore
      }
    }

    // Smoothly animate volume / amplitude towards target
    const targetVolume = isSpeaking
      ? Math.max(0.65, audioVol * 2.5)
      : audioVol > 0.05
      ? audioVol * 2.0
      : isThinking || isTool
      ? 0.35 + Math.sin(state.clock.elapsedTime * 6) * 0.15
      : 0
    currentVolume.current += (targetVolume - currentVolume.current) * 0.15
    const volume = currentVolume.current

    // Dynamically blend colors according to active state
    let baseColor = colorIdle
    if (isListening) baseColor = colorListen
    else if (isThinking) baseColor = colorThinking
    else if (isTool) baseColor = colorTool
    else if (isSpeaking) baseColor = colorSpeaking

    colorTarget.lerpColors(baseColor, colorSpeaking, Math.min(1, volume * 1.5))
    ;(mesh.current.material as THREE.PointsMaterial).color.copy(colorTarget)

    const currentPos = mesh.current.geometry.attributes.position.array as Float32Array

    for (let i = 0; i < count; i++) {
      const ix = i * 3
      const iy = i * 3 + 1
      const iz = i * 3 + 2

      const expansion = 1 + volume * spreadFactors[i] * 0.4

      currentPos[ix] = originalPositions[ix] * expansion
      currentPos[iy] = originalPositions[iy] * expansion
      currentPos[iz] = originalPositions[iz] * expansion
    }

    mesh.current.geometry.attributes.position.needsUpdate = true
  })

  return (
    <points ref={mesh}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color="#00F0FF"
        size={0.012}
        transparent={true}
        opacity={0.9}
        sizeAttenuation={true}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  )
}

const Sphere = () => {
  return (
    <Canvas
      camera={{ position: [0, 0, 4.5] }}
      dpr={[1, 1.5]}
      performance={{ min: 0.5 }}
      gl={{ antialias: false, powerPreference: 'high-performance' }}
    >
      <ambientLight intensity={0.6} />
      <CustomParticleSphere />
    </Canvas>
  )
}

export default Sphere

