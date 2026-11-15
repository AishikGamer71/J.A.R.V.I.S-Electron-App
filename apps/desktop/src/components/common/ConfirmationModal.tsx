import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RiErrorWarningLine,
  RiCheckLine,
  RiCloseLine,
  RiTimeLine,
  RiTerminalBoxLine
} from 'react-icons/ri';
import { gatewayClient, ConfirmationRequest } from '@/lib/gateway-client';

export const ConfirmationModal: React.FC = () => {
  const [activeRequest, setActiveRequest] = useState<ConfirmationRequest | null>(null);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(30);

  useEffect(() => {
    const unsub = gatewayClient.onConfirmationRequest((req) => {
      setActiveRequest(req);
      setSecondsRemaining(req.timeoutSeconds || 30);
    });
    return () => {
      unsub();
    };
  }, []);

  useEffect(() => {
    if (!activeRequest) return;

    const interval = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          handleDeny();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [activeRequest]);

  const handleApprove = () => {
    if (!activeRequest) return;
    gatewayClient.sendConfirmationResponse(activeRequest.confirmationId, true);
    setActiveRequest(null);
  };

  const handleDeny = () => {
    if (!activeRequest) return;
    gatewayClient.sendConfirmationResponse(activeRequest.confirmationId, false, 'User denied');
    setActiveRequest(null);
  };

  if (!activeRequest) return null;

  const getRiskColor = (risk: string) => {
    if (risk === 'CRITICAL') return 'text-red-400 bg-red-500/10 border-red-500/30';
    if (risk === 'HIGH') return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
  };

  const progressPercent = Math.max(
    0,
    Math.min(100, (secondsRemaining / (activeRequest.timeoutSeconds || 30)) * 100)
  );

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/75 backdrop-blur-md select-none font-sans p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="w-full max-w-lg bg-zinc-950 border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="p-5 border-b border-white/5 flex items-center justify-between bg-zinc-900/60">
            <div className="flex items-center gap-3">
              <RiErrorWarningLine className="text-amber-400 text-2xl animate-pulse" />
              <div>
                <h3 className="text-sm font-bold text-zinc-100 tracking-wide">
                  SECURITY CONFIRMATION REQUIRED
                </h3>
                <p className="text-[11px] font-mono text-zinc-400">
                  JARVIS Autonomous Tool Gating Layer
                </p>
              </div>
            </div>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border ${getRiskColor(
                activeRequest.riskLevel
              )}`}
            >
              RISK: {activeRequest.riskLevel}
            </span>
          </div>

          {/* Countdown Progress Bar */}
          <div className="w-full h-1 bg-zinc-800">
            <div
              className="h-full bg-amber-500 transition-all duration-1000"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Body Content */}
          <div className="p-5 space-y-4">
            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">Tool Name</span>
              <div className="text-sm font-mono font-bold text-emerald-400 mt-0.5 flex items-center gap-2">
                <RiTerminalBoxLine /> {activeRequest.toolName}
              </div>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-zinc-500">
                Execution Parameters
              </span>
              <div className="mt-1 p-3 rounded-xl bg-zinc-900/90 border border-white/5 font-mono text-xs text-zinc-300 max-h-40 overflow-y-auto whitespace-pre-wrap break-all">
                {JSON.stringify(activeRequest.arguments, null, 2)}
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400 bg-white/5 p-3 rounded-xl">
              <span className="flex items-center gap-1.5">
                <RiTimeLine /> Auto-deny countdown:
              </span>
              <span className="text-amber-400 font-bold">{secondsRemaining}s</span>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-white/5 bg-zinc-900/40 flex items-center justify-end gap-3">
            <button
              onClick={handleDeny}
              className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-zinc-300 border border-white/10 text-xs font-mono font-semibold transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <RiCloseLine /> Deny & Block
            </button>
            <button
              onClick={handleApprove}
              className="px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-xs font-mono font-bold transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)] flex items-center gap-1.5 cursor-pointer"
            >
              <RiCheckLine /> Approve & Execute
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default ConfirmationModal;
