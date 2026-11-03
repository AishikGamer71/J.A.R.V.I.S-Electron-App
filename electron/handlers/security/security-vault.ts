import { ipcMain } from 'electron'
import Store from 'electron-store'
import bcrypt from 'bcryptjs'

const StoreClass = (Store as any).default || Store
const store = new StoreClass()

export default function registerSecurityVault() {
  // --- MIGRATION: Rename all 'iris_' keys to 'jarvis_' ---
  const legacyKeys = ['vault_face', 'vault_faces', 'vault_hash', 'personality', 'keys']
  legacyKeys.forEach((key) => {
    if (store.has(`iris_${key}`)) {
      store.set(`jarvis_${key}`, store.get(`iris_${key}`))
      store.delete(`iris_${key}`)
    }
  })
  // -------------------------------------------------------

  const legacyFace = store.get('jarvis_vault_face') as number[] | undefined
  if (legacyFace && !store.get('jarvis_vault_faces')) {
    store.set('jarvis_vault_faces', [legacyFace])
    store.delete('jarvis_vault_face')
  }

  ipcMain.handle('check-vault-status', () => {
    const hasPin = !!store.get('jarvis_vault_hash')
    const faces = store.get('jarvis_vault_faces') as number[][] | undefined
    const hasFace = faces && faces.length > 0
    return { hasPin, hasFace, faceCount: faces ? faces.length : 0 }
  })

  ipcMain.handle('get-personality', () => {
    return store.get('jarvis_personality') as string | undefined
  })

  ipcMain.handle('set-personality', (_, text: string) => {
    store.set('jarvis_personality', text)
    return true
  })

  ipcMain.handle('setup-vault-pin', async (_, pin: string) => {
    const salt = await bcrypt.genSalt(10)
    const hash = await bcrypt.hash(pin, salt)
    store.set('jarvis_vault_hash', hash)
    return true
  })

  ipcMain.handle('verify-vault-pin', async (_, pin: string) => {
    const hash = store.get('jarvis_vault_hash') as string
    if (!hash) return false
    return await bcrypt.compare(pin, hash)
  })

  ipcMain.handle('setup-vault-face', (_, descriptor: number[]) => {
    const faces = (store.get('jarvis_vault_faces') as number[][]) || []
    faces.push(descriptor)
    store.set('jarvis_vault_faces', faces)
    return true
  })

  ipcMain.handle('verify-vault-face', (_, descriptor: number[]) => {
    const faces = store.get('jarvis_vault_faces') as number[][] | undefined
    if (!faces || faces.length === 0) return false

    for (const savedFace of faces) {
      if (savedFace.length !== 128) continue
      let distance = 0
      for (let i = 0; i < descriptor.length; i++) {
        distance += Math.pow(descriptor[i] - savedFace[i], 2)
      }
      distance = Math.sqrt(distance)

      if (distance < 0.55) return true
    }
    return false
  })

  ipcMain.handle('secure-save-keys', (_, keys: { groqKey?: string; geminiKey?: string }) => {
    store.set('jarvis_keys', keys)
    return true
  })

  ipcMain.handle('secure-get-keys', () => {
    return store.get('jarvis_keys') || {}
  })
}
