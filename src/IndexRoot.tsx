import { useState, useEffect, useRef } from 'react'
import MiniOverlay from '@/components/dashboard/mini-overlay'
import { jarvisService } from './services/jarvis-voice-ai'
import { getScreenSourceId } from './hooks/use-capture-desktop'
import JARVIS from './layouts/jarvis-layout'
import LeafletMapWidget from '@/components/widgets/map-view'
import ImageWidget from '@/components/widgets/image-widget'
import EmailWidget from '@/components/widgets/email-widget'
import WeatherWidget from '@/components/widgets/weather-widget'
import StockWidget from '@/components/widgets/stock-widget'
import WormholeWidget from '@/components/widgets/wormhole'
import TitleBar from '@/components/common/titlebar'
import ParticleNetwork from '@/components/dashboard/particle-network'


import { useSettingsStore } from './store/settings-store'
import { applyThemeToDom } from './services/theme-manager'

export type VisionMode = 'camera' | 'screen' | 'none'

const IndexRoot = () => {
  const [isOverlay, setIsOverlay] = useState(false)
  const theme = useSettingsStore((state) => state.theme)

  useEffect(() => {
    if (theme) {
      applyThemeToDom(theme)
    }
  }, [theme])

  const [isSystemActive, setIsSystemActive] = useState(false)
  const [isMicMuted, setIsMicMuted] = useState(true)

  const [isVideoOn, setIsVideoOn] = useState(false)
  const [visionMode, setVisionMode] = useState<VisionMode>('none')

  const processingVideoRef = useRef<HTMLVideoElement>(document.createElement('video'))
  const activeStreamRef = useRef<MediaStream | null>(null)
  const aiIntervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (window.electron?.ipcRenderer) {
      window.electron.ipcRenderer.on('overlay-mode', (_e: any, mode: any) => setIsOverlay(mode))
      return () => {
        window.electron.ipcRenderer.removeAllListeners('overlay-mode')
      }
    }
  }, [])

  useEffect(() => {
    const watchdog = setInterval(() => {
      if (isSystemActive && !jarvisService.isConnected) {
        setIsSystemActive(false)
        setIsMicMuted(true)
        stopVision()
      }
    }, 1000)
    return () => clearInterval(watchdog)
  }, [isSystemActive])

  const toggleSystem = async () => {
    if (!isSystemActive) {
      try {
        await jarvisService.connect()
        setIsSystemActive(true)
        setIsMicMuted(false)
        jarvisService.setMute(false)
      } catch (err: any) {
        if (err.message === 'NO_API_KEY') {
          alert(
            '⚠️ CRITICAL ERROR: Gemini API Key is missing. Please enter it in the Command Center Vault (Settings Tab).'
          )
        } else {
          alert(`Connection failed: ${err.message}`)
        }
        setIsSystemActive(false)
      }
    } else {
      jarvisService.disconnect()
      setIsSystemActive(false)
      setIsMicMuted(true)
      jarvisService.setMute(true)
      stopVision()
    }
  }

  const toggleMic = () => {
    const s = !isMicMuted
    setIsMicMuted(s)
    jarvisService.setMute(s)
  }

  const startVision = async (mode: 'camera' | 'screen') => {
    if (!isSystemActive) return

    try {
      if (activeStreamRef.current) {
        activeStreamRef.current.getTracks().forEach((t) => t.stop())
      }

      let stream: MediaStream

      if (mode === 'camera') {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 }
        })
      } else {
        const sourceId = await getScreenSourceId()
        if (!sourceId) return
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            // @ts-ignore
            mandatory: {
              chromeMediaSource: 'desktop',
              chromeMediaSourceId: sourceId,
              maxWidth: 1280,
              maxHeight: 720
            }
          }
        })
      }

      activeStreamRef.current = stream

      processingVideoRef.current.srcObject = stream
      await processingVideoRef.current.play()

      setVisionMode(mode)
      setIsVideoOn(true)

      startAIProcessing()

      stream.getVideoTracks()[0].onended = () => stopVision()
    } catch (e) {
      stopVision()
    }
  }

  const stopVision = () => {
    setIsVideoOn(false)
    setVisionMode('none')

    if (activeStreamRef.current) {
      activeStreamRef.current.getTracks().forEach((t) => t.stop())
      activeStreamRef.current = null
    }

    if (processingVideoRef.current) {
      processingVideoRef.current.srcObject = null
    }

    if (aiIntervalRef.current) {
      clearInterval(aiIntervalRef.current)
      aiIntervalRef.current = null
    }
  }

  const startAIProcessing = () => {
    if (aiIntervalRef.current) clearInterval(aiIntervalRef.current)

    aiIntervalRef.current = setInterval(() => {
      const vid = processingVideoRef.current
      if (vid && vid.readyState === 4 && jarvisService.isConnected) {
        const canvas = document.createElement('canvas')
        canvas.width = 800
        canvas.height = 450
        const ctx = canvas.getContext('2d')
        if (ctx) {
          ctx.drawImage(vid, 0, 0, canvas.width, canvas.height)
          const base64 = canvas.toDataURL('image/jpeg', 0.6).split(',')[1]
          jarvisService.sendVideoFrame(base64)
        }
      }
    }, 2000)
  }

  if (isOverlay) {
    return (
      <div className="w-screen h-screen overflow-hidden flex items-center justify-center bg-transparent">
        <MiniOverlay
          isSystemActive={isSystemActive}
          toggleSystem={toggleSystem}
          isMicMuted={isMicMuted}
          toggleMic={toggleMic}
          isVideoOn={isVideoOn}
          visionMode={visionMode}
          startVision={startVision}
          stopVision={stopVision}
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-transparent overflow-hidden relative border border-emerald-500/20 rounded-xl">
      <div className="absolute inset-0 z-0 pointer-events-none">
        <ParticleNetwork />
      </div>
      <TitleBar />
      <div className="flex-1 relative">
        <JARVIS
          isSystemActive={isSystemActive}
          toggleSystem={toggleSystem}
          isMicMuted={isMicMuted}
          toggleMic={toggleMic}
          isVideoOn={isVideoOn}
          visionMode={visionMode}
          startVision={startVision}
          stopVision={stopVision}
          activeStream={activeStreamRef.current}
        />
      </div>
      <WormholeWidget />
      <LeafletMapWidget />
      <StockWidget />
      <WeatherWidget />
      <ImageWidget />
      <EmailWidget />
    </div>
  )
}

export default IndexRoot
