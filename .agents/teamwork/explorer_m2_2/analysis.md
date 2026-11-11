# Technical Analysis & Blueprint: SessionDB & SQLite WAL Schema 12

**Author**: `explorer_m2_2`  
**Milestone**: Milestone 2 (State Store & SQLite WAL Schema 12)  
**Target Module**: `backend/memory/state_db.py`  
**Database Path**: `~/.jarvis/state.db`  
**Schema Version**: 12  

---

## 1. Executive Summary

This document provides the complete architectural specification, schema definition (DDL), concurrency/thread-safety strategy, and drop-in code blueprint for `SessionDB` in `backend/memory/state_db.py`.

`SessionDB` serves as the primary conversational and agentic state store for the unified J.A.R.V.I.S. Desktop System. It assimilates the proven SQLite state engine from `NousResearch/hermes-agent` while meeting the exact requirements of `PROJECT.md`, `ORIGINAL_REQUEST.md`, and the execution directive.

Key capabilities:
1. **SQLite WAL (Write-Ahead Logging)** mode with `PRAGMA synchronous=NORMAL; foreign_keys=ON; busy_timeout=30000;`.
2. **Schema Version 12** containing 5 core tables: `schema_version`, `sessions`, `messages`, `tool_calls`, and FTS5 virtual table `fts_messages`.
3. **Automated FTS5 Synchronization** via three SQLite triggers: `messages_ai` (AFTER INSERT), `messages_ad` (AFTER DELETE), and `messages_au` (AFTER UPDATE).
4. **Thread-Safe Multi-Worker Access** combining connection-per-thread (`threading.local`) for non-blocking concurrent readers with an intra-process write lock (`threading.Lock`) and SQLite 30s busy timeout for writers.
5. **Complete API Contract**: Full support for `create_session`, `get_session`, `list_sessions`, `delete_session`, `add_message` (and alias `append_message`), `get_messages`, `search_fts` (and alias `search_messages`), and `record_tool_call`.
6. **Input Sanitization**: Resilient FTS5 query parser adapted from `hermes_state.py` to prevent SQL injection or FTS5 syntax crashes on arbitrary characters (colons, hyphens, unclosed quotes, boolean operators).

---

## 2. Requirements & Interface Mapping

| Requirement | Interface / DDL Item | Implementation Detail |
|---|---|---|
| **WAL Storage** | `~/.jarvis/state.db` | Auto-creates `~/.jarvis/`, sets `journal_mode=WAL`, `synchronous=NORMAL` |
| **Schema Ver 12** | `schema_version` table | Single-column table tracking `version = 12` |
| **Session Model** | `sessions` table | `id`, `created_at`, `updated_at`, `title`, `metadata`, `message_count`, `tool_call_count` |
| **Message Model** | `messages` table | `id`, `session_id`, `role`, `content`, `tokens`, `created_at`, `tool_call_id`, `tool_calls`, `tool_name`, `active` |
| **Tool Call Model**| `tool_calls` table | `id`, `session_id`, `message_id`, `tool_name`, `arguments`, `result`, `status`, `duration_ms`, `created_at` |
| **Full-Text Search**| `fts_messages` | SQLite FTS5 external content virtual table referencing `messages(id)` |
| **FTS Triggers** | `messages_ai`, `messages_ad`, `messages_au` | Live synchronization on INSERT, DELETE, UPDATE |
| **Thread Safety** | `threading.local` + `Lock` | Connection-per-thread for concurrent reads; write-lock for atomic writes |
| **REST Endpoints** | `GET /sessions`, `GET /api/sessions`, `GET /sessions/{id}/messages`, `DELETE /sessions/{id}`, `GET /api/history`, `POST /api/history/clear`, `GET /search` | Direct 1:1 mapping to `SessionDB` methods |

---

## 3. SQLite WAL Schema Version 12 (DDL)

