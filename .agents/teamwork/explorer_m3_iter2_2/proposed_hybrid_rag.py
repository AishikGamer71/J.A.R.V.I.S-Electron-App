"""
backend/memory/hybrid_rag.py
============================
Hybrid RAG Memory System for J.A.R.V.I.S.
Assimilated from open-jarvis/OpenJarvis (src/openjarvis/rag/hybrid_rag.py).

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
from contextlib import contextmanager
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
    Guarded against non-positive ranks and zero/negative denominators.
    """
    if rank <= 0 or (k + rank) <= 0:
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

    def __getitem__(self, item: Union[int, slice]) -> Any:
        """
        Enables tuple-like indexing and sequence unpacking:
        res[0] / res[-4] -> doc_id
        res[1] / res[-3] -> score
        res[2] / res[-2] -> content
        res[3] / res[-1] -> metadata
        """
        fields = (self.doc_id, self.score, self.content, self.metadata)
        try:
            return fields[item]
        except (IndexError, TypeError) as exc:
            raise IndexError(f"SearchResult index out of range: {item}") from exc

    def __len__(self) -> int:
        return 4

    def __iter__(self):
        """Allows direct sequence unpacking: d, s, c, m = res."""
        return iter((self.doc_id, self.score, self.content, self.metadata))


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
    Hybrid memory store combining SQLite FTS5 keyword search
    and dense vector search via Reciprocal Rank Fusion (k=60).
    """

    def __init__(
        self,
        db_path: Optional[Union[Path, str]] = None,
        k: int = 60,
        embedding_dim: int = 384,
    ):
        self.k = k
        self.embedding_dim = embedding_dim
        self.embedder = NumpyDenseEmbedder(dim=embedding_dim)

        if not db_path:
            self.db_path = DEFAULT_MEMORY_DB_PATH
        elif isinstance(db_path, str):
            self.db_path = Path(db_path)
        else:
            self.db_path = db_path

        self._lock = threading.Lock()
        self._is_memory = str(self.db_path) == ":memory:"
        self._shared_conn: Optional[sqlite3.Connection] = None

        # In-memory vector index cache: doc_id -> np.ndarray
        self._vectors: Dict[str, np.ndarray] = {}
        self._docs: Dict[str, Dict[str, Any]] = {}

        if not self._is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _db_connection(self):
        """
        Thread-safe context manager managing SQLite transaction lifecycle
        and guaranteeing immediate, explicit connection closing on Windows.
        """
        with self._lock:
            if self._is_memory:
                if self._shared_conn is None:
                    self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
                with self._shared_conn:
                    yield self._shared_conn
            else:
                conn = sqlite3.connect(str(self.db_path))
                try:
                    with conn:
                        yield conn
                finally:
                    conn.close()

    def _init_db(self):
        with self._db_connection() as conn:
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
        with self._db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memory_docs (id, content, metadata, created_at) VALUES (?, ?, ?, ?)",
                (doc_id, text, meta_str, now),
            )
            try:
                conn.execute("DELETE FROM memory_fts WHERE id = ?", (doc_id,))
            except Exception:
                pass
            conn.execute("INSERT INTO memory_fts (id, content) VALUES (?, ?)", (doc_id, text))

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
        with self._db_connection() as conn:
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
        with self._db_connection() as conn:
            conn.execute("DELETE FROM memory_docs WHERE id = ?", (doc_id,))
            conn.execute("DELETE FROM memory_fts WHERE id = ?", (doc_id,))
        self._vectors.pop(doc_id, None)
        self._docs.pop(doc_id, None)
        return True

    def clear(self) -> None:
        """Clears all indexed documents."""
        with self._db_connection() as conn:
            conn.execute("DELETE FROM memory_docs")
            conn.execute("DELETE FROM memory_fts")
        self._vectors.clear()
        self._docs.clear()

    def close(self) -> None:
        """Explicitly closes any persistent shared in-memory connection."""
        with self._lock:
            if self._shared_conn is not None:
                try:
                    self._shared_conn.close()
                except Exception:
                    pass
                self._shared_conn = None
