import React, { useEffect, useRef, useState } from 'react'
import { Terminal as XTerm } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { RiArrowDownSLine, RiAddLine, RiTerminalBoxLine, RiSettings4Line, RiCloseLine } from 'react-icons/ri'
import { VscTerminalCmd } from 'react-icons/vsc'
import { FaGitAlt } from 'react-icons/fa'

let nextTabId = 1;
const generateTabId = () => `tab-${nextTabId++}`;

interface TabData {
  id: string;
  name: string;
  shellCmd: string;
}

function TerminalInstance({ tab, isActive }: { tab: TabData, isActive: boolean }) {
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<XTerm | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)

  useEffect(() => {
    if (!terminalRef.current) return

    const term = new XTerm({
      allowTransparency: true,
      cursorBlink: true,
      fontFamily: 'Consolas, "Courier New", monospace',
      fontSize: 14,
      theme: {
        background: 'transparent',
        foreground: '#10b981',
        cursor: '#10b981',
        selectionBackground: 'rgba(16, 185, 129, 0.3)',
        black: '#000000',
        red: '#ef4444',
        green: '#10b981',
        yellow: '#f59e0b',
        blue: '#3b82f6',
        magenta: '#8b5cf6',
        cyan: '#06b6d4',
        white: '#ffffff',
      }
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)

    term.open(terminalRef.current)
    
    xtermRef.current = term
    fitAddonRef.current = fitAddon
    
    // Spawn process on backend
    const { ipcRenderer } = (window as any).electron
    ipcRenderer.send('terminal-spawn', { tabId: tab.id, shellName: tab.shellCmd })

    const handleOutput = (event: any, payload: { tabId: string, data: string }) => {
      if (payload.tabId === tab.id) {
        term.write(payload.data)
      }
    }

    ipcRenderer.on('terminal-output', handleOutput)

    term.onData((data) => {
      ipcRenderer.send('terminal-input', { tabId: tab.id, data })
    })

    const handleResize = () => {
      if (terminalRef.current?.offsetWidth && terminalRef.current?.offsetHeight) {
        fitAddon.fit()
        ipcRenderer.send('terminal-resize', { tabId: tab.id, cols: term.cols, rows: term.rows })
      }
    }
    
    // Small delay to ensure DOM is ready before fitting
    setTimeout(handleResize, 100)
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      ipcRenderer.removeListener('terminal-output', handleOutput)
      ipcRenderer.send('terminal-close', tab.id)
      term.dispose()
    }
  }, [tab.id, tab.shellCmd])
  
  // Force a resize when the tab becomes active because xterm loses layout when hidden
  useEffect(() => {
    if (isActive && fitAddonRef.current && xtermRef.current) {
      setTimeout(() => {
        try {
          fitAddonRef.current?.fit()
          const { ipcRenderer } = (window as any).electron
          ipcRenderer.send('terminal-resize', { tabId: tab.id, cols: xtermRef.current?.cols, rows: xtermRef.current?.rows })
        } catch(e) {}
      }, 50)
    }
  }, [isActive, tab.id])

  return (
    <div 
      className="w-full h-full p-2 pt-1 pb-4 relative z-0"
      style={{ display: isActive ? 'block' : 'none' }}
    >
      <div ref={terminalRef} className="w-full h-full" />
    </div>
  )
}

