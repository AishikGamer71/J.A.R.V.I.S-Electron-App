/**
 * Challenger 1: Adversarial Stress Test Harness for Milestone 2
 * Visualizer State Arbitration & Event Wiring
 *
 * Objectives:
 * 1. Rapid concurrent event bursts (1000+ rapid state changes and 64 combination subsets)
 *    testing strict priority hierarchy invariance:
 *    ALERT > VISION_SCAN > SPEAKING > ACTIVE_TOOL > THINKING > LISTENING > IDLE.
 * 2. Race condition stress tests: tool during speaking, alert during tool,
 *    vision during alert, tool finish during alert.
 * 3. Fallback and dwell time lifecycles (TOOL_DWELL_MS=2000, TOOL_TIMEOUT_MS=20000, ALERT_DWELL_MS=4000)
 *    and empirical verification of runtime wiring in HolographicCoreScene & GatewayClient.
 * 4. Crash resilience, extreme corrupted payloads, circular references, and numerical stability.
 * 5. Shadowing of voiceState by stale realtimeBusState.
 */

// Ensure global window and EventTarget exist for headless Node execution
if (typeof (globalThis as any).window === 'undefined') {
  const dummyWindow = {
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
    CustomEvent: class CustomEvent {
      type: string
      detail: any
      constructor(type: string, init?: any) {
        this.type = type
        this.detail = init?.detail
      }
    },
  } as any
  ;(globalThis as any).window = dummyWindow
  ;(globalThis as any).CustomEvent = dummyWindow.CustomEvent
}

import {
  classifyToolState,
  createDefaultStateWeights,
  normalizeStateName,
  resolveActiveState,
  unpackJarvisStateDetail,
  updateStateWeights,
  VisualizerStateArbitrator,
  TOOL_DWELL_MS,
  TOOL_TIMEOUT_MS,
  ALERT_DWELL_MS,
  SPEECH_DECAY_MS,
  calculateCardiacBeat,
} from '../src/components/dashboard/holographic-core/state-machine'
import { STATE_KEYS, KEY_STATE_MAP } from '../src/components/dashboard/holographic-core/constants'
import type { HolographicState, SphereProps, StateWeights } from '../src/components/dashboard/holographic-core/types'
import { jarvisRealtimeRef } from '../src/services/jarvisBridge'
import * as fs from 'fs'
import * as path from 'path'

export interface TestCaseResult {
  suite: string
  name: string
  passed: boolean
  expected: any
  actual: any
  details?: string
  isVulnerability?: boolean
}

const testResults: TestCaseResult[] = []

function assert(condition: boolean, suite: string, name: string, expected: any, actual: any, details?: string, isVulnerability = false) {
  testResults.push({
    suite,
    name,
    passed: condition,
    expected,
    actual,
    details,
    isVulnerability: !condition || isVulnerability,
  })
}

console.log('========================================================================')
console.log('CHALLENGER 1: ADVERSARIAL STRESS TEST HARNESS — MILESTONE 2')
console.log('Visualizer State Arbitration & Event Wiring')
console.log('========================================================================\n')

// ============================================================================
// SUITE 1: 500+ RAPID CONCURRENT EVENT BURSTS & COMBINATORIAL INVARIANCE
// ============================================================================
console.log('>>> Running Suite 1: Concurrent Event Bursts & Combinatorial Invariance...')

const TOOL_SAMPLES: Record<string, HolographicState> = {
  'crawl4ai_scrape': 'WEB_SEARCH',
  'browser_use_nav': 'WEB_SEARCH',
  'gpt_researcher_deep': 'DEEP_RESEARCH',
  'delegate_task_batch': 'DEEP_RESEARCH',
  'markitdown_doc': 'CODING',
  'code_exec_py': 'CODING',
  'camera_frame_capture': 'VISION_SCAN',
  'mediapipe_landmarks': 'VISION_SCAN',
  'memory_store_fact': 'MEMORY_SYNC',
  'session_search_recent': 'MEMORY_SYNC',
  'windows_mcp_run': 'EXECUTING_TOOL',
}

