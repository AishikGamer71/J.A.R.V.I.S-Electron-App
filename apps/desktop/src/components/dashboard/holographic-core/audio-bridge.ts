import { jarvisService } from '@/services/jarvis-voice-ai'
import { jarvisRealtimeRef } from '@/services/jarvisBridge'
import type { AudioFrequencyBands, HolographicState } from './types'

/**
 * 3-Band FFT Audio Reactivity Bridge.
 *
 * Samples AnalyserNode frequency bins, WebSocket audioLevel, and prop audio levels.
 * Provides autonomous speech cadence simulation fallback when audio amplitude is quiescent.
 * Runs zero-re-render 60 FPS updates smoothed with continuous exponential decay (k = 14.0 s^-1).
 */
export class AudioReactivityBridge {
  private bands: AudioFrequencyBands = { bass: 0, mid: 0, treble: 0 }
  private dataArray = new Uint8Array(128)

  /**
   * Resets audio frequency bands to zero.
   */
  public reset(): void {
    this.bands.bass = 0
    this.bands.mid = 0
    this.bands.treble = 0
  }

  /**
   * Samples current audio inputs and updates smoothed frequency bands.
   */
  public update(
    dt: number,
    elapsedTime: number,
    activeState: HolographicState,
    propAudioLevel?: number
  ): AudioFrequencyBands {
    const safeDt = Number.isFinite(dt) ? Math.max(0, dt) : 0
    const audioDamp = 1 - Math.exp(-14 * safeDt)

    let rawBass = 0
    let rawMid = 0
    let rawTreble = 0

    // 1. Direct Web Audio API AnalyserNode sampling (if active)
    if (jarvisService?.analyser) {
      try {
        jarvisService.analyser.getByteFrequencyData(this.dataArray)
        // Bass: Bins 0-15 (0 Hz to ~2.8 kHz)
        for (let i = 0; i < 16; i++) rawBass += this.dataArray[i]
        // Mid: Bins 16-55 (~2.8 kHz to ~9.8 kHz)
        for (let i = 16; i < 56; i++) rawMid += this.dataArray[i]
        // Treble: Bins 56-111 (~9.8 kHz to ~19.6 kHz)
        for (let i = 56; i < 112; i++) rawTreble += this.dataArray[i]

        rawBass /= 16 * 255
        rawMid /= 40 * 255
        rawTreble /= 56 * 255
      } catch {
        // Safe fallback on audio context shutdown or detached node
      }
    }

    // 2. Mutable Realtime WebSocket & Prop Audio Level Sampling
    const refLevel = Number.isFinite(jarvisRealtimeRef.audioLevel) ? (jarvisRealtimeRef.audioLevel as number) : 0
    const propLevel = Number.isFinite(propAudioLevel) ? (propAudioLevel as number) : 0
    const rawExternal = Math.max(refLevel, propLevel)
    const externalLevel = Number.isFinite(rawExternal) ? Math.min(1.0, Math.max(0, rawExternal)) : 0

    if (externalLevel > 0) {
      rawBass = Math.max(rawBass, externalLevel * 0.95)
      rawMid = Math.max(rawMid, externalLevel * 0.85)
      rawTreble = Math.max(rawTreble, externalLevel * 0.75)
    }

    // 3. Fallbacks and State Modulation
    const totalRaw = (rawBass + rawMid + rawTreble) / 3

    if (activeState === 'SPEAKING' && totalRaw < 0.03) {
      // Autonomous harmonic speech cadence simulation when speaking without mic feed
      const syllable = Math.pow(
        Math.max(0, Math.sin(elapsedTime * 7.2) * 0.65 + Math.sin(elapsedTime * 11.7) * 0.35),
        1.4
      )
      const cadence = 0.45 + 0.55 * Math.max(0, Math.sin(elapsedTime * 2.1 + 0.5))
      rawBass = 0.22 + syllable * cadence * 0.65
      rawMid = 0.18 + Math.abs(Math.sin(elapsedTime * 9.5)) * cadence * 0.58
      rawTreble = 0.14 + Math.abs(Math.cos(elapsedTime * 14.3)) * cadence * 0.52
    } else if (activeState === 'LISTENING') {
      if (totalRaw < 0.02) {
        // Attentive synthetic mic pulse when testing LISTENING without microphone feed
        const pulse = Math.max(0, Math.sin(elapsedTime * 3.8) * 0.5 + Math.sin(elapsedTime * 6.3) * 0.3)
        rawBass = 0.1 + pulse * 0.32
        rawMid = 0.08 + pulse * 0.28
        rawTreble = 0.05 + pulse * 0.2
      } else {
        // Boost live mic sensitivity for responsive listening HUD
        rawBass = Math.min(1, rawBass * 2.2)
        rawMid = Math.min(1, rawMid * 2.2)
        rawTreble = Math.min(1, rawTreble * 2.0)
      }
    }

    // 4. Exponential Smoothing (continuous time decay)
    this.bands.bass = Math.min(1.0, Math.max(0, this.bands.bass + (rawBass - this.bands.bass) * audioDamp))
    this.bands.mid = Math.min(1.0, Math.max(0, this.bands.mid + (rawMid - this.bands.mid) * audioDamp))
    this.bands.treble = Math.min(1.0, Math.max(0, this.bands.treble + (rawTreble - this.bands.treble) * audioDamp))

    return this.bands
  }

  /**
   * Returns current smoothed audio frequency band values.
   */
  public getBands(): AudioFrequencyBands {
    return this.bands
  }
}
