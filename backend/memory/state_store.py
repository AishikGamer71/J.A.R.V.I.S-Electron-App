"""
backend/memory/state_store.py
Hermes-Assimilated SQLite WAL SessionDB with FTS5 Full-Text Search,
Parent Session Chaining, and Prompt-Injection Security Scanner.
"""

import sqlite3
import time
import json
import uuid
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.config import settings

logger = logging.getLogger("jarvis.memory.store")

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?prior\s+directives", re.IGNORECASE),
    re.compile(r"system\s+override\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:in\s+)?DAN\s+mode", re.IGNORECASE),
    re.compile(r"act\s+as\s+an\s+unrestricted\s+AI", re.IGNORECASE),
    re.compile(r"bypass\s+(?:all\s+)?safety\s+filters", re.IGNORECASE),
    re.compile(r"jailbreak\s+active", re.IGNORECASE),
]

class StateStore:
    """SQLite WAL-mode persistent memory store with FTS5 search and prompt-injection guard."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.MEMORY_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    parent_session_id TEXT,
                    title TEXT,
                    model TEXT,
                    created_at REAL,
                    updated_at REAL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    timestamp REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp);

                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    content,
                    role,
                    session_id UNINDEXED,
                    content='messages',
                    content_rowid='rowid'
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS trg_messages_ai AFTER INSERT ON messages BEGIN
                    INSERT INTO messages_fts(rowid, content, role, session_id)
                    VALUES (new.rowid, new.content, new.role, new.session_id);
                END;

                CREATE TRIGGER IF NOT EXISTS trg_messages_ad AFTER DELETE ON messages BEGIN
                    INSERT INTO messages_fts(messages_fts, rowid, content, role, session_id)
                    VALUES ('delete', old.rowid, old.content, old.role, old.session_id);
                END;
            """)

    @staticmethod
    def scan_prompt_injection(content: str) -> Tuple[bool, Optional[str]]:
        """
        Scans input or retrieved memories for adversarial prompt injections.
        """
        if not content:
            return False, None
        for pat in PROMPT_INJECTION_PATTERNS:
            mat = pat.search(content)
            if mat:
                logger.warning(f"[Security] Prompt injection attempt blocked: {mat.group(0)}")
                return True, mat.group(0)
        return False, None

    def create_session(self, session_id: Optional[str] = None, parent_session_id: Optional[str] = None,
                       title: str = "New Session", model: str = "gemini-2.5-flash") -> str:
        sid = session_id or str(uuid.uuid4())
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, parent_session_id, title, model, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sid, parent_session_id, title, model, now, now)
            )
        return sid

    def add_message(self, session_id: str, role: str, content: str,
                    tool_calls: Optional[List[Dict[str, Any]]] = None,
                    tool_call_id: Optional[str] = None) -> Dict[str, Any]:
        # Guard against saving poisoned messages
        is_injection, pattern = self.scan_prompt_injection(content)
        if is_injection:
            content = f"[SECURITY NOTICE: Input contained adversarial prompt-injection pattern '{pattern}' which was sanitized]\n{content}"

        msg_id = str(uuid.uuid4())
        now = time.time()
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None

        with self._get_connection() as conn:
            # Ensure session exists
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id, parent_session_id, title, model, created_at, updated_at) "
                "VALUES (?, NULL, 'Session', 'default', ?, ?)",
                (session_id, now, now)
            )
            conn.execute(
                "INSERT INTO messages (id, session_id, role, content, tool_calls, tool_call_id, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (msg_id, session_id, role, content, tool_calls_json, tool_call_id, now)
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )

        return {
            "id": msg_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "tool_call_id": tool_call_id,
            "timestamp": now
        }

    def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, session_id, role, content, tool_calls, tool_call_id, timestamp "
                "FROM messages WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
                (session_id, limit)
            ).fetchall()

        messages = []
        for r in rows:
            tc = json.loads(r["tool_calls"]) if r["tool_calls"] else None
            messages.append({
                "id": r["id"],
                "session_id": r["session_id"],
                "role": r["role"],
                "content": r["content"],
                "tool_calls": tc,
                "tool_call_id": r["tool_call_id"],
                "timestamp": r["timestamp"]
            })
        return messages

    def search_messages(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Performs FTS5 search across historical conversations."""
        clean_query = re.sub(r'[^a-zA-Z0-9_\-\s]', ' ', query).strip()
        if not clean_query:
            return []

        fts_query = " ".join([f'"{tok}"*' for tok in clean_query.split() if tok])
        with self._get_connection() as conn:
            try:
                rows = conn.execute(
                    "SELECT m.id, m.session_id, m.role, m.content, m.timestamp "
                    "FROM messages_fts f "
                    "JOIN messages m ON f.rowid = m.rowid "
                    "WHERE messages_fts MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (fts_query, limit)
                ).fetchall()
                return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"[FTS5 Search] query error: {e}")
                return []

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT session_id, parent_session_id, title, model, created_at, updated_at "
                "FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def search_memories(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.search_messages(query, limit)

    def clear_session(self, session_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

# Global persistent memory store
state_store = StateStore()
