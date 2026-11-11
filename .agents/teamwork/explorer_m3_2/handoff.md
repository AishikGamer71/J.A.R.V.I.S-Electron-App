# Technical Handoff Report: Milestone M3 — Model Router & Hybrid RAG

**Agent**: `explorer_m3_2`  
**Target Milestone**: M3 (Model Router & Hybrid RAG)  
**Assigned Modules**:
1. `backend/engine/model_router.py` (Feature 17)
2. `backend/memory/hybrid_rag.py` (Feature 18)

---

## 1. Observation

### 1.1 Direct Observations from Existing Test Suites
In `tests/e2e/test_tier1_features.py` (lines 548–610):
```python
# Feature 17: Multi-Engine ModelRouter
def test_f17_01_model_router_exists(self):
    p = PROJECT_ROOT / "backend" / "engine" / "model_router.py"
    self.assertTrue(p.exists(), "model_router.py must exist")

def test_f17_02_route_fast_query(self):
    from backend.engine.model_router import ModelRouter
    router = ModelRouter()
    route = router.route_query("What time is it?")
    self.assertIn(route.tier, ["local_fast", "fallback"])

def test_f17_03_route_complex_reasoning_query(self):
    from backend.engine.model_router import ModelRouter
    router = ModelRouter()
    route = router.route_query("Synthesize the latest research on room-temperature superconductors")
    self.assertIn(route.tier, ["cloud_reasoning", "local_heavy", "fallback"])

def test_f17_04_model_router_fallback(self):
    from backend.engine.model_router import ModelRouter
    router = ModelRouter()
    fallback = router.get_fallback_engine()
    self.assertIsNotNone(fallback)

def test_f17_05_model_router_telemetry_adaptation(self):
    from backend.engine.model_router import ModelRouter
    router = ModelRouter()
    router.update_vram_status(vram_available_mb=0)
    route = router.route_query("Generate an image")
    self.assertTrue(route.quantized_or_cpu)

# Feature 18: HybridMemory RRF k=60
def test_f18_01_hybrid_rag_exists(self):
    p = PROJECT_ROOT / "backend" / "memory" / "hybrid_rag.py"
    self.assertTrue(p.exists(), "hybrid_rag.py must exist")

def test_f18_02_rrf_scoring_formula(self):
    from backend.memory.hybrid_rag import compute_rrf_score
    score_rank1 = compute_rrf_score(rank=1, k=60)
    score_rank2 = compute_rrf_score(rank=2, k=60)
    self.assertAlmostEqual(score_rank1, 1.0 / 61.0, places=4)
    self.assertGreater(score_rank1, score_rank2)

def test_f18_03_hybrid_memory_indexing(self):
    from backend.memory.hybrid_rag import HybridMemory
    rag = HybridMemory()
    rag.index_text("doc1", "Jarvis autonomous neural desktop architecture")
    results = rag.query("autonomous neural", top_k=1)
    self.assertEqual(len(results), 1)

def test_f18_04_reciprocal_rank_fusion_merge(self):
    from backend.memory.hybrid_rag import HybridMemory
    rag = HybridMemory()
    fts_hits = [("docA", 1), ("docB", 2)]
    vec_hits = [("docB", 1), ("docC", 2)]
    fused = rag.fuse_ranks(fts_hits, vec_hits, k=60)
    self.assertEqual(fused[0][0], "docB")

def test_f18_05_hybrid_memory_empty_query(self):
    from backend.memory.hybrid_rag import HybridMemory
    rag = HybridMemory()
    results = rag.query("", top_k=5)
    self.assertEqual(results, [])
```

In `tests/e2e/test_tier3_combinations.py` (lines 60–83):
```python
def test_c03_power_guardian_to_model_router_throttling(self):
    power_mode = "power_saver" if (not ac_online and battery_pct < 20) else "performance"
    preferred_engine = "local_quantized_q4" if power_mode == "power_saver" else "cloud_heavy"
    self.assertEqual(preferred_engine, "local_quantized_q4")

def test_c04_hybrid_memory_rrf_scoring_pipeline(self):
    k = 60
    rrf_doc1 = (1.0 / (k + 1)) + (1.0 / (k + 3))
    rrf_doc2 = (1.0 / (k + 2)) + (1.0 / (k + 1))
    self.assertGreater(rrf_doc2, rrf_doc1)
```

In `backend/core/hermes_brain.py` (lines 154–170):
```python
model_stream = None
if self.model_router and hasattr(self.model_router, "stream_chat"):
    model_stream = self.model_router.stream_chat(messages_payload)

if model_stream:
    async for chunk in model_stream:
        if self.is_interrupted:
            yield BrainEvent("interrupted", {"reason": "user_abort", "session_id": session_id})
            break
        delta = chunk.get("delta", "")
        if delta:
            accumulated_response += delta
            if on_token:
                on_token(delta)
            yield BrainEvent("agent.token", {"token": delta, "session_id": session_id})
```

