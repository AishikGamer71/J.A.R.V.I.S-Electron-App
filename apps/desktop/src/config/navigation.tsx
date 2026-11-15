import {
  RiHomeLine,
  RiChat1Line,
  RiCompass3Line,
  RiGlobalLine,
  RiHistoryLine,
  RiLayoutGridLine,
  RiDashboard2Line,
  RiFolderOpenLine,
  RiImageLine,
  RiTerminalBoxLine,
  RiPhoneLine,
  RiSettings4Line,
  RiCpuLine
} from 'react-icons/ri'

export const NAVIGATION_MODULES = [
  { id: 'CHAT', icon: <RiChat1Line />, isCore: true },
  { id: 'MODULES', icon: <RiCpuLine />, isCore: true },
  { id: 'DASHBOARD', icon: <RiLayoutGridLine />, isCore: true },
  { id: 'TASK MANAGER', icon: <RiDashboard2Line /> },
  { id: 'Apps', icon: <RiFolderOpenLine /> },
  { id: 'NOTES', icon: <RiFolderOpenLine /> },
  { id: 'GALLERY', icon: <RiImageLine /> },
  { id: 'TERMINAL', icon: <RiTerminalBoxLine /> },
  { id: 'PHONE', icon: <RiPhoneLine /> },
  { id: 'SETTINGS', icon: <RiSettings4Line />, isCore: true }
]
