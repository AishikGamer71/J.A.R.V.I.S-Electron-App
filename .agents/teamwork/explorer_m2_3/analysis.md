# Technical Analysis & Blueprint: Autonomous Brain & Execution Core (Milestone 2)

**Author**: `teamwork_explorer` (`explorer_m2_3`)  
**Scope**: Milestone 2 Subsystem 3 (Phase 6 Core Execution Engine)  
**Target Modules**:
1. `backend/core/hermes_brain.py` (`HermesBrain`, `BrainEvent`, `TurnResult`)
2. `backend/core/prompt_builder.py` (`PromptBuilder`, System Prompt Assembly, Skills/Instincts Injection)
3. `backend/core/context_compressor.py` (`ContextCompressor`, Token Budget Tracking, Semantic Compaction)
4. `backend/core/tool_dispatcher.py` (`ToolDispatcher`, Parallel Workers, 3-Tier Validation, Loop Guard)
5. `backend/core/cron_scheduler.py` (`CronScheduler`, 60s Tick Loop, Windows File Lock, Job Delivery)

**Authoritative Sources**:
- `c:\Users\utpal\Downloads\jarvis_antigravity_master_prompt.md` (Sections 3.2, 6.2, 6.5)
- `e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md` (Lines 6-13, 27-32, 69-93)
- `e:\Projects\J.A.R.V.I.S Electron App\ORIGINAL_REQUEST.md` (R3.2, R4.1, R4.2)
- Cached Donor Repo: `C:\Users\utpal\AppData\Local\hermes\hermes-agent` (`run_agent.py`, `agent/conversation_loop.py`, `agent/prompt_builder.py`, `agent/context_compressor.py`, `agent/tool_executor.py`, `agent/tool_guardrails.py`, `model_tools.py`, `cron/scheduler.py`, `cron/jobs.py`)
- Peer Specifications: `explorer_m2_1/analysis.md` (`AgentShield`, `ECCHookDispatcher`, `InstinctEngine`), `explorer_m2_2/analysis.md` (`SessionDB` Schema 12)

---

## 1. Executive Summary & Architectural Overview

Milestone 2 establishes the autonomous decision-making and execution brain of the J.A.R.V.I.S. Desktop System. The execution engine must maintain strict full-duplex responsiveness, zero-lag voice/chat interaction, resilient long-running tool dispatch, and background autonomy while running on Windows 11.

The core subsystem consists of five tightly integrated Python modules located under `backend/core/`:

```
backend/core/
├── hermes_brain.py       # High-level conversation loop, streaming generator, interrupt controller
├── prompt_builder.py     # System prompt assembly, SOUL/USER/MEMORY loading, instinct & skill injection
├── context_compressor.py # Token budget tracking, middle-turn semantic summarization, orphan sanitization
├── tool_dispatcher.py    # ThreadPool 8-worker execution, 3-tier validation, 5-streak loop guard, ECC hooks
└── cron_scheduler.py     # 60s periodic tick loop, Windows msvcrt file locking, inbox & WebSocket notification
```

### Key Architectural Invariants
1. **Interruptibility**: Any in-flight LLM generation stream or running tool must halt immediately upon receiving an interrupt signal (`brain.interrupt()` or WebSocket `reset_abort`), releasing locks and exiting cleanly in $<15\text{ ms}$.
2. **Context Preservation**: Conversations exceeding the 50% threshold of the model context window (default: 8,192 tokens; threshold: 4,096 tokens) must compact older turns without dropping system instructions (`head`), recent user/assistant turns (`tail`), or leaving dangling `tool_call` / `tool_result` pairs.
3. **Execution Safety**: Every tool call is subjected to a 3-tier validation gauntlet:
   - *Tier 1 (Security)*: `AgentShield` regex scanning and destructive command filtering.
   - *Tier 2 (Governance & Role)*: Subagent capability checks (e.g., `planner` and `architect` are strictly read-only).
   - *Tier 3 (Routing & Loop Guard)*: Detection of repetitive identical tool executions (max 5 identical calls before hard circuit-break halt).
4. **Observable Feedback**: All tool invocations trigger `ECCHookDispatcher.pre_tool_use` and `post_tool_use`, appending structured execution logs to `~/.jarvis/homunculus/observations.jsonl`.
5. **Background Scheduling**: Autonomous tasks run on a 60-second cadence via `CronScheduler`, guarded by cross-process Windows `msvcrt` file locking (`.tick.lock`), with completions pushed directly to the inbox (`GET /v1/inbox`) and broadcast via WebSockets.

