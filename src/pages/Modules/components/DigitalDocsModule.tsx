import React, { useState } from 'react'
import { motion } from 'framer-motion'
import {
  RiBookOpenLine,
  RiSearchLine,
  RiCodeBoxLine,
  RiTerminalBoxLine,
  RiVoiceprintLine,
  RiShieldCheckLine,
  RiFileTextLine,
  RiDownload2Line,
  RiFileCopyLine,
  RiCheckLine,
  RiEditLine
} from 'react-icons/ri'
import { useSettingsStore } from '@/store/settings-store'
import { hexToRgba } from '@/services/theme-manager'

interface DocSection {
  id: string
  title: string
  icon: any
  summary: string
  content: string
}

const DOC_SECTIONS: DocSection[] = [
  {
    id: 'arch',
    title: 'System Architecture & Neural Core',
    icon: <RiCodeBoxLine size={18} />,
    summary: 'Electron main process, IPC channels, and local Python neural services.',
    content: `### 🏛️ JARVIS Dual-Layer Architecture

JARVIS combines a ultra-low latency **Electron Desktop Shell** with autonomous **Python Microservices**:

1. **Frontend Interface (Electron / React 19 / Vite)**:
   - Modern glassmorphic HUD designed with reactive State Management (Zustand).
   - Real-time hardware telemetry (CPU, RAM, GPU, Network) polled via OS native handles.
   - Dynamic Theme & Preset Engine with real-time CSS custom property injection.

2. **Core AI Service (\`apps/core-service\` • Port 8765)**:
   - Autonomous multi-agent coordination engine.
   - Tool execution gateway with explicit permission sandboxing.
   - Encrypted local OS keystore for zero-leak external model tokens.

3. **Neural Voice Service (\`services/voice-service\` • Port 8766)**:
   - WebSocket streaming audio synthesis and speech transcription.
   - Bidirectional audio visualizer pipeline.`
  },
  {
    id: 'voice',
    title: 'Voice Commands & NLP Triggers',
    icon: <RiVoiceprintLine size={18} />,
    summary: 'Voice activation phrases, system queries, and automation directives.',
    content: `### 🗣️ Vocal Command Protocol

Speak naturally to JARVIS using any of the following standard protocols:

- **System Diagnostics**:
  - *"JARVIS, report system status"* — Live metrics on CPU, Memory, GPU & Network.
  - *"Run diagnostics sequence"* — Audits all microservice ports and background daemons.

- **Workspace Automation**:
  - *"Open terminal and run build"* — Automatically launches shell and passes compilation commands.
  - *"Create note titled Project Roadmap"* — Appends new persistent document in Notes module.
  - *"Search web for latest AI news"* — Dispatches autonomous agent query with summary citations.

- **Theme & HUD Control**:
  - *"Switch theme to Stark Arc Reactor"* — Activates blue cyan HUD preset.
  - *"Activate privacy lock"* — Engages biometric and 4-digit PIN security shield.`
  },
  {
    id: 'tools',
    title: 'Autonomous Tool Sandboxing',
    icon: <RiShieldCheckLine size={18} />,
    summary: 'Security risk levels, execution gating, and audit logging.',
    content: `### 🛡️ Tool Sandboxing & Permission Matrix

Every action JARVIS performs on your local PC is classified by risk:

| Risk Level | Trigger Mode | Action Examples |
| :--- | :--- | :--- |
| **LOW** | Auto-executed | Read system info, fetch public web pages, search local notes |
| **MEDIUM** | Gated / Confirmed | Execute shell scripts, modify configuration files |
| **HIGH** | Explicit Confirmation | Terminate active OS tasks, install software packages |
| **CRITICAL**| Vault PIN Required | Modify master encryption keys, format storage directories |

> [!NOTE]
> Tool permissions can be permanently granted or revoked inside **Settings ➔ Permissions** at any time.`
  },
  {
    id: 'hotkeys',
    title: 'Keyboard Shortcuts & Quick Access',
    icon: <RiTerminalBoxLine size={18} />,
    summary: 'Global accelerators, window shortcuts, and terminal toggles.',
    content: `### ⌨️ Global Accelerators & Hotkeys

- **\`Alt + Space\`**: Toggle JARVIS Mini-Overlay (Floating HUD)
- **\`Ctrl + T\`**: Switch immediately to Terminal Console
- **\`Ctrl + M\`**: Toggle Microphone Active / Standby
- **\`Ctrl + Shift + S\`**: Open Settings Command Center
- **\`Ctrl + L\`**: Clear current chat or terminal session
- **\`Esc\`**: Exit full-screen / Close active modals`
  }
]

