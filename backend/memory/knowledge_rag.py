"""
backend/memory/knowledge_rag.py
OpenJarvis-Assimilated Hybrid FTS5 + BM25 Reciprocal Rank Fusion (RRF)
Local File & Knowledge Document Indexer.
"""

import sqlite3
import time
import math
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
from backend.config import settings

logger = logging.getLogger("jarvis.memory.rag")

class KnowledgeRAG:
    """Hybrid SQLite/FTS5 document store with Reciprocal Rank Fusion retrieval."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(settings.MEMORY_DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    updated_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_doc_source ON documents(source_path);

                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    content,
                    source_path UNINDEXED,
                    content='documents',
                    content_rowid='id'
                );

                CREATE TRIGGER IF NOT EXISTS trg_docs_ai AFTER INSERT ON documents BEGIN
                    INSERT INTO documents_fts(rowid, content, source_path)
                    VALUES (new.id, new.content, new.source_path);
                END;

                CREATE TRIGGER IF NOT EXISTS trg_docs_ad AFTER DELETE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, content, source_path)
                    VALUES ('delete', old.id, old.content, old.source_path);
                END;
            """)

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        words = text.split()
        if len(words) <= chunk_size:
            return [text]
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i : i + chunk_size])
            chunks.append(chunk)
            i += (chunk_size - overlap)
        return chunks

    def index_document(self, source_path: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Chunks and indexes text content with automatic FTS update."""
        meta_str = json_str = "" if not metadata else str(metadata)
        chunks = self.chunk_text(content)
        now = time.time()

        with self._get_connection() as conn:
            # Delete old chunks for this file
            conn.execute("DELETE FROM documents WHERE source_path = ?", (source_path,))
            for idx, ch in enumerate(chunks):
                conn.execute(
                    "INSERT INTO documents (source_path, chunk_index, content, metadata, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (source_path, idx, ch, meta_str, now)
                )

        logger.info(f"[KnowledgeRAG] Indexed {len(chunks)} chunks for {source_path}")
        return len(chunks)

    def retrieve_context(self, query: str, top_k: int = 5, rrf_k: int = 60) -> List[Dict[str, Any]]:
        """
        Executes hybrid FTS5 query combined with BM25 Reciprocal Rank Fusion.
        """
        clean_query = re.sub(r'[^a-zA-Z0-9_\-\s]', ' ', query).strip()
        if not clean_query:
            return []

        fts_query = " ".join([f'"{tok}"*' for tok in clean_query.split() if tok])
        query_terms = [t.lower() for t in clean_query.split() if len(t) > 2]

        with self._get_connection() as conn:
            # 1. FTS rank
            try:
                fts_rows = conn.execute(
                    "SELECT d.id, d.source_path, d.chunk_index, d.content "
                    "FROM documents_fts f "
                    "JOIN documents d ON f.rowid = d.id "
                    "WHERE documents_fts MATCH ? "
                    "ORDER BY rank LIMIT 25",
                    (fts_query,)
                ).fetchall()
            except Exception:
                fts_rows = []

            # 2. Term overlap (simple BM25 proxy)
            all_rows = conn.execute("SELECT id, source_path, chunk_index, content FROM documents LIMIT 200").fetchall()

        scores = defaultdict(float)
        item_map = {}

        # FTS5 ranking component
        for rank, r in enumerate(fts_rows):
            doc_id = r["id"]
            scores[doc_id] += 1.0 / (rrf_k + rank + 1)
            item_map[doc_id] = dict(r)

        # Keyword frequency component
        term_scores = []
        for r in all_rows:
            doc_id = r["id"]
            cnt = sum(r["content"].lower().count(term) for term in query_terms)
            if cnt > 0:
                term_scores.append((cnt, doc_id, dict(r)))

        term_scores.sort(key=lambda x: x[0], reverse=True)
        for rank, (_, doc_id, r_dict) in enumerate(term_scores[:25]):
            scores[doc_id] += 1.0 / (rrf_k + rank + 1)
            if doc_id not in item_map:
                item_map[doc_id] = r_dict

        sorted_ids = sorted(scores.keys(), key=lambda did: scores[did], reverse=True)
        results = []
        for did in sorted_ids[:top_k]:
            item = item_map[did]
            item["rrf_score"] = round(scores[did], 4)
            results.append(item)

        return results

knowledge_rag = KnowledgeRAG()
