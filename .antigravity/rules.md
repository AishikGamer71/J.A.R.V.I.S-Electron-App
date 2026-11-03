# PERMANENT WORKSPACE RULES & IRONCLAD LAWS FOR J.A.R.V.I.S ELECTRON APP

## 1. STEP-ZERO GITHUB UI RECOVERY & ZERO UI DRIFT
- The original UI files restored from https://github.com/AishikGamer71/J.A.R.V.I.S-Electron-App.git are the single source of visual truth.
- NEVER delete, rename, move, restyle, or alter even a single button, icon, color, font, CSS/Tailwind class, SVG, or layout grid.
- Keep the exact filenames, folder structure, and JSX layout.
- Backend attachment only: remove dummy random timers, bind real WebSocket/IPC telemetry, voice states, logs, and buttons to `jarvisBridge`.

## 2. DESKTOP APPLICATION ONLY — NEVER AN OS
- This is a standalone Windows Electron Desktop Application, NOT an operating system, desktop shell replacement, or window manager.

## 3. POLYGLOT LANGUAGE DISCIPLINE
- TypeScript / TSX (Frontend & Electron): Keep Electron main, preload, and React UI in native TypeScript/TSX.
- Python 3.11 (backend/): AI orchestration, LLM routing, memory, VLM grounding, and voice pipelines in Python 3.11.
- Rust & C++ (native_core/): Low-level Windows OS controls, sub-millisecond charger unplug interrupts, BitBlt capture, SendInput, and hardware emergency kill-switch (`Ctrl+Alt+Backspace`) in compiled Rust / C++ Win32 with zero-crash `ctypes.windll` fallback.

## 4. GOLDEN FOLDER MANAGEMENT & NATIVE CODE ASSIMILATION
- Never leave cloned third-party repositories inside subfolders.
- Shallow-clone donor repositories into temporary `_donor_staging/`, assimilate required logic into `backend/` and `native_core/`, and permanently delete `_donor_staging/`.
- No truncation, `# TODO`, `pass`, or mock placeholders. Every file must be 100% complete.

## 5. HARDWARE INTERRUPT & SAFETY SHIELD
- 1ms charger unplug/plug detection via Win32 `GetSystemPowerStatus` triggers instant voice alerts.
- Emergency hardware kill-switch (`Ctrl+Alt+Backspace`) halts GUI computer-use in under 1ms.
- ECC AgentShield enforces PreToolUse command blocking, protected file access, and credential redaction.