export const DigitalDocsModule: React.FC = () => {
  const theme = useSettingsStore((state) => state.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  const [activeSectionId, setActiveSectionId] = useState('arch')
  const [searchQuery, setSearchQuery] = useState('')
  const [customNotes, setCustomNotes] = useState(
    `# User System Notes\n\n- [x] Initialized JARVIS Neural Interface\n- [x] Configured Theme & HUD Parameters\n- [ ] Connected External Model API Keys\n\n*Created in JARVIS Digital Documentation Hub.*`
  )
  const [isEditingNotes, setIsEditingNotes] = useState(false)
  const [copied, setCopied] = useState(false)

  const activeDoc = DOC_SECTIONS.find((d) => d.id === activeSectionId) || DOC_SECTIONS[0]

  const filteredDocs = DOC_SECTIONS.filter(
    (d) =>
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.content.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleCopy = () => {
    navigator.clipboard.writeText(isEditingNotes ? customNotes : activeDoc.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const textToDownload = isEditingNotes ? customNotes : activeDoc.content
    const blob = new Blob([textToDownload], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${activeDoc.title.replace(/\s+/g, '_')}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="h-full flex flex-col gap-6 overflow-y-auto pr-2 scrollbar-small">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2.5">
            <RiBookOpenLine style={{ color: primaryColor }} size={24} />
            Digital Technical Documentation
          </h3>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            System architectural manuals, voice command specifications, and local markdown reference.
          </p>
        </div>

        {/* Search & Mode Switcher */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-zinc-950/60 border border-white/10 rounded-xl px-3 py-1.5 focus-within:border-white/30">
            <RiSearchLine className="text-zinc-500 mr-2" size={16} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search documentation..."
              className="bg-transparent border-none outline-none text-xs text-zinc-100 placeholder:text-zinc-600 font-mono w-40"
            />
          </div>

          <button
            onClick={() => setIsEditingNotes(!isEditingNotes)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-mono font-bold transition-all flex items-center gap-2 cursor-pointer ${
              isEditingNotes
                ? 'bg-white text-black border-white shadow-md'
                : 'bg-white/5 text-zinc-400 border-white/10 hover:text-white'
            }`}
          >
            <RiEditLine size={14} /> {isEditingNotes ? 'DOCS VIEW' : 'SCRATCHPAD'}
          </button>
        </div>
      </div>

      {/* Main Grid: Left Sub-topics + Right Doc Reader */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 1 Col: Section List */}
        <div className="flex flex-col gap-2.5">
          <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest font-mono pl-1">
            Documentation Modules
          </span>

          {filteredDocs.map((sec) => {
            const isSelected = activeSectionId === sec.id && !isEditingNotes
            return (
              <button
                key={sec.id}
                onClick={() => {
                  setActiveSectionId(sec.id)
                  setIsEditingNotes(false)
                }}
                className={`p-4 rounded-2xl border text-left transition-all cursor-pointer flex flex-col gap-1.5 ${
                  isSelected
                    ? 'shadow-lg border-2'
                    : 'bg-zinc-950/40 border-white/10 hover:border-white/20 hover:bg-white/5'
                }`}
                style={
                  isSelected
                    ? {
                        backgroundColor: hexToRgba(primaryColor, 0.08),
                        borderColor: primaryColor,
                        boxShadow: `0 0 15px ${hexToRgba(primaryColor, 0.2)}`
                      }
                    : {}
                }
              >
                <div className="flex items-center gap-2 text-xs font-bold text-white">
                  <span style={isSelected ? { color: primaryColor } : { color: '#a1a1aa' }}>
                    {sec.icon}
                  </span>
                  <span>{sec.title}</span>
                </div>
                <p className="text-[11px] text-zinc-400 line-clamp-2 leading-relaxed font-sans">
                  {sec.summary}
                </p>
              </button>
            )
          })}
        </div>

        {/* Right 2 Cols: Markdown Document Viewer / Editor */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-zinc-950/50 backdrop-blur-md border border-white/10 flex flex-col justify-between gap-4 shadow-xl min-h-[400px]">
          <div className="flex flex-col gap-4">
            {/* Header bar inside viewer */}
            <div className="flex justify-between items-center border-b border-white/10 pb-3">
              <span className="text-xs font-bold uppercase tracking-widest font-mono text-zinc-300 flex items-center gap-2">
                <RiFileTextLine style={{ color: primaryColor }} size={16} />
                {isEditingNotes ? 'Interactive Markdown Scratchpad' : activeDoc.title}
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                  title="Copy Document"
                >
                  {copied ? <RiCheckLine size={16} style={{ color: primaryColor }} /> : <RiFileCopyLine size={16} />}
                </button>
                <button
                  onClick={handleDownload}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                  title="Export as Markdown .md"
                >
                  <RiDownload2Line size={16} />
                </button>
              </div>
            </div>

            {/* Document Content */}
            {isEditingNotes ? (
              <textarea
                value={customNotes}
                onChange={(e) => setCustomNotes(e.target.value)}
                rows={14}
                className="w-full bg-transparent border-none outline-none text-xs font-mono text-zinc-100 placeholder:text-zinc-600 resize-none leading-relaxed scrollbar-small"
                placeholder="Write custom system notes or documentation here..."
              />
            ) : (
              <div className="prose prose-invert max-w-none text-xs text-zinc-300 leading-relaxed font-sans whitespace-pre-wrap select-text">
                {activeDoc.content}
              </div>
            )}
          </div>

          <div className="flex justify-between items-center pt-3 border-t border-white/5 text-[10px] font-mono text-zinc-500">
            <span>JARVIS SYSTEM DOCUMENTATION v4.1</span>
            <span style={{ color: primaryColor }}>READY TO EXPORT</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DigitalDocsModule
