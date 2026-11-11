import React, { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import {
  RiMicLine,
  RiMicFill,
  RiMicOffLine,
  RiFileCopyLine,
  RiDeleteBin7Line,
  RiDownload2Line,
  RiCheckLine,
  RiGlobalLine,
  RiVoiceprintLine,
  RiPauseFill,
  RiPlayFill
} from 'react-icons/ri'
import { useSettingsStore } from '@/store/settings-store'
import { hexToRgba } from '@/services/theme-manager'

const SUPPORTED_LANGUAGES = [
  { code: 'en-US', name: 'English (United States)' },
  { code: 'en-GB', name: 'English (United Kingdom)' },
  { code: 'en-IN', name: 'English (India)' },
  { code: 'es-ES', name: 'Spanish (Spain)' },
  { code: 'fr-FR', name: 'French (France)' },
  { code: 'de-DE', name: 'German (Germany)' },
  { code: 'ja-JP', name: 'Japanese (Japan)' },
  { code: 'zh-CN', name: 'Chinese (Mandarin)' },
  { code: 'hi-IN', name: 'Hindi (India)' },
  { code: 'ru-RU', name: 'Russian (Russia)' }
]

export const SpeechToTextModule: React.FC = () => {
  const theme = useSettingsStore((state) => state.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [interimText, setInterimText] = useState('')
  const [selectedLang, setSelectedLang] = useState('en-US')
  const [continuous, setContinuous] = useState(true)
  const [copied, setCopied] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) {
      setErrorMsg('Speech Recognition API is not supported in this browser/environment.')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = continuous
    recognition.interimResults = true
    recognition.lang = selectedLang

    recognition.onresult = (event: any) => {
      let finalStr = ''
      let interimStr = ''

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalStr += event.results[i][0].transcript + ' '
        } else {
          interimStr += event.results[i][0].transcript
        }
      }

      if (finalStr) {
        setTranscript((prev) => prev + finalStr)
      }
      setInterimText(interimStr)
    }

    recognition.onerror = (event: any) => {
      console.warn('Speech Recognition error', event.error)
      if (event.error !== 'no-speech') {
        setErrorMsg(`Speech Error: ${event.error}`)
      }
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
      setInterimText('')
    }

    recognitionRef.current = recognition

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
    }
  }, [selectedLang, continuous])

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Speech Recognition is not available.')
      return
    }

    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      setErrorMsg('')
      try {
        recognitionRef.current.lang = selectedLang
        recognitionRef.current.continuous = continuous
        recognitionRef.current.start()
        setIsListening(true)
      } catch (err: any) {
        console.error('Error starting recognition:', err)
        setErrorMsg('Microphone initialization failed or was blocked.')
      }
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(transcript + (interimText ? ' ' + interimText : ''))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const fullText = transcript + (interimText ? '\n' + interimText : '')
    const blob = new Blob([fullText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `JARVIS_Transcription_${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="h-full flex flex-col gap-6 overflow-y-auto pr-2 scrollbar-small">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2.5">
            <RiMicLine style={{ color: primaryColor }} size={24} />
            Speech-to-Text Transcription Engine
          </h3>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Real-time vocal microphone input converted into continuous textual transcripts.
          </p>
        </div>

        {/* Live Audio Input Status Badge */}
        <div
          className="flex items-center gap-2 px-4 py-2 rounded-xl border backdrop-blur-md"
          style={{
            backgroundColor: hexToRgba(primaryColor, 0.08),
            borderColor: hexToRgba(primaryColor, 0.3)
          }}
        >
          <div
            className={`w-2.5 h-2.5 rounded-full ${isListening ? 'animate-ping' : ''}`}
            style={{ backgroundColor: isListening ? '#ef4444' : '#71717a' }}
          />
          <span
            className="text-xs font-mono font-bold tracking-widest uppercase"
            style={{ color: isListening ? '#ef4444' : '#a1a1aa' }}
          >
            {isListening ? 'MIC ACTIVE • RECORDING' : 'MIC IDLE'}
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {/* Main Container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Transcript Box & Microphone Trigger */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="p-5 rounded-2xl bg-zinc-950/40 backdrop-blur-md border border-white/10 flex flex-col gap-4 shadow-lg">
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
              <span className="text-xs font-bold text-zinc-300 uppercase tracking-widest font-mono flex items-center gap-2">
                <RiVoiceprintLine style={{ color: primaryColor }} /> Live Transcription Stream
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
                  title="Copy transcript"
                >
                  {copied ? <RiCheckLine size={15} style={{ color: primaryColor }} /> : <RiFileCopyLine size={15} />}
                </button>
                <button
                  onClick={handleDownload}
                  disabled={!transcript && !interimText}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white transition-colors disabled:opacity-30 cursor-pointer"
                  title="Download transcript as .txt"
                >
                  <RiDownload2Line size={15} />
                </button>
                <button
                  onClick={() => {
                    setTranscript('')
                    setInterimText('')
                  }}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-red-400 transition-colors"
                  title="Clear transcript"
                >
                  <RiDeleteBin7Line size={15} />
                </button>
              </div>
            </div>

            {/* Transcript Text Box */}
            <div className="min-h-[220px] max-h-[350px] overflow-y-auto p-4 rounded-xl bg-black/40 border border-white/5 font-mono text-sm leading-relaxed scrollbar-small">
              {transcript || interimText ? (
                <div>
                  <span className="text-zinc-100">{transcript}</span>
                  {interimText && (
                    <span className="text-zinc-500 italic opacity-80 animate-pulse">
                      {interimText}
                    </span>
                  )}
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-zinc-600 text-xs py-10 gap-2">
                  <RiMicLine size={28} className="opacity-40" />
                  <span>Press "START LISTENING" or the microphone button to dictate...</span>
                </div>
              )}
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-white/10">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleListening}
                className="px-6 py-3 rounded-xl font-mono text-xs font-bold transition-all shadow-lg flex items-center gap-2 cursor-pointer text-white"
                style={{
                  backgroundColor: isListening ? '#ef4444' : primaryColor,
                  boxShadow: `0 0 20px ${hexToRgba(isListening ? '#ef4444' : primaryColor, 0.4)}`,
                  color: isListening ? '#ffffff' : '#000000'
                }}
              >
                {isListening ? <RiMicOffLine size={18} /> : <RiMicFill size={18} />}
                {isListening ? 'STOP RECORDING' : 'START LISTENING'}
              </motion.button>

              <div className="flex items-center gap-3 text-xs font-mono text-zinc-400">
                <span>{transcript.trim().split(/\s+/).filter(Boolean).length} WORDS</span>
                <span>•</span>
                <span>{transcript.length} CHARS</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Audio & Recognition Settings */}
        <div className="flex flex-col gap-4">
          <div className="p-5 rounded-2xl bg-zinc-950/40 backdrop-blur-md border border-white/10 flex flex-col gap-5 shadow-lg">
            <span className="text-xs font-bold text-zinc-300 uppercase tracking-widest font-mono flex items-center gap-2 border-b border-white/5 pb-2">
              <RiGlobalLine style={{ color: primaryColor }} /> Recognition Settings
            </span>

            {/* Recognition Language */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-300">Spoken Language Dialect</label>
              <select
                value={selectedLang}
                onChange={(e) => setSelectedLang(e.target.value)}
                className="w-full bg-zinc-900/90 border border-white/10 rounded-xl px-3 py-2.5 text-xs font-mono text-zinc-200 outline-none focus:border-white/30 cursor-pointer"
              >
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code} className="bg-zinc-900 text-zinc-200">
                    {lang.name} ({lang.code})
                  </option>
                ))}
              </select>
            </div>

            {/* Continuous Transcription */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
              <div className="flex flex-col">
                <span className="text-xs font-semibold text-zinc-200">Continuous Dictation</span>
                <span className="text-[10px] text-zinc-500 font-mono">Keep listening without stopping</span>
              </div>
              <button
                onClick={() => setContinuous(!continuous)}
                className="w-12 h-6 rounded-full p-1 transition-colors cursor-pointer"
                style={{ backgroundColor: continuous ? primaryColor : '#3f3f46' }}
              >
                <div
                  className={`w-4 h-4 bg-white rounded-full transition-transform ${
                    continuous ? 'translate-x-6' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Live Frequency Visualizer */}
            <div className="p-4 rounded-xl bg-black/40 border border-white/5 flex flex-col items-center justify-center gap-3">
              <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
                Acoustic Frequency Monitor
              </span>
              <div className="flex items-end justify-center gap-1.5 h-12 w-full px-4">
                {[0.2, 0.5, 0.9, 1.2, 0.7, 1.4, 0.8, 1.1, 0.4, 1.3, 0.6, 0.3].map((heightScale, idx) => (
                  <motion.div
                    key={idx}
                    className="flex-1 rounded-full max-w-[8px]"
                    style={{ backgroundColor: isListening ? primaryColor : '#3f3f46' }}
                    animate={
                      isListening
                        ? {
                            height: [`${heightScale * 15}px`, `${heightScale * 45}px`, `${heightScale * 10}px`]
                          }
                        : { height: '6px' }
                    }
                    transition={{
                      repeat: Infinity,
                      duration: 0.6,
                      delay: idx * 0.05
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SpeechToTextModule
