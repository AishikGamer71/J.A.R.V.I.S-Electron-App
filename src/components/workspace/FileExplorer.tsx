import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  RiFolderLine,
  RiFolderOpenLine,
  RiFileCodeLine,
  RiFileLine,
  RiArrowRightSLine,
  RiRefreshLine,
  RiFolderOpenFill,
  RiSearchLine,
  RiCloseLine,
  RiLoader4Line,
  RiSubtractLine,
  RiCodeSSlashLine
} from 'react-icons/ri'
import { useSettingsStore } from '@/store/settings-store'
import { useWorkspaceStore } from '@/store/workspace-store'
import { hexToRgba } from '@/services/theme-manager'

export interface FileItem {
  name: string
  type: string
  path: string
  info: string
}

export interface DirectoryResponse {
  directory: string
  items_found: number
  content: FileItem[]
}

export interface FileExplorerProps {
  projectPath?: string | null
  onSelectFile?: (filePath: string) => void
  selectedFilePath?: string | null
  className?: string
}

const CODE_EXTENSIONS = new Set([
  'ts',
  'tsx',
  'js',
  'jsx',
  'mjs',
  'cjs',
  'py',
  'pyw',
  'pyi',
  'java',
  'kt',
  'kts',
  'scala',
  'groovy',
  'c',
  'cpp',
  'cc',
  'cxx',
  'h',
  'hpp',
  'hh',
  'hxx',
  'cs',
  'rs',
  'go',
  'html',
  'htm',
  'xhtml',
  'css',
  'scss',
  'sass',
  'less',
  'json',
  'jsonc',
  'json5',
  'yaml',
  'yml',
  'toml',
  'xml',
  'sql',
  'sh',
  'bash',
  'zsh',
  'bat',
  'cmd',
  'ps1',
  'psm1',
  'md',
  'mdx',
  'markdown',
  'vue',
  'svelte',
  'astro',
  'graphql',
  'gql',
  'php',
  'rb',
  'swift',
  'dart',
  'lua',
  'r',
  'env'
])

function isCodeFile(filename: string, type: string): boolean {
  if (type === 'text') return true
  const lower = filename.toLowerCase()
  if (
    lower === 'dockerfile' ||
    lower === 'makefile' ||
    lower.startsWith('.env') ||
    lower === 'package.json' ||
    lower === 'tsconfig.json'
  ) {
    return true
  }
  const parts = lower.split('.')
  if (parts.length > 1) {
    const ext = parts.pop() || ''
    if (CODE_EXTENSIONS.has(ext)) return true
  }
  return false
}

function isFolderItem(item: FileItem): boolean {
  return item.info?.startsWith('[DIR]') || item.type === 'directory'
}

function extractFileSize(info: string): string | null {
  if (!info || info.startsWith('[DIR]')) return null
  const match = info.match(/\|\s*([^\]]+)\]/)
  return match ? match[1].trim() : null
}

function getBasename(pathStr: string): string {
  if (!pathStr) return ''
  const clean = pathStr.replace(/[\\/]+$/, '')
  const segments = clean.split(/[\\/]/).filter(Boolean)
  return segments.pop() || clean
}

interface TreeNodeProps {
  item: FileItem
  depth: number
  expandedFolders: Set<string>
  loadingPaths: Set<string>
  directoryCache: Record<string, FileItem[]>
  activeFilePath: string | null
  primaryColor: string
  searchFilter: string
  onToggleFolder: (path: string) => void
  onSelectFile: (path: string) => void
}

