import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RiArrowDownSLine, RiCheckLine } from 'react-icons/ri'

export type OptionGroup = {
  label: string
  options: { label: string, value: string }[]
}

export type SelectOption = { label: string, value: string }

type CustomSelectProps = {
  value: string
  onChange: (val: string) => void
  options?: SelectOption[]
  groups?: OptionGroup[]
}

export const CustomSelect = ({ value, onChange, options, groups }: CustomSelectProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  let selectedLabel = value
  if (options) {
    const opt = options.find(o => o.value === value)
    if (opt) selectedLabel = opt.label
  } else if (groups) {
    for (const g of groups) {
      const opt = g.options.find(o => o.value === value)
      if (opt) selectedLabel = opt.label
    }
  }

  return (
    <div className="relative w-full text-[11px]" ref={containerRef}>
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="bg-zinc-950/40 backdrop-blur-md border border-white/10 hover:border-emerald-500/50 rounded-lg p-2 flex items-center justify-between cursor-pointer transition-colors text-zinc-200 font-bold"
      >
        <span className="truncate">{selectedLabel}</span>
        <RiArrowDownSLine size={16} className={`transition-transform duration-300 ${isOpen ? 'rotate-180 text-emerald-500' : 'text-zinc-400'}`} />
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 right-0 mt-1 bg-[#050505] border border-white/10 rounded-lg shadow-xl z-[100] max-h-60 overflow-y-auto scrollbar-small"
          >
            {options && options.map((opt) => (
              <div
                key={opt.value}
                onClick={() => { onChange(opt.value); setIsOpen(false) }}
                className={`p-2 px-3 cursor-pointer transition-colors flex items-center justify-between ${value === opt.value ? 'bg-emerald-500/20 text-emerald-400' : 'hover:bg-white/10 text-zinc-300'}`}
              >
                {opt.label}
                {value === opt.value && <RiCheckLine size={12} />}
              </div>
            ))}

            {groups && groups.map((g, i) => (
              <div key={g.label} className={i !== 0 ? 'border-t border-white/5 mt-1 pt-1' : ''}>
                <div className="px-3 py-1.5 text-[9px] font-bold tracking-widest text-zinc-500 uppercase">
                  {g.label}
                </div>
                {g.options.map(opt => (
                  <div
                    key={opt.value}
                    onClick={() => { onChange(opt.value); setIsOpen(false) }}
                    className={`p-2 px-4 cursor-pointer transition-colors flex items-center justify-between ${value === opt.value ? 'bg-emerald-500/20 text-emerald-400' : 'hover:bg-white/10 text-zinc-300'}`}
                  >
                    {opt.label}
                    {value === opt.value && <RiCheckLine size={12} />}
                  </div>
                ))}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
