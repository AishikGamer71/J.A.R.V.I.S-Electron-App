"""
backend/memory/state_db.py
==========================
SQLite WAL State Database (Schema Version 12).
Provides thread-safe persistence for sessions, messages, tool calls, and FTS5 search.
"""

import json
import logging
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("jarvis.state_db")

SCHEMA_VERSION: int = 12

DDL_STATEMENTS = """
-- 1. Schema version tracker
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

-- 2. Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    title TEXT,
    metadata TEXT,
    source TEXT NOT NULL DEFAULT 'electron',
    user_id TEXT,
    model TEXT,
    parent_session_id TEXT,
    message_count INTEGER NOT NULL DEFAULT 0,
    tool_call_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id);

-- 3. Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    tokens INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    tool_call_id TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    metadata TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
CREATE INDEX IF NOT EXISTS idx_messages_session_active ON messages(session_id, active, id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);

-- 4. Tool calls table
CREATE TABLE IF NOT EXISTS tool_calls (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_id INTEGER,
    tool_name TEXT NOT NULL,
    arguments TEXT,
    result TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    duration_ms REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_name ON tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_calls_created_at ON tool_calls(created_at DESC);

-- 5. FTS5 Virtual Tables (External Content Tables referencing messages)
CREATE VIRTUAL TABLE IF NOT EXISTS fts_messages USING fts5(
    content,
    content='messages',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='id'
);

-- 6. FTS5 Synchronization Triggers
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO fts_messages(rowid, content) VALUES (new.id, new.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO fts_messages(fts_messages, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO fts_messages(fts_messages, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO fts_messages(rowid, content) VALUES (new.id, new.content);
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
"""


def _sanitize_fts_query(query: str) -> str:
    """
    Sanitizes arbitrary text input for safe SQLite FTS5 MATCH queries.
    Prevents syntax crashes on colons, operators, hyphens, and unmatched quotes.
    """
    if not query or not query.strip():
        return '""'

    q = query.strip()[:500]

    # Preserve exact quoted phrases by tokenizing
    quoted_phrases: List[str] = []
    def _quote_repl(match):
        quoted_phrases.append(match.group(1).replace('"', ''))
        return f" __QPHRASE_{len(quoted_phrases)-1}__ "

    q = re.sub(r'"([^"]*)"', _quote_repl, q)

    # Strip dangerous FTS5 operators and punctuation
    q = re.sub(r'[\+\-\*\^\{\}\(\)\:\[\]\~\<\>\=]', ' ', q)

    # Remove dangling standalone boolean words
    tokens = q.split()
    clean_tokens: List[str] = []
    for token in tokens:
        upper = token.upper()
        if upper in ("AND", "OR", "NOT", "NEAR"):
            continue
        if token.startswith("__QPHRASE_") and token.endswith("__"):
            idx_str = token[len("__QPHRASE_"):-2]
            try:
                idx = int(idx_str)
                phrase = quoted_phrases[idx].strip()
                if phrase:
                    clean_tokens.append(f'"{phrase}"')
            except (ValueError, IndexError):
                pass
        else:
            # Wrap in double quotes if alphanumeric to match exact token prefix
            cleaned = re.sub(r'[^a-zA-Z0-9_]', '', token)
            if cleaned:
                clean_tokens.append(f'"{cleaned}"*')

    if not clean_tokens:
        return '""'

    return " AND ".join(clean_tokens)


