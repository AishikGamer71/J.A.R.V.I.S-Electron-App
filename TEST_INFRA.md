# J.A.R.V.I.S. Unified Desktop System — E2E Test Infrastructure Specification

**Document Version**: 2.0.0  
**Status**: APPROVED & ACTIVE  
**Last Updated**: 2026-11-10T08:30:00Z  
**Target System**: J.A.R.V.I.S. Electron Application & Unified Backend  

---

## 1. Test Philosophy

The J.A.R.V.I.S. End-to-End (E2E) testing framework is built upon three foundational engineering principles:

### 1.1 Opaque-Box Testing
All tests exercise the system strictly through its observable, public interfaces. The test suite does not bind to internal private methods or implementation idiosyncrasies. Observable boundaries include:
- **HTTP/REST Endpoints** on `http://127.0.0.1:8765` (`/health`, `/api/system/stats`, `/v1/tools`, etc.)
- **Full-Duplex WebSockets** on `ws://127.0.0.1:8765/ws` and `/ws/jarvis`
- **Filesystem Artifacts & Schemas** (`~/.jarvis/state.db`, `~/.jarvis/homunculus/observations.jsonl`, `backend/voice/assets/jarvis_ref.wav`, governance files)
- **Standard Process Exits & CLI Contracts** (`python tests/e2e/runner.py`, `scripts/setup-environments.ps1`)
- **UI Source Immutability** (`src/components/widgets/arc-reactor.tsx`, lighting configs, clean diffs across tabs)

### 1.2 Requirement-Driven Coverage
Every test case in the suite directly traces back to:
1. Master prompt requirements ($R1$ through $R5$) in `ORIGINAL_REQUEST.md`.
2. The 40 enumerated features in `PROJECT.md`.
3. Explicit interface contracts documented in `PROJECT.md § Interface Contracts`.

### 1.3 Progressive Testability
During milestone execution, test runs provide immediate and reliable validation signals:
- **Current Milestone (M1)**: Tests verify existing workspace assets, directory trees, audio hashes, governance markdown rules, and UI lighting parameters immediately.
- **Subsequent Milestones (M2–M5)**: Tests assess module availability, contract conformity, and endpoint health. When a backend module or service is in progress or absent, tests identify pending milestones cleanly without crashing the test runner.
- **Full System (M6)**: All 4 tiers execute across the unified system with zero tolerance for regressions.

---

## 2. Test Suite Architecture

```
tests/e2e/
├── __init__.py                  # Package marker
├── conftest_utils.py            # Shared test fixtures, mock servers, HTTP/WS test clients
├── runner.py                    # Unified CLI test runner with structured ASCII/JSON reporting
├── test_tier1_features.py       # Tier 1: Feature coverage (>=5 tests per feature)
├── test_tier2_boundaries.py     # Tier 2: Boundary & Corner Cases (>=5 tests per feature)
├── test_tier3_combinations.py   # Tier 3: Cross-Feature combination tests
└── test_tier4_scenarios.py      # Tier 4: Real-World Application scenarios
```

### 2.1 Test Execution Commands
The test suite operates cleanly with Python's standard library (`unittest`), requiring no external test runner dependencies.

- **Run Full Suite via Runner**:
  ```bash
  python tests/e2e/runner.py
  ```
- **Run Specific Tier**:
  ```bash
  python tests/e2e/runner.py --tier 1
  python tests/e2e/runner.py --tier 2
  python tests/e2e/runner.py --tier 3
  python tests/e2e/runner.py --tier 4
  ```
- **Run Specific Milestone**:
  ```bash
  python tests/e2e/runner.py --milestone M1
  python tests/e2e/runner.py --milestone M2
  ```
- **Run via Standard Library Unittest**:
  ```bash
  python -m unittest discover tests/e2e
  ```
- **Structured JSON Output**:
  ```bash
  python tests/e2e/runner.py --json
  ```

---

## 3. Complete Feature Inventory Matrix (Features #1 to #40)

