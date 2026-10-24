import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  RiHistoryLine,
  RiRefreshLine,
  RiShieldCheckLine,
  RiErrorWarningLine,
  RiCheckDoubleLine,
  RiCloseCircleLine,
  RiTerminalBoxLine,
  RiFilter3Line
} from 'react-icons/ri';
import { gatewayClient, AuditLogEntry } from '@/lib/gateway-client';

export const ActivityPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [filterTool, setFilterTool] = useState<string>('');
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(() => {
      if (autoRefresh) {
        fetchLogs(false);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [filterTool, autoRefresh]);

  const fetchLogs = async (showLoading: boolean = true) => {
    if (showLoading) setIsLoading(true);
    const data = await gatewayClient.getAuditLogs(100, 0, filterTool || undefined);
    setLogs(data);
    if (showLoading) setIsLoading(false);
  };

  const getRiskBadge = (risk: string) => {
    if (risk === 'CRITICAL')
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-red-500/15 text-red-400 border border-red-500/30">CRITICAL</span>;
    if (risk === 'HIGH')
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">HIGH</span>;
    if (risk === 'MEDIUM')
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">MEDIUM</span>;
    return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">LOW</span>;
  };

  const getOutcomeBadge = (outcome: string) => {
    if (outcome === 'SUCCESS')
      return (
        <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-400 font-semibold">
          <RiCheckDoubleLine /> ALLOWED / SUCCESS
        </span>
      );
    if (outcome.startsWith('BLOCKED'))
      return (
        <span className="flex items-center gap-1 text-[11px] font-mono text-red-400 font-semibold">
          <RiCloseCircleLine /> {outcome.replace('BLOCKED_', 'BLOCKED: ')}
        </span>
      );
    return (
      <span className="flex items-center gap-1 text-[11px] font-mono text-amber-400 font-semibold">
        <RiErrorWarningLine /> {outcome}
      </span>
    );
  };

  return (
    <div className="flex h-full w-full bg-zinc-950/60 backdrop-blur-md text-zinc-100 overflow-hidden font-sans select-none">
      {/* Audit Log Table Area */}
      <div className="flex-1 flex flex-col h-full border-r border-white/5 overflow-hidden">
        {/* Header Bar */}
        <div className="p-4 border-b border-white/5 flex items-center justify-between bg-zinc-950/40">
          <div className="flex items-center gap-3">
            <RiHistoryLine className="text-emerald-400 text-xl" />
            <div>
              <h2 className="text-sm font-bold text-zinc-100 tracking-wider uppercase">
                SECURITY & TOOL AUDIT TRAIL
              </h2>
              <p className="text-[10px] font-mono text-zinc-400">
                Append-only record of all tool invocations & permission checks
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono">
            <button
              onClick={() => setAutoRefresh((prev) => !prev)}
              className={`px-3 py-1.5 rounded-lg border text-xs transition-all cursor-pointer ${
                autoRefresh
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : 'bg-white/5 text-zinc-500 border-white/10'
              }`}
            >
              Auto-stream: {autoRefresh ? 'LIVE' : 'PAUSED'}
            </button>
            <button
              onClick={() => fetchLogs(true)}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 transition-all cursor-pointer"
            >
              <RiRefreshLine className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Filter Input */}
        <div className="p-3 border-b border-white/5 bg-zinc-900/20 flex items-center gap-3">
          <RiFilter3Line className="text-zinc-500 text-sm" />
          <input
            type="text"
            value={filterTool}
            onChange={(e) => setFilterTool(e.target.value)}
            placeholder="Filter by tool name (e.g. write_file, web_search)..."
            className="flex-1 bg-transparent text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none"
          />
          <span className="text-[10px] font-mono text-zinc-500">
            Total entries: {logs.length}
          </span>
        </div>

        {/* Table Content */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {logs.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-60">
              <RiShieldCheckLine className="text-4xl text-zinc-600 mb-2" />
              <p className="text-xs text-zinc-400 font-mono">No audit entries recorded yet.</p>
            </div>
          ) : (
            logs.map((log) => (
              <motion.div
                key={log.id}
                onClick={() => setSelectedLog(log)}
                whileHover={{ scale: 1.005 }}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                  selectedLog?.id === log.id
                    ? 'bg-emerald-500/10 border-emerald-500/40 shadow-lg'
                    : 'bg-zinc-900/40 hover:bg-white/5 border-white/5'
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded-lg bg-white/5 border border-white/10 text-zinc-300">
                    <RiTerminalBoxLine className="text-base" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-zinc-200">{log.tool}</span>
                      {getRiskBadge(log.risk_level)}
                    </div>
                    <div className="text-[11px] text-zinc-400 font-mono mt-0.5 truncate max-w-md">
                      Hash: {log.args_hash}
                    </div>
                  </div>
                </div>

                <div className="text-right flex flex-col items-end gap-1">
                  {getOutcomeBadge(log.outcome)}
                  <span className="text-[9px] font-mono text-zinc-500">
                    {new Date(log.timestamp * 1000).toLocaleTimeString()}
                  </span>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* Inspector Drawer */}
      <div className="w-96 p-5 bg-zinc-950/80 flex flex-col justify-between overflow-y-auto">
        {selectedLog ? (
          <div className="space-y-4">
            <div className="border-b border-white/5 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-wider text-emerald-400 uppercase">
                ENTRY INSPECTOR
              </h3>
              <p className="text-[10px] font-mono text-zinc-500 mt-0.5">ID: {selectedLog.id}</p>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">Tool</span>
              <div className="text-xs font-mono font-bold text-zinc-200 mt-0.5">
                {selectedLog.tool}
              </div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">Risk Tier</span>
              <div className="mt-1">{getRiskBadge(selectedLog.risk_level)}</div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">Outcome</span>
              <div className="mt-1">{getOutcomeBadge(selectedLog.outcome)}</div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">Timestamp</span>
              <div className="text-xs font-mono text-zinc-300 mt-0.5">
                {new Date(selectedLog.timestamp * 1000).toLocaleString()}
              </div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">
                Arguments Payload
              </span>
              <div className="mt-1 p-3 rounded-xl bg-zinc-900/90 border border-white/5 font-mono text-[11px] text-zinc-300 max-h-48 overflow-y-auto whitespace-pre-wrap">
                {JSON.stringify(selectedLog.args_summary, null, 2)}
              </div>
            </div>

            {Object.keys(selectedLog.details || {}).length > 0 && (
              <div>
                <span className="text-[10px] font-mono uppercase text-zinc-500">
                  Execution Details
                </span>
                <div className="mt-1 p-3 rounded-xl bg-zinc-900/90 border border-white/5 font-mono text-[11px] text-zinc-300 max-h-36 overflow-y-auto whitespace-pre-wrap">
                  {JSON.stringify(selectedLog.details, null, 2)}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-50 p-6">
            <RiShieldCheckLine className="text-3xl text-zinc-600 mb-2" />
            <p className="text-xs text-zinc-400 font-mono">
              Select an audit entry from the log table to inspect details.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ActivityPage;