class SessionDB:
    """Thread-safe SQLite state database manager for sessions and conversations."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        if db_path is None:
            self.db_path = Path.home() / ".jarvis" / "state.db"
        else:
            self.db_path = Path(db_path) if isinstance(db_path, str) else db_path

        self._is_memory = str(self.db_path) == ":memory:"
        if not self._is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._shared_memory_conn: Optional[sqlite3.Connection] = None

        if self._is_memory:
            # For :memory:, share a single connection across threads guarded by write_lock
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            self._shared_memory_conn = conn
            self._init_db(conn)
        else:
            # Initialize schema with an initial connection
            conn = self._get_connection()
            self._init_db(conn)

    def _get_connection(self) -> sqlite3.Connection:
        if self._is_memory:
            return self._shared_memory_conn  # type: ignore

        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=True,
            )
            conn.row_factory = sqlite3.Row
            # Configure WAL mode and pragmas
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self, conn: sqlite3.Connection) -> None:
        with self._write_lock:
            cur = conn.cursor()
            cur.executescript(DDL_STATEMENTS)

            # Check or insert schema version
            cur.execute("SELECT version FROM schema_version LIMIT 1")
            row = cur.fetchone()
            if row is None:
                cur.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            else:
                cur.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
            conn.commit()

    def get_schema_version(self) -> int:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version FROM schema_version LIMIT 1")
        row = cur.fetchone()
        return row["version"] if row else 12

    # -----------------------------------------------------------------------
    # Session Management
    # -----------------------------------------------------------------------
    def create_session(
        self,
        title: str = "New Session",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "electron",
        model: Optional[str] = None,
        parent_session_id: Optional[str] = None,
    ) -> str:
        sid = session_id or f"s-{uuid.uuid4().hex[:12]}"
        now = time.time()
        meta_str = json.dumps(metadata or {})

        conn = self._get_connection()
        with self._write_lock:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sessions (
                    id, created_at, updated_at, title, metadata, source, model, parent_session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    title = COALESCE(excluded.title, sessions.title)
                """,
                (sid, now, now, title, meta_str, source, model, parent_session_id),
            )
            conn.commit()
        return sid

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("metadata"):
            try:
                res["metadata"] = json.loads(res["metadata"])
            except Exception:
                pass
        return res

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        results = []
        for row in cur.fetchall():
            d = dict(row)
            if d.get("metadata"):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    pass
            results.append(d)
        return results

    def delete_session(self, session_id: str) -> bool:
        conn = self._get_connection()
        with self._write_lock:
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cur.rowcount > 0

    # -----------------------------------------------------------------------
    # Message Management
    # -----------------------------------------------------------------------
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens: int = 0,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[Any] = None,
        tool_name: Optional[str] = None,
        active: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        now = time.time()
        tc_str = json.dumps(tool_calls) if tool_calls else None
        meta_str = json.dumps(metadata) if metadata else None

        conn = self._get_connection()
        with self._write_lock:
            cur = conn.cursor()
            # Ensure session exists
            cur.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO sessions (id, created_at, updated_at, title) VALUES (?, ?, ?, ?)",
                    (session_id, now, now, (content or "Chat")[:40]),
                )

            cur.execute(
                """
                INSERT INTO messages (
                    session_id, role, content, tokens, created_at,
                    tool_call_id, tool_calls, tool_name, active, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, role, content, tokens, now, tool_call_id, tc_str, tool_name, active, meta_str),
            )
            msg_id = cur.lastrowid

            # Update session message count and updated_at
            cur.execute(
                """
                UPDATE sessions
                SET message_count = message_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (now, session_id),
            )
            conn.commit()
        return msg_id or 0

    append_message = add_message

    def get_messages(
        self,
        session_id: str,
        active_only: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        query = "SELECT * FROM messages WHERE session_id = ?"
        params: List[Any] = [session_id]

        if active_only:
            query += " AND active = 1"

        query += " ORDER BY id ASC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cur.execute(query, params)
        messages = []
        for row in cur.fetchall():
            d = dict(row)
            if d.get("tool_calls"):
                try:
                    d["tool_calls"] = json.loads(d["tool_calls"])
                except Exception:
                    pass
            if d.get("metadata"):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    pass
            messages.append(d)
        return messages

    def soft_compact_messages(self, session_id: str, message_ids: List[int]) -> int:
        """Sets active = 0 for compacted middle messages."""
        if not message_ids:
            return 0
        conn = self._get_connection()
        with self._write_lock:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in message_ids)
            cur.execute(
                f"UPDATE messages SET active = 0 WHERE session_id = ? AND id IN ({placeholders})",
                [session_id] + message_ids,
            )
            conn.commit()
            return cur.rowcount

    # -----------------------------------------------------------------------
    # Tool Calls Tracking
    # -----------------------------------------------------------------------
    def record_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        status: str = "success",
        duration_ms: float = 0.0,
        message_id: Optional[int] = None,
        tool_call_id: Optional[str] = None,
    ) -> str:
        tcid = tool_call_id or f"tc-{uuid.uuid4().hex[:10]}"
        now = time.time()
        args_str = json.dumps(arguments, default=str)
        res_str = result if isinstance(result, str) else json.dumps(result, default=str)

        conn = self._get_connection()
        with self._write_lock:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO tool_calls (
                    id, session_id, message_id, tool_name, arguments, result, status, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tcid, session_id, message_id, tool_name, args_str, res_str, status, duration_ms, now),
            )
            cur.execute(
                "UPDATE sessions SET tool_call_count = tool_call_count + 1, updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            conn.commit()
        return tcid

    # -----------------------------------------------------------------------
    # FTS5 Full-Text Search
    # -----------------------------------------------------------------------
    def search_fts(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Executes full-text search against fts_messages.
        Gracefully handles syntax errors and falls back to LIKE search if needed.
        """
        if not query or not query.strip():
            return []

        conn = self._get_connection()
        cur = conn.cursor()

        sanitized = _sanitize_fts_query(query)
        try:
            if sanitized and sanitized != '""':
                sql = """
                    SELECT m.id, m.session_id, m.role, m.content, m.created_at
                    FROM fts_messages f
                    JOIN messages m ON f.rowid = m.id
                    WHERE fts_messages MATCH ?
                """
                params: List[Any] = [sanitized]
                if session_id:
                    sql += " AND m.session_id = ?"
                    params.append(session_id)
                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)

                cur.execute(sql, params)
                rows = cur.fetchall()
                if rows:
                    return [dict(r) for r in rows]
        except sqlite3.OperationalError as e:
            logger.debug("FTS5 match failed, falling back to LIKE: %s", e)

        # Fallback to standard SQL LIKE search
        like_term = f"%{query.strip()}%"
        fallback_sql = """
            SELECT id, session_id, role, content, created_at
            FROM messages
            WHERE content LIKE ?
        """
        params = [like_term]
        if session_id:
            fallback_sql += " AND session_id = ?"
            params.append(session_id)
        fallback_sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        cur.execute(fallback_sql, params)
        return [dict(r) for r in cur.fetchall()]

    search_messages = search_fts

    def close(self) -> None:
        """Closes thread-local or shared connections."""
        if self._is_memory and self._shared_memory_conn:
            try:
                self._shared_memory_conn.close()
            except Exception:
                pass
            self._shared_memory_conn = None
        elif hasattr(self._local, "conn") and self._local.conn:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None
