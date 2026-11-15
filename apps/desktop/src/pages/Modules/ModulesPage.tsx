import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  RiVolumeUpLine,
  RiMicLine,
  RiTranslate2,
  RiBookOpenLine,
  RiCpuLine,
  RiRecordCircleLine
} from 'react-icons/ri'
import { useSettingsStore } from '@/store/settings-store'
import { hexToRgba } from '@/services/theme-manager'
import TextToSpeechModule from './components/TextToSpeechModule'
import SpeechToTextModule from './components/SpeechToTextModule'
import TranslatorModule from './components/TranslatorModule'
import DigitalDocsModule from './components/DigitalDocsModule'

type ModuleType = 'tts' | 'stt' | 'translator' | 'docs'

interface ModuleItem {
  id: ModuleType
  name: string
  subtitle: string
  icon: any
}

const MODULE_LIST: ModuleItem[] = [
  {
    id: 'tts',
    name: 'Text-to-Speech',
    subtitle: 'Vocal Synthesis Engine',
    icon: <RiVolumeUpLine size={20} />
  },
  {
    id: 'stt',
    name: 'Speech-to-Text',
    subtitle: 'Microphone Dictation Stream',
    icon: <RiMicLine size={20} />
  },
  {
    id: 'translator',
    name: 'Translator',
    subtitle: 'Multi-Language AI Matrix',
    icon: <RiTranslate2 size={20} />
  },
  {
    id: 'docs',
    name: 'Digital Documentation',
    subtitle: 'System Manuals & Scratchpad',
    icon: <RiBookOpenLine size={20} />
  }
]

export const ModulesPage: React.FC = () => {
  const [activeModule, setActiveModule] = useState<ModuleType>('tts')
  const theme = useSettingsStore((state) => state.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  return (
    <div className="flex-1 p-6 md:p-8 lg:p-10 flex flex-col md:flex-row bg-transparent h-full text-zinc-100 overflow-hidden">
      <motion.div
        className="w-full max-w-7xl mx-auto flex flex-col md:flex-row gap-8 h-full"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {/* LEFT SIDEBAR: MODULE SELECTOR */}
        <div className="w-full md:w-72 flex flex-col gap-6 flex-shrink-0 md:border-r md:border-white/5 md:pr-6">
          {/* Header Badge */}
          <div className="flex items-center gap-4 pb-6 border-b border-white/10">
            <div
              className="p-3 rounded-xl border flex items-center justify-center shadow-lg transition-all"
              style={{
                backgroundColor: hexToRgba(primaryColor, 0.1),
                borderColor: hexToRgba(primaryColor, 0.3)
              }}
            >
              <RiCpuLine size={28} style={{ color: primaryColor }} />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white leading-tight">
                Neural
                <br />
                Modules
              </h2>
              <p className="text-[10px] text-zinc-400 font-mono mt-1.5 tracking-widest flex items-center gap-1.5 uppercase">
                <RiRecordCircleLine
                  className="animate-pulse"
                  style={{ color: primaryColor }}
                  size={12}
                />
                Subsystems Ready
              </p>
            </div>
          </div>

          {/* Module Buttons List */}
          <div className="flex flex-row md:flex-col gap-2 overflow-x-auto md:overflow-visible pb-2 md:pb-0 scrollbar-small">
            {MODULE_LIST.map((mod) => {
              const isSelected = activeModule === mod.id
              return (
                <button
                  key={mod.id}
                  onClick={() => setActiveModule(mod.id)}
                  className={`relative p-3.5 rounded-2xl border text-left transition-all duration-300 cursor-pointer overflow-hidden z-20 flex items-center gap-3.5 flex-shrink-0 w-auto md:w-full ${
                    isSelected
                      ? 'border shadow-lg scale-[1.01]'
                      : 'bg-zinc-950/30 border-white/5 text-zinc-400 hover:text-white hover:bg-white/5 hover:border-white/15'
                  }`}
                  style={
                    isSelected
                      ? {
                          color: '#ffffff',
                          backgroundColor: hexToRgba(primaryColor, 0.1),
                          borderColor: hexToRgba(primaryColor, 0.35),
                          boxShadow: `0 0 15px ${hexToRgba(primaryColor, 0.15)}`
                        }
                      : {}
                  }
                >
                  {isSelected && (
                    <motion.div
                      layoutId="activeModuleGlow"
                      className="absolute inset-0 rounded-2xl -z-10"
                      style={{
                        backgroundColor: hexToRgba(primaryColor, 0.08)
                      }}
                      transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                    />
                  )}
                  <div
                    className="p-2 rounded-xl border flex items-center justify-center"
                    style={{
                      backgroundColor: isSelected
                        ? hexToRgba(primaryColor, 0.2)
                        : 'rgba(255, 255, 255, 0.04)',
                      borderColor: isSelected
                        ? hexToRgba(primaryColor, 0.4)
                        : 'rgba(255, 255, 255, 0.08)',
                      color: isSelected ? primaryColor : '#a1a1aa'
                    }}
                  >
                    {mod.icon}
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold font-mono tracking-wide text-white">
                      {mod.name}
                    </span>
                    <span className="text-[10px] text-zinc-400 font-mono line-clamp-1">
                      {mod.subtitle}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* RIGHT SECTION: ACTIVE FUNCTIONAL WORKSPACE */}
        <div className="flex-1 relative overflow-y-auto scrollbar-small pr-2 md:pr-4 pb-12 mt-2 md:mt-0 min-h-[500px]">
          <AnimatePresence mode="wait">
            {activeModule === 'tts' && (
              <motion.div
                key="tts"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                <TextToSpeechModule />
              </motion.div>
            )}

            {activeModule === 'stt' && (
              <motion.div
                key="stt"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                <SpeechToTextModule />
              </motion.div>
            )}

            {activeModule === 'translator' && (
              <motion.div
                key="translator"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                <TranslatorModule />
              </motion.div>
            )}

            {activeModule === 'docs' && (
              <motion.div
                key="docs"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                <DigitalDocsModule />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  )
}

export default ModulesPage