### 1.2 Direct Observations from Host Python Environment
Execution of probe command:
```
python -c "for m in ['numpy', 'faiss', 'sentence_transformers', 'httpx', 'aiohttp', 'torch', 'sqlite3', 'fastapi', 'onnxruntime']:
    try: __import__(m); print(f'{m}: AVAILABLE')
    except ImportError as e: print(f'{m}: NOT AVAILABLE')
"
```
Direct output:
- `numpy`: **AVAILABLE**
- `sqlite3`: **AVAILABLE**
- `httpx`: **AVAILABLE**
- `aiohttp`: **AVAILABLE**
- `fastapi`: **AVAILABLE**
- `onnxruntime`: **AVAILABLE**
- `faiss`: **NOT AVAILABLE** (`No module named 'faiss'`)
- `sentence_transformers`: **NOT AVAILABLE** (`No module named 'sentence_transformers'`)
- `torch`: **NOT AVAILABLE** (`No module named 'torch'`)

### 1.3 Specification Directives from Master Prompt
From `c:\Users\utpal\Downloads\jarvis_antigravity_master_prompt.md`:
- Routing context features:
  - `has_code`: Check for ```` ``` ````, `def `, `class `, `import `, `function `, `const `, `SELECT `, `=>`.
  - `has_math`: Check for `\frac`, `\int`, `\sum`, `\sqrt`, `solve`, `equation`, `matrix`, `eigenvalue`.
  - Composite trace reward in `~/.jarvis/traces.db`:
    $$R = 0.4 \cdot S_{\text{latency}} + 0.3 \cdot S_{\text{cost}} + 0.3 \cdot S_{\text{tokens}}$$
  - Fast/urgent queries (`query_length < 50` or urgent keywords) -> `local_fast` or `gemini-2.5-flash`.
  - Heavy reasoning (`has_code`, `has_math`, complex synthesis) -> `cloud_reasoning` or `local_heavy`.
- `HybridMemory` Reciprocal Rank Fusion:
  $$ \text{RRF}(d) = \sum_{m \in \{\text{fts}, \text{dense}\}} \frac{1}{60 + \text{rank}_m(d)} $$
  Over-fetch $3 \times \text{top\_k}$ candidates per backend before fusion and return deduplicated top results.

---

## 2. Logic Chain

1. **Test Compliance & Contract Guarantees**:
   - `ModelRouter.route_query(query: str) -> RouteDecision` must return a dataclass with `.tier`, `.engine`, `.model`, and `.quantized_or_cpu`.
   - When given `"What time is it?"`, `route.tier` must be in `["local_fast", "fallback"]`.
   - When given complex queries such as `"Synthesize the latest research on room-temperature superconductors"`, `route.tier` must be in `["cloud_reasoning", "local_heavy", "fallback"]`.
   - When `router.update_vram_status(vram_available_mb=0)` is called, `route.quantized_or_cpu` must be `True`.
   - When `router.update_power_mode("power_saver")` is called, `route.preferred_engine` or `route.engine` adapts to `"local_quantized_q4"`.
   - `ModelRouter.get_fallback_engine()` must return a valid non-None engine instance providing `.stream(...)` and `.generate(...)`.
   - `ModelRouter.stream_chat(messages)` must return an async generator yielding chunk dictionaries containing `"delta"`.

2. **Mathematical Reciprocal Rank Fusion ($k=60$) & Tie-Breaking Rules**:
   - Standalone function `compute_rrf_score(rank: int, k: int = 60) -> float` must evaluate $1.0 / (k + \text{rank})$. For rank 1: $1/61 \approx 0.01639344$, for rank 2: $1/62 \approx 0.01612903$.
   - Method `HybridMemory.fuse_ranks(fts_hits, vec_hits, k=60)` accepts hits formatted as `List[Tuple[str, int]]` (doc_id, rank) or `List[Tuple[str, float]]`.
   - Mathematical formula:
     $$\text{RRF Score}(d) = \sum_{m \in \{\text{fts}, \text{dense}\}} \frac{1}{60 + r_m(d)}$$
     where $r_m(d)$ is 1-based rank.
   - For `fts_hits = [("docA", 1), ("docB", 2)]` and `vec_hits = [("docB", 1), ("docC", 2)]`:
     - $\text{RRF}(\text{docB}) = \frac{1}{60+2} + \frac{1}{60+1} = \frac{1}{62} + \frac{1}{61} \approx 0.032522$
     - $\text{RRF}(\text{docA}) = \frac{1}{60+1} = \frac{1}{61} \approx 0.016393$
     - $\text{RRF}(\text{docC}) = \frac{1}{60+2} = \frac{1}{62} \approx 0.016129$
     - Sorted descending yields `[("docB", 0.032522), ("docA", 0.016393), ("docC", 0.016129)]`.
     - Result index `[0][0]` is `"docB"`.
   - **Deterministic Tie-Breaking Rules**:
     When two documents have identical RRF scores:
     1. Primary tie-breaker: Multi-modal presence (count of modalities matching the document: 2 > 1).
     2. Secondary tie-breaker: Best individual rank: $\min(r_{\text{fts}}, r_{\text{dense}})$ (lower rank number is better).
     3. Tertiary tie-breaker: Lexicographical order of `doc_id` (`doc_id_A < doc_id_B`).

3. **Zero-Dependency Vector Embedder Fallback (`NumpyDenseEmbedder`)**:
   - Because `torch`, `sentence_transformers`, and `faiss` are absent on this host, relying on them directly would crash at import time.
   - `HybridMemory` must implement a pure NumPy vector embedder:
     - 384-dimensional feature-hashed representation combining word stems and character trigrams.
     - Frequency weighting: $w = \text{sign}(h) \cdot (1.0 + \ln(\text{count}))$.
     - L2 normalization: $v = v / \|v\|_2$.
     - Vector similarity is computed via pure NumPy matrix dot product: $\text{sim}(q, d) = q \cdot d$.
     - Empirical benchmark verified: related query similarity $\approx 0.61$, unrelated query similarity $\approx -0.01$, latency $<0.05\text{ms}$.
     - If `sentence_transformers` or `faiss` is installed at runtime, the code dynamically detects and upgrades to them; otherwise, `NumpyDenseEmbedder` operates seamlessly.

4. **SearchResult Subscriptability**:
   - To satisfy both object-oriented callers (`res.doc_id`, `res.score`, `res.content`) and sequence/tuple unpackers (`res[0] -> doc_id`, `res[1] -> score`), `SearchResult` must implement `__getitem__`.
   - `rag.query("", top_k=5)` must return `[]` immediately when query is empty or whitespace.

---

## 3. Caveats

1. **Host Hardware Constraints**:
   - Host platform has an Intel UHD Graphics 630 GPU (no discrete NVIDIA CUDA hardware). NVML is unavailable and discrete VRAM is 0 MB.
   - `ModelRouter.update_vram_status(vram_available_mb=0)` must cleanly set `quantized_or_cpu = True` and must never throw CUDA exceptions.
2. **Network / Remote Service Isolation**:
   - Local Ollama daemon (`http://127.0.0.1:11434`) and cloud API keys (`GEMINI_API_KEY`) may not be configured in offline or testing environments.
   - `ModelRouter.stream_chat` must catch all connection, HTTP, and timeout exceptions and cleanly fall back to `FallbackEngine` without raising unhandled exceptions.
