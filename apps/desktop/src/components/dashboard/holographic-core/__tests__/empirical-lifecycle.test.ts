import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as THREE from 'three'
import {
  normalizeStateName,
  resolveActiveState,
  classifyToolState,
  unpackJarvisStateDetail,
  createDefaultStateWeights,
  updateStateWeights,
  calculateCardiacBeat,
  StateTransitionPulseTracker,
  calculateRingSpeed,
  calculateBaseRingOpacity,
} from '../state-machine'
import {
  MAX_PITCH_ANGLE,
  STATE_KEYS,
} from '../constants'
import { AudioReactivityBridge } from '../audio-bridge'
import {
  createVolumetricGlowTexture,
  createBackdropHaloTexture,
  createProceduralTextures,
  disposeProceduralTextures,
} from '../procedural-textures'
import type { HolographicState, SphereProps } from '../types'
import { jarvisService } from '@/services/jarvis-voice-ai'
import { jarvisRealtimeRef } from '@/services/jarvisBridge'

describe('Empirical Verification: Holographic Core Lifecycle & State Machine', () => {
  // =========================================================================
  // 1. 11-STATE ARBITRATION HIERARCHY & NORMALIZATION
  // =========================================================================
  describe('Area 1: 11-State Priority Arbitration (6-Level Hierarchy)', () => {
    it('normalizes all 11 canonical states and known aliases correctly', () => {
      let passedNormalizations = 0
      // 11 canonical states
      for (const state of STATE_KEYS) {
        expect(normalizeStateName(state)).toBe(state)
        expect(normalizeStateName(state.toLowerCase())).toBe(state)
        expect(normalizeStateName(`  ${state}  `)).toBe(state)
        passedNormalizations += 3
      }

      // Backend aliases
      const aliases: Array<[string, HolographicState]> = [
        ['LISTEN', 'LISTENING'],
        ['HEARING', 'LISTENING'],
        ['THINK', 'THINKING'],
        ['PROCESSING', 'THINKING'],
        ['REASONING', 'THINKING'],
        ['SPEAK', 'SPEAKING'],
        ['TALKING', 'SPEAKING'],
        ['SEARCH', 'WEB_SEARCH'],
        ['WEB', 'WEB_SEARCH'],
        ['BROWSE', 'WEB_SEARCH'],
        ['RESEARCH', 'DEEP_RESEARCH'],
        ['DEEP', 'DEEP_RESEARCH'],
        ['CODE', 'CODING'],
        ['CODING_TOOL', 'CODING'],
        ['VISION', 'VISION_SCAN'],
        ['SCAN', 'VISION_SCAN'],
        ['CAMERA', 'VISION_SCAN'],
        ['MEMORY', 'MEMORY_SYNC'],
        ['SYNC', 'MEMORY_SYNC'],
        ['RECALL', 'MEMORY_SYNC'],
        ['TOOL', 'EXECUTING_TOOL'],
        ['EXECUTE', 'EXECUTING_TOOL'],
        ['EXECUTING', 'EXECUTING_TOOL'],
        ['ERROR', 'ALERT'],
        ['WARN', 'ALERT'],
        ['WARNING', 'ALERT'],
        ['CRITICAL', 'ALERT'],
        ['STANDBY', 'IDLE'],
        ['DEFAULT', 'IDLE'],
      ]

      for (const [alias, expected] of aliases) {
        expect(normalizeStateName(alias)).toBe(expected)
        expect(normalizeStateName(alias.toLowerCase())).toBe(expected)
        passedNormalizations += 2
      }

      // Invalid & edge cases
      expect(normalizeStateName(null)).toBeNull()
      expect(normalizeStateName(undefined)).toBeNull()
      expect(normalizeStateName('')).toBeNull()
      expect(normalizeStateName('UNKNOWN_STATE_XYZ')).toBeNull()
      passedNormalizations += 4

      console.log(`[Area 1 Metrics] Total normalizations tested: ${passedNormalizations}, all passed.`)
    })

    it('Level 1: Explicit overrideState / state prop overrides all other levels', () => {
      // Overrides Level 2 (error), Level 3 (activeTool), Level 4 (booleans), Level 5 (voiceState)
      const props: SphereProps = {
        overrideState: 'CODING',
        error: 'Critical failure',
        activeTool: 'google_search',
        isSpeaking: true,
        isThinking: true,
        isListening: true,
      }
      expect(resolveActiveState(props, 'LISTENING')).toBe('CODING')

      // props.state also works if overrideState is unset
      const props2: SphereProps = {
        state: 'VISION_SCAN',
        error: 'Critical failure',
        activeTool: 'google_search',
        isSpeaking: true,
      }
      expect(resolveActiveState(props2, 'IDLE')).toBe('VISION_SCAN')

      // If explicit state is invalid string, falls through to lower levels
      const propsInvalidExplicit: SphereProps = {
        overrideState: 'NOT_A_REAL_STATE' as any,
        error: 'Network timeout',
      }
      expect(resolveActiveState(propsInvalidExplicit)).toBe('ALERT')
    })

    it('Level 2: Error condition produces ALERT over tools, booleans, and realtime', () => {
      const props: SphereProps = {
        error: 'Fatal IPC disconnect',
        activeTool: 'code_runner',
        isSpeaking: true,
        isThinking: true,
        isListening: true,
      }
      expect(resolveActiveState(props, 'SPEAKING')).toBe('ALERT')

      // Falsy error strings / null do not trigger ALERT
      const propsNoError: SphereProps = {
        error: null,
        activeTool: 'code_runner',
      }
      expect(resolveActiveState(propsNoError)).toBe('CODING')
    })

    it('Level 3: activeTool maps tools to distinct canonical states', () => {
      const validCases: Array<{ tool: string; expected: HolographicState }> = [
        { tool: 'google_web_search', expected: 'WEB_SEARCH' },
        { tool: 'crawl4ai_extract', expected: 'WEB_SEARCH' },
        { tool: 'browser_use_action', expected: 'WEB_SEARCH' },
        { tool: 'delegate_task_subagent', expected: 'DEEP_RESEARCH' },
        { tool: 'data_analyzer', expected: 'DEEP_RESEARCH' },
        { tool: 'deep_investigate', expected: 'DEEP_RESEARCH' },
        { tool: 'gpt_researcher_query', expected: 'DEEP_RESEARCH' },
        { tool: 'code_interpreter', expected: 'CODING' },
        { tool: 'terminal_bash_exec', expected: 'CODING' },
        { tool: 'shell_command', expected: 'CODING' },
        { tool: 'file_editor', expected: 'CODING' },
        { tool: 'camera_stream_read', expected: 'VISION_SCAN' },
        { tool: 'mediapipe_face_mesh', expected: 'VISION_SCAN' },
        { tool: 'lidar_depth_scan', expected: 'VISION_SCAN' },
        { tool: 'memory_sync_checkpoint', expected: 'MEMORY_SYNC' },
        { tool: 'sqlite_db_query', expected: 'MEMORY_SYNC' },
        { tool: 'vector_store_recall', expected: 'MEMORY_SYNC' },
        { tool: 'random_calculator_math', expected: 'EXECUTING_TOOL' },
        { tool: 'weather_fetcher_api', expected: 'EXECUTING_TOOL' },
      ]

      for (const { tool, expected } of validCases) {
        const props: SphereProps = {
          activeTool: tool,
          isSpeaking: false,
          isThinking: true, // ACTIVE_TOOL (70) preempts THINKING (60)
          isListening: true, // ACTIVE_TOOL (70) preempts LISTENING (50)
        }
        expect(resolveActiveState(props)).toBe(expected)
      }

      // Explicit M2 Contract Check: SPEAKING (80) preempts ACTIVE_TOOL (70)
      for (const { tool } of validCases) {
        const props: SphereProps = {
          activeTool: tool,
          isSpeaking: true,
        }
        const expectedState = classifyToolState(tool) === 'VISION_SCAN' ? 'VISION_SCAN' : 'SPEAKING'
        expect(resolveActiveState(props)).toBe(expectedState)
      }

      // Whitespace / empty activeTool falls through to Level 4
      expect(resolveActiveState({ activeTool: '   ', isSpeaking: true })).toBe('SPEAKING')
      expect(resolveActiveState({ activeTool: '', isThinking: true })).toBe('THINKING')
    })

    it('Level 3: gpt_researcher correctly maps to DEEP_RESEARCH (resolves D1 substring masking defect)', () => {
      // In PROJECT.md line 68: gpt_researcher_* -> DEEP_RESEARCH
      // Verified: /research/ check takes precedence over /search/ to eliminate substring collision
      const props: SphereProps = {
        activeTool: 'gpt_researcher_query',
      }
      const actualState = resolveActiveState(props)
      expect(actualState).toBe('DEEP_RESEARCH')
    })

    it('CustomEvent Detail Unpacking: unpacks object payload { detail: { state: "THINKING" } } and primitives', () => {
      // Direct object payload per PROJECT.md line 62: { state: HolographicState }
      expect(unpackJarvisStateDetail({ state: 'THINKING' })).toBe('THINKING')
      expect(unpackJarvisStateDetail({ state: 'ALERT' })).toBe('ALERT')
      expect(unpackJarvisStateDetail({ state: 'listening' })).toBe('LISTENING')

      // String primitives
      expect(unpackJarvisStateDetail('SPEAKING')).toBe('SPEAKING')
      expect(unpackJarvisStateDetail('coding')).toBe('CODING')

      // Nested detail payload
      expect(unpackJarvisStateDetail({ detail: { state: 'THINKING' } })).toBe('THINKING')
      expect(unpackJarvisStateDetail({ voiceState: 'speaking' })).toBe('SPEAKING')

      // Invalid / edge cases
      expect(unpackJarvisStateDetail(null)).toBeNull()
      expect(unpackJarvisStateDetail(undefined)).toBeNull()
      expect(unpackJarvisStateDetail('')).toBeNull()
      expect(unpackJarvisStateDetail({ state: 'NON_EXISTENT' })).toBeNull()

      // Browser CustomEvent simulation matching holographic-core-scene handleJarvisState
      let receivedState: string | null = null
      const handleJarvisState = (e: Event) => {
        const customDetail = (e as CustomEvent).detail
        if (customDetail) {
          if (typeof customDetail === 'object' && customDetail !== null && 'state' in customDetail) {
            receivedState = String((customDetail as { state: unknown }).state)
          } else {
            receivedState = String(customDetail)
          }
        }
      }

      window.addEventListener('jarvis-state', handleJarvisState)
      try {
        // Dispatch object payload per PROJECT.md spec
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } }))
        expect(receivedState).toBe('THINKING')

        // Dispatch string payload per legacy adapters
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'SPEAKING' }))
        expect(receivedState).toBe('SPEAKING')
      } finally {
        window.removeEventListener('jarvis-state', handleJarvisState)
      }
    })

    it('Level 4: Exhaustive permutations of legacy booleans follow speaking > thinking > listening', () => {
      // 8 boolean permutations
      const permutations = [
        { s: false, t: false, l: false, expected: 'IDLE' },
        { s: false, t: false, l: true, expected: 'LISTENING' },
        { s: false, t: true, l: false, expected: 'THINKING' },
        { s: false, t: true, l: true, expected: 'THINKING' },
        { s: true, t: false, l: false, expected: 'SPEAKING' },
        { s: true, t: false, l: true, expected: 'SPEAKING' },
        { s: true, t: true, l: false, expected: 'SPEAKING' },
        { s: true, t: true, l: true, expected: 'SPEAKING' },
      ]

      for (const { s, t, l, expected } of permutations) {
        const props: SphereProps = {
          isSpeaking: s,
          isThinking: t,
          isListening: l,
        }
        expect(resolveActiveState(props)).toBe(expected)
      }
    })

    it('Level 5: Realtime voiceState resolves when legacy booleans are inactive', () => {
      const props: SphereProps = {
        isSpeaking: false,
        isThinking: false,
        isListening: false,
      }

      expect(resolveActiveState(props, 'SPEAKING')).toBe('SPEAKING')
      expect(resolveActiveState(props, 'HEARING')).toBe('LISTENING')
      expect(resolveActiveState(props, 'REASONING')).toBe('THINKING')
      expect(resolveActiveState(props, 'UNKNOWN_AUDIO_STATE')).toBe('IDLE')
    })

    it('Level 6: Fallback resolves strictly to IDLE', () => {
      expect(resolveActiveState({})).toBe('IDLE')
      expect(resolveActiveState({}, null)).toBe('IDLE')
      expect(resolveActiveState({}, undefined)).toBe('IDLE')
    })
  })

  // =========================================================================
  // 2. RAPID STATE TRANSITIONS ENGINE & PARTITION OF UNITY
  // =========================================================================
  describe('Area 2: Rapid State Transitions & Partition of Unity', () => {
    it('executes 100 random state transitions verifying partition of unity and convergence', () => {
      const weights = createDefaultStateWeights()

      // Initial state check
      expect(weights.IDLE).toBe(1)
      let sum = Object.values(weights).reduce((a, b) => a + b, 0)
      expect(sum).toBeCloseTo(1.0, 6)

      let maxPartitionDrift = 0
      let minWeightObserved = 1
      let maxWeightObserved = 0

      // Seeded / deterministic pseudo-random state transitions
      let rngState = 123456789
      const nextRandom = () => {
        rngState = (1103515245 * rngState + 12345) % 2147483648
        return rngState / 2147483648
      }

      const totalTransitions = 100
      const framesPerDwell = 30 // ~500ms at 60 FPS (dt = 0.01667)
      const fixedDt = 1 / 60
      let totalFramesExecuted = 0

      for (let t = 0; t < totalTransitions; t++) {
        const nextStateIdx = Math.floor(nextRandom() * STATE_KEYS.length)
        const targetState = STATE_KEYS[nextStateIdx]

        for (let frame = 0; frame < framesPerDwell; frame++) {
          totalFramesExecuted++
          const { damp } = updateStateWeights(weights, targetState, fixedDt)

          // Verify damping factor formula: damp = 1 - Math.exp(-6.2 * dt)
          const expectedDamp = 1 - Math.exp(-6.2 * fixedDt)
          expect(damp).toBeCloseTo(expectedDamp, 6)

          // 1. Partition of unity check: sum w_i == 1.0
          let currentSum = 0
          for (let i = 0; i < STATE_KEYS.length; i++) {
            const w = weights[STATE_KEYS[i]]

            // Check no NaN or Infinite
            expect(Number.isFinite(w)).toBe(true)

            // Non-negativity check
            expect(w).toBeGreaterThanOrEqual(-1e-7)
            expect(w).toBeLessThanOrEqual(1.0 + 1e-7)

            if (w < minWeightObserved) minWeightObserved = w
            if (w > maxWeightObserved) maxWeightObserved = w
            currentSum += w
          }

          const drift = Math.abs(currentSum - 1.0)
          if (drift > maxPartitionDrift) {
            maxPartitionDrift = drift
          }
          expect(currentSum).toBeCloseTo(1.0, 5)
        }

        // Asymptotic convergence after 500ms (30 frames at 60 FPS):
        // Analytical target: 1 - exp(-6.2 * 0.5) = 1 - exp(-3.1) = ~0.95499
        expect(weights[targetState]).toBeGreaterThanOrEqual(0.95)
      }

      console.log(`[Area 2 Metrics] Transitions: ${totalTransitions}, Frames: ${totalFramesExecuted}`)
      console.log(`[Area 2 Metrics] Max partition drift: ${maxPartitionDrift.toExponential(4)}`)
      console.log(`[Area 2 Metrics] Weight bounds: [${minWeightObserved.toFixed(6)}, ${maxWeightObserved.toFixed(6)}]`)

      // Empirical drift metrics
      expect(maxPartitionDrift).toBeLessThan(1e-5)
      expect(minWeightObserved).toBeGreaterThanOrEqual(0)
      expect(maxWeightObserved).toBeLessThanOrEqual(1.000001)
    })

    it('enforces dt clamping at 0.05s to prevent overshoot on frame rate drops', () => {
      const weights = createDefaultStateWeights()
      // Call updateStateWeights with huge delta (e.g. 5.0 seconds tab backgrounded)
      const { dt, damp } = updateStateWeights(weights, 'ALERT', 5.0)

      expect(dt).toBe(0.05)
      expect(damp).toBeCloseTo(1 - Math.exp(-6.2 * 0.05), 6)
      expect(weights.ALERT).toBeCloseTo(damp, 6)
      expect(weights.ALERT).toBeLessThan(1.0) // No overshoot
    })

    it('enforces lower bound clamping (dt >= 0) and non-finite protection in updateStateWeights', () => {
      const weights = createDefaultStateWeights()

      // Negative delta time (clock rollback / NTP jitter)
      const resNeg = updateStateWeights(weights, 'ALERT', -0.016)
      expect(resNeg.dt).toBe(0)
      expect(resNeg.damp).toBe(0)
      expect(weights.ALERT).toBe(0)
      expect(weights.IDLE).toBe(1)

      // Non-finite delta time (NaN)
      const resNaN = updateStateWeights(weights, 'ALERT', NaN)
      expect(resNaN.dt).toBe(0)
      expect(resNaN.damp).toBe(0)
      expect(weights.ALERT).toBe(0)
      expect(weights.IDLE).toBe(1)
    })

    it('verifies twin-beat cardiac shockwave math', () => {
      // f = 1.18 Hz -> period T = 1 / 1.18 = 0.84745 s
      // Systole at tau = 0.12 (t = 0.12 / 1.18 = 0.1017 s)
      const tSystole = 0.12 / 1.18
      const beatSystole = calculateCardiacBeat(tSystole)
      expect(beatSystole).toBeGreaterThan(0.99) // Primary lub peak

      // Diastole at tau = 0.30 (t = 0.30 / 1.18 = 0.2542 s)
      const tDiastole = 0.30 / 1.18
      const beatDiastole = calculateCardiacBeat(tDiastole)
      expect(beatDiastole).toBeCloseTo(0.68, 1) // Secondary dub peak

      // Quiescent phase at tau = 0.70
      const tQuiet = 0.70 / 1.18
      const beatQuiet = calculateCardiacBeat(tQuiet)
      expect(beatQuiet).toBeLessThan(0.01)

      // Strict non-negativity across 100 sample timestamps
      for (let s = 0; s < 100; s++) {
        const beat = calculateCardiacBeat(s * 0.02)
        expect(beat).toBeGreaterThanOrEqual(0)
      }
    })

    it('verifies StateTransitionPulseTracker expansion and decay over 450ms', () => {
      const tracker = new StateTransitionPulseTracker()

      // Initial state: pulse completed
      const initial = tracker.update('IDLE', 0.016)
      expect(initial.active).toBe(false)
      expect(initial.opacity).toBe(0)

      // State transition: IDLE -> CODING triggers pulse
      const t0 = tracker.update('CODING', 0.0)
      expect(t0.active).toBe(true)
      expect(t0.scale).toBeCloseTo(1.0, 2)
      expect(t0.opacity).toBeCloseTo(0.65, 2)

      // Halfway through pulse (225ms)
      const tHalf = tracker.update('CODING', 0.225)
      expect(tHalf.active).toBe(true)
      expect(tHalf.scale).toBeGreaterThan(1.0)
      expect(tHalf.scale).toBeLessThan(1.35)
      expect(tHalf.opacity).toBeLessThan(0.65)
      expect(tHalf.opacity).toBeGreaterThan(0)

      // Beyond pulse duration (450ms + 10ms)
      const tEnd = tracker.update('CODING', 0.235)
      expect(tEnd.active).toBe(false)
      expect(tEnd.opacity).toBe(0)
      expect(tEnd.scale).toBe(1.0)
    })

    it('verifies ring speeds and base opacities across all 11 states', () => {
      for (const state of STATE_KEYS) {
        const w = createDefaultStateWeights()
        w.IDLE = 0
        w[state] = 1.0

        const speed = calculateRingSpeed(w)
        expect(speed).toBeGreaterThan(0)
        expect(Number.isFinite(speed)).toBe(true)

        const opacity = calculateBaseRingOpacity(w, 0.5)
        expect(opacity).toBeGreaterThan(0)
        expect(opacity).toBeLessThanOrEqual(1.0)
      }
    })
  })

  // =========================================================================
  // 3. AUDIO REACTIVITY BRIDGE
  // =========================================================================
  describe('Area 3: Audio Reactivity Bridge (3-Band FFT & Fallback)', () => {
    let bridge: AudioReactivityBridge

    beforeEach(() => {
      bridge = new AudioReactivityBridge()
      bridge.reset()
      if (jarvisRealtimeRef) {
        jarvisRealtimeRef.audioLevel = 0
      }
    })

    it('aggregates 3-band FFT bins correctly (Bass 0-15, Mid 16-55, Treble 56-111)', () => {
      const mockAnalyser = {
        getByteFrequencyData: vi.fn((arr: Uint8Array) => {
          arr.fill(0)
          // Set bass bins 0-15 to full volume (255)
          for (let i = 0; i < 16; i++) arr[i] = 255
        }),
      }

      // Temporarily inject mock analyser into jarvisService
      const originalAnalyser = (jarvisService as any).analyser
      ;(jarvisService as any).analyser = mockAnalyser

      try {
        // Run single update with dt = 0.5 (large enough to observe smoothed output)
        const bands = bridge.update(0.5, 1.0, 'IDLE')
        expect(mockAnalyser.getByteFrequencyData).toHaveBeenCalled()
        expect(bands.bass).toBeGreaterThan(0.9)
        expect(bands.mid).toBe(0)
        expect(bands.treble).toBe(0)

        // Now set mid bins 16-55 to full volume (255)
        bridge.reset()
        mockAnalyser.getByteFrequencyData.mockImplementation((arr: Uint8Array) => {
          arr.fill(0)
          for (let i = 16; i < 56; i++) arr[i] = 255
        })
        const bandsMid = bridge.update(0.5, 1.0, 'IDLE')
        expect(bandsMid.bass).toBe(0)
        expect(bandsMid.mid).toBeGreaterThan(0.9)
        expect(bandsMid.treble).toBe(0)

        // Now set treble bins 56-111 to full volume (255)
        bridge.reset()
        mockAnalyser.getByteFrequencyData.mockImplementation((arr: Uint8Array) => {
          arr.fill(0)
          for (let i = 56; i < 112; i++) arr[i] = 255
        })
        const bandsTreble = bridge.update(0.5, 1.0, 'IDLE')
        expect(bandsTreble.bass).toBe(0)
        expect(bandsTreble.mid).toBe(0)
        expect(bandsTreble.treble).toBeGreaterThan(0.9)

        // Test unused bins 112-127: should not affect any band
        bridge.reset()
        mockAnalyser.getByteFrequencyData.mockImplementation((arr: Uint8Array) => {
          arr.fill(0)
          for (let i = 112; i < 128; i++) arr[i] = 255
        })
        const bandsUnused = bridge.update(0.5, 1.0, 'IDLE')
        expect(bandsUnused.bass).toBe(0)
        expect(bandsUnused.mid).toBe(0)
        expect(bandsUnused.treble).toBe(0)
      } finally {
        ;(jarvisService as any).analyser = originalAnalyser
      }
    })

    it('scales scalar audioLevel prop across bass, mid, and treble (0.95, 0.85, 0.75)', () => {
      // With propAudioLevel = 0.8 and dt large enough to settle
      const bands = bridge.update(0.5, 0, 'IDLE', 0.8)

      // Expected raw levels: Bass = 0.8 * 0.95 = 0.76, Mid = 0.8 * 0.85 = 0.68, Treble = 0.8 * 0.75 = 0.60
      expect(bands.bass).toBeCloseTo(0.76, 1)
      expect(bands.mid).toBeCloseTo(0.68, 1)
      expect(bands.treble).toBeCloseTo(0.60, 1)
    })

    it('strictly clamps overdriven audio inputs (level > 1.0) and negative/NaN values to [0, 1]', () => {
      // Pass excessive overdrive audio level (5.0)
      const bandsOverdrive = bridge.update(0.5, 0, 'IDLE', 5.0)
      // Clamped to 1.0: rawBass = 0.95, rawMid = 0.85, rawTreble = 0.75
      expect(bandsOverdrive.bass).toBeCloseTo(0.95, 1)
      expect(bandsOverdrive.mid).toBeCloseTo(0.85, 1)
      expect(bandsOverdrive.treble).toBeCloseTo(0.75, 1)
      expect(bandsOverdrive.bass).toBeLessThanOrEqual(1.0)
      expect(bandsOverdrive.mid).toBeLessThanOrEqual(1.0)
      expect(bandsOverdrive.treble).toBeLessThanOrEqual(1.0)

      // Pass negative and NaN audio levels
      bridge.reset()
      const bandsNegative = bridge.update(0.5, 0, 'IDLE', -2.0)
      expect(bandsNegative.bass).toBe(0)
      expect(bandsNegative.mid).toBe(0)
      expect(bandsNegative.treble).toBe(0)

      bridge.reset()
      const bandsNaN = bridge.update(0.5, 0, 'IDLE', NaN)
      expect(bandsNaN.bass).toBe(0)
      expect(bandsNaN.mid).toBe(0)
      expect(bandsNaN.treble).toBe(0)
    })

    it('activates autonomous speech cadence simulation fallback when speaking without audio feed (< 0.03)', () => {
      // With audioLevel = 0, no analyser, activeState = 'SPEAKING'
      // Test over 50 timestamps to verify dynamic speech cadence
      let minBass = 1, maxBass = 0
      let minMid = 1, maxMid = 0
      let minTreble = 1, maxTreble = 0

      for (let i = 0; i < 50; i++) {
        const time = i * 0.1
        const bands = bridge.update(0.016, time, 'SPEAKING', 0)

        // Should produce non-zero, healthy speech levels
        expect(bands.bass).toBeGreaterThan(0)
        expect(bands.mid).toBeGreaterThan(0)
        expect(bands.treble).toBeGreaterThan(0)

        expect(bands.bass).toBeLessThanOrEqual(1.0)
        expect(bands.mid).toBeLessThanOrEqual(1.0)
        expect(bands.treble).toBeLessThanOrEqual(1.0)

        if (bands.bass < minBass) minBass = bands.bass
        if (bands.bass > maxBass) maxBass = bands.bass
        if (bands.mid < minMid) minMid = bands.mid
        if (bands.mid > maxMid) maxMid = bands.mid
        if (bands.treble < minTreble) minTreble = bands.treble
        if (bands.treble > maxTreble) maxTreble = bands.treble
      }

      console.log(`[Area 3 Speech Cadence] Bass: [${minBass.toFixed(3)}, ${maxBass.toFixed(3)}], Mid: [${minMid.toFixed(3)}, ${maxMid.toFixed(3)}], Treble: [${minTreble.toFixed(3)}, ${maxTreble.toFixed(3)}]`)
    })

    it('activates attentive synthetic mic pulse fallback when LISTENING without audio feed (< 0.02)', () => {
      for (let i = 0; i < 30; i++) {
        const time = i * 0.1
        const bands = bridge.update(0.016, time, 'LISTENING', 0)

        expect(bands.bass).toBeGreaterThan(0)
        expect(bands.mid).toBeGreaterThan(0)
        expect(bands.treble).toBeGreaterThan(0)
      }
    })

    it('amplifies live mic sensitivity when LISTENING with active feed (>= 0.02)', () => {
      // Input: 0.1 audioLevel
      // Scaled raw: Bass = 0.1 * 0.95 = 0.095, boosted by 2.2x = 0.209
      const bands = bridge.update(0.5, 0, 'LISTENING', 0.1)
      expect(bands.bass).toBeGreaterThan(0.15)
      expect(bands.mid).toBeGreaterThan(0.15)
    })

    it('smooths values exponentially with decay k = 14.0 s^-1', () => {
      // Sudden step input
      bridge.reset()
      const b1 = bridge.update(0.016, 0, 'IDLE', 1.0)
      // damp = 1 - Math.exp(-14 * 0.016) = 1 - Math.exp(-0.224) = ~0.2007
      expect(b1.bass).toBeCloseTo(0.95 * (1 - Math.exp(-14 * 0.016)), 2)

      // After 20 frames (320ms), values converge close to 0.95
      let bRecent = b1
      for (let i = 0; i < 20; i++) {
        bRecent = bridge.update(0.016, i * 0.016, 'IDLE', 1.0)
      }
      expect(bRecent.bass).toBeCloseTo(0.95, 1)
    })
  })

  // =========================================================================
  // 4. PROCEDURAL TEXTURES GENERATION
  // =========================================================================
  describe('Area 4: Procedural Texture Generation', () => {
    let mockContext2D: any
    let originalGetContext: any

    beforeEach(() => {
      // Mock Canvas 2D context to verify gradient profiles in jsdom
      mockContext2D = {
        createRadialGradient: vi.fn((_x0, _y0, _r0, _x1, _y1, _r1) => {
          const stops: Array<{ offset: number; color: string }> = []
          return {
            addColorStop: vi.fn((offset, color) => {
              stops.push({ offset, color })
            }),
            __stops: stops,
          }
        }),
        fillRect: vi.fn(),
        fillStyle: '',
      }

      originalGetContext = HTMLCanvasElement.prototype.getContext
      HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue(mockContext2D) as any
    })

    afterEach(() => {
      HTMLCanvasElement.prototype.getContext = originalGetContext
    })

    it('creates volumetric glow texture with 64x64 dimensions, radial gradient, and alpha profile', () => {
      const glowTex = createVolumetricGlowTexture()
      expect(glowTex).toBeInstanceOf(THREE.CanvasTexture)
      expect(glowTex.image).toBeDefined()
      expect(glowTex.image.width).toBe(64)
      expect(glowTex.image.height).toBe(64)
      expect(glowTex.version).toBeGreaterThan(0) // Three.js increments version when needsUpdate=true

      // Verify radial gradient parameters: center at (32, 32), r0=0, r1=32
      expect(mockContext2D.createRadialGradient).toHaveBeenCalledWith(32, 32, 0, 32, 32, 32)
      expect(mockContext2D.fillRect).toHaveBeenCalledWith(0, 0, 64, 64)

      glowTex.dispose()
    })

    it('creates backdrop halo texture with 128x128 dimensions, radial gradient, and dark navy profile', () => {
      const haloTex = createBackdropHaloTexture()
      expect(haloTex).toBeInstanceOf(THREE.CanvasTexture)
      expect(haloTex.image).toBeDefined()
      expect(haloTex.image.width).toBe(128)
      expect(haloTex.image.height).toBe(128)
      expect(haloTex.version).toBeGreaterThan(0)

      // Verify radial gradient parameters: center at (64, 64), r0=0, r1=64
      expect(mockContext2D.createRadialGradient).toHaveBeenCalledWith(64, 64, 0, 64, 64, 64)
      expect(mockContext2D.fillRect).toHaveBeenCalledWith(0, 0, 128, 128)

      haloTex.dispose()
    })

    it('creates and disposes procedural textures without error', () => {
      const textures = createProceduralTextures()
      expect(textures.glowTexture).toBeDefined()
      expect(textures.backdropTexture).toBeDefined()

      const disposeGlowSpy = vi.spyOn(textures.glowTexture, 'dispose')
      const disposeBackdropSpy = vi.spyOn(textures.backdropTexture, 'dispose')

      disposeProceduralTextures(textures)
      expect(disposeGlowSpy).toHaveBeenCalledTimes(1)
      expect(disposeBackdropSpy).toHaveBeenCalledTimes(1)

      // Safe against null/undefined
      expect(() => disposeProceduralTextures(null)).not.toThrow()
      expect(() => disposeProceduralTextures(undefined)).not.toThrow()
    })
  })

  // =========================================================================
  // 5. POINTER ORBIT PITCH CLAMPING
  // =========================================================================
  describe('Area 5: Pointer Orbit Pitch Clamping (±1.05 rad / ±60 deg)', () => {
    it('strictly clamps pointer orbit pitch angle within [-1.05, +1.05] radians', () => {
      expect(MAX_PITCH_ANGLE).toBe(1.05)

      // Test extreme pointer dy inputs
      let targetRotX = 0
      const clampOrbitPitch = (current: number, dy: number) => {
        return Math.max(-MAX_PITCH_ANGLE, Math.min(MAX_PITCH_ANGLE, current + dy * 0.005))
      }

      // Extreme upward drag: dy = +10,000 px
      targetRotX = clampOrbitPitch(0, 10000)
      expect(targetRotX).toBe(1.05)

      // Extreme downward drag: dy = -10,000 px
      targetRotX = clampOrbitPitch(0, -10000)
      expect(targetRotX).toBe(-1.05)

      // Moderate inputs within bounds
      targetRotX = clampOrbitPitch(0, 100) // 100 * 0.005 = 0.5
      expect(targetRotX).toBe(0.5)

      targetRotX = clampOrbitPitch(0.8, 100) // 0.8 + 0.5 = 1.3 -> clamped to 1.05
      expect(targetRotX).toBe(1.05)

      targetRotX = clampOrbitPitch(-0.8, -100) // -0.8 - 0.5 = -1.3 -> clamped to -1.05
      expect(targetRotX).toBe(-1.05)
    })

    it('simulates damped pitch rotation convergence within clamp bounds', () => {
      let currentRotX = 0
      const targetRotX = 1.05 // Clamped limit

      // Run 60 frames of damped pitch rotation: current += (target - current) * 0.15
      for (let frame = 0; frame < 60; frame++) {
        currentRotX += (targetRotX - currentRotX) * 0.15
        expect(currentRotX).toBeLessThanOrEqual(1.05)
        expect(currentRotX).toBeGreaterThanOrEqual(-1.05)
      }

      expect(currentRotX).toBeCloseTo(1.05, 3)
    })
  })
})
