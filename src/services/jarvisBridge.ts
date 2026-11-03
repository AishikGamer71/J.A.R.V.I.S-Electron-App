/**
 * src/services/jarvisBridge.ts
 * High-speed Typed WebSocket & IPC Bridge to J.A.R.V.I.S Python Sidecar (ws://127.0.0.1:8765/ws).
 * Dispatches live hardware telemetry, 60 FPS audio visualizer amplitude, terminal logs,
 * and autonomous agent events to the restored UI without altering visual components.
 */

export interface TelemetryHardware {
  cpu_percent: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  battery_percent: number;
  battery_charging: boolean;
  ac_plugged_in: boolean;
  charger_state_changed?: boolean;
}

export interface TelemetryNetwork {
  is_online: boolean;
  latency_ms: number;
  rate: number;
  tx: number;
  rx: number;
}

export interface TelemetryEnvelope {
  type: 'telemetry' | 'system.metrics';
  hardware: TelemetryHardware;
  network: TelemetryNetwork;
  timestamp: number;
}

export interface VoiceStateEnvelope {
  type: 'voice_state' | 'agent.state';
  state: 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING';
  amplitude: number;
  is_speaking: boolean;
}

export interface TerminalLogEnvelope {
  type: 'terminal_log';
  level: 'info' | 'warn' | 'error' | 'critical' | 'success';
  message: string;
  timestamp: number;
}

export interface AgentResponseEnvelope {
  type: 'agent_response' | 'agent.complete';
  session_id: string;
  content: string;
  model?: string;
  tool_executed?: string | null;
  timestamp: number;
}

export type JarvisBridgeEvent =
  | TelemetryEnvelope
  | VoiceStateEnvelope
  | TerminalLogEnvelope
  | AgentResponseEnvelope
  | { type: string; [key: string]: any };

type Listener<T> = (data: T) => void;

/**
 * Zero-re-render mutable reference store for high-frequency 60 FPS audio
 * amplitude and voice state updates. Consumed directly in Three.js useFrame
 * without triggering React re-renders.
 */
export const jarvisRealtimeRef = {
  audioLevel: 0,
  voiceState: 'IDLE' as string,
  isSpeaking: false,
  isListening: false,
};

class JarvisBridge {
  private ws: WebSocket | null = null;
  private wsUrl: string = 'ws://127.0.0.1:8765/ws';
  private reconnectTimer: any = null;
  private isExplicitlyClosed: boolean = false;
  private reconnectAttempts: number = 0;

  public isConnected: boolean = false;

  private telemetryListeners: Set<Listener<TelemetryEnvelope>> = new Set();
  private voiceStateListeners: Set<Listener<VoiceStateEnvelope>> = new Set();
  private terminalLogListeners: Set<Listener<TerminalLogEnvelope>> = new Set();
  private agentResponseListeners: Set<Listener<AgentResponseEnvelope>> = new Set();

  constructor() {
    this.connect();
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.reconnectAttempts = 0;
        console.log('[JarvisBridge] Connected to live backend at', this.wsUrl);
        window.dispatchEvent(new CustomEvent('jarvis-bridge-status', { detail: 'online' }));
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const data: JarvisBridgeEvent = JSON.parse(event.data);
          this.handleIncoming(data);
        } catch (e) {
          console.warn('[JarvisBridge] Failed to parse message:', e);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        window.dispatchEvent(new CustomEvent('jarvis-bridge-status', { detail: 'offline' }));
        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (err) => {
        console.warn('[JarvisBridge] WebSocket notice:', err);
      };
    } catch (e) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectAttempts++;
    const backoff = Math.min(1000 * Math.pow(1.3, this.reconnectAttempts), 5000);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, backoff);
  }

  private handleIncoming(data: JarvisBridgeEvent): void {
    const type = data.type;

    // 1. Telemetry
    if (type === 'telemetry' || type === 'system.metrics') {
      const tel = data as TelemetryEnvelope;
      this.telemetryListeners.forEach((l) => l(tel));
      window.dispatchEvent(new CustomEvent('jarvis-telemetry', { detail: tel }));
    }

    // 2. Voice State & 60 FPS Audio Amplitude - Directly update mutable ref store
    else if (type === 'voice_state' || type === 'agent.state') {
      const vs = data as VoiceStateEnvelope;
      const amp = typeof vs.amplitude === 'number' ? vs.amplitude : 0;
      const state = (vs.state || 'IDLE').toUpperCase();

      jarvisRealtimeRef.audioLevel = amp;
      jarvisRealtimeRef.voiceState = state;
      jarvisRealtimeRef.isSpeaking = vs.is_speaking ?? (state === 'SPEAKING');
      jarvisRealtimeRef.isListening = state === 'LISTENING';

      this.voiceStateListeners.forEach((l) => l(vs));
      window.dispatchEvent(new CustomEvent('jarvis-voice-state', { detail: vs }));
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: state }));
    }

    // 3. Live Terminal Logs & Agent Step Stream
    else if (type === 'terminal_log') {
      const log = data as TerminalLogEnvelope;
      this.terminalLogListeners.forEach((l) => l(log));
      window.dispatchEvent(new CustomEvent('jarvis-terminal-log', { detail: log }));
    }

    // 4. Agent Response
    else if (type === 'agent_response' || type === 'agent.complete') {
      const res = data as AgentResponseEnvelope;
      this.agentResponseListeners.forEach((l) => l(res));
      window.dispatchEvent(new CustomEvent('jarvis-agent-response', { detail: res }));
    }
  }

  // Outgoing Emitter Methods
  public sendMessage(content: string, sessionId: string = 'default', model?: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'user.message',
        content,
        session_id: sessionId,
        model
      }));
    }
  }

  public stopAudio(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'audio.control', action: 'cancel_speech' }));
    }
  }

  public resetAbort(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'reset_abort' }));
    }
  }

  // Listener Registration
  public onTelemetry(listener: Listener<TelemetryEnvelope>): () => void {
    this.telemetryListeners.add(listener);
    return () => this.telemetryListeners.delete(listener);
  }

  public onVoiceState(listener: Listener<VoiceStateEnvelope>): () => void {
    this.voiceStateListeners.add(listener);
    return () => this.voiceStateListeners.delete(listener);
  }

  public onTerminalLog(listener: Listener<TerminalLogEnvelope>): () => void {
    this.terminalLogListeners.add(listener);
    return () => this.terminalLogListeners.delete(listener);
  }

  public onAgentResponse(listener: Listener<AgentResponseEnvelope>): () => void {
    this.agentResponseListeners.add(listener);
    return () => this.agentResponseListeners.delete(listener);
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const jarvisBridge = new JarvisBridge();
