import { lazy, Suspense } from 'react'
import { useWorkspaceStore } from '@/store/workspace-store'
import { useSettingsStore } from '@/store/settings-store'
import { hexToRgba } from '@/services/theme-manager'
import ViewSkeleton from '@/components/common/view-skeleton'
import FileExplorer from '@/components/workspace/FileExplorer'
import { RiFolderOpenLine, RiTerminalBoxLine, RiCodeSSlashLine } from 'react-icons/ri'

const ChatPage = lazy(() => import('@/pages/Chat/ChatPage'))
const Terminal = lazy(() => import('@/components/terminal/terminal'))

/**
 * Code Workspace — Split-pane development environment.
 * Left sidebar: File explorer
 * Right top: Chat interface
 * Right bottom: Integrated terminal
 */
const CodeWorkspace = () => {
  const {
    isFileExplorerOpen,
    toggleFileExplorer,
    isTerminalOpen,
    toggleTerminal,
    projectPath,
    setProjectPath
  } = useWorkspaceStore()

  const theme = useSettingsStore((s) => s.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  return (
    <div className="flex flex-col h-full w-full overflow-hidden bg-zinc-950">
      {/* Toolbar */}
      <div className="h-10 flex items-center justify-between px-4 bg-zinc-950/60 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="flex items-center gap-2 flex-shrink-0">
            <RiCodeSSlashLine style={{ color: primaryColor }} className="text-sm" />
            <span className="text-[10px] font-mono font-bold tracking-widest text-zinc-300 uppercase">
              Code Mode
            </span>
          </div>

          {/* Project Context Badge */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-[10px] font-mono max-w-xs sm:max-w-sm md:max-w-md truncate"
            style={
              projectPath
                ? {
                    color: primaryColor,
                    backgroundColor: hexToRgba(primaryColor, 0.1),
                    borderColor: hexToRgba(primaryColor, 0.3)
                  }
                : {
                    color: '#71717a',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    borderColor: 'rgba(255, 255, 255, 0.08)'
                  }
            }
            title={projectPath || 'No project open'}
          >
            <span
              className="w-1.5 h-1.5 rounded-full flex-shrink-0"
              style={{
                backgroundColor: projectPath ? primaryColor : '#71717a'
              }}
            />
            <span className="truncate">
              {projectPath ? projectPath : 'No project open'}
            </span>
          </div>
        </div>

        {/* Toggle Controls */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* File Explorer Toggle */}
          <button
            onClick={toggleFileExplorer}
            className={`p-1.5 rounded-lg border text-xs transition-all cursor-pointer flex items-center gap-1.5 ${
              isFileExplorerOpen
                ? 'shadow-md'
                : 'bg-white/5 border-white/10 text-zinc-500 hover:text-zinc-300'
            }`}
            style={
              isFileExplorerOpen
                ? {
                    backgroundColor: hexToRgba(primaryColor, 0.12),
                    borderColor: hexToRgba(primaryColor, 0.35),
                    color: primaryColor
                  }
                : {}
            }
            title="Toggle File Explorer"
          >
            <RiFolderOpenLine className="text-sm" />
            <span className="text-[10px] font-mono hidden sm:inline">Files</span>
          </button>

          {/* Terminal Toggle */}
          <button
            onClick={toggleTerminal}
            className={`p-1.5 rounded-lg border text-xs transition-all cursor-pointer flex items-center gap-1.5 ${
              isTerminalOpen
                ? 'shadow-md'
                : 'bg-white/5 border-white/10 text-zinc-500 hover:text-zinc-300'
            }`}
            style={
              isTerminalOpen
                ? {
                    backgroundColor: hexToRgba(primaryColor, 0.12),
                    borderColor: hexToRgba(primaryColor, 0.35),
                    color: primaryColor
                  }
                : {}
            }
            title="Toggle Terminal"
          >
            <RiTerminalBoxLine className="text-sm" />
            <span className="text-[10px] font-mono hidden sm:inline">Terminal</span>
          </button>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - File Explorer */}
        {isFileExplorerOpen && (
          <div className="w-64 border-r border-white/5 flex-shrink-0 overflow-hidden bg-zinc-950/40">
            <FileExplorer />
          </div>
        )}

        {/* Right Area - Chat & Terminal */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Panel - Main Chat */}
          <div className="flex-1 overflow-hidden relative">
            <Suspense fallback={<ViewSkeleton />}>
              <ChatPage />
            </Suspense>
          </div>

          {/* Bottom Panel - Terminal */}
          {isTerminalOpen && (
            <div className="h-56 border-t border-white/5 flex-shrink-0 overflow-hidden bg-zinc-950/60">
              <Suspense fallback={<ViewSkeleton />}>
                <Terminal />
              </Suspense>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CodeWorkspace
