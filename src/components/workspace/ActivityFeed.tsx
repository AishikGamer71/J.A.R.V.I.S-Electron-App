import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  RiHistoryLine,
  RiShieldCheckLine,
  RiCheckLine,
  RiCloseLine,
  RiRefreshLine,
  RiAlertLine,
  RiArrowDownSLine,
  RiArrowRightSLine,
  RiTerminalBoxLine,
  RiTimeLine,
  RiCodeSSlashLine
} from 'react-icons/ri'
import { gatewayClient, AuditLogEntry } from '@/lib/gateway-client'
import { useSettingsStore } from '@/store/settings-store'
import { hexToRgba } from '@/services/theme-manager'

export const ActivityFeed: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const theme = useSettingsStore((s) => s.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  const fetchLogs = useCallback(async (showSpinner: boolean = false) => {
    if (showSpinner) setIsLoading(true)
    try {
      const data = await gatewayClient.getAuditLogs(50, 0)
      if (Array.isArray(data)) {
        setLogs(data)
      }
    } catch (err) {
      console.error('[ActivityFeed] Failed to fetch audit logs:', err)
    } finally {
      if (showSpinner) setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLogs(true)
    const interval = setInterval(() => {
      fetchLogs(false)
    }, 3000)
    return () => clearInterval(interval)
  }, [fetchLogs])

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  const formatTimestamp = (ts: number): string => {
    if (!ts) return '--:--:--'
    // Support both second and millisecond unix timestamps
    const date = ts > 1e11 ? new Date(ts) : new Date(ts * 1000)
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  }

  const getRiskBadge = (risk: string) => {
    const upper = (risk || '').toUpperCase()
    let colorClass = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
    if (upper === 'CRITICAL') {
      colorClass = 'bg-red-500/15 text-red-400 border-red-500/30'
    } else if (upper === 'HIGH') {
      colorClass = 'bg-amber-500/15 text-amber-400 border-amber-500/30'
    } else if (upper === 'MEDIUM') {
      colorClass = 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30'
    } else if (upper === 'LOW') {
      colorClass = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
    }

    return (
      <span
        className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold tracking-wider border ${colorClass}`}
      >
        {upper || 'LOW'}
      </span>
    )
  }

  const getOutcomeBadge = (outcome: string) => {
    const upper = (outcome || '').toUpperCase()
    if (upper === 'SUCCESS' || upper === 'ALLOWED') {
      return (
        <span className="flex items-center gap-1 text-[10px] font-mono font-semibold text-emerald-400">
          <RiCheckLine className="text-xs" />
          <span>SUCCESS</span>
        </span>
      )
    }
    if (
      upper.includes('BLOCKED') ||
      upper.includes('DENIED') ||
      upper === 'FAILURE' ||
      upper === 'FAILED'
    ) {
      return (
        <span className="flex items-center gap-1 text-[10px] font-mono font-semibold text-red-400">
          <RiCloseLine className="text-xs" />
          <span>{upper.replace('BLOCKED_', '') || 'BLOCKED'}</span>
        </span>
      )
    }
    return (
      <span className="flex items-center gap-1 text-[10px] font-mono font-semibold text-amber-400">
        <RiAlertLine className="text-xs" />
        <span>{upper}</span>
      </span>
    )
  }

  return (
    <div className="flex flex-col h-full w-full bg-zinc-950/60 backdrop-blur-md border-l border-white/5 text-zinc-100 overflow-hidden font-sans select-none">
      {/* Header */}
      <div className="p-3 border-b border-white/5 flex items-center justify-between bg-zinc-950/40 flex-shrink-0">
        <div className="flex items-center gap-2">
          <RiHistoryLine style={{ color: primaryColor }} className="text-base flex-shrink-0" />
          <div>
            <h2 className="text-xs font-mono font-bold text-zinc-100 tracking-wider uppercase">
              ACTIVITY FEED
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Live pulse indicator */}
          <div
            className="flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[9px] font-mono font-bold tracking-widest"
            style={{
              backgroundColor: hexToRgba(primaryColor, 0.1),
              borderColor: hexToRgba(primaryColor, 0.25),
              color: primaryColor
            }}
          >
            <span className="relative flex h-1.5 w-1.5">
              <span
                className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                style={{ backgroundColor: primaryColor }}
              />
              <span
                className="relative inline-flex rounded-full h-1.5 w-1.5"
                style={{ backgroundColor: primaryColor }}
              />
            </span>
            <span>LIVE</span>
          </div>

          {/* Refresh button */}
          <button
            onClick={() => fetchLogs(true)}
            className="p-1 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-400 hover:text-zinc-200 transition-all cursor-pointer"
            title="Refresh logs"
          >
            <RiRefreshLine className={`text-xs ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Entries List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 opacity-60">
            <RiShieldCheckLine className="text-4xl text-zinc-600 mb-2" />
            <p className="text-xs font-mono text-zinc-400">No activity recorded yet</p>
          </div>
        ) : (
          logs.map((log) => {
            const isExpanded = expandedId === log.id
            return (
              <motion.div
                key={log.id}
                onClick={() => toggleExpand(log.id)}
                whileHover={{ scale: 1.01 }}
                className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
                  isExpanded
                    ? 'border-white/20 shadow-md'
                    : 'bg-zinc-900/40 hover:bg-white/5 border-white/5'
                }`}
                style={
                  isExpanded
                    ? {
                        backgroundColor: hexToRgba(primaryColor, 0.08),
                        borderColor: hexToRgba(primaryColor, 0.3)
                      }
                    : {}
                }
              >
                {/* Top Row: Tool Name + Risk Badge */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 truncate">
                    {isExpanded ? (
                      <RiArrowDownSLine className="text-xs text-zinc-400 flex-shrink-0" />
                    ) : (
                      <RiArrowRightSLine className="text-xs text-zinc-400 flex-shrink-0" />
                    )}
                    <RiTerminalBoxLine className="text-xs text-zinc-400 flex-shrink-0" />
                    <span className="text-xs font-mono font-bold text-zinc-200 truncate">
                      {log.tool}
                    </span>
                  </div>
                  <div className="flex-shrink-0">{getRiskBadge(log.risk_level)}</div>
                </div>

                {/* Second Row: Outcome Badge + Timestamp */}
                <div className="flex items-center justify-between mt-2 pt-1 border-t border-white/5">
                  <div>{getOutcomeBadge(log.outcome)}</div>
                  <div className="flex items-center gap-1 text-[9px] font-mono text-zinc-500">
                    <RiTimeLine className="text-[10px]" />
                    <span>{formatTimestamp(log.timestamp)}</span>
                  </div>
                </div>

                {/* Expanded Details Drawer */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.15 }}
                      className="mt-2.5 pt-2 border-t border-white/10 space-y-2 overflow-hidden"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {/* Log ID & Hash */}
                      <div className="flex items-center justify-between text-[9px] font-mono text-zinc-500">
                        <span className="truncate max-w-[120px]">ID: {log.id}</span>
                        {log.args_hash && (
                          <span className="truncate max-w-[120px]">
                            Hash: {log.args_hash.slice(0, 10)}...
                          </span>
                        )}
                      </div>

                      {/* Args Summary Payload */}
                      {log.args_summary && Object.keys(log.args_summary).length > 0 && (
                        <div>
                          <div className="flex items-center gap-1 text-[9px] font-mono uppercase text-zinc-400 mb-1">
                            <RiCodeSSlashLine className="text-[10px]" />
                            <span>Arguments</span>
                          </div>
                          <div className="p-2 rounded-lg bg-zinc-950/80 border border-white/5 font-mono text-[10px] text-zinc-300 max-h-32 overflow-y-auto whitespace-pre-wrap select-text">
                            {JSON.stringify(log.args_summary, null, 2)}
                          </div>
                        </div>
                      )}

                      {/* Execution Details if any */}
                      {log.details && Object.keys(log.details).length > 0 && (
                        <div>
                          <div className="text-[9px] font-mono uppercase text-zinc-400 mb-1">
                            Details
                          </div>
                          <div className="p-2 rounded-lg bg-zinc-950/80 border border-white/5 font-mono text-[10px] text-zinc-300 max-h-24 overflow-y-auto whitespace-pre-wrap select-text">
                            {JSON.stringify(log.details, null, 2)}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="px-3 py-2 border-t border-white/5 bg-zinc-950/40 flex items-center justify-between text-[9px] font-mono text-zinc-500 flex-shrink-0">
        <span>{logs.length} events logged</span>
        <span className="text-zinc-600">3s poll</span>
      </div>
    </div>
  )
}

export default ActivityFeed
