import React, { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import {
  RiVolumeUpLine,
  RiPlayFill,
  RiPauseFill,
  RiStopFill,
  RiFileCopyLine,
  RiDeleteBin7Line,
  RiVoiceprintLine,
  RiSettings3Line,
  RiCheckLine,
  RiSparklingLine
} from 'react-icons/ri'
import { useSettingsStore } from '@/store/settings-store'
import { hexToRgba } from '@/services/theme-manager'

const QUICK_PROMPTS = [
  'All primary subsystems are online and operating at maximum efficiency.',
  'Good morning, sir. I have prepared your daily diagnostic report and agenda.',
  'Warning: Security anomaly detected in network gateway. Engaging defensive protocols.',
  'Quantum neural parameters calibrated. Awaiting your direct command.'
]

export const TextToSpeechModule: React.FC = () => {
  const theme = useSettingsStore((state) => state.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  const [text, setText] = useState('Welcome back, sir. All core subsystems and neural networks are online and functioning within nominal parameters.')
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([])
  const [selectedVoiceURI, setSelectedVoiceURI] = useState<string>('')
  const [rate, setRate] = useState(1.0)
  const [pitch, setPitch] = useState(1.0)
  const [volume, setVolume] = useState(1.0)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [copied, setCopied] = useState(false)

  // Load browser/OS voices
  useEffect(() => {
    const updateVoices = () => {
      const available = window.speechSynthesis.getVoices()
      if (available.length > 0) {
        setVoices(available)
        if (!selectedVoiceURI) {
          const defaultVoice =
            available.find((v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('David') || v.name.includes('Google'))) ||
            available[0]
          if (defaultVoice) setSelectedVoiceURI(defaultVoice.voiceURI)
        }
      }
    }

    updateVoices()
    window.speechSynthesis.onvoiceschanged = updateVoices
    return () => {
      window.speechSynthesis.cancel()
    }
  }, [])

  const handleSpeak = () => {
    if (!text.trim()) return

    if (isPaused) {
      window.speechSynthesis.resume()
      setIsPaused(false)
      setIsSpeaking(true)
      return
    }

    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    const voiceObj = voices.find((v) => v.voiceURI === selectedVoiceURI)
    if (voiceObj) utterance.voice = voiceObj
    utterance.rate = rate
    utterance.pitch = pitch
    utterance.volume = volume

    utterance.onstart = () => {
      setIsSpeaking(true)
      setIsPaused(false)
    }

    utterance.onend = () => {
      setIsSpeaking(false)
      setIsPaused(false)
    }

    utterance.onerror = () => {
      setIsSpeaking(false)
      setIsPaused(false)
    }

    window.speechSynthesis.speak(utterance)
  }

  const handlePause = () => {
    if (isSpeaking && !isPaused) {
      window.speechSynthesis.pause()
      setIsPaused(true)
    } else if (isPaused) {
      window.speechSynthesis.resume()
      setIsPaused(false)
    }
  }

  const handleStop = () => {
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
    setIsPaused(false)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="h-full flex flex-col gap-6 overflow-y-auto pr-2 scrollbar-small">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2.5">
            <RiVolumeUpLine style={{ color: primaryColor }} size={24} />
            Text-to-Speech Engine
          </h3>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Convert custom text and commands into natural synthesized vocal output.
          </p>
        </div>

        {/* Live Audio Visualizer Banner */}
        <div
          className="flex items-center gap-2 px-4 py-2 rounded-xl border backdrop-blur-md"
          style={{
            backgroundColor: hexToRgba(primaryColor, 0.08),
            borderColor: hexToRgba(primaryColor, 0.3)
          }}
        >
          <RiVoiceprintLine
            className={isSpeaking && !isPaused ? 'animate-pulse' : 'text-zinc-500'}
            style={{ color: isSpeaking && !isPaused ? primaryColor : undefined }}
            size={20}
          />
          <div className="flex items-center gap-1 h-4">
            {[0.4, 0.8, 1.2, 0.6, 1.0, 0.5, 0.9, 0.3].map((delay, idx) => (
              <motion.div
                key={idx}
                className="w-1 rounded-full"
                style={{ backgroundColor: primaryColor }}
                animate={
                  isSpeaking && !isPaused
                    ? { height: ['4px', '16px', '6px', '14px', '4px'] }
                    : { height: '4px' }
                }
                transition={{
                  repeat: Infinity,
                  duration: 0.8,
                  delay: delay * 0.2
                }}
              />
            ))}
          </div>
          <span
            className="text-xs font-mono font-bold tracking-widest uppercase ml-2"
            style={{ color: primaryColor }}
          >
            {isSpeaking && !isPaused ? 'SYNTHESIZING...' : isPaused ? 'PAUSED' : 'READY'}
          </span>
        </div>
      </div>

      {/* Main Grid: Left Text Input + Right Voice Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Text Box & Quick Prompts */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="p-5 rounded-2xl bg-zinc-950/40 backdrop-blur-md border border-white/10 flex flex-col gap-3 shadow-lg">
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
              <span className="text-xs font-bold text-zinc-300 uppercase tracking-widest font-mono flex items-center gap-2">
                <RiSparklingLine style={{ color: primaryColor }} /> Input Text Buffer
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-zinc-500">
                  {text.length} chars • {text.trim().split(/\s+/).filter(Boolean).length} words
                </span>
                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
                  title="Copy text"
                >
                  {copied ? <RiCheckLine size={15} style={{ color: primaryColor }} /> : <RiFileCopyLine size={15} />}
                </button>
                <button
                  onClick={() => setText('')}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-red-400 transition-colors"
                  title="Clear text"
                >
                  <RiDeleteBin7Line size={15} />
                </button>
              </div>
            </div>

            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Enter text to synthesize into spoken audio..."
              rows={7}
              className="w-full bg-transparent border-none outline-none text-sm text-zinc-100 placeholder:text-zinc-600 resize-none font-sans leading-relaxed scrollbar-small"
            />

            {/* Playback Control Bar */}
            <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-white/10">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSpeak}
                className="px-6 py-2.5 rounded-xl font-mono text-xs font-bold transition-all shadow-lg flex items-center gap-2 cursor-pointer text-black"
                style={{
                  backgroundColor: primaryColor,
                  boxShadow: `0 0 15px ${hexToRgba(primaryColor, 0.35)}`
                }}
              >
                <RiPlayFill size={16} /> {isPaused ? 'RESUME' : 'SPEAK'}
              </motion.button>

              <button
                onClick={handlePause}
                disabled={!isSpeaking}
                className={`px-4 py-2.5 rounded-xl border text-xs font-mono font-bold transition-all flex items-center gap-2 ${
                  isSpeaking
                    ? 'bg-white/10 text-white border-white/20 hover:bg-white/20 cursor-pointer'
                    : 'bg-white/5 text-zinc-600 border-white/5 cursor-not-allowed'
                }`}
              >
                <RiPauseFill size={16} /> {isPaused ? 'UNPAUSE' : 'PAUSE'}
              </button>

              <button
                onClick={handleStop}
                disabled={!isSpeaking && !isPaused}
                className={`px-4 py-2.5 rounded-xl border text-xs font-mono font-bold transition-all flex items-center gap-2 ${
                  isSpeaking || isPaused
                    ? 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20 cursor-pointer'
                    : 'bg-white/5 text-zinc-600 border-white/5 cursor-not-allowed'
                }`}
              >
                <RiStopFill size={16} /> STOP
              </button>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="flex flex-col gap-2">
            <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest font-mono">
              Quick Vocal Presets
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {QUICK_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => setText(prompt)}
                  className="p-3 rounded-xl bg-zinc-950/30 hover:bg-white/5 border border-white/5 hover:border-white/15 text-left text-xs text-zinc-300 hover:text-white transition-all line-clamp-2 cursor-pointer"
                >
                  "{prompt}"
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right 1 Col: Voice Configuration & Sliders */}
        <div className="flex flex-col gap-4">
          <div className="p-5 rounded-2xl bg-zinc-950/40 backdrop-blur-md border border-white/10 flex flex-col gap-5 shadow-lg">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="text-xs font-bold text-zinc-300 uppercase tracking-widest font-mono flex items-center gap-2">
                <RiSettings3Line style={{ color: primaryColor }} /> Voice Parameters
              </span>
            </div>

            {/* Voice Dropdown */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-300">Installed Speech Synthesizer</label>
              <select
                value={selectedVoiceURI}
                onChange={(e) => setSelectedVoiceURI(e.target.value)}
                className="w-full bg-zinc-900/90 border border-white/10 rounded-xl px-3 py-2.5 text-xs font-mono text-zinc-200 outline-none focus:border-white/30 cursor-pointer"
              >
                {voices.map((v) => (
                  <option key={v.voiceURI} value={v.voiceURI} className="bg-zinc-900 text-zinc-200">
                    {v.name} ({v.lang})
                  </option>
                ))}
              </select>
            </div>

            {/* Speed / Rate Slider */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-zinc-300">Speech Rate</span>
                <span className="font-mono font-bold" style={{ color: primaryColor }}>
                  {rate.toFixed(1)}x
                </span>
              </div>
              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={rate}
                onChange={(e) => setRate(parseFloat(e.target.value))}
                className="w-full cursor-pointer"
                style={{ accentColor: primaryColor }}
              />
              <div className="flex justify-between text-[9px] font-mono text-zinc-500">
                <span>0.5x (Slow)</span>
                <span>1.0x (Normal)</span>
                <span>2.0x (Fast)</span>
              </div>
            </div>

            {/* Pitch Slider */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-zinc-300">Voice Pitch</span>
                <span className="font-mono font-bold" style={{ color: primaryColor }}>
                  {pitch.toFixed(1)}
                </span>
              </div>
              <input
                type="range"
                min="0.5"
                max="1.8"
                step="0.1"
                value={pitch}
                onChange={(e) => setPitch(parseFloat(e.target.value))}
                className="w-full cursor-pointer"
                style={{ accentColor: primaryColor }}
              />
              <div className="flex justify-between text-[9px] font-mono text-zinc-500">
                <span>Deep</span>
                <span>Natural</span>
                <span>High</span>
              </div>
            </div>

            {/* Volume Slider */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-zinc-300">Volume Output</span>
                <span className="font-mono font-bold" style={{ color: primaryColor }}>
                  {Math.round(volume * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1.0"
                step="0.05"
                value={volume}
                onChange={(e) => setVolume(parseFloat(e.target.value))}
                className="w-full cursor-pointer"
                style={{ accentColor: primaryColor }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TextToSpeechModule