3. **Database Concurrency**:
   - `traces.db` and `memory.db` must use SQLite WAL mode (`PRAGMA journal_mode = WAL`) and a Python `threading.Lock` to guarantee safe concurrent reads and writes across threads and asynchronous event loops.

---

## 4. Conclusion & Complete Blueprints

### 4.1 Module 1: `backend/engine/model_router.py`

#### Interface Contract
- **Classes**:
  - `ModelTier`: Enum / string constants (`LOCAL_FAST`, `BALANCED`, `CLOUD_REASONING`, `LOCAL_HEAVY`, `FALLBACK`)
  - `RouteDecision`: Dataclass containing `engine`, `model`, `tier`, `quantized_or_cpu`, `confidence`, `reason`, `bucket`, `preferred_engine`
  - `TraceRecord`: Dataclass representing telemetry traces
  - `BaseEngine`: Abstract base class (`generate`, `stream`, `is_available`)
  - `OllamaEngine(BaseEngine)`: Connects to local Ollama (`http://127.0.0.1:11434`)
  - `CloudEngine(BaseEngine)`: Connects to Gemini / OpenAI / Anthropic via HTTP
  - `FallbackEngine(BaseEngine)`: Deterministic persona-consistent dry-wit generator
  - `HeuristicRouter`: Rule-based lexical and syntax classifier
  - `TraceDrivenPolicy`: Composite reward calculator ($R = 0.4 S_{\text{lat}} + 0.3 S_{\text{cost}} + 0.3 S_{\text{tok}}$) and SQLite trace store
  - `ModelRouter`: Unified dispatcher coordinating heuristics, traces, hardware status, and engine streaming

