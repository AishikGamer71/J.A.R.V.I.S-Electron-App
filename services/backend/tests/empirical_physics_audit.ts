/**
 * Empirical Physics & UI Mathematical Stability Audit
 * 
 * Verifies exact production expressions for:
 * 1. Arc Reactor delta-time clamping: Math.max(0, Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05))
 * 2. Sphere delta-time clamping: Math.max(0, Math.min(0.05, delta))
 * 3. Exponential damping under dt boundaries: dt in [-1000, 0, 0.016, 0.033, 0.05, 10.0, 1000.0]
 * 4. Multi-frame simulation under clock jumps and audio spikes
 */

function arcReactorDt(timestamp: number, lastFrame: number): number {
  return Math.max(0, Math.min((timestamp - lastFrame) / 1000, 0.05))
}

function sphereDt(delta: number): number {
  return Math.max(0, Math.min(0.05, delta))
}

interface CaseResult {
  name: string
  input: any
  dt: number
  smoothing10: number
  damp6_2: number
  audioDamp14: number
  stable: boolean
  comment: string
}

const cases: CaseResult[] = []

const dtTestInputs = [
  { name: 'Negative clock rollback (-60s)', ts: 0, last: 60000, delta: -60.0 },
  { name: 'Negative minor skew (-10ms)', ts: 990, last: 1000, delta: -0.01 },
  { name: 'Negative sub-millisecond jitter (-0.0001s)', ts: 999.9, last: 1000, delta: -0.0001 },
  { name: 'Zero dt (immediate re-render)', ts: 1000, last: 1000, delta: 0 },
  { name: 'Sub-millisecond positive jitter (0.0001s)', ts: 1000.1, last: 1000, delta: 0.0001 },
  { name: '240 FPS frame (0.00416s)', ts: 1004.167, last: 1000, delta: 0.004167 },
  { name: '144 FPS frame (0.00694s)', ts: 1006.944, last: 1000, delta: 0.006944 },
  { name: '60 FPS frame (0.01666s)', ts: 1016.667, last: 1000, delta: 0.016667 },
  { name: '30 FPS frame (0.03333s)', ts: 1033.333, last: 1000, delta: 0.033333 },
  { name: '20 FPS frame (0.05000s clamp boundary)', ts: 1050, last: 1000, delta: 0.05 },
  { name: '10 FPS slow frame (0.100s)', ts: 1100, last: 1000, delta: 0.10 },
  { name: '1 FPS freeze recovery (1.0s)', ts: 2000, last: 1000, delta: 1.0 },
  { name: 'Tab background sleep recovery (30s)', ts: 31000, last: 1000, delta: 30.0 },
  { name: 'Extreme positive sleep recovery (3600s)', ts: 3601000, last: 1000, delta: 3600.0 },
]

console.log('=== EMPIRICAL PHYSICS AUDIT: EXACT PRODUCTION FORMULAS ===\n')

let allPass = true

for (const c of dtTestInputs) {
  const dtR = arcReactorDt(c.ts, c.last)
  const dtS = sphereDt(c.delta)

  // Verify parity between reactor dt and sphere dt
  const parity = Math.abs(dtR - dtS) < 1e-4

  // Verify bounds: 0 <= dt <= 0.05
  const inBounds = dtR >= 0 && dtR <= 0.05 && dtS >= 0 && dtS <= 0.05

  const s10 = 1 - Math.exp(-10 * dtR)
  const d62 = 1 - Math.exp(-6.2 * dtS)
  const ad14 = 1 - Math.exp(-14 * dtS)

  // All smoothing factors must be strictly within [0, 1) and finite
  const sFinite = Number.isFinite(s10) && Number.isFinite(d62) && Number.isFinite(ad14)
  const sRange = s10 >= 0 && s10 < 1 && d62 >= 0 && d62 < 1 && ad14 >= 0 && ad14 < 1

  const passed = parity && inBounds && sFinite && sRange
  if (!passed) allPass = false

  cases.push({
    name: c.name,
    input: { ts: c.ts, last: c.last, delta: c.delta },
    dt: dtR,
    smoothing10: s10,
    damp6_2: d62,
    audioDamp14: ad14,
    stable: passed,
    comment: `dt=${dtR.toFixed(4)}, s10=${s10.toFixed(4)}, d6.2=${d62.toFixed(4)}, ad14=${ad14.toFixed(4)}`
  })

  console.log(`[${passed ? 'PASS' : 'FAIL'}] ${c.name}: ${cases[cases.length - 1].comment}`)
}

console.log('\n--- Multi-Frame Dynamic Simulation Under Adversarial Conditions ---')

// Simulation: 1000 frames with random jitter, clock rollbacks, and massive audio spikes
let smoothedAudio = 0
let currentGlow = 5.2
let timestamp = 0
let framesPassed = true

for (let frame = 0; frame < 1000; frame++) {
  let deltaMs: number
  if (frame === 100) {
    deltaMs = -5000 // Clock rollback 5s
  } else if (frame === 200) {
    deltaMs = 30000 // Tab background sleep 30s
  } else if (frame === 300) {
    deltaMs = 0 // Immediate 0ms re-render
  } else {
    deltaMs = 16.66 + (Math.sin(frame) * 5) // Normal 60fps jitter (11ms - 21ms)
  }

  const prevTs = timestamp
  timestamp += deltaMs
  const dt = arcReactorDt(timestamp, prevTs)

  // Audio level spike at frame 500
  let audioInput = 0.2
  if (frame >= 500 && frame < 510) {
    audioInput = 50.0 // 50x audio overload
  } else if (frame >= 600 && frame < 610) {
    audioInput = -10.0 // Negative audio spike
  }

  // Clamping guard from arc-reactor.tsx:
  if (audioInput > 0) {
    const rawAudioRms = Math.min(1.0, audioInput) // If clamped or raw
    const smoothing = 1 - Math.exp(-10 * dt)
    smoothedAudio += (rawAudioRms - smoothedAudio) * smoothing
  }

  const targetGlow = 8.0 * (0.65 + smoothedAudio * 0.35)
  currentGlow += (targetGlow - currentGlow) * (1 - Math.exp(-6 * dt))

  if (!Number.isFinite(smoothedAudio) || !Number.isFinite(currentGlow) || smoothedAudio < 0 || smoothedAudio > 2.0) {
    console.error(`Frame ${frame} unstable: smoothedAudio=${smoothedAudio}, currentGlow=${currentGlow}, dt=${dt}`)
    framesPassed = false
    break
  }
}

console.log(`[${framesPassed ? 'PASS' : 'FAIL'}] 1,000-frame adversarial simulation (with rollbacks, sleeps, and spikes): stable=${framesPassed}`)
if (!framesPassed) allPass = false

console.log(`\nOverall Physics Stability: ${allPass ? 'VERIFIED STABLE' : 'UNSTABLE'}`)
process.exit(allPass ? 0 : 1)
