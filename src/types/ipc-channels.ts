/**
 * Single source of truth for all IPC channel names.
 * Import from here to avoid typos in channel strings.
 */

export const IPC_CHANNELS = {
  // Chat & Memory
  ADD_MESSAGE: 'add-message',
  GET_HISTORY: 'get-history',
  CLEAR_HISTORY: 'clear-history',
  SAVE_CORE_MEMORY: 'save-core-memory',
  SEARCH_CORE_MEMORY: 'search-core-memory',

  // Security & Auth
  CHECK_VAULT_STATUS: 'check-vault-status',
  SETUP_VAULT_PIN: 'setup-vault-pin',
  VERIFY_VAULT_PIN: 'verify-vault-pin',
  SETUP_VAULT_FACE: 'setup-vault-face',
  VERIFY_VAULT_FACE: 'verify-vault-face',
  SECURE_SAVE_KEYS: 'secure-save-keys',
  SECURE_GET_KEYS: 'secure-get-keys',
  GET_PERSONALITY: 'get-personality',
  SET_PERSONALITY: 'set-personality',

  // System
  GET_SYSTEM_STATS: 'get-system-stats',
  GET_INSTALLED_APPS: 'get-installed-apps',
  GET_DRIVES: 'get-drives',

  // App Behaviors
  SET_ALWAYS_ON_TOP: 'set-always-on-top',
  SET_AUTO_START: 'set-auto-start',
  SELECT_STORAGE_PATH: 'select-storage-path',

  // Profile Storage
  GET_USER_PROFILE: 'get-user-profile',
  SAVE_USER_PROFILE: 'save-user-profile',
  GET_SYSTEM_PROFILE: 'get-system-profile',
  SAVE_SYSTEM_PROFILE: 'save-system-profile'
} as const
