import React, { useState, useEffect, useMemo, memo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Menu,
  LayoutGrid,
  Activity,
  Gauge,
  Users,
  List,
  Settings,
  PlaySquare,
  XCircle,
  Leaf,
  MoreHorizontal,
  ChevronRight,
  ChevronDown,
  Monitor
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Virtuoso } from 'react-virtuoso'

// --- Interfaces ---
interface ProcessChild {
  pid: number
  cpu: number
  mem: number
  user: string
}

interface Process {
  name: string
  pid: number
  cpu: number
  mem: number
  user: string
  path: string
  children: ProcessChild[]
}

interface SystemLoad {
  cpu: string
  memory: string
  memoryUsedGb: string
  memoryTotalGb: string
}

const getHeatmap = (val: number, max: number) => {
  if (val <= 0) return 'transparent'
  const intensity = Math.min(1, val / max)
  if (val > 30 && max === 100) return `rgba(239, 68, 68, 0.4)` // Red for high CPU
  return `rgba(16, 185, 129, ${0.1 + intensity * 0.4})` // Emerald theme heatmap
}

// --- Memoized Row Components for Extreme Performance ---
const ParentRow = memo(({ proc, isExpanded, onToggle, onKill }: any) => {
  const hasChildren = proc.children.length > 1
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="group grid grid-cols-[3fr_1fr_1fr_1fr_1fr_1fr] gap-4 px-5 py-1 items-center hover:bg-emerald-500/10 cursor-default text-[12px] rounded-sm transition-colors border border-transparent hover:border-emerald-500/20">
      <div className="flex items-center gap-2 overflow-hidden pr-2">
        {hasChildren ? (
          <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }} onClick={() => onToggle(proc.name)} className="p-0.5 rounded hover:bg-emerald-500/20 text-emerald-500/70 cursor-pointer transition-colors">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </motion.button>
        ) : <div className="w-[18px]" />}
        <Monitor size={14} className="text-emerald-400 shrink-0 drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]" />
        <span className="truncate text-zinc-100 font-medium">{proc.name} {hasChildren && `(${proc.children.length})`}</span>
      </div>
      <div className="text-emerald-400 text-[11px] opacity-0 group-hover:opacity-100 transition-opacity">
        <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={(e) => { e.stopPropagation(); onKill(proc.pid); }} className="text-red-400 font-bold bg-red-500/10 hover:bg-red-500 hover:text-white px-2 rounded cursor-pointer transition-colors">KILL</motion.button>
      </div>
      <div className="text-right pr-4 py-1 rounded" style={{ backgroundColor: getHeatmap(proc.cpu, 100) }}>{proc.cpu.toFixed(1)}%</div>
      <div className="text-right pr-4 py-1 rounded" style={{ backgroundColor: getHeatmap(proc.mem, 2000) }}>{proc.mem.toFixed(1)} MB</div>
      <div className="text-right pr-4 py-1 text-zinc-500">0 MB/s</div>
      <div className="text-right pr-4 py-1 text-zinc-500">0 Mbps</div>
    </motion.div>
  )
})

const ChildRow = memo(({ proc, child }: any) => (
  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="grid grid-cols-[3fr_1fr_1fr_1fr_1fr_1fr] gap-4 px-5 py-0.5 items-center hover:bg-emerald-500/5 cursor-default text-[12px] transition-colors">
    <div className="flex items-center gap-2 overflow-hidden pl-10 pr-2">
      <Monitor size={12} className="text-emerald-500/50 shrink-0" />
      <span className="truncate text-zinc-400">{proc.name}</span>
    </div>
    <div className="text-emerald-500/70 text-[11px] truncate uppercase tracking-widest">{child.user}</div>
    <div className="text-right pr-4 rounded" style={{ backgroundColor: getHeatmap(child.cpu, 100) }}>{child.cpu === 0 ? '0%' : `${child.cpu.toFixed(1)}%`}</div>
    <div className="text-right pr-4 rounded" style={{ backgroundColor: getHeatmap(child.mem, 2000) }}>{child.mem.toFixed(1)} MB</div>
    <div className="text-right pr-4 text-zinc-600">0 MB/s</div>
    <div className="text-right pr-4 text-zinc-600">0 Mbps</div>
  </motion.div>
))