const TreeNode: React.FC<TreeNodeProps> = React.memo(
  ({
    item,
    depth,
    expandedFolders,
    loadingPaths,
    directoryCache,
    activeFilePath,
    primaryColor,
    searchFilter,
    onToggleFolder,
    onSelectFile
  }) => {
    const isFolder = isFolderItem(item)
    const isExpanded = expandedFolders.has(item.path)
    const isLoading = loadingPaths.has(item.path)
    const isSelected = !isFolder && activeFilePath === item.path
    const children = directoryCache[item.path]
    const fileSize = !isFolder ? extractFileSize(item.info) : null

    // Determine if file/folder matches search filter
    const isMatchingSearch = useMemo(() => {
      if (!searchFilter.trim()) return true
      const query = searchFilter.toLowerCase()
      if (item.name.toLowerCase().includes(query)) return true
      // If folder, check if any cached children match
      if (isFolder && children) {
        return children.some((c) => c.name.toLowerCase().includes(query))
      }
      return false
    }, [searchFilter, item.name, isFolder, children])

    if (!isMatchingSearch && searchFilter.trim()) {
      return null
    }

    const handleClick = (e: React.MouseEvent) => {
      e.stopPropagation()
      if (isFolder) {
        onToggleFolder(item.path)
      } else {
        onSelectFile(item.path)
      }
    }

    return (
      <div className="flex flex-col select-none">
        {/* Node Row */}
        <div
          onClick={handleClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              if (isFolder) onToggleFolder(item.path)
              else onSelectFile(item.path)
            }
          }}
          className={`group flex items-center justify-between py-1 px-1.5 rounded-md transition-all duration-150 cursor-pointer font-mono text-xs ${
            isSelected
              ? 'font-semibold border shadow-sm'
              : 'hover:bg-white/5 border border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
          style={{
            paddingLeft: `${depth * 14 + 6}px`,
            ...(isSelected
              ? {
                  backgroundColor: hexToRgba(primaryColor, 0.15),
                  borderColor: hexToRgba(primaryColor, 0.35),
                  color: primaryColor,
                  boxShadow: `0 0 10px ${hexToRgba(primaryColor, 0.15)}`
                }
              : {})
          }}
          title={item.path}
        >
          {/* Left item content: Arrow + Icon + Name */}
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            {/* Arrow chevron for folders */}
            {isFolder ? (
              <span
                className="w-3.5 h-3.5 flex items-center justify-center flex-shrink-0 text-zinc-500 group-hover:text-zinc-300"
                onClick={(e) => {
                  e.stopPropagation()
                  onToggleFolder(item.path)
                }}
              >
                <RiArrowRightSLine
                  className={`text-xs transition-transform duration-200 ${
                    isExpanded ? 'rotate-90 text-zinc-200' : ''
                  }`}
                  style={isExpanded ? { color: primaryColor } : undefined}
                />
              </span>
            ) : (
              <span className="w-3.5 h-3.5 flex-shrink-0" />
            )}

            {/* Main File/Folder Icon */}
            <span className="flex-shrink-0 flex items-center justify-center text-sm">
              {isFolder ? (
                isExpanded ? (
                  <RiFolderOpenLine
                    className="transition-colors duration-150"
                    style={{ color: primaryColor }}
                  />
                ) : (
                  <RiFolderLine className="text-zinc-400 group-hover:text-zinc-200 transition-colors duration-150" />
                )
              ) : isCodeFile(item.name, item.type) ? (
                <RiFileCodeLine
                  className="transition-colors duration-150"
                  style={{ color: isSelected ? primaryColor : '#38bdf8' }}
                />
              ) : (
                <RiFileLine
                  className="transition-colors duration-150"
                  style={{ color: isSelected ? primaryColor : '#a1a1aa' }}
                />
              )}
            </span>

            {/* Name */}
            <span
              className={`truncate text-xs tracking-tight ${
                isSelected
                  ? 'text-inherit font-semibold'
                  : isFolder && isExpanded
                    ? 'text-zinc-200 font-medium'
                    : 'text-zinc-300 group-hover:text-zinc-100'
              }`}
            >
              {item.name}
            </span>
          </div>

          {/* Right item content: Loading spinner or File size */}
          <div className="flex items-center gap-1 flex-shrink-0 ml-1">
            {isLoading && (
              <RiLoader4Line
                className="animate-spin text-xs"
                style={{ color: primaryColor }}
              />
            )}
            {fileSize && !isLoading && (
              <span className="text-[9px] font-mono text-zinc-500 group-hover:text-zinc-400 opacity-60 group-hover:opacity-100 transition-opacity">
                {fileSize}
              </span>
            )}
          </div>
        </div>

        {/* Child Subtree */}
        <AnimatePresence initial={false}>
          {isFolder && isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15, ease: 'easeInOut' }}
              className="overflow-hidden relative"
            >
              {/* Subtle vertical nesting guide line */}
              <div
                className="absolute top-0 bottom-0 border-l border-white/5 pointer-events-none"
                style={{ left: `${depth * 14 + 12}px` }}
              />

              {isLoading && (!children || children.length === 0) ? (
                <div
                  className="flex items-center gap-2 py-1 text-[10px] font-mono text-zinc-500 italic"
                  style={{ paddingLeft: `${(depth + 1) * 14 + 14}px` }}
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full animate-ping"
                    style={{ backgroundColor: primaryColor }}
                  />
                  <span>Loading contents...</span>
                </div>
              ) : children && children.length > 0 ? (
                <div className="flex flex-col">
                  {children.map((child) => (
                    <TreeNode
                      key={child.path}
                      item={child}
                      depth={depth + 1}
                      expandedFolders={expandedFolders}
                      loadingPaths={loadingPaths}
                      directoryCache={directoryCache}
                      activeFilePath={activeFilePath}
                      primaryColor={primaryColor}
                      searchFilter={searchFilter}
                      onToggleFolder={onToggleFolder}
                      onSelectFile={onSelectFile}
                    />
                  ))}
                </div>
              ) : (
                <div
                  className="py-1 text-[10px] font-mono text-zinc-600 italic"
                  style={{ paddingLeft: `${(depth + 1) * 14 + 14}px` }}
                >
                  (empty)
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    )
  }
)

TreeNode.displayName = 'TreeNode'

/**
 * FileExplorer — Collapsible Cyberpunk HUD File Tree for Code Workspace
 */
export const FileExplorer: React.FC<FileExplorerProps> = ({
  projectPath: propProjectPath,
  onSelectFile,
  selectedFilePath: propSelectedFilePath,
  className = ''
}) => {
  const storeProjectPath = useWorkspaceStore((s) => s.projectPath)
  const setStoreProjectPath = useWorkspaceStore((s) => s.setProjectPath)
  const theme = useSettingsStore((s) => s.theme)
  const primaryColor = theme?.primaryColor || '#10b981'

  const activePath = propProjectPath ?? storeProjectPath

  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
  const [directoryCache, setDirectoryCache] = useState<Record<string, FileItem[]>>({})
  const [loadingPaths, setLoadingPaths] = useState<Set<string>>(new Set())
  const [isRootLoading, setIsRootLoading] = useState<boolean>(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [searchFilter, setSearchFilter] = useState<string>('')
  const [isSearching, setIsSearching] = useState<boolean>(false)

  const activeSelectedFilePath = propSelectedFilePath ?? selectedFile

  // Read directory contents via IPC
  const readDirectoryIPC = useCallback(async (dirPath: string): Promise<FileItem[]> => {
    if (!dirPath) return []
    try {
      if (window.electron?.ipcRenderer) {
        const raw = await window.electron.ipcRenderer.invoke('read-directory', dirPath)
        let parsed: DirectoryResponse | null = null

        if (typeof raw === 'string') {
          const trimmed = raw.trim()
          if (!trimmed.startsWith('Error:') && !trimmed.startsWith('System Error:')) {
            try {
              parsed = JSON.parse(trimmed)
            } catch (err) {
              console.error('[FileExplorer] JSON parse failed for read-directory:', err)
            }
          } else {
            console.warn('[FileExplorer] read-directory IPC error string:', raw)
          }
        } else if (raw && typeof raw === 'object' && Array.isArray(raw.content)) {
          parsed = raw as DirectoryResponse
        }

        if (parsed && Array.isArray(parsed.content)) {
          return parsed.content
        }
      }
    } catch (err) {
      console.error(`[FileExplorer] Failed to read directory '${dirPath}':`, err)
    }
    return []
  }, [])

  // Load a directory into cache
  const loadDirectory = useCallback(
    async (dirPath: string, isRoot: boolean = false) => {
      if (!dirPath) return
      setLoadingPaths((prev) => new Set(prev).add(dirPath))
      if (isRoot) setIsRootLoading(true)

      try {
        const content = await readDirectoryIPC(dirPath)
        setDirectoryCache((prev) => ({
          ...prev,
          [dirPath]: content
        }))
      } finally {
        setLoadingPaths((prev) => {
          const next = new Set(prev)
          next.delete(dirPath)
          return next
        })
        if (isRoot) setIsRootLoading(false)
      }
    },
    [readDirectoryIPC]
  )

  // When activePath changes, reload root directory
  useEffect(() => {
    if (activePath) {
      setDirectoryCache({})
      setExpandedFolders(new Set([activePath]))
      loadDirectory(activePath, true)
    } else {
      setDirectoryCache({})
      setExpandedFolders(new Set())
    }
  }, [activePath, loadDirectory])

  // Toggle folder open/closed
  const handleToggleFolder = useCallback(
    async (folderPath: string) => {
      const willExpand = !expandedFolders.has(folderPath)

      setExpandedFolders((prev) => {
        const next = new Set(prev)
        if (next.has(folderPath)) {
          next.delete(folderPath)
        } else {
          next.add(folderPath)
        }
        return next
      })

      if (willExpand && !directoryCache[folderPath]) {
        await loadDirectory(folderPath, false)
      }
    },
    [expandedFolders, directoryCache, loadDirectory]
  )

  // Handle clicking a file
  const handleSelectFile = useCallback(
    (filePath: string) => {
      setSelectedFile(filePath)
      onSelectFile?.(filePath)
    },
    [onSelectFile]
  )

  // Folder picker dialog IPC
  const handleOpenFolderDialog = async () => {
    try {
      if (!window.electron?.ipcRenderer) {
        console.warn('[FileExplorer] window.electron.ipcRenderer is unavailable')
        return
      }
      const res = await window.electron.ipcRenderer.invoke('dialog:openDirectory')
      let chosenPath: string | null = null

      if (typeof res === 'string' && res.trim()) {
        chosenPath = res.trim()
      } else if (Array.isArray(res) && res.length > 0 && typeof res[0] === 'string') {
        chosenPath = res[0]
      } else if (res && typeof res === 'object') {
        if (Array.isArray(res.filePaths) && res.filePaths.length > 0) {
          chosenPath = res.filePaths[0]
        } else if (typeof res.dir === 'string' && res.dir.trim()) {
          chosenPath = res.dir.trim()
        }
      }

      if (chosenPath) {
        setStoreProjectPath(chosenPath)
      }
    } catch (err) {
      console.error('[FileExplorer] Error in dialog:openDirectory:', err)
    }
  }

  // Refresh entire tree or active directories
  const handleRefresh = async () => {
    if (!activePath) return
    const pathsToReload = Array.from(expandedFolders)
    if (!pathsToReload.includes(activePath)) {
      pathsToReload.push(activePath)
    }

    setIsRootLoading(true)
    try {
      const results = await Promise.all(
        pathsToReload.map(async (dir) => {
          const content = await readDirectoryIPC(dir)
          return { dir, content }
        })
      )

      setDirectoryCache((prev) => {
        const next = { ...prev }
        for (const res of results) {
          next[res.dir] = res.content
        }
        return next
      })
    } finally {
      setIsRootLoading(false)
    }
  }

  // Collapse all expanded folders
  const handleCollapseAll = () => {
    if (activePath) {
      setExpandedFolders(new Set([activePath]))
    } else {
      setExpandedFolders(new Set())
    }
  }

  const rootItems = activePath ? directoryCache[activePath] || [] : []
  const folderName = activePath ? getBasename(activePath) : ''

  return (
    <div
      className={`flex flex-col h-full w-full bg-zinc-950/80 backdrop-blur-md border-r border-white/5 text-zinc-100 overflow-hidden font-mono select-none ${className}`}
    >
      {/* Header */}
      <div className="p-2.5 border-b border-white/5 flex items-center justify-between bg-zinc-950/50 flex-shrink-0 gap-1.5">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <div
            className="p-1 rounded-md border flex items-center justify-center flex-shrink-0"
            style={{
              backgroundColor: hexToRgba(primaryColor, 0.1),
              borderColor: hexToRgba(primaryColor, 0.3)
            }}
          >
            <RiFolderLine className="text-sm" style={{ color: primaryColor }} />
          </div>
          <div className="min-w-0 flex-1">
            <h2
              className="text-xs font-mono font-bold tracking-wider uppercase text-zinc-200 truncate"
              title={activePath || 'No project open'}
            >
              {activePath ? folderName : 'EXPLORER'}
            </h2>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {activePath && (
            <>
              {/* Search Toggle Button */}
              <button
                onClick={() => {
                  setIsSearching((prev) => !prev)
                  if (isSearching) setSearchFilter('')
                }}
                className={`p-1 rounded-md border transition-all cursor-pointer ${
                  isSearching || searchFilter
                    ? 'shadow-sm'
                    : 'bg-white/5 hover:bg-white/10 border-white/10 text-zinc-400 hover:text-zinc-200'
                }`}
                style={
                  isSearching || searchFilter
                    ? {
                        backgroundColor: hexToRgba(primaryColor, 0.15),
                        borderColor: hexToRgba(primaryColor, 0.35),
                        color: primaryColor
                      }
                    : {}
                }
                title="Filter files"
              >
                <RiSearchLine className="text-xs" />
              </button>

              {/* Collapse All Button */}
              <button
                onClick={handleCollapseAll}
                className="p-1 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-400 hover:text-zinc-200 transition-all cursor-pointer"
                title="Collapse all folders"
              >
                <RiSubtractLine className="text-xs" />
              </button>

              {/* Refresh Button */}
              <button
                onClick={handleRefresh}
                disabled={isRootLoading}
                className="p-1 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-400 hover:text-zinc-200 transition-all cursor-pointer disabled:opacity-50"
                title="Refresh explorer"
              >
                <RiRefreshLine className={`text-xs ${isRootLoading ? 'animate-spin' : ''}`} />
              </button>
            </>
          )}

          {/* Select Project Folder Button */}
          <button
            onClick={handleOpenFolderDialog}
            className="px-2 py-1 rounded-md border text-[10px] font-mono font-semibold flex items-center gap-1.5 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]"
            style={{
              backgroundColor: hexToRgba(primaryColor, 0.12),
              borderColor: hexToRgba(primaryColor, 0.3),
              color: primaryColor
            }}
            title="Open project folder dialog"
          >
            <RiFolderOpenFill className="text-xs" />
            <span className="hidden sm:inline">OPEN</span>
          </button>
        </div>
      </div>

      {/* Search Filter Bar (if open) */}
      <AnimatePresence>
        {isSearching && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="px-2.5 py-1.5 border-b border-white/5 bg-zinc-950/40 overflow-hidden flex-shrink-0"
          >
            <div className="relative flex items-center">
              <RiSearchLine className="absolute left-2 text-xs text-zinc-500 pointer-events-none" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter files..."
                autoFocus
                className="w-full pl-6 pr-6 py-1 bg-zinc-900/80 border border-white/10 rounded text-[11px] font-mono text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
                style={{
                  borderColor: searchFilter ? hexToRgba(primaryColor, 0.4) : undefined
                }}
              />
              {searchFilter && (
                <button
                  onClick={() => setSearchFilter('')}
                  className="absolute right-1.5 p-0.5 text-zinc-400 hover:text-zinc-200 cursor-pointer"
                >
                  <RiCloseLine className="text-xs" />
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Body */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 space-y-0.5 custom-scrollbar">
        {!activePath ? (
          /* Empty / No Project State */
          <div className="h-full flex flex-col items-center justify-center p-6 text-center select-none">
            <div
              className="p-3.5 rounded-2xl border mb-3 flex items-center justify-center transition-all duration-300"
              style={{
                backgroundColor: hexToRgba(primaryColor, 0.08),
                borderColor: hexToRgba(primaryColor, 0.25),
                boxShadow: `0 0 20px ${hexToRgba(primaryColor, 0.1)}`
              }}
            >
              <RiFolderLine className="text-3xl" style={{ color: primaryColor }} />
            </div>
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-200 mb-1">
              No Project Open
            </h3>
            <p className="text-[10px] font-mono text-zinc-500 max-w-[200px] mb-4 leading-relaxed">
              Select a workspace directory to explore and edit code files.
            </p>
            <button
              onClick={handleOpenFolderDialog}
              className="px-3 py-1.5 rounded-lg border font-mono text-xs font-semibold flex items-center gap-2 cursor-pointer transition-all duration-200 hover:scale-105"
              style={{
                backgroundColor: hexToRgba(primaryColor, 0.15),
                borderColor: hexToRgba(primaryColor, 0.4),
                color: primaryColor,
                boxShadow: `0 0 12px ${hexToRgba(primaryColor, 0.15)}`
              }}
            >
              <RiFolderOpenLine className="text-sm" />
              <span>OPEN PROJECT</span>
            </button>
          </div>
        ) : isRootLoading && rootItems.length === 0 ? (
          /* Root Loading State */
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
            <RiLoader4Line
              className="text-2xl animate-spin"
              style={{ color: primaryColor }}
            />
            <div className="flex items-center gap-2">
              <span
                className="w-1.5 h-1.5 rounded-full animate-ping"
                style={{ backgroundColor: primaryColor }}
              />
              <span className="text-xs font-mono text-zinc-400 tracking-wider">
                SCANNING DIRECTORY...
              </span>
            </div>
          </div>
        ) : rootItems.length === 0 ? (
          /* Empty Directory State */
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-zinc-500">
            <RiCodeSSlashLine className="text-3xl text-zinc-600 mb-2" />
            <p className="text-xs font-mono text-zinc-400">Empty directory</p>
            <p className="text-[10px] font-mono text-zinc-600 mt-1">No files or subfolders found</p>
          </div>
        ) : (
          /* Tree View */
          <div className="flex flex-col space-y-0.5">
            {rootItems.map((item) => (
              <TreeNode
                key={item.path}
                item={item}
                depth={0}
                expandedFolders={expandedFolders}
                loadingPaths={loadingPaths}
                directoryCache={directoryCache}
                activeFilePath={activeSelectedFilePath}
                primaryColor={primaryColor}
                searchFilter={searchFilter}
                onToggleFolder={handleToggleFolder}
                onSelectFile={handleSelectFile}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer Info */}
      {activePath && (
        <div className="px-3 py-1.5 border-t border-white/5 bg-zinc-950/50 flex items-center justify-between text-[9px] font-mono text-zinc-500 flex-shrink-0">
          <span className="truncate max-w-[150px]" title={activePath}>
            {folderName}
          </span>
          <span>{rootItems.length} items</span>
        </div>
      )}
    </div>
  )
}

export default FileExplorer
