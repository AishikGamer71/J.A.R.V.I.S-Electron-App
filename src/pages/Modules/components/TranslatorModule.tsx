import React, { useState } from 'react'
import { motion } from 'framer-motion'
import {
  RiTranslate2,
  RiArrowLeftRightLine,
  RiFileCopyLine,
  RiDeleteBin7Line,
  RiVolumeUpLine,
  RiCheckLine,
  RiSparklingLine,
  RiLoader4Line
} from 'react-icons/ri'
import { useSettingsStore } from '@/store/settings-store'
import { hexToRgba } from '@/services/theme-manager'

const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Spanish' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'it', name: 'Italian' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'ru', name: 'Russian' },
  { code: 'ja', name: 'Japanese' },
  { code: 'zh', name: 'Chinese (Simplified)' },
  { code: 'hi', name: 'Hindi' },
  { code: 'ar', name: 'Arabic' },
  { code: 'ko', name: 'Korean' }
]

const SAMPLE_PHRASES = [
  { label: 'System Briefing', text: 'All security protocols and autonomous background services are running normally.' },
  { label: 'Greeting', text: 'Good morning. How may I assist you with your projects today?' },
  { label: 'Emergency Protocol', text: 'Critical alert: Unauthorized access attempt blocked at firewall level.' },
  { label: 'Hardware Diagnostic', text: 'CPU and GPU temperatures are within optimal operating thresholds.' }
]