const DetailRow = memo(({ child }: any) => (
  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="grid grid-cols-[2fr_1fr_1fr_1fr_2fr] gap-4 px-5 py-1.5 items-center hover:bg-emerald-500/10 text-[12px] text-zinc-200 border-b border-emerald-500/10 transition-colors">
    <div className="truncate flex items-center gap-2 text-zinc-300"><Monitor size={14} className="text-emerald-500/70"/> Process</div>
    <div className="text-zinc-500 font-mono">{child.pid}</div>
    <div className="text-emerald-400 font-semibold tracking-wider uppercase text-[10px]">Running</div>
    <div className="text-zinc-500 uppercase tracking-widest text-[10px]">{child.user}</div>
    <div className="text-right w-20 text-emerald-300">{child.mem.toFixed(1)} K</div>
  </motion.div>
))

const ServiceRow = memo(({ srv }: any) => (
  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="grid grid-cols-[2fr_1fr_1fr_1fr] gap-4 px-5 py-1.5 items-center hover:bg-emerald-500/10 text-[12px] text-zinc-200 border-b border-emerald-500/10 transition-colors">
    <div className="truncate flex items-center gap-2 text-zinc-300"><Settings size={14} className="text-emerald-500/70"/> {srv.name}</div>
    <div className="text-zinc-500 font-mono">{srv.pids?.join(', ')}</div>
    <div className={srv.running ? 'text-emerald-400 font-semibold tracking-wider uppercase text-[10px]' : 'text-zinc-500 uppercase tracking-wider text-[10px]'}>{srv.running ? 'Running' : 'Stopped'}</div>
    <div className="text-zinc-400 uppercase tracking-widest text-[10px]">{srv.startmode}</div>
  </motion.div>
))

const StartupRow = memo(({ app }: any) => (
  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="grid grid-cols-[1fr_2fr_2fr] gap-4 px-5 py-2 items-center hover:bg-emerald-500/10 text-[12px] text-zinc-200 border-b border-emerald-500/10 transition-colors">
    <div className="truncate font-semibold text-emerald-100">{app.Name}</div>
    <div className="truncate text-emerald-500/70 font-mono">{app.Command}</div>
    <div className="truncate text-zinc-500 font-mono">{app.Location}</div>
  </motion.div>
))

