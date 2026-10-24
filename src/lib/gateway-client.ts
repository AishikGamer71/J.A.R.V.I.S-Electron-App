/**
 * J.A.R.V.I.S Gateway Client (WebSocket & HTTP Control Plane)
 */

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  tier?: 'tier1_local' | 'tier2_balanced' | 'tier3_cloud';
  model?: string;
  created_at: number;
}

export interface HardwareTelemetry {
  cpu_percent: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  gpu_name?: string;
  vram_used_mb?: number;
  vram_total_mb?: number;
  system_tier: 'low' | 'mid' | 'high';
}

export interface NetworkStatus {
  is_online: boolean;
  latency_ms?: number;
}

export interface ConfirmationRequest {
  confirmationId: string;
  toolName: string;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  arguments: Record<string, any>;
  timeoutSeconds: number;
  timestamp: number;
}

export interface AuditLogEntry {
  id: string;
  tool: string;
  args_hash: string;
  args_summary: Record<string, any>;
  risk_level: string;
  outcome: string;
  timestamp: number;
  details: Record<string, any>;
}

export interface PermissionEntry {
  tool: string;
  scope: string;
  granted: boolean;
  granted_at: number;
}

export interface ToolDefinition {
  name: string;
  description: string;
  risk_level: string;
  parameters_schema: Record<string, any>;
}

type TelemetryListener = (data: { hardware: HardwareTelemetry; network: NetworkStatus }) => void;
type ChatRouteListener = (data: { sessionId: string; tier: string; model: string; provider: string; isFallback: boolean; reason: string }) => void;
type ConfirmationListener = (req: ConfirmationRequest) => void;
type StateListener = (state: string) => void;
type ToolListener = (data: { phase: 'start' | 'result'; tool: string; arguments?: any; result?: any }) => void;

class JarvisGatewayClient {
  private ws: WebSocket | null = null;
  private baseUrl: string = 'http://127.0.0.1:8765';
  private wsUrl: string = 'ws://127.0.0.1:8765/ws';
  private reconnectTimer: any = null;
  private isExplicitlyClosed: boolean = false;
  private currentAudio: HTMLAudioElement | null = null;
  
  public isConnected: boolean = false;
  private telemetryListeners: Set<TelemetryListener> = new Set();
  private routeListeners: Set<ChatRouteListener> = new Set();
  private confirmationListeners: Set<ConfirmationListener> = new Set();
  private stateListeners: Set<StateListener> = new Set();
  private toolListeners: Set<ToolListener> = new Set();
  private activeStreams: Map<string, { onDelta: (d: string) => void; onDone: (m: ChatMessage) => void; onError: (e: any) => void }> = new Map();

  constructor() {
    this.init();
  }

  public init() {
    this.isExplicitlyClosed = false;
    this.connectWs();
  }