// 1.1 Combinatorial Priority Ladder Matrix
// Test all 2^6 = 64 boolean combinations of active signals (error, isVideoOn, isSpeaking, activeTool, isThinking, isListening)
let combinationsTested = 0
let combinationsPassed = 0
const priorityFailures: Array<{ flags: any; expected: HolographicState; actual: HolographicState; reason: string }> = []

const bools = [false, true]
for (const error of bools) {
  for (const isVideoOn of bools) {
    for (const isSpeaking of bools) {
      for (const hasTool of bools) {
        for (const isThinking of bools) {
          for (const isListening of bools) {
            combinationsTested++
            const toolName = hasTool ? 'code_exec_py' : undefined // maps to CODING (Priority 70)
            const props: SphereProps = {
              error: error ? 'Simulated Alarm' : undefined,
              isVideoOn: isVideoOn,
              isSpeaking: isSpeaking,
              activeTool: toolName,
              isThinking: isThinking,
              isListening: isListening,
            }

            // Theoretical expected based on canonical contract:
            // ALERT (100) > VISION_SCAN (90) > SPEAKING (80) > ACTIVE_TOOL (70) > THINKING (60) > LISTENING (50) > IDLE (10)
            let expected: HolographicState = 'IDLE'
            if (error) {
              expected = 'ALERT'
            } else if (isVideoOn) {
              expected = 'VISION_SCAN'
            } else if (isSpeaking) {
              expected = 'SPEAKING'
            } else if (hasTool) {
              expected = 'CODING'
            } else if (isThinking) {
              expected = 'THINKING'
            } else if (isListening) {
              expected = 'LISTENING'
            }

            const actual = resolveActiveState(props)
            if (actual === expected) {
              combinationsPassed++
            } else {
              priorityFailures.push({
                flags: { error, isVideoOn, isSpeaking, hasTool, isThinking, isListening },
                expected,
                actual,
                reason: `Priority inversion: expected ${expected} but got ${actual}`,
              })
            }
          }
        }
      }
    }
  }
}

assert(
  priorityFailures.length === 0,
  'Suite 1: Combinatorial Invariance',
  '64 Boolean Signal Combinations Priority Hierarchy',
  `${combinationsTested}/${combinationsTested} pass`,
  `${combinationsPassed}/${combinationsTested} pass`,
  priorityFailures.length > 0
    ? `Identified ${priorityFailures.length} priority inversions! Details: ${JSON.stringify(priorityFailures[0])}`
    : 'All 64 combinations strictly followed priority hierarchy.'
)

// 1.2 Burst of 1000 Rapid Random Events
let burstPassed = 0
const BURST_COUNT = 1000
const burstInversions: string[] = []

for (let i = 0; i < BURST_COUNT; i++) {
  const err = Math.random() < 0.15 ? 'Random Error' : undefined
  const video = Math.random() < 0.20
  const speak = Math.random() < 0.35
  const toolKeys = Object.keys(TOOL_SAMPLES)
  const toolName = Math.random() < 0.5 ? toolKeys[Math.floor(Math.random() * toolKeys.length)] : undefined
  const think = Math.random() < 0.4
  const listen = Math.random() < 0.4

  const props: SphereProps = {
    error: err,
    isVideoOn: video,
    isSpeaking: speak,
    activeTool: toolName,
    isThinking: think,
    isListening: listen,
  }

  // Canonical hierarchy computation
  let expected: HolographicState = 'IDLE'
  if (err) {
    expected = 'ALERT'
  } else if (video) {
    expected = 'VISION_SCAN'
  } else if (toolName && classifyToolState(toolName) === 'VISION_SCAN') {
    expected = 'VISION_SCAN'
  } else if (speak) {
    expected = 'SPEAKING'
  } else if (toolName) {
    expected = classifyToolState(toolName)
  } else if (think) {
    expected = 'THINKING'
  } else if (listen) {
    expected = 'LISTENING'
  }

  const actual = resolveActiveState(props)
  if (actual === expected) {
    burstPassed++
  } else {
    if (burstInversions.length < 5) {
      burstInversions.push(`Iter ${i}: expected=${expected}, actual=${actual}, props=${JSON.stringify(props)}`)
    }
  }
}

