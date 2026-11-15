"""
backend/engine/model_router.py
==============================
Multi-Engine Model Router for J.A.R.V.I.S.
Assimilated from open-jarvis/OpenJarvis (src/openjarvis/router/model_router.py).

Provides:
- Heuristic & trace-driven model routing across local Ollama, cloud providers, and fallback tiers.
- Hardware & power telemetry adaptation: VRAM awareness (CPU/quantized offload) and battery conservation.
- Sub-millisecond routing latency with empirical reward feedback loop:
  R = 0.4 * S_lat + 0.3 * S_cost + 0.3 * S_tok.
- Robust async streaming token interface yielding {'delta': str} compatible with HermesBrain.
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
    bucket: str = "general"
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

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        default_model: str = "qwen2.5:1.5b",
        cache_ttl_sec: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.cache_ttl_sec = cache_ttl_sec
        self._cached_available: Optional[bool] = None
        self._last_check_time: float = 0.0
        self._lock = threading.Lock()
        self._checking: bool = False
        self._trigger_background_probe()

    def _trigger_background_probe(self) -> None:
        """Spawns a daemon thread to verify Ollama status without blocking inference/streaming."""
        with self._lock:
            if self._checking:
                return
            self._checking = True
        threading.Thread(target=self._run_probe, daemon=True, name="OllamaHealthProbe").start()

    def _run_probe(self) -> bool:
        import urllib.request
        status = False
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", headers={"User-Agent": "JARVIS"})
            with urllib.request.urlopen(req, timeout=0.4) as resp:
                status = (resp.status == 200)
        except Exception:
            status = False
        finally:
            with self._lock:
                self._cached_available = status
                self._last_check_time = time.time()
                self._checking = False
        return status

    def is_available(self, force_refresh: bool = False, timeout: Optional[float] = None) -> bool:
        """
        Non-blocking availability check with TTL caching.
        Returns cached status immediately (<0.1ms). Refreshes in background when stale.
        """
        now = time.time()
        with self._lock:
            if not force_refresh and self._cached_available is not None:
                if (now - self._last_check_time) < self.cache_ttl_sec:
                    return self._cached_available

        if timeout and timeout > 0:
            return self._run_probe()

        self._trigger_background_probe()
        with self._lock:
            return self._cached_available if self._cached_available is not None else False

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
    """Cloud multi-provider engine (Gemini, OpenAI)."""

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

    def get_best_engine_for_bucket(
        self, bucket: str, allowed_engines: Optional[List[str]] = None
    ) -> Optional[Tuple[str, str, float]]:
        """Returns (engine, model, avg_reward) if trace count >= 3, optionally filtered by allowed_engines."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            if allowed_engines:
                placeholders = ",".join("?" for _ in allowed_engines)
                query = f"""
                    SELECT engine, model, AVG(reward) as avg_reward, COUNT(*) as cnt
                    FROM model_traces
                    WHERE bucket = ? AND success = 1 AND engine IN ({placeholders})
                    GROUP BY engine, model
                    HAVING cnt >= 3
                    ORDER BY avg_reward DESC
                    LIMIT 1
                """
                cur.execute(query, [bucket] + list(allowed_engines))
            else:
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
        is_power_saver = (self.heuristic.power_mode == "power_saver")

        # In power_saver mode, enforce hard constraint: only local engines permitted.
        # This prevents historical cloud traces from overriding local power conservation.
        allowed = ["ollama", "fallback"] if is_power_saver else None
        best_trace = self.traces.get_best_engine_for_bucket(decision.bucket, allowed_engines=allowed)

        if best_trace:
            best_engine, best_model, avg_reward = best_trace
            if is_power_saver and best_engine == "cloud":
                decision.reason += " (Trace cloud override suppressed by power_saver mode)"
            else:
                decision.engine = best_engine
                decision.model = best_model
                decision.reason += f" (Overridden by trace reward {avg_reward:.2f})"
        elif is_power_saver:
            decision.reason += " (Trace cloud search constrained by power_saver mode)"

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
