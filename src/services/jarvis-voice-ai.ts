import { gatewayClient } from '@/lib/gateway-client'

export class GeminiLiveService {
  public isConnected: boolean = false
  public isMicMuted: boolean = false
  public analyser: AnalyserNode | null = null
  public audioContext: AudioContext | null = null
  public apiKey: string = 'hermes-auth-handled-internally'
  
  private mediaStream: MediaStream | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private voiceWs: WebSocket | null = null

  constructor() {}

  async initAudio(): Promise<void> {
    try {
      if (!this.audioContext) {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
        if (AudioCtx) {
          this.audioContext = new AudioCtx()
        }
      }

      if (this.audioContext && this.audioContext.state === 'suspended') {
        await this.audioContext.resume()
      }

      if (!this.analyser && this.audioContext) {
        this.analyser = this.audioContext.createAnalyser()
        this.analyser.fftSize = 256
        this.analyser.smoothingTimeConstant = 0.8
      }

      if (!this.isMicMuted && !this.mediaStream && navigator.mediaDevices?.getUserMedia) {
        try {
          this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
          if (this.audioContext && this.analyser) {
            this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream)
            this.sourceNode.connect(this.analyser)
          }
        } catch (micErr) {
          console.warn('[jarvis-voice] Microphone permission or device unavailable:', micErr)
        }
      }
    } catch (e) {
      console.warn('[jarvis-voice] Failed to initialize Web Audio:', e)
    }
  }

  setMute(muted: boolean) {
    this.isMicMuted = muted
    if (this.mediaStream) {
      this.mediaStream.getAudioTracks().forEach((track) => {
        track.enabled = !muted
      })
    }
    if (!muted && !this.mediaStream) {
      this.initAudio().catch(() => {})
    }
  }

  async connect(): Promise<void> {
    try {
      gatewayClient.init()
      this.isConnected = true
      
      // Initialize real Web Audio analyser for particle sphere HUD
      await this.initAudio()

      // Connect to voice service for wake word detection if available
      this.connectVoiceStream()
    } catch (e) {
      this.isConnected = false
      console.error('[jarvis-voice] Failed to connect:', e)
      throw new Error('Failed to connect to J.A.R.V.I.S backend')
    }
  }

  private connectVoiceStream() {
    try {
      if (this.voiceWs && (this.voiceWs.readyState === WebSocket.OPEN || this.voiceWs.readyState === WebSocket.CONNECTING)) {
        return
      }

      this.voiceWs = new WebSocket('ws://127.0.0.1:8766/v1/voice/stream')

      this.voiceWs.onopen = () => {
        console.log('[jarvis-voice] Voice microservice WebSocket connected')
      }

      this.voiceWs.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.event === 'wake_word_detected') {
            console.log('[jarvis-voice] Wake word detected:', data.wake_word)
            window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'SPEAKING' }))
            // Send ambient notification / start listening prompt
            this.sendTextCommand('JARVIS, I am listening.')
          } else if (data.event === 'transcription_complete' && data.text) {
            this.sendTextCommand(data.text)
          }
        } catch {
          // ignore non-json frames
        }
      }

      this.voiceWs.onerror = () => {
        // Voice service may not be running standalone, fail gracefully
      }

      this.voiceWs.onclose = () => {
        this.voiceWs = null
      }
    } catch {
      // ignore
    }
  }

  private currentFile: string | null = null
  private lastVideoFrame: string | null = null

  sendVideoFrame(base64Image: string): void {
    this.lastVideoFrame = base64Image
  }

  sendTextCommand(text: string): void {
    if (text && text.trim()) {
      gatewayClient.sendChat(
        'jarvis-main-chat',
        text.trim(),
        () => {},
        () => {},
        (err) => console.error('[jarvis-voice] Error:', err)
      )
    }
  }

  setFile(filePath: string): void {
    this.currentFile = filePath
  }

  disconnect(): void {
    this.isConnected = false

    if (this.voiceWs) {
      this.voiceWs.close()
      this.voiceWs = null
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop())
      this.mediaStream = null
    }

    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect()
      } catch {
        // ignore
      }
      this.sourceNode = null
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.close()
      } catch {
        // ignore
      }
      this.audioContext = null
    }
    this.analyser = null
  }
}

export const jarvisService = new GeminiLiveService()
