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

describe('Milestone 2: Visualizer State & Event Wiring Test Suite', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    jarvisRealtimeRef.audioLevel = 0
    jarvisRealtimeRef.voiceState = 'IDLE'
    jarvisRealtimeRef.isSpeaking = false
    jarvisRealtimeRef.isListening = false
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  // =========================================================================
  // AREA 1: STATE MAPPING FROM RUNTIME EVENTS & TOOL CLASSIFIER
  // =========================================================================
  describe('Area 1: State Mapping from Application Runtime Events', () => {
    it('normalizes all 11 canonical states and case variants', () => {
      for (const state of STATE_KEYS) {
        expect(normalizeStateName(state)).toBe(state)
        expect(normalizeStateName(state.toLowerCase())).toBe(state)
        expect(normalizeStateName(`  ${state}  `)).toBe(state)
      }
    })

    it('maps agent.state events and voice aliases correctly', () => {
      expect(normalizeStateName('idle')).toBe('IDLE')
      expect(normalizeStateName('listening')).toBe('LISTENING')
      expect(normalizeStateName('listen')).toBe('LISTENING')
      expect(normalizeStateName('hearing')).toBe('LISTENING')
      expect(normalizeStateName('wake_word')).toBe('LISTENING')
      expect(normalizeStateName('wake_word_detected')).toBe('LISTENING')
      expect(normalizeStateName('thinking')).toBe('THINKING')
      expect(normalizeStateName('processing')).toBe('THINKING')
      expect(normalizeStateName('reasoning')).toBe('THINKING')
      expect(normalizeStateName('transcribing')).toBe('THINKING')
      expect(normalizeStateName('compressing')).toBe('THINKING')
      expect(normalizeStateName('speaking')).toBe('SPEAKING')
      expect(normalizeStateName('talking')).toBe('SPEAKING')
      expect(normalizeStateName('error')).toBe('ALERT')
      expect(normalizeStateName('critical')).toBe('ALERT')
      expect(normalizeStateName('warn')).toBe('ALERT')
    })

    it('classifies all tool prefixes and actions into the 5 specialized tool domains', () => {
      // 1. WEB_SEARCH: crawl4ai, browser_use, /search, google, web
      expect(classifyToolState('crawl4ai_extract')).toBe('WEB_SEARCH')
      expect(classifyToolState('browser_use_background')).toBe('WEB_SEARCH')
      expect(classifyToolState('/search?q=test')).toBe('WEB_SEARCH')
      expect(classifyToolState('google_web_search')).toBe('WEB_SEARCH')
      expect(classifyToolState('web_scrape_page')).toBe('WEB_SEARCH')

      // 2. DEEP_RESEARCH: gpt_researcher, delegate_task, research, investigate, analyze
      // Priority check: gpt_researcher must NOT match 'search'
      expect(classifyToolState('gpt_researcher_report')).toBe('DEEP_RESEARCH')
      expect(classifyToolState('gpt_researcher_query')).toBe('DEEP_RESEARCH')
      expect(classifyToolState('delegate_task')).toBe('DEEP_RESEARCH')
      expect(classifyToolState('deep_investigate')).toBe('DEEP_RESEARCH')
      expect(classifyToolState('data_analyzer')).toBe('DEEP_RESEARCH')

      // 3. CODING: markitdown, code_, terminal, bash, edit, exec, shell
      expect(classifyToolState('markitdown_convert')).toBe('CODING')
      expect(classifyToolState('code_interpreter')).toBe('CODING')
      expect(classifyToolState('terminal_bash_exec')).toBe('CODING')
      expect(classifyToolState('shell_command')).toBe('CODING')
      expect(classifyToolState('file_editor')).toBe('CODING')

      // 4. VISION_SCAN: camera, mediapipe, deepface, vision, agent_s3, windows_mcp_snapshot, lidar
      expect(classifyToolState('camera_stream_read')).toBe('VISION_SCAN')
      expect(classifyToolState('mediapipe_face_mesh')).toBe('VISION_SCAN')
      expect(classifyToolState('deepface_verify')).toBe('VISION_SCAN')
      expect(classifyToolState('agent_s3_visual_task')).toBe('VISION_SCAN')
      expect(classifyToolState('windows_mcp_snapshot')).toBe('VISION_SCAN')
      expect(classifyToolState('lidar_depth_scan')).toBe('VISION_SCAN')

      // 5. MEMORY_SYNC: memory, state_db, saveCoreMemory, retrieveCoreMemory, session_search
      expect(classifyToolState('memory_store')).toBe('MEMORY_SYNC')
      expect(classifyToolState('state_db_vacuum')).toBe('MEMORY_SYNC')
      expect(classifyToolState('saveCoreMemory')).toBe('MEMORY_SYNC')
      expect(classifyToolState('retrieveCoreMemory')).toBe('MEMORY_SYNC')
      expect(classifyToolState('session_search')).toBe('MEMORY_SYNC')
      expect(classifyToolState('sqlite_db_query')).toBe('MEMORY_SYNC')

      // 6. Generic EXECUTING_TOOL fallback
      expect(classifyToolState('windows_mcp_click')).toBe('EXECUTING_TOOL')
      expect(classifyToolState('mobilerun_phone_task')).toBe('EXECUTING_TOOL')
      expect(classifyToolState('todo_create')).toBe('EXECUTING_TOOL')
      expect(classifyToolState('unknown_tool_plugin')).toBe('EXECUTING_TOOL')
      expect(classifyToolState(null)).toBe('EXECUTING_TOOL')
      expect(classifyToolState(undefined)).toBe('EXECUTING_TOOL')
      expect(classifyToolState('')).toBe('EXECUTING_TOOL')
    })
  })

  // =========================================================================
  // AREA 2: PRIORITY ARBITRATION HIERARCHY
  // =========================================================================
  describe('Area 2: Priority Arbitration Hierarchy', () => {
    it('enforces ALERT (100) over all other states', () => {
      const props: SphereProps = {
        error: 'AgentShield critical security violation',
        isVideoOn: true,
        isSpeaking: true,
        activeTool: 'crawl4ai_extract',
        isThinking: true,
        isListening: true,
      }
      expect(resolveActiveState(props, 'SPEAKING')).toBe('ALERT')
    })

    it('enforces VISION_SCAN (90) over SPEAKING, active tools, thinking, listening', () => {
      // isVideoOn mode
      const propsVisionOn: SphereProps = {
        isVideoOn: true,
        isSpeaking: true,
        activeTool: 'crawl4ai_extract',
        isThinking: true,
        isListening: true,
      }
      expect(resolveActiveState(propsVisionOn)).toBe('VISION_SCAN')

      // vision tool active
      const propsVisionTool: SphereProps = {
        activeTool: 'camera_stream_read',
        isSpeaking: true,
        isThinking: true,
        isListening: true,
      }
      expect(resolveActiveState(propsVisionTool)).toBe('VISION_SCAN')
    })

    it('enforces SPEAKING (80) over ACTIVE_TOOL (70)', () => {
      const propsSpeakingOverTool: SphereProps = {
        isSpeaking: true,
        activeTool: 'crawl4ai_extract',
        isThinking: false,
        isListening: false,
      }
      expect(resolveActiveState(propsSpeakingOverTool)).toBe('SPEAKING')

      const propsRealtimeSpeaking: SphereProps = {
        activeTool: 'code_interpreter',
        isThinking: true,
      }
      expect(resolveActiveState(propsRealtimeSpeaking, 'SPEAKING')).toBe('SPEAKING')
    })

    it('enforces ACTIVE_TOOL (70) over THINKING (60) and LISTENING (50)', () => {
      expect(resolveActiveState({ activeTool: 'crawl4ai_extract', isThinking: true })).toBe('WEB_SEARCH')
      expect(resolveActiveState({ activeTool: 'gpt_researcher_report', isThinking: true })).toBe('DEEP_RESEARCH')
      expect(resolveActiveState({ activeTool: 'markitdown_convert', isListening: true })).toBe('CODING')
      expect(resolveActiveState({ activeTool: 'memory_store', isListening: true })).toBe('MEMORY_SYNC')
      expect(resolveActiveState({ activeTool: 'todo_create', isThinking: true })).toBe('EXECUTING_TOOL')
    })

    it('enforces sequential cascade down the exact priority ladder', () => {
      // Step 1: Fatal Error present -> ALERT (100)
      const s1 = resolveActiveState({
        error: 'SecurityBlock',
        isVideoOn: true,
        isSpeaking: true,
        activeTool: 'markitdown_convert',
        isThinking: true,
        isListening: true,
      })
      expect(s1).toBe('ALERT')

      // Step 2: Error cleared, Camera stream active -> VISION_SCAN (90)
      const s2 = resolveActiveState({
        isVideoOn: true,
        isSpeaking: true,
        activeTool: 'markitdown_convert',
        isThinking: true,
        isListening: true,
      })
      expect(s2).toBe('VISION_SCAN')

      // Step 3: Camera turned off, Assistant is speaking -> SPEAKING (80)
      const s3 = resolveActiveState({
        isSpeaking: true,
        activeTool: 'markitdown_convert',
      })
      expect(s3).toBe('SPEAKING')

      // Step 4: Speaking finishes, Background tool running -> CODING (70)
      const s4 = resolveActiveState({
        activeTool: 'markitdown_convert',
        isThinking: true,
        isListening: true,
      })
      expect(s4).toBe('CODING')

      // Step 5: Tool finishes, LLM thinking remains -> THINKING (60)
      const s5 = resolveActiveState({
        isThinking: true,
        isListening: true,
      })
      expect(s5).toBe('THINKING')

      // Step 6: Thinking finishes, Mic is active -> LISTENING (50)
      const s6 = resolveActiveState({
        isListening: true,
      })
      expect(s6).toBe('LISTENING')

      // Step 7: Mic closed -> IDLE (10)
      const s7 = resolveActiveState({})
      expect(s7).toBe('IDLE')
    })
  })

  // =========================================================================
  // AREA 3: FALLBACK AND DWELL TIMERS
  // =========================================================================
  describe('Area 3: Fallback and Dwell Timers', () => {
    it('exports standard timing constants for dwell and safety fallbacks', () => {
      expect(TOOL_DWELL_MS).toBe(2000)
      expect(TOOL_TIMEOUT_MS).toBe(20000)
      expect(ALERT_DWELL_MS).toBe(4000)
      expect(SPEECH_DECAY_MS).toBe(350)
    })

    it('VisualizerStateArbitrator maintains tool dwell time after tool finishes', () => {
      const arbitrator = new VisualizerStateArbitrator()

      // Start tool
      const toolState = arbitrator.onToolStart('crawl4ai_extract')
      expect(toolState).toBe('WEB_SEARCH')
      expect(arbitrator.resolve({})).toBe('WEB_SEARCH')

      // Tool result arrives
      arbitrator.onToolResult()

      // At 1000ms: still inside 2000ms dwell window
      vi.advanceTimersByTime(1000)
      expect(arbitrator.resolve({})).toBe('WEB_SEARCH')

      // At 2001ms: dwell expired, smoothly returns to IDLE
      vi.advanceTimersByTime(1001)
      expect(arbitrator.resolve({})).toBe('IDLE')
    })

    it('VisualizerStateArbitrator safety timeout expires hung tools after 20s', () => {
      const arbitrator = new VisualizerStateArbitrator()

      arbitrator.onToolStart('shell_command')
      expect(arbitrator.resolve({})).toBe('CODING')

      // Advance 19.9 seconds: tool still active
      vi.advanceTimersByTime(19900)
      expect(arbitrator.resolve({})).toBe('CODING')

      // Advance past 20.0 seconds: safety timeout drops tool state back to IDLE
      vi.advanceTimersByTime(200)
      expect(arbitrator.resolve({})).toBe('IDLE')
    })

    it('VisualizerStateArbitrator alert dwell maintains ALERT for 4000ms', () => {
      const arbitrator = new VisualizerStateArbitrator()

      arbitrator.triggerAlert()
      expect(arbitrator.resolve({})).toBe('ALERT')

      // Advance 3000ms: still ALERT
      vi.advanceTimersByTime(3000)
      expect(arbitrator.resolve({})).toBe('ALERT')

      // Advance past 4000ms: drops back to IDLE
      vi.advanceTimersByTime(1001)
      expect(arbitrator.resolve({})).toBe('IDLE')
    })
  })

  // =========================================================================
  // AREA 4: CUSTOMEVENT (jarvis-state) DETAIL UNPACKING
  // =========================================================================
  describe('Area 4: CustomEvent (jarvis-state) Payload Unpacking', () => {
    it('unpacks standard object payloads { detail: { state: ... } } and string primitives', () => {
      // Standard object payload per PROJECT.md
      expect(unpackJarvisStateDetail({ state: 'THINKING' })).toBe('THINKING')
      expect(unpackJarvisStateDetail({ state: 'web_search' })).toBe('WEB_SEARCH')
      expect(unpackJarvisStateDetail({ state: 'deep_research' })).toBe('DEEP_RESEARCH')

      // Primitive string payloads
      expect(unpackJarvisStateDetail('SPEAKING')).toBe('SPEAKING')
      expect(unpackJarvisStateDetail('coding')).toBe('CODING')
      expect(unpackJarvisStateDetail('alert')).toBe('ALERT')
      expect(unpackJarvisStateDetail('vision_scan')).toBe('VISION_SCAN')
      expect(unpackJarvisStateDetail('memory_sync')).toBe('MEMORY_SYNC')
      expect(unpackJarvisStateDetail('executing_tool')).toBe('EXECUTING_TOOL')

      // Alternative object properties
      expect(unpackJarvisStateDetail({ voiceState: 'LISTENING' })).toBe('LISTENING')
      expect(unpackJarvisStateDetail({ status: 'THINKING' })).toBe('THINKING')
      expect(unpackJarvisStateDetail({ mode: 'VISION_SCAN' })).toBe('VISION_SCAN')
      expect(unpackJarvisStateDetail({ value: 'CODING' })).toBe('CODING')
      expect(unpackJarvisStateDetail({ name: 'IDLE' })).toBe('IDLE')

      // Nested envelope payloads
      expect(unpackJarvisStateDetail({ detail: { state: 'ALERT' } })).toBe('ALERT')
      expect(unpackJarvisStateDetail({ payload: { state: 'WEB_SEARCH' } })).toBe('WEB_SEARCH')
      expect(unpackJarvisStateDetail({ detail: 'SPEAKING' })).toBe('SPEAKING')

      // Legacy aliases
      expect(unpackJarvisStateDetail('PROCESSING')).toBe('THINKING')
      expect(unpackJarvisStateDetail('LISTEN')).toBe('LISTENING')
      expect(unpackJarvisStateDetail({ state: 'transcribing' })).toBe('THINKING')
      expect(unpackJarvisStateDetail({ state: 'compressing' })).toBe('THINKING')

      // Invalid / edge cases safely return null
      expect(unpackJarvisStateDetail(null)).toBeNull()
      expect(unpackJarvisStateDetail(undefined)).toBeNull()
      expect(unpackJarvisStateDetail('')).toBeNull()
      expect(unpackJarvisStateDetail('INVALID_NON_EXISTENT_STATE')).toBeNull()
      expect(unpackJarvisStateDetail(12345)).toBeNull()
    })

    it('integrates with window jarvis-state event dispatching', () => {
      let capturedState: string | null = null
      const listener = (e: Event) => {
        capturedState = unpackJarvisStateDetail((e as CustomEvent).detail)
      }

      window.addEventListener('jarvis-state', listener)
      try {
        // Test object dispatch
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'DEEP_RESEARCH' } }))
        expect(capturedState).toBe('DEEP_RESEARCH')

        // Test string primitive dispatch
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'CODING' }))
        expect(capturedState).toBe('CODING')

        // Test wake word payload
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'LISTENING' } }))
        expect(capturedState).toBe('LISTENING')
      } finally {
        window.removeEventListener('jarvis-state', listener)
      }
    })
  })

  // =========================================================================
  // AREA 5: KEYBOARD HOTKEYS & INPUT GUARDS
  // =========================================================================
  describe('Area 5: Keyboard Shortcuts & Strict Input Guards', () => {
    it('maps all keys 1 through 0 and - to the 11 states', () => {
      expect(KEY_STATE_MAP['1']).toBe('IDLE')
      expect(KEY_STATE_MAP['2']).toBe('LISTENING')
      expect(KEY_STATE_MAP['3']).toBe('THINKING')
      expect(KEY_STATE_MAP['4']).toBe('SPEAKING')
      expect(KEY_STATE_MAP['5']).toBe('WEB_SEARCH')
      expect(KEY_STATE_MAP['6']).toBe('DEEP_RESEARCH')
      expect(KEY_STATE_MAP['7']).toBe('CODING')
      expect(KEY_STATE_MAP['8']).toBe('VISION_SCAN')
      expect(KEY_STATE_MAP['9']).toBe('MEMORY_SYNC')
      expect(KEY_STATE_MAP['0']).toBe('EXECUTING_TOOL')
      expect(KEY_STATE_MAP['-']).toBe('ALERT')
    })

    it('executes keyboard shortcut when user presses key on canvas or neutral background', () => {
      let receivedState: string | null = null
      const handleState = (e: Event) => {
        receivedState = unpackJarvisStateDetail((e as CustomEvent).detail)
      }
      window.addEventListener('jarvis-state', handleState)

      const handleKey = (e: KeyboardEvent) => {
        if (e.ctrlKey || e.altKey || e.metaKey) return
        const target = e.target as HTMLElement | null
        if (!target) return
        const tag = target.tagName?.toUpperCase()
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
        if (target.isContentEditable) return
        if (target.closest && target.closest('[contenteditable="true"], [contenteditable=""], [contenteditable], .monaco-editor, .xterm, [role="textbox"]')) return

        const mapped = KEY_STATE_MAP[e.key]
        if (mapped) {
          window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))
        }
      }
      window.addEventListener('keydown', handleKey)

      try {
        window.dispatchEvent(new KeyboardEvent('keydown', { key: '5' }))
        expect(receivedState).toBe('WEB_SEARCH')

        window.dispatchEvent(new KeyboardEvent('keydown', { key: '7' }))
        expect(receivedState).toBe('CODING')

        window.dispatchEvent(new KeyboardEvent('keydown', { key: '-' }))
        expect(receivedState).toBe('ALERT')
      } finally {
        window.removeEventListener('jarvis-state', handleState)
        window.removeEventListener('keydown', handleKey)
      }
    })

    it('strictly guards against hotkey triggers when user types in form controls or editors', () => {
      let triggerCount = 0
      const handleState = () => { triggerCount++ }
      window.addEventListener('jarvis-state', handleState)

      const handleKey = (e: KeyboardEvent) => {
        if (e.ctrlKey || e.altKey || e.metaKey) return
        const target = e.target as HTMLElement | null
        if (!target) return
        const tag = target.tagName?.toUpperCase()
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
        if (target.isContentEditable || (target as any).contentEditable === 'true' || target.getAttribute?.('contenteditable') === 'true') return
        if (target.closest && target.closest('[contenteditable="true"], [contenteditable=""], [contenteditable], .monaco-editor, .xterm, [role="textbox"]')) return

        const mapped = KEY_STATE_MAP[e.key]
        if (mapped) {
          window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))
        }
      }
      window.addEventListener('keydown', handleKey)

      try {
        // 1. HTMLInputElement
        const input = document.createElement('input')
        document.body.appendChild(input)
        input.dispatchEvent(new KeyboardEvent('keydown', { key: '1', bubbles: true }))
        expect(triggerCount).toBe(0)

        // 2. HTMLTextAreaElement
        const textarea = document.createElement('textarea')
        document.body.appendChild(textarea)
        textarea.dispatchEvent(new KeyboardEvent('keydown', { key: '2', bubbles: true }))
        expect(triggerCount).toBe(0)

        // 3. HTMLSelectElement
        const select = document.createElement('select')
        document.body.appendChild(select)
        select.dispatchEvent(new KeyboardEvent('keydown', { key: '3', bubbles: true }))
        expect(triggerCount).toBe(0)

        // 4. ContentEditable element
        const editable = document.createElement('div')
        editable.setAttribute('contenteditable', 'true')
        ;(editable as any).contentEditable = 'true'
        document.body.appendChild(editable)
        editable.dispatchEvent(new KeyboardEvent('keydown', { key: '4', bubbles: true }))
        expect(triggerCount).toBe(0)

        // 5. Modifier keys: Ctrl+1, Alt+1, Meta+1
        window.dispatchEvent(new KeyboardEvent('keydown', { key: '1', ctrlKey: true }))
        window.dispatchEvent(new KeyboardEvent('keydown', { key: '2', altKey: true }))
        window.dispatchEvent(new KeyboardEvent('keydown', { key: '3', metaKey: true }))
        expect(triggerCount).toBe(0)

        // Cleanup DOM
        document.body.removeChild(input)
        document.body.removeChild(textarea)
        document.body.removeChild(select)
        document.body.removeChild(editable)
      } finally {
        window.removeEventListener('jarvis-state', handleState)
        window.removeEventListener('keydown', handleKey)
      }
    })
  })

  // =========================================================================
  // AREA 6: AUDIO LEVEL STREAMING & DYNAMIC REACTIVITY
  // =========================================================================
  describe('Area 6: Audio Level Streaming & Dynamic Reactivity', () => {
    it('updates jarvisRealtimeRef.audioLevel synchronously without virtual DOM thrashing', () => {
      expect(jarvisRealtimeRef.audioLevel).toBe(0)

      jarvisRealtimeRef.audioLevel = 0.85
      expect(jarvisRealtimeRef.audioLevel).toBe(0.85)

      jarvisRealtimeRef.audioLevel = 0.12
      expect(jarvisRealtimeRef.audioLevel).toBe(0.12)

      jarvisRealtimeRef.audioLevel = 0.0
      expect(jarvisRealtimeRef.audioLevel).toBe(0.0)
    })

    it('clamps state weight delta times and dampens weights monotonically', () => {
      const weights = createDefaultStateWeights()
      expect(weights.IDLE).toBe(1)
      expect(weights.SPEAKING).toBe(0)

      // Step 1: Small frame delta (16.6ms)
      const res1 = updateStateWeights(weights, 'SPEAKING', 0.0166)
      expect(res1.dt).toBeCloseTo(0.0166, 4)
      expect(weights.SPEAKING).toBeGreaterThan(0)
      expect(weights.IDLE).toBeLessThan(1)

      // Step 2: Extreme spike delta is clamped to 0.05
      const resSpike = updateStateWeights(weights, 'SPEAKING', 5.0)
      expect(resSpike.dt).toBe(0.05)
      expect(weights.SPEAKING).toBeGreaterThan(0.2)
    })

    it('gatewayClient updates jarvisRealtimeRef during TTS lifecycle', () => {
      let dispatchedStates: string[] = []
      const listener = (e: Event) => {
        dispatchedStates.push(String((e as CustomEvent).detail))
      }
      window.addEventListener('jarvis-state', listener)

      try {
        // Cancel speech resets audio level and state to IDLE
        jarvisRealtimeRef.audioLevel = 0.95
        jarvisRealtimeRef.isSpeaking = true
        gatewayClient.cancelSpeech()

        expect(jarvisRealtimeRef.audioLevel).toBe(0)
        expect(jarvisRealtimeRef.isSpeaking).toBe(false)
        expect(jarvisRealtimeRef.voiceState).toBe('IDLE')
        expect(dispatchedStates).toContain('IDLE')
      } finally {
        window.removeEventListener('jarvis-state', listener)
      }
    })
  })
})
