import React, { useState, useEffect, Suspense, lazy } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  RiWifiLine,
  RiShieldFlashLine,
  RiLayoutGridLine,
  RiBrainLine,
  RiFolderOpenLine,
  RiPhoneLine,
  RiSettings4Line,
  RiBatteryChargeLine,
  RiCameraLine,
  RiComputerLine,
  RiCloseLine,
  RiImageLine,
  RiDashboard2Line,
  RiTerminalBoxLine
} from 'react-icons/ri'
import { getSystemStatus } from '@/services/system-info'
import { getHistory } from '@/services/jarvis-ai-brain'
import ViewSkeleton from '@/components/common/view-skeleton'

import DashboardView from '../pages/dashboard'
import PhoneView from '../pages/phone'
import { VisionMode } from '@/IndexRoot'
import { useSettingsStore } from '../store/settings-store'
import { useProfileStore } from '../store/profile-store'
import { NAVIGATION_MODULES } from '../config/navigation'
import { hexToRgba } from '@/services/theme-manager'

const WorkspaceContainer = lazy(() => import('../pages/Workspace/WorkspaceContainer'))
const ModulesPage = lazy(() => import('../pages/Modules/ModulesPage'))
import ConfirmationModal from '@/components/common/ConfirmationModal'
const AppsView = lazy(() => import('../pages/app-store'))
const TaskManagerView = lazy(() => import('../pages/task-manager'))
const NotesView = lazy(() => import('../pages/notes'))
const SettingsView = lazy(() => import('../pages/settings'))
const GalleryView = lazy(() => import('../pages/gallery'))
const TerminalView = lazy(() => import('@/components/terminal/terminal'))

interface JarvisProps {
  isSystemActive: boolean
  toggleSystem: () => void
  isMicMuted: boolean
  toggleMic: () => void
  isVideoOn: boolean
  visionMode: VisionMode
  startVision: (mode: 'camera' | 'screen') => void
  stopVision: () => void
  activeStream: MediaStream | null
}

const glassPanel = 'bg-zinc-950/40 backdrop-blur-sm border border-white/5 rounded-2xl shadow-xl glass-panel-gpu'

// Isolated clock component: re-renders only itself at 1 Hz, never the full layout
const LiveClock = React.memo(() => {
  const [timeStr, setTimeStr] = useState(() => new Date().toLocaleTimeString())
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeStr(new Date().toLocaleTimeString())
    }, 1000)
    return () => clearInterval(timer)
  }, [])
  return (
    <div className="bg-zinc-800 px-2 py-1 rounded text-zinc-300">
      {timeStr}
    </div>
  )
})

