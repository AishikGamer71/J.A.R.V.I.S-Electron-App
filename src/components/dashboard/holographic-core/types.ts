import type * as THREE from 'three'

/**
 * The 11 canonical cognitive and operational states of the J.A.R.V.I.S. Holographic Core.
 */
export type HolographicState =
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

/**
 * Backward-compatibility alias for the 11 visual states.
 */
export type JarvisVisualState = HolographicState

/**
 * Metadata associated with each holographic state for HUD and inspector display.
 */
export interface StateMetadata {
  key: string
  id: HolographicState
  colorName: string
  hex: string
  rgb: [number, number, number]
  normalizedRgb: [number, number, number]
  desc: string
}

/**
 * Normalized weights (0.0 to 1.0) for exponential state transitions.
 */
export type StateWeights = Record<HolographicState, number>

/**
 * Three-band audio frequency decomposition values (0.0 to 1.0).
 */
export interface AudioFrequencyBands {
  bass: number
  mid: number
  treble: number
}

/**
 * Shorthand alias for audio frequency bands.
 */
export type AudioBands = AudioFrequencyBands

/**
 * Precomputed geometry buffers and stochastic seed arrays for the particle cloud.
 */
export interface ParticleGeometryData {
  positions: Float32Array
  colors: Float32Array
  normals: Float32Array
  globeNormals: Float32Array
  cubeNormals: Float32Array
  thetas: Float32Array
  phis: Float32Array
  phases: Float32Array
  spreads: Float32Array
  colSeeds: Float32Array
}

/**
 * Shorthand alias for particle geometry data.
 */
export type ParticleBuffers = ParticleGeometryData

/**
 * Procedurally generated Canvas textures for the optical pipeline.
 */
export interface ProceduralTextures {
  glowTexture: THREE.CanvasTexture
  backdropTexture: THREE.CanvasTexture
}

/**
 * Comprehensive props accepted by the Holographic Core and Sphere wrapper.
 */
export interface SphereProps {
  /** Total number of particles distributed in the 3D Fibonacci cloud (default: 2600) */
  count?: number
  /** Explicit holographic visual state override (highest priority) */
  state?: HolographicState | string | null
  /** Alias for explicit holographic state override */
  overrideState?: HolographicState | string | null
  /** Legacy boolean flag: when true, maps to LISTENING */
  isListening?: boolean
  /** Legacy boolean flag: when true, maps to SPEAKING */
  isSpeaking?: boolean
  /** Legacy boolean flag: when true, maps to THINKING */
  isThinking?: boolean
  /** Active tool identifier string (mapped to WEB_SEARCH, DEEP_RESEARCH, CODING, etc.) */
  activeTool?: string | null
  /** Active camera / video feed indicator: when true, maps to VISION_SCAN */
  isVideoOn?: boolean
  /** Alias for active vision mode */
  visionActive?: boolean
  /** Error indicator or object: when present, maps to ALERT */
  error?: string | Error | null
  /** Direct audio level override (0.0 to 1.0) */
  audioLevel?: number
  /** Additional CSS class names for the outer container */
  className?: string
  /** Enable mouse/touch orbit drag controls */
  interactive?: boolean
  /** Automatically decay user camera rotation back to neutral orientation when released */
  autoReturn?: boolean
}

/**
 * Backward-compatibility alias for SphereProps.
 */
export type ParticleSphereProps = SphereProps

/**
 * Ring configuration parameters.
 */
export interface RingConfig {
  radius: number
  tube: number
  radialSegments: number
  tubularSegments: number
  baseOpacity: number
}

/**
 * Ring dynamic configuration state.
 */
export interface RingStateConfig {
  speed: number
  baseOpacity: number
  scaleRing1: number
  scaleRing2: number
  ring3Mode: 'inactive' | 'lidar' | 'radar'
}

/**
 * Configuration for concentric particle shells used in DEEP_RESEARCH state.
 */
export interface ParticleShellConfig {
  shellIndex: number
  scale: number
  spinVelocity: number
  tiltX?: number
  highlightBoost: number
}

