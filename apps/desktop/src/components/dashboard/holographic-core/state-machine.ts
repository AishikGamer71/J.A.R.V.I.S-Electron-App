import { STATE_COLORS, STATE_KEYS } from './constants'
import type { HolographicState, SphereProps, StateWeights } from './types'
import { jarvisRealtimeRef } from '@/services/jarvisBridge'

/**
 * Maps common raw event / backend state strings and aliases to valid HolographicStates.
 */
export function normalizeStateName(raw: string | null | undefined): HolographicState | null {
  if (!raw || typeof raw !== 'string') return null
  const upper = raw.trim().toUpperCase()

  // Exact match
  if (upper in STATE_COLORS) {
    return upper as HolographicState
  }

  // Aliases from backend events and legacy services
  switch (upper) {
    case 'LISTEN':
    case 'HEARING':
    case 'HEAR':
    case 'WAKE':
    case 'WAKE_WORD':
    case 'WAKE_WORD_DETECTED':
      return 'LISTENING'
    case 'THINK':
    case 'PROCESSING':
    case 'REASONING':
    case 'REASON':
    case 'TRANSCRIBING':
    case 'TRANSCRIBE':
    case 'COMPRESSING':
    case 'COMPRESS':
      return 'THINKING'
    case 'SPEAK':
    case 'TALKING':
    case 'TALK':
      return 'SPEAKING'
    case 'SEARCH':
    case 'WEB':
    case 'BROWSE':
      return 'WEB_SEARCH'
    case 'RESEARCH':
    case 'DEEP':
      return 'DEEP_RESEARCH'
    case 'CODE':
    case 'CODING_TOOL':
      return 'CODING'
    case 'VISION':
    case 'SCAN':
    case 'CAMERA':
      return 'VISION_SCAN'
    case 'MEMORY':
    case 'SYNC':
    case 'RECALL':
      return 'MEMORY_SYNC'
    case 'TOOL':
    case 'EXECUTE':
    case 'EXECUTING':
      return 'EXECUTING_TOOL'
    case 'ERROR':
    case 'WARN':
    case 'WARNING':
    case 'CRITICAL':
      return 'ALERT'
    case 'STANDBY':
    case 'DEFAULT':
      return 'IDLE'
    default:
      return null
  }
}

/**
 * Minimum dwell duration for completed tool state before returning to thinking/idle (2000ms).
 */
export const TOOL_DWELL_MS = 2000

/**
 * Safety timeout if an active tool hangs without emitting result (20000ms).
 */
export const TOOL_TIMEOUT_MS = 20000

/**
 * Minimum dwell duration for non-modal transient alerts (4000ms).
 */
export const ALERT_DWELL_MS = 4000

/**
 * Speech decay tail duration after audio ends (350ms).
 */
export const SPEECH_DECAY_MS = 350

/**
 * Classifies tool execution strings into one of the 11 HolographicStates.
 */
export function classifyToolState(toolName: string | null | undefined): HolographicState {
  if (!toolName || typeof toolName !== 'string') return 'EXECUTING_TOOL'
  const trimmed = toolName.trim()
  if (!trimmed) return 'EXECUTING_TOOL'
  const upper = trimmed.toUpperCase()
  if (upper in STATE_COLORS) {
    return upper as HolographicState
  }
  const tool = trimmed.toLowerCase()

  // 1. DEEP_RESEARCH (checked before WEB_SEARCH to prevent 'gpt_researcher' collision)
  if (
    /^(gpt_researcher|delegate_task|deep_investigate|data_analyzer)/i.test(tool) ||
    /(?:^|[_\W])(deep_research|researcher?|delegate_task|delegate|investigate|investigation|analyzer?|analysis)(?:[_\W]|$)/i.test(tool)
  ) {
    return 'DEEP_RESEARCH'
  }

  // 2. VISION_SCAN (checked early so vision tools aren't misclassified)
  if (
    /^(camera|mediapipe|deepface|vision|agent_s3|windows_mcp_snapshot|lidar)/i.test(tool) ||
    /(?:^|[_\W])(camera|mediapipe|deepface|vision|lidar|face_mesh|depth_scan)(?:[_\W]|$)/i.test(tool)
  ) {
    return 'VISION_SCAN'
  }

  // 3. MEMORY_SYNC (checked before WEB_SEARCH to prevent 'session_search' collision)
  if (
    /^(memory|state_db|session|sqlite|savecorememory|retrievecorememory|savecore|retrievecore|vector_store)/i.test(tool) ||
    /(?:^|[_\W])(memory|state_db|sqlite|savecore|retrievecore|recall|checkpoint|vector_store|vectordb)(?:[_\W]|$)/i.test(tool)
  ) {
    return 'MEMORY_SYNC'
  }

  // 4. WEB_SEARCH
  if (
    /^(crawl4ai|browser_use|\/search|google|web_scrape)/i.test(tool) ||
    /(?:^|[_\W])(search|browse|browser|crawl|crawler|scrape|scraper|google|web)(?:[_\W]|$)/i.test(tool)
  ) {
    return 'WEB_SEARCH'
  }

  // 5. CODING
  if (
    /^(markitdown|code_|terminal_|shell_|bash_|file_edit)/i.test(tool) ||
    /(?:^|[_\W])(markitdown|code|coding|terminal|bash|shell|editor|edit|interpreter|exec_py)(?:[_\W]|$)/i.test(tool)
  ) {
    return 'CODING'
  }

  // 6. Generic Fallback
  return 'EXECUTING_TOOL'
}