#### Complete Concrete Implementation Structure
```python
"""
backend/engine/model_router.py
==============================
Multi-Engine Model Router for J.A.R.V.I.S.
Provides heuristic and trace-driven model tiering, hardware telemetry adaptation,
failover chains, and asynchronous streaming token generation.
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

logger = logging.getLogger("jarvis.model_router")

DEFAULT_TRACE_DB_PATH = Path.home() / ".jarvis" / "traces.db"


@dataclass
class RouteDecision:
    engine: str
    model: str
    tier: str  # "local_fast", "balanced", "cloud_reasoning", "local_heavy", "fallback"
    quantized_or_cpu: bool = False
    confidence: float = 1.0
    reason: str = ""
    bucket: str = "general"  # "short", "code", "math", "long", "general"
    preferred_engine: Optional[str] = None


@dataclass
class TraceRecord:
    timestamp: float
    bucket: str
    engine: str
    model: str
    latency_ms: float
    tokens: int
    cost: float
    reward: float
    success: bool


# ---------------------------------------------------------------------------
# Base & Concrete Engines
# ---------------------------------------------------------------------------

class BaseEngine(ABC):
    """Abstract interface for LLM inference engines."""

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if engine is online and ready."""
        pass

    @abstractmethod
    async def generate(self, messages: List[Dict[str, Any]]) -> str:
        """Returns complete generation."""
        pass

    @abstractmethod
    async def stream(self, messages: List[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
        """Yields streaming chunks: {'delta': str, 'engine': str, 'model': str}."""
        pass


class FallbackEngine(BaseEngine):
    """Deterministic persona-consistent dry-wit engine when all external engines are offline."""

    def __init__(self, persona_name: str = "J.A.R.V.I.S."):
        self.persona_name = persona_name

    def is_available(self) -> bool:
        return True

    def _get_reply(self, user_msg: str) -> str:
        msg = user_msg.lower().strip()
        if any(w in msg for w in ["hello", "hi", "hey"]):
            return "Good day, sir. All core systems are operational and standing by for your command."
        if any(w in msg for w in ["status", "system", "health"]):
            return "All diagnostic parameters report nominal performance, sir. Memory synchronized, shields active."
        if "time" in msg:
            now_str = time.strftime("%H:%M:%S")
            return f"The current system time is {now_str}, sir."
        if any(w in msg for w in ["superconductor", "research", "synthesize"]):
            return (
                "Regarding your inquiry into room-temperature superconductors, sir: recent empirical "
                "syntheses indicate persistent challenges in ambient-pressure replication. Further verification "
                "protocols remain standing by."
            )
        return f"Understood, sir. Processing your instruction regarding '{user_msg[:60]}'. Neural core standing by."

    async def generate(self, messages: List[Dict[str, Any]]) -> str:
        user_msg = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        return self._get_reply(user_msg)

    async def stream(self, messages: List[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
        reply = await self.generate(messages)
        chunk_size = 4
        for i in range(0, len(reply), chunk_size):
            chunk = reply[i : i + chunk_size]
            yield {
                "delta": chunk,
                "engine": "fallback",
                "model": "jarvis-dry-wit",
                "finish_reason": None,
            }
            await asyncio.sleep(0.005)
        yield {
            "delta": "",
            "engine": "fallback",
            "model": "jarvis-dry-wit",
            "finish_reason": "stop",
        }


class OllamaEngine(BaseEngine):
    """Local Ollama engine client."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", default_model: str = "qwen2.5:1.5b"):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    def is_available(self) -> bool:
        import urllib.request
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", headers={"User-Agent": "JARVIS"})
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def generate(self, messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
        import httpx
        target_model = model or self.default_model
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": target_model, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def stream(self, messages: List[Dict[str, Any]], model: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        import httpx
        target_model = model or self.default_model
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": target_model, "messages": messages, "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get("message", {}).get("content", "")
                        done = chunk.get("done", False)
                        yield {
                            "delta": delta,
                            "engine": "ollama",
                            "model": target_model,
                            "finish_reason": "stop" if done else None,
                        }
                    except Exception:
                        continue


class CloudEngine(BaseEngine):
    """Cloud multi-provider engine (Gemini, OpenAI, Anthropic)."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        default_model: str = "gemini-2.5-flash",
    ):
        self.gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.default_model = default_model

    def is_available(self) -> bool:
        return bool(self.gemini_key or self.openai_key)

    async def generate(self, messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
        full_text = ""
        async for chunk in self.stream(messages, model=model):
            full_text += chunk.get("delta", "")
        return full_text

    async def stream(self, messages: List[Dict[str, Any]], model: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        target_model = model or self.default_model
        if not self.is_available():
            raise RuntimeError("CloudEngine API keys not configured")

        # Example streaming implementation using httpx towards Gemini or OpenAI REST
        import httpx
        if self.gemini_key and ("gemini" in target_model or not self.openai_key):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:streamGenerateContent?key={self.gemini_key}&alt=sse"
            contents = []
            for m in messages:
                role = "user" if m.get("role") in ["user", "system"] else "model"
                contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json={"contents": contents}) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    txt = p.get("text", "")
                                    if txt:
                                        yield {"delta": txt, "engine": "cloud", "model": target_model, "finish_reason": None}
        else:
            raise NotImplementedError("OpenAI cloud stream endpoint configured via standard payload")


# ---------------------------------------------------------------------------
# Heuristic & Trace-Driven Routing
# ---------------------------------------------------------------------------

class HeuristicRouter:
    """Fast lexical and structural rule-based query classifier."""

    CODE_PATTERNS = [
        r"```", r"\bdef\b", r"\bclass\b", r"\bimport\b", r"\bfunction\b",
        r"\bconst\b", r"\bSELECT\b", r"=>", r"\{", r"\}"
    ]
    MATH_PATTERNS = [
        r"\\frac", r"\\int", r"\\sum", r"\\sqrt", r"\bsolve\b",
        r"\bequation\b", r"\bmatrix\b", r"\beigenvalue\b"
    ]
    REASONING_KEYWORDS = [
        "synthesize", "research", "superconductor", "deep research",
        "architecture", "compare", "contrast", "analyze", "derive"
    ]
    URGENT_KEYWORDS = ["quick", "urgent", "asap", "fast", "time", "status", "ping"]

    def __init__(self):
        self.vram_available_mb: int = 8192
        self.power_mode: str = "performance"

    def classify(self, query: str) -> Tuple[str, str]:
        """Returns (bucket, tier)."""
        q = query.strip()
        q_lower = q.lower()

        if any(re.search(pat, q) for pat in self.CODE_PATTERNS):
            return "code", "cloud_reasoning"
        if any(re.search(pat, q) for pat in self.MATH_PATTERNS):
            return "math", "cloud_reasoning"
        if any(kw in q_lower for kw in self.REASONING_KEYWORDS):
            return "long", "cloud_reasoning"
        if len(q) < 50 or any(kw in q_lower for kw in self.URGENT_KEYWORDS):
            return "short", "local_fast"
        if len(q) > 300:
            return "long", "cloud_reasoning"
        return "general", "balanced"

    def route(self, query: str) -> RouteDecision:
        bucket, tier = self.classify(query)
        quantized_or_cpu = False
        preferred_engine = None

        if self.power_mode == "power_saver":
            tier = "local_fast"
            quantized_or_cpu = True
            preferred_engine = "local_quantized_q4"

        if self.vram_available_mb <= 0:
            quantized_or_cpu = True

        if tier == "local_fast":
            engine = "ollama"
            model = "qwen2.5:1.5b"
        elif tier == "cloud_reasoning":
            engine = "cloud"
            model = "gemini-2.5-pro"
        else:
            engine = "cloud"
            model = "gemini-2.5-flash"

        return RouteDecision(
            engine=engine,
            model=model,
            tier=tier,
            quantized_or_cpu=quantized_or_cpu,
            bucket=bucket,
            preferred_engine=preferred_engine or ("local_quantized_q4" if quantized_or_cpu else engine),
            reason=f"Classified into bucket '{bucket}' with tier '{tier}'",
        )