---

## 2. Interface & System Boundary Matrix

| Calling Component | Target Component | Method / Contract | Purpose |
|---|---|---|---|
| `backend/main.py` (`/ws`, `user.message`) | `backend/core/hermes_brain.py` | `run_turn(session_id, user_message, on_token)` | Executes async conversation turn; yields streaming `BrainEvent` objects |
| `backend/main.py` (`/ws`, `reset_abort`) | `backend/core/hermes_brain.py` | `interrupt()` / `request_hard_interrupt()` | Halts current generation or tool execution immediately |
| `backend/core/hermes_brain.py` | `backend/core/prompt_builder.py` | `build_system_prompt()`, `assemble_messages()` | Builds full LLM payload with memory, skills, and instincts |
| `backend/core/hermes_brain.py` | `backend/core/context_compressor.py`| `should_compress()`, `compress(messages)` | Enforces token budget and middle-turn compaction |
| `backend/core/hermes_brain.py` | `backend/core/tool_dispatcher.py` | `dispatch_tool_calls(tool_calls, session_id)` | Executes parallel/sequential tool calls with loop guards |
| `backend/core/hermes_brain.py` | `backend/memory/state_db.py` | `add_message()`, `get_messages()`, `record_tool_call()` | Persists session history and tool telemetry in SQLite WAL |
| `backend/core/tool_dispatcher.py` | `backend/security/agent_shield.py` | `validate_tool_call(tool_name, args)` | Validates commands and arguments against security rules |
| `backend/core/tool_dispatcher.py` | `backend/security/ecc_hooks.py` | `pre_tool_use()`, `post_tool_use()` | Fires ECC hooks and logs to `observations.jsonl` |
| `backend/core/prompt_builder.py` | `backend/memory/instinct_engine.py` | `get_active_instincts(min_confidence=0.70)` | Injects high-confidence learned behavioral instincts |
| `backend/core/cron_scheduler.py` | `backend/core/hermes_brain.py` | `run_turn(session_id="cron_...", prompt)` | Executes scheduled jobs via background brain instance |
| `backend/main.py` (REST `GET /v1/tools`) | `backend/core/tool_dispatcher.py` | `get_tool_definitions()` | Exposes registered tool schemas to UI `MODULES` tab |
| `backend/main.py` (REST `POST /v1/tools/invoke`)| `backend/core/tool_dispatcher.py` | `invoke_tool(tool, args)` | Executes direct tool invocation from UI or API clients |
| `backend/main.py` (REST `GET /v1/inbox`)| `backend/core/cron_scheduler.py` | `get_inbox_items()` | Serves scheduled task completions and notifications |

---

## 3. Component 1: `HermesBrain` (`backend/core/hermes_brain.py`)

### 3.1 Design Principles
`HermesBrain` assimilates `AIAgent` from `NousResearch/hermes-agent/run_agent.py` and `conversation_loop.py`, modernizing it for native asynchronous Python execution, streaming delta callbacks, and full WebSocket event serialization.

### 3.2 Data Contracts & Event Models
```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

@dataclass
class BrainEvent:
    event_type: str  # "state" | "token" | "tool_start" | "tool_result" | "complete" | "error" | "interrupted"
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class TurnResult:
    session_id: str
    user_message: str
    assistant_response: str
    tool_calls: List[Dict[str, Any]]
    total_tokens: int
    interrupted: bool
    duration_ms: float
```

### 3.3 Public Method Signatures & Implementation Logic

#### `run_turn(session_id: str, user_message: str, on_token: Optional[Callable[[str], None]] = None) -> AsyncIterator[BrainEvent]`
```python
class HermesBrain:
    def __init__(
        self,
        prompt_builder: "PromptBuilder",
        context_compressor: "ContextCompressor",
        tool_dispatcher: "ToolDispatcher",
        state_db: "SessionDB",
        model_router: Optional[Any] = None,
        max_turn_iterations: int = 25,
    ):
        self.prompt_builder = prompt_builder
        self.context_compressor = context_compressor
        self.tool_dispatcher = tool_dispatcher
        self.state_db = state_db
        self.model_router = model_router
        self.max_turn_iterations = max_turn_iterations
        self._interrupt_event = asyncio.Event()
        self._interrupt_requested = False
        self._active_children: List[Any] = []
        self._active_children_lock = threading.Lock()
```

