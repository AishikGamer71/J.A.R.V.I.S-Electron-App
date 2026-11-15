import { describe, it, expect, beforeEach, vi } from 'vitest'
import { HermesAdapter } from './hermes-adapter'

describe('HermesAdapter', () => {
  let adapter: HermesAdapter

  beforeEach(() => {
    adapter = new HermesAdapter()
    // Mock window.hermesDesktop and window.electron
    ;(window as any).hermesDesktop = {
      getConnection: vi.fn().mockResolvedValue({ baseUrl: 'http://127.0.0.1:9119', token: 'test-token' }),
      getGatewayWsUrl: vi.fn().mockResolvedValue('ws://127.0.0.1:9119/api/ws?token=test-token'),
      api: vi.fn().mockImplementation(async ({ path, method }: { path: string; method?: string }) => {
        if (path === '/api/sessions' && method === 'POST') {
          return { id: 'test-session-123' }
        }
        if (path.includes('/messages') && method === 'GET') {
          return {
            messages: [
              { role: 'user', content: 'Hello JARVIS' },
              { role: 'assistant', content: 'Online and ready, sir.' }
            ]
          }
        }
        return { ok: true }
      })
    }
    ;(window as any).electron = {
      ipcRenderer: {
        invoke: vi.fn().mockResolvedValue(true)
      }
    }
  })

  it('creates and returns a session ID', async () => {
    const sessionId = await adapter.getOrCreateSession()
    expect(sessionId).toBe('test-session-123')
  })

  it('retrieves and formats message history correctly', async () => {
    await adapter.getOrCreateSession()
    const history = await adapter.getHistory()
    expect(history.length).toBe(2)
    expect(history[0]).toEqual({
      role: 'user',
      parts: [{ text: 'Hello JARVIS' }]
    })
    expect(history[1]).toEqual({
      role: 'model',
      parts: [{ text: 'Online and ready, sir.' }]
    })
  })

  it('dispatches jarvis-state events on gateway stream events', () => {
    const eventsDispatched: string[] = []
    const listener = (e: any) => {
      eventsDispatched.push(e.detail)
    }
    window.addEventListener('jarvis-state', listener)

    // Trigger internal private handler simulation
    ;(adapter as any).handleGatewayEvent({
      type: 'agent.message_chunk',
      payload: { text: 'Processing command' }
    })
    ;(adapter as any).handleGatewayEvent({
      type: 'tool.started'
    })
    ;(adapter as any).handleGatewayEvent({
      type: 'agent.complete'
    })

    window.removeEventListener('jarvis-state', listener)
    expect(eventsDispatched).toContain('SPEAKING')
    expect(eventsDispatched).toContain('PROCESSING')
    expect(eventsDispatched).toContain('LISTEN')
  })
})