assert(
  burstPassed === BURST_COUNT,
  'Suite 1: Concurrent Event Bursts',
  '1000 Rapid Random Event Bursts Hierarchy Invariance',
  BURST_COUNT,
  burstPassed,
  burstInversions.length > 0
    ? `Burst test failed with ${BURST_COUNT - burstPassed} inversions. First failure: ${burstInversions[0]}`
    : `1000/1000 rapid state transitions preserved priority order.`
)

// 1.3 Pinpointing the isLegacyTestFixture Priority Inversion
// Test the exact condition: activeTool present, isSpeaking=true, isThinking=true, isListening=true
const testFixtureProps: SphereProps = {
  activeTool: 'crawl4ai_scrape', // maps to WEB_SEARCH
  isSpeaking: true,
  isThinking: true,
  isListening: true,
}
const fixtureActual = resolveActiveState(testFixtureProps)
assert(
  fixtureActual === 'SPEAKING',
  'Suite 1: Specific Bug Probes',
  'Legacy Test Fixture Priority Inversion Check (isSpeaking vs activeTool)',
  'SPEAKING',
  fixtureActual,
  fixtureActual === 'SPEAKING'
    ? 'SPEAKING correctly took precedence over activeTool.'
    : `VULNERABILITY CONFIRMED: resolveActiveState line 185 has hardcoded 'isLegacyTestFixture' exception causing activeTool (${fixtureActual}) to override SPEAKING when all booleans are true.`
)


// ============================================================================
// SUITE 2: RACE CONDITION STRESS HARNESS
// ============================================================================
console.log('>>> Running Suite 2: Race Condition Stress Harness...')

// Scenario A: Tool starts while speaking -> SPEAKING must dominate, then tool takes over when speaking finishes
let raceProps: SphereProps = { isSpeaking: true }
let stateAtA1 = resolveActiveState(raceProps)
assert(stateAtA1 === 'SPEAKING', 'Suite 2: Race Conditions', 'Scenario A1: Speaking initially active', 'SPEAKING', stateAtA1)

// Tool starts
raceProps.activeTool = 'gpt_researcher_deep'
let stateAtA2 = resolveActiveState(raceProps)
assert(stateAtA2 === 'SPEAKING', 'Suite 2: Race Conditions', 'Scenario A2: Tool starts while speaking (SPEAKING > TOOL)', 'SPEAKING', stateAtA2)

// Speaking ends -> Tool must immediately become visible
raceProps.isSpeaking = false
let stateAtA3 = resolveActiveState(raceProps)
assert(stateAtA3 === 'DEEP_RESEARCH', 'Suite 2: Race Conditions', 'Scenario A3: Speaking ends while tool running (TOOL revealed)', 'DEEP_RESEARCH', stateAtA3)

// Scenario B: Alert triggers while tool is running -> ALERT must preempt tool
raceProps.error = 'Security breach: AgentShield blocked prompt injection'
let stateAtB1 = resolveActiveState(raceProps)
assert(stateAtB1 === 'ALERT', 'Suite 2: Race Conditions', 'Scenario B1: Alert triggers while tool running (ALERT > TOOL)', 'ALERT', stateAtB1)

// Scenario C: Vision turns on while alert is active -> ALERT must dominate vision
raceProps.isVideoOn = true
let stateAtC1 = resolveActiveState(raceProps)
assert(stateAtC1 === 'ALERT', 'Suite 2: Race Conditions', 'Scenario C1: Vision turns on while alert active (ALERT > VISION_SCAN)', 'ALERT', stateAtC1)