1. **Turn Initialization**:
   - Clear `self._interrupt_requested = False` and `self._interrupt_event.clear()`.
   - Ensure session exists in `state_db.get_session(session_id)`. If absent, call `state_db.create_session(title=user_message[:40], session_id=session_id)`.
   - Add user message: `state_db.add_message(session_id, role="user", content=user_message)`.
   - Yield `BrainEvent("agent.state", {"state": "thinking", "session_id": session_id})`.

2. **Context Preparation & Compression**:
   - Fetch active message history: `history = self.state_db.get_messages(session_id)`.
   - Check compression threshold:
     ```python
     if self.context_compressor.should_compress(history):
         yield BrainEvent("agent.state", {"state": "compressing", "session_id": session_id})
         history = await self.context_compressor.compress_async(history, session_id=session_id)
     ```
   - Build system prompt with memory, instincts, and skills:
     ```python
     system_prompt = self.prompt_builder.build_system_prompt()
     messages_payload = self.prompt_builder.assemble_messages(system_prompt, history)
     ```

3. **Multi-Turn Reasoning & Tool Loop**:
   - Loop `iteration` from 1 to `self.max_turn_iterations`:
     - **Check Interrupt**: If `self.is_interrupted()`, yield `BrainEvent("interrupted", {"reason": "user_abort"})` and break.
     - **Model Dispatch**: Query `model_router` (or configured Ollama/Gemini/OpenAI client) with `messages_payload` and tool schemas from `tool_dispatcher.get_tool_definitions()`.
     - **Streaming Response**:
       - As token deltas stream in, check `self.is_interrupted()`.
       - If token emitted:
         - Invoke `on_token(delta)` if provided.
         - Yield `BrainEvent("agent.token", {"token": delta, "session_id": session_id})`.
       - Accumulate total response text.
     - **Tool Invocation Evaluation**:
       - If no tool calls emitted:
         - Record final assistant message: `state_db.add_message(session_id, role="assistant", content=accumulated_text)`.
         - Yield `BrainEvent("agent.complete", {"response": accumulated_text, "session_id": session_id})`.
         - Trigger `self._spawn_background_review(session_id, history)` in background thread.
         - Break from loop.
       - If model emitted tool calls:
         - Record assistant message with tool calls in `state_db`.
         - For each tool call:
           - Yield `BrainEvent("tool.start", {"tool": tool_name, "args": args, "call_id": call_id})`.
         - Execute tool calls via `tool_dispatcher.dispatch_tool_calls(tool_calls, session_id=session_id)`.
         - For each tool result:
           - Yield `BrainEvent("tool.result", {"tool": tool_name, "result": result, "status": status, "call_id": call_id})`.
           - Record tool message in `state_db.add_message(session_id, role="tool", content=result, tool_call_id=call_id, tool_name=tool_name)`.
           - Record in `tool_calls` table via `state_db.record_tool_call(...)`.
         - Append tool results to `messages_payload` and continue loop for model synthesis.

4. **Turn Completion**:
   - Yield `BrainEvent("agent.state", {"state": "idle", "session_id": session_id})`.

#### `interrupt(message: Optional[str] = None) -> None` / `request_hard_interrupt() -> None`
- Sets `self._interrupt_requested = True` and calls `self._interrupt_event.set()`.
- Forwards interrupt signal to `self.tool_dispatcher.interrupt()`.
- Propagates interrupt to all running subagents in `self._active_children`.
- Guarantees immediate termination of long-running subprocesses.

#### Subagent Delegation (`delegate_task`)
- Method: `async def delegate_task(self, goal: str, role: str = "planner", context: str = "") -> str`
- Reads agent profile from `backend/agents/{role}.md`.
- Instantiates a scoped subagent with restricted permissions:
  - Planner & Architect: Read-only tool access (`read_file`, `search_files`, `markitdown_read`, `list_directory`).
  - Iteration ceiling: 10 turns max.
  - Returns structured markdown plan or architecture document.

#### Background Memory Review (`_spawn_background_review`)
- Spawns background thread running `_run_background_review(messages)`.
- Prompts auxiliary model to identify durable user preferences, hardware updates, or persistent conventions.
- Appends verified declarative facts to `backend/memory/MEMORY.md`.

---

## 4. Component 2: `PromptBuilder` (`backend/core/prompt_builder.py`)

### 4.1 Design Principles
Stateless, deterministic prompt assembler that loads governance files, memory profiles, learned instincts, and skill schemas. Scans all injected markdown for prompt injection before loading into the system prompt.