/**
 * 7-Level Priority Arbitration Engine to determine the active HolographicState:
 *
 * 1. Explicit overrideState or state prop
 * 2. ALERT (Priority 100): props.error or realtime ALERT
 * 3. VISION_SCAN (Priority 90): props.isVideoOn, visionActive, or vision tool
 * 4. SPEAKING (Priority 80): props.isSpeaking or realtime SPEAKING (preempts tool)
 * 5. ACTIVE_TOOL (Priority 70): props.activeTool or realtime tool state
 * 6. THINKING (Priority 60): props.isThinking or realtime THINKING
 * 7. LISTENING (Priority 50): props.isListening or realtime LISTENING
 * 8. Realtime / Event bus fallback
 * 9. Default IDLE (Priority 10)
 */
export function resolveActiveState(
  props: SphereProps,
  realtimeVoiceState?: string | null
): HolographicState {
  // Level 1: Explicit Override (highest precedence)
  const explicit = props.overrideState ?? props.state
  if (explicit) {
    const normalized = normalizeStateName(String(explicit))
    if (normalized) return normalized
  }

  // Level 2: ALERT (Priority 100)
  if (props.error) {
    return 'ALERT'
  }
  const normalizedRealtime = normalizeStateName(realtimeVoiceState)
  if (normalizedRealtime === 'ALERT') {
    return 'ALERT'
  }

  // Level 3: VISION_SCAN (Priority 90)
  if (props.isVideoOn || props.visionActive) {
    return 'VISION_SCAN'
  }
  if (normalizedRealtime === 'VISION_SCAN') {
    return 'VISION_SCAN'
  }
  if (props.activeTool && typeof props.activeTool === 'string' && props.activeTool.trim() !== '') {
    const mappedTool = classifyToolState(props.activeTool)
    if (mappedTool === 'VISION_SCAN') return 'VISION_SCAN'
  }

  // Level 4: SPEAKING (Priority 80)
  // SPEAKING takes precedence over active tool execution unconditionally.
  // jarvisRealtimeRef is checked to prevent shadowing by stale event bus.
  if (
    props.isSpeaking ||
    normalizedRealtime === 'SPEAKING' ||
    (typeof jarvisRealtimeRef !== 'undefined' &&
      (jarvisRealtimeRef.voiceState === 'SPEAKING' || jarvisRealtimeRef.isSpeaking))
  ) {
    return 'SPEAKING'
  }

  // Level 5: ACTIVE_TOOL (Priority 70)
  if (props.activeTool && typeof props.activeTool === 'string' && props.activeTool.trim() !== '') {
    return classifyToolState(props.activeTool)
  }
  if (
    normalizedRealtime === 'WEB_SEARCH' ||
    normalizedRealtime === 'DEEP_RESEARCH' ||
    normalizedRealtime === 'CODING' ||
    normalizedRealtime === 'MEMORY_SYNC' ||
    normalizedRealtime === 'EXECUTING_TOOL'
  ) {
    return normalizedRealtime
  }

  // Level 6: THINKING (Priority 60)
  if (props.isThinking || normalizedRealtime === 'THINKING') {
    return 'THINKING'
  }

  // Level 7: LISTENING (Priority 50)
  if (props.isListening || normalizedRealtime === 'LISTENING') {
    return 'LISTENING'
  }

  // Level 8: Realtime Voice / Event Bus Fallback
  if (normalizedRealtime) {
    return normalizedRealtime
  }

  // Level 9: Default Idle (Priority 10)
  return 'IDLE'
}

