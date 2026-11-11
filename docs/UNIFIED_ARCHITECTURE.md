# J.A.R.V.I.S. Unified Desktop System — Architecture Specification

**Document Version**: 2.0.0  
**Status**: APPROVED & ACTIVE  
**Last Updated**: 2026-11-10T15:40:00Z  

---

## 1. Executive Summary & Core Architectural Law
The J.A.R.V.I.S. Desktop System combines an untouched, pristine React 19 / TypeScript / Electron holographic frontend with a real, production-ready 17-repository Python backend.

**Architectural Law 1 (Visual Immutability)**:
No visual UI layouts, buttons, widgets, or components in `src/layouts/jarvis-layout.tsx` or `src/components/**` are altered. All functionality is powered by the unified gateway on `127.0.0.1:8765`.

---

## 2. 17-Repository Assimilation Matrix

| # | Open-Source Repository | Assimilated Subsystem | Source Path | Target Port / Location |
|---|------------------------|-----------------------|-------------|------------------------|
| 1 | `NousResearch/hermes-agent` | Autonomous Brain & Conversation Loop | `hermes_brain.py` | `backend/core/hermes_brain.py` |
| 2 | `NousResearch/hermes-agent` | SQLite WAL State DB Schema 12 | `hermes_state_schema.py` | `backend/memory/state_db.py` |
| 3 | `NousResearch/hermes-agent` | Tool Dispatcher & Worker Pool | `tool_dispatcher.py` | `backend/core/tool_dispatcher.py` |
| 4 | `NousResearch/hermes-agent` | Context Compressor & Prompt Builder | `context_compressor.py` | `backend/core/context_compressor.py` |
| 5 | `OpenJarvis` | Hardware Profiler & Telemetry Store | `hardware_profiler.py` | `backend/engine/hardware_profiler.py` |
| 6 | `OpenJarvis` | Multi-Engine Model Router | `model_router.py` | `backend/engine/model_router.py` |
| 7 | `OpenJarvis` | Hybrid RAG (RRF $k=60$) | `hybrid_rag.py` | `backend/memory/hybrid_rag.py` |
| 8 | `OmniVoice` | 24kHz Voice Cloning TTS | `omnivoice_service.py` | Microservice on **Port 8001** |
| 9 | `OmniParser V2` | YOLOv9-E + Florence-2 Icon Grounding | `omniparser_service.py` | Microservice on **Port 8002** |
| 10 | `Windows-MCP` | Native COM UIAutomation Bridge | `windows_mcp_bridge.py` | `backend/automation/windows_mcp_bridge.py` |
| 11 | `Agent-S3` | OSWorld Desktop Task Runner | `agent_s3_runner.py` | `backend/automation/agent_s3_runner.py` |
| 12 | `Browser-Use` | Headless Background CDP Automation | `browser_use_runner.py` | `backend/automation/browser_use_runner.py` |
| 13 | `MarkItDown` | Document to Markdown Conversion | `markitdown_service.py` | `backend/automation/markitdown_service.py` |
| 14 | `DeepFace` | Facenet512 Face ID & Sentry | `deepface_sentry.py` | `backend/senses/deepface_sentry.py` |
| 15 | `MediaPipe` | 60 FPS Hand Air-Gesture Recognition | `mediapipe_gestures.py` | `backend/senses/mediapipe_gestures.py` |
| 16 | `MobileRun` | Wireless Android ADB & Portal Bridge | `mobilerun_service.py` | `backend/senses/mobilerun_service.py` |
| 17 | `Crawl4AI` & `GPT-Researcher` | Web Extraction & Research Synthesis | `crawl4ai_service.py` | `backend/senses/crawl4ai_service.py` |

---

## 3. Tri-Port Process & Microservice Model

1. **Port 8765: Unified REST & WebSocket Gateway (`backend/main.py`)**:
   - The primary gateway consumed by Electron and external clients.
   - Provides all REST operations, full-duplex WebSockets (`/ws` and `/ws/jarvis`), background telemetry broadcasting, and orchestrates subprocess runners.
2. **Port 8001: OmniVoice TTS Microservice (`backend/voice/omnivoice_service.py`)**:
   - Isolated in `.venv-omnivoice` (`transformers>=5.3.0`, `torch>=2.4`).
   - Generates 24kHz zero-shot cloned speech buffers.
3. **Port 8002: OmniParser V2 Grounding Microservice (`backend/automation/omniparser_service.py`)**:
   - Isolated in `.venv-omniparser` (`transformers==4.40.0`, `numpy==1.26.4`).
   - Identifies bounding boxes, icons, and interactive elements across screen captures.

---

## 4. WebSocket Protocol Specification

All communications across `/ws` and `/ws/jarvis` adhere to `WebSocketEnvelope`:

```json
{
  "type": "<ProtocolMessageType>",
  "request_id": "<UUID string>",
  "timestamp": "<ISO 8601 UTC timestamp>",
  "payload": { ... }
}
```

### Message Types
- `user.message`: Inbound user text or audio prompt.
- `agent.state`: Downstream state changes (`idle`, `listening`, `thinking`, `executing_tool`, `speaking`).
- `agent.token`: Streaming LLM response deltas.
- `agent.complete`: Final structured turn response.
- `tool.start` & `tool.result`: Pre- and post-tool execution events.
- `system.metrics`: Hardware telemetry snapshot.
- `audio.control`: Audio barge-in and microphone controls.
- `client.command`: Window minimize/maximize and HUD control.

---

## 5. Security Architecture (AgentShield & ECC)
`AgentShield` sits in front of all input parsing and tool executions:
1. **14 Secret Patterns**: Regex pattern scanning for AWS keys, GitHub tokens, Slack Webhooks, OpenAI/Google API keys, private keys, database connection URIs.
2. **Destructive Command Blocking**: Prohibits `rm -rf`, `format`, `dd`, `drop table`, `del /f /s /q`.
3. **Config File Protection**: Prevents modifications to system configs, `.env`, or governance rules.
4. **Prompt Injection Scanner**: Blocks adversarial bypass strings (`ignore all previous instructions`, jailbreak phrases).
5. **Shannon Entropy Analysis**: Flags high-entropy encrypted blobs and obfuscated shell commands.
6. **Security Scoring**: Assigns letter grades `A` through `F` dynamically reflected in the Terminal tab.

---

## 6. Multi-Environment Isolation Model
Reconciled via `scripts/setup-environments.ps1`:
- `.venv`: Primary core services (Python 3.12).
- `.venv-omnivoice`: Voice microservice (`transformers>=5.3.0`).
- `.venv-omniparser`: Vision grounding microservice (`transformers==4.40.0`, `numpy==1.26.4`).

---

## 7. Verification Suites
- Tier 1: Feature Coverage (`tests/e2e/test_tier1_features.py`)
- Tier 2: Boundary Cases (`tests/e2e/test_tier2_boundaries.py`)
- Tier 3: Cross-Feature Combos (`tests/e2e/test_tier3_combinations.py`)
- Tier 4: Real-World Scenarios (`tests/e2e/test_tier4_scenarios.py`)
- Unified CLI Runner: `python tests/e2e/runner.py`
