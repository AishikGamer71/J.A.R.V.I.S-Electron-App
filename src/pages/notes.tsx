import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  RiStickyNoteLine,
  RiDeleteBinLine,
  RiFileTextLine,
  RiMarkdownLine,
  RiAddLine,
  RiSave3Line,
  RiCloseLine,
  RiEditLine 
} from 'react-icons/ri'

interface Note {
  filename: string
  title: string
  content: string
  createdAt: Date
}

const MarkdownComponents = {
  code({ node, inline, className, children, ...props }: any) {
    return !inline ? (
      <div className="bg-black/50 rounded-lg p-3 my-2 border border-white/10 font-mono text-xs overflow-x-auto">
        <code {...props}>{children}</code>
      </div>
    ) : (
      <code
        className="bg-white/10 px-1 py-0.5 rounded text-emerald-400 font-mono text-xs"
        {...props}
      >
        {children}
      </code>
    )
  }
}

const NotesView = ({ glassPanel }: { glassPanel?: string }) => {
  const [notes, setNotes] = useState<Note[]>([])
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)

  const [isEditorOpen, setIsEditorOpen] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newContent, setNewContent] = useState('')
  const [editOriginalFilename, setEditOriginalFilename] = useState<string | null>(null)

  const fetchNotes = async () => {
    try {
      if (window.electron?.ipcRenderer) {
        const data = await window.electron.ipcRenderer.invoke('get-notes')
        if (Array.isArray(data)) setNotes(data)
      } else {
        const stored = localStorage.getItem('jarvis_notes')
        if (stored) {
          try {
            const parsed = JSON.parse(stored)
            if (Array.isArray(parsed)) setNotes(parsed)
          } catch {}
        }
      }
    } catch (e) {
    }
  }

  useEffect(() => {
    fetchNotes()
    const interval = setInterval(fetchNotes, 3000) 
    return () => clearInterval(interval)
  }, [])


  const startCreating = () => {
    setSelectedNote(null)
    setEditOriginalFilename(null)
    setNewTitle('')
    setNewContent('')
    setIsEditorOpen(true)
  }

  const startEditing = () => {
    if (!selectedNote) return

    setEditOriginalFilename(selectedNote.filename)
    setNewTitle(selectedNote.title)

    const cleanContent = selectedNote.content.replace(/^# .+\n\n/, '')
    setNewContent(cleanContent)

    setIsEditorOpen(true)
  }

  const cancelEditor = () => {
    setIsEditorOpen(false)
    setEditOriginalFilename(null)
  }

  const saveManualNote = async () => {
    if (!newTitle.trim() || !newContent.trim()) return

    if (window.electron?.ipcRenderer) {
      await window.electron.ipcRenderer.invoke('save-note', {
        title: newTitle,
        content: newContent
      })
    } else {
      const stored = localStorage.getItem('jarvis_notes')
      const currentList = stored ? JSON.parse(stored) : []
      const newNote = {
        filename: `${Date.now()}_note.md`,
        title: newTitle,
        content: newContent,
        lastModified: new Date().toISOString()
      }
      localStorage.setItem('jarvis_notes', JSON.stringify([newNote, ...currentList]))
    }

    setIsEditorOpen(false)
    setEditOriginalFilename(null)
    fetchNotes()

    setTimeout(() => {
      if (window.electron?.ipcRenderer) {
        window.electron.ipcRenderer.invoke('get-notes').then((data: Note[]) => {
          const created = data?.find((n) =>
            n.title.toLowerCase().includes(newTitle.toLowerCase().replace(/ /g, '_'))
          )
          if (created) setSelectedNote(created)
        }).catch(() => {})
      }
    }, 500)
  }

  const deleteNote = async (filename: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.electron?.ipcRenderer) {
      await window.electron.ipcRenderer.invoke('delete-note', filename)
    } else {
      const stored = localStorage.getItem('jarvis_notes')
      if (stored) {
        const currentList = JSON.parse(stored)
        localStorage.setItem('jarvis_notes', JSON.stringify(currentList.filter((n: any) => n.filename !== filename)))
      }
    }
    fetchNotes()
    if (selectedNote?.filename === filename) setSelectedNote(null)
  }

  return (
    <div className="h-full w-full flex bg-transparent text-zinc-100 font-sans select-none overflow-hidden p-4 gap-4 animate-in fade-in duration-500">
      {/* LEFT SIDEBAR (Memory Bank) */}
      <div className="w-[280px] bg-black/40 backdrop-blur-md border border-emerald-500/20 rounded-xl flex flex-col shadow-2xl overflow-hidden shrink-0">
        <div className="p-4 pl-4 border-b border-emerald-500/20 bg-emerald-500/5 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
              <RiStickyNoteLine size={18} />
            </div>
            <div>
              <h2 className="text-sm font-black tracking-widest text-emerald-400 uppercase drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]">
                Memory Bank
              </h2>
              <span className="text-[9px] text-zinc-500 font-mono tracking-widest">{notes.length} ITEMS</span>
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={startCreating}
            className="p-1.5 bg-emerald-500/10 text-emerald-400 rounded-lg hover:bg-emerald-500 hover:text-black border border-emerald-500/30 transition-all cursor-pointer"
            title="Create Manual Note"
          >
            <RiAddLine size={16} />
          </motion.button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1.5 p-3 scrollbar-small">
          {notes.length === 0 ? (
            <div className="text-center text-zinc-400 text-xs mt-10">
              <p>No memories saved.</p>
              <p className="mt-2 opacity-50 font-mono text-[10px]">Click + or ask JARVIS.</p>
            </div>
          ) : (
            notes.map((note) => {
              const isSelected = selectedNote?.filename === note.filename && !isEditorOpen
              return (
                <div
                  key={note.filename}
                  onClick={() => {
                    setIsEditorOpen(false)
                    setSelectedNote(note)
                  }}
                  className={`group relative p-3 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                      : 'bg-black/20 border-emerald-500/10 hover:bg-emerald-500/5 hover:border-emerald-500/20 text-zinc-300'
                  }`}
                >
                  {isSelected && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.8)] rounded-l" />
                  )}
                  <div className="overflow-hidden pl-1">
                    <h3
                      className={`text-xs font-bold truncate ${isSelected ? 'text-emerald-300' : 'text-zinc-200'}`}
                    >
                      {note.title.toUpperCase()}
                    </h3>
                    <p className="text-[9px] text-zinc-500 mt-0.5 font-mono">
                      {new Date(note.createdAt).toLocaleDateString()}
                    </p>
                  </div>

                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={(e) => deleteNote(note.filename, e)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all cursor-pointer"
                  >
                    <RiDeleteBinLine size={13} />
                  </motion.button>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* MAIN CONTENT AREA (Glassmorphism matching Task Manager) */}
      <div className="flex-1 flex flex-col relative overflow-hidden bg-black/40 backdrop-blur-md border border-emerald-500/20 rounded-xl shadow-2xl">
        {isEditorOpen ? (
          <div className="flex-1 flex flex-col p-6 md:p-8 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="flex items-center justify-between mb-4 border-b border-emerald-500/20 pb-4">
              <input
                type="text"
                placeholder="ENTER NOTE TITLE..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="bg-transparent border-none outline-none text-lg font-bold text-white placeholder-zinc-500 w-full tracking-wider"
                autoFocus
              />
              <div className="flex gap-2">
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={cancelEditor}
                  className="p-2 text-zinc-500 hover:text-white transition-colors cursor-pointer"
                >
                  <RiCloseLine size={20} />
                </motion.button>
              </div>
            </div>

            <textarea
              placeholder="Write your note in Markdown..."
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              className="flex-1 bg-transparent border-none outline-none resize-none text-sm font-mono text-zinc-50 placeholder-zinc-500 leading-relaxed p-2 scrollbar-small"
            />

            <div className="flex justify-end pt-4 border-t border-emerald-500/10">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={saveManualNote}
                disabled={!newTitle || !newContent}
                className="flex items-center gap-2 px-6 py-2 bg-emerald-500 text-black font-bold text-xs rounded-lg hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer shadow-lg"
              >
                <RiSave3Line /> {editOriginalFilename ? 'UPDATE MEMORY' : 'SAVE TO MEMORY'}
              </motion.button>
            </div>
          </div>
        ) : selectedNote ? (
          <>
            <div className="px-8 py-4 border-b border-emerald-500/10 flex items-center justify-between shrink-0 bg-emerald-500/[0.02]">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
                  <RiMarkdownLine size={18} />
                </div>
                <div>
                  <h2 className="text-sm font-black tracking-widest text-emerald-400 uppercase drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]">
                    {selectedNote.title}
                  </h2>
                  <p className="text-[9px] text-zinc-500 font-mono tracking-widest">
                    CREATED {new Date(selectedNote.createdAt).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20">
                  READ ONLY
                </span>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={startEditing}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-bold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg transition-all cursor-pointer"
                  title="Edit Note"
                >
                  <RiEditLine size={14} /> EDIT
                </motion.button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-8 scrollbar-small bg-transparent">
              <div className="prose prose-invert prose-sm max-w-none text-zinc-300">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents}>
                  {selectedNote.content}
                </ReactMarkdown>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 gap-4">
            <RiFileTextLine size={48} className="opacity-30 text-emerald-500/50" />
            <span className="text-xs tracking-widest opacity-60 font-mono">
              SELECT A DATA NODE OR CREATE NEW
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export default NotesView
