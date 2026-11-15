import { useState, useEffect, useCallback } from 'react'
import {
  RiSubtractLine,
  RiCloseLine,
  RiCheckboxBlankLine,
  RiCheckboxMultipleBlankLine
} from 'react-icons/ri'

const TitleBar = () => {
  const [isMaximized, setIsMaximized] = useState(false)
  const [isMac, setIsMac] = useState(false)

  // Query actual window maximize state from main process
  const checkMaximized = useCallback(() => {
    if (window.electron?.ipcRenderer) {
      window.electron.ipcRenderer
        .invoke('window-is-maximized')
        .then((max: boolean) => {
          setIsMaximized(Boolean(max))
        })
        .catch(() => {})
    } else if (window.jarvis?.window?.isMaximized) {
      window.jarvis.window
        .isMaximized()
        .then((max: boolean) => {
          setIsMaximized(Boolean(max))
        })
        .catch(() => {})
    }
  }, [])

  useEffect(() => {
    if (window.electron && window.electron.process) {
      setIsMac(window.electron.process.platform === 'darwin')
    } else {
      setIsMac(navigator.userAgent.toLowerCase().includes('mac'))
    }

    checkMaximized()

    // Listen for maximize/unmaximize pushes from Electron main process
    const removeListener = window.electron?.ipcRenderer?.on(
      'window-maximize-change',
      (_event: any, isMax: boolean) => {
        setIsMaximized(Boolean(isMax))
      }
    )

    // Global F11 shortcut listener
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'F11') {
        e.preventDefault()
        window.electron?.ipcRenderer?.send('window-toggle-fullscreen')
      }
    }
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      removeListener?.()
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [checkMaximized])

  const minimize = () => {
    if (window.electron?.ipcRenderer) {
      window.electron.ipcRenderer.send('window-min')
    } else if (window.jarvis?.window?.minimize) {
      window.jarvis.window.minimize()
    }
  }

  const toggleMaximize = () => {
    if (window.electron?.ipcRenderer) {
      window.electron.ipcRenderer.send('window-max')
    } else if (window.jarvis?.window?.maximize) {
      window.jarvis.window.maximize()
    }
    // Re-verify maximize state after IPC round-trip
    setTimeout(checkMaximized, 100)
  }

  const close = () => {
    if (window.electron?.ipcRenderer) {
      window.electron.ipcRenderer.send('window-close')
    } else if (window.jarvis?.window?.close) {
      window.jarvis.window.close()
    }
  }

  return (
    <div
      onDoubleClick={(e) => {
        // Only double-click to maximize if target is the titlebar itself, not a button
        if ((e.target as HTMLElement)?.closest('button')) return
        toggleMaximize()
      }}
      className="w-full h-10 shrink-0 flex items-center justify-between px-4 bg-black/90 backdrop-blur-md border-b border-emerald-500/20 shadow-md shadow-emerald-500/5 drag-region select-none z-1000 relative overflow-hidden"
    >
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent pointer-events-none" />

      {isMac && (
        <div
          className="flex items-center gap-2 no-drag z-50 pointer-events-auto"
          style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
        >
          <button
            onClick={close}
            title="Close"
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
            className="w-3 h-3 rounded-full bg-red-500 hover:bg-red-600 border border-red-600 flex items-center justify-center group cursor-pointer transition-colors"
          >
            <span className="hidden group-hover:block text-[8px] text-red-900 font-bold">✕</span>
          </button>
          <button
            onClick={minimize}
            title="Minimize"
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
            className="w-3 h-3 rounded-full bg-yellow-500 hover:bg-yellow-600 border border-yellow-600 flex items-center justify-center group cursor-pointer transition-colors"
          >
            <span className="hidden group-hover:block text-[8px] text-yellow-900 font-bold">−</span>
          </button>
          <button
            onClick={toggleMaximize}
            title={isMaximized ? 'Restore' : 'Maximize'}
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
            className="w-3 h-3 rounded-full bg-emerald-500 hover:bg-emerald-600 border border-emerald-600 flex items-center justify-center group cursor-pointer transition-colors"
          >
            <span className="hidden group-hover:block text-[8px] text-emerald-900 font-bold">+</span>
          </button>
        </div>
      )}

      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-2 opacity-60 pointer-events-none">
        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_#10b981]" />
        <div className="text-[11px] font-bold text-zinc-300 tracking-[0.3em]">
          JARVIS
        </div>
      </div>

      {!isMac && (
        <div
          className="flex h-full no-drag ml-auto -mr-4 z-50 pointer-events-auto"
          style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
        >
          {/* Minimize: Horizontal bar (Subtract line) */}
          <button
            onClick={minimize}
            title="Minimize"
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
            className="w-12 h-full flex items-center justify-center text-zinc-400 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
          >
            <RiSubtractLine size={16} />
          </button>

          {/* Maximize / Restore Down: Single square when normal, overlapping squares when maximized */}
          <button
            onClick={toggleMaximize}
            title={isMaximized ? 'Restore Down' : 'Maximize'}
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
            className="w-12 h-full flex items-center justify-center text-zinc-400 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
          >
            {isMaximized ? (
              <RiCheckboxMultipleBlankLine size={14} className="text-zinc-300" />
            ) : (
              <RiCheckboxBlankLine size={14} className="text-zinc-300" />
            )}
          </button>

          {/* Close: Cross */}
          <button
            onClick={close}
            title="Close"
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
            className="w-12 h-full flex items-center justify-center text-zinc-400 hover:bg-red-600 hover:text-white transition-colors cursor-pointer"
          >
            <RiCloseLine size={18} />
          </button>
        </div>
      )}
    </div>
  )
}

export default TitleBar