// Scenario D: Tool finishes while alert is active -> Visualizer must remain in ALERT
raceProps.activeTool = undefined
let stateAtD1 = resolveActiveState(raceProps)
assert(stateAtD1 === 'ALERT', 'Suite 2: Race Conditions', 'Scenario D1: Tool finishes while alert active (ALERT remains)', 'ALERT', stateAtD1)

// Alert clears -> Vision must now be active
raceProps.error = undefined
let stateAtD2 = resolveActiveState(raceProps)
assert(stateAtD2 === 'VISION_SCAN', 'Suite 2: Race Conditions', 'Scenario D2: Alert clears while vision on (VISION_SCAN revealed)', 'VISION_SCAN', stateAtD2)

// Vision turns off -> Visualizer returns to IDLE
raceProps.isVideoOn = false
let stateAtD3 = resolveActiveState(raceProps)
assert(stateAtD3 === 'IDLE', 'Suite 2: Race Conditions', 'Scenario D3: Vision turns off (IDLE reached cleanly)', 'IDLE', stateAtD3)


// ============================================================================
// SUITE 3: DWELL TIMES, FALLBACK TIMEOUTS & RUNTIME INTEGRATION FORENSICS
// ============================================================================
console.log('>>> Running Suite 3: Dwell Times & Fallback Forensics...')

// 3.1 VisualizerStateArbitrator in isolation
const arb = new VisualizerStateArbitrator()

// Test 3.1.1: Tool dwell time (2000ms)
const t0 = Date.now()
arb.onToolStart('shell_command') // CODING
assert(arb.resolve({}) === 'CODING', 'Suite 3: Arbitrator Unit', 'Tool started -> CODING', 'CODING', arb.resolve({}))

arb.onToolResult()
const originalDateNow = Date.now
try {
  Date.now = () => t0 + 1000
  assert(arb.resolve({}) === 'CODING', 'Suite 3: Arbitrator Unit', 'Tool dwell at 1000ms holds state', 'CODING', arb.resolve({}))

  Date.now = () => t0 + 2050
  assert(arb.resolve({}) === 'IDLE', 'Suite 3: Arbitrator Unit', 'Tool dwell expired at 2050ms returns to IDLE', 'IDLE', arb.resolve({}))
} finally {
  Date.now = originalDateNow
}

// Test 3.1.2: Hung Tool Safety Timeout (20000ms)
const hungArb = new VisualizerStateArbitrator()
const hungT0 = 1000000
try {
  Date.now = () => hungT0
  hungArb.onToolStart('browser_use_nav')
  assert(hungArb.resolve({}) === 'WEB_SEARCH', 'Suite 3: Arbitrator Unit', 'Hung tool starts -> WEB_SEARCH', 'WEB_SEARCH', hungArb.resolve({}))

  // At 19.9s: still running
  Date.now = () => hungT0 + 19900
  assert(hungArb.resolve({}) === 'WEB_SEARCH', 'Suite 3: Arbitrator Unit', 'Hung tool at 19.9s still active', 'WEB_SEARCH', hungArb.resolve({}))

  // At 20.1s: times out back to IDLE
  Date.now = () => hungT0 + 20100
  assert(hungArb.resolve({}) === 'IDLE', 'Suite 3: Arbitrator Unit', 'Hung tool at 20.1s times out to IDLE', 'IDLE', hungArb.resolve({}))
} finally {
  Date.now = originalDateNow
}

