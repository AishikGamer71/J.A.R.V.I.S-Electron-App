export const getScreenSourceId = async (): Promise<string | null> => {
  try {
    if (!window.electron?.ipcRenderer) return null
    return await window.electron.ipcRenderer.invoke('get-screen-source')
  } catch (err) {
    return null
  }
}