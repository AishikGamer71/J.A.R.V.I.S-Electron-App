export class HermesAdapter {
  private socket: WebSocket | null = null
  private currentSessionId: string | null = null
  private messageBuffer = ''

  async getConnectionInfo() {
    const conn = await window.hermesDesktop.getConnection(null)
    const wsUrlResult = await window.hermesDesktop.getGatewayWsUrl(null)
    
    let wsUrl = ''
    if (typeof wsUrlResult === 'string') {
      wsUrl = wsUrlResult
    } else if (wsUrlResult && typeof wsUrlResult === 'object' && wsUrlResult.ok) {
      wsUrl = wsUrlResult.wsUrl
    } else {
      const base = conn.baseUrl.replace(/^http/, 'ws')
      wsUrl = `${base}/api/ws?token=${encodeURIComponent(conn.token)}`
    }
    
    return { ...conn, wsUrl }
  }

  async connectGateway() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return
    }

    const { wsUrl } = await this.getConnectionInfo()

    return new Promise<void>((resolve, reject) => {
      this.socket = new WebSocket(wsUrl)
      
      this.socket.onopen = () => resolve()
      
      this.socket.onerror = (err) => reject(err)
      
      this.socket.onmessage = (event) => {
        try {
          const frame = JSON.parse(event.data)
          if (frame.method === 'event' && frame.params) {
            this.handleGatewayEvent(frame.params)
          } else if (frame.event) {
            this.handleGatewayEvent({ type: frame.event, payload: frame.data || frame.payload })
          } else if (frame.type) {
            this.handleGatewayEvent(frame)
          }
        } catch (e) {
          // ignore invalid frames
        }
      }
      
      this.socket.onclose = () => {
        this.socket = null
      }
    })
  }

  private handleGatewayEvent(event: any) {
    const type = event?.type || event?.event
    const payload = event?.payload || event?.data || event

    if (
      type === 'message.delta' ||
      type === 'agent.message_chunk' ||
      type === 'agent.chunk' ||
      type === 'turn.delta' ||
      type === 'message.chunk'
    ) {
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'SPEAKING' }))
      const text = payload?.text || payload?.chunk || (typeof payload === 'string' ? payload : '')
      if (text) {
        this.messageBuffer += text
      }
    } else if (
      type === 'message.complete' ||
      type === 'agent.complete' ||
      type === 'agent.finish' ||
      type === 'turn.complete' ||
      type === 'message.finished'
    ) {
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'LISTEN' }))
      if (this.messageBuffer.trim()) {
        this.saveMessage('model', this.messageBuffer.trim())
        this.messageBuffer = ''
      }
    } else if (
      type === 'tool.start' ||
      type === 'tool.started' ||
      type === 'agent.tool_call' ||
      type === 'turn.start' ||
      type === 'agent.start' ||
      type === 'processing'
    ) {
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'PROCESSING' }))
    } else if (type === 'error' || type === 'agent.error') {
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'LISTEN' }))
    }
  }

  async getOrCreateSession() {
    if (this.currentSessionId) {
      return this.currentSessionId
    }

    try {
      const response = await window.hermesDesktop.api({
        path: '/api/sessions',
        method: 'POST',
        body: {}
      })
      this.currentSessionId = (response as any)?.id || (response as any)?.session_id || (response as any)?.sessionId
      return this.currentSessionId
    } catch (e) {
      console.error('Failed to create session:', e)
      throw e
    }
  }

  async saveMessage(role: 'user' | 'model' | 'jarvis', text: string) {
    if (!text) return
    const safeRole = role === 'jarvis' ? 'assistant' : role === 'model' ? 'assistant' : role
    
    try {
      if (window.electron?.ipcRenderer) {
        await window.electron.ipcRenderer.invoke('add-message', {
          role: role === 'jarvis' ? 'model' : role,
          parts: [{ text }]
        })
      }
    } catch (e) {
      // ignore
    }
  }

  async getHistory(): Promise<Array<{ role: 'user' | 'model'; parts: [{ text: string }] }>> {
    if (!this.currentSessionId) return []
    try {
      const response = await window.hermesDesktop.api({
        path: `/api/sessions/${this.currentSessionId}/messages`,
        method: 'GET'
      })
      
      const messages: any[] = Array.isArray(response)
        ? response
        : (response as any)?.messages || []

      return messages.map((m: any) => {
        const content =
          typeof m.content === 'string'
            ? m.content
            : Array.isArray(m.parts)
            ? m.parts.map((p: any) => p?.text || '').join('')
            : m.text || ''

        const role: 'user' | 'model' = m.role === 'assistant' || m.role === 'model' ? 'model' : 'user'

        return {
          role,
          parts: [{ text: content }] as [{ text: string }]
        }
      })
    } catch (e) {
      return []
    }
  }

  async clearHistory() {
    if (this.currentSessionId) {
      try {
        await window.hermesDesktop.api({
          path: `/api/sessions/${this.currentSessionId}`,
          method: 'DELETE'
        })
      } catch (e) {
        // ignore
      }
      this.currentSessionId = null
    }
    
    try {
      if (window.electron?.ipcRenderer) {
        await window.electron.ipcRenderer.invoke('clear-history')
      }
      return true
    } catch (e) {
      return false
    }
  }

  async submitPrompt(text: string) {
    const sessionId = await this.getOrCreateSession()
    
    await this.connectGateway()
    
    // Save locally
    await this.saveMessage('user', text)
    
    window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'PROCESSING' }))
    
    try {
      await window.hermesDesktop.api({
        path: `/api/sessions/${sessionId}/messages`,
        method: 'POST',
        body: { content: text },
        timeoutMs: 1800000
      })
    } catch (e) {
      console.error('Failed to submit prompt:', e)
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'LISTEN' }))
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }
}

export const hermesAdapter = new HermesAdapter()