### 4.2 Module Structure & Methods
```python
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

class PromptBuilder:
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        instinct_engine: Optional[Any] = None,
        shield: Optional[Any] = None,
    ):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.memory_dir = self.base_dir / "memory"
        self.skills_dir = self.base_dir / "skills"
        self.agents_dir = self.base_dir / "agents"
        self.instinct_engine = instinct_engine
        self.shield = shield
```

#### 1. Core Profile Loaders
- `load_soul_md() -> str`:
  - Path: `backend/memory/SOUL.md`.
  - Reads UTF-8 text, strips BOM (`\ufeff`), scans with `AgentShield`.
  - Defines J.A.R.V.I.S.'s cultured British persona, dry wit, and strict tool grounding.
- `load_user_md() -> str`:
  - Path: `backend/memory/USER.md`.
  - Returns user preferences, address ("Sir"), and system environment details.
- `load_memory_md() -> str`:
  - Path: `backend/memory/MEMORY.md`.
  - Returns durable factual knowledge, system topology, and governance rules.

#### 2. Learned Instincts Dynamic Injection
- `load_active_instincts(min_confidence: float = 0.70) -> str`:
  - Invokes `self.instinct_engine.get_active_instincts(min_confidence=0.70)`.
  - If engine unavailable, reads `~/.jarvis/homunculus/instincts/personal/*.yaml` directly.
  - Formats into an authoritative Markdown section:
    ```markdown
    ## Active Learned Instincts (Confidence >= 0.70)
    You have internalized the following behavioral patterns:
    - [security] Never execute destructive disk operations without explicit confirmation (confidence: 1.00)
    - [desktop] Prefer native COM UIAutomation over visual grounding for standard Windows controls (confidence: 0.85)
    - [preference] Respond concisely with British dry wit (confidence: 0.90)
    ```

#### 3. Runtime Skills Index Loader
- `load_skills_catalog() -> List[Dict[str, Any]]`:
  - Scans `backend/skills/*.md`.
  - Parses YAML frontmatter between `---` delimiters:
    - `name`: string identifier (e.g. `desktop_control`, `browser_background`, `deep_research`).
    - `description`: concise summary of capability.
    - `trigger`: comma-separated trigger keywords.
    - `tools`: list of bound tool names.
  - Returns structured skill catalog.
- `build_skills_system_prompt() -> str`:
  - Formats skills catalog into a grounding guide explaining when and how each skill toolset should be selected.

#### 4. System Prompt Assembly
- `build_system_prompt(extra_context: str = "") -> str`:
  - Assembles prompt sections in strict priority order:
    1. **Persona & Soul**: `load_soul_md()`
    2. **Operational Rules & 3-Tier Action Routing**: Windows COM UIA -> Background CDP -> Vision VLM.
    3. **User Profile**: `load_user_md()`
    4. **Long-Term Factual Memory**: `load_memory_md()`
    5. **Active Learned Instincts**: `load_active_instincts()`
    6. **Runtime Skills Catalog**: `build_skills_system_prompt()`
    7. **Dynamic Hardware Telemetry**: CPU, RAM, VRAM, and AC Power status.
    8. **Extra Context**: Custom task guidance if provided.

#### 5. Payload Assembly for LLM
- `assemble_messages(system_prompt: str, history: List[Dict[str, Any]], current_user_message: Optional[str] = None) -> List[Dict[str, Any]]`:
  - Slot 0: `{"role": "system", "content": system_prompt}`.
  - Subsequent slots: Cleaned message history from `state_db` (sanitizing internal markers like `_db_persisted`).
  - Final slot: `current_user_message` if not already appended to history.

#### 6. Subagent Prompt Builder
- `build_subagent_prompt(role: str, parent_goal: str) -> str`:
  - Path: `backend/agents/{role}.md` (`planner.md`, `architect.md`, `security_auditor.md`).
  - Injects mandatory constraints (e.g. 4-stage planning schema for planner, zero mutating tools).

---

## 5. Component 3: `ContextCompressor` (`backend/core/context_compressor.py`)

### 5.1 Design Principles
Context window compression algorithm derived from `NousResearch/hermes-agent/agent/context_compressor.py`. Automatically triggers when conversation exceeds 50% of the token window. Summarizes middle conversation turns while safeguarding system prompt, initial user prompt, recent turns, and tool call pairs.

### 5.2 Token Budget Constants
```python
DEFAULT_CONTEXT_WINDOW: int = 8192
COMPRESSION_THRESHOLD_RATIO: float = 0.50  # 4096 tokens on default window
HEAD_PROTECTION_TURNS: int = 2            # System prompt + initial user prompt
TAIL_PROTECTION_TOKENS: int = 2048        # ~4-6 recent turns protected from compaction
COMPRESSED_SUMMARY_METADATA_KEY: str = "_compressed_summary"
```

