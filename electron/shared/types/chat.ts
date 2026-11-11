/**
 * Chat message types shared between Main process and Renderer.
 */

export type ChatRole = 'user' | 'model' | 'jarvis'

export interface ChatMessagePart {
  text: string
}

export interface ChatMessage {
  role: ChatRole
  parts: ChatMessagePart[]
  content?: string
  timestamp?: string
}
