import React from 'react'
import { HolographicCoreScene } from './holographic-core/holographic-core-scene'
import type { ParticleSphereProps, SphereProps } from './holographic-core/types'

// Re-export complete public type system and constants
export * from './holographic-core/types'
export * from './holographic-core/constants'
export * from './holographic-core/procedural-textures'
export * from './holographic-core/geometries'
export * from './holographic-core/state-machine'
export * from './holographic-core/audio-bridge'
export * from './holographic-core/holographic-core-scene'

/**
 * Internal functional component wrapper for the 3D Holographic Core Scene.
 */
const SphereComponent: React.FC<SphereProps> = (props) => {
  return <HolographicCoreScene {...props} />
}

/**
 * Drop-in backward-compatible Sphere component with React.memo isolation.
 *
 * Prevents unnecessary WebGL canvas rebuilds when parent dashboard telemetry
 * (CPU, RAM, network stats, clock ticks) updates frequently, while allowing
 * re-renders if visual props change explicitly.
 */
export const Sphere = React.memo(SphereComponent, (prev, next) => {
  return (
    prev.state === next.state &&
    prev.overrideState === next.overrideState &&
    prev.count === next.count &&
    prev.interactive === next.interactive &&
    prev.className === next.className &&
    prev.isListening === next.isListening &&
    prev.isSpeaking === next.isSpeaking &&
    prev.isThinking === next.isThinking &&
    prev.activeTool === next.activeTool &&
    prev.isVideoOn === next.isVideoOn &&
    prev.visionActive === next.visionActive &&
    prev.error === next.error &&
    prev.audioLevel === next.audioLevel &&
    prev.autoReturn === next.autoReturn
  )
})

export default Sphere