export default function Terminal() {
  const [showDropdown, setShowDropdown] = useState(false)
  const [tabs, setTabs] = useState<TabData[]>([
    { id: generateTabId(), name: 'Windows PowerShell', shellCmd: 'powershell.exe' }
  ])
  const [activeTabId, setActiveTabId] = useState<string>(tabs[0].id)

  const addNewTab = (name: string, shellCmd: string) => {
    const newTab = { id: generateTabId(), name, shellCmd }
    setTabs(prev => [...prev, newTab])
    setActiveTabId(newTab.id)
    setShowDropdown(false)
  }

  const closeTab = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setTabs(prev => {
      const newTabs = prev.filter(t => t.id !== id)
      if (newTabs.length > 0 && activeTabId === id) {
        setActiveTabId(newTabs[newTabs.length - 1].id)
      }
      return newTabs
    })
  }
  
  const handleAiExecute = (e: any) => {
    // If JARVIS executes a command, send it to the active tab
    const command = e.detail
    const { ipcRenderer } = (window as any).electron
    if (activeTabId) {
      ipcRenderer.send('terminal-input', { tabId: activeTabId, data: command + '\r' })
    }
  }

  useEffect(() => {
    window.addEventListener('jarvis-terminal-execute', handleAiExecute)
    return () => window.removeEventListener('jarvis-terminal-execute', handleAiExecute)
  }, [activeTabId])

  return (
    <div className="w-full h-full bg-transparent backdrop-blur-md flex flex-col relative overflow-hidden font-segoe border border-emerald-500/20 rounded-xl shadow-inner shadow-emerald-500/10">
      {/* Title Bar - App Theme */}
      <div className="h-10 flex items-end pl-2 select-none relative z-10 border-b border-emerald-500/20 bg-black/20 overflow-x-auto overflow-y-hidden no-scrollbar">
        
        <div className="flex flex-row items-end flex-nowrap">
          {tabs.map((tab) => {
            const isActive = tab.id === activeTabId;
            return (
              <div 
                key={tab.id}
                onClick={() => setActiveTabId(tab.id)}
                className={`h-8 rounded-t-lg flex items-center px-3 min-w-[160px] max-w-[200px] border-t border-x cursor-pointer transition-colors group ${
                  isActive 
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-[0_-2px_10px_rgba(16,185,129,0.1)]' 
                    : 'bg-transparent border-transparent text-emerald-500/50 hover:bg-emerald-500/5 hover:text-emerald-400'
                } gap-2 mr-1`}
              >
                {tab.name.includes('PowerShell') ? <RiTerminalBoxLine className="text-emerald-400 text-sm" /> :
                 tab.name.includes('Command') ? <VscTerminalCmd className="text-emerald-400 text-sm" /> :
                 <FaGitAlt className="text-emerald-400 text-sm" />}
                 
                <span className="flex-1 font-medium tracking-wide truncate text-xs">{tab.name}</span>
                
                <div 
                  onClick={(e) => closeTab(e, tab.id)}
                  className="hover:bg-emerald-500/20 p-0.5 rounded cursor-pointer transition-colors text-emerald-500/50 hover:text-emerald-400 opacity-0 group-hover:opacity-100"
                >
                  <RiCloseLine size={14} />
                </div>
              </div>
            )
          })}
        </div>

        {/* New Tab & Dropdown Buttons */}
        <div className="h-8 flex items-center mb-0 ml-1 sticky right-0 bg-gradient-to-l from-black/80 via-black/50 to-transparent pl-4 pr-2">
          <div 
            className="h-7 w-8 flex items-center justify-center hover:bg-emerald-500/10 rounded cursor-pointer text-emerald-500/80 hover:text-emerald-400 transition-colors"
            onClick={() => addNewTab('Windows PowerShell', 'powershell.exe')}
          >
            <RiAddLine size={16} />
          </div>
          <div 
            className="h-7 w-6 flex items-center justify-center hover:bg-emerald-500/10 rounded cursor-pointer text-emerald-500/80 hover:text-emerald-400 transition-colors"
            onClick={() => setShowDropdown(!showDropdown)}
          >
            <RiArrowDownSLine size={16} />
          </div>
        </div>
      </div>

      {/* Dropdown Menu Overlay */}
      {showDropdown && (
        <div className="absolute top-10 left-[230px] w-[260px] bg-black/80 backdrop-blur-xl border border-emerald-500/30 rounded-md shadow-2xl py-1 z-50 text-[13px] text-emerald-100/80">
          <div className="px-1">
            <div 
              className="flex items-center px-3 py-1.5 hover:bg-emerald-500/20 rounded cursor-pointer group"
              onClick={() => addNewTab('Windows PowerShell', 'powershell.exe')}
            >
              <RiTerminalBoxLine className="text-emerald-400 mr-3 text-lg" />
              <span className="flex-1 text-emerald-100">Windows PowerShell</span>
              <span className="text-[10px] opacity-0 group-hover:opacity-50 tracking-wider">Ctrl+Shift+1</span>
            </div>
            <div 
              className="flex items-center px-3 py-1.5 hover:bg-emerald-500/20 rounded cursor-pointer group"
              onClick={() => addNewTab('Command Prompt', 'cmd.exe')}
            >
              <VscTerminalCmd className="text-emerald-400 mr-3 text-lg" />
              <span className="flex-1 text-emerald-100">Command Prompt</span>
              <span className="text-[10px] opacity-0 group-hover:opacity-50 tracking-wider">Ctrl+Shift+2</span>
            </div>
            <div 
              className="flex items-center px-3 py-1.5 hover:bg-emerald-500/20 rounded cursor-pointer group"
              onClick={() => addNewTab('Git Bash', 'bash.exe')}
            >
              <FaGitAlt className="text-emerald-400 mr-3 text-lg" />
              <span className="flex-1 text-emerald-100">Git Bash</span>
              <span className="text-[10px] opacity-0 group-hover:opacity-50 tracking-wider">Ctrl+Shift+3</span>
            </div>
          </div>
          <div className="h-px bg-emerald-500/20 my-1 mx-2" />
          <div className="px-1">
            <div className="flex items-center px-3 py-1.5 hover:bg-emerald-500/20 rounded cursor-pointer">
              <RiSettings4Line className="text-emerald-500/70 mr-3 text-lg" />
              <span className="flex-1 text-emerald-100">Settings</span>
            </div>
          </div>
        </div>
      )}

      {/* Terminal Containers (One for each tab) */}
      <div className="flex-1 w-full bg-transparent relative z-0">
        {tabs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-emerald-500/50">
            No active terminal sessions. Click '+' to open one.
          </div>
        ) : (
          tabs.map(tab => (
            <TerminalInstance 
              key={tab.id} 
              tab={tab} 
              isActive={tab.id === activeTabId} 
            />
          ))
        )}
      </div>
    </div>
  )
}
