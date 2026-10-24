import { useEffect, useCallback, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CustomSelect } from '@/components/common/custom-select'
import Sphere from '@/components/dashboard/sphere'
import { jarvisService } from '@/services/jarvis-voice-ai'
import { clearHistory, saveMessage } from '@/services/jarvis-ai-brain'
import { gatewayClient } from '@/lib/gateway-client'
import {
  RiCpuLine,
  RiCameraLine,
  RiTerminalBoxLine,
  RiSwapBoxLine,
  RiLayoutGridLine,
  RiMicLine,
  RiMicOffLine,
  RiPhoneFill,
  RiHistoryLine,
  RiPulseLine,
  RiWifiLine,
  RiServerLine,
  RiEarthLine,
  RiSendPlaneLine,
  RiAttachment2,
  RiCloseLine,
  RiFileTextLine,
  RiFileCopyLine,
  RiCheckLine,
  RiToolsLine
} from 'react-icons/ri'
import { FaMemory } from 'react-icons/fa6'
import { GiTinker } from 'react-icons/gi'
import { HiComputerDesktop } from 'react-icons/hi2'
import * as faceapi from 'face-api.js'
import { useSettingsStore } from '../store/settings-store'
import { RiBrainLine } from 'react-icons/ri'
import { VisionMode } from '@/IndexRoot'

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

interface DashboardViewProps {
  props: JarvisProps
  stats: any
  chatHistory: any[]
  onVisionClick: () => void
}

const glassPanel = 'bg-zinc-950/40 backdrop-blur-sm border border-white/5 rounded-2xl shadow-xl'


const modelGroupsBase = [
  {
    label: "Google",
    options: [
      { label: "Gemini 2.5 Pro", value: "gemini-2.5-pro" },
      { label: "Gemini 2.5 Flash", value: "gemini-2.5-flash" }
    ],
    envKey: "GEMINI_API_KEY"
  },
  {
    label: "OpenAI",
    options: [
      { label: "GPT-4o", value: "gpt-4o" },
      { label: "o1", value: "o1" },
      { label: "o3-mini", value: "o3-mini" }
    ],
    envKey: "OPENAI_API_KEY"
  },
  {
    label: "Anthropic",
    options: [
      { label: "Claude 3.7 Sonnet", value: "claude-3-7-sonnet" }
    ],
    envKey: "ANTHROPIC_API_KEY"
  },
  {
    label: "DeepSeek",
    options: [
      { label: "DeepSeek R1", value: "deepseek-r1" },
      { label: "DeepSeek V3", value: "deepseek-v3" }
    ],
    envKey: "DEEPSEEK_API_KEY"
  }
];

const reasoningOptions = [
  { label: "None", value: "none" },
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" }
];