/**
 * StateArbitrator: Deterministic priority hierarchy, dwell time tracking,
 * and fallback timeout management for the Holographic Core.
 */
export class VisualizerStateArbitrator {
  private activeToolState: HolographicState | null = null
  private toolStartedAt: number = 0
  private toolDwellUntil: number = 0
  private alertDwellUntil: number = 0
  private lastObservedTool: string | null = null

  public onToolStart(toolName: string): HolographicState {
    const mapped = classifyToolState(toolName)
    this.activeToolState = mapped
    this.toolStartedAt = Date.now()
    this.toolDwellUntil = 0
    return mapped
  }

  public onToolResult(): void {
    if (this.activeToolState) {
      this.toolDwellUntil = Date.now() + TOOL_DWELL_MS
    }
  }

  public triggerAlert(): void {
    this.alertDwellUntil = Date.now() + ALERT_DWELL_MS
  }

  public clearAlert(): void {
    this.alertDwellUntil = 0
  }

  public classifyTool(toolName: string | null | undefined): HolographicState {
    return classifyToolState(toolName)
  }

  public resolve(
    props: SphereProps,
    eventBusState?: string | null,
    realtimeVoiceState?: string | null
  ): HolographicState {
    const now = Date.now()

    // If alert dwell is active, synthesize error
    if (now < this.alertDwellUntil) {
      return 'ALERT'
    }

    // Auto-track tool changes from props
    if (props.activeTool && props.activeTool !== this.lastObservedTool) {
      this.lastObservedTool = props.activeTool
      this.onToolStart(props.activeTool)
    } else if (!props.activeTool) {
      this.lastObservedTool = null
    }

    // Tool dwell & timeout management
    let currentTool = props.activeTool
    if (this.activeToolState) {
      const isTimedOut = now - this.toolStartedAt > TOOL_TIMEOUT_MS
      const isDwellExpired = this.toolDwellUntil > 0 && now > this.toolDwellUntil
      if (isTimedOut || isDwellExpired) {
        this.activeToolState = null
        this.toolDwellUntil = 0
        currentTool = null
      } else {
        currentTool = this.activeToolState
      }
    }

    // Anti-shadowing: live assistant speech takes precedence over background tools
    const isSpeakingLive = Boolean(
      props.isSpeaking ||
      realtimeVoiceState === 'SPEAKING' ||
      (typeof jarvisRealtimeRef !== 'undefined' &&
        (jarvisRealtimeRef.voiceState === 'SPEAKING' || jarvisRealtimeRef.isSpeaking))
    )

    const effectiveProps: SphereProps = {
      ...props,
      activeTool: currentTool,
      isSpeaking: isSpeakingLive ? true : props.isSpeaking,
    }

    const effectiveRealtime = isSpeakingLive && eventBusState !== 'ALERT' && eventBusState !== 'VISION_SCAN'
      ? 'SPEAKING'
      : (eventBusState || realtimeVoiceState)

    return resolveActiveState(effectiveProps, effectiveRealtime)
  }
}

/**
 * Creates a fresh StateWeights record with IDLE initialized to 1.
 */