```sql
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

-- 5. FTS5 Virtual Table (External Content Table referencing messages)
CREATE VIRTUAL TABLE IF NOT EXISTS fts_messages USING fts5(
    content,
    content='messages',
    content_rowid='id'
);

-- Compatibility FTS5 table alias for Hermes agent references
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='id'
);

-- 6. FTS5 Synchronization Triggers
-- After Insert Trigger
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO fts_messages(rowid, content) VALUES (new.id, new.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;

-- After Delete Trigger
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO fts_messages(fts_messages, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

-- After Update Trigger
CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO fts_messages(fts_messages, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO fts_messages(rowid, content) VALUES (new.id, new.content);
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
```

---

## 4. Concurrency & Thread-Safety Design

### 4.1 WAL Mode Mechanics
In standard SQLite rollback-journal mode, any write transaction locks the entire database file from readers. Under high-frequency telemetry polling (`GET /api/system/stats`), streaming LLM token generation, tool dispatching, and WebSocket broadcast turns, this causes `sqlite3.OperationalError: database is locked` errors.

By enforcing WAL (Write-Ahead Logging):
1. **Readers never block writers**: Multiple threads can read concurrently from committed database states without taking shared locks on the main DB file.
2. **Writers never block readers**: Background threads writing messages or tool calls append to `-wal` without stopping UI requests.
3. **Checkpoints**: WAL frames are checkpointed periodically back to the main DB (`PRAGMA wal_checkpoint(PASSIVE)` every 50–100 writes).

### 4.2 Connection-per-Thread via `threading.local`
Python's `sqlite3` module raises `ProgrammingError: SQLite objects created in a thread can only be used in that same thread` if a single connection is accessed across threads. 

Instead of a heavy third-party connection pool dependency, `SessionDB` manages connections via `threading.local()`:
- Each OS or worker thread (FastAPI thread pool workers, Hermes brain loop, cron scheduler, audio pipeline) lazily creates its own `sqlite3.Connection`.
- Every new connection executes:
  - `PRAGMA journal_mode=WAL;`
  - `PRAGMA synchronous=NORMAL;`
  - `PRAGMA foreign_keys=ON;`
  - `PRAGMA busy_timeout=30000;` (30 seconds)
- `row_factory = sqlite3.Row` is configured for dictionary-like column access.

### 4.3 Intra-Process Write Mutex
While SQLite WAL supports concurrent readers, SQLite allows only **one writer at a time**. If two threads initiate `INSERT`/`UPDATE` at the exact same microsecond, SQLite's internal busy handler sleeps. To prevent lock convoy effects and avoid contention overhead, `SessionDB` wraps all mutating methods in a Python `threading.Lock` (`self._write_lock`).

---

## 5. FTS5 Query Sanitization Algorithm

FTS5 syntax treats characters such as `"`, `:`, `(`, `)`, `+`, `*`, `^`, `{`, `}` and standalone boolean words (`AND`, `OR`, `NOT`) as query operators. If a user enters text like `C:\Users\path`, `def test():`, or `TODO: fix`, a raw `MATCH ?` throws `sqlite3.OperationalError: syntax error`.

`SessionDB` integrates the proven 6-step sanitization routine from `hermes_state.py`:
1. **Length Bounding**: Clip raw queries to 500 characters to prevent regex denial of service.
2. **Quoted Phrase Preservation**: Extract balanced quotes (`"exact phrase"`) and replace them with unique placeholders (`\x00Q0\x00`).
3. **Special Character Stripping**: Replace unquoted `+{}():"^` with whitespace.
4. **Wildcard & Boolean Clean-up**: Collapse multiple `***` wildcards, remove leading wildcards, and strip dangling `AND`, `OR`, `NOT` tokens.
5. **Dotted/Hyphenated Phrase Quoting**: Wrap unquoted patterns like `foo-bar` or `state.db` in quotes so FTS5 doesn't split on hyphens/dots.
6. **Placeholder Restoration**: Restore preserved quoted phrases.
7. **Graceful Fallback**: If sanitized FTS MATCH query fails or is empty, execute standard SQL `WHERE content LIKE ?` to ensure 100% search uptime.

---

## 6. Complete Python Implementation Blueprint

Here is the exact code blueprint for `backend/memory/state_db.py`:

