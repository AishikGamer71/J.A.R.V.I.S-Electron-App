import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import * as faceapi from 'face-api.js'
import { GiArtificialIntelligence } from 'react-icons/gi'
import {
  RiKey2Line,
  RiSave3Line,
  RiUserVoiceLine,
  RiUserLine,
  RiLockPasswordLine,
  RiScan2Line,
  RiAddLine,
  RiRecordCircleLine,
  RiLock2Line,
  RiSettings4Line,
  RiShieldKeyholeLine,
  RiBrainLine,
  RiTerminalWindowLine,
  RiRefreshLine,
  RiDownloadCloud2Line,
  RiLayoutGridLine,
  RiInformationLine,
  RiErrorWarningLine,
  RiShieldCheckLine,
  RiDeleteBin7Line,
  RiPaletteLine,
  RiCheckLine,
  RiRestartLine,
  RiSparklingLine,
  RiContrastLine
} from 'react-icons/ri'

import { useSettingsStore } from '../store/settings-store'
import { NAVIGATION_MODULES } from '../config/navigation'
import { gatewayClient } from '@/lib/gateway-client'
import {
  PRESET_THEMES,
  ThemePresetId,
  ThemeSettings,
  hexToRgba
} from '@/services/theme-manager'

interface SettingsProps {
  isSystemActive: boolean
}

type TabType =
  | 'general'
  | 'appearance'
  | 'ai'
  | 'behaviors'
  | 'keys'
  | 'permissions'
  | 'security'
  | 'about'

const SWATCH_COLORS = [
  { name: 'Emerald', hex: '#10b981' },
  { name: 'Arc Blue', hex: '#38bdf8' },
  { name: 'Cyan', hex: '#06b6d4' },
  { name: 'Purple', hex: '#a855f7' },
  { name: 'Crimson', hex: '#ef4444' },
  { name: 'Amber Gold', hex: '#f59e0b' },
  { name: 'Rose Pink', hex: '#ec4899' },
  { name: 'Pure White', hex: '#ffffff' }
]

const BG_TONES = [
  { name: 'Obsidian Black', hex: '#050505', desc: 'Default OLED deep dark' },
  { name: 'Midnight Navy', hex: '#030712', desc: 'Deep cosmic stark blue' },
  { name: 'Dark Carbon', hex: '#0c0a09', desc: 'Warm armor iron carbon' },
  { name: 'Pitch Black', hex: '#000000', desc: 'Zero ambient illumination' }
]