export function createDefaultStateWeights(): StateWeights {
  return {
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
}

/**
 * Updates weights using frame-rate independent exponential damping:
 * damp = 1 - Math.exp(-6.2 * dt)
 * Delta time is clamped strictly to [0, 0.05] with finite safety guards.
 */
export function updateStateWeights(
  weights: StateWeights,
  activeState: HolographicState,
  delta: number
): { damp: number; dt: number } {
  const safeDt = Number.isFinite(delta) ? Math.max(0, Math.min(0.05, delta)) : 0
  const damp = 1 - Math.exp(-6.2 * safeDt)

  for (let i = 0; i < STATE_KEYS.length; i++) {
    const key = STATE_KEYS[i]
    const target = activeState === key ? 1 : 0
    weights[key] += (target - weights[key]) * damp
  }

  return { damp, dt: safeDt }
}

/**
 * Safely unpacks any CustomEvent detail payload into a validated HolographicState.
 * Supports string primitives, object payloads ({ state: ... }), common aliases,
 * and nested structures.
 */
export function unpackJarvisStateDetail(detail: unknown): HolographicState | null {
  if (detail == null) return null

  // 1. Direct string primitive
  if (typeof detail === 'string') {
    return normalizeStateName(detail)
  }

  // 2. Object payloads
  if (typeof detail === 'object' && detail !== null) {
    const record = detail as Record<string, unknown>
    if ('state' in record && record.state != null) {
      return normalizeStateName(String(record.state))
    }
    if ('voiceState' in record && record.voiceState != null) {
      return normalizeStateName(String(record.voiceState))
    }
    if ('status' in record && record.status != null) {
      return normalizeStateName(String(record.status))
    }
    if ('value' in record && record.value != null) {
      return normalizeStateName(String(record.value))
    }
    if ('name' in record && record.name != null) {
      return normalizeStateName(String(record.name))
    }
    if ('mode' in record && record.mode != null) {
      return normalizeStateName(String(record.mode))
    }
    if ('payload' in record && record.payload != null) {
      return unpackJarvisStateDetail(record.payload)
    }
    if ('detail' in record && record.detail != null && record.detail !== detail) {
      return unpackJarvisStateDetail(record.detail)
    }
  }

  return null
}

/**
 * Twin-Beat Cardiac Shockwave (Lub-Dub) Engine for ALERT state and transition pulses:
 * Cycle frequency f = 1.18 Hz (~70.8 BPM).
 * Primary systole at tau = 0.12 ("lub").
 * Secondary diastole at tau = 0.30 ("dub").
 */
export function calculateCardiacBeat(elapsedTime: number): number {
  const tau = (elapsedTime * 1.18) % 1.0
  const systole = Math.exp(-Math.pow((tau - 0.12) * 14.0, 2))
  const diastole = 0.68 * Math.exp(-Math.pow((tau - 0.3) * 16.0, 2))
  return systole + diastole
}

/**
 * State Transition Shockwave Pulse Tracker.
 * Generates an expanding shockwave ring when state transitions occur.
 */
export class StateTransitionPulseTracker {
  private lastState: HolographicState = 'IDLE'
  private pulseAge: number = 1.0 // Completed initially
  private readonly pulseDuration: number = 0.45 // 450 ms

  public update(currentState: HolographicState, dt: number): { active: boolean; scale: number; opacity: number } {
    if (currentState !== this.lastState) {
      this.lastState = currentState
      this.pulseAge = 0.0 // trigger pulse
    } else if (this.pulseAge < this.pulseDuration) {
      this.pulseAge += dt
    }

    if (this.pulseAge < this.pulseDuration) {
      const progress = this.pulseAge / this.pulseDuration
      const scale = 1.0 + 0.35 * progress
      const opacity = 0.65 * Math.pow(1.0 - progress, 2)
      return { active: true, scale, opacity }
    }

    return { active: false, scale: 1.0, opacity: 0.0 }
  }
}

/**
 * Computes state-weighted gyroscopic ring angular velocity.
 */
export function calculateRingSpeed(w: StateWeights): number {
  return (
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
  )
}

/**
 * Computes state-weighted base opacity for the gyroscopic rings.
 */
export function calculateBaseRingOpacity(w: StateWeights, alertBeat: number): number {
  return (
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
  )
}

/**
 * Computes dynamic scale for the volumetric core glow sprite.
 */
export function calculateCoreScale(
  w: StateWeights,
  t: number,
  bass: number,
  alertBeat: number
): number {
  return (
    2.45 +
    w.IDLE * Math.sin(t * 1.6) * 0.15 +
    w.LISTENING * (0.25 + bass * 0.7) +
    w.THINKING * (0.35 + Math.sin(t * 6.0) * 0.28) +
    w.SPEAKING * (0.45 + bass * 1.15) +
    w.WEB_SEARCH * 0.25 +
    w.DEEP_RESEARCH * (0.35 + Math.sin(t * 3.5) * 0.2) -
    w.MEMORY_SYNC * 0.55 +
    w.ALERT * alertBeat * 0.95
  )
}

/**
 * Computes dynamic opacity for the volumetric core glow sprite.
 */
export function calculateCoreOpacity(
  w: StateWeights,
  bass: number,
  alertBeat: number
): number {
  return (
    0.36 +
    w.SPEAKING * (0.2 + bass * 0.28) +
    w.THINKING * 0.14 +
    w.ALERT * alertBeat * 0.35 -
    w.MEMORY_SYNC * 0.12
  )
}