export default function DashboardView({
  props,
  stats,
  chatHistory,
  onVisionClick
}: DashboardViewProps) {
  const {
    isSystemActive,
    isVideoOn,
    visionMode,
    startVision,
    activeStream,
    toggleMic,
    toggleSystem,
    isMicMuted
  } = props

  const scrollRef = useRef<HTMLDivElement>(null)
  const videoElementRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const faceScanInterval = useRef<NodeJS.Timeout | null>(null)

  const [modelsLoaded, setModelsLoaded] = useState(false)
  const { model, setModel, reasoningEffort, setReasoningEffort, computeMode, setComputeMode } = useSettingsStore()

  const [activeModelGroups, setActiveModelGroups] = useState(modelGroupsBase)

  useEffect(() => {
    const fetchKeys = async () => {
      try {
        let envData: Record<string, any> | null = null
        try {
          const res = await fetch('http://127.0.0.1:8765/api/env')
          if (res.ok) envData = await res.json()
        } catch {}

        const activeGroups = await Promise.all(
          modelGroupsBase.map(async (g) => {
            let key = ''
            if (envData && envData[g.envKey]) {
              key = envData[g.envKey]
            } else if (window.jarvis?.settings?.getApiKey) {
              key = (await window.jarvis.settings.getApiKey(g.label.toLowerCase())) || ''
            }
            if (!key) {
              key = localStorage.getItem('jarvis_key_' + g.label.toLowerCase()) || ''
            }
            if (g.label === 'Google') return g
            return key ? g : null
          })
        )
        const valid = activeGroups.filter(Boolean) as typeof modelGroupsBase
        if (valid.length > 0) {
          setActiveModelGroups(valid)
        }
      } catch (e) {}
    }
    fetchKeys()
  }, [])

  const [networkStats, setNetworkStats] = useState({ ping: 0, rate: 0.0, tx: 0, rx: 0 })
  const [activeTool, setActiveTool] = useState<{ tool: string; phase: 'start' | 'result' } | null>(null)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)

  useEffect(() => {
    const handleTool = (e: any) => {
      if (e.detail) {
        setActiveTool({ tool: e.detail.tool, phase: e.detail.phase })
        if (e.detail.phase === 'result') {
          setTimeout(() => setActiveTool(null), 3000)
        }
      }
    }
    window.addEventListener('jarvis-tool-call', handleTool)
    return () => window.removeEventListener('jarvis-tool-call', handleTool)
  }, [])

  const [chatInput, setChatInput] = useState('')
  const [selectedFile, setSelectedFile] = useState<{name: string, path: string} | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSendChat = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    
    if (chatInput.trim() === '/clear') {
      await clearHistory()
      setChatInput('')
      return
    }

    if (chatInput.trim() || selectedFile) {
      if (selectedFile) jarvisService.setFile(selectedFile.path)
      const text = chatInput.trim()
      if (text) {
        await saveMessage('user', text)
        jarvisService.sendTextCommand(text)
      }
      setChatInput('')
      setSelectedFile(null)
    }
  }

  useEffect(() => {
    // Delay slightly to ensure ReactMarkdown finishes rendering DOM nodes
    const timer = setTimeout(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight
      }
    }, 50)
    return () => clearTimeout(timer)
  }, [chatHistory])

  useEffect(() => {
    if (!isSystemActive) {
      setNetworkStats({ ping: 0, rate: 0.0, tx: 0, rx: 0 })
      return
    }

    const unsub = gatewayClient.onTelemetry((data) => {
      if (data.network) {
        const net = data.network as any
        const rxRateKb = net.rx_bytes_sec ? net.rx_bytes_sec / 1024 : 0
        const txRateKb = net.tx_bytes_sec ? net.tx_bytes_sec / 1024 : 0
        setNetworkStats({
          ping: net.latency_ms || 18,
          rate: parseFloat(rxRateKb.toFixed(1)),
          tx: Math.min(100, Math.round(txRateKb / 10)),
          rx: Math.min(100, Math.round(rxRateKb / 10))
        })
      }
    })

    return () => {
      unsub()
    }
  }, [isSystemActive])

  useEffect(() => {
    const loadModels = async () => {
      try {
        const MODEL_URL = './models'
        await Promise.all([
          faceapi.nets.ssdMobilenetv1.loadFromUri(MODEL_URL),
          faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL),
          faceapi.nets.ageGenderNet.loadFromUri(MODEL_URL)
        ])
        setModelsLoaded(true)
      } catch (e) {}
    }
    loadModels()
  }, [])

  useEffect(() => {
    if (
      isVideoOn &&
      visionMode === 'camera' &&
      modelsLoaded &&
      videoElementRef.current &&
      canvasRef.current
    ) {
      if (faceScanInterval.current) clearInterval(faceScanInterval.current)

      faceScanInterval.current = setInterval(async () => {
        const video = videoElementRef.current
        const canvas = canvasRef.current
        if (!video || !canvas || video.readyState !== 4 || video.videoWidth === 0) return

        try {
          const vw = video.videoWidth
          const vh = video.videoHeight

          if (canvas.width !== vw || canvas.height !== vh) {
            canvas.width = vw
            canvas.height = vh
          }

          const ctx = canvas.getContext('2d')
          if (!ctx) return

          const options = new faceapi.SsdMobilenetv1Options({ minConfidence: 0.3 })
          const detection = await faceapi
            .detectSingleFace(video, options)
            .withFaceExpressions()
            .withAgeAndGender()

          ctx.clearRect(0, 0, vw, vh)

          if (detection) {
            const { x, y, width, height } = detection.detection.box

            const mirroredX = vw - x - width

            ctx.strokeStyle = '#34d399'
            ctx.lineWidth = 4
            const l = 25

            ctx.beginPath()
            ctx.moveTo(mirroredX, y + l)
            ctx.lineTo(mirroredX, y)
            ctx.lineTo(mirroredX + l, y)
            ctx.moveTo(mirroredX + width - l, y)
            ctx.lineTo(mirroredX + width, y)
            ctx.lineTo(mirroredX + width, y + l)
            ctx.moveTo(mirroredX, y + height - l)
            ctx.lineTo(mirroredX, y + height)
            ctx.lineTo(mirroredX + l, y + height)
            ctx.moveTo(mirroredX + width - l, y + height)
            ctx.lineTo(mirroredX + width, y + height)
            ctx.lineTo(mirroredX + width, y + height - l)
            ctx.stroke()

            const expressions = detection.expressions
            const domExp = (Object.keys(expressions) as Array<keyof typeof expressions>).reduce((a, b) =>
              expressions[a] > expressions[b] ? a : b
            )
            const gender = detection.gender === 'male' ? 'M' : 'F'
            const age = Math.round(detection.age)
            const labelText = ` ID:${gender} | AGE:${age} | ${domExp.toUpperCase()} `

            ctx.fillStyle = 'rgba(10, 10, 10, 0.85)'
            ctx.fillRect(mirroredX, y - 32, width, 26)

            ctx.fillStyle = '#34d399'
            ctx.font = 'bold 16px monospace'
            ctx.fillText(labelText, mirroredX + 5, y - 14)
          } else {
            ctx.fillStyle = 'rgba(52, 211, 153, 0.8)'
            ctx.font = 'bold 14px monospace'
            ctx.fillText('SCANNING OPTICS...', 20, 30)
          }
        } catch (e) {}
      }, 1000)
    } else {
      if (faceScanInterval.current) clearInterval(faceScanInterval.current)
      const ctx = canvasRef.current?.getContext('2d')
      if (ctx) ctx.clearRect(0, 0, canvasRef.current!.width, canvasRef.current!.height)
    }

    return () => {
      if (faceScanInterval.current) clearInterval(faceScanInterval.current)
    }
  }, [isVideoOn, visionMode, modelsLoaded])

  const setVideoRef = useCallback(
    (node: HTMLVideoElement | null) => {
      videoElementRef.current = node
      if (node && activeStream && isVideoOn) {
        node.srcObject = activeStream
        node.onloadedmetadata = () => node.play().catch(() => {})
      }
    },
    [activeStream, isVideoOn, visionMode]
  )

  const setMobileVideoRef = useCallback(
    (node: HTMLVideoElement | null) => {
      if (node && activeStream && isVideoOn) {
        node.srcObject = activeStream
        node.onloadedmetadata = () => node.play().catch(() => {})
      }
    },
    [activeStream, isVideoOn, visionMode]
  )

  const toggleSource = () => {
    if (!isSystemActive) return
    const nextMode = visionMode === 'camera' ? 'screen' : 'camera'
    startVision(nextMode)
  }

  const systemMetrics = [
    {
      icon: <RiCpuLine />,
      bgIcon: <RiCpuLine size={140} />,
      label: 'CPU LOAD',
      val: isSystemActive && stats ? `${stats.cpu}%` : '--',
      raw: isSystemActive && stats ? stats.cpu : 0,
      colorClass: 'text-emerald-400',
      bgClass: 'bg-emerald-500',
      glowClass: 'via-emerald-500/50',
      shadowClass: 'shadow-[0_0_8px_#10b981]',
      bgGradient: 'from-emerald-950/30 to-black/60',
      pattern:
        'bg-[linear-linear(to_right,#10b98108_1px,transparent_1px),linear-linear(to_bottom,#10b98108_1px,transparent_1px)] bg-[size:12px_12px]'
    },
    {
      icon: <FaMemory />,
      bgIcon: <FaMemory size={140} />,
      label: 'RAM USAGE',
      val: isSystemActive && stats ? `${stats.memory.usedPercentage}%` : '--',
      raw: isSystemActive && stats ? stats.memory.usedPercentage : 0,
      colorClass: 'text-cyan-400',
      bgClass: 'bg-cyan-500',
      glowClass: 'via-cyan-500/50',
      shadowClass: 'shadow-[0_0_8px_#06b6d4]',
      bgGradient: 'from-cyan-950/30 to-black/60',
      pattern: 'bg-[radial-linear(#06b6d415_1px,transparent_1px)] bg-[size:10px_10px]'
    },
    {
      icon: <GiTinker />,
      bgIcon: <GiTinker size={140} />,
      label: 'TEMP',
      val: isSystemActive && stats ? `${stats.temperature}°C` : '--',
      raw: isSystemActive && stats ? Math.min((stats.temperature / 90) * 100, 100) : 0,
      colorClass: 'text-orange-400',
      bgClass: 'bg-orange-500',
      glowClass: 'via-orange-500/50',
      shadowClass: 'shadow-[0_0_8px_#f97316]',
      bgGradient: 'from-orange-950/30 to-black/60',
      pattern:
        'bg-[radial-linear(ellipse_at_top_right,_var(--tw-linear-stops))] from-orange-900/20 via-transparent to-transparent'
    },
    {
      icon: <HiComputerDesktop />,
      bgIcon: <HiComputerDesktop size={140} />,
      label: 'OS',
      val: isSystemActive && stats ? `${stats.os.type}` : '--',
      raw: 0,
      colorClass: 'text-purple-400',
      bgClass: 'bg-purple-500',
      glowClass: 'via-purple-500/50',
      shadowClass: '',
      bgGradient: 'from-purple-950/30 to-black/60',
      pattern:
        'bg-[linear-linear(45deg,#a855f708_25%,transparent_25%,transparent_50%,#a855f708_50%,#a855f708_75%,transparent_75%,transparent)] bg-[size:24px_24px]',
      hideBar: true
    }
  ]

  return (
    <div className="flex-1 p-4 bg-white/2 grid grid-cols-12 gap-4 h-full overflow-hidden relative animate-in fade-in zoom-in duration-300 w-full">
      
      <div className="hidden lg:flex col-span-3 flex-col gap-4 h-full z-40">
                <div className={`${glassPanel} h-70 shrink-0 flex flex-col p-4 relative group z-50`}>
          <div className="flex items-center justify-between border-b border-white/10 pb-3 mb-3">
            <span className="text-[11px] font-bold tracking-widest text-emerald-400 flex items-center gap-2">
              <RiBrainLine size={16} /> NEURAL CORE SETTINGS
            </span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_#10b981]" />
          </div>

          <div className="flex flex-col gap-5 flex-1 pr-1">
            {/* Compute Mode */}
            <div className="flex flex-col gap-2 border-b border-white/5 pb-3">
              <span className="text-[10px] text-zinc-400 font-bold tracking-widest uppercase">Compute Mode</span>
              <div className="flex gap-1.5">
                {(['local', 'cloud', 'adaptive'] as const).map(mode => (
                  <button
                    key={mode}
                    onClick={() => setComputeMode(mode as 'local'|'cloud'|'adaptive')}
                    className={`flex-1 py-1.5 rounded text-[10px] font-bold tracking-widest uppercase transition-all ${computeMode === mode ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-black/30 text-zinc-500 border border-transparent hover:bg-black/50'}`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-zinc-500 font-mono mt-2">
                Adaptive mode dynamically routes simple tasks to Local, and complex tasks to Cloud.
              </p>
            </div>

            {/* Model and Reasoning Side-by-Side */}
            <div className="flex gap-2 w-full">
              {/* Model Selection */}
              <div className="flex flex-col gap-2 flex-1 w-1/2">
                <span className="text-[10px] text-zinc-400 font-bold tracking-widest uppercase truncate">Active Model</span>
                <CustomSelect value={model} onChange={setModel} groups={activeModelGroups} />
              </div>

              {/* Reasoning Effort */}
              <div className="flex flex-col gap-2 flex-1 w-1/2">
                <span className="text-[10px] text-zinc-400 font-bold tracking-widest uppercase truncate">Reasoning</span>
                <CustomSelect value={reasoningEffort} onChange={(val) => setReasoningEffort(val as 'none'|'low'|'medium'|'high')} options={reasoningOptions} />
              </div>
            </div>
          </div>
        </div>
<div
          className={`${glassPanel} h-32 shrink-0 p-4 flex flex-col justify-between relative overflow-hidden`}
        >
          <div
            className={`absolute inset-0 bg-linear-to-r from-emerald-500/5 to-transparent transition-opacity duration-1000 ${isSystemActive ? 'opacity-100' : 'opacity-0'}`}
          />

          <div className="flex items-center justify-between border-b border-white/10 pb-2 relative z-10">
            <span className="text-[10px] font-bold tracking-widest text-zinc-400 flex items-center gap-1">
              <RiPulseLine className={isSystemActive ? 'text-emerald-500 animate-pulse' : ''} />{' '}
              NETWORK TELEMETRY
            </span>
            <span
              className={`text-[8px] px-2 py-0.5 rounded-full font-mono font-bold border ${isSystemActive ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' : 'text-zinc-600 border-zinc-800 bg-zinc-900'}`}
            >
              {isSystemActive ? 'SECURE UPLINK' : 'STANDBY'}
            </span>
          </div>

          <div className="flex items-center justify-between mt-2 relative z-10">
            <div className="flex flex-col">
              <span className="text-[8px] text-zinc-600 font-mono tracking-widest flex items-center gap-1">
                WSS LATENCY
              </span>
              <span className="text-xs font-bold text-emerald-50 font-mono flex items-center gap-1.5 transition-all">
                <RiWifiLine className={isSystemActive ? 'text-emerald-400' : 'text-zinc-600'} />
                {isSystemActive ? `${networkStats.ping}ms` : '--'}
              </span>
            </div>

            <div className="flex flex-col items-center">
              <span className="text-[8px] text-zinc-600 font-mono tracking-widest">
                PACKET RATE
              </span>
              <span className="text-xs font-bold text-emerald-50 font-mono transition-all">
                {isSystemActive ? `${networkStats.rate} MB/s` : '--'}
              </span>
            </div>

            <div className="flex flex-col items-end">
              <span className="text-[8px] text-zinc-600 font-mono tracking-widest">ROUTING</span>
              <span className="text-xs font-bold text-emerald-50 font-mono flex items-center gap-1.5">
                {isSystemActive ? 'GLOBAL' : 'LOCAL'}
                {isSystemActive ? (
                  <RiEarthLine className="text-cyan-400" />
                ) : (
                  <RiServerLine className="text-zinc-500" />
                )}
              </span>
            </div>
          </div>

          <div className="w-full flex flex-col gap-1 mt-3 relative z-10">
            <div className="flex items-center gap-2">
              <span className="text-[7px] font-mono text-zinc-500 w-3">TX</span>
              <div className="flex-1 h-1 bg-black/60 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 shadow-[0_0_8px_#10b981] transition-all duration-300 ease-out"
                  style={{ width: `${isSystemActive ? networkStats.tx : 0}%` }}
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[7px] font-mono text-zinc-500 w-3">RX</span>
              <div className="flex-1 h-1 bg-black/60 rounded-full overflow-hidden">
                <div
                  className="h-full bg-cyan-500 shadow-[0_0_8px_#06b6d4] transition-all duration-300 ease-out delay-75"
                  style={{ width: `${isSystemActive ? networkStats.rx : 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className={`${glassPanel} flex-1 p-4 flex flex-col gap-3`}>
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <span className="text-[10px] font-bold tracking-widest text-zinc-400">
              <RiLayoutGridLine className="inline mr-1" /> CORE METRICS
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 h-full pb-1">
            {systemMetrics.map((m, i) => (
              <div
                key={i}
                className={`cursor-pointer relative rounded-xl p-3 flex flex-col justify-between border border-white/5 overflow-hidden group hover:border-white/10 transition-all duration-300 bg-linear-to-br ${m.bgGradient}`}
              >
                <div
                  className={`absolute inset-0 ${m.pattern} opacity-30 group-hover:opacity-60 transition-opacity duration-500 pointer-events-none`}
                />

                <div
                  className={`absolute -bottom-8 -right-8 opacity-[0.03] group-hover:opacity-[0.08] transition-all duration-500 transform group-hover:scale-110 pointer-events-none ${m.colorClass}`}
                >
                  {m.bgIcon}
                </div>

                <div
                  className={`absolute top-0 left-0 w-full h-px bg-linear-to-r from-transparent ${m.glowClass} to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500`}
                />

                <div className="relative z-10 flex justify-between items-start text-zinc-500">
                  <span
                    className={`text-base ${m.colorClass} opacity-70 group-hover:opacity-100 transition-opacity`}
                  >
                    {m.icon}
                  </span>
                  <span className="text-[8px] font-mono tracking-widest uppercase opacity-70 group-hover:opacity-100 transition-opacity text-zinc-300">
                    {m.label}
                  </span>
                </div>

                <div className="relative z-10 flex flex-col gap-1.5 mt-2">
                  <span className="text-sm font-bold text-white text-right font-mono tracking-wider drop-shadow-md">
                    {m.val}
                  </span>

                  {!m.hideBar && (
                    <div className="w-full h-1 bg-black/40 rounded-full overflow-hidden backdrop-blur-sm border border-white/5">
                      <div
                        className={`h-full ${m.bgClass} ${m.shadowClass} transition-all duration-700 ease-out`}
                        style={{ width: isSystemActive ? `${m.raw}%` : '0%' }}
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="col-span-12 lg:col-span-6 relative flex flex-col items-center justify-center">
        <div
          className={`lg:hidden absolute top-4 right-4 w-32 h-24 ${glassPanel} z-50 overflow-hidden ${isVideoOn ? 'block' : 'hidden'}`}
        >
          <video
            ref={setMobileVideoRef}
            className={`w-full h-full object-cover ${visionMode === 'camera' ? '-scale-x-100' : ''}`}
            autoPlay
            playsInline
            muted
          />
        </div>

        

        
          <div
            className={`w-[60vh] h-[60vh] max-w-full transition-all duration-1000 ${isSystemActive ? 'opacity-100 scale-100' : 'opacity-85 scale-90 grayscale'}`}
          >
            <Sphere />
          </div>

<div className="absolute bottom-10 z-50">
          <div
            className={`${glassPanel} px-6 py-3 rounded-full flex items-center gap-6 border border-emerald-500/20 shadow-[0_0_30px_rgba(0,0,0,0.5)]`}
          >
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={onVisionClick}
              className={`cursor-pointer p-3 rounded-full transition-all ${isVideoOn ? 'bg-red-500/20 text-red-400' : 'hover:bg-white/10 text-zinc-400'}`}
            >
              {isVideoOn ? <RiSwapBoxLine size={20} /> : <RiCameraLine size={20} />}
            </motion.button>
            <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={toggleSystem} className="relative group mx-2 cursor-pointer">
              <div
                className={`cursor-pointer p-4 rounded-full border-2 transition-all duration-500 ${isSystemActive ? 'bg-emerald-500 border-emerald-400 text-black shadow-[0_0_20px_#10b981]' : 'bg-red-500/10 border-red-500/50 text-red-500'}`}
              >
                <RiPhoneFill size={24} className={isSystemActive ? 'animate-pulse' : ''} />
              </div>
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={toggleMic}
              className={`cursor-pointer p-3 rounded-full transition-all ${isMicMuted ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/10 text-emerald-400'}`}
            >
              {isMicMuted ? <RiMicOffLine size={20} /> : <RiMicLine size={20} />}
            </motion.button>
          </div>
        </div>
      </div>

      <div className="hidden lg:flex col-span-3 flex-col overflow-hidden h-full z-40">
        <div className={`${glassPanel} h-full p-4 flex flex-col`}>
          <div className="flex items-center justify-between border-b border-white/10 pb-3 mb-2">
            <span className="text-[10px] font-bold tracking-widest text-zinc-400">
              <RiTerminalBoxLine className="inline mr-1" /> TRANSCRIPT
            </span>
            <span className="text-[8px] font-mono text-emerald-500/50">LIVE-LOG</span>
          </div>
          <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-small">
            {activeTool && (
              <div className="px-3 py-1.5 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-300 font-mono text-[11px] flex items-center justify-between animate-pulse mb-2">
                <div className="flex items-center gap-2">
                  <RiToolsLine className="text-purple-400" />
                  <span>TOOL: {activeTool.tool}</span>
                </div>
                <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-purple-500/20 font-bold">{activeTool.phase}</span>
              </div>
            )}
            {chatHistory.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-zinc-700 gap-2 opacity-50">
                <RiHistoryLine size={24} />
                <span className="text-[9px] tracking-widest uppercase font-mono">
                  No Data Stream
                </span>
              </div>
            ) : (
              chatHistory.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} mb-4`}
                >
                  <div
                    className={`max-w-[95%] py-3 px-4 rounded-xl text-xs leading-relaxed border font-mono whitespace-pre-wrap break-words shadow-lg ${msg.role === 'user' ? 'bg-emerald-900/30 border-emerald-500/30 text-emerald-100 rounded-br-none' : 'bg-zinc-900/80 border-white/10 text-zinc-300 rounded-bl-none'}`}
                  >
                    <div className="flex items-center justify-between pb-1 mb-1 border-b border-white/5 text-[10px] text-zinc-500 font-mono">
                      <span>{msg.role === 'user' ? 'YOU' : 'JARVIS'}</span>
                      <button
                        onClick={() => {
                          const raw = msg.parts && msg.parts[0] ? msg.parts[0].text : msg.content
                          navigator.clipboard.writeText(raw)
                          setCopiedIdx(idx)
                          setTimeout(() => setCopiedIdx(null), 2000)
                        }}
                        className="p-1 hover:text-white transition-colors cursor-pointer"
                        title="Copy message"
                      >
                        {copiedIdx === idx ? <RiCheckLine className="text-emerald-400" /> : <RiFileCopyLine />}
                      </button>
                    </div>
                    <div className="prose prose-invert max-w-none prose-p:my-1 prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10 prose-pre:p-2 prose-pre:rounded-lg prose-code:text-emerald-400 prose-code:bg-black/30 prose-code:px-1 prose-code:rounded">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.parts && msg.parts[0] ? msg.parts[0].text : msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          
          <div className="mt-3 pt-3 border-t border-white/10 shrink-0">
            {selectedFile && (
              <div className="flex items-center justify-between bg-emerald-900/20 border border-emerald-500/20 p-2 rounded-lg mb-2">
                <div className="flex items-center gap-2 overflow-hidden">
                  <RiFileTextLine className="text-emerald-400 shrink-0" />
                  <span className="text-xs text-emerald-100/90 font-mono truncate">{selectedFile.name}</span>
                </div>
                <motion.button 
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => setSelectedFile(null)}
                  className="p-1 hover:bg-white/10 rounded-md text-zinc-400 hover:text-white transition-colors cursor-pointer"
                >
                  <RiCloseLine />
                </motion.button>
              </div>
            )}
            
            <form onSubmit={handleSendChat} className="flex gap-2 relative">
              <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    const file = e.target.files[0]
                    setSelectedFile({ name: file.name, path: (file as any).path })
                  }
                }}
              />
              <motion.button 
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className={`p-3 rounded-xl border transition-all flex items-center justify-center shrink-0 cursor-pointer ${selectedFile ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400' : 'bg-black/40 border-white/10 text-zinc-400 hover:bg-white/10 hover:text-white'}`}
              >
                <RiAttachment2 size={18} />
              </motion.button>
              
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                disabled={!isSystemActive}
                placeholder={isSystemActive ? "Message JARVIS..." : "System offline..."}
                className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-xs font-mono text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              />
              
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                type="submit"
                disabled={(!chatInput.trim() && !selectedFile) || !isSystemActive}
                className="p-3 rounded-xl bg-emerald-500 text-black font-bold flex items-center justify-center shrink-0 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-emerald-400 transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] cursor-pointer"
              >
                <RiSendPlaneLine size={18} />
              </motion.button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

