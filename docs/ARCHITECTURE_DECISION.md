# Architecture Decision Record: J.A.R.V.I.S v4 Architecture

**Status:** Approved  
**Date:** 2026-08-15  
**Version:** 4.0.0  

---

## 1. Context & Motivation

J.A.R.V.I.S previously operated as a hybrid Electron application with scattered backend responsibilities, tightly coupling renderer code to platform APIs and legacy daemon implementations.

Version 4 reorganizes J.A.R.V.I.S into a clean, hexagonal monorepo architecture:
- **`apps/desktop`**: Electron + React + Vite frontend focused purely on presentation, user interactions, HUD rendering, and thin IPC communication.
- **`apps/core-service`**: Python-based core engine (FastAPI/WebSockets/SQLite FTS5/LiteLLM/Ollama) acting as the single autonomous brain and control plane.
- **`services/voice-service`**: Standalone audio process with isolated dependencies (faster-whisper, piper, wake-word engine, echo-gating).
- **`packages/shared-types`**: Shared TypeScript definitions bridging IPC and WebSocket interfaces.

---

## 2. Audit of Existing Codebase & Component Decisions

| Component | Status | Decision & Rationale |
|---|---|---|
| **Renderer UI / HUD Layout** | **Keep & Enhance** | Existing futuristic particle network, theme tokens, and component skeletons are visually rich and reusable; ported to `apps/desktop/src/` with page-based modularity. |
| **Electron Main & IPC Bridge** | **Rebuild (Streamline)** | Legacy `main.ts` had over 370KB of cluttered backend spawning logic. Replaced with clean child process supervisor, typed IPC channels in `electron/ipc/channels.ts`, and strict context isolation in `preload.ts`. |
| **Python Backend / Core** | **Rebuild (Hexagonal Architecture)** | Rebuilt as a standalone Python src-layout package (`apps/core-service/src/jarvis`) with strict separation of domain entities, ports, providers, router, and gateway. |
| **Model Router** | **New Implementation** | 3-tier classification (Tier 1 Local / Tier 2 Balanced / Tier 3 Advanced Cloud) combined with real-time hardware telemetry and network status for instant local fallback. |
| **Memory Subsystem** | **Rebuild (SQLite + FTS5 -> Vector RAG)** | Initial foundation uses SQLite with an FTS5 virtual table for lightning-fast search across chat history, with seamless upgrade path to ChromaDB/Mem0 vector memory. |
| **Tool Execution & Security** | **New Implementation** | Strict Risk Classifier (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), Permission Store, Confirmation Bridge to renderer, and Docker sandbox execution for high-risk operations. |
| **Voice Pipeline** | **Isolate to Standalone Service** | Voice processing (wake word, Whisper STT, Piper TTS, echo gating) moved to `services/voice-service` so heavy audio/C++ native deps do not impact core service stability. |

---

## 3. Communication Architecture

```
+-------------------------------------------------------------+
|                     Electron Renderer UI                    |
|                (React + Vite + Zustand + HUD)               |
+-------------------------------------------------------------+
               | (Typed IPC via Preload ContextBridge)
               v
+-------------------------------------------------------------+
|                     Electron Main Process                   |
|                   (Window, Tray, Supervisor)                |
+-------------------------------------------------------------+
               | (WebSocket / HTTP Control Plane - localhost)
               v
+-------------------------------------------------------------+
|                     apps/core-service                       |
|           (FastAPI Gateway + Router + SQLite FTS5)          |
+-------------------------------------------------------------+
       |                           |                      |
       v                           v                      v
[ Local Ollama ]          [ LiteLLM Cloud ]      [ Tool Sandbox ]
 (Offline/Tier 1)         (Anthropic/Gemini)       (Docker HIGH+)
```

---

## 4. Migration & Rollback Strategy

1. The initial commit state is permanently tagged as `pre-v4-baseline`.
2. Existing UI components are moved to `apps/desktop/` and adapted to connect through `gateway-client.ts`.
3. Development workflows utilize Turborepo and npm/pnpm workspaces for concurrent execution of desktop and core-service.