```python
"""
backend/memory/state_db.py
==========================
SQLite WAL State Database (Schema Version 12).
Provides thread-safe persistence for sessions, messages, tool calls, and FTS5 search.

Conforms to J.A.R.V.I.S. Architecture Specification:
- DB Path: ~/.jarvis/state.db
- WAL Mode: PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
- Schema Version: 12
- Thread-safe connection-per-thread + write lock
"""

import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("jarvis.state_db")

SCHEMA_VERSION = 12
DEFAULT_DB_PATH = Path.home() / ".jarvis" / "state.db"
MAX_FTS5_QUERY_CHARS = 500


class SessionDB:
    """
    SQLite-backed state store with WAL mode and FTS5 search.
    Thread-safe connection-per-thread architecture for concurrent FastAPI workers.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        else:
            self.db_path = Path(db_path).expanduser().resolve()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._write_counter = 0

        # Initialize schema on startup
        self._init_schema()

    # --------------------------------------------------------------------------
    # Connection Management (Thread-Local)
    # --------------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection configured with WAL and foreign keys."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode for explicit transaction control
            )
            conn.row_factory = sqlite3.Row
            # Enable WAL mode, fast sync, and foreign key cascades
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA busy_timeout=30000;")
            self._local.conn = conn
        return conn

    def close(self) -> None:
        """Closes the thread-local connection if open."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    # --------------------------------------------------------------------------
    # Schema Initialization & Migrations
    # --------------------------------------------------------------------------

    def _init_schema(self) -> None:
        """Creates Schema Version 12 tables, indexes, virtual tables, and triggers."""
        with self._write_lock:
            conn = self._get_connection()
            with conn:
                # 1. Schema version table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER NOT NULL
                    );
                """)

                # 2. Sessions table
                conn.execute("""
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
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);")

                # 3. Messages table
                conn.execute("""
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
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_active ON messages(session_id, active, id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);")

                # 4. Tool calls table
                conn.execute("""
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
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id, created_at DESC);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_name ON tool_calls(tool_name);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_created_at ON tool_calls(created_at DESC);")

                # 5. FTS5 Virtual Tables (fts_messages and compatibility messages_fts)
                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS fts_messages USING fts5(
                            content,
                            content='messages',
                            content_rowid='id'
                        );
                    """)
                    conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                            content,
                            content='messages',
                            content_rowid='id'
                        );
                    """)

                    # 6. Triggers keeping FTS in sync
                    conn.execute("""
                        CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                            INSERT INTO fts_messages(rowid, content) VALUES (new.id, new.content);
                            INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
                        END;
                    """)
                    conn.execute("""
                        CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                            INSERT INTO fts_messages(fts_messages, rowid, content) VALUES('delete', old.id, old.content);
                            INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
                        END;
                    """)
                    conn.execute("""
                        CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                            INSERT INTO fts_messages(fts_messages, rowid, content) VALUES('delete', old.id, old.content);
                            INSERT INTO fts_messages(rowid, content) VALUES (new.id, new.content);
                            INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
                            INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
                        END;
                    """)
                except sqlite3.OperationalError as e:
                    logger.warning(f"FTS5 setup notification: {e}")

                # 7. Check or record schema version 12
                cursor = conn.execute("SELECT version FROM schema_version LIMIT 1;")
                row = cursor.fetchone()
                if row is None:
                    conn.execute("INSERT INTO schema_version (version) VALUES (?);", (SCHEMA_VERSION,))
                elif row["version"] != SCHEMA_VERSION:
                    conn.execute("UPDATE schema_version SET version = ?;", (SCHEMA_VERSION,))

    def _maybe_checkpoint(self) -> None:
        """Periodically checkpoints the WAL file to keep disk size bounded."""
        self._write_counter += 1
        if self._write_counter % 100 == 0:
            try:
                conn = self._get_connection()
                conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            except Exception:
                pass

    # --------------------------------------------------------------------------
    # Sessions API
    # --------------------------------------------------------------------------

    def create_session(
        self,
        title: str = "New Session",
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        source: str = "electron",
        parent_session_id: Optional[str] = None,
    ) -> str:
        """Creates a new session and returns its ID."""
        sid = session_id or f"session_{uuid.uuid4().hex[:12]}"
        now = time.time()
        meta_json = json.dumps(metadata or {})

        with self._write_lock:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        id, created_at, updated_at, title, metadata, source, model, parent_session_id,
                        message_count, tool_call_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0);
                    """,
                    (sid, now, now, title, meta_json, source, model, parent_session_id),
                )
            self._maybe_checkpoint()
        return sid

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves session metadata by ID, returning None if not found."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM sessions WHERE id = ?;", (session_id,))
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        if data.get("metadata"):
            try:
                data["metadata"] = json.loads(data["metadata"])
            except Exception:
                pass
        return data

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Lists sessions ordered by updated_at descending."""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?;",
            (limit, offset),
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            if item.get("metadata"):
                try:
                    item["metadata"] = json.loads(item["metadata"])
                except Exception:
                    pass
            results.append(item)
        return results

    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Updates session title or metadata."""
        fields = []
        params = []
        now = time.time()

        if title is not None:
            fields.append("title = ?")
            params.append(title)
        if metadata is not None:
            fields.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not fields:
            return False

        fields.append("updated_at = ?")
        params.append(now)
        params.append(session_id)

        query = f"UPDATE sessions SET {', '.join(fields)} WHERE id = ?;"

        with self._write_lock:
            conn = self._get_connection()
            with conn:
                cursor = conn.execute(query, tuple(params))
                updated = cursor.rowcount > 0
            self._maybe_checkpoint()
        return updated

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session and cascades deletion to messages and tool calls."""
        with self._write_lock:
            conn = self._get_connection()
            with conn:
                cursor = conn.execute("DELETE FROM sessions WHERE id = ?;", (session_id,))
                deleted = cursor.rowcount > 0
            self._maybe_checkpoint()
        return deleted

    # --------------------------------------------------------------------------
    # Messages API
    # --------------------------------------------------------------------------

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens: int = 0,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[Any] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Appends a message to a session. Auto-creates session if it doesn't exist.
        Returns the new message ID as string.
        """
        now = time.time()
        tool_calls_str = json.dumps(tool_calls) if tool_calls is not None else None
        meta_str = json.dumps(metadata) if metadata is not None else None

        with self._write_lock:
            conn = self._get_connection()
            with conn:
                # Ensure session exists
                sess = conn.execute("SELECT id FROM sessions WHERE id = ?;", (session_id,)).fetchone()
                if not sess:
                    conn.execute(
                        """
                        INSERT INTO sessions (id, created_at, updated_at, title, message_count, tool_call_count)
                        VALUES (?, ?, ?, 'Auto Session', 0, 0);
                        """,
                        (session_id, now, now),
                    )

                cursor = conn.execute(
                    """
                    INSERT INTO messages (
                        session_id, role, content, tokens, created_at, tool_call_id,
                        tool_calls, tool_name, active, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?);
                    """,
                    (session_id, role, content, tokens, now, tool_call_id, tool_calls_str, tool_name, meta_str),
                )
                msg_id = cursor.lastrowid

                # Update session metadata
                conn.execute(
                    """
                    UPDATE sessions
                    SET updated_at = ?, message_count = message_count + 1
                    WHERE id = ?;
                    """,
                    (now, session_id),
                )
            self._maybe_checkpoint()

        return str(msg_id)

    def append_message(self, *args, **kwargs) -> str:
        """Hermes compatibility alias for add_message."""
        return self.add_message(*args, **kwargs)

    def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves messages for a session in chronological order.
        When limit is applied, returns the latest `limit` messages.
        """
        conn = self._get_connection()
        active_clause = "AND active = 1" if active_only else ""

        # Subquery fetches the latest N rows, outer query sorts them chronologically
        query = f"""
            SELECT * FROM (
                SELECT * FROM messages
                WHERE session_id = ? {active_clause}
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC;
        """
        cursor = conn.execute(query, (session_id, limit))
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            if item.get("tool_calls"):
                try:
                    item["tool_calls"] = json.loads(item["tool_calls"])
                except Exception:
                    pass
            if item.get("metadata"):
                try:
                    item["metadata"] = json.loads(item["metadata"])
                except Exception:
                    pass
            results.append(item)
        return results

    def clear_messages(self, session_id: str) -> bool:
        """Deletes all messages for a session and resets message_count."""
        with self._write_lock:
            conn = self._get_connection()
            now = time.time()
            with conn:
                conn.execute("DELETE FROM messages WHERE session_id = ?;", (session_id,))
                conn.execute(
                    "UPDATE sessions SET message_count = 0, updated_at = ? WHERE id = ?;",
                    (now, session_id),
                )
            self._maybe_checkpoint()
        return True

    # --------------------------------------------------------------------------
    # Tool Calls API
    # --------------------------------------------------------------------------

    def record_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: Union[str, Dict[str, Any]],
        result: Any = None,
        status: str = "success",
        duration_ms: float = 0.0,
        message_id: Optional[int] = None,
    ) -> str:
        """
        Records a tool execution invocation in the database.
        Returns the generated tool call ID.
        """
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        now = time.time()
        args_str = arguments if isinstance(arguments, str) else json.dumps(arguments or {})
        res_str = result if isinstance(result, str) else json.dumps(result or {})

        with self._write_lock:
            conn = self._get_connection()
            with conn:
                # Ensure session exists
                sess = conn.execute("SELECT id FROM sessions WHERE id = ?;", (session_id,)).fetchone()
                if not sess:
                    conn.execute(
                        """
                        INSERT INTO sessions (id, created_at, updated_at, title, message_count, tool_call_count)
                        VALUES (?, ?, ?, 'Auto Session', 0, 0);
                        """,
                        (session_id, now, now),
                    )

                conn.execute(
                    """
                    INSERT INTO tool_calls (
                        id, session_id, message_id, tool_name, arguments, result, status,
                        duration_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (call_id, session_id, message_id, tool_name, args_str, res_str, status, duration_ms, now),
                )

                conn.execute(
                    """
                    UPDATE sessions
                    SET updated_at = ?, tool_call_count = tool_call_count + 1
                    WHERE id = ?;
                    """,
                    (now, session_id),
                )
            self._maybe_checkpoint()

        return call_id

    def get_tool_calls(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieves tool execution records for a session."""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY created_at DESC LIMIT ?;",
            (session_id, limit),
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            if item.get("arguments"):
                try:
                    item["arguments"] = json.loads(item["arguments"])
                except Exception:
                    pass
            if item.get("result"):
                try:
                    item["result"] = json.loads(item["result"])
                except Exception:
                    pass
            results.append(item)
        return results

    # --------------------------------------------------------------------------
    # Full-Text Search (FTS5) API
    # --------------------------------------------------------------------------

    @staticmethod
    def _sanitize_fts5_query(query: str) -> str:
        """
        Sanitizes user query for safe SQLite FTS5 MATCH execution.
        Assimilated from NousResearch/hermes-agent hermes_state.py.
        """
        query = query[:MAX_FTS5_QUERY_CHARS]

        # Step 1: Protect balanced double-quoted phrases
        _quoted_parts = []
        pieces = []
        i = 0
        while i < len(query):
            ch = query[i]
            if ch != '"':
                pieces.append(ch)
                i += 1
                continue
            end = query.find('"', i + 1)
            if end == -1:
                pieces.append(" ")
                i += 1
                continue
            _quoted_parts.append(query[i : end + 1])
            pieces.append(f"\x00Q{len(_quoted_parts) - 1}\x00")
            i = end + 1

        sanitized = "".join(pieces)

        # Step 2: Strip unquoted FTS5 special characters
        sanitized = re.sub(r'[+{}():\"^]', " ", sanitized)

        # Step 3: Collapse repeated wildcards and strip leading wildcards
        sanitized = re.sub(r"\*+", "*", sanitized)
        sanitized = re.sub(r"(^|\s)\*", r"\1", sanitized)

        # Step 4: Remove dangling boolean operators
        sanitized = re.sub(r"(?i)^(AND|OR|NOT)\b\s*", "", sanitized.strip())
        sanitized = re.sub(r"(?i)\s+(AND|OR|NOT)\s*$", "", sanitized.strip())

        # Step 5: Wrap unquoted dotted/hyphenated words in double quotes
        sanitized = re.sub(r"\b(\w+(?:[._-]\w+)+)\b", r'"\1"', sanitized)

        # Step 6: Restore preserved quotes
        for idx, quoted in enumerate(_quoted_parts):
            sanitized = sanitized.replace(f"\x00Q{idx}\x00", quoted)

        return sanitized.strip()

    def search_fts(
        self,
        query: str,
        limit: int = 20,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across messages using SQLite FTS5.
        Falls back to LIKE wildcard if FTS5 encounters any error or empty sanitize.
        """
        clean_q = self._sanitize_fts5_query(query)
        conn = self._get_connection()

        if clean_q:
            try:
                if session_id:
                    cursor = conn.execute(
                        """
                        SELECT m.*, snippet(fts_messages, 0, '<b>', '</b>', '...', 32) AS snippet,
                               fts_messages.rank AS rank
                        FROM fts_messages
                        JOIN messages m ON m.id = fts_messages.rowid
                        WHERE fts_messages MATCH ? AND m.session_id = ?
                        ORDER BY rank
                        LIMIT ?;
                        """,
                        (clean_q, session_id, limit),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT m.*, snippet(fts_messages, 0, '<b>', '</b>', '...', 32) AS snippet,
                               fts_messages.rank AS rank
                        FROM fts_messages
                        JOIN messages m ON m.id = fts_messages.rowid
                        WHERE fts_messages MATCH ?
                        ORDER BY rank
                        LIMIT ?;
                        """,
                        (clean_q, limit),
                    )

                rows = cursor.fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except sqlite3.OperationalError as e:
                logger.debug(f"FTS5 match failed, falling back to LIKE: {e}")

        # Fallback to LIKE search
        like_pattern = f"%{query.strip()}%"
        if session_id:
            cursor = conn.execute(
                """
                SELECT *, content AS snippet, 0.0 AS rank
                FROM messages
                WHERE session_id = ? AND content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (session_id, like_pattern, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT *, content AS snippet, 0.0 AS rank
                FROM messages
                WHERE content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (like_pattern, limit),
            )

        return [dict(r) for r in cursor.fetchall()]

    def search_messages(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Hermes compatibility alias for search_fts."""
        return self.search_fts(*args, **kwargs)
```

