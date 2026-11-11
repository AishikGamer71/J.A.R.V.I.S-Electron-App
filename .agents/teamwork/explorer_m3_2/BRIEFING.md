# BRIEFING — 2026-11-10T11:53:30Z

## Mission
Investigate and design complete technical blueprints for Milestone M3 backend modules: `backend/engine/model_router.py` and `backend/memory/hybrid_rag.py`.

## 🔒 My Identity
- Archetype: explorer
- Roles: Technical investigation, architectural blueprinting, synthesis
- Working directory: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m3_2\
- Original parent: 0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4
- Milestone: M3 (Model Router & Hybrid RAG)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code files in backend/ or other project code.
- Write analysis and blueprint handoff to `.agents/teamwork/explorer_m3_2/handoff.md`.
- Include exact data classes/schemas, method signatures, exact RRF k=60 math and tie-breaking, and concrete code structure ready for Worker.

## Current Parent
- Conversation ID: 0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4
- Updated: 2026-11-10T11:53:30Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`, `PROJECT.md`
  - `c:\Users\utpal\Downloads\jarvis_antigravity_master_prompt.md` (Phases 3, 6.2)
  - `backend/core/hermes_brain.py` (streaming contract with `model_router.stream_chat`)
  - `backend/memory/state_db.py` (FTS5 search mechanism and SQLite WAL schema)
  - `backend/main.py` (Gateway integration: `/v1/core-memory`, `/search`)
  - `tests/e2e/test_tier1_features.py` (exact test assertions for F17 & F18)
  - `tests/e2e/test_tier3_combinations.py` (PowerGuardian throttling & RRF pipeline)
  - Python runtime environment dependency probe (`numpy`, `onnxruntime`, `sqlite3`, `httpx` available; `faiss`, `sentence_transformers`, `torch` absent)
- **Key findings**:
  1. `ModelRouter` must provide `route_query(query) -> RouteDecision` with attributes `.tier`, `.engine`, `.model`, `.quantized_or_cpu`.
  2. `ModelRouter.update_vram_status(vram_available_mb=0)` sets `quantized_or_cpu = True`.
  3. `ModelRouter.get_fallback_engine()` returns deterministic persona engine.
  4. `ModelRouter.stream_chat(messages)` returns async generator yielding chunks with `"delta"` field.
  5. `compute_rrf_score(rank: int, k: int = 60)` must compute $1.0 / (k + \text{rank})$.
  6. `HybridMemory.fuse_ranks(fts_hits, vec_hits, k=60)` returns merged results where index `[0][0]` is the top `doc_id`.
  7. Because `faiss` and `sentence_transformers` are not installed, `HybridMemory` must implement a resilient `NumpyDenseEmbedder` (384-D character/token hash vectors with L2 normalization) providing <0.1ms semantic similarity.
- **Unexplored areas**: None remaining for M3.2 scope.

## Key Decisions Made
- Architecture for `ModelRouter` uses 3-layer routing: HeuristicRouter (syntax/urgency analysis) -> TraceDrivenPolicy (`~/.jarvis/traces.db` composite reward) -> MultiEngineDispatcher (Ollama, Cloud, Fallback).
- Architecture for `HybridMemory` uses unified SQLite FTS5 for lexical search + `NumpyDenseEmbedder` with pure NumPy dot product for vector search, fused via RRF $k=60$.

## Artifact Index
- `DISPATCH.md` — Record of dispatch task
- `BRIEFING.md` — Persistent working memory
- `progress.md` — Liveness heartbeat and progress tracker
- `handoff.md` — Final technical blueprint for Worker