| # | Feature Name | Milestone | Primary Interface / Contract | Tier 1 Tests | Tier 2 Boundaries | Tier 3 Combos | Tier 4 Scenarios |
|---|--------------|-----------|-----------------------------|--------------|-------------------|---------------|------------------|
| 1 | Reference Audio Backup & Restore | M1 | `backend/voice/assets/jarvis_ref.wav` | 5 | 5 | Yes | Yes (S2) |
| 2 | Legacy Backend & Doc Wipe | M1 | Workspace file layout, no legacy py/md | 5 | 5 | Yes | Yes (S1) |
| 3 | Target Directory Structure | M1 | 10 subdirectories under `backend/` | 5 | 5 | Yes | Yes (S1) |
| 4 | Workspace Governance Rules | M1 | `.antigravity/rules.md`, `.agent/rules/rules.md` | 5 | 5 | Yes | Yes (S1, S5) |
| 5 | Agent, Memory & Skill Profiles | M1 | `backend/agents/`, `memory/`, `skills/` | 5 | 5 | Yes | Yes (S1, S3) |
| 6 | Arc Reactor & Sphere Tuning | M1 | `src/components/widgets/arc-reactor.tsx` | 5 | 5 | Yes | Yes (S4) |
| 7 | AgentShield 14 Secret Patterns | M2 | `backend/security/agent_shield.py` | 5 | 5 | Yes | Yes (S5) |
| 8 | ECCHookDispatcher & Homunculus Log | M2 | `backend/security/ecc_hooks.py` | 5 | 5 | Yes | Yes (S1) |
| 9 | InstinctEngine & Dynamic Injection | M2 | `backend/memory/instinct_engine.py` | 5 | 5 | Yes | Yes (S1) |
| 10 | SessionDB SQLite WAL Schema 12 | M2 | `~/.jarvis/state.db` (Schema v12, FTS5) | 5 | 5 | Yes | Yes (S1, S2) |
| 11 | ContextCompressor | M2 | `backend/core/context_compressor.py` | 5 | 5 | Yes | Yes (S2, S3) |
| 12 | Dynamic PromptBuilder | M2 | `backend/core/prompt_builder.py` | 5 | 5 | Yes | Yes (S1, S3) |
| 13 | ToolDispatcher & Parallel Workers | M2 | `backend/core/tool_dispatcher.py` | 5 | 5 | Yes | Yes (S1) |
| 14 | HermesBrain Conversation Loop | M2 | `backend/core/hermes_brain.py` | 5 | 5 | Yes | Yes (S1, S2) |
| 15 | CronScheduler | M2 | `backend/core/cron_scheduler.py` | 5 | 5 | Yes | Yes (S5) |
| 16 | HardwareProfiler & TelemetryStore | M3 | `backend/engine/hardware_profiler.py` | 5 | 5 | Yes | Yes (S5) |
| 17 | Multi-Engine ModelRouter | M3 | `backend/engine/model_router.py` | 5 | 5 | Yes | Yes (S1, S2) |
| 18 | HybridMemory RRF k=60 | M3 | `backend/memory/hybrid_rag.py` | 5 | 5 | Yes | Yes (S3) |
| 19 | WakewordEngine | M3 | `backend/voice/wakeword_engine.py` | 5 | 5 | Yes | Yes (S2) |
| 20 | RealtimeSTT | M3 | `backend/voice/realtime_stt.py` | 5 | 5 | Yes | Yes (S2) |
| 21 | OmniVoiceService Microservice | M3 | Port 8001, 24kHz cloning TTS | 5 | 5 | Yes | Yes (S2) |
| 22 | Full-Duplex AudioPipeline & Barge-In | M3 | `backend/voice/audio_pipeline.py` (<32ms) | 5 | 5 | Yes | Yes (S2) |
| 23 | PowerGuardian | M3 | `backend/hardware/power_guardian.py` | 5 | 5 | Yes | Yes (S5) |
| 24 | WindowsMCPBridge | M4 | `backend/automation/windows_mcp_bridge.py` | 5 | 5 | Yes | Yes (S1) |
| 25 | OmniParserService Microservice | M4 | Port 8002, YOLOv9-E + Florence-2 | 5 | 5 | Yes | Yes (S1) |
| 26 | AgentS3Runner | M4 | `backend/automation/agent_s3_runner.py` | 5 | 5 | Yes | Yes (S1, S5) |
| 27 | BrowserUseRunner | M4 | `backend/automation/browser_use_runner.py` | 5 | 5 | Yes | Yes (S3) |
| 28 | MarkItDownService | M4 | `backend/automation/markitdown_service.py` | 5 | 5 | Yes | Yes (S3) |
| 29 | CameraHub | M5 | `backend/senses/camera_hub.py` (60 FPS SPMC) | 5 | 5 | Yes | Yes (S4) |
| 30 | MediaPipeGestures | M5 | `backend/senses/mediapipe_gestures.py` | 5 | 5 | Yes | Yes (S4) |
| 31 | DeepFaceSentry | M5 | `backend/senses/deepface_sentry.py` | 5 | 5 | Yes | Yes (S4) |
| 32 | Crawl4AIService | M5 | `backend/senses/crawl4ai_service.py` | 5 | 5 | Yes | Yes (S3) |
| 33 | GPTResearcherService | M5 | `backend/senses/gpt_researcher_service.py` | 5 | 5 | Yes | Yes (S3) |
| 34 | MobileRunService | M5 | `backend/senses/mobilerun_service.py` | 5 | 5 | Yes | Yes (S1) |
| 35 | Unified REST API Gateway | M5 | `backend/main.py` (`http://127.0.0.1:8765`) | 5 | 5 | Yes | Yes (All) |
| 36 | Full-Duplex WebSocket Gateway | M5 | `/ws` and `/ws/jarvis` | 5 | 5 | Yes | Yes (All) |
| 37 | Multi-Env Bootstrap Script | M5 | `scripts/setup-environments.ps1` | 5 | 5 | Yes | Yes (All) |
| 38 | System Architecture Documentation | M5 | `README.md`, `docs/UNIFIED_ARCHITECTURE.md` | 5 | 5 | Yes | Yes (All) |
| 39 | E2E Testing Suite (Tiers 1-4) | M6 | `tests/e2e/runner.py` | 5 | 5 | Yes | Yes (All) |
| 40 | Adversarial Hardening (Tier 5) | M6 | Edge cases, fuzzing, injection defense | 5 | 5 | Yes | Yes (All) |