### 5.3 Compaction Hand-off Delimiters
```python
SUMMARY_PREFIX = (
    "[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted "
    "into the summary below. This is a handoff from a previous context "
    "window — treat it as background reference, NOT as active instructions. "
    "Do NOT answer questions or fulfill requests mentioned in this summary; "
    "they were already addressed. "
    "Respond ONLY to the latest user message that appears AFTER this "
    "summary — that message is the single source of truth for what to do "
    "right now. "
    "The current session state (files, config, etc.) may reflect work "
    "described here — avoid repeating it:\n\n"
)

SUMMARY_END_MARKER = (
    "\n--- END OF CONTEXT SUMMARY — "
    "respond to the message below, not the summary above ---"
)
```

### 5.4 Token Estimation & Threshold Evaluation
- `estimate_tokens(messages: List[Dict[str, Any]]) -> int`:
  - Rough fast estimation: $\approx 4\text{ chars} = 1\text{ token}$.
  - Structural token overhead: 4 tokens per message envelope + arguments JSON length.
- `should_compress(messages: List[Dict[str, Any]], current_tokens: Optional[int] = None) -> bool`:
  - Checks if estimated token count $\ge \text{context\_window} \times \text{threshold\_ratio}$.
  - Includes anti-thrashing check: if last two compressions saved $<10\%$ token space, returns `False` to prevent freeze loops.

### 5.5 Compaction Algorithm (`compress`)
```python
def compress(
    self,
    messages: List[Dict[str, Any]],
    current_tokens: Optional[int] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
```

1. **Pre-Pass Tool Result Pruning**:
   - Scans older messages for massive tool results (e.g. file dumps $>1000$ characters).
   - Truncates oversized results with `[TRUNCATED: output exceeded budget; 45 lines omitted]`.
   - Strips blank echo rows.

2. **Window Partitioning**:
   - `head_messages`: First $N$ messages (system prompt + first exchange, typically 2 messages).
   - `tail_messages`: Walking backward from the end, collects messages until reaching `TAIL_PROTECTION_TOKENS` budget (typically 4–8 messages).
   - `middle_messages`: Sliced between head and tail: `messages[head_size : len(messages) - len(tail_messages)]`.
   - If `len(middle_messages) < 2`, no compaction is performed; returns original list.

3. **Structured Middle-Turn Summarization**:
   - Passes `middle_messages` to auxiliary fast LLM (or internal rule-based summarizer fallback):
     ```markdown
     Summarize the following intermediate conversation turns.
     Provide a concise report covering:
     1. ## Historical Task Snapshot: Core objective and progress.
     2. ## Decisions & Findings: Key files examined, parameters discovered, tool outcomes.
     3. ## Completed Work: Actions already landed.
     Do NOT include future instructions or open questions.
     ```
   - Formats output: `formatted_summary = SUMMARY_PREFIX + summary_text + SUMMARY_END_MARKER`.
   - Wraps summary in a message dictionary:
     ```python
     summary_message = {
         "role": "user",
         "content": formatted_summary,
         COMPRESSED_SUMMARY_METADATA_KEY: True,
     }
     ```

4. **Orphaned Tool Call / Result Sanitization**:
   - Verifies every `assistant` message with `tool_calls` in `tail_messages` has corresponding `tool` messages matching `tool_call_id`.
   - Removes dangling `tool` results whose parent `assistant` message was compacted into the middle slice.
   - Prevents provider API errors (`"tool_call_id not found"`).

5. **Soft-Compacting in Database**:
   - If `state_db` and `session_id` are provided:
     - Updates compacted middle messages in SQLite WAL:
       `UPDATE messages SET active = 0 WHERE session_id = ? AND id IN (...)`
     - Inserts the newly generated summary row into `messages` with `active = 1` and `metadata = '{"is_summary": true}'`.

6. **Assembly**:
   - Assembles final list: `head_messages + [summary_message] + tail_messages`.
   - Strips internal persistence markers (`_db_persisted`).

---

## 6. Component 4: `ToolDispatcher` (`backend/core/tool_dispatcher.py`)

### 6.1 Design Principles
Parallel execution engine assimilating `model_tools.py` and `agent/tool_executor.py` with `_MAX_TOOL_WORKERS = 8`, 3-tier validation gauntlet, loop guardrail halting, and ECC hook dispatching.

### 6.2 3-Tier Action Validation Architecture