// Test 3.1.3: Alert Dwell Time (4000ms)
const alertArb = new VisualizerStateArbitrator()
const alertT0 = 2000000
try {
  Date.now = () => alertT0
  alertArb.triggerAlert()
  assert(alertArb.resolve({}) === 'ALERT', 'Suite 3: Arbitrator Unit', 'Alert triggered -> ALERT', 'ALERT', alertArb.resolve({}))

  // At 3900ms: still ALERT
  Date.now = () => alertT0 + 3900
  assert(alertArb.resolve({}) === 'ALERT', 'Suite 3: Arbitrator Unit', 'Alert at 3900ms still ALERT', 'ALERT', alertArb.resolve({}))

  // At 4100ms: drops to IDLE
  Date.now = () => alertT0 + 4100
  assert(alertArb.resolve({}) === 'IDLE', 'Suite 3: Arbitrator Unit', 'Alert at 4100ms drops to IDLE', 'IDLE', alertArb.resolve({}))
} finally {
  Date.now = originalDateNow
}

// 3.2 RUNTIME WIRING AUDIT: Is VisualizerStateArbitrator used in HolographicCoreScene?
const scenePath = path.resolve(process.cwd(), 'src/components/dashboard/holographic-core/holographic-core-scene.tsx')
const sceneCode = fs.readFileSync(scenePath, 'utf8')

const arbitratorInScene = sceneCode.includes('VisualizerStateArbitrator')
assert(
  arbitratorInScene,
  'Suite 3: Runtime Wiring Forensics',
  'VisualizerStateArbitrator instantiated in HolographicCoreScene',
  true,
  arbitratorInScene,
  arbitratorInScene
    ? 'Arbitrator is connected to HolographicCoreScene.'
    : 'CRITICAL ARCHITECTURAL FLAW: VisualizerStateArbitrator is NEVER imported or instantiated in holographic-core-scene.tsx! The scene calls resolveActiveState directly with no dwell tracking, no hung tool timeout, and no alert decay!',
  !arbitratorInScene
)

// 3.3 GATEWAY CLIENT AUDIT: Tool Result premature THINKING dispatch
const gatewayPath = path.resolve(process.cwd(), 'src/lib/gateway-client.ts')
const gatewayCode = fs.readFileSync(gatewayPath, 'utf8')

const toolResultDispatchesThinkingImmediately = gatewayCode.includes("window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } }))")
assert(
  !toolResultDispatchesThinkingImmediately,
  'Suite 3: Runtime Wiring Forensics',
  'GatewayClient respects TOOL_DWELL_MS before dispatching THINKING',
  false,
  toolResultDispatchesThinkingImmediately,
  toolResultDispatchesThinkingImmediately
    ? "VULNERABILITY: In gateway-client.ts line 290, tool.result immediately dispatches jarvis-state: { state: 'THINKING' } with 0ms dwell, violating the 2000ms TOOL_DWELL_MS specification!"
    : 'GatewayClient respects dwell time before switching to THINKING.',
  toolResultDispatchesThinkingImmediately
)

// 3.4 DASHBOARD DWELL AUDIT: Conflicting 3000ms vs 2000ms timer
const dashboardPath = path.resolve(process.cwd(), 'src/pages/dashboard.tsx')
const dashboardCode = fs.readFileSync(dashboardPath, 'utf8')

const has3000msTimerInDashboard = dashboardCode.includes('setTimeout(() => setActiveTool(null), 3000)')
assert(
  !has3000msTimerInDashboard,
  'Suite 3: Runtime Wiring Forensics',
  'DashboardView uses TOOL_DWELL_MS (2000ms) not hardcoded 3000ms',
  false,
  has3000msTimerInDashboard,
  has3000msTimerInDashboard
    ? 'VULNERABILITY: In dashboard.tsx line 418, activeTool is held for hardcoded 3000ms (setTimeout 3000), conflicting with TOOL_DWELL_MS (2000ms) defined in state-machine.ts!'
    : 'DashboardView uses consistent dwell constant.',
  has3000msTimerInDashboard
)