export const TranslatorModule: React.FC = () => {
  const theme = useSettingsStore((state) => state.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  const [sourceText, setSourceText] = useState('Hello JARVIS, please analyze the real-time system metrics.')
  const [translatedText, setTranslatedText] = useState('Hola JARVIS, por favor analiza las métricas del sistema en tiempo real.')
  const [sourceLang, setSourceLang] = useState('en')
  const [targetLang, setTargetLang] = useState('es')
  const [isTranslating, setIsTranslating] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleTranslate = async () => {
    if (!sourceText.trim()) {
      setTranslatedText('')
      return
    }

    setIsTranslating(true)
    try {
      // Use MyMemory public translation API
      const res = await fetch(
        `https://api.mymemory.translated.net/get?q=${encodeURIComponent(
          sourceText
        )}&langpair=${sourceLang}|${targetLang}`
      )
      const data = await res.json()
      if (data?.responseData?.translatedText) {
        setTranslatedText(data.responseData.translatedText)
      } else {
        // Fallback placeholder
        setTranslatedText(`[Translated (${targetLang})]: ${sourceText}`)
      }
    } catch (e) {
      console.warn('Translation API error, fallback to demo mode:', e)
      setTranslatedText(`[Translated (${targetLang})]: ${sourceText}`)
    } finally {
      setIsTranslating(false)
    }
  }

  const handleSwap = () => {
    setSourceLang(targetLang)
    setTargetLang(sourceLang)
    setSourceText(translatedText)
    setTranslatedText(sourceText)
  }

  const handleSpeak = (textToSpeak: string, langCode: string) => {
    if (!textToSpeak) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(textToSpeak)
    const voices = window.speechSynthesis.getVoices()
    const matchingVoice = voices.find((v) => v.lang.toLowerCase().startsWith(langCode.toLowerCase()))
    if (matchingVoice) utterance.voice = matchingVoice
    window.speechSynthesis.speak(utterance)
  }

  const handleCopy = () => {
    if (!translatedText) return
    navigator.clipboard.writeText(translatedText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="h-full flex flex-col gap-6 overflow-y-auto pr-2 scrollbar-small">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2.5">
            <RiTranslate2 style={{ color: primaryColor }} size={24} />
            Universal AI Translator
          </h3>
          <p className="text-xs text-zinc-400 font-mono mt-1">
            Real-time multi-language neural translation and dual-channel speech pronunciation.
          </p>
        </div>

        {/* Language Bar Controls */}
        <div className="flex items-center gap-2 bg-zinc-950/60 p-1.5 rounded-xl border border-white/10 shadow-lg">
          <select
            value={sourceLang}
            onChange={(e) => setSourceLang(e.target.value)}
            className="bg-zinc-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs font-mono text-zinc-200 outline-none cursor-pointer"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>

          <button
            onClick={handleSwap}
            className="p-2 rounded-lg hover:bg-white/10 text-zinc-400 hover:text-white transition-colors cursor-pointer"
            title="Swap Languages"
          >
            <RiArrowLeftRightLine size={16} />
          </button>

          <select
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            className="bg-zinc-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs font-mono text-zinc-200 outline-none cursor-pointer"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Translation Dual-Column Container */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Source Box */}
        <div className="p-5 rounded-2xl bg-zinc-950/40 backdrop-blur-md border border-white/10 flex flex-col justify-between gap-4 shadow-lg min-h-[280px]">
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
              <span className="text-xs font-bold text-zinc-300 uppercase tracking-widest font-mono">
                Source ({LANGUAGES.find((l) => l.code === sourceLang)?.name})
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleSpeak(sourceText, sourceLang)}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                  title="Listen in Source Voice"
                >
                  <RiVolumeUpLine size={16} />
                </button>
                <button
                  onClick={() => setSourceText('')}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-red-400 transition-colors cursor-pointer"
                  title="Clear"
                >
                  <RiDeleteBin7Line size={16} />
                </button>
              </div>
            </div>

            <textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="Enter text to translate..."
              rows={6}
              className="w-full bg-transparent border-none outline-none text-sm text-zinc-100 placeholder:text-zinc-600 resize-none font-sans leading-relaxed scrollbar-small"
            />
          </div>

          <div className="flex justify-between items-center pt-3 border-t border-white/10">
            <span className="text-[10px] font-mono text-zinc-500">{sourceText.length} characters</span>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleTranslate}
              disabled={isTranslating}
              className="px-6 py-2 rounded-xl font-mono text-xs font-bold transition-all shadow-lg flex items-center gap-2 cursor-pointer text-black"
              style={{
                backgroundColor: primaryColor,
                boxShadow: `0 0 15px ${hexToRgba(primaryColor, 0.35)}`
              }}
            >
              {isTranslating ? (
                <>
                  <RiLoader4Line className="animate-spin" size={16} /> TRANSLATING...
                </>
              ) : (
                <>
                  <RiSparklingLine size={16} /> TRANSLATE
                </>
              )}
            </motion.button>
          </div>
        </div>

        {/* Output Box */}
        <div
          className="p-5 rounded-2xl backdrop-blur-md border flex flex-col justify-between gap-4 shadow-lg min-h-[280px]"
          style={{
            backgroundColor: hexToRgba(primaryColor, 0.04),
            borderColor: hexToRgba(primaryColor, 0.25)
          }}
        >
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
              <span className="text-xs font-bold uppercase tracking-widest font-mono" style={{ color: primaryColor }}>
                Translation ({LANGUAGES.find((l) => l.code === targetLang)?.name})
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleSpeak(translatedText, targetLang)}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                  title="Listen Pronunciation"
                >
                  <RiVolumeUpLine size={16} />
                </button>
                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded-md hover:bg-white/10 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                  title="Copy Translation"
                >
                  {copied ? <RiCheckLine size={16} style={{ color: primaryColor }} /> : <RiFileCopyLine size={16} />}
                </button>
              </div>
            </div>

            <div className="min-h-[140px] text-sm text-zinc-100 leading-relaxed font-sans select-text">
              {isTranslating ? (
                <div className="flex items-center gap-2 text-zinc-500 font-mono text-xs animate-pulse py-8">
                  <RiLoader4Line className="animate-spin" size={18} style={{ color: primaryColor }} />
                  Synthesizing neural translation matrix...
                </div>
              ) : (
                translatedText || <span className="text-zinc-600 italic">Translated result will appear here...</span>
              )}
            </div>
          </div>

          <div className="flex justify-between items-center pt-3 border-t border-white/10">
            <span className="text-[10px] font-mono text-zinc-500">
              {translatedText.length} characters
            </span>
            <span className="text-[10px] font-mono text-emerald-400">NEURAL ENGINE ACTIVE</span>
          </div>
        </div>
      </div>

      {/* Preset Phrases */}
      <div className="flex flex-col gap-2">
        <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest font-mono">
          Quick Translation Samples
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {SAMPLE_PHRASES.map((item, idx) => (
            <button
              key={idx}
              onClick={() => {
                setSourceText(item.text)
              }}
              className="p-3 rounded-xl bg-zinc-950/40 hover:bg-white/5 border border-white/5 hover:border-white/20 text-left transition-all cursor-pointer flex flex-col gap-1"
            >
              <span className="text-[10px] font-mono uppercase font-bold text-zinc-400">{item.label}</span>
              <span className="text-xs text-zinc-300 line-clamp-2">"{item.text}"</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default TranslatorModule