```
Incoming Tool Call: {"tool": "...", "args": {...}}
                  │
                  ▼
┌────────────────────────────────────────────────────────┐
│  Tier 1: Security & Governance Validation             │
│  - AgentShield.validate_tool_call()                    │
│  - Regex check: 14 secret patterns                     │
│  - Destructive command block (rm -rf, format, del)     │
│  - HWND deadlock exclusion for J.A.R.V.I.S. Electron   │
│  - ECCHookDispatcher.pre_tool_use() hook check         │
└────────────────────────┬───────────────────────────────┘
                         │ Pass
                         ▼
┌────────────────────────────────────────────────────────┐
│  Tier 2: Role Permissions & Action Classification      │
│  - Subagent constraint check (Planner/Architect = RO)  │
│  - Read/Write categorization:                          │
│    * Read tools -> Parallel execution segment          │
│    * Mutating tools -> Sequential execution barrier    │
└────────────────────────┬───────────────────────────────┘
                         │ Pass
                         ▼
┌────────────────────────────────────────────────────────┐
│  Tier 3: Execution Routing & Loop Guardrail            │
│  - Hash signature check: sha256(tool_name + args)      │
│  - Streak tracking: max 5 identical calls -> HALT      │
│  - Route to target service (MCP / OmniParser / Runner) │
│  - ECCHookDispatcher.post_tool_use() observation log   │
└────────────────────────────────────────────────────────┘
```

### 6.3 Tool Execution Loop Guard (`ToolCallGuardrailController`)
- **Signature**: `ToolCallSignature(tool_name: str, args_hash: str)` where `args_hash = sha256(canonical_json(args))`.
- **Thresholds**:
  - `warn_after = 2`: Consecutive identical tool calls log an internal warning.
  - `hard_stop_after = 5`: Consecutive identical tool calls raise `ToolLoopHaltException`.
  - Injected error payload:
    ```json
    {
      "error": "Tool execution loop halted",
      "message": "Tool 'read_file' with identical arguments was called 5 consecutive times without making progress. Execution halted."
    }
    ```

### 6.4 Registered Capabilities Catalog (Section 6.5 Tools)
The dispatcher registers handlers for all Phase 6 tools:

1. **`windows_mcp_snapshot(use_dom: bool = False)`**:
   - Calls `WindowsMCPBridge.get_state()`.
   - Excludes Electron `HWND` to prevent COM UIAutomation deadlock.
2. **`windows_mcp_click(x: int, y: int, button: str = "left", clicks: int = 1)`**:
   - Native sub-10ms Windows UIA mouse click.
3. **`windows_mcp_type(x: int, y: int, text: str, clear: bool = False, press_enter: bool = False)`**:
   - Native Windows UIA text input.
4. **`windows_mcp_app(action: str, name: str)`**:
   - Launches, focuses, or closes Windows applications.
5. **`windows_mcp_shortcut(keys: List[str])`**:
   - Executes OS hotkeys (`["ctrl", "c"]`, `["win", "d"]`).
6. **`agent_s3_visual_task(instruction: str)`**:
   - Takes desktop screenshot, calls `omniparser_service.py` on port 8002 for Set-of-Marks, evaluates exact termination `action[0].strip().upper() in ("DONE", "FAIL")`, executes `pyautogui`.
7. **`browser_use_background(task: str, headless: bool = True)`**:
   - Headless background Chrome DevTools Protocol automation without moving user cursor.
8. **`markitdown_convert(source_path_or_url: str)`**:
   - Converts PDF, DOCX, XLSX (with `showZeroes` XML repair), images to Markdown.
9. **`crawl4ai_extract(url: str, query: str = "")`**:
   - Fast noise-free web scraping with `PruningContentFilterLXML` + `BM25ContentFilter`.
10. **`gpt_researcher_report(query: str, report_type: str = "research_report")`**:
    - Multi-source web research report generator.
11. **`mobilerun_phone_task(goal: str, device_ip: str = "")`**:
    - Wireless Android ADB (`:5555`) and Portal HTTP (`:8080`) mobile automation.
12. **Agent Loop Tools**:
    - `todo(action, task_id, title)`: Manages task items.
    - `memory(action, content, category)`: Updates long-term memory.
    - `session_search(query, limit)`: FTS5 search across sessions.
    - `delegate_task(goal, role, context)`: Spawns planner/architect subagents.

