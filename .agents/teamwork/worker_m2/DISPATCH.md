## 2026-11-10T09:46:28Z
You are worker_m2, a teamwork_worker subagent.
Your Working Directory: .agents/teamwork/worker_m2 (create this directory, write only in this directory for your logs/progress/handoff).
Parent Orchestrator Conversation ID: 0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Context & Source Material:
- e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md
- e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md
- e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_1\analysis.md
- e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_1\handoff.md
- e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_2\analysis.md
- e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_2\handoff.md
- e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_3\analysis.md
- e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_3\handoff.md
- Donor repo reference at: C:\Users\utpal\AppData\Local\hermes\hermes-agent\

Exclusive Write Ownership:
You have exclusive write ownership of the following 9 backend files:
1. backend/security/agent_shield.py
2. backend/security/ecc_hooks.py
3. backend/memory/instinct_engine.py
4. backend/memory/state_db.py
5. backend/core/context_compressor.py
6. backend/core/prompt_builder.py
7. backend/core/tool_dispatcher.py
8. backend/core/hermes_brain.py
9. backend/core/cron_scheduler.py
(You may also make necessary import/wiring adjustments in backend/main.py to wire state_db, agent_shield audit logs, tool dispatcher, and inbox endpoints without breaking existing M1 health or CORS or routing).
ZERO UI TOUCH: DO NOT modify any files in src/!

Target Implementations:
1. backend/security/agent_shield.py:
   - 14 secret patterns (OpenAI, Anthropic, AWS, GitHub, Google API keys, private keys, JWT, passwords, Slack, Discord, Telegram, Azure, Stripe, high-entropy).
   - Destructive command blocking (rm -rf, format, del /f /s /q, registry wipe, disk wipe, fork bombs).
   - Config-protection guard (.env, config.json, governance rules, system files, .eslintrc, tsconfig.json, vite.config.ts, package.json, locked UI files).
   - Prompt injection scanning (scan_for_threats, jailbreaks, DAN, system prompt extraction, rule overrides).
   - Dataclass SecurityScanResult and public methods scan_input(text) -> SecurityScanResult, validate_command(cmd) -> bool, sanitize_output(text) -> str, verify_file_path(path, write_mode) -> Tuple[bool, str], validate_tool_call(tool, args) -> Tuple[bool, str].
   - Expose audit_logs list for GET /v1/audit.
2. backend/security/ecc_hooks.py:
   - ECCHookDispatcher with pre_tool_use(tool_name, args, session_id) / pre_tool_hook and post_tool_use(tool_name, args, result, status, duration_ms, session_id) / post_tool_hook.
   - pre_tool_use runs AgentShield.validate_tool_call().
   - post_tool_use appends JSON line to ~/.jarvis/homunculus/observations.jsonl.
   - format_observation(tool, args, status).
3. backend/memory/instinct_engine.py:
   - InstinctEngine: parse observations from ~/.jarvis/homunculus/observations.jsonl.
   - Store atomic YAML/Markdown instincts in ~/.jarvis/homunculus/instincts/personal/.
   - Confidence scoring: Score = min(1.0, max(0.0, 0.50 + 0.05 * confirmations - 0.10 * contradictions)), where 10 confirmations evaluates to 1.0 (>= 0.9).
   - Methods: get_active_instincts(), score_instinct(trigger, confs, conts), render_prompt_injection(), prune_instincts(min_confidence).
4. backend/memory/state_db.py:
   - SessionDB with SQLite WAL mode at ~/.jarvis/state.db.
   - PRAGMAs: journal_mode=WAL; synchronous=NORMAL; foreign_keys=ON; busy_timeout=30000;.
   - Schema Version 12: schema_version, sessions, messages (with active INTEGER DEFAULT 1), tool_calls, fts_messages external content FTS5 virtual table.
   - Triggers: messages_ai, messages_ad, messages_au keeping fts_messages synchronized.
   - Thread-local SQLite connection pool (threading.local()) + write lock.
   - FTS5 query sanitization with fallback to LIKE %query%.
   - Methods: create_session, get_session, list_sessions, delete_session, add_message, get_messages, search_fts, record_tool_call.
5. backend/core/context_compressor.py:
   - ContextCompressor: compacts when exceeding 50% window. Preserves head/tail, cleans orphaned tool pairs, soft-compacts rows in SessionDB (active = 0). Anti-thrashing strike counter.
6. backend/core/prompt_builder.py:
   - PromptBuilder: loads SOUL.md, USER.md, MEMORY.md, skills/*.md, and active instincts (>= 0.7) from instinct_engine.py. Strips BOM, sanitizes prompt injection threats.
7. backend/core/tool_dispatcher.py:
   - ToolDispatcher: _MAX_TOOL_WORKERS = 8 parallel read workers + sequential write barriers.
   - ToolCallGuardrailController detecting repetitive loops (warn at 2, block at 5).
   - Integrates AgentShield.validate_tool_call() and ECCHookDispatcher (pre_tool_use, post_tool_use).
   - Full tool registry (windows_mcp_*, agent_s3_*, browser_use_*, markitdown_*, crawl4ai_*, gpt_researcher_*, mobilerun_*, todo, memory, session_search, delegate_task).
8. backend/core/hermes_brain.py:
   - HermesBrain: asynchronous run_conversation / run_turn streaming BrainEvent deltas (tokens, tool call start/result, status).
   - interrupt() / request_hard_interrupt() wired to reset_abort (halts LLM stream and cancels tool tasks within 15ms).
   - delegate_task() supporting planner and architect subagents.
   - Fallback/mock completion generator when live ModelRouter is not yet available.
9. backend/core/cron_scheduler.py:
   - CronScheduler: 60-second tick() loop.
   - Windows msvcrt file lock (.tick.lock).
   - Job registration, execution, pushing alerts to ~/.jarvis/inbox.json and WebSocket broadcast.
