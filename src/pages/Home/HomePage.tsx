import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  RiCpuLine,
  RiServerLine,
  RiWifiLine,
  RiShieldCheckLine,
  RiTerminalBoxLine,
  RiFlashlightLine,
  RiBrainLine,
  RiFolderOpenLine,
  RiCompass3Line,
  RiTimeLine
} from 'react-icons/ri';
import { gatewayClient, HardwareTelemetry, NetworkStatus } from '@/lib/gateway-client';

interface HomePageProps {
  onNavigateTab: (tabId: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigateTab }) => {
  const [telemetry, setTelemetry] = useState<HardwareTelemetry>({
    cpu_percent: 0,
    ram_percent: 0,
    ram_used_gb: 0,
    ram_total_gb: 0,
    system_tier: 'mid'
  });
  const [network, setNetwork] = useState<NetworkStatus>({
    is_online: true,
    latency_ms: 15
  });
  const [isCoreConnected, setIsCoreConnected] = useState(gatewayClient.isConnected);
  const [time, setTime] = useState<Date>(new Date());

  useEffect(() => {
    const unsub = gatewayClient.onTelemetry((data) => {
      setTelemetry(data.hardware);
      setNetwork(data.network);
      setIsCoreConnected(true);
    });

    const clock = setInterval(() => {
      setTime(new Date());
      setIsCoreConnected(gatewayClient.isConnected);
      gatewayClient.pollTelemetry();
    }, 1000);

    return () => {
      unsub();
      clearInterval(clock);
    };
  }, []);

  const actionCards = [
    {
      id: 'CHAT',
      title: 'Neural Chat Stream',
      desc: 'Multi-tier autonomous conversation with local Ollama fallback',
      icon: <RiBrainLine className="text-2xl text-emerald-400" />,
      action: () => onNavigateTab('CHAT')
    },
    {
      id: 'TERMINAL',
      title: 'Command Terminal',
      desc: 'Interactive CLI terminal and shell execution environment',
      icon: <RiTerminalBoxLine className="text-2xl text-cyan-400" />,
      action: () => onNavigateTab('TERMINAL')
    },
    {
      id: 'DASHBOARD',
      title: 'Full HUD Matrix',
      desc: 'Multi-window widget dashboard, weather, stocks, and feeds',
      icon: <RiCompass3Line className="text-2xl text-amber-400" />,
      action: () => onNavigateTab('DASHBOARD')
    },
    {
      id: 'SETTINGS',
      title: 'Vault & Configuration',
      desc: 'API keys, system models, permission gates, and preferences',
      icon: <RiShieldCheckLine className="text-2xl text-indigo-400" />,
      action: () => onNavigateTab('SETTINGS')
    }
  ];

  return (
    <div className="h-full w-full bg-zinc-950/60 backdrop-blur-md text-zinc-100 p-8 overflow-y-auto font-sans select-none flex flex-col justify-between">
      {/* Header Banner */}
      <div className="flex items-center justify-between border-b border-white/5 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black tracking-widest text-zinc-100 uppercase">
              J.A.R.V.I.S COMMAND CENTER
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              v4.0 ACTIVE
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Intelligent Operating Layer • Hexagonal Architecture • Real-Time Resilience
          </p>
        </div>

        <div className="flex items-center gap-6 font-mono text-xs">
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isCoreConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'
              }`}
            />
            <span className={isCoreConnected ? 'text-emerald-400' : 'text-red-400'}>
              CORE ENGINE: {isCoreConnected ? 'LINKED (8765)' : 'STANDBY'}
            </span>
          </div>
          <div className="text-zinc-500 flex items-center gap-1.5">
            <RiTimeLine /> {time.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Telemetry HUD Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 my-6">
        {/* CPU */}
        <div className="bg-zinc-900/60 border border-white/5 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-mono font-semibold uppercase flex items-center gap-1.5">
              <RiCpuLine className="text-emerald-400 text-base" /> CPU LOAD
            </span>
            <span className="text-xs font-mono text-emerald-400">{telemetry.cpu_percent}%</span>
          </div>
          <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden mt-3">
            <div
              className="h-full bg-emerald-500 transition-all duration-500"
              style={{ width: `${Math.min(telemetry.cpu_percent, 100)}%` }}
            />
          </div>
        </div>

        {/* RAM */}
        <div className="bg-zinc-900/60 border border-white/5 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-mono font-semibold uppercase flex items-center gap-1.5">
              <RiServerLine className="text-cyan-400 text-base" /> MEMORY
            </span>
            <span className="text-xs font-mono text-cyan-400">
              {telemetry.ram_used_gb} / {telemetry.ram_total_gb} GB
            </span>
          </div>
          <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden mt-3">
            <div
              className="h-full bg-cyan-500 transition-all duration-500"
              style={{ width: `${Math.min(telemetry.ram_percent, 100)}%` }}
            />
          </div>
        </div>

        {/* System Tier */}
        <div className="bg-zinc-900/60 border border-white/5 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-mono font-semibold uppercase flex items-center gap-1.5">
              <RiFlashlightLine className="text-amber-400 text-base" /> SYSTEM TIER
            </span>
            <span className="text-xs font-mono uppercase text-amber-400 font-bold">
              {telemetry.system_tier}
            </span>
          </div>
          <p className="text-[11px] text-zinc-500 mt-2 font-mono">
            {telemetry.gpu_name ? telemetry.gpu_name : 'Local CPU Acceleration'}
          </p>
        </div>

        {/* Network */}
        <div className="bg-zinc-900/60 border border-white/5 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between text-zinc-400 mb-2">
            <span className="text-xs font-mono font-semibold uppercase flex items-center gap-1.5">
              <RiWifiLine className="text-indigo-400 text-base" /> NETWORK
            </span>
            <span
              className={`text-xs font-mono font-bold ${
                network.is_online ? 'text-indigo-400' : 'text-amber-400'
              }`}
            >
              {network.is_online ? 'ONLINE' : 'OFFLINE (OLLAMA)'}
            </span>
          </div>
          <p className="text-[11px] text-zinc-500 mt-2 font-mono">
            {network.latency_ms ? `Latency: ${network.latency_ms} ms` : 'Local Fallback Active'}
          </p>
        </div>
      </div>

      {/* Quick Launch Operations */}
      <div className="flex-1">
        <h2 className="text-xs font-mono font-bold tracking-wider text-zinc-400 uppercase mb-4">
          OPERATIONAL MODULES
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {actionCards.map((card) => (
            <motion.button
              whileHover={{ scale: 1.01, borderColor: 'rgba(16, 185, 129, 0.4)' }}
              whileTap={{ scale: 0.99 }}
              key={card.id}
              onClick={card.action}
              className="text-left p-6 rounded-2xl bg-zinc-900/40 hover:bg-zinc-900/70 border border-white/5 transition-all shadow-xl flex items-start gap-4 cursor-pointer"
            >
              <div className="p-3 rounded-xl bg-white/5 border border-white/10">{card.icon}</div>
              <div>
                <h3 className="text-sm font-bold text-zinc-200 tracking-wide">{card.title}</h3>
                <p className="text-xs text-zinc-400 mt-1 leading-relaxed">{card.desc}</p>
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Bottom Footer Status */}
      <div className="border-t border-white/5 pt-4 mt-6 flex items-center justify-between text-[11px] font-mono text-zinc-500">
        <div>AUTONOMOUS CONTROLLER: SUPERVISOR ACTIVE</div>
        <div>JARVIS AI SYSTEM OS • READY</div>
      </div>
    </div>
  );
};

export default HomePage;