### 6.5 Dispatching Logic (`dispatch_tool_calls`)
```python
def dispatch_tool_calls(
    self,
    tool_calls: List[Dict[str, Any]],
    session_id: str = "default",
) -> List[Dict[str, Any]]:
```
1. Partition incoming `tool_calls` into sequential segments:
   - Groups consecutive read-only tools into a parallel execution segment.
   - Treats any mutating tool as a sequential execution barrier.
2. For read segments:
   - Dispatch to `ThreadPoolExecutor(max_workers=8)` using `futures = [pool.submit(self._run_tool, call, session_id) for call in segment]`.
   - Await all reads concurrently with timeout (default: 60s).
3. For mutating tools:
   - Execute one at a time on the main execution thread.
4. In `_run_tool(call, session_id)`:
   - **Pre-execution**: Check loop guard. Check `AgentShield.validate_tool_call()`. Check `ECCHookDispatcher.pre_tool_use()`.
   - **Execution**: Measure start time with `time.perf_counter()`. Invoke handler.
   - **Post-execution**: Measure `duration_ms`.
   - **Logging**: Invoke `ECCHookDispatcher.post_tool_use(tool_name, args, result, status, duration_ms, session_id)`.
   - **Return**: `{tool_call_id, tool_name, result, status, duration_ms}`.

---

## 7. Component 5: `CronScheduler` (`backend/core/cron_scheduler.py`)

### 7.1 Design Principles
Background scheduled task executor running on a 60-second tick cadence. Incorporates cross-process Windows `msvcrt` file locking (`.tick.lock`) to prevent concurrent execution when multiple instances or testing workers overlap.

### 7.2 Storage Schema & Paths
- Directory: `~/.jarvis/cron/`
- Jobs File: `~/.jarvis/cron/jobs.json`
- Output Logs: `~/.jarvis/cron/output/{job_id}/{timestamp}.json`
- Heartbeat: `~/.jarvis/cron/ticker_heartbeat`
- Tick Lock: `~/.jarvis/cron/.tick.lock`
- Inbox File: `~/.jarvis/inbox.json`

### 7.3 Data Models
```python
@dataclass
class CronJob:
    id: str
    name: str
    schedule: str  # Cron expression (e.g. "*/15 * * * *") or interval ("every 1h", "daily 09:00")
    task_prompt: str
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

### 7.4 Windows-Safe Cross-Process File Lock
```python
import msvcrt

class WindowsTickLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._file = None

    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.lock_path, "a+b")
        try:
            # LK_NBLCK: Non-blocking exclusive lock
            msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            return self
        except OSError:
            self._file.close()
            self._file = None
            return None  # Another process holds the tick lock

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            try:
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                self._file.close()
                self._file = None
