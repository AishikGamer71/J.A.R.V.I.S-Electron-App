import { lazy, Suspense } from 'react'
import { useWorkspaceStore } from '@/store/workspace-store'
import { useSettingsStore } from '@/store/settings-store'
import { hexToRgba } from '@/services/theme-manager'
import ViewSkeleton from '@/components/common/view-skeleton'
import ActivityFeed from '@/components/workspace/ActivityFeed'
import { RiLayoutRightLine, RiTeamLine } from 'react-icons/ri'

const ChatPage = lazy(() => import('@/pages/Chat/ChatPage'))

/**
 * Cowork Workspace — AI performs work with you.
 * Chat + live activity feed sidebar showing agent actions and tool executions.
 */
const CoworkWorkspace = () => {
  const { isActivityPanelOpen, toggleActivityPanel } = useWorkspaceStore()
  const theme = useSettingsStore((s) => s.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  return (
    <div className="flex flex-col h-full w-full overflow-hidden">
      {/* Toolbar */}
      <div className="h-10 flex items-center justify-between px-4 bg-zinc-950/60 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center gap-2">
          <RiTeamLine style={{ color: primaryColor }} className="text-sm" />
          <span className="text-[10px] font-mono font-bold tracking-widest text-zinc-300 uppercase">
            Cowork Mode
          </span>
          <span
            className="text-[9px] font-mono px-2 py-0.5 rounded-full border"
            style={{
              color: primaryColor,
              backgroundColor: hexToRgba(primaryColor, 0.1),
              borderColor: hexToRgba(primaryColor, 0.3)
            }}
          >
            MULTI-STEP TASK ENGINE
          </span>
        </div>

        <button
          onClick={toggleActivityPanel}
          className={`p-1.5 rounded-lg border text-xs transition-all cursor-pointer flex items-center gap-1.5 ${
            isActivityPanelOpen
              ? 'shadow-md'
              : 'bg-white/5 border-white/10 text-zinc-500 hover:text-zinc-300'
          }`}
          style={
            isActivityPanelOpen
              ? {
                  backgroundColor: hexToRgba(primaryColor, 0.12),
                  borderColor: hexToRgba(primaryColor, 0.35),
                  color: primaryColor
                }
              : {}
          }
          title="Toggle Activity Panel"
        >
          <RiLayoutRightLine className="text-sm" />
          <span className="text-[10px] font-mono">Activity</span>
        </button>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat Area */}
        <div className="flex-1 overflow-hidden">
          <Suspense fallback={<ViewSkeleton />}>
            <ChatPage />
          </Suspense>
        </div>

        {/* Activity Feed Sidebar */}
        {isActivityPanelOpen && (
          <div className="w-80 border-l border-white/5 flex-shrink-0 overflow-hidden">
            <ActivityFeed />
          </div>
        )}
      </div>
    </div>
  )
}

export default CoworkWorkspace