export default function TaskManager() {
  const [activeTab, setActiveTab] = useState('Processes')
  const [searchTerm, setSearchTerm] = useState('')

  // Data states
  const [processes, setProcesses] = useState<Process[]>([])
  const [sysLoad, setSysLoad] = useState<SystemLoad | null>(null)
  const [startupApps, setStartupApps] = useState<any[]>([])
  const [services, setServices] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  
  // For Performance graphs
  const [cpuHistory, setCpuHistory] = useState<{ time: string, value: number }[]>([])
  const [memHistory, setMemHistory] = useState<{ time: string, value: number }[]>([])

  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({})

  // Fetch logic
  const fetchStats = async () => {
    try {
      if (activeTab === 'Processes' || activeTab === 'Details' || activeTab === 'Performance') {
        const [procRes, loadRes] = await Promise.all([
          (window as any).electron.ipcRenderer.invoke('get-processes'),
          (window as any).electron.ipcRenderer.invoke('get-system-load')
        ])
        if (loadRes.success) {
          setSysLoad(loadRes)
          const now = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
          setCpuHistory(prev => [...prev.slice(-30), { time: now, value: parseFloat(loadRes.cpu) }])
          setMemHistory(prev => [...prev.slice(-30), { time: now, value: parseFloat(loadRes.memory) }])
        }
        if (procRes.success) setProcesses(procRes.processes)
      } else if (activeTab === 'StartupApps') {
        const res = await (window as any).electron.ipcRenderer.invoke('get-startup-apps')
        if (res.success) setStartupApps(res.apps)
      } else if (activeTab === 'Services') {
        const res = await (window as any).electron.ipcRenderer.invoke('get-services')
        if (res.success) setServices(res.services)
      } else if (activeTab === 'Users') {
        const res = await (window as any).electron.ipcRenderer.invoke('get-users')
        if (res.success) setUsers(res.users)
      }
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 2000) 
    return () => clearInterval(interval)
  }, [activeTab])

  const handleKill = async (pid: number) => {
    await (window as any).electron.ipcRenderer.invoke('kill-process', pid)
    setProcesses((prev) => prev.filter((p) => p.pid !== pid))
  }

  const toggleRow = (name: string) => {
    setExpandedRows(prev => ({ ...prev, [name]: !prev[name] }))
  }

  // --- Flatten Data for Virtualization ---
  const flattenedProcesses = useMemo(() => {
    const list: any[] = []
    const sorted = processes
      .filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()))
      .sort((a, b) => b.mem - a.mem)
    
    sorted.forEach(proc => {
      list.push({ type: 'parent', proc, isExpanded: expandedRows[proc.name] || false })
      if (expandedRows[proc.name] && proc.children.length > 1) {
        proc.children.forEach(child => list.push({ type: 'child', proc, child }))
      }
    })
    return list
  }, [processes, searchTerm, expandedRows])

  const flattenedDetails = useMemo(() => {
    return processes.flatMap(p => p.children)
  }, [processes])

  const filteredStartup = useMemo(() => startupApps.filter(s => s.Name?.toLowerCase().includes(searchTerm.toLowerCase())), [startupApps, searchTerm])
  const filteredServices = useMemo(() => services.filter(s => s.name?.toLowerCase().includes(searchTerm.toLowerCase())), [services, searchTerm])

  // --- Render Helpers ---
  const SidebarItem = ({ icon: Icon, label, id }: any) => {
    const isActive = activeTab === id
    return (
      <div
        onClick={() => { setActiveTab(id); setSearchTerm(''); }}
        className={`relative flex items-center gap-4 px-4 py-3 cursor-pointer transition-all duration-300 ${
          isActive ? 'bg-emerald-500/15' : 'hover:bg-emerald-500/5'
        }`}
      >
        {isActive && <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]" />}
        <Icon size={18} className={`transition-colors ${isActive ? 'text-emerald-400' : 'text-emerald-500/50'}`} />
        <span className={`text-[13px] tracking-wide transition-colors ${isActive ? 'text-emerald-300 font-bold' : 'text-zinc-400 font-medium'}`}>
          {label}
        </span>
      </div>
    )
  }

  return (
    <div className="h-full w-full flex bg-transparent text-zinc-100 font-sans select-none overflow-hidden p-4 gap-4 animate-in fade-in duration-500">
      
      {/* LEFT SIDEBAR (Glassmorphism) */}
      <div className="w-[260px] bg-black/40 backdrop-blur-md border border-emerald-500/20 rounded-xl flex flex-col shadow-2xl overflow-hidden">
        <div className="p-4 pl-4 border-b border-emerald-500/20 bg-emerald-500/5 flex items-center gap-3">
           <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
             <LayoutGrid size={20} />
           </div>
           <h2 className="text-sm font-black tracking-widest text-emerald-400 uppercase drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]">
             Task Manager
           </h2>
        </div>
        <div className="flex-1 flex flex-col gap-0.5 mt-2">
          <SidebarItem id="Processes" icon={LayoutGrid} label="Processes" />
          <SidebarItem id="Performance" icon={Activity} label="Performance" />
          <SidebarItem id="StartupApps" icon={Gauge} label="Startup Apps" />
          <SidebarItem id="Users" icon={Users} label="Users" />
          <SidebarItem id="Details" icon={List} label="Details" />
          <SidebarItem id="Services" icon={Settings} label="Services" />
        </div>
      </div>

      {/* MAIN CONTENT AREA (Glassmorphism) */}
      <div className="flex-1 flex flex-col relative overflow-hidden bg-black/40 backdrop-blur-md border border-emerald-500/20 rounded-xl shadow-2xl">
        
        {/* Floating Search Bar */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 w-[400px] z-50">
          <div className="bg-black/60 border border-emerald-500/30 rounded-lg flex items-center px-4 py-2 shadow-[0_0_15px_rgba(16,185,129,0.1)] backdrop-blur-xl transition-all focus-within:border-emerald-400 focus-within:shadow-[0_0_20px_rgba(16,185,129,0.3)]">
            <input 
              type="text" 
              placeholder={`Search ${activeTab}...`}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-transparent border-none outline-none w-full text-[13px] text-emerald-100 placeholder:text-emerald-500/50 font-medium"
            />
          </div>
        </div>

        {/* Header Title */}
        <div className="mt-[70px] px-8 py-4 flex items-center justify-between shrink-0">
          <h1 className="text-[24px] font-black tracking-widest text-emerald-400 uppercase drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]">
            {activeTab === 'StartupApps' ? 'Startup apps' : activeTab}
          </h1>
          {activeTab === 'Processes' && (
            <div className="flex items-center gap-2">
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.95 }} className="flex items-center gap-2 px-4 py-2 text-[12px] uppercase tracking-widest font-bold bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500 hover:text-black rounded-lg transition-all border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.1)] hover:shadow-[0_0_20px_rgba(16,185,129,0.4)] cursor-pointer">
                <PlaySquare size={14} /> Run Task
              </motion.button>
            </div>
          )}
        </div>

        <AnimatePresence mode="wait">
          {activeTab === 'Processes' && (
            <motion.div key="Processes" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.2 }} className="flex-1 flex flex-col min-h-0">
              <div className="grid grid-cols-[3fr_1fr_1fr_1fr_1fr_1fr] gap-4 px-8 py-3 border-y border-emerald-500/20 bg-emerald-500/5 text-[10px] font-black uppercase tracking-widest text-emerald-500 shrink-0">
                <div className="pl-6">Name</div>
                <div>Status</div>
                <div className="flex flex-col border-l border-emerald-500/20 pl-4">
                  <span className="mb-0.5 text-emerald-300 drop-shadow-[0_0_5px_rgba(16,185,129,0.8)]">{sysLoad?.cpu || 0}%</span><span>CPU</span>
                </div>
                <div className="flex flex-col border-l border-emerald-500/20 pl-4">
                  <span className="mb-0.5 text-emerald-300 drop-shadow-[0_0_5px_rgba(16,185,129,0.8)]">{sysLoad?.memory || 0}%</span><span>Memory</span>
                </div>
                <div className="border-l border-emerald-500/20 pl-4">Disk</div>
                <div className="border-l border-emerald-500/20 pl-4">Network</div>
              </div>
              <div className="flex-1 min-h-0">
                <Virtuoso
                  style={{ height: '100%' }}
                  data={flattenedProcesses}
                  itemContent={(index, item) => {
                    if (item.type === 'parent') {
                      return <ParentRow key={item.proc.pid} proc={item.proc} isExpanded={item.isExpanded} onToggle={toggleRow} onKill={handleKill} />
                    }
                    return <ChildRow key={item.child.pid} proc={item.proc} child={item.child} />
                  }}
                />
              </div>
            </motion.div>
          )}

          {activeTab === 'Details' && (
            <motion.div key="Details" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.2 }} className="flex-1 flex flex-col min-h-0">
              <div className="grid grid-cols-[2fr_1fr_1fr_1fr_2fr] gap-4 px-8 py-3 border-y border-emerald-500/20 bg-emerald-500/5 text-[10px] font-black uppercase tracking-widest text-emerald-500 shrink-0">
                <div>Name</div><div>PID</div><div>Status</div><div>User</div><div>Memory</div>
              </div>
              <div className="flex-1 min-h-0">
                <Virtuoso
                  style={{ height: '100%' }}
                  data={flattenedDetails}
                  itemContent={(index, child) => <DetailRow key={child.pid} child={child} />}
                />
              </div>
            </motion.div>
          )}

          {activeTab === 'Services' && (
            <motion.div key="Services" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.2 }} className="flex-1 flex flex-col min-h-0">
              <div className="grid grid-cols-[2fr_1fr_1fr_1fr] gap-4 px-8 py-3 border-y border-emerald-500/20 bg-emerald-500/5 text-[10px] font-black uppercase tracking-widest text-emerald-500 shrink-0">
                <div>Name</div><div>PID</div><div>Status</div><div>Start Mode</div>
              </div>
              <div className="flex-1 min-h-0">
                <Virtuoso
                  style={{ height: '100%' }}
                  data={filteredServices}
                  itemContent={(index, srv) => <ServiceRow key={index} srv={srv} />}
                />
              </div>
            </motion.div>
          )}

          {activeTab === 'StartupApps' && (
            <motion.div key="StartupApps" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.2 }} className="flex-1 flex flex-col min-h-0">
              <div className="grid grid-cols-[1fr_2fr_2fr] gap-4 px-8 py-3 border-y border-emerald-500/20 bg-emerald-500/5 text-[10px] font-black uppercase tracking-widest text-emerald-500 shrink-0">
                <div>Name</div><div>Publisher / Command</div><div>Status (Location)</div>
              </div>
              <div className="flex-1 min-h-0">
                <Virtuoso
                  style={{ height: '100%' }}
                  data={filteredStartup}
                  itemContent={(index, app) => <StartupRow key={index} app={app} />}
                />
              </div>
            </motion.div>
          )}

          {activeTab === 'Performance' && (
            <motion.div key="Performance" initial="hidden" animate="show" exit="hidden" variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } }} className="flex-1 flex flex-col p-8 overflow-y-auto custom-scrollbar">
              <motion.h2 variants={{ hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } }} className="text-[16px] font-black tracking-widest text-emerald-400 uppercase mb-4 drop-shadow-[0_0_5px_rgba(16,185,129,0.5)] flex items-center gap-3">
                <Activity size={18} /> CPU Performance
              </motion.h2>
              <motion.div variants={{ hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } }} className="h-48 w-full bg-black/40 rounded-xl border border-emerald-500/20 p-4 mb-8 shadow-inner">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={cpuHistory}>
                    <XAxis dataKey="time" stroke="#10b981" opacity={0.5} fontSize={10} />
                    <YAxis stroke="#10b981" opacity={0.5} fontSize={10} domain={[0, 100]} />
                    <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', borderColor: '#10b981', borderRadius: '8px', backdropFilter: 'blur(10px)' }} />
                    <Line type="monotone" dataKey="value" stroke="#34d399" strokeWidth={3} dot={false} isAnimationActive={false} style={{ filter: 'drop-shadow(0px 0px 5px rgba(52,211,153,0.8))' }} />
                  </LineChart>
                </ResponsiveContainer>
              </motion.div>

              <motion.h2 variants={{ hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } }} className="text-[16px] font-black tracking-widest text-emerald-400 uppercase mb-4 drop-shadow-[0_0_5px_rgba(16,185,129,0.5)] flex items-center gap-3">
                <Gauge size={18} /> Memory Usage <span className="text-emerald-500/50 text-[12px]">({sysLoad?.memoryUsedGb} GB / {sysLoad?.memoryTotalGb} GB)</span>
              </motion.h2>
              <motion.div variants={{ hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } }} className="h-48 w-full bg-black/40 rounded-xl border border-emerald-500/20 p-4 shadow-inner">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={memHistory}>
                    <XAxis dataKey="time" stroke="#10b981" opacity={0.5} fontSize={10} />
                    <YAxis stroke="#10b981" opacity={0.5} fontSize={10} domain={[0, 100]} />
                    <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', borderColor: '#10b981', borderRadius: '8px', backdropFilter: 'blur(10px)' }} />
                    <Line type="monotone" dataKey="value" stroke="#34d399" strokeWidth={3} dot={false} isAnimationActive={false} style={{ filter: 'drop-shadow(0px 0px 5px rgba(52,211,153,0.8))' }} />
                  </LineChart>
                </ResponsiveContainer>
              </motion.div>
            </motion.div>
          )}

          {activeTab === 'Users' && (
            <motion.div key="Users" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.2 }} className="flex-1 flex flex-col min-h-0 p-8">
              <div className="text-emerald-500/50 font-black uppercase tracking-widest text-[12px] mb-6 border-b border-emerald-500/20 pb-2">Logged In Users</div>
              {users.map((u, i) => (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: i * 0.1 }} key={i} className="flex items-center gap-4 bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/20 w-96 mb-4 hover:bg-emerald-500/10 transition-colors shadow-lg">
                  <div className="p-3 bg-emerald-500/20 rounded-full border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                    <Users size={24} className="text-emerald-400" />
                  </div>
                  <div>
                    <div className="font-black text-emerald-100 text-[16px] tracking-wider">{u.user}</div>
                    <div className="text-[11px] text-emerald-400 font-bold tracking-widest uppercase mt-1 drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]">
                      Active Session • <span className="text-emerald-500/70">{u.date} {u.time}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