const JARVISComponent = (props: JarvisProps) => {
  const hiddenTabs = useSettingsStore((state) => state.hiddenTabs)
  const theme = useSettingsStore((state) => state.theme)
  const loadProfiles = useProfileStore((state) => state.loadProfiles)
  const [activeTab, setActiveTab] = useState('DASHBOARD')
  const [stats, setStats] = useState<any>(null)
  const [chatHistory, setChatHistory] = useState<any[]>([])
  const [showSourceModal, setShowSourceModal] = useState(false)

  const primaryColor = theme?.primaryColor || '#10b981'

  useEffect(() => {
    loadProfiles()
  }, [])

  // Poll system stats at 1 Hz without re-rendering parent components
  useEffect(() => {
    let mounted = true
    const poll = () => {
      getSystemStatus().then((s) => {
        if (mounted && s) setStats(s)
      }).catch(() => {})
    }
    poll()
    const timer = setInterval(poll, 1000)
    return () => {
      mounted = false
      clearInterval(timer)
    }
  }, [])

  // Fetch chat history with change detection to prevent render storms
  useEffect(() => {
    let mounted = true
    const fetchHistory = async () => {
      try {
        const history = await getHistory()
        if (mounted && Array.isArray(history)) {
          setChatHistory((prev) => {
            const lastPrev = prev[prev.length - 1]
            const lastNew = history[history.length - 1]
            const prevText = lastPrev?.parts?.[0]?.text ?? (lastPrev as any)?.content
            const newText = lastNew?.parts?.[0]?.text ?? (lastNew as any)?.content
            if (
              prev.length === history.length &&
              prev.length > 0 &&
              prevText === newText
            ) {
              return prev
            }
            return history.slice(-50)
          })
        }
      } catch {}
    }
    fetchHistory()
    const interval = setInterval(fetchHistory, 1500)
    window.addEventListener('jarvis-agent-response', fetchHistory)
    return () => {
      mounted = false
      clearInterval(interval)
      window.removeEventListener('jarvis-agent-response', fetchHistory)
    }
  }, [])

  useEffect(() => {
    const handleJarvisExecute = () => {
      setActiveTab('TERMINAL')
    }
    window.addEventListener('jarvis-terminal-execute', handleJarvisExecute)
    return () => window.removeEventListener('jarvis-terminal-execute', handleJarvisExecute)
  }, [])

  const handleVisionClick = () => {
    if (props.isVideoOn) {
      props.stopVision()
    } else {
      setShowSourceModal(true)
    }
  }

  return (
    <div className="h-full w-full bg-transparent text-zinc-100 font-sans overflow-hidden select-none flex flex-col relative pb-5">
      <div className="h-14 w-full flex items-center justify-between px-6 bg-zinc-950/80 border-b border-white/5 z-50 backdrop-blur-md">
        <div className="hidden lg:flex items-center gap-3">
          <RiShieldFlashLine
            className="text-xl animate-pulse"
            style={{ color: primaryColor }}
          />
          <div className="flex flex-col leading-none">
            <span className="font-black tracking-[0.2em] text-sm text-zinc-100">JARVIS AI</span>
            <span
              className="text-[11px] font-mono tracking-widest"
              style={{ color: hexToRgba(primaryColor, 0.7) }}
            >
              NEURAL INTERFACE
            </span>
          </div>
        </div>

        <div className="hidden md:flex gap-2 bg-zinc-950/40 backdrop-blur-md border border-white/10 p-1 rounded-lg shadow-xl z-[5]">
          {NAVIGATION_MODULES
            .filter((module) => !hiddenTabs.includes(module.id))
            .map((module) => {
              const isActive = activeTab === module.id
              return (
                <button
                  key={module.id}
                  onClick={() => setActiveTab(module.id)}
                  className={`relative px-4 py-1.5 rounded-md text-xs font-mono font-bold transition-all duration-300 flex items-center gap-2 cursor-pointer ${
                    isActive
                      ? 'border shadow-lg'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border border-transparent'
                  }`}
                  style={
                    isActive
                      ? {
                          color: primaryColor,
                          backgroundColor: hexToRgba(primaryColor, 0.12),
                          borderColor: hexToRgba(primaryColor, 0.35),
                          boxShadow: `0 0 15px ${hexToRgba(primaryColor, 0.2)}`
                        }
                      : {}
                  }
                >
                  {module.icon}
                  <span>{module.id}</span>
                  {isActive && (
                    <motion.div
                      layoutId="activeTabGlow"
                      className="absolute inset-0 rounded-md -z-10"
                      style={{ backgroundColor: hexToRgba(primaryColor, 0.05) }}
                      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    />
                  )}
                </button>
              )
            })}
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <button
            onClick={props.toggleSystem}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all cursor-pointer ${
              props.isSystemActive
                ? 'shadow-lg'
                : 'bg-zinc-900 border-zinc-700 text-zinc-400 hover:border-zinc-500'
            }`}
            style={
              props.isSystemActive
                ? {
                    backgroundColor: hexToRgba(primaryColor, 0.12),
                    borderColor: hexToRgba(primaryColor, 0.35),
                    color: primaryColor,
                    boxShadow: `0 0 15px ${hexToRgba(primaryColor, 0.25)}`
                  }
                : {}
            }
          >
            <div
              className={`w-2 h-2 rounded-full ${props.isSystemActive ? 'animate-ping' : 'bg-zinc-600'}`}
              style={props.isSystemActive ? { backgroundColor: primaryColor } : {}}
            />
            <span>{props.isSystemActive ? 'SYSTEM ONLINE' : 'SYSTEM STANDBY'}</span>
          </button>

          <LiveClock />
        </div>
      </div>

      <div className="flex-1 overflow-hidden relative bg-transparent">
        <AnimatePresence mode="wait">
          {activeTab === 'CHAT' && (
            <motion.div
              key="CHAT"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <WorkspaceContainer />
              </Suspense>
            </motion.div>
          )}

          {activeTab === 'MODULES' && (
            <motion.div
              key="MODULES"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <ModulesPage />
              </Suspense>
            </motion.div>
          )}

          {activeTab === 'DASHBOARD' && (
            <motion.div
              key="DASHBOARD"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <DashboardView
                props={props}
                stats={stats}
                chatHistory={chatHistory}
                onVisionClick={handleVisionClick}
              />
            </motion.div>
          )}

          {activeTab === 'PHONE' && (
            <motion.div
              key="PHONE"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <PhoneView glassPanel={glassPanel} />
            </motion.div>
          )}

          {activeTab === 'TASK MANAGER' && (
            <motion.div
              key="TASK MANAGER"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <TaskManagerView />
              </Suspense>
            </motion.div>
          )}

          {activeTab === 'Apps' && (
            <motion.div
              key="Apps"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <AppsView />
              </Suspense>
            </motion.div>
          )}

          {activeTab === 'NOTES' && (
            <motion.div
              key="NOTES"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <NotesView glassPanel={glassPanel} />
              </Suspense>
            </motion.div>
          )}

          {activeTab === 'SETTINGS' && (
            <motion.div
              key="SETTINGS"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <SettingsView isSystemActive={props.isSystemActive} />
              </Suspense>
            </motion.div>
          )}

          {activeTab === 'GALLERY' && (
            <motion.div
              key="GALLERY"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <Suspense fallback={<ViewSkeleton />}>
                <GalleryView />
              </Suspense>
            </motion.div>
          )}

          {activeTab === 'TERMINAL' && (
            <motion.div
              key="TERMINAL"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 300, damping: 30 }}
              className="absolute inset-0"
            >
              <div className="w-full h-full p-4">
                <Suspense fallback={<ViewSkeleton />}>
                  <TerminalView />
                </Suspense>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {showSourceModal && (
        <div className="absolute inset-0 z-100 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className={`${glassPanel} w-96 p-1 border-emerald-500/30 flex flex-col shadow-2xl`}>
            <div className="flex items-center justify-between p-4 border-b border-white/5 bg-white/5">
              <span className="text-xs font-bold tracking-widest text-emerald-400">
                ESTABLISH UPLINK
              </span>
              <button
                onClick={() => setShowSourceModal(false)}
                className="cursor-pointer text-zinc-500 hover:text-white"
              >
                <RiCloseLine size={18} />
              </button>
            </div>

            <div className="p-4 grid grid-cols-2 gap-4">
              <button
                onClick={() => {
                  props.startVision('camera')
                  setShowSourceModal(false)
                }}
                className="cursor-pointer group flex flex-col items-center justify-center gap-3 p-6 rounded-xl bg-black/40 border border-white/10 hover:border-emerald-500/50 hover:bg-emerald-500/10 transition-all"
              >
                <div className="p-3 rounded-full bg-zinc-900 group-hover:bg-emerald-500 text-zinc-400 group-hover:text-black transition-colors">
                  <RiCameraLine size={28} />
                </div>
                <span className="text-[10px] font-bold tracking-widest text-zinc-300 group-hover:text-emerald-400">
                  CAMERA FEED
                </span>
              </button>

              <button
                onClick={() => {
                  props.startVision('screen')
                  setShowSourceModal(false)
                }}
                className="cursor-pointer group flex flex-col items-center justify-center gap-3 p-6 rounded-xl bg-black/40 border border-white/10 hover:border-emerald-500/50 hover:bg-emerald-500/10 transition-all"
              >
                <div className="p-3 rounded-full bg-zinc-900 group-hover:bg-emerald-500 text-zinc-400 group-hover:text-black transition-colors">
                  <RiComputerLine size={28} />
                </div>
                <span className="text-[10px] font-bold tracking-widest text-zinc-300 group-hover:text-emerald-400">
                  SCREEN SHARE
                </span>
              </button>
            </div>

            <div className="p-3 bg-black/20 text-center">
              <p className="text-[9px] text-zinc-600 font-mono">
                SELECT INPUT SOURCE FOR NEURAL PROCESSING
              </p>
            </div>
          </div>
        </div>
      )}

      <ConfirmationModal />
    </div>
  )
}

export const JARVIS = React.memo(JARVISComponent)
export default JARVIS