  private connectWs() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        console.log('[GatewayClient] Connected to JARVIS Core Control Plane');
        this.pollTelemetry();
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleMessage(msg);
        } catch (e) {
          console.error('[GatewayClient] Error parsing message:', e);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (err) => {
        console.warn('[GatewayClient] WebSocket connection error:', err);
      };
    } catch (e) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connectWs();
    }, 2500);
  }

  private handleMessage(msg: any) {
    if (msg.type === 'telemetry:update') {
      this.telemetryListeners.forEach((listener) =>
        listener({ hardware: msg.hardware, network: msg.network })
      );
    } else if (msg.type === 'confirmation_request') {
      this.confirmationListeners.forEach((listener) =>
        listener({
          confirmationId: msg.confirmationId,
          toolName: msg.toolName,
          riskLevel: msg.riskLevel,
          arguments: msg.arguments,
          timeoutSeconds: msg.timeoutSeconds,
          timestamp: msg.timestamp
        })
      );
    } else if (msg.type === 'chat:routed') {
      this.routeListeners.forEach((listener) => listener(msg));
    } else if (msg.type === 'agent_state') {
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: (msg.state || '').toUpperCase() }));
      this.stateListeners.forEach((listener) => listener(msg.state));
    } else if (msg.type === 'agent_stream_chunk') {
      const stream = this.activeStreams.get(msg.sessionId);
      if (stream) {
        stream.onDelta(msg.delta);
      }
    } else if (msg.type === 'agent_message_complete') {
      const stream = this.activeStreams.get(msg.sessionId);
      if (stream) {
        stream.onDone(msg.message);
        this.activeStreams.delete(msg.sessionId);
      }
    } else if (msg.type === 'tool_call_start') {
      this.toolListeners.forEach((listener) => listener({ phase: 'start', tool: msg.tool, arguments: msg.arguments }));
      window.dispatchEvent(new CustomEvent('jarvis-tool-call', { detail: { phase: 'start', tool: msg.tool, arguments: msg.arguments } }));
    } else if (msg.type === 'tool_call_result') {
      this.toolListeners.forEach((listener) => listener({ phase: 'result', tool: msg.tool, result: msg.result }));
      window.dispatchEvent(new CustomEvent('jarvis-tool-call', { detail: { phase: 'result', tool: msg.tool, result: msg.result } }));
      if (msg.result && typeof msg.result === 'object' && msg.result.widget) {
        window.dispatchEvent(new CustomEvent(`show-${msg.result.widget}`, { detail: msg.result.data || msg.result }));
      }
    } else if (msg.type === 'widget_dispatch') {
      if (msg.widget === 'weather') {
        window.dispatchEvent(new CustomEvent('show-weather', { detail: msg.data }));
      } else if (msg.widget === 'stock') {
        window.dispatchEvent(new CustomEvent('show-stock', { detail: msg.data }));
      } else if (msg.widget === 'image') {
        window.dispatchEvent(new CustomEvent('show-image', { detail: msg.data }));
      } else if (msg.widget === 'emails') {
        window.dispatchEvent(new CustomEvent('show-emails', { detail: msg.data }));
      }
    } else if (msg.type === 'tts_playback') {
      window.dispatchEvent(new CustomEvent('jarvis-tts', { detail: msg }));
      this.playTtsAudio(msg.audioBase64, msg.mimeType);
    } else if (msg.type === 'chat:delta') {
      const stream = this.activeStreams.get(msg.sessionId);
      if (stream) {
        stream.onDelta(msg.delta);
      }
    } else if (msg.type === 'chat:done') {
      const stream = this.activeStreams.get(msg.sessionId);
      if (stream) {
        stream.onDone(msg.message);
        this.activeStreams.delete(msg.sessionId);
      }
    } else if (msg.type === 'chat:error') {
      const stream = this.activeStreams.get(msg.sessionId);
      if (stream) {
        stream.onError(msg.error);
        this.activeStreams.delete(msg.sessionId);
      }
    }
  }

  public pollTelemetry() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'telemetry:poll' }));
    }
  }

  public onTelemetry(listener: TelemetryListener) {
    this.telemetryListeners.add(listener);
    return () => this.telemetryListeners.delete(listener);
  }

  public onChatRouted(listener: ChatRouteListener) {
    this.routeListeners.add(listener);
    return () => this.routeListeners.delete(listener);
  }

  public onAgentState(listener: StateListener) {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }

  public onToolCall(listener: ToolListener) {
    this.toolListeners.add(listener);
    return () => this.toolListeners.delete(listener);
  }

  public cancelSpeech() {
    if (this.currentAudio) {
      try {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
      } catch {}
      this.currentAudio = null;
    }
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'cancel_speech' }));
    }
    window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'IDLE' }));
  }

  public playTtsAudio(audioBase64: string, mimeType: string = 'audio/mp3') {
    try {
      if (this.currentAudio) {
        this.currentAudio.pause();
      }
      const audioUrl = `data:${mimeType};base64,${audioBase64}`;
      const audio = new Audio(audioUrl);
      this.currentAudio = audio;
      
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'SPEAKING' }));
      
      audio.onended = () => {
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'IDLE' }));
        this.currentAudio = null;
      };
      audio.onerror = () => {
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'IDLE' }));
        this.currentAudio = null;
      };
      
      audio.play().catch(() => {
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'IDLE' }));
      });
    } catch (e) {
      console.warn('[GatewayClient] Error playing TTS audio:', e);
    }
  }

  public onConfirmationRequest(listener: ConfirmationListener) {
    this.confirmationListeners.add(listener);
    return () => this.confirmationListeners.delete(listener);
  }

  public sendConfirmationResponse(confirmationId: string, approved: boolean, reason: string = '') {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: 'confirmation_response',
          confirmationId,
          approved,
          reason
        })
      );
    }
  }

  public sendChat(
    sessionId: string,
    content: string,
    onDelta: (delta: string) => void,
    onDone: (message: ChatMessage) => void,
    onError: (err: any) => void
  ) {
    this.activeStreams.set(sessionId, { onDelta, onDone, onError });
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: 'chat:send',
          sessionId,
          content
        })
      );
    } else {
      this.sendChatHttp(sessionId, content, onDelta, onDone, onError);
    }
  }

  private async sendChatHttp(
    sessionId: string,
    content: string,
    onDelta: (delta: string) => void,
    onDone: (message: ChatMessage) => void,
    onError: (err: any) => void
  ) {
    try {
      const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, content, stream: true })
      });

      if (!response.body) throw new Error('No response body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let lastModel = '';
      let lastTier: any = undefined;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        const lines = text.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (!dataStr) continue;
            try {
              const data = JSON.parse(dataStr);
              if (data.delta) {
                fullContent += data.delta;
                lastModel = data.model;
                lastTier = data.tier;
                onDelta(data.delta);
              }
              if (data.done) {
                onDone({
                  id: String(Date.now()),
                  session_id: sessionId,
                  role: 'assistant',
                  content: fullContent,
                  tier: lastTier,
                  model: lastModel,
                  created_at: Date.now() / 1000
                });
              }
            } catch {}
          }
        }
      }
    } catch (e) {
      onError(e);
    }
  }

  public async getHealth(): Promise<{ status: string; service: string; model_status: string; subsystems: any; uptime_seconds: number } | null> {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  public async getSessions(): Promise<any[]> {
    try {
      const res = await fetch(`${this.baseUrl}/sessions`);
      return await res.json();
    } catch {
      return [];
    }
  }

  public async getMessages(sessionId: string, limit: number = 100): Promise<ChatMessage[]> {
    try {
      const res = await fetch(`${this.baseUrl}/sessions/${sessionId}/messages?limit=${limit}`);
      return await res.json();
    } catch {
      return [];
    }
  }

  public async deleteSession(sessionId: string): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/sessions/${sessionId}`, { method: 'DELETE' });
      return res.ok;
    } catch {
      return false;
    }
  }

  public async searchMessages(query: string): Promise<ChatMessage[]> {
    try {
      const res = await fetch(`${this.baseUrl}/search?q=${encodeURIComponent(query)}`);
      return await res.json();
    } catch {
      return [];
    }
  }

  public async getAuditLogs(limit: number = 50, offset: number = 0, tool?: string): Promise<AuditLogEntry[]> {
    try {
      const url = `${this.baseUrl}/v1/audit?limit=${limit}&offset=${offset}${tool ? `&tool=${encodeURIComponent(tool)}` : ''}`;
      const res = await fetch(url);
      return await res.json();
    } catch {
      return [];
    }
  }

  public async getPermissions(): Promise<PermissionEntry[]> {
    try {
      const res = await fetch(`${this.baseUrl}/v1/permissions`);
      return await res.json();
    } catch {
      return [];
    }
  }

  public async grantPermission(tool: string, scope: string = '*'): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/v1/permissions/grant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool, scope })
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  public async revokePermission(tool: string, scope: string = '*'): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/v1/permissions/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool, scope })
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  public async getTools(): Promise<ToolDefinition[]> {
    try {
      const res = await fetch(`${this.baseUrl}/v1/tools`);
      return await res.json();
    } catch {
      return [];
    }
  }

  public async invokeTool(name: string, args: Record<string, any> = {}, scope: string = '*'): Promise<any> {
    try {
      const res = await fetch(`${this.baseUrl}/v1/tools/invoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, arguments: args, scope })
      });
      return await res.json();
    } catch (e: any) {
      return { success: false, error: e.message || String(e) };
    }
  }

  // --- Multi-Agent & Inbox System (Hermes Pattern) ---
  public async getAgents(): Promise<AgentInfo[]> {
    try {
      const res = await fetch(`${this.baseUrl}/v1/agents`);
      return await res.json();
    } catch {
      return [];
    }
  }

  public async getInboxTasks(agentName?: string, limit: number = 50): Promise<InboxTask[]> {
    try {
      const url = new URL(`${this.baseUrl}/v1/inbox`);
      url.searchParams.set('limit', String(limit));
      if (agentName) url.searchParams.set('agent_name', agentName);
      const res = await fetch(url.toString());
      return await res.json();
    } catch {
      return [];
    }
  }

  public async executeAgentGoal(task: string, context: Record<string, any> = {}): Promise<AgentExecutionResult> {
    try {
      const res = await fetch(`${this.baseUrl}/v1/agents/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, context })
      });
      return await res.json();
    } catch (e: any) {
      return {
        agent_name: 'planning_agent',
        success: false,
        summary: `Goal execution failed: ${e.message || String(e)}`,
        error: e.message || String(e)
      };
    }
  }
}

export interface AgentInfo {
  name: string;
  description: string;
  system_prompt: string;
  allowed_tools: string[];
}

export interface InboxTask {
  task_id: string;
  parent_task_id: string | null;
  agent_name: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  input_payload: Record<string, any>;
  output_payload: Record<string, any>;
  artifacts: Array<Record<string, any>>;
  created_at: number;
  updated_at: number;
}

export interface AgentExecutionResult {
  agent_name: string;
  task_id?: string;
  success: boolean;
  summary: string;
  output_data?: Record<string, any>;
  artifacts?: Array<Record<string, any>>;
  error?: string | null;
}

export const gatewayClient = new JarvisGatewayClient();