---

## 7. Verification & Testing Strategy

To verify this implementation when deployed:
1. **Schema Check**:
   ```python
   db = SessionDB(":memory:")
   cursor = db._get_connection().execute("SELECT name FROM sqlite_master WHERE type='table';")
   tables = [r[0] for r in cursor.fetchall()]
   assert "schema_version" in tables
   assert "sessions" in tables
   assert "messages" in tables
   assert "tool_calls" in tables
   assert "fts_messages" in tables
   ```
2. **Schema Version Verification**:
   ```python
   v = db._get_connection().execute("SELECT version FROM schema_version").fetchone()[0]
   assert v == 12
   ```
3. **FTS Trigger Sync Verification**:
   ```python
   sid = db.create_session("Test")
   mid = db.add_message(sid, "user", "Searching for quantum resonance")
   results = db.search_fts("quantum")
   assert len(results) == 1
   assert results[0]["id"] == int(mid)
   ```
4. **Cascade Deletion Verification**:
   ```python
   db.delete_session(sid)
   assert len(db.get_messages(sid)) == 0
   assert len(db.search_fts("quantum")) == 0
   ```
5. **Multi-Threaded Concurrency Verification**:
   Spawn 10 concurrent threads: 5 writers appending messages, 5 readers querying sessions and searching FTS. Verify 0 deadlocks and 0 `database is locked` errors.
