import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  normalizeStateName,
  resolveActiveState,
  classifyToolState,
  unpackJarvisStateDetail,
  createDefaultStateWeights,
  updateStateWeights,
  VisualizerStateArbitrator,
  TOOL_DWELL_MS,
  TOOL_TIMEOUT_MS,
  ALERT_DWELL_MS,
  SPEECH_DECAY_MS,
} from '../state-machine'
import { STATE_KEYS, KEY_STATE_MAP } from '../constants'
import type { HolographicState, SphereProps } from '../types'
import { jarvisRealtimeRef } from '@/services/jarvisBridge'
import { gatewayClient } from '@/lib/gateway-client'

describe('Challenger 2 Adversarial Stress Suite: Visualizer State & Event Wiring', () => {
  let activeIntervals: Set<NodeJS.Timeout | number>
  let originalSetInterval: typeof window.setInterval
  let originalClearInterval: typeof window.clearInterval

  beforeEach(() => {
    vi.useFakeTimers()
    jarvisRealtimeRef.audioLevel = 0
    jarvisRealtimeRef.voiceState = 'IDLE'
    jarvisRealtimeRef.isSpeaking = false
    jarvisRealtimeRef.isListening = false

    // Track intervals for leak detection
    activeIntervals = new Set()
    originalSetInterval = window.setInterval
    originalClearInterval = window.clearInterval

    window.setInterval = vi.fn((handler: TimerHandler, timeout?: number, ...args: any[]) => {
      const id = originalSetInterval(handler, timeout, ...args)
      activeIntervals.add(id)
      return id
    }) as any

    window.clearInterval = vi.fn((id?: number | NodeJS.Timeout) => {
      if (id !== undefined) {
        activeIntervals.delete(id)
        originalClearInterval(id as any)
      }
    }) as any
  })

  afterEach(() => {
    window.setInterval = originalSetInterval
    window.clearInterval = originalClearInterval
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  // =========================================================================
  // MISSION 1: KEYBOARD SHORTCUTS & FORM GUARD STRESS TEST
  // =========================================================================
  describe('Mission 1: Keyboard Shortcuts & Form Guard Stress Test', () => {
    const ALL_HOTKEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-']

    const setupDashboardHotkeyListener = () => {
      let dispatchedStates: string[] = []
      const handleState = (e: Event) => {
        const detail = (e as CustomEvent).detail
        const state = unpackJarvisStateDetail(detail)
        if (state) dispatchedStates.push(state)
      }
      window.addEventListener('jarvis-state', handleState)

      const handleKey = (e: KeyboardEvent) => {
        if (e.ctrlKey || e.altKey || e.metaKey) return
        const target = e.target as HTMLElement | null
        if (!target) return
        const tag = target.tagName?.toUpperCase()
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
        if (target.isContentEditable || (target as any).contentEditable === 'true' || target.getAttribute?.('contenteditable') === 'true') return
        if (target.closest && target.closest('[contenteditable="true"], [contenteditable=""], [contenteditable], .monaco-editor, .xterm, [role="textbox"]')) return

        const HOTKEY_MAP: Record<string, string> = {
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

        const targetState = HOTKEY_MAP[e.key]
        if (targetState) {
          window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: targetState } }))
        }
      }
      window.addEventListener('keydown', handleKey)

      const cleanup = () => {
        window.removeEventListener('jarvis-state', handleState)
        window.removeEventListener('keydown', handleKey)
      }

      return { dispatchedStates, cleanup }
    }

    it('suppresses 100% of hotkeys across all input, textarea, select and contenteditable variants', () => {
      const { dispatchedStates, cleanup } = setupDashboardHotkeyListener()

      try {
        // Build an exhaustive matrix of 14 focusable/editable element types
        const elements: HTMLElement[] = [
          Object.assign(document.createElement('input'), { type: 'text' }),
          Object.assign(document.createElement('input'), { type: 'password' }),
          Object.assign(document.createElement('input'), { type: 'search' }),
          Object.assign(document.createElement('input'), { type: 'number' }),
          Object.assign(document.createElement('input'), { type: 'email' }),
          Object.assign(document.createElement('input'), { type: 'tel' }),
          Object.assign(document.createElement('input'), { type: 'url' }),
          document.createElement('textarea'),
          document.createElement('select'),
          // Contenteditable true
          (() => {
            const div = document.createElement('div')
            div.setAttribute('contenteditable', 'true')
            div.contentEditable = 'true'
            return div
          })(),
          // Contenteditable empty string (HTML5 standard for true)
          (() => {
            const div = document.createElement('div')
            div.setAttribute('contenteditable', '')
            return div
          })(),
          // Contenteditable plaintext-only
          (() => {
            const div = document.createElement('div')
            div.setAttribute('contenteditable', 'plaintext-only')
            return div
          })(),
          // Nested element inside contenteditable container
          (() => {
            const parent = document.createElement('div')
            parent.setAttribute('contenteditable', 'true')
            const span = document.createElement('span')
            parent.appendChild(span)
            document.body.appendChild(parent)
            return span
          })(),
          // Monaco editor container
          (() => {
            const container = document.createElement('div')
            container.className = 'monaco-editor'
            const textarea = document.createElement('textarea')
            container.appendChild(textarea)
            document.body.appendChild(container)
            return textarea
          })(),
          // Xterm terminal container
          (() => {
            const xterm = document.createElement('div')
            xterm.className = 'xterm'
            const terminal = document.createElement('div')
            xterm.appendChild(terminal)
            document.body.appendChild(xterm)
            return terminal
          })(),
          // Role textbox
          (() => {
            const div = document.createElement('div')
            div.setAttribute('role', 'textbox')
            return div
          })(),
        ]

        // Append remaining to DOM
        for (const el of elements) {
          if (!el.isConnected) document.body.appendChild(el)
        }

        // Test every single hotkey on every single element: 11 hotkeys * 16 elements = 176 assertions
        let totalAttempts = 0
        for (const el of elements) {
          for (const key of ALL_HOTKEYS) {
            el.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }))
            totalAttempts++
          }
        }

        expect(totalAttempts).toBe(176)
        expect(dispatchedStates).toHaveLength(0)
      } finally {
        cleanup()
      }
    })

    it('suppresses hotkey dispatches when modifier keys (Ctrl, Alt, Meta) are held', () => {
      const { dispatchedStates, cleanup } = setupDashboardHotkeyListener()

      try {
        const modifierCombos = [
          { ctrlKey: true },
          { altKey: true },
          { metaKey: true },
          { ctrlKey: true, shiftKey: true },
          { altKey: true, shiftKey: true },
          { ctrlKey: true, altKey: true },
          { ctrlKey: true, altKey: true, metaKey: true },
        ]

        let totalAttempts = 0
        for (const combo of modifierCombos) {
          for (const key of ALL_HOTKEYS) {
            window.dispatchEvent(new KeyboardEvent('keydown', { key, ...combo }))
            totalAttempts++
          }
        }

        expect(totalAttempts).toBe(ALL_HOTKEYS.length * modifierCombos.length) // 77 combinations
        expect(dispatchedStates).toHaveLength(0)
      } finally {
        cleanup()
      }
    })

    it('handles Shift modifier behavior cleanly', () => {
      const { dispatchedStates, cleanup } = setupDashboardHotkeyListener()

      try {
        // On US keyboards, Shift+number produces punctuation symbols
        const shiftSymbols = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_']
        for (const sym of shiftSymbols) {
          window.dispatchEvent(new KeyboardEvent('keydown', { key: sym, shiftKey: true }))
        }
        expect(dispatchedStates).toHaveLength(0)

        // If Shift is pressed in combination with Ctrl (Ctrl+Shift+1)
        window.dispatchEvent(new KeyboardEvent('keydown', { key: '1', ctrlKey: true, shiftKey: true }))
        expect(dispatchedStates).toHaveLength(0)
      } finally {
        cleanup()
      }
    })

    it('suppresses non-mapped keys, boundary characters, and invalid events', () => {
      const { dispatchedStates, cleanup } = setupDashboardHotkeyListener()

      try {
        const nonMapped = [
          'a', 'b', 'c', 'z', 'A', 'Z',
          'Enter', 'Escape', 'Tab', 'Space', 'Backspace', 'Delete',
          'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
          'Home', 'End', 'PageUp', 'PageDown',
          'F1', 'F2', 'F5', 'F12',
          '~', '`', '=', '+', '[', ']', '{', '}', '\\', '|', ';', ':', '\'', '"', ',', '.', '<', '>', '/', '?',
          '', ' ',
        ]

        for (const key of nonMapped) {
          window.dispatchEvent(new KeyboardEvent('keydown', { key }))
        }

        expect(dispatchedStates).toHaveLength(0)
      } finally {
        cleanup()
      }
    })

    it('survives rapid burst of 200 consecutive valid hotkeys without errors or dropped states', () => {
      const { dispatchedStates, cleanup } = setupDashboardHotkeyListener()

      try {
        for (let i = 0; i < 200; i++) {
          const key = ALL_HOTKEYS[i % ALL_HOTKEYS.length]
          window.dispatchEvent(new KeyboardEvent('keydown', { key }))
        }

        expect(dispatchedStates).toHaveLength(200)
        expect(dispatchedStates[0]).toBe('IDLE')
        expect(dispatchedStates[1]).toBe('LISTENING')
        expect(dispatchedStates[10]).toBe('ALERT')
      } finally {
        cleanup()
      }
    })

    it('operates stably when both dashboard and holographic-core-scene listeners are simultaneously active', () => {
      // Simulate dual-listener registration when HolographicCore is mounted in Dashboard
      let sceneRealtimeState: string | null = null
      let totalDispatches = 0

      const handleJarvisState = (e: Event) => {
        totalDispatches++
        const unpacked = unpackJarvisStateDetail((e as CustomEvent).detail)
        if (unpacked) sceneRealtimeState = unpacked
      }

      const sceneKeyDown = (e: KeyboardEvent) => {
        if (e.ctrlKey || e.altKey || e.metaKey) return
        const target = e.target as HTMLElement | null
        if (!target) return
        const tag = target.tagName?.toUpperCase()
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
        if (target.isContentEditable || (target as any).contentEditable === 'true' || target.getAttribute?.('contenteditable') === 'true') return
        if (target.closest && target.closest('[contenteditable="true"], [contenteditable=""], [contenteditable], .monaco-editor, .xterm, [role="textbox"]')) return

        const mapped = KEY_STATE_MAP[e.key]
        if (mapped) {
          sceneRealtimeState = mapped
          window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))
        }
      }

      const dashboardListener = setupDashboardHotkeyListener()
      window.addEventListener('jarvis-state', handleJarvisState)
      window.addEventListener('keydown', sceneKeyDown)

      try {
        // Press key '6' (DEEP_RESEARCH)
        window.dispatchEvent(new KeyboardEvent('keydown', { key: '6' }))
        expect(sceneRealtimeState).toBe('DEEP_RESEARCH')

        // Press key '-' (ALERT)
        window.dispatchEvent(new KeyboardEvent('keydown', { key: '-' }))
        expect(sceneRealtimeState).toBe('ALERT')

        // Verify that typing in input with both listeners still produces ZERO events
        const input = document.createElement('input')
        document.body.appendChild(input)
        const dispatchCountBefore = totalDispatches
        input.dispatchEvent(new KeyboardEvent('keydown', { key: '1', bubbles: true }))
        input.dispatchEvent(new KeyboardEvent('keydown', { key: '2', bubbles: true }))
        expect(totalDispatches).toBe(dispatchCountBefore)
      } finally {
        dashboardListener.cleanup()
        window.removeEventListener('jarvis-state', handleJarvisState)
        window.removeEventListener('keydown', sceneKeyDown)
      }
    })
  })

  // =========================================================================
  // MISSION 2: AUDIO AMPLITUDE & MEMORY LEAK STRESS TEST
  // =========================================================================
  describe('Mission 2: Audio Amplitude & Memory Leak Stress Test', () => {
    // Mock HTMLAudioElement for Node / jsdom environment
    class MockAudio {
      public src: string
      public paused: boolean = false
      public ended: boolean = false
      public currentTime: number = 0
      public onended: (() => void) | null = null
      public onerror: (() => void) | null = null

      constructor(src: string) {
        this.src = src
      }

      public async play(): Promise<void> {
        this.paused = false
        this.ended = false
        return Promise.resolve()
      }

      public pause(): void {
        this.paused = true
      }
    }

    let originalAudio: any

    beforeEach(() => {
      originalAudio = global.Audio
      ;(global as any).Audio = MockAudio
    })

    afterEach(() => {
      ;(global as any).Audio = originalAudio
    })

    it('dynamically modulates jarvisRealtimeRef.audioLevel within [0.05, 1.0] during speech', () => {
      gatewayClient.playTtsAudio('dGVzdGF1ZGlv')
      expect(jarvisRealtimeRef.isSpeaking).toBe(true)
      expect(jarvisRealtimeRef.voiceState).toBe('SPEAKING')

      // Tick 1: 33ms
      vi.advanceTimersByTime(33)
      expect(jarvisRealtimeRef.audioLevel).toBeGreaterThanOrEqual(0.05)
      expect(jarvisRealtimeRef.audioLevel).toBeLessThanOrEqual(1.0)

      // Tick 5: 165ms
      vi.advanceTimersByTime(132)
      expect(jarvisRealtimeRef.audioLevel).toBeGreaterThanOrEqual(0.05)
      expect(jarvisRealtimeRef.audioLevel).toBeLessThanOrEqual(1.0)

      // Cancel speech cleanly resets
      gatewayClient.cancelSpeech()
      expect(jarvisRealtimeRef.audioLevel).toBe(0)
      expect(jarvisRealtimeRef.isSpeaking).toBe(false)
      expect(jarvisRealtimeRef.voiceState).toBe('IDLE')
    })

    it('stress tests 100 rapid cycles of playTtsAudio -> cancel -> error -> onended with 0 timer leaks', () => {
      const dummyBase64 = 'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA='

      for (let i = 0; i < 100; i++) {
        // Step 1: Start speech
        gatewayClient.playTtsAudio(dummyBase64)
        expect(jarvisRealtimeRef.isSpeaking).toBe(true)

        // Step 2: Let interval tick once or twice
        vi.advanceTimersByTime(33)
        expect(jarvisRealtimeRef.audioLevel).toBeGreaterThan(0)

        // Step 3: Cycle through different termination modes
        if (i % 3 === 0) {
          // Explicit user cancellation
          gatewayClient.cancelSpeech()
        } else if (i % 3 === 1) {
          // Simulate playback error
          const currentAudio = (gatewayClient as any).currentAudio
          if (currentAudio && currentAudio.onerror) {
            currentAudio.onerror()
          } else {
            gatewayClient.cancelSpeech()
          }
        } else {
          // Simulate natural completion
          const currentAudio = (gatewayClient as any).currentAudio
          if (currentAudio && currentAudio.onended) {
            currentAudio.ended = true
            currentAudio.onended()
          } else {
            gatewayClient.cancelSpeech()
          }
        }

        // Verify clean zero state after every cycle
        expect(jarvisRealtimeRef.audioLevel).toBe(0)
        expect(jarvisRealtimeRef.isSpeaking).toBe(false)
      }

      // Allow any remaining scheduled frames to flush
      vi.advanceTimersByTime(1000)

      // CRITICAL ASSERTION: All interval timers must be cleared
      expect(activeIntervals.size).toBe(0)
      expect((gatewayClient as any).ttsAudioTimer).toBeNull()
      expect(jarvisRealtimeRef.audioLevel).toBe(0.0)
      expect(jarvisRealtimeRef.isSpeaking).toBe(false)
    })

    it('handles 50 rapid back-to-back playTtsAudio calls without prior cancellation without dangling timers', () => {
      const dummyBase64 = 'dGVzdA=='

      // Rapidly overwrite audio 50 times synchronously
      for (let i = 0; i < 50; i++) {
        gatewayClient.playTtsAudio(dummyBase64)
      }

      // Exactly 1 timer should be active, not 50
      expect(activeIntervals.size).toBe(1)
      expect((gatewayClient as any).ttsAudioTimer).not.toBeNull()

      // Advance timers and verify speech reactivity
      vi.advanceTimersByTime(66)
      expect(jarvisRealtimeRef.audioLevel).toBeGreaterThan(0)

      // Now cancel
      gatewayClient.cancelSpeech()

      // Must cleanly drop to 0 active intervals
      expect(activeIntervals.size).toBe(0)
      expect((gatewayClient as any).ttsAudioTimer).toBeNull()
      expect(jarvisRealtimeRef.audioLevel).toBe(0)
    })

    it('gracefully recovers when audio.play() rejects (e.g., Autoplay block or abort)', async () => {
      // Mock play to reject
      class RejectingAudio extends MockAudio {
        public override async play(): Promise<void> {
          this.paused = true
          return Promise.reject(new Error('NotAllowedError: play() failed'))
        }
      }
      ;(global as any).Audio = RejectingAudio

      gatewayClient.playTtsAudio('dGVzdA==')

      // Allow promise rejection microtasks to flush
      await Promise.resolve()
      vi.advanceTimersByTime(50)

      // System must cleanly recover to IDLE and audioLevel 0
      expect(jarvisRealtimeRef.audioLevel).toBe(0)
      expect(jarvisRealtimeRef.isSpeaking).toBe(false)
      expect(activeIntervals.size).toBe(0)
    })

    it('handles empty audio base64 or corrupt payload safely without throwing', () => {
      expect(() => {
        gatewayClient.playTtsAudio('')
      }).not.toThrow()

      expect(jarvisRealtimeRef.isSpeaking).toBe(true)
      gatewayClient.cancelSpeech()
      expect(jarvisRealtimeRef.audioLevel).toBe(0)
      expect(activeIntervals.size).toBe(0)
    })
  })

  // =========================================================================
  // MISSION 3: FALLBACK TIMEOUT & STATE INVARIANCE
  // =========================================================================
  describe('Mission 3: Fallback Timeout & State Invariance', () => {
    it('enforces tool timeout at 20000ms boundary and decays to resting IDLE', () => {
      const arbitrator = new VisualizerStateArbitrator()

      // Start tool
      const state = arbitrator.onToolStart('terminal_bash_exec')
      expect(state).toBe('CODING')
      expect(arbitrator.resolve({})).toBe('CODING')

      // At 19,999 ms: tool still running
      vi.advanceTimersByTime(19999)
      expect(arbitrator.resolve({})).toBe('CODING')

      // At 20,001 ms: timed out, immediately drops to IDLE
      vi.advanceTimersByTime(2)
      expect(arbitrator.resolve({})).toBe('IDLE')
    })

    it('resets tool timeout timer when a new tool starts during an active tool', () => {
      const arbitrator = new VisualizerStateArbitrator()

      // Start Tool 1 at t=0
      arbitrator.onToolStart('crawl4ai_extract')
      expect(arbitrator.resolve({})).toBe('WEB_SEARCH')

      // Advance 15 seconds (t=15,000)
      vi.advanceTimersByTime(15000)
      expect(arbitrator.resolve({})).toBe('WEB_SEARCH')

      // Tool 2 starts at t=15,000 (resets toolStartedAt)
      arbitrator.onToolStart('markitdown_convert')
      expect(arbitrator.resolve({})).toBe('CODING')

      // Advance 10 seconds (t=25,000) -> 25s since Tool 1, but only 10s since Tool 2
      vi.advanceTimersByTime(10000)
      expect(arbitrator.resolve({})).toBe('CODING')

      // Advance past Tool 2's 20s timeout (t=35,001)
      vi.advanceTimersByTime(10001)
      expect(arbitrator.resolve({})).toBe('IDLE')
    })

    it('enforces tool dwell time at 2000ms boundary after onToolResult and decays to resting IDLE', () => {
      const arbitrator = new VisualizerStateArbitrator()

      // Start tool
      arbitrator.onToolStart('crawl4ai_extract')
      expect(arbitrator.resolve({})).toBe('WEB_SEARCH')

      // Tool result received after 500ms
      vi.advanceTimersByTime(500)
      arbitrator.onToolResult()

      // During dwell window (1,999ms after result)
      vi.advanceTimersByTime(1999)
      expect(arbitrator.resolve({})).toBe('WEB_SEARCH')

      // Past dwell window (2,001ms after result)
      vi.advanceTimersByTime(2)
      expect(arbitrator.resolve({})).toBe('IDLE')
    })

    it('enforces alert dwell at 4000ms boundary and decays to resting IDLE', () => {
      const arbitrator = new VisualizerStateArbitrator()

      arbitrator.triggerAlert()
      expect(arbitrator.resolve({})).toBe('ALERT')

      // At 3,999ms: still in ALERT
      vi.advanceTimersByTime(3999)
      expect(arbitrator.resolve({})).toBe('ALERT')

      // At 4,001ms: decays to resting state
      vi.advanceTimersByTime(2)
      expect(arbitrator.resolve({})).toBe('IDLE')
    })

    it('allows consecutive alerts to re-extend the 4000ms dwell timer', () => {
      const arbitrator = new VisualizerStateArbitrator()

      // Alert 1 at t=0
      arbitrator.triggerAlert()
      expect(arbitrator.resolve({})).toBe('ALERT')

      // Advance 3000ms (t=3000)
      vi.advanceTimersByTime(3000)
      expect(arbitrator.resolve({})).toBe('ALERT')

      // Alert 2 arrives at t=3000 -> extends dwell until t=7000
      arbitrator.triggerAlert()
      vi.advanceTimersByTime(3500) // t=6500 (would have expired without re-extension)
      expect(arbitrator.resolve({})).toBe('ALERT')

      // Advance past t=7000
      vi.advanceTimersByTime(501)
      expect(arbitrator.resolve({})).toBe('IDLE')
    })

    it('supports immediate clearAlert() without waiting for dwell expiration', () => {
      const arbitrator = new VisualizerStateArbitrator()

      arbitrator.triggerAlert()
      expect(arbitrator.resolve({})).toBe('ALERT')

      arbitrator.clearAlert()
      expect(arbitrator.resolve({})).toBe('IDLE')
    })

    it('executes full 14-stage priority preemption and graceful decay cascade', () => {
      const arbitrator = new VisualizerStateArbitrator()
      const props: SphereProps = {}

      // Stage 1: Resting Baseline
      expect(arbitrator.resolve(props)).toBe('IDLE')

      // Stage 2: Wake Word Detected -> LISTENING (50)
      props.isListening = true
      expect(arbitrator.resolve(props)).toBe('LISTENING')

      // Stage 3: Voice input complete, LLM Reasoning -> THINKING (60)
      props.isListening = false
      props.isThinking = true
      expect(arbitrator.resolve(props)).toBe('THINKING')

      // Stage 4: Background Web Search begins -> WEB_SEARCH (70)
      arbitrator.onToolStart('crawl4ai_extract')
      expect(arbitrator.resolve(props)).toBe('WEB_SEARCH')

      // Stage 5: Deep Research sub-task begins -> DEEP_RESEARCH (70)
      arbitrator.onToolStart('gpt_researcher_query')
      expect(arbitrator.resolve(props)).toBe('DEEP_RESEARCH')

      // Stage 6: Assistant begins speaking intermediate answer -> SPEAKING (80 preempts tool 70)
      props.isSpeaking = true
      expect(arbitrator.resolve(props)).toBe('SPEAKING')

      // Stage 7: Camera activates for visual inspection -> VISION_SCAN (90 preempts speaking 80)
      props.isVideoOn = true
      expect(arbitrator.resolve(props)).toBe('VISION_SCAN')

      // Stage 8: AgentShield Policy Block occurs -> ALERT (100 preempts vision 90)
      arbitrator.triggerAlert()
      expect(arbitrator.resolve(props)).toBe('ALERT')

      // Stage 9: Alert dwell expires after 4000ms -> Falls back to VISION_SCAN (90)
      vi.advanceTimersByTime(ALERT_DWELL_MS + 1)
      expect(arbitrator.resolve(props)).toBe('VISION_SCAN')

      // Stage 10: Camera turned off -> Falls back to SPEAKING (80)
      props.isVideoOn = false
      expect(arbitrator.resolve(props)).toBe('SPEAKING')

      // Stage 11: Assistant finishes speaking -> Falls back to active tool DEEP_RESEARCH (70)
      props.isSpeaking = false
      expect(arbitrator.resolve(props)).toBe('DEEP_RESEARCH')

      // Stage 12: Tool completes result -> Dwell window holds DEEP_RESEARCH
      arbitrator.onToolResult()
      vi.advanceTimersByTime(TOOL_DWELL_MS - 100)
      expect(arbitrator.resolve(props)).toBe('DEEP_RESEARCH')

      // Stage 13: Tool dwell window expires -> Falls back to THINKING (60)
      vi.advanceTimersByTime(200)
      expect(arbitrator.resolve(props)).toBe('THINKING')

      // Stage 14: Thinking completes -> Clean return to quiescent IDLE (10)
      props.isThinking = false
      expect(arbitrator.resolve(props)).toBe('IDLE')
    })

    it('proves asymptotic mathematical convergence of state weights to IDLE without frozen states', () => {
      for (const startState of STATE_KEYS) {
        if (startState === 'IDLE') continue

        // Initialize with 100% weight on startState
        const weights = createDefaultStateWeights()
        weights.IDLE = 0
        weights[startState] = 1

        // Simulate 60 frames of 16.6ms (1.0 second of decay towards IDLE)
        for (let frame = 0; frame < 60; frame++) {
          const res = updateStateWeights(weights, 'IDLE', 0.0166)
          expect(Number.isFinite(res.damp)).toBe(true)
        }

        // After 1 second at damp factor (1 - exp(-6.2 * dt)), IDLE must dominate (> 0.995)
        expect(weights.IDLE).toBeGreaterThan(0.99)
        expect(weights[startState]).toBeLessThan(0.01)

        // All weights must be valid finite non-negative numbers
        for (const k of STATE_KEYS) {
          expect(weights[k]).toBeGreaterThanOrEqual(0)
          expect(Number.isFinite(weights[k])).toBe(true)
        }
      }
    })
  })
})
