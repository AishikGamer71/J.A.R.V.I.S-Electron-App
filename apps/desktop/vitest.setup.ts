import { configure } from '@testing-library/react'

// React 19 + Testing Library 16: opt into the act environment so render(),
// fireEvent(), and findBy* queries automatically flush state updates without
// spurious "not wrapped in act(...)" warnings.
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true

// findBy*/waitFor default to a 1000ms deadline — too tight for async-heavy
// panels (radix menus, refetch chains) when the full suite runs under xdist
// CPU contention in CI. Success still resolves the instant the node appears;
// the wider deadline only absorbs a starved runner, killing timing flakes.
configure({ asyncUtilTimeout: 5000 })

// Mock WebSocket to prevent unhandled background connection errors in jsdom
if (typeof window !== 'undefined') {
  class MockWebSocket extends EventTarget {
    static readonly CONNECTING = 0
    static readonly OPEN = 1
    static readonly CLOSING = 2
    static readonly CLOSED = 3
    readonly CONNECTING = 0
    readonly OPEN = 1
    readonly CLOSING = 2
    readonly CLOSED = 3

    readyState = 3 // CLOSED
    url: string
    onopen: any = null
    onclose: any = null
    onerror: any = null
    onmessage: any = null

    constructor(url: string) {
      super()
      this.url = url
    }
    close() {}
    send() {}
  }
  ;(window as any).WebSocket = MockWebSocket
  ;(globalThis as any).WebSocket = MockWebSocket
}