// 3.5 PERMANENT STUCK STATE AUDIT: Does jarvis-state CustomEvent or hotkey return to IDLE?
const hasRealtimeBusTimer = /realtimeBusState\.current\s*=\s*null|clearTimeout|setTimeout.*realtimeBusState/i.test(sceneCode)
assert(
  hasRealtimeBusTimer,
  'Suite 3: Runtime Wiring Forensics',
  'HolographicCoreScene has timeout to return realtimeBusState to IDLE/null',
  true,
  hasRealtimeBusTimer,
  hasRealtimeBusTimer
    ? 'realtimeBusState has automatic expiration.'
    : 'CRITICAL BUG: HolographicCoreScene sets realtimeBusState.current on jarvis-state / keydown but NEVER clears or expires it! If an alert or tool event is dispatched via window CustomEvent or hotkey, the visualizer remains permanently stuck in that state indefinitely!',
  !hasRealtimeBusTimer
)


// ============================================================================
// SUITE 4: EXTREME INPUT HARDENING & CRASH RESILIENCE
// ============================================================================
console.log('>>> Running Suite 4: Extreme Input Hardening & Crash Resilience...')

// 4.1 unpackJarvisStateDetail Adversarial Inputs
const adversarialPayloads: Array<{ desc: string; input: any; expected: HolographicState | null }> = [
  { desc: 'null', input: null, expected: null },
  { desc: 'undefined', input: undefined, expected: null },
  { desc: 'empty string', input: '', expected: null },
  { desc: 'whitespace string', input: '   ', expected: null },
  { desc: 'numeric value', input: 9999, expected: null },
  { desc: 'boolean true', input: true, expected: null },
  { desc: 'boolean false', input: false, expected: null },
  { desc: 'empty object', input: {}, expected: null },
  { desc: 'empty array', input: [], expected: null },
  { desc: 'nested null payload', input: { payload: null }, expected: null },
  { desc: 'nested undefined state', input: { state: undefined }, expected: null },
  { desc: 'invalid string state', input: 'NON_EXISTENT_STATE_XYZ', expected: null },
  { desc: 'function input', input: () => 'ALERT', expected: null },
  { desc: 'Symbol input', input: Symbol('ALERT'), expected: null },
]

let payloadCrashes = 0
for (const tc of adversarialPayloads) {
  try {
    const res = unpackJarvisStateDetail(tc.input)
    if (res !== tc.expected) {
      assert(false, 'Suite 4: Payload Resilience', `Payload ${tc.desc}`, tc.expected, res)
    }
  } catch (err: any) {
    payloadCrashes++
    assert(false, 'Suite 4: Payload Resilience', `Payload ${tc.desc} threw exception`, 'no throw', err.message)
  }
}
assert(payloadCrashes === 0, 'Suite 4: Payload Resilience', 'Zero payload parser crashes', 0, payloadCrashes)

// 4.2 Circular Object Injection into unpackJarvisStateDetail
let circularCrash = false
try {
  const circular: any = { state: 'THINKING' }
  circular.detail = circular
  circular.payload = circular
  const circularRes = unpackJarvisStateDetail(circular)
  assert(circularRes === 'THINKING', 'Suite 4: Payload Resilience', 'Circular object safely extracts state', 'THINKING', circularRes)
} catch (err: any) {
  circularCrash = true
  assert(false, 'Suite 4: Payload Resilience', 'Circular object threw recursion error', 'no crash', err.message, undefined, true)
}

// 4.3 updateStateWeights Numerical Resilience
const weights = createDefaultStateWeights()
const extremeDeltas = [
  -1.0,           // negative delta (clock rollback)
  0.0,            // zero delta
  0.0000000001,   // sub-millisecond delta
  0.016666,       // nominal 60 FPS
  0.05,           // boundary clamp
  10.0,           // tab sleep 10s
  3600.0,         // tab sleep 1 hour
  NaN,            // corrupt clock
  Infinity,       // overflow
  -Infinity,      // underflow
]

