import { lazy, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RiChat1Line, RiCodeSSlashLine, RiTeamLine } from 'react-icons/ri'
import { useWorkspaceStore, WorkspaceMode } from '@/store/workspace-store'
import { useSettingsStore } from '@/store/settings-store'
import { hexToRgba } from '@/services/theme-manager'
import ViewSkeleton from '@/components/common/view-skeleton'

const NormalChatWorkspace = lazy(() => import('./NormalChatWorkspace'))
const CodeWorkspace = lazy(() => import('./CodeWorkspace'))
const CoworkWorkspace = lazy(() => import('./CoworkWorkspace'))

const WORKSPACE_MODES: { id: WorkspaceMode; label: string; icon: React.ReactNode; desc: string }[] = [
  {
    id: 'chat',
    label: 'Normal Chat',
    icon: <RiChat1Line className="text-sm" />,
    desc: 'AI talks with you'
  },
  {
    id: 'code',
    label: 'Code Workspace',
    icon: <RiCodeSSlashLine className="text-sm" />,
    desc: 'AI develops software with you'
  },
  {
    id: 'cowork',
    label: 'Cowork',
    icon: <RiTeamLine className="text-sm" />,
    desc: 'AI performs work with you'
  }
]

/**
 * WorkspaceContainer — Top-level workspace host.
 * Renders a mode switcher bar and the active workspace view.
 */
const WorkspaceContainer = () => {
  const { activeMode, setActiveMode } = useWorkspaceStore()
  const theme = useSettingsStore((s) => s.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  return (
    <div className="flex flex-col h-full w-full overflow-hidden">
      {/* Mode Switcher Bar */}
      <div className="flex items-center gap-1 px-4 py-2 bg-zinc-950/70 backdrop-blur-md border-b border-white/5 flex-shrink-0">
        <div className="flex items-center bg-zinc-900/60 border border-white/10 p-0.5 rounded-lg">
          {WORKSPACE_MODES.map((mode) => {
            const isActive = activeMode === mode.id
            return (
              <button
                key={mode.id}
                onClick={() => setActiveMode(mode.id)}
                className={`relative px-4 py-2 rounded-md text-xs font-mono font-bold transition-all duration-300 flex items-center gap-2 cursor-pointer ${
                  isActive
                    ? 'text-white shadow-lg'
                    : 'text-zinc-500 hover:text-zinc-200 hover:bg-white/5'
                }`}
                style={
                  isActive
                    ? {
                        color: primaryColor,
                        backgroundColor: hexToRgba(primaryColor, 0.15),
                        boxShadow: `0 0 12px ${hexToRgba(primaryColor, 0.2)}`
                      }
                    : {}
                }
                title={mode.desc}
              >
                {mode.icon}
                <span className="hidden sm:inline">{mode.label}</span>
              </button>
            )
          })}
        </div>

        {/* Mode Description */}
        <div className="ml-3 hidden lg:flex items-center gap-2">
          <div
            className="w-1.5 h-1.5 rounded-full animate-pulse"
            style={{ backgroundColor: primaryColor }}
          />
          <span className="text-[10px] font-mono text-zinc-500">
            {WORKSPACE_MODES.find((m) => m.id === activeMode)?.desc?.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Active Workspace */}
      <div className="flex-1 overflow-hidden relative">
        <AnimatePresence mode="wait">
          {activeMode === 'chat' && (
            <motion.div
              key="workspace-chat"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2, type: 'spring', stiffness: 400, damping: 35 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <NormalChatWorkspace />
              </Suspense>
            </motion.div>
          )}

          {activeMode === 'code' && (
            <motion.div
              key="workspace-code"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2, type: 'spring', stiffness: 400, damping: 35 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <CodeWorkspace />
              </Suspense>
            </motion.div>
          )}

          {activeMode === 'cowork' && (
            <motion.div
              key="workspace-cowork"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2, type: 'spring', stiffness: 400, damping: 35 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <CoworkWorkspace />
              </Suspense>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default WorkspaceContainer
