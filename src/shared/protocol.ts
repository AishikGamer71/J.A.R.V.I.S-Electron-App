/**
 * J.A.R.V.I.S. Unified WebSocket Contract & IPC Interfaces
 * Shared Source of Truth between Electron Frontend/Main and Python Sidecar.
 * Keeps strict parity with backend/schemas/protocol.py
 */

export type ProtocolMessageType =
  | 'user.message'
  | 'audio.control'
  | 'agent.state'
  | 'agent.token'
  | 'agent.complete'
  | 'tool.start'
  | 'tool.result'
  | 'system.metrics'
  | 'client.command'
  | 'error'

export type AgentStateValue =
  | 'idle'
  | 'listening'
  | 'transcribing'
  | 'thinking'
  | 'executing_tool'
  | 'speaking'

export interface WebSocketEnvelope<T = Record<string, any>> {
  type: ProtocolMessageType
  request_id: string
  timestamp: string
  payload: T
}

export interface UserMessagePayload {
  content: string
  session_id: string
  audio_base64?: string
  mime_type?: string
}

export interface AudioControlPayload {
  action: 'start_listen' | 'stop_listen' | 'cancel_speech' | 'synthesize'
  text?: string
  voice?: string
  session_id?: string
}

export interface AgentStatePayload {
  state: AgentStateValue
  session_id?: string
  details?: string
}

export interface AgentTokenPayload {
  session_id: string
  delta: string
}

export interface AgentCompletePayload {
  session_id: string
  content: string
  message_id?: string
  role?: 'assistant'
  created_at?: number
  audio_base64?: string
  mime_type?: string
}

export interface ToolStartPayload {
  session_id: string
  tool: string
  arguments: Record<string, any>
  timestamp?: number
}

export interface ToolResultPayload {
  session_id: string
  tool: string
  result: any
  duration_ms?: number
  risk_level?: string
  outcome?: 'SUCCESS' | 'ERROR' | 'DENIED'
}

export interface SystemHardwareMetrics {
  cpu_percent: number
  cpu_temp?: number
  cpu_freq_mhz?: number
  cores?: number[]
  ram_percent: number
  ram_used_gb: number
  ram_total_gb: number
  disk_percent?: number
  disk_used_gb?: number
  disk_total_gb?: number
  battery_percent?: number
  battery_charging?: boolean
  gpu_name?: string
  vram_used_mb?: number
  vram_total_mb?: number
  system_tier?: 'low' | 'mid' | 'high'
}

export interface SystemNetworkMetrics {
  is_online: boolean
  bytes_sent_rate?: number
  bytes_recv_rate?: number
  latency_ms?: number
}

export interface SystemMetricsPayload {
  hardware: SystemHardwareMetrics
  network: SystemNetworkMetrics
  uptime_seconds: number
}

export type ClientCommandType =
  | 'hud.minimize'
  | 'hud.show'
  | 'hud.compact_mode'
  | 'hud.expand_mode'
  | 'hud.always_on_top'
  | 'hud.toggle_mic'
  | 'hud.notification'

export interface ClientCommandPayload {
  command: ClientCommandType
  params?: Record<string, any>
}

export interface ErrorPayload {
  message: string
  code?: string
  details?: any
}

/** Factory helper to build valid envelopes */
export function createEnvelope<T>(type: ProtocolMessageType, payload: T, requestId?: string): WebSocketEnvelope<T> {
  return {
    type,
    request_id: requestId || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `req_${Date.now()}`),
    timestamp: new Date().toISOString(),
    payload
  }
}