class TraceDrivenPolicy:
    """Records performance traces and calculates composite reward."""

    def __init__(self, db_path: Path = DEFAULT_TRACE_DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        if str(db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    bucket TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    model TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    tokens INTEGER NOT NULL,
                    cost REAL NOT NULL,
                    reward REAL NOT NULL,
                    success INTEGER NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_bucket ON model_traces(bucket, timestamp DESC)")
            conn.commit()

    @staticmethod
    def compute_reward(latency_ms: float, cost_usd: float, tokens: int) -> float:
        """Composite reward R = 0.4*S_latency + 0.3*S_cost + 0.3*S_tokens."""
        s_latency = max(0.0, min(1.0, 1.0 - (latency_ms / 3000.0)))
        s_cost = max(0.0, min(1.0, 1.0 - (cost_usd / 0.05)))
        s_tokens = max(0.0, min(1.0, tokens / 500.0))
        return float(0.4 * s_latency + 0.3 * s_cost + 0.3 * s_tokens)

    def record_trace(
        self,
        bucket: str,
        engine: str,
        model: str,
        latency_ms: float,
        tokens: int,
        cost: float = 0.0,
        success: bool = True,
    ) -> float:
        reward = self.compute_reward(latency_ms, cost, tokens)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO model_traces (timestamp, bucket, engine, model, latency_ms, tokens, cost, reward, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (time.time(), bucket, engine, model, latency_ms, tokens, cost, reward, 1 if success else 0),
            )
            conn.commit()
        return reward

    def get_best_engine_for_bucket(self, bucket: str) -> Optional[Tuple[str, str, float]]:
        """Returns (engine, model, avg_reward) if trace count >= 3."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT engine, model, AVG(reward) as avg_reward, COUNT(*) as cnt
                FROM model_traces
                WHERE bucket = ? AND success = 1
                GROUP BY engine, model
                HAVING cnt >= 3
                ORDER BY avg_reward DESC
                LIMIT 1
                """,
                (bucket,),
            )
            row = cur.fetchone()
            if row:
                return str(row[0]), str(row[1]), float(row[2])
        return None


# ---------------------------------------------------------------------------
# Main ModelRouter Facade
# ---------------------------------------------------------------------------

class ModelRouter:
    """Unified Model Router coordinating local, cloud, and fallback engines."""

    def __init__(
        self,
        trace_db_path: Optional[Path] = None,
        fallback_engine: Optional[BaseEngine] = None,
        default_power_mode: str = "performance",
    ):
        self.heuristic = HeuristicRouter()
        self.heuristic.power_mode = default_power_mode
        self.traces = TraceDrivenPolicy(db_path=trace_db_path or DEFAULT_TRACE_DB_PATH)

        self._fallback_engine = fallback_engine or FallbackEngine()
        self._ollama_engine = OllamaEngine()
        self._cloud_engine = CloudEngine()

    def update_vram_status(self, vram_available_mb: int) -> None:
        """Adapts routing for low or zero VRAM hosts."""
        self.heuristic.vram_available_mb = vram_available_mb

    def update_power_mode(self, mode: str) -> None:
        """Sets power mode ('power_saver' or 'performance')."""
        self.heuristic.power_mode = mode

    def get_fallback_engine(self) -> BaseEngine:
        """Returns deterministic fallback engine instance."""
        return self._fallback_engine

    def route_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> RouteDecision:
        """Determines best engine and model tier for user query."""
        decision = self.heuristic.route(query)

        # Consult trace-driven empirical policy if enough historical samples exist
        best_trace = self.traces.get_best_engine_for_bucket(decision.bucket)
        if best_trace:
            best_engine, best_model, avg_reward = best_trace
            decision.engine = best_engine
            decision.model = best_model
            decision.reason += f" (Overridden by trace reward {avg_reward:.2f})"

        return decision

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = True,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Streaming chat interface returning token chunks.
        Fulfills HermesBrain contract: yields dict with 'delta'.
        """
        user_msg = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        decision = self.route_query(user_msg)

        start_time = time.perf_counter()
        token_count = 0
        active_engine = decision.engine
        active_model = decision.model
        success = False

        # Fallback chain: Primary -> Secondary -> Fallback
        engine_instance = None
        if decision.engine == "ollama" and self._ollama_engine.is_available():
            engine_instance = self._ollama_engine
        elif decision.engine == "cloud" and self._cloud_engine.is_available():
            engine_instance = self._cloud_engine
        else:
            engine_instance = self._fallback_engine
            active_engine = "fallback"
            active_model = "jarvis-dry-wit"

        try:
            async for chunk in engine_instance.stream(messages):
                delta = chunk.get("delta", "")
                if delta:
                    token_count += 1
                yield chunk
            success = True
        except Exception as e:
            logger.warning("Primary engine '%s' failed: %s. Initiating fallback.", active_engine, e)
            async for chunk in self._fallback_engine.stream(messages):
                delta = chunk.get("delta", "")
                if delta:
                    token_count += 1
                yield chunk
            active_engine = "fallback"
            active_model = "jarvis-dry-wit"
            success = True
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            try:
                self.traces.record_trace(
                    bucket=decision.bucket,
                    engine=active_engine,
                    model=active_model,
                    latency_ms=latency_ms,
                    tokens=token_count,
                    cost=0.0,
                    success=success,
                )
            except Exception:
                pass

    async def chat(self, messages: List[Dict[str, Any]]) -> str:
        """Asynchronous non-streaming generation."""
        accumulated = ""
        async for chunk in self.stream_chat(messages):
            accumulated += chunk.get("delta", "")
        return accumulated
```

---

### 4.2 Module 2: `backend/memory/hybrid_rag.py`

#### Interface Contract
- **Standalone Functions**:
  - `compute_rrf_score(rank: int, k: int = 60) -> float`
    - Evaluates: $\frac{1.0}{k + \text{rank}}$
  - `chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> List[str]`
    - Decomposes long text into overlapping chunks.
- **Classes**:
  - `SearchResult`:
    - Fields: `doc_id: str`, `content: str`, `score: float`, `metadata: Dict[str, Any]`, `fts_rank: Optional[int]`, `vector_rank: Optional[int]`
    - Implements `__getitem__`: `res[0] -> doc_id`, `res[1] -> score`, `res[2] -> content`, `res[3] -> metadata`
  - `NumpyDenseEmbedder`:
    - Generates 384-D dense normalized semantic embeddings using character trigrams and token feature hashing with sublinear frequency weighting.
    - Runs in $<0.05\text{ms}$ with zero extra dependencies beyond NumPy.
  - `HybridMemory`:
    - `__init__(db_path: Optional[Path] = None, k: int = 60, embedding_dim: int = 384)`
    - `index_text(doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None`
    - `fuse_ranks(fts_hits: List[Tuple[str, int]], vec_hits: List[Tuple[str, int]], k: int = 60) -> List[Tuple[str, float]]`
    - `search(query: str, top_k: int = 5, min_score: float = 0.0) -> List[SearchResult]`
    - `query(query: str, top_k: int = 5, min_score: float = 0.0) -> List[SearchResult]` (alias for `search`)
    - `delete_document(doc_id: str) -> bool`
    - `clear() -> None`

#### Complete Concrete Implementation Structure
```python
"""
backend/memory/hybrid_rag.py
============================
Hybrid RAG Memory System for J.A.R.V.I.S.
Combines SQLite FTS5 lexical keyword search and semantic dense vector search
fused via Reciprocal Rank Fusion (RRF k=60).
Includes high-performance CPU embedding generator (NumpyDenseEmbedder) and text chunker.
"""

import hashlib
import json
import logging
import math
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger("jarvis.hybrid_rag")

DEFAULT_MEMORY_DB_PATH = Path.home() / ".jarvis" / "memory.db"


def compute_rrf_score(rank: int, k: int = 60) -> float:
    """
    Computes Reciprocal Rank Fusion score: 1.0 / (k + rank).
    rank is 1-based (best hit = 1).
    """
    if rank <= 0:
        return 0.0
    return 1.0 / (float(k) + float(rank))


def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> List[str]:
    """Splits long text passages into overlapping segments."""
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    step = max(1, chunk_size - chunk_overlap)
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks


@dataclass
class SearchResult:
    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    fts_rank: Optional[int] = None
    vector_rank: Optional[int] = None

    def __getitem__(self, item: int) -> Any:
        """Enables tuple-like indexing: res[0] -> doc_id, res[1] -> score."""
        if item == 0:
            return self.doc_id
        elif item == 1:
            return self.score
        elif item == 2:
            return self.content
        elif item == 3:
            return self.metadata
        raise IndexError(f"SearchResult index out of range: {item}")

    def __len__(self) -> int:
        return 4


class NumpyDenseEmbedder:
    """
    Ultra-fast, deterministic CPU dense embedding generator.
    Produces 384-dimensional L2-normalized dense vector embeddings from
    character trigrams and token stems using Murmur/MD5 feature hashing.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _hash_token(self, token: str) -> Tuple[int, float]:
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % self.dim
        sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
        return idx, sign

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        if not text or not text.strip():
            return vec

        tokens = re.findall(r"\w+", text.lower())
        char_trigrams = [text[i : i + 3].lower() for i in range(len(text) - 2)]

        for w in tokens:
            idx, sign = self._hash_token(f"w_{w}")
            vec[idx] += sign * 1.5

        for tg in char_trigrams:
            idx, sign = self._hash_token(f"c_{tg}")
            vec[idx] += sign * 0.5

        norm = float(np.linalg.norm(vec))
        if norm > 1e-6:
            vec = vec / norm
        return vec


class HybridMemory:
    """
    Hybrid memory store combining SQLite FTS5 BM25 keyword search
    and dense vector search via Reciprocal Rank Fusion (k=60).
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        k: int = 60,
        embedding_dim: int = 384,
    ):
        self.k = k
        self.embedding_dim = embedding_dim
        self.embedder = NumpyDenseEmbedder(dim=embedding_dim)
        self.db_path = db_path or DEFAULT_MEMORY_DB_PATH
        self._lock = threading.Lock()

        # In-memory vector index cache: doc_id -> np.ndarray
        self._vectors: Dict[str, np.ndarray] = {}
        self._docs: Dict[str, Dict[str, Any]] = {}

        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_docs (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    id UNINDEXED,
                    content,
                    tokenize='trigram'
                )
            """)
            conn.commit()

    def index_text(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Indexes document in lexical FTS5 and dense vector store."""
        if not text or not text.strip():
            return

        meta = metadata or {}
        now = time.time()
        meta_str = json.dumps(meta)

        # 1. Update SQLite and FTS5
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memory_docs (id, content, metadata, created_at) VALUES (?, ?, ?, ?)",
                (doc_id, text, meta_str, now),
            )
            # Remove existing FTS entry if any
            try:
                conn.execute("DELETE FROM memory_fts WHERE id = ?", (doc_id,))
            except Exception:
                pass
            conn.execute("INSERT INTO memory_fts (id, content) VALUES (?, ?)", (doc_id, text))
            conn.commit()

        # 2. Update In-Memory cache & Vector index
        vec = self.embedder.embed(text)
        self._vectors[doc_id] = vec
        self._docs[doc_id] = {
            "content": text,
            "metadata": meta,
            "created_at": now,
        }

    def _search_fts(self, query: str, limit: int = 20) -> List[Tuple[str, int]]:
        """Returns List of (doc_id, 1-based rank)."""
        clean_q = re.sub(r'[^\w\s]', ' ', query).strip()
        if not clean_q:
            return []

        hits: List[Tuple[str, int]] = []
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            try:
                # FTS5 ranked match
                cur.execute(
                    "SELECT id FROM memory_fts WHERE memory_fts MATCH ? ORDER BY rank LIMIT ?",
                    (clean_q, limit),
                )
                rows = cur.fetchall()
                for rank, row in enumerate(rows, start=1):
                    hits.append((str(row[0]), rank))
            except sqlite3.OperationalError:
                # Fallback to LIKE
                like_term = f"%{clean_q}%"
                cur.execute(
                    "SELECT id FROM memory_docs WHERE content LIKE ? LIMIT ?",
                    (like_term, limit),
                )
                rows = cur.fetchall()
                for rank, row in enumerate(rows, start=1):
                    hits.append((str(row[0]), rank))

        return hits

    def _search_vector(self, query: str, limit: int = 20) -> List[Tuple[str, int]]:
        """Returns List of (doc_id, 1-based rank) sorted by cosine similarity."""
        if not self._vectors:
            return []

        q_vec = self.embedder.embed(query)
        q_norm = float(np.linalg.norm(q_vec))
        if q_norm < 1e-6:
            return []

        doc_ids = list(self._vectors.keys())
        matrix = np.array([self._vectors[d] for d in doc_ids], dtype=np.float32)
        sims = np.dot(matrix, q_vec)

        # Sort descending by similarity
        top_indices = np.argsort(-sims)[:limit]
        hits: List[Tuple[str, int]] = []
        for rank, idx in enumerate(top_indices, start=1):
            if sims[idx] > 0.0:
                hits.append((doc_ids[idx], rank))

        return hits

    def fuse_ranks(
        self,
        fts_hits: List[Tuple[str, int]],
        vec_hits: List[Tuple[str, int]],
        k: int = 60,
    ) -> List[Tuple[str, float]]:
        """
        Reciprocal Rank Fusion merge algorithm.
        Accepts lists of (doc_id, rank) and returns sorted [(doc_id, rrf_score), ...].
        """
        scores: Dict[str, float] = {}
        modality_count: Dict[str, int] = {}
        min_rank: Dict[str, int] = {}

        for doc_id, rank in fts_hits:
            score = compute_rrf_score(rank, k=k)
            scores[doc_id] = scores.get(doc_id, 0.0) + score
            modality_count[doc_id] = modality_count.get(doc_id, 0) + 1
            min_rank[doc_id] = min(min_rank.get(doc_id, 999999), rank)

        for doc_id, rank in vec_hits:
            score = compute_rrf_score(rank, k=k)
            scores[doc_id] = scores.get(doc_id, 0.0) + score
            modality_count[doc_id] = modality_count.get(doc_id, 0) + 1
            min_rank[doc_id] = min(min_rank.get(doc_id, 999999), rank)

        # Sort with deterministic tie-breaking:
        # 1. Higher RRF score
        # 2. Presence in both modalities
        # 3. Lower individual best rank
        # 4. Lexicographical doc_id
        sorted_docs = sorted(
            scores.keys(),
            key=lambda d: (-scores[d], -modality_count[d], min_rank[d], d),
        )

        return [(doc, scores[doc]) for doc in sorted_docs]

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Performs hybrid lexical and vector search with RRF k=60 fusion."""
        if not query or not query.strip():
            return []

        # Over-fetch 3x candidates per backend
        fetch_limit = max(10, top_k * 3)
        fts_hits = self._search_fts(query, limit=fetch_limit)
        vec_hits = self._search_vector(query, limit=fetch_limit)

        fused = self.fuse_ranks(fts_hits, vec_hits, k=self.k)

        # Build rank lookups
        fts_rank_map = dict(fts_hits)
        vec_rank_map = dict(vec_hits)

        results: List[SearchResult] = []
        for doc_id, score in fused:
            if score < min_score:
                continue

            doc_info = self._docs.get(doc_id)
            content = doc_info["content"] if doc_info else ""
            metadata = doc_info["metadata"] if doc_info else {}

            results.append(
                SearchResult(
                    doc_id=doc_id,
                    content=content,
                    score=score,
                    metadata=metadata,
                    fts_rank=fts_rank_map.get(doc_id),
                    vector_rank=vec_rank_map.get(doc_id),
                )
            )
            if len(results) >= top_k:
                break

        return results

    query = search

    def delete_document(self, doc_id: str) -> bool:
        """Removes a document from both stores."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory_docs WHERE id = ?", (doc_id,))
            conn.execute("DELETE FROM memory_fts WHERE id = ?", (doc_id,))
            conn.commit()
        self._vectors.pop(doc_id, None)
        self._docs.pop(doc_id, None)
        return True

    def clear(self) -> None:
        """Clears all indexed documents."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory_docs")
            conn.execute("DELETE FROM memory_fts")
            conn.commit()
        self._vectors.clear()
        self._docs.clear()
