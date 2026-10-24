import json
import time
import aiosqlite
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.config import settings

class SQLiteMemory:
    def __init__(self, db_path: Path = settings.DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    tool TEXT NOT NULL,
                    args_hash TEXT,
                    args_summary TEXT,
                    risk_level TEXT,
                    outcome TEXT,
                    timestamp REAL NOT NULL,
                    details TEXT
                )
            """)
            await db.commit()

    async def get_or_create_session(self, session_id: str, title: str = "New Session") -> str:
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            row = await cursor.fetchone()
            if not row:
                await db.execute(
                    "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (session_id, title, now, now)
                )
                await db.commit()
        return session_id

    async def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_messages(self, session_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, session_id, role, content, tool_calls, created_at FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                (session_id, limit)
            )
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                if item.get("tool_calls"):
                    try:
                        item["tool_calls"] = json.loads(item["tool_calls"])
                    except Exception:
                        pass
                result.append(item)
            return result

    async def save_message(self, session_id: str, role: str, content: str, tool_calls: Optional[List] = None) -> int:
        now = time.time()
        calls_json = json.dumps(tool_calls) if tool_calls else None
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO messages (session_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, calls_json, now)
            )
            await db.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
            await db.commit()
            return cursor.lastrowid or 0

    async def clear_session(self, session_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            await db.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (time.time(), session_id))
            await db.commit()

    async def search_messages(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, session_id, role, content, created_at FROM messages WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", limit)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def log_audit(
        self,
        tool: str,
        args_summary: Dict[str, Any],
        risk_level: str = "LOW",
        outcome: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        import hashlib
        import uuid
        entry_id = f"audit_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        args_str = json.dumps(args_summary, sort_keys=True)
        args_hash = hashlib.sha256(args_str.encode("utf-8")).hexdigest()[:12]
        now = time.time()
        details_str = json.dumps(details or {})

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO audit_logs (id, tool, args_hash, args_summary, risk_level, outcome, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (entry_id, tool, args_hash, args_str, risk_level, outcome, now, details_str)
            )
            await db.commit()
        return entry_id

    async def get_audit_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        tool: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if tool:
                cursor = await db.execute(
                    """
                    SELECT id, tool, args_hash, args_summary, risk_level, outcome, timestamp, details
                    FROM audit_logs
                    WHERE tool = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (tool, limit, offset)
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT id, tool, args_hash, args_summary, risk_level, outcome, timestamp, details
                    FROM audit_logs
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["args_summary"] = json.loads(item["args_summary"])
                except Exception:
                    item["args_summary"] = {}
                try:
                    item["details"] = json.loads(item["details"])
                except Exception:
                    item["details"] = {}
                results.append(item)
            return results

memory_store = SQLiteMemory()
