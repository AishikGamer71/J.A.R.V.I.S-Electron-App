/**
 * Typed IPC Channel Constants and Protocol Definitions
 */

export const IPC_CHANNELS = {
  // Chat & Gateway
  CHAT_SEND: 'chat:send',
  CHAT_STREAM_DELTA: 'chat:stream:delta',
  CHAT_STREAM_DONE: 'chat:stream:done',
  CHAT_GET_HISTORY: 'chat:getHistory',
  CHAT_GET_SESSIONS: 'chat:getSessions',
  CHAT_SEARCH_HISTORY: 'chat:searchHistory',
  
  // System & Telemetry
  SYSTEM_GET_TELEMETRY: 'system:getTelemetry',
  SYSTEM_GET_NETWORK: 'system:getNetwork',
  SYSTEM_TELEMETRY_STREAM: 'system:telemetry:stream',
  
  // Core Service Control
  CORE_GET_STATUS: 'core:getStatus',
  CORE_RESTART: 'core:restart',
  
  // Window & Overlay
  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_CLOSE: 'window:close',
  OVERLAY_TOGGLE: 'overlay:toggle'
} as const;

export type IPCChannelName = typeof IPC_CHANNELS[keyof typeof IPC_CHANNELS];