const SettingsView = ({ isSystemActive }: SettingsProps) => {
  const [activeTab, setActiveTab] = useState<TabType>('general')

  const {
    hiddenTabs,
    toggleTabVisibility,
    voice,
    setVoice,
    temperature,
    setTemperature,
    maxTokens,
    setMaxTokens,
    alwaysOnTop,
    setAlwaysOnTop,
    autoStart,
    setAutoStart,
    storagePath,
    setStoragePath,
    uiSoundEffects,
    setUiSoundEffects,
    theme,
    setTheme,
    setThemePreset,
    resetThemeToDefault
  } = useSettingsStore()

  const [selectedGender, setSelectedGender] = useState<'MALE' | 'FEMALE'>(
    ['Charon', 'Fenrir', 'Puck'].includes(voice) ? 'MALE' : 'FEMALE'
  )
  const [personality, setPersonality] = useState('')
  const [userName, setUserName] = useState(localStorage.getItem('jarvis_user_name') || '')

  const [apiKeys, setApiKeys] = useState<Record<string, string>>({})
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [isGeminiConfigured, setIsGeminiConfigured] = useState(false)

  const [isSecurityUnlocked, setIsSecurityUnlocked] = useState(false)
  const [authPin, setAuthPin] = useState('')
  const [authError, setAuthError] = useState(false)

  const [newPin, setNewPin] = useState('')
  const [faceCount, setFaceCount] = useState(0)

  const [isScanningFace, setIsScanningFace] = useState(false)
  const [enrollStatus, setEnrollStatus] = useState('')
  const videoRef = useRef<HTMLVideoElement>(null)

  const [appVersion, setAppVersion] = useState('1.1.5')
  const [updateStatus, setUpdateStatus] = useState<
    'idle' | 'checking' | 'available' | 'downloading' | 'ready' | 'error'
  >('idle')
  const [updateNotes, setUpdateNotes] = useState('No new updates detected.')
  const [downloadProgress, setDownloadProgress] = useState(0)

  useEffect(() => {
    if (window.electron?.ipcRenderer) {
      window.electron.ipcRenderer.invoke('get-personality').then((res) => {
        setPersonality(typeof res === 'string' ? res : '')
      })
      window.electron.ipcRenderer
        .invoke('check-vault-status')
        .then((res) => setFaceCount(res?.faceCount || 0))

      window.electron.ipcRenderer.invoke('get-app-version').then((v) => setAppVersion(v))

      window.electron.ipcRenderer.on('updater-event', (_e, { status, data, error }) => {
        if (status === 'checking') setUpdateStatus('checking')
        if (status === 'available') {
          setUpdateStatus('available')
          setUpdateNotes(data.releaseNotes || 'Bug fixes and performance improvements.')
        }
        if (status === 'not-available') {
          setUpdateStatus('idle')
          setUpdateNotes('System is up to date.')
        }
        if (status === 'downloading') {
          setUpdateStatus('downloading')
          setDownloadProgress(Math.round(data.percent))
        }
        if (status === 'downloaded') setUpdateStatus('ready')
        if (status === 'error') {
          setUpdateStatus('error')
          setUpdateNotes(`Error: ${error}`)
        }
      })
    }
    return () => {
      if (window.electron?.ipcRenderer)
        window.electron.ipcRenderer.removeAllListeners('updater-event')
    }
  }, [])

  useEffect(() => {
    const loadKeys = async () => {
      const keys: Record<string, string> = {}
      const providerList = [
        'gemini', 'groq', 'openai', 'anthropic', 'openrouter', 'deepseek', 'tavily', 'xai', 'hf'
      ]
      for (const p of providerList) {
        try {
          if (window.jarvis?.settings?.getApiKey) {
            const keyVal = await window.jarvis.settings.getApiKey(p)
            if (keyVal) {
              keys[p] = keyVal
              continue
            }
          }
        } catch {}
        const local = localStorage.getItem('jarvis_key_' + p)
        if (local) keys[p] = local
      }
      setApiKeys(keys)
      try {
        const health = await gatewayClient.getHealth()
        if (health && health.model_status === 'ready') {
          setIsGeminiConfigured(true)
        } else if (keys.gemini) {
          setIsGeminiConfigured(true)
        }
      } catch {}
    }
    loadKeys()
  }, [])

  const checkForUpdates = () => window.electron?.ipcRenderer?.invoke('check-for-updates')
  const downloadUpdate = () => window.electron?.ipcRenderer?.invoke('download-update')
  const installUpdate = () => window.electron?.ipcRenderer?.invoke('install-update')

  const handleVoiceChange = (v: string) => {
    if (isSystemActive) return
    setVoice(v)

    const utterance = new SpeechSynthesisUtterance('Hello there, I am JARVIS.')
    const voices = window.speechSynthesis.getVoices()
    if (voices.length > 0) {
      if (['Charon', 'Fenrir', 'Puck'].includes(v)) {
        utterance.voice =
          voices.find(
            (vo) =>
              vo.name.toLowerCase().includes('male') ||
              vo.name.toLowerCase().includes('david') ||
              vo.name.toLowerCase().includes('mark')
          ) || voices[0]
      } else {
        utterance.voice =
          voices.find(
            (vo) =>
              vo.name.toLowerCase().includes('female') ||
              vo.name.toLowerCase().includes('zira') ||
              vo.name.toLowerCase().includes('samantha')
          ) || voices[0]
      }
    }
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
  }

  const handlePersonalityChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value
    const words = text
      .trim()
      .split(/\s+/)
      .filter((w) => w.length > 0)
    if (words.length <= 150) setPersonality(text)
  }

  const savePersonality = async () => {
    if (window.electron?.ipcRenderer) {
      await window.electron.ipcRenderer.invoke('set-personality', personality)
      alert('Personality Matrix Saved Securely to OS.')
    }
  }

  const saveUserName = () => {
    localStorage.setItem('jarvis_user_name', userName)
    alert('User Designation Saved.')
  }

  const saveApiKeys = async () => {
    const providers = [
      { id: 'gemini', envKey: 'GEMINI_API_KEY' },
      { id: 'groq', envKey: 'GROQ_API_KEY' },
      { id: 'hf', envKey: 'HF_TOKEN' },
      { id: 'tavily', envKey: 'TAVILY_API_KEY' },
      { id: 'fireworks', envKey: 'FIREWORKS_API_KEY' },
      { id: 'openrouter', envKey: 'OPENROUTER_API_KEY' },
      { id: 'anthropic', envKey: 'ANTHROPIC_API_KEY' },
      { id: 'xai', envKey: 'XAI_API_KEY' },
      { id: 'deepseek', envKey: 'DEEPSEEK_API_KEY' },
      { id: 'openai', envKey: 'OPENAI_API_KEY' }
    ]

    for (const provider of providers) {
      const val = apiKeys[provider.id]
      if (val !== undefined && val !== null) {
        localStorage.setItem('jarvis_key_' + provider.id, val)
        if (window.jarvis?.settings?.saveApiKey) {
          try {
            await window.jarvis.settings.saveApiKey(provider.id, val)
          } catch (e) {
            console.warn('Could not save key via IPC:', provider.id, e)
          }
        }
        if (val) {
          try {
            await fetch('http://127.0.0.1:8765/api/env', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ key: provider.envKey, value: val })
            })
          } catch (e) {
            console.warn('Could not sync key to backend:', provider.id, e)
          }
        }
      }
    }
    if (apiKeys.gemini && apiKeys.gemini.trim().length > 0) {
      setIsGeminiConfigured(true)
    }
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3500)
  }

  const currentWordCount = (typeof personality === 'string' ? personality : '')
    .trim()
    .split(/\s+/)
    .filter((w) => w.length > 0).length

  const unlockSecurityModule = async () => {
    if (!window.electron?.ipcRenderer) return
    const isValid = await window.electron.ipcRenderer.invoke('verify-vault-pin', authPin)
    if (isValid) {
      setIsSecurityUnlocked(true)
      setAuthPin('')
    } else {
      setAuthError(true)
      setTimeout(() => setAuthError(false), 1000)
    }
  }

  const updateMasterPin = async () => {
    if (newPin.length !== 4 || !window.electron?.ipcRenderer) return
    await window.electron.ipcRenderer.invoke('setup-vault-pin', newPin)
    setNewPin('')
    alert('Master PIN Updated Successfully.')
  }

  const startFaceEnrollment = async () => {
    setIsScanningFace(true)
    setEnrollStatus('INITIALIZING CAMERA...')
    try {
      await Promise.all([
        faceapi.nets.ssdMobilenetv1.loadFromUri('./models'),
        faceapi.nets.faceLandmark68Net.loadFromUri('./models'),
        faceapi.nets.faceRecognitionNet.loadFromUri('./models')
      ])

      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        setEnrollStatus('POSITION FACE IN FRAME')

        const scanInterval = setInterval(async () => {
          if (!videoRef.current || videoRef.current.readyState !== 4) return
          const detection = await faceapi
            .detectSingleFace(videoRef.current)
            .withFaceLandmarks()
            .withFaceDescriptor()

          if (detection) {
            clearInterval(scanInterval)
            setEnrollStatus('FACE ACQUIRED. ENCRYPTING...')
            const descriptorArray = Array.from(detection.descriptor)

            if (window.electron?.ipcRenderer) {
              await window.electron.ipcRenderer.invoke('setup-vault-face', descriptorArray)
            }

            stream.getTracks().forEach((t) => t.stop())
            setIsScanningFace(false)
            setFaceCount((prev) => prev + 1)
            alert('New Biometric Identity Saved.')
          }
        }, 1000)
      }
    } catch {
      setEnrollStatus('CAMERA ERROR')
      setTimeout(() => setIsScanningFace(false), 2000)
    }
  }

  const [toolsList, setToolsList] = useState<any[]>([])
  const [permissionsList, setPermissionsList] = useState<any[]>([])

  const loadPermissionsData = async () => {
    try {
      const tools = await gatewayClient.getTools()
      const perms = await gatewayClient.getPermissions()
      setToolsList(Array.isArray(tools) ? tools : [])
      setPermissionsList(Array.isArray(perms) ? perms : [])
    } catch {
      setToolsList([])
      setPermissionsList([])
    }
  }

  useEffect(() => {
    if (activeTab === 'permissions') {
      loadPermissionsData()
    }
  }, [activeTab])

  const handleTogglePermission = async (toolName: string, currentlyGranted: boolean) => {
    if (currentlyGranted) {
      await gatewayClient.revokePermission(toolName)
    } else {
      await gatewayClient.grantPermission(toolName)
    }
    await loadPermissionsData()
  }

  const cardClass =
    'bg-black/40 backdrop-blur-md border border-emerald-500/20 p-6 md:p-8 rounded-2xl flex flex-col gap-5 hover:border-emerald-500/40 transition-all shadow-2xl'
  const inputContainerClass =
    'flex items-center bg-black/30 border border-emerald-500/20 rounded-lg px-4 py-3 focus-within:border-emerald-500/50 focus-within:bg-black/50 transition-all duration-300 w-full'
  const titleClass = 'text-sm font-semibold text-white flex items-center gap-2'

  const SETTINGS_TABS: { id: TabType; label: string; icon: any }[] = [
    { id: 'general', label: 'GENERAL', icon: <RiUserLine size={15} /> },
    { id: 'appearance', label: 'APPEARANCE', icon: <RiPaletteLine size={15} /> },
    { id: 'ai', label: 'AI PARAMETERS', icon: <RiBrainLine size={15} /> },
    { id: 'behaviors', label: 'BEHAVIORS', icon: <RiSettings4Line size={15} /> },
    { id: 'keys', label: 'API KEYS', icon: <RiKey2Line size={15} /> },
    { id: 'permissions', label: 'PERMISSIONS', icon: <RiShieldCheckLine size={15} /> },
    { id: 'security', label: 'SECURITY', icon: <RiShieldKeyholeLine size={15} /> },
    { id: 'about', label: 'ABOUT', icon: <RiInformationLine size={15} /> }
  ]

  return (
    <div className="flex-1 p-4 md:p-6 lg:p-8 flex flex-col md:flex-row h-full text-zinc-100 overflow-hidden">
      <motion.div
        className="w-full max-w-6xl mx-auto flex flex-col md:flex-row gap-6 md:gap-8 h-full"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {/* LEFT SIDEBAR */}
        <div className="w-full md:w-64 bg-black/40 backdrop-blur-md border border-emerald-500/20 rounded-2xl p-5 flex flex-col gap-6 flex-shrink-0 shadow-2xl">
          <div className="flex items-center gap-4 pb-5 border-b border-emerald-500/20">
            <div
              className="p-3 rounded-xl border flex items-center justify-center shadow-lg transition-all"
              style={{
                backgroundColor: hexToRgba(theme?.primaryColor || '#10b981', 0.1),
                borderColor: hexToRgba(theme?.primaryColor || '#10b981', 0.3)
              }}
            >
              <GiArtificialIntelligence
                size={28}
                style={{ color: theme?.primaryColor || '#10b981' }}
              />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white leading-tight">
                Command
                <br />
                Center
              </h2>
              <p className="text-[10px] text-zinc-400 font-mono mt-1.5 tracking-widest flex items-center gap-1.5 uppercase">
                <RiRecordCircleLine
                  className={isSystemActive ? 'animate-pulse' : 'text-zinc-600'}
                  style={{ color: isSystemActive ? theme?.primaryColor || '#10b981' : undefined }}
                  size={12}
                />
                {isSystemActive ? 'Online' : 'Offline'}
              </p>
            </div>
          </div>

          <div className="flex flex-row md:flex-col gap-1 overflow-x-auto md:overflow-visible pb-2 md:pb-0 scrollbar-small">
            {SETTINGS_TABS.map((tabItem) => {
              const isActive = activeTab === tabItem.id
              return (
                <button
                  key={tabItem.id}
                  onClick={() => setActiveTab(tabItem.id)}
                  className={`relative px-4 py-3 md:py-3.5 font-bold tracking-widest text-[10px] md:text-[11px] transition-all duration-300 rounded-xl w-auto md:w-full text-center md:text-left cursor-pointer overflow-hidden z-20 flex-shrink-0 flex items-center gap-2.5 ${
                    isActive
                      ? 'text-white'
                      : 'text-zinc-400 hover:text-zinc-100 hover:bg-white/5'
                  }`}
                  style={
                    isActive
                      ? {
                          color: theme?.primaryColor || '#10b981'
                        }
                      : {}
                  }
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeSettingsTab"
                      className="absolute inset-0 border backdrop-blur-md rounded-xl shadow-lg"
                      style={{
                        backgroundColor: hexToRgba(theme?.primaryColor || '#10b981', 0.15),
                        borderColor: hexToRgba(theme?.primaryColor || '#10b981', 0.4),
                        boxShadow: `0 0 15px ${hexToRgba(theme?.primaryColor || '#10b981', 0.25)}`,
                        zIndex: -1
                      }}
                      initial={false}
                      transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                    />
                  )}
                  {tabItem.icon}
                  <span>{tabItem.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* CONTENT AREA */}
        <div className="flex-1 relative overflow-y-auto scrollbar-small pr-2 md:pr-4 pb-12 min-h-[500px]">
          <AnimatePresence mode="wait">
            {/* ============================================================ */}
            {/* TAB: APPEARANCE & THEMES                                     */}
            {/* ============================================================ */}
            {activeTab === 'appearance' && (
              <motion.div
                key="appearance"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="flex flex-col gap-6 w-full"
              >
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <RiPaletteLine style={{ color: theme.primaryColor }} size={22} />
                      Appearance & Customization
                    </h3>
                    <p className="text-xs text-zinc-400 font-mono mt-1">
                      Customize software themes, HUD neon accents, background tones, and glassmorphic effects.
                    </p>
                  </div>
                  <button
                    onClick={resetThemeToDefault}
                    className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-mono text-zinc-300 hover:text-white transition-all flex items-center gap-2 cursor-pointer w-fit"
                  >
                    <RiRestartLine size={14} /> Reset Defaults
                  </button>
                </div>

                {/* Section 1: Ready-Made Theme Presets */}
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-zinc-300 uppercase tracking-widest flex items-center gap-2 font-mono">
                      <RiSparklingLine style={{ color: theme.primaryColor }} />
                      Ready-Made Theme Presets
                    </span>
                    <span className="text-[10px] font-mono text-zinc-500">
                      CURRENT: <span style={{ color: theme.primaryColor }} className="font-bold uppercase">{theme.preset}</span>
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-4">
                    {Object.values(PRESET_THEMES).map((preset) => {
                      const isSelected = theme.preset === preset.id
                      return (
                        <div
                          key={preset.id}
                          onClick={() => setThemePreset(preset.id as ThemePresetId)}
                          className={`p-5 rounded-2xl border transition-all cursor-pointer relative overflow-hidden flex flex-col justify-between gap-4 group ${
                            isSelected
                              ? 'border-2 shadow-2xl scale-[1.01]'
                              : 'bg-black/30 backdrop-blur-sm border-emerald-500/20 hover:border-emerald-500/40 hover:bg-emerald-500/5 shadow-md'
                          }`}
                          style={{
                            backgroundColor: isSelected
                              ? hexToRgba(preset.primaryColor, 0.08)
                              : undefined,
                            borderColor: isSelected
                              ? preset.primaryColor
                              : undefined,
                            boxShadow: isSelected
                              ? `0 0 25px ${hexToRgba(preset.primaryColor, 0.25)}`
                              : undefined
                          }}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              <span className="text-2xl">{preset.iconBadge}</span>
                              <div>
                                <h4 className="text-sm font-bold text-white group-hover:text-zinc-100">
                                  {preset.name}
                                </h4>
                                <span className="text-[10px] font-mono text-zinc-400">
                                  {preset.subtitle}
                                </span>
                              </div>
                            </div>
                            {isSelected && (
                              <div
                                className="w-6 h-6 rounded-full flex items-center justify-center text-black font-bold text-xs shadow-md"
                                style={{ backgroundColor: preset.primaryColor }}
                              >
                                <RiCheckLine size={14} />
                              </div>
                            )}
                          </div>

                          <p className="text-xs text-zinc-400 leading-relaxed font-sans">
                            {preset.description}
                          </p>

                          {/* Color Palette Indicators */}
                          <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                            <span className="text-[10px] font-mono text-zinc-500 uppercase mr-1">Palette:</span>
                            <div
                              className="w-5 h-5 rounded-full border border-white/20 shadow-sm"
                              style={{ backgroundColor: preset.primaryColor }}
                              title={`Primary: ${preset.primaryColor}`}
                            />
                            <div
                              className="w-5 h-5 rounded-full border border-white/20 shadow-sm"
                              style={{ backgroundColor: preset.secondaryColor }}
                              title={`Secondary: ${preset.secondaryColor}`}
                            />
                            <div
                              className="w-5 h-5 rounded-full border border-white/20 shadow-sm"
                              style={{ backgroundColor: preset.bgColor }}
                              title={`Background: ${preset.bgColor}`}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Section 2: Custom Accent & Color Palette */}
                <div className={`${cardClass} gap-6`}>
                  <div className="flex items-center justify-between border-b border-white/10 pb-3">
                    <h4 className={titleClass}>
                      <RiContrastLine style={{ color: theme.primaryColor }} size={18} />
                      Custom Color Palette
                    </h4>
                    <span className="text-[10px] font-mono text-zinc-400">FINE-TUNE HUD COLORS</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Primary Accent */}
                    <div className="flex flex-col gap-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-zinc-200">Primary Accent Glow</span>
                        <span className="text-xs font-mono font-bold" style={{ color: theme.primaryColor }}>
                          {theme.primaryColor.toUpperCase()}
                        </span>
                      </div>

                      {/* Swatches */}
                      <div className="flex flex-wrap gap-2">
                        {SWATCH_COLORS.map((swatch) => (
                          <button
                            key={swatch.hex}
                            onClick={() => setTheme({ primaryColor: swatch.hex, preset: 'custom' })}
                            className={`w-8 h-8 rounded-lg border transition-all cursor-pointer flex items-center justify-center ${
                              theme.primaryColor.toLowerCase() === swatch.hex.toLowerCase()
                                ? 'scale-110 border-white shadow-lg'
                                : 'border-white/20 hover:scale-105'
                            }`}
                            style={{ backgroundColor: swatch.hex }}
                            title={swatch.name}
                          >
                            {theme.primaryColor.toLowerCase() === swatch.hex.toLowerCase() && (
                              <RiCheckLine
                                size={14}
                                className={['#ffffff', '#f59e0b', '#38bdf8'].includes(swatch.hex) ? 'text-black' : 'text-white'}
                              />
                            )}
                          </button>
                        ))}
                      </div>

                      {/* Hex input & Color Picker */}
                      <div className="flex items-center gap-3 mt-1">
                        <input
                          type="color"
                          value={theme.primaryColor}
                          onChange={(e) => setTheme({ primaryColor: e.target.value, preset: 'custom' })}
                          className="w-10 h-10 rounded-lg cursor-pointer bg-black/50 border border-white/20 overflow-hidden"
                        />
                        <input
                          type="text"
                          value={theme.primaryColor}
                          onChange={(e) => setTheme({ primaryColor: e.target.value, preset: 'custom' })}
                          placeholder="#10b981"
                          className="bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-zinc-200 uppercase w-32 focus:border-white/30 outline-none"
                        />
                      </div>
                    </div>

                    {/* Secondary Accent */}
                    <div className="flex flex-col gap-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-zinc-200">Secondary Neon Accent</span>
                        <span className="text-xs font-mono font-bold" style={{ color: theme.secondaryColor }}>
                          {theme.secondaryColor.toUpperCase()}
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {SWATCH_COLORS.map((swatch) => (
                          <button
                            key={swatch.hex}
                            onClick={() => setTheme({ secondaryColor: swatch.hex, preset: 'custom' })}
                            className={`w-8 h-8 rounded-lg border transition-all cursor-pointer flex items-center justify-center ${
                              theme.secondaryColor.toLowerCase() === swatch.hex.toLowerCase()
                                ? 'scale-110 border-white shadow-lg'
                                : 'border-white/20 hover:scale-105'
                            }`}
                            style={{ backgroundColor: swatch.hex }}
                            title={swatch.name}
                          >
                            {theme.secondaryColor.toLowerCase() === swatch.hex.toLowerCase() && (
                              <RiCheckLine
                                size={14}
                                className={['#ffffff', '#f59e0b', '#38bdf8'].includes(swatch.hex) ? 'text-black' : 'text-white'}
                              />
                            )}
                          </button>
                        ))}
                      </div>

                      <div className="flex items-center gap-3 mt-1">
                        <input
                          type="color"
                          value={theme.secondaryColor}
                          onChange={(e) => setTheme({ secondaryColor: e.target.value, preset: 'custom' })}
                          className="w-10 h-10 rounded-lg cursor-pointer bg-black/50 border border-white/20 overflow-hidden"
                        />
                        <input
                          type="text"
                          value={theme.secondaryColor}
                          onChange={(e) => setTheme({ secondaryColor: e.target.value, preset: 'custom' })}
                          placeholder="#06b6d4"
                          className="bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-zinc-200 uppercase w-32 focus:border-white/30 outline-none"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Background Tone Selector */}
                  <div className="flex flex-col gap-3 pt-4 border-t border-white/5">
                    <span className="text-xs font-semibold text-zinc-200">Base Ambient Tone</span>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {BG_TONES.map((bg) => {
                        const isBgSelected = theme.bgColor.toLowerCase() === bg.hex.toLowerCase()
                        return (
                          <button
                            key={bg.hex}
                            onClick={() => setTheme({ bgColor: bg.hex, preset: 'custom' })}
                            className={`p-3 rounded-xl border text-left transition-all cursor-pointer flex flex-col gap-1 ${
                              isBgSelected
                                ? 'border-emerald-400 bg-white/10 shadow-lg'
                                : 'bg-black/40 border-white/10 hover:border-white/20 hover:bg-white/5'
                            }`}
                            style={isBgSelected ? { borderColor: theme.primaryColor } : {}}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-zinc-200">{bg.name}</span>
                              <div
                                className="w-3.5 h-3.5 rounded-full border border-white/30"
                                style={{ backgroundColor: bg.hex }}
                              />
                            </div>
                            <span className="text-[10px] text-zinc-500 font-mono">{bg.desc}</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                </div>

                {/* Section 3: Visual Effects & Glassmorphism */}
                <div className={`${cardClass} gap-6`}>
                  <div className="flex items-center justify-between border-b border-white/10 pb-3">
                    <h4 className={titleClass}>
                      <RiSparklingLine style={{ color: theme.primaryColor }} size={18} />
                      Visual Effects & Glassmorphism
                    </h4>
                    <span className="text-[10px] font-mono text-zinc-400">ENGINE CONFIG</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Glass Blur Slider */}
                    <div className="flex flex-col gap-2">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-zinc-200">Backdrop Glass Blur</span>
                        <span className="text-xs font-mono font-bold" style={{ color: theme.primaryColor }}>
                          {theme.glassBlur}px
                        </span>
                      </div>
                      <input
                        type="range"
                        min="4"
                        max="32"
                        step="2"
                        value={theme.glassBlur}
                        onChange={(e) => setTheme({ glassBlur: parseInt(e.target.value) })}
                        className="w-full cursor-pointer accent-emerald-500"
                        style={{ accentColor: theme.primaryColor }}
                      />
                      <div className="flex justify-between text-[9px] font-mono text-zinc-500">
                        <span>Crisp (4px)</span>
                        <span>Standard (16px)</span>
                        <span>Ultra Blur (32px)</span>
                      </div>
                    </div>

                    {/* Glow Intensity */}
                    <div className="flex flex-col gap-2">
                      <span className="text-xs font-semibold text-zinc-200">HUD Neon Glow Intensity</span>
                      <div className="flex gap-2">
                        {(['none', 'subtle', 'vibrant'] as const).map((intensity) => (
                          <button
                            key={intensity}
                            onClick={() => setTheme({ glowIntensity: intensity })}
                            className={`flex-1 py-2 rounded-lg text-xs font-mono font-bold uppercase border transition-all cursor-pointer ${
                              theme.glowIntensity === intensity
                                ? 'text-white border-white bg-white/10 shadow-md'
                                : 'text-zinc-500 border-white/5 hover:border-white/20'
                            }`}
                            style={
                              theme.glowIntensity === intensity
                                ? { borderColor: theme.primaryColor, color: theme.primaryColor }
                                : {}
                            }
                          >
                            {intensity}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Hologram Tech Grid Toggle */}
                    <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                      <div className="flex flex-col">
                        <span className="text-xs font-semibold text-zinc-200">Holographic Scanlines</span>
                        <span className="text-[10px] text-zinc-500 font-mono">Cybernetic CRT matrix grid</span>
                      </div>
                      <button
                        onClick={() => setTheme({ hologramGrid: !theme.hologramGrid })}
                        className="w-12 h-6 rounded-full p-1 transition-colors cursor-pointer"
                        style={{ backgroundColor: theme.hologramGrid ? theme.primaryColor : '#3f3f46' }}
                      >
                        <div
                          className={`w-4 h-4 bg-white rounded-full transition-transform ${
                            theme.hologramGrid ? 'translate-x-6' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>

                    {/* Background Neural Particles */}
                    <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                      <div className="flex flex-col">
                        <span className="text-xs font-semibold text-zinc-200">Neural Network Particles</span>
                        <span className="text-[10px] text-zinc-500 font-mono">Interactive canvas constellation</span>
                      </div>
                      <button
                        onClick={() => setTheme({ particlesEnabled: !theme.particlesEnabled })}
                        className="w-12 h-6 rounded-full p-1 transition-colors cursor-pointer"
                        style={{ backgroundColor: theme.particlesEnabled ? theme.primaryColor : '#3f3f46' }}
                      >
                        <div
                          className={`w-4 h-4 bg-white rounded-full transition-transform ${
                            theme.particlesEnabled ? 'translate-x-6' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Section 4: Live Component Preview */}
                <div
                  className="p-6 rounded-2xl border flex flex-col gap-4 shadow-xl transition-all"
                  style={{
                    backgroundColor: hexToRgba(theme.bgColor, 0.8),
                    borderColor: hexToRgba(theme.primaryColor, 0.3),
                    boxShadow: `0 0 25px ${hexToRgba(theme.primaryColor, 0.15)}`
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-widest font-mono text-zinc-300">
                      Live Interface Preview
                    </span>
                    <span
                      className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border"
                      style={{
                        color: theme.primaryColor,
                        backgroundColor: hexToRgba(theme.primaryColor, 0.1),
                        borderColor: hexToRgba(theme.primaryColor, 0.3)
                      }}
                    >
                      ACTIVE MATRIX
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
                    <button
                      className="px-4 py-2.5 rounded-xl font-mono text-xs font-bold transition-all shadow-md cursor-pointer flex items-center justify-center gap-2 text-black"
                      style={{
                        backgroundColor: theme.primaryColor,
                        boxShadow: `0 0 15px ${hexToRgba(theme.primaryColor, 0.4)}`
                      }}
                    >
                      <RiSparklingLine /> Primary Action
                    </button>

                    <div
                      className="p-3 rounded-xl border flex items-center justify-between"
                      style={{
                        backgroundColor: hexToRgba(theme.secondaryColor, 0.08),
                        borderColor: hexToRgba(theme.secondaryColor, 0.3)
                      }}
                    >
                      <span className="text-xs font-mono" style={{ color: theme.secondaryColor }}>
                        Secondary Metric
                      </span>
                      <span className="text-xs font-bold text-white font-mono">100% OK</span>
                    </div>

                    <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-xl px-3 py-2">
                      <div
                        className="w-2.5 h-2.5 rounded-full animate-pulse"
                        style={{ backgroundColor: theme.primaryColor }}
                      />
                      <span className="text-xs font-mono text-zinc-300">JARVIS Neural Core</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* TAB: ABOUT & UPDATES                                         */}
            {/* ============================================================ */}
            {activeTab === 'about' && (
              <motion.div
                key="about"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="flex flex-col w-full max-w-3xl mx-auto px-4 pb-12"
              >
                {/* Header Profile */}
                <div className="flex flex-col items-center justify-center py-6 gap-2">
                  <div className="w-16 h-16 bg-black/40 backdrop-blur-md border border-emerald-500/20 rounded-xl overflow-hidden shadow-lg">
                    <img
                      src="./assets/icon.png"
                      alt="Logo"
                      className="w-full h-full object-cover rounded-sm grayscale hover:grayscale-0 transition-all"
                    />
                  </div>
                  <h2 className="text-[16px] font-bold text-white tracking-tight mt-1">JARVIS Desktop</h2>
                  <p className="text-[11px] font-mono text-zinc-500">Version {appVersion}</p>
                </div>

                {/* Updates Section */}
                <div className="flex flex-col gap-2 mt-2">
                  <div className="flex items-center gap-2 text-zinc-300 font-bold text-[11px] uppercase tracking-widest pl-1">
                    <RiRefreshLine size={14} /> Updates
                  </div>
                  <div className="bg-black/40 backdrop-blur-md border border-emerald-500/20 rounded-2xl p-6 flex flex-col gap-3 shadow-2xl">
                    <div className="flex items-start gap-3">
                      <RiDownloadCloud2Line size={16} className="text-zinc-400 mt-0.5" />
                      <div className="flex flex-col">
                        <span className="text-[13px] font-bold text-white">
                          {updateStatus === 'available'
                            ? 'A new update is ready (1 change included).'
                            : updateStatus === 'checking'
                            ? 'Checking for updates...'
                            : 'You are up to date.'}
                        </span>
                        <span className="text-[11px] text-zinc-500 mt-0.5">
                          {updateNotes || 'System is up to date.'}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 mt-1 pl-7 text-[12px] font-medium">
                      <button
                        onClick={checkForUpdates}
                        className="text-zinc-400 hover:text-white transition-colors cursor-pointer"
                      >
                        Check now
                      </button>
                      {updateStatus === 'available' && (
                        <button
                          onClick={downloadUpdate}
                          className="bg-white text-black px-4 py-1.5 rounded-md hover:bg-zinc-200 transition-colors font-bold cursor-pointer"
                        >
                          Update now
                        </button>
                      )}
                      {updateStatus === 'ready' && (
                        <button
                          onClick={installUpdate}
                          className="bg-emerald-500 text-black px-4 py-1.5 rounded-md hover:bg-emerald-400 transition-colors font-bold cursor-pointer"
                        >
                          Restart to Install
                        </button>
                      )}
                    </div>

                    {updateStatus === 'downloading' && (
                      <div className="w-full pl-7 flex flex-col gap-1.5 mt-2">
                        <div className="flex justify-between text-[10px] font-mono text-zinc-400">
                          <span>DOWNLOADING...</span>
                          <span>{downloadProgress}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-black/60 rounded-full overflow-hidden border border-white/10">
                          <div
                            className="h-full bg-white transition-all duration-300"
                            style={{ width: `${downloadProgress}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Automatic Updates Section */}
                <div className="flex flex-col gap-1 mt-6 pl-1">
                  <span className="text-[13px] font-bold text-white">Automatic updates</span>
                  <p className="text-[12px] text-zinc-400">
                    JARVIS checks for updates automatically in the background and lets you know when one is ready.
                  </p>
                  <p className="text-[10px] font-mono text-zinc-600 mt-1">
                    Branch main • Commit 07e97d2
                  </p>
                </div>
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* TAB: BEHAVIORS                                               */}
            {/* ============================================================ */}
            {activeTab === 'behaviors' && (
              <motion.div
                key="behaviors"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full"
              >
                <div className={`${cardClass} md:col-span-1`}>
                  <div className="flex justify-between items-center border-b border-white/10 pb-4">
                    <h3 className={titleClass}>
                      <RiSettings4Line className="text-emerald-500 text-lg" style={{ color: theme.primaryColor }} />
                      App Behaviors
                    </h3>
                  </div>

                  <div className="flex flex-col gap-4 mt-6">
                    <div className="flex items-center justify-between">
                      <div className="flex flex-col">
                        <span className="text-white text-sm font-semibold">Always on Top</span>
                        <span className="text-zinc-500 text-xs">Keep JARVIS above other windows</span>
                      </div>
                      <button
                        onClick={() => {
                          setAlwaysOnTop(!alwaysOnTop)
                          window.electron?.ipcRenderer?.send('set-always-on-top', !alwaysOnTop)
                        }}
                        className="w-12 h-6 rounded-full p-1 transition-colors cursor-pointer"
                        style={{ backgroundColor: alwaysOnTop ? theme.primaryColor : '#3f3f46' }}
                      >
                        <div
                          className={`w-4 h-4 bg-white rounded-full transition-transform ${
                            alwaysOnTop ? 'translate-x-6' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>

                    <div className="flex items-center justify-between mt-2">
                      <div className="flex flex-col">
                        <span className="text-white text-sm font-semibold">Auto-Start</span>
                        <span className="text-zinc-500 text-xs">Launch JARVIS when Windows starts</span>
                      </div>
                      <button
                        onClick={() => {
                          setAutoStart(!autoStart)
                          window.electron?.ipcRenderer?.send('set-auto-start', !autoStart)
                        }}
                        className="w-12 h-6 rounded-full p-1 transition-colors cursor-pointer"
                        style={{ backgroundColor: autoStart ? theme.primaryColor : '#3f3f46' }}
                      >
                        <div
                          className={`w-4 h-4 bg-white rounded-full transition-transform ${
                            autoStart ? 'translate-x-6' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                </div>

                <div className={`${cardClass} md:col-span-1`}>
                  <div className="flex justify-between items-center border-b border-white/10 pb-4">
                    <h3 className={titleClass}>
                      <RiSettings4Line className="text-emerald-500 text-lg" style={{ color: theme.primaryColor }} />
                      Audio & Storage
                    </h3>
                  </div>

                  <div className="flex flex-col gap-4 mt-6">
                    <div className="flex items-center justify-between">
                      <div className="flex flex-col">
                        <span className="text-white text-sm font-semibold">UI Sound Effects</span>
                        <span className="text-zinc-500 text-xs">Play clicks and beeps</span>
                      </div>
                      <button
                        onClick={() => setUiSoundEffects(!uiSoundEffects)}
                        className="w-12 h-6 rounded-full p-1 transition-colors cursor-pointer"
                        style={{ backgroundColor: uiSoundEffects ? theme.primaryColor : '#3f3f46' }}
                      >
                        <div
                          className={`w-4 h-4 bg-white rounded-full transition-transform ${
                            uiSoundEffects ? 'translate-x-6' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>

                    <div className="flex flex-col mt-4">
                      <span className="text-white text-sm font-semibold">Storage Path</span>
                      <span className="text-zinc-500 text-xs mb-2">Where JARVIS saves Notes & Gallery</span>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          readOnly
                          value={storagePath || 'Default directory'}
                          className="flex-1 bg-black/30 border border-emerald-500/20 rounded-lg px-3 py-2 text-xs text-zinc-300 outline-none"
                        />
                        <button
                          onClick={async () => {
                            const path = await window.electron?.ipcRenderer?.invoke('select-storage-path')
                            if (path) setStoragePath(path)
                          }}
                          className="px-3 py-2 rounded-lg text-xs font-bold transition-colors cursor-pointer"
                          style={{
                            backgroundColor: hexToRgba(theme.primaryColor, 0.15),
                            color: theme.primaryColor
                          }}
                        >
                          BROWSE
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* TAB: AI PARAMETERS                                           */}
            {/* ============================================================ */}
            {activeTab === 'ai' && (
              <motion.div
                key="ai"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full"
              >
                <div className={`${cardClass} md:col-span-2`}>
                  <div className="flex justify-between items-center border-b border-emerald-500/10 pb-4">
                    <h3 className={titleClass}>
                      <RiBrainLine className="text-emerald-500 text-lg" style={{ color: theme.primaryColor }} />
                      AI Brain Parameters
                    </h3>
                  </div>

                  <div className="flex flex-col gap-6 mt-6">
                    <div className="flex flex-col gap-2">
                      <div className="flex justify-between items-end">
                        <div className="flex flex-col">
                          <span className="text-white text-sm font-semibold">Creativity (Temperature)</span>
                          <span className="text-zinc-500 text-xs">Low = Strict/Analytical, High = Creative</span>
                        </div>
                        <span className="font-mono text-sm font-bold" style={{ color: theme.primaryColor }}>
                          {temperature.toFixed(2)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={temperature}
                        onChange={(e) => setTemperature(parseFloat(e.target.value))}
                        disabled={isSystemActive}
                        className={`w-full ${isSystemActive ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
                        style={{ accentColor: theme.primaryColor }}
                      />
                    </div>

                    <div className="flex flex-col gap-2 mt-4">
                      <div className="flex justify-between items-end">
                        <div className="flex flex-col">
                          <span className="text-white text-sm font-semibold">Response Length (Max Tokens)</span>
                          <span className="text-zinc-500 text-xs">Limit how much JARVIS can output at once</span>
                        </div>
                        <span className="font-mono text-sm font-bold" style={{ color: theme.primaryColor }}>
                          {maxTokens}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="256"
                        max="8192"
                        step="256"
                        value={maxTokens}
                        onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                        disabled={isSystemActive}
                        className={`w-full ${isSystemActive ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
                        style={{ accentColor: theme.primaryColor }}
                      />
                    </div>

                    {isSystemActive && (
                      <div className="mt-2 text-[10px] text-amber-500/80 bg-amber-500/10 p-2 rounded border border-amber-500/20 text-center uppercase tracking-widest font-bold">
                        Disconnect JARVIS to change AI parameters
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* TAB: GENERAL                                                 */}
            {/* ============================================================ */}
            {activeTab === 'general' && (
              <motion.div
                key="general"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full"
              >
                <div className={`${cardClass} md:col-span-2`}>
                  <div className="flex justify-between items-center">
                    <span className={titleClass}>
                      <RiUserLine className="text-zinc-400" size={18} /> AI Personality Matrix
                    </span>
                    <div className="flex items-center gap-4">
                      <span
                        className={`text-[10px] font-mono tracking-widest ${
                          currentWordCount >= 150 ? 'text-red-400' : 'text-zinc-400'
                        }`}
                      >
                        {currentWordCount} / 150 WORDS
                      </span>
                      <button
                        onClick={savePersonality}
                        className="text-zinc-400 hover:text-white transition-colors bg-white/5 p-2 rounded-md hover:bg-white/10 border border-white/5 cursor-pointer"
                      >
                        <RiSave3Line size={18} />
                      </button>
                    </div>
                  </div>
                  <textarea
                    value={personality}
                    onChange={handlePersonalityChange}
                    placeholder="Define who JARVIS is. Example: 'You are a sassy, highly technical assistant...'"
                    className="bg-black/30 backdrop-blur-md border border-emerald-500/20 rounded-lg p-4 text-sm text-zinc-200 h-32 resize-none focus:border-emerald-500/50 focus:bg-black/50 outline-none transition-all scrollbar-small"
                  />
                </div>

                <div className={cardClass}>
                  <div className="flex justify-between items-end">
                    <span className={titleClass}>
                      <RiUserLine className="text-zinc-400" size={18} /> User Designation
                    </span>
                  </div>
                  <div className={inputContainerClass}>
                    <input
                      type="text"
                      value={userName}
                      onChange={(e) => setUserName(e.target.value)}
                      placeholder="Enter operator name..."
                      className="bg-transparent border-none outline-none text-sm text-zinc-100 w-full placeholder:text-zinc-600 font-medium"
                    />
                    <button
                      onClick={saveUserName}
                      className="text-zinc-500 hover:text-white transition-colors ml-2 cursor-pointer"
                    >
                      <RiSave3Line size={20} />
                    </button>
                  </div>
                </div>

                <div className={`${cardClass} md:col-span-2 relative`}>
                  <div className="flex justify-between items-center">
                    <span className={titleClass}>
                      <RiUserVoiceLine className="text-zinc-400" size={18} /> OS Voice Profile
                    </span>
                    {isSystemActive && (
                      <span className="text-[10px] text-red-400 font-mono tracking-widest flex items-center gap-1 bg-red-500/10 px-2 py-1 rounded border border-red-500/20">
                        <RiLock2Line /> LOCKED AS JARVIS IS CONNECTED
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col gap-3 mt-1">
                    <div
                      className={`flex gap-2 w-full ${
                        isSystemActive ? 'opacity-40 pointer-events-none' : ''
                      }`}
                    >
                      <button
                        onClick={() => setSelectedGender('MALE')}
                        className={`flex-1 py-2 rounded-md text-[10px] font-bold tracking-widest border transition-all cursor-pointer ${
                          selectedGender === 'MALE'
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-md'
                            : 'bg-black/30 text-zinc-400 border-emerald-500/10 hover:border-emerald-500/30 hover:text-white'
                        }`}
                      >
                        MALE VOICES
                      </button>
                      <button
                        onClick={() => setSelectedGender('FEMALE')}
                        className={`flex-1 py-2 rounded-md text-[10px] font-bold tracking-widest border transition-all cursor-pointer ${
                          selectedGender === 'FEMALE'
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-md'
                            : 'bg-black/30 text-zinc-400 border-emerald-500/10 hover:border-emerald-500/30 hover:text-white'
                        }`}
                      >
                        FEMALE VOICES
                      </button>
                    </div>

                    <div
                      className={`flex flex-wrap gap-3 ${
                        isSystemActive ? 'opacity-40 cursor-not-allowed' : ''
                      }`}
                    >
                      {(selectedGender === 'MALE' ? ['Charon', 'Fenrir', 'Puck'] : ['Kore', 'Aoede']).map(
                        (s) => (
                          <button
                            key={s}
                            onClick={() => handleVoiceChange(s)}
                            disabled={isSystemActive}
                            className={`cursor-pointer flex-1 min-w-[100px] h-12 flex items-center justify-center text-[12px] font-bold rounded-lg transition-all tracking-widest border ${
                              voice === s
                                ? 'bg-white text-black border-white shadow-lg font-black'
                                : 'bg-black/30 border-emerald-500/10 text-zinc-400 hover:text-white hover:border-emerald-500/30 hover:bg-emerald-500/5'
                            }`}
                          >
                            {s.toUpperCase()}
                          </button>
                        )
                      )}
                    </div>
                  </div>
                </div>

                <div className={`${cardClass} md:col-span-2`}>
                  <div className="flex justify-between items-center pb-2 border-b border-white/10">
                    <span className={titleClass}>
                      <RiLayoutGridLine className="text-zinc-400" size={18} /> Navigation Modules
                    </span>
                    <span className="text-[10px] text-zinc-400 font-mono tracking-widest">
                      TOGGLE VISIBILITY
                    </span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {NAVIGATION_MODULES.filter((tab) => !tab.isCore).map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => toggleTabVisibility(tab.id)}
                        className={`cursor-pointer flex items-center justify-between px-4 py-3 rounded-xl border transition-all ${
                          !hiddenTabs.includes(tab.id)
                            ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                            : 'bg-black/30 backdrop-blur-md border-emerald-500/10 text-zinc-400 hover:border-emerald-500/30 hover:text-zinc-200'
                        }`}
                        style={
                          !hiddenTabs.includes(tab.id)
                            ? {
                                backgroundColor: hexToRgba(theme.primaryColor, 0.1),
                                borderColor: hexToRgba(theme.primaryColor, 0.3),
                                color: theme.primaryColor
                              }
                            : {}
                        }
                      >
                        <span className="text-[11px] font-bold tracking-widest">{tab.id.toUpperCase()}</span>
                        <div
                          className="w-8 h-4 rounded-full p-0.5 transition-colors"
                          style={{
                            backgroundColor: !hiddenTabs.includes(tab.id)
                              ? theme.primaryColor
                              : '#3f3f46'
                          }}
                        >
                          <div
                            className={`w-3 h-3 bg-white rounded-full transition-transform ${
                              !hiddenTabs.includes(tab.id) ? 'translate-x-4' : 'translate-x-0'
                            }`}
                          />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* TAB: API KEYS                                                */}
            {/* ============================================================ */}
            {activeTab === 'keys' && (
              <motion.div
                key="keys"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="grid grid-cols-1 gap-6 w-full"
              >
                <div className={`${cardClass} gap-6`}>
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
                    <span className={titleClass}>
                      <RiKey2Line className="text-zinc-400" size={18} /> External API Endpoints
                    </span>
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={saveApiKeys}
                      className={`px-6 py-2.5 rounded-lg text-xs font-bold tracking-widest transition-all shadow-lg flex items-center justify-center gap-2 cursor-pointer ${
                        saveSuccess
                          ? 'bg-emerald-500 text-black hover:bg-emerald-400'
                          : 'bg-white text-black hover:bg-zinc-200'
                      }`}
                    >
                      {saveSuccess ? (
                        <>
                          <RiCheckLine size={16} /> KEYS SECURED & SYNCED
                        </>
                      ) : (
                        <>
                          <RiSave3Line size={16} /> SAVE ALL KEYS
                        </>
                      )}
                    </motion.button>
                  </div>

                  {!isGeminiConfigured && !apiKeys.gemini && (
                    <div className="bg-amber-500/10 border border-amber-500/30 p-3.5 rounded-xl flex items-start gap-3">
                      <RiErrorWarningLine className="text-amber-400 shrink-0 mt-0.5" size={18} />
                      <div className="flex flex-col gap-0.5">
                        <span className="text-xs font-bold text-amber-300 font-mono tracking-wider">
                          ACTION REQUIRED: GEMINI API KEY UNSET
                        </span>
                        <p className="text-[11px] text-zinc-300 leading-relaxed font-mono">
                          J.A.R.V.I.S. requires a Google AI Studio / Gemini API key for natural language reasoning, function calling, and conversation memory. Enter your key below and click "SAVE ALL KEYS".
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="flex flex-col gap-1 max-h-[500px] overflow-y-auto pr-2 scrollbar-small">
                    {[
                      { id: 'gemini', label: 'Google AI Studio / Gemini Core', placeholder: 'AQ.A...jQKg / AIzaSy_...' },
                      { id: 'groq', label: 'Groq Fast Inferencing', placeholder: 'gsk_...' },
                      { id: 'openai', label: 'OpenAI API Key', placeholder: 'sk-proj-...' },
                      { id: 'anthropic', label: 'Anthropic Claude', placeholder: 'sk-ant-api...' },
                      { id: 'openrouter', label: 'OpenRouter Multi-Model', placeholder: 'sk-or-v1-...' },
                      { id: 'deepseek', label: 'DeepSeek API Key', placeholder: 'sk-...' },
                      { id: 'tavily', label: 'Tavily Search Engine', placeholder: 'tvly-...' },
                      { id: 'xai', label: 'xAI Grok', placeholder: 'xai-...' },
                      { id: 'hf', label: 'HuggingFace Token', placeholder: 'hf_...' }
                    ].map((provider) => (
                      <div
                        key={provider.id}
                        className="flex flex-col md:flex-row md:items-center justify-between gap-2 p-3 rounded-lg border-b border-white/5 hover:bg-white/5 transition-colors"
                      >
                        <label className="text-[11px] text-zinc-300 font-bold flex items-center gap-2 flex-shrink-0 md:w-1/3">
                          <div className="w-1.5 h-1.5 rounded-full bg-zinc-600"></div>
                          {provider.label}
                        </label>
                        <div className="flex-1 w-full md:max-w-md">
                          <input
                            type="password"
                            value={apiKeys[provider.id] || ''}
                            onChange={(e) =>
                              setApiKeys((prev) => ({ ...prev, [provider.id]: e.target.value }))
                            }
                            placeholder={provider.placeholder}
                            className="bg-black/30 border border-transparent hover:border-emerald-500/20 rounded-md px-3 py-1.5 outline-none text-xs font-mono text-zinc-100 w-full placeholder:text-zinc-600 focus:border-emerald-500/40 focus:bg-black/50 transition-all"
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="bg-black/30 border border-emerald-500/20 p-4 rounded-xl mt-2 flex items-start gap-3">
                    <RiShieldKeyholeLine className="text-emerald-400 shrink-0 mt-0.5" size={16} />
                    <p className="text-[10px] text-zinc-400 font-mono leading-relaxed">
                      [SECURITY NOTICE]: All API keys are encrypted and stored strictly in your local
                      OS. JARVIS does not transmit these keys to any centralized server.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* TAB: PERMISSIONS                                             */}
            {/* ============================================================ */}
            {activeTab === 'permissions' && (
              <motion.div
                key="permissions"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="flex flex-col gap-6"
              >
                <div className={cardClass}>
                  <div>
                    <h3 className={titleClass}>
                      <RiShieldCheckLine style={{ color: theme.primaryColor }} size={18} />
                      Autonomous Tool Permissions
                    </h3>
                    <p className="text-xs text-zinc-400 font-mono mt-1">
                      Manage explicit execution grants for autonomous tools. Ungranted MEDIUM+ tools require confirmation dialog.
                    </p>
                  </div>

                  <div className="space-y-3">
                    {!Array.isArray(toolsList) || toolsList.length === 0 ? (
                      <div className="text-center p-6 text-xs text-zinc-500 font-mono">
                        No registered tools detected or core service is offline.
                      </div>
                    ) : (
                      toolsList.map((t) => {
                        const isGranted = Array.isArray(permissionsList) && permissionsList.some(
                          (p) => p.tool === t.name && p.granted
                        )
                        return (
                          <div
                            key={t.name}
                            className="p-4 rounded-xl bg-black/30 border border-emerald-500/20 flex items-center justify-between hover:bg-black/50 transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                                <RiTerminalWindowLine />
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-mono font-bold text-zinc-100">
                                    {t.name}
                                  </span>
                                  <span
                                    className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold border ${
                                      t.risk_level === 'CRITICAL'
                                        ? 'text-red-400 bg-red-500/10 border-red-500/30'
                                        : t.risk_level === 'HIGH'
                                        ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                                        : t.risk_level === 'MEDIUM'
                                        ? 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30'
                                        : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                                    }`}
                                  >
                                    {t.risk_level}
                                  </span>
                                </div>
                                <p className="text-[11px] text-zinc-400 mt-0.5">{t.description}</p>
                              </div>
                            </div>

                            <button
                              onClick={() => handleTogglePermission(t.name, isGranted)}
                              className={`px-4 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer ${
                                isGranted
                                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-red-500/20 hover:text-red-400'
                                  : 'bg-white/5 text-zinc-400 border border-white/10 hover:bg-emerald-500/20 hover:text-emerald-300'
                              }`}
                              style={
                                isGranted
                                  ? {
                                      backgroundColor: hexToRgba(theme.primaryColor, 0.15),
                                      borderColor: hexToRgba(theme.primaryColor, 0.3),
                                      color: theme.primaryColor
                                    }
                                  : {}
                              }
                            >
                              {isGranted ? 'GRANTED (Click to Revoke)' : 'DENIED (Click to Grant)'}
                            </button>
                          </div>
                        )
                      })
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* TAB: SECURITY                                                */}
            {/* ============================================================ */}
            {activeTab === 'security' && (
              <motion.div
                key="security"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="w-full rounded-2xl overflow-hidden shadow-2xl border border-emerald-500/20 relative"
              >
                <AnimatePresence>
                  {!isSecurityUnlocked && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0, backdropFilter: 'blur(0px)' }}
                      className="absolute inset-0 z-20 backdrop-blur-2xl bg-black/85 border border-emerald-500/20 rounded-2xl flex flex-col items-center justify-center"
                    >
                      <div className="bg-black/60 backdrop-blur-md p-5 rounded-full mb-6 border border-emerald-500/20 shadow-lg">
                        <RiLockPasswordLine size={40} className="text-emerald-400" />
                      </div>
                      <p className="text-xs text-zinc-300 font-mono tracking-widest uppercase mb-6 font-semibold">
                        Authenticate to access Vault Settings
                      </p>
                      <div className="flex gap-3 items-center h-12">
                        <input
                          type="password"
                          maxLength={4}
                          pattern="\d*"
                          value={authPin}
                          onChange={(e) => setAuthPin(e.target.value.replace(/\D/g, ''))}
                          placeholder="PIN"
                          className={`h-full bg-black/60 border w-32 rounded-lg text-center text-xl tracking-[0.5em] text-white outline-none transition-colors ${
                            authError
                              ? 'border-red-500 text-red-500 bg-red-500/10'
                              : 'border-emerald-500/30 focus:border-emerald-400 focus:bg-black/80 backdrop-blur-md'
                          }`}
                        />
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={unlockSecurityModule}
                          className="h-full px-8 bg-emerald-500 text-black text-xs font-bold tracking-widest rounded-lg hover:bg-emerald-400 transition-colors shadow-lg cursor-pointer"
                        >
                          UNLOCK
                        </motion.button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-black/30 backdrop-blur-sm p-6 rounded-2xl border border-emerald-500/20">
                  <div className="bg-black/40 backdrop-blur-md border border-emerald-500/20 p-7 rounded-xl flex flex-col gap-5">
                    <span className={titleClass}>
                      <RiLockPasswordLine className="text-zinc-400" size={18} /> Update Master PIN
                    </span>
                    <div className={inputContainerClass}>
                      <input
                        type="password"
                        maxLength={4}
                        pattern="\d*"
                        value={newPin}
                        onChange={(e) => setNewPin(e.target.value.replace(/\D/g, ''))}
                        placeholder="Enter new 4-digit PIN..."
                        className="bg-transparent border-none outline-none text-sm font-mono text-zinc-100 w-full tracking-[0.3em]"
                      />
                      <button
                        onClick={updateMasterPin}
                        className="text-zinc-500 hover:text-white transition-colors ml-2 cursor-pointer"
                      >
                        <RiSave3Line size={20} />
                      </button>
                    </div>
                  </div>

                  <div className="bg-black/40 backdrop-blur-md border border-emerald-500/20 p-7 rounded-xl flex flex-col gap-6">
                    <div className="flex justify-between items-center border-b border-emerald-500/20 pb-4">
                      <span className={titleClass}>
                        <RiScan2Line className="text-zinc-400" size={18} /> Biometric Registry
                      </span>
                      <span className="text-[10px] text-emerald-400 font-mono tracking-widest bg-emerald-500/10 px-3 py-1.5 rounded-md font-semibold border border-emerald-500/20">
                        {faceCount} ENROLLED
                      </span>
                    </div>

                    {isScanningFace ? (
                      <div className="flex items-center gap-4 bg-black/60 p-3 rounded-xl border border-emerald-500/30">
                        <video
                          ref={videoRef}
                          autoPlay
                          muted
                          playsInline
                          className="w-16 h-16 rounded-lg object-cover -scale-x-100 border border-white/10"
                        />
                        <div className="flex flex-col gap-1">
                          <span className="text-[11px] text-white font-mono tracking-widest animate-pulse font-bold">
                            {enrollStatus}
                          </span>
                          <span className="text-xs text-zinc-400">Keep head steady...</span>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-4 h-full justify-between">
                        <p className="text-xs text-zinc-400 leading-relaxed">
                          Enroll additional structural face descriptors. Data is mathematically encrypted
                          and stored locally.
                        </p>
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={startFaceEnrollment}
                          className="w-full py-3 rounded-lg bg-white text-black font-bold tracking-widest text-[12px] flex items-center justify-center gap-2 hover:bg-zinc-200 transition-all shadow-lg mt-auto cursor-pointer"
                        >
                          <RiAddLine size={18} /> ENROLL NEW IDENTITY
                        </motion.button>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  )
}

export default SettingsView