---

## 4. Test Tiers Specification

### Tier 1: Feature Coverage (>=5 Tests Per Feature)
- Verifies primary functionality (happy path) for all 40 features.
- Progressive testability ensures M1 features pass immediately upon M1 completion.
- Modules for subsequent milestones are verified against their defined interface contracts, file locations, schemas, and endpoint responses.

### Tier 2: Boundary & Corner Cases (>=5 Tests Per Feature)
- Fuzzing and edge conditions:
  - Empty strings, whitespace-only queries, 1MB+ oversized payloads.
  - SQL injection substrings in SQLite FTS5 queries (`'`, `"`, `*`, `AND`, `OR`, `MATCH ""`).
  - Regex evasion attempts against `AgentShield` 14 secret patterns (fragmented tokens, unicode homoglyphs, newlines).
  - Malformed WebSocket JSON frames and truncated audio buffers.
  - Concurrent tool invocation collisions in `ToolDispatcher`.
  - Zero-token and maximum-context edge conditions in `ContextCompressor`.
  - Negative and zero latency barge-in triggers in `AudioPipeline`.

### Tier 3: Cross-Feature Combinations
End-to-end integration tests chaining multiple subsystems:
1. **Speech-to-Brain-to-Voice Loop**: Wakeword detection triggers STT -> transcription delivered to `HermesBrain` -> `ToolDispatcher` executes action -> output synthesized by `OmniVoiceService` -> playback emitted.
2. **Security & Audited Tool Execution**: User input scanned by `AgentShield` -> validated by `ToolDispatcher` -> pre-tool ECC hook logged -> execution completed -> post-tool ECC hook logged -> observation ingested by `InstinctEngine`.
3. **Multimodal Grounding & Automation**: OmniParser V2 identifies screen coordinates -> AgentS3 dispatches native Windows COM event via `WindowsMCPBridge` -> UI updates captured by telemetry.
4. **Biometric Guard & Visual Tab Control**: DeepFace validates user authentication -> MediaPipe gesture (swipe left) detected -> WebSocket broadcasts navigation event to React UI.
5. **Hardware Throttling Under Battery Constraint**: Win32 power status indicates battery operation -> `PowerGuardian` fires throttle event -> `ModelRouter` redirects high-overhead queries to quantized local models.

### Tier 4: Real-World Application Scenarios
1. **Scenario 1: Autonomous Desktop Task & Self-Correction**: Complete developer workflow: user asks J.A.R.V.I.S. to inspect files, execute tests, log observations, and report results through REST/WebSocket.
2. **Scenario 2: Conversational Barge-In & Stream Interruption**: User talks to J.A.R.V.I.S., assistant begins streaming response audio, user interrupts mid-sentence, assistant halts TTS within 32ms and transitions immediately back to listening state.
3. **Scenario 3: Deep Academic & Web Research**: User requests deep research on an emerging topic -> GPT-Researcher gathers queries -> Crawl4AI crawls target pages -> MarkItDown cleans documents -> HybridMemory stores references in SQLite FTS5 + FAISS.
4. **Scenario 4: Biometric Authentication & Gesture Navigation**: User sits before camera -> DeepFace authenticates identity -> Arc Reactor visualizer glows golden-amber -> Air swipe gesture changes UI navigation tab.
5. **Scenario 5: Power Guardian & Emergency Abort**: Laptop switches from AC to battery power -> System initiates energy-saving mode -> Emergency abort trigger (`Ctrl+Alt+Backspace` or `reset_abort` WS frame) halts all active automation runners cleanly.

---

## 5. Verification Protocol

1. **Self-Contained Isolation**: Every test creates its own temporary test assets or operates non-destructively on standard project paths.
2. **Deterministic Validation**: Timestamps, PIDs, and system UUIDs use regex pattern assertions or flexible matching rather than fixed equality.
3. **Standard Reporting**: Runner outputs total tests, passed, skipped (pending milestone features), failed, and execution duration.