```

### 7.5 Ticker Loop (`tick`) & Execution Flow
1. **Tick Lock**: Attempt to acquire `WindowsTickLock`. If not acquired, exit tick immediately (sibling process is ticking).
2. **Heartbeat**: Touch `~/.jarvis/cron/ticker_heartbeat` with current UTC timestamp.
3. **Paused Check**: If paused via `system.toggle` (`self._is_paused = True`), log status and return.
4. **Load & Evaluate Jobs**:
   - Load `jobs.json` with thread safety (`threading.RLock`).
   - For each enabled job:
     - Check if `current_time >= next_run`.
     - If due:
       - **Prompt Threat Scan**: Run `AgentShield.scan_input(job.task_prompt)`. If prompt injection detected, flag `CronPromptInjectionBlocked` and abort job.
       - **Execution**: Dispatch job to background worker or `HermesBrain.run_turn(session_id=f"cron_{job.id}", user_message=job.task_prompt)`.
       - **Persist Output**: Write execution outcome to `~/.jarvis/cron/output/{job.id}/{timestamp}.json`.
       - **Push to Inbox**: Append notification item to `~/.jarvis/inbox.json`:
         ```json
         {
           "id": "notif_uuid",
           "type": "cron_completion",
           "job_id": "job_123",
           "title": "Scheduled Briefing: System Health",
           "summary": "Completed successfully. CPU load 12%, Battery 98%.",
           "timestamp": "2026-11-10T09:45:00Z",
           "read": false
         }
         ```
       - **WebSocket Broadcast**: If `ws_broadcast_callback` is provided:
         `broadcast({"type": "cron.job_complete", "payload": {"job_id": job.id, "name": job.name}})`
       - **Compute Next Run**: Calculate new `next_run` timestamp via `croniter` or parsed interval.
       - Update `last_run` timestamp.
   - Save updated jobs to `jobs.json`.

### 7.6 Public Interface Methods
- `start()`: Starts daemon thread calling `tick()` every 60 seconds.
- `stop()`: Signals cancellation event and joins thread.
- `pause()` / `resume()` / `toggle()`: Integrates with `system.toggle` WebSocket command.
- `add_job(name, schedule, task_prompt, enabled=True) -> CronJob`: Registers new job.
- `remove_job(job_id) -> bool`: Deletes scheduled job.
- `list_jobs() -> List[CronJob]`: Returns all registered jobs.
- `get_inbox_items() -> List[Dict[str, Any]]`: Returns inbox records for `GET /v1/inbox`.

---

## 8. Edge Cases & Resilience Strategy

| Module | Edge Case | Expected Behavior |
|---|---|---|
| `HermesBrain` | User calls `reset_abort` while LLM is generating tokens | `interrupt()` sets `_interrupt_event`; streaming loop detects flag, breaks out immediately, outputs checkpoint, and yields `interrupted` event. |
| `HermesBrain` | Tool call triggers an infinite error loop (e.g. file not found repeatedly) | `ToolDispatcher`'s loop guard halts turn on the 5th identical call, feeding a clean explanation back to the model. |
| `PromptBuilder` | `SOUL.md` or a skill file contains prompt injection attack | `_scan_context_content()` detects threat via `AgentShield`, replaces content with `[BLOCKED: potential prompt injection]`. |
| `PromptBuilder` | Windows Notepad UTF-8 BOM (`\ufeff`) prepended to `SOUL.md` | `PromptBuilder` strips `\ufeff` before parsing so file loads cleanly without false-positive threat triggers. |
| `ContextCompressor` | Middle turns contain dangling `tool_call` without `tool_result` | Post-compaction sanitization drops or synthesizes empty tool response so downstream LLM APIs don't fail. |
| `ContextCompressor` | Incompressible floor: system prompt + tool schemas already exceed 50% | `_record_ineffective_compression_verdict()` detects $<10\%$ token savings and stops compactor from infinite thrashing. |
| `ToolDispatcher` | Model requests parallel write operations to the same file | Mutating tools are classified as sequential barriers; parallel pool only executes read-only tools. |
| `ToolDispatcher` | Desktop automation attempts to inspect J.A.R.V.I.S. Electron window | `windows_mcp_*` tools automatically exclude the Electron `HWND`, preventing UIAutomation COM deadlocks. |
| `CronScheduler` | Multiple ticker processes or test runners overlap | `WindowsTickLock` (`msvcrt.locking`) allows only one process to execute the tick; sibling processes return immediately. |
| `CronScheduler` | System power toggle (`system.toggle`) pauses assistant | Scheduler pauses task dispatching while keeping interval timers intact until resumed. |

---

## 9. Verification & Smoke Test Plan

To verify the Milestone 2 autonomous brain and execution core implementation:

### Step 1: Unit & Component Tests
```powershell
python -m unittest tests/test_m2_core.py
```
- Tests `HermesBrain.run_turn` streaming generator and event schemas.
- Tests `HermesBrain.interrupt()` halting generation within 15 ms.
- Tests `PromptBuilder` loading `SOUL.md`, `USER.md`, `MEMORY.md`, instincts, and skills.
- Tests `ContextCompressor` token tracking, middle-turn reduction, and orphan sanitization.
- Tests `ToolDispatcher` parallel execution of 8 workers and 5-streak loop guard halting.
- Tests `CronScheduler` 60s tick, file locking, and inbox notifications.

### Step 2: REST & WebSocket Gateway Integration
```powershell
python -m unittest tests/test_challenger_empirical_m1.py
```
- Validates `GET /v1/tools` returns the full tool catalog from `ToolDispatcher`.
- Validates `POST /v1/tools/invoke` executes registered tools.
- Validates `GET /v1/inbox` returns scheduled task completions.
- Validates `GET /sessions` and `GET /sessions/{id}/messages` interact with `SessionDB`.

### Step 3: End-to-End WebSocket Flow
```powershell
python -m unittest tests/e2e/test_tier1_features.py -k "Brain or Dispatcher or Cron"
```
- Verifies client sending `user.message` receives `agent.token`, `tool.start`, `tool.result`, and `agent.complete` events.
- Verifies client sending `reset_abort` halts the brain turn immediately.

---

## 10. Conclusion & Handoff Readiness
All five core execution modules are comprehensively specified with clear interface boundaries, exact data schemas, resilient failure modes, and seamless cross-module interoperability. Implementers can directly translate these blueprints into production-ready code in `backend/core/`.
