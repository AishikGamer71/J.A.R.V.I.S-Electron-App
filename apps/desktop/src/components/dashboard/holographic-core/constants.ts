import type { HolographicState, ParticleShellConfig, RingConfig, StateMetadata, StateWeights } from './types'

/** Base radius of the 3D Fibonacci sphere in Three.js world units */
export const BASE_RADIUS = 1.72

/** Default number of particles in the primary cloud */
export const DEFAULT_PARTICLE_COUNT = 2600

/** Camera configuration */
export const CAMERA_POSITION: [number, number, number] = [0, 0, 5.1]
export const CAMERA_FOV = 58

/** Pitch clamping limits for orbit drag (±60 degrees in radians) */
export const MAX_PITCH_ANGLE = 1.05

/**
 * 11 Canonical States of the J.A.R.V.I.S Holographic Core
 */
export const JARVIS_STATES: StateMetadata[] = [
  {
    key: '1',
    id: 'IDLE',
    colorName: 'Ice-Cyan',
    hex: '#67e8f9',
    rgb: [103, 232, 249],
    normalizedRgb: [0.40392, 0.90980, 0.97647],
    desc: 'Calm breathing surface wave, slow axial drift, soft dual rings',
  },
  {
    key: '2',
    id: 'LISTENING',
    colorName: 'Sky-Cyan',
    hex: '#00f0ff',
    rgb: [0, 240, 255],
    normalizedRgb: [0.00000, 0.94118, 1.00000],
    desc: 'Inward focus contraction + concentric equatorial-to-polar sonar ripples + live mic reactivity',
  },
  {
    key: '3',
    id: 'THINKING',
    colorName: 'Amber-Gold',
    hex: '#fbbf24',
    rgb: [251, 191, 36],
    normalizedRgb: [0.98431, 0.74902, 0.14118],
    desc: 'Counter-twisting hemisphere vortex + 3D spherical-harmonic lobes + fast gyroscope rings',
  },
  {
    key: '4',
    id: 'SPEAKING',
    colorName: 'White-Ice',
    hex: '#e0f2fe',
    rgb: [224, 242, 254],
    normalizedRgb: [0.87843, 0.94902, 0.99608],
    desc: 'Multi-band audio reactivity (bass core punch, mid standing waves, treble corona spikes)',
  },
  {
    key: '5',
    id: 'WEB_SEARCH',
    colorName: 'Cyber Azure',
    hex: '#38bdf8',
    rgb: [56, 189, 248],
    normalizedRgb: [0.21961, 0.74118, 0.97255],
    desc: '3D planetary lat/lon wireframe globe on a 23.5° axial tilt with a sweeping meridian radar beam and live search-hit data pings',
  },
  {
    key: '6',
    id: 'DEEP_RESEARCH',
    colorName: 'Periwinkle',
    hex: '#818cf8',
    rgb: [129, 140, 248],
    normalizedRgb: [0.50588, 0.54902, 0.97255],
    desc: 'Sphere splits into 3 nested counter-rotating concentric knowledge shells (core, tilted mid-shell, outer halo)',
  },
  {
    key: '7',
    id: 'CODING',
    colorName: 'Matrix Mint',
    hex: '#4ade80',
    rgb: [74, 222, 128],
    normalizedRgb: [0.29020, 0.87059, 0.50196],
    desc: 'Morphs into a beveled 3D holo-cube with cascading vertical digital code streams down its faces',
  },
  {
    key: '8',
    id: 'VISION_SCAN',
    colorName: 'Laser Rose',
    hex: '#f472b6',
    rgb: [244, 114, 182],
    normalizedRgb: [0.95686, 0.44706, 0.71373],
    desc: 'Precision horizontal optical lidar ring & laser plane sweeping smoothly from top pole to bottom pole',
  },
  {
    key: '9',
    id: 'MEMORY_SYNC',
    colorName: 'Teal-Cyan',
    hex: '#2dd4bf',
    rgb: [45, 212, 191],
    normalizedRgb: [0.17647, 0.83137, 0.74902],
    desc: 'Opens a central polar tunnel into an Arc-Reactor 3D torus with continuous poloidal particle flow',
  },
  {
    key: '0',
    id: 'EXECUTING_TOOL',
    colorName: 'Neon Violet',
    hex: '#c084fc',
    rgb: [192, 132, 252],
    normalizedRgb: [0.75294, 0.51765, 0.98824],
    desc: 'High-speed multi-axis spin with crisp octupole geometric facets',
  },
  {
    key: '-',
    id: 'ALERT',
    colorName: 'Crimson-Coral',
    hex: '#fb7185',
    rgb: [251, 113, 133],
    normalizedRgb: [0.98431, 0.44314, 0.52157],
    desc: 'Urgent twin-beat cardiac shockwave (lub-dub) with sharp radial warning spikes',
  },
]

/**
 * Canonical hex colors indexed by HolographicState.
 */
export const STATE_COLORS: Record<HolographicState, string> = {
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

/**
 * Array of state keys.
 */
export const STATE_KEYS: HolographicState[] = [
  'IDLE',
  'LISTENING',
  'THINKING',
  'SPEAKING',
  'WEB_SEARCH',
  'DEEP_RESEARCH',
  'CODING',
  'VISION_SCAN',
  'MEMORY_SYNC',
  'EXECUTING_TOOL',
  'ALERT',
]

/**
 * Keyboard shortcut mapping to state IDs.
 */
export const KEY_STATE_MAP: Record<string, HolographicState> = {
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

/**
 * Gyroscopic and scanner ring geometric configurations.
 */
export const RING1_CONFIG: RingConfig = {
  radius: 2.06,
  tube: 0.01,
  radialSegments: 12,
  tubularSegments: 144,
  baseOpacity: 0.25,
}

export const RING2_CONFIG: RingConfig = {
  radius: 2.19,
  tube: 0.007,
  radialSegments: 12,
  tubularSegments: 144,
  baseOpacity: 0.2,
}

export const RING3_CONFIG: RingConfig = {
  radius: 1.74,
  tube: 0.012,
  radialSegments: 12,
  tubularSegments: 144,
  baseOpacity: 0.0,
}

/**
 * Initial ring rotations in radians [pitch, yaw, roll].
 */
export const RING1_INITIAL_ROTATION: [number, number, number] = [Math.PI * 0.32, 0.2, 0]
export const RING2_INITIAL_ROTATION: [number, number, number] = [
  -Math.PI * 0.25,
  0.5,
  Math.PI * 0.15,
]
export const RING3_INITIAL_ROTATION: [number, number, number] = [0, 0, 0]

/**
 * Initial default state weights (IDLE active).
 */
export const DEFAULT_STATE_WEIGHTS: StateWeights = {
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
}

/**
 * Concentric shell configuration for DEEP_RESEARCH state.
 */
export const PARTICLE_SHELLS: ParticleShellConfig[] = [
  { shellIndex: 0, scale: 0.52, spinVelocity: 1.35, highlightBoost: 0.55 },
  { shellIndex: 1, scale: 0.88, spinVelocity: -0.85, tiltX: 0.48, highlightBoost: 0.15 },
  { shellIndex: 2, scale: 1.2, spinVelocity: 0.42, highlightBoost: 0.15 },
]

