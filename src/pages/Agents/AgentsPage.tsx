import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  RiRobotLine,
  RiSendPlaneFill,
  RiInboxArchiveLine,
  RiRefreshLine,
  RiCheckDoubleLine,
  RiCloseCircleLine,
  RiTimeLine,
  RiTerminalBoxLine,
  RiFolder2Line,
  RiSearchLine,
  RiCompass3Line
} from 'react-icons/ri';
import {
  gatewayClient,
  AgentInfo,
  InboxTask,
  AgentExecutionResult
} from '@/lib/gateway-client';

export const AgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [inboxTasks, setInboxTasks] = useState<InboxTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<InboxTask | null>(null);
  const [goalInput, setGoalInput] = useState<string>('');
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [executionResult, setExecutionResult] = useState<AgentExecutionResult | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      if (autoRefresh) {
        fetchInbox(false);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const fetchData = async () => {
    const [agentList, tasks] = await Promise.all([
      gatewayClient.getAgents(),
      gatewayClient.getInboxTasks()
    ]);
    setAgents(agentList);
    setInboxTasks(tasks);
  };

  const fetchInbox = async (showLoading: boolean = false) => {
    const tasks = await gatewayClient.getInboxTasks();
    setInboxTasks(tasks);
  };

  const handleExecuteGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalInput.trim() || isExecuting) return;

    setIsExecuting(true);
    setExecutionResult(null);

    const res = await gatewayClient.executeAgentGoal(goalInput);
    setExecutionResult(res);
    setIsExecuting(false);
    await fetchInbox();
  };

  const getAgentIcon = (name: string) => {
    if (name.includes('research')) return <RiSearchLine className="text-cyan-400" />;
    if (name.includes('file')) return <RiFolder2Line className="text-amber-400" />;
    if (name.includes('planning')) return <RiCompass3Line className="text-emerald-400" />;
    return <RiRobotLine className="text-purple-400" />;
  };

  const getStatusBadge = (status: string) => {
    if (status === 'COMPLETED')
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
          <RiCheckDoubleLine /> COMPLETED
        </span>
      );
    if (status === 'RUNNING')
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 flex items-center gap-1">
          <RiTimeLine className="animate-spin" /> RUNNING
        </span>
      );
    if (status === 'FAILED')
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-red-500/15 text-red-400 border border-red-500/30 flex items-center gap-1">
          <RiCloseCircleLine /> FAILED
        </span>
      );
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-zinc-500/15 text-zinc-400 border border-zinc-500/30">
        PENDING
      </span>
    );
  };

  return (
    <div className="flex h-full w-full bg-zinc-950/60 backdrop-blur-md text-zinc-100 overflow-hidden font-sans select-none">
      {/* Main Orchestration & Inbox Column */}
      <div className="flex-1 flex flex-col h-full border-r border-white/5 overflow-hidden">
        {/* Top Header */}
        <div className="p-4 border-b border-white/5 flex items-center justify-between bg-zinc-950/40">
          <div className="flex items-center gap-3">
            <RiCompass3Line className="text-emerald-400 text-2xl" />
            <div>
              <h2 className="text-sm font-bold text-zinc-100 tracking-wider uppercase">
                HERMES MULTI-AGENT ORCHESTRATION & INBOX
              </h2>
              <p className="text-[10px] font-mono text-zinc-400">
                Context-isolated subagent execution with structured task inbox routing
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono">
            <button
              onClick={() => setAutoRefresh((p) => !p)}
              className={`px-3 py-1.5 rounded-lg border text-xs transition-all cursor-pointer ${
                autoRefresh
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : 'bg-white/5 text-zinc-500 border-white/10'
              }`}
            >
              Inbox Poll: {autoRefresh ? 'ACTIVE' : 'PAUSED'}
            </button>
            <button
              onClick={() => fetchInbox(true)}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 transition-all cursor-pointer"
            >
              <RiRefreshLine />
            </button>
          </div>
        </div>

        {/* Goal Execution Input Bar */}
        <div className="p-4 border-b border-white/5 bg-zinc-900/30">
          <form onSubmit={handleExecuteGoal} className="flex items-center gap-3">
            <div className="flex-1 relative flex items-center">
              <RiRobotLine className="absolute left-3.5 text-zinc-500 text-base" />
              <input
                type="text"
                value={goalInput}
                onChange={(e) => setGoalInput(e.target.value)}
                placeholder="Dispatch complex goal to Planning Orchestrator (e.g. 'Search the web for quantum algorithms and summarize')..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-zinc-900/80 border border-white/10 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <button
              type="submit"
              disabled={isExecuting || !goalInput.trim()}
              className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-zinc-950 text-xs font-mono font-bold transition-all shadow-[0_0_20px_rgba(16,185,129,0.25)] flex items-center gap-2 cursor-pointer"
            >
              {isExecuting ? <RiRefreshLine className="animate-spin" /> : <RiSendPlaneFill />}
              {isExecuting ? 'Planning...' : 'Dispatch'}
            </button>
          </form>

          {/* Goal Execution Live Output */}
          {executionResult && (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-3 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs font-mono"
            >
              <div className="flex items-center justify-between text-[11px] text-emerald-400 font-bold mb-1">
                <span>Orchestrator Result ({executionResult.agent_name})</span>
                <span>Delegated: {executionResult.output_data?.delegated_agent || 'direct'}</span>
              </div>
              <div className="text-zinc-200 whitespace-pre-wrap">{executionResult.summary}</div>
            </motion.div>
          )}
        </div>

        {/* Active Agents Horizontal Roster */}
        <div className="p-4 border-b border-white/5 bg-zinc-950/20">
          <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block mb-2">
            Active Subagent Roster
          </span>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {agents.map((ag) => (
              <div
                key={ag.name}
                className="p-3 rounded-xl bg-zinc-900/40 border border-white/5 flex flex-col justify-between"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <div className="p-1.5 rounded-lg bg-white/5 border border-white/10 text-sm">
                    {getAgentIcon(ag.name)}
                  </div>
                  <span className="text-xs font-mono font-bold text-zinc-200">{ag.name}</span>
                </div>
                <p className="text-[10px] text-zinc-400 line-clamp-2 leading-relaxed">
                  {ag.description}
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {ag.allowed_tools.length === 0 ? (
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-mono bg-white/5 text-zinc-500">
                      reasoning-only
                    </span>
                  ) : (
                    ag.allowed_tools.map((t) => (
                      <span
                        key={t}
                        className="px-1.5 py-0.5 rounded text-[8px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      >
                        {t}
                      </span>
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Subagent Task Inbox Table */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <div className="flex items-center justify-between pb-2">
            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
              <RiInboxArchiveLine className="text-emerald-400" /> Subagent Task Inbox ({inboxTasks.length})
            </span>
          </div>

          {inboxTasks.length === 0 ? (
            <div className="h-48 flex flex-col items-center justify-center text-center p-8 opacity-60">
              <RiInboxArchiveLine className="text-4xl text-zinc-600 mb-2" />
              <p className="text-xs text-zinc-400 font-mono">No subagent tasks recorded in inbox yet.</p>
            </div>
          ) : (
            inboxTasks.map((t) => (
              <motion.div
                key={t.task_id}
                onClick={() => setSelectedTask(t)}
                whileHover={{ scale: 1.005 }}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                  selectedTask?.task_id === t.task_id
                    ? 'bg-emerald-500/10 border-emerald-500/40 shadow-lg'
                    : 'bg-zinc-900/40 hover:bg-white/5 border-white/5'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-white/5 border border-white/10">
                    {getAgentIcon(t.agent_name)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-zinc-200">{t.agent_name}</span>
                      {getStatusBadge(t.status)}
                    </div>
                    <div className="text-[11px] text-zinc-400 font-mono mt-0.5 truncate max-w-md">
                      Task: {JSON.stringify(t.input_payload)}
                    </div>
                  </div>
                </div>

                <div className="text-right flex flex-col items-end gap-1">
                  <span className="text-[10px] font-mono text-zinc-400">
                    Artifacts: {t.artifacts.length}
                  </span>
                  <span className="text-[9px] font-mono text-zinc-500">
                    {new Date(t.created_at * 1000).toLocaleTimeString()}
                  </span>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* Task & Artifact Inspector Drawer */}
      <div className="w-96 p-5 bg-zinc-950/80 flex flex-col justify-between overflow-y-auto">
        {selectedTask ? (
          <div className="space-y-4">
            <div className="border-b border-white/5 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-wider text-emerald-400 uppercase">
                TASK INBOX INSPECTOR
              </h3>
              <p className="text-[10px] font-mono text-zinc-500 mt-0.5 truncate">
                ID: {selectedTask.task_id}
              </p>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">Assigned Agent</span>
              <div className="text-xs font-mono font-bold text-zinc-200 mt-0.5 flex items-center gap-1.5">
                {getAgentIcon(selectedTask.agent_name)} {selectedTask.agent_name}
              </div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">Status</span>
              <div className="mt-1">{getStatusBadge(selectedTask.status)}</div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">Input Payload</span>
              <div className="mt-1 p-3 rounded-xl bg-zinc-900/90 border border-white/5 font-mono text-[11px] text-zinc-300 max-h-36 overflow-y-auto whitespace-pre-wrap">
                {JSON.stringify(selectedTask.input_payload, null, 2)}
              </div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">Output Payload</span>
              <div className="mt-1 p-3 rounded-xl bg-zinc-900/90 border border-white/5 font-mono text-[11px] text-zinc-300 max-h-40 overflow-y-auto whitespace-pre-wrap">
                {JSON.stringify(selectedTask.output_payload, null, 2)}
              </div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">
                Inbox Artifacts ({selectedTask.artifacts.length})
              </span>
              <div className="mt-1 p-3 rounded-xl bg-zinc-900/90 border border-white/5 font-mono text-[11px] text-zinc-300 max-h-48 overflow-y-auto whitespace-pre-wrap">
                {JSON.stringify(selectedTask.artifacts, null, 2)}
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-50 p-6">
            <RiInboxArchiveLine className="text-3xl text-zinc-600 mb-2" />
            <p className="text-xs text-zinc-400 font-mono">
              Select a task from the Hermes inbox to inspect payload and subagent artifacts.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentsPage;