let weightAnomalies = 0
for (const dt of extremeDeltas) {
  try {
    const { damp, dt: safeDt } = updateStateWeights(weights, 'SPEAKING', dt)
    if (isNaN(damp) || damp < 0 || damp > 1) {
      weightAnomalies++
    }
    if (isNaN(safeDt) || safeDt < 0 || safeDt > 0.05) {
      weightAnomalies++
    }
    for (const key of STATE_KEYS) {
      const val = weights[key]
      if (isNaN(val) || !isFinite(val) || val < -0.01 || val > 1.01) {
        weightAnomalies++
      }
    }
  } catch (err: any) {
    weightAnomalies++
  }
}
assert(weightAnomalies === 0, 'Suite 4: Numerical Resilience', 'updateStateWeights surviving extreme deltas', 0, weightAnomalies)

// 4.4 Cardiac Beat Calculation Extreme Timestamps
const extremeTimestamps = [-100.0, 0.0, 1.0, 1e5, 1e9, NaN, Infinity]
let beatAnomalies = 0
for (const t of extremeTimestamps) {
  try {
    const beat = calculateCardiacBeat(t)
    if (isNaN(t) && !isNaN(beat)) {
      // NaN in -> NaN out
    } else if (!isNaN(t) && isFinite(t)) {
      if (isNaN(beat) || !isFinite(beat) || beat < 0 || beat > 2.0) {
        beatAnomalies++
      }
    }
  } catch (err) {
    beatAnomalies++
  }
}
assert(beatAnomalies === 0, 'Suite 4: Numerical Resilience', 'calculateCardiacBeat bounded in [0, 2]', 0, beatAnomalies)


// ============================================================================
// SUITE 5: VOICE STATE SHADOWING & IPC DESYNCHRONIZATION
// ============================================================================
console.log('>>> Running Suite 5: Voice State Shadowing & IPC Desynchronization...')

{
  let mockRealtimeBusState: string | null = 'CODING' // Left over from hotkey or prior event
  jarvisRealtimeRef.voiceState = 'SPEAKING'
  jarvisRealtimeRef.isSpeaking = true

  const effectiveVoice = mockRealtimeBusState || jarvisRealtimeRef.voiceState
  const dashboardProps: SphereProps = { activeTool: undefined, isVideoOn: false }
  const resolved = resolveActiveState(dashboardProps, effectiveVoice)

  assert(
    resolved === 'SPEAKING',
    'Suite 5: Shadowing & Desynchronization',
    'realtimeBusState must not shadow jarvisRealtimeRef.voiceState during assistant speech',
    'SPEAKING',
    resolved,
    resolved === 'SPEAKING'
      ? 'Assistant speech correctly resolved.'
      : `VULNERABILITY: Stale realtimeBusState ('CODING') shadowed jarvisRealtimeRef.voiceState ('SPEAKING'), causing the visualizer to remain in ${resolved} while assistant was speaking!`,
    resolved !== 'SPEAKING'
  )
}

// ============================================================================
// SUMMARY & VERDICT GENERATION
// ============================================================================
console.log('\n========================================================================')
console.log('ADVERSARIAL STRESS TEST SUMMARY')
console.log('========================================================================')

const totalTests = testResults.length
const passedTests = testResults.filter((r) => r.passed).length
const failedTests = testResults.filter((r) => !r.passed).length
const vulnerabilities = testResults.filter((r) => r.isVulnerability && !r.passed)

console.log(`Total Probes Executed: ${totalTests}`)
console.log(`Passed: ${passedTests}`)
console.log(`Failed: ${failedTests}`)
console.log(`Confirmed Vulnerabilities: ${vulnerabilities.length}`)

for (const v of vulnerabilities) {
  console.log(`\n[CRITICAL FAILURE] ${v.suite} -> ${v.name}`)
  console.log(`  Expected: ${v.expected}`)
  console.log(`  Actual:   ${v.actual}`)
  if (v.details) console.log(`  Details:  ${v.details}`)
}

console.log('\n========================================================================')
const verdict = vulnerabilities.length === 0 ? 'APPROVE' : 'REJECT'
console.log(`FINAL EMPIRICAL VERDICT: ${verdict}`)
console.log('========================================================================')

process.exit(0)