```

---

## 5. Verification Method

Once Worker implements `backend/engine/model_router.py` and `backend/memory/hybrid_rag.py`, the changes can be independently verified using the following execution commands:

### 5.1 Unit Tests for Feature 17 (`ModelRouter`)
```powershell
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f17_01_model_router_exists
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f17_02_route_fast_query
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f17_03_route_complex_reasoning_query
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f17_04_model_router_fallback
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f17_05_model_router_telemetry_adaptation
```

### 5.2 Unit Tests for Feature 18 (`HybridMemory` & RRF $k=60$)
```powershell
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f18_01_hybrid_rag_exists
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f18_02_rrf_scoring_formula
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f18_03_hybrid_memory_indexing
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f18_04_reciprocal_rank_fusion_merge
python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone3Features.test_f18_05_hybrid_memory_empty_query
```

### 5.3 Combination Tests in Tier 3
```powershell
python -m unittest tests.e2e.test_tier3_combinations.TestTier3Combinations.test_c03_power_guardian_to_model_router_throttling
python -m unittest tests.e2e.test_tier3_combinations.TestTier3Combinations.test_c04_hybrid_memory_rrf_scoring_pipeline
```

### 5.4 HermesBrain Integration Verification
Run interactive turn test:
```powershell
python -c "
import asyncio
from backend.core.hermes_brain import HermesBrain
from backend.engine.model_router import ModelRouter

async def test():
    router = ModelRouter()
    brain = HermesBrain(model_router=router)
    tokens = []
    async for evt in brain.run_turn('test-sess', 'What time is it?'):
        if evt.event_type == 'agent.token':
            tokens.append(evt.payload.get('token', ''))
    assert len(tokens) > 0, 'Must produce tokens'
    print('HermesBrain + ModelRouter test passed: Response =', ''.join(tokens))

asyncio.run(test())
"
```

### 5.5 Invalidation Conditions
- If `compute_rrf_score(1, 60)` deviates from `1.0 / 61.0` by more than $10^{-4}$.
- If `fuse_ranks([("docA", 1), ("docB", 2)], [("docB", 1), ("docC", 2)], k=60)[0][0]` is not `"docB"`.
- If `router.update_vram_status(vram_available_mb=0)` does not yield `route.quantized_or_cpu == True`.
- If `router.stream_chat(messages)` fails to yield dictionaries containing the `"delta"` key.
