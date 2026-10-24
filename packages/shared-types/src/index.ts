/**
 * Shared Type Definitions for J.A.R.V.I.S AI Monorepo
 */

export type MessageRole = 'system' | 'user' | 'assistant' | 'tool';

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: MessageRole;
  content: string;
  tier?: ModelTier;
  model?: string;
  createdAt: number;
  tokens?: {
    prompt?: number;
    completion?: number;
    total?: number;
  };
  metadata?: Record<string, any>;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  metadata?: Record<string, any>;
}

export type ModelTier = 'tier1_local' | 'tier2_balanced' | 'tier3_cloud';

export interface HardwareTelemetry {
  cpuPercent: number;
  ramPercent: number;
  ramUsedGb: number;
  ramTotalGb: number;
  gpuName?: string;
  vramUsedMb?: number;
  vramTotalMb?: number;
  systemTier: 'low' | 'mid' | 'high';
  temperatureC?: number;
  timestamp: number;
}

export interface NetworkStatus {
  isOnline: boolean;
  latencyMs?: number;
  checkedAt: number;
}

export interface RouterDecision {
  tier: ModelTier;
  selectedProvider: 'ollama' | 'litellm';
  selectedModel: string;
  reason: string;
  isFallback: boolean;
}

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface ToolDefinition {
  name: string;
  description: string;
  riskLevel: RiskLevel;
  parameters: Record<string, any>;
}

export interface ToolConfirmationRequest {
  confirmationId: string;
  toolName: string;
  riskLevel: RiskLevel;
  arguments: Record<string, any>;
  requestedAt: number;
  timeoutSeconds: number;
}

export interface ToolConfirmationResponse {
  confirmationId: string;
  approved: boolean;
  reason?: string;
}

export interface StreamChunk {
  sessionId: string;
  messageId: string;
  delta: string;
  done: boolean;
  tier?: ModelTier;
  model?: string;
}

export interface CoreServiceStatus {
  isRunning: boolean;
  pid?: number;
  port: number;
  uptimeSeconds: number;
  restarts: number;
  version: string;
}

export type IPCChannels = {
  'chat:send': (payload: { sessionId: string; content: string }) => Promise<ChatMessage>;
  'chat:getHistory': (payload: { sessionId: string }) => Promise<ChatMessage[]>;
  'chat:getSessions': () => Promise<ChatSession[]>;
  'chat:searchHistory': (payload: { query: string }) => Promise<ChatMessage[]>;
  'system:getTelemetry': () => Promise<HardwareTelemetry>;
  'system:getNetwork': () => Promise<NetworkStatus>;
  'core:getStatus': () => Promise<CoreServiceStatus>;
  'core:restart': () => Promise<{ success: boolean }>;
};
