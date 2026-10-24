import { gatewayClient } from '@/lib/gateway-client'

export interface ChatMessage {
  role: 'user' | 'model'
  parts: [{ text: string }]
}

const DEFAULT_SESSION = 'jarvis-main-chat'

export const saveMessage = async (role: 'user' | 'model' | 'jarvis', text: string) => {
  if (window.electron?.ipcRenderer) {
    try {
      await window.electron.ipcRenderer.invoke('add-message', {
        role: role === 'jarvis' ? 'model' : role,
        parts: [{ text }]
      })
    } catch {}
  }
  return true
}

export const getHistory = async (): Promise<ChatMessage[]> => {
  try {
    const messages = await gatewayClient.getMessages(DEFAULT_SESSION, 20)
    if (Array.isArray(messages) && messages.length > 0) {
      return messages.map((m: any) => ({
        role: m.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: m.content }]
      }))
    }
  } catch {}
  
  if (window.electron?.ipcRenderer) {
    try {
      const hist = await window.electron.ipcRenderer.invoke('get-history')
      if (Array.isArray(hist)) return hist
    } catch {}
  }
  return []
}

export const clearHistory = async (): Promise<boolean> => {
  try {
    await gatewayClient.deleteSession(DEFAULT_SESSION)
  } catch {}
  if (window.electron?.ipcRenderer) {
    try {
      await window.electron.ipcRenderer.invoke('clear-history')
    } catch {}
  }
  return true
}

export const saveCoreMemory = async (fact: string): Promise<string> => {
  try {
    if (window.electron?.ipcRenderer) {
      const success = await window.electron.ipcRenderer.invoke('save-core-memory', fact)
      if (success) {
        return `✅ Successfully committed to permanent memory: "${fact}"`
      }
    }
    return '❌ System failure: Could not save to permanent memory.'
  } catch (error) {
    return `❌ System failure: ${String(error)}`
  }
}

export const retrieveCoreMemory = async (): Promise<string> => {
  try {
    if (window.electron?.ipcRenderer) {
      const memories = await window.electron.ipcRenderer.invoke('search-core-memory')
      if (Array.isArray(memories) && memories.length > 0) {
        return `Here is the permanent memory bank data:\n${JSON.stringify(memories, null, 2)}`
      }
    }
    return 'The permanent memory bank is currently empty.'
  } catch (error) {
    return `❌ System failure: ${String(error)}`
  }
}
