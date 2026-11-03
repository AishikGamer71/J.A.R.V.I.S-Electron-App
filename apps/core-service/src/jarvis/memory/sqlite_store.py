import json
import logging
from pathlib import Path
import aiosqlite
from jarvis.config.settings import settings
from jarvis.domain.entities.models import ChatMessage, ChatSession, MessageRole, ModelTier
from jarvis.domain.ports.memory_port import MemoryPort

logger = logging.getLogger("jarvis.memory.sqlite")


class SQLiteMemoryStore(MemoryPort):
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.DATABASE_PATH)

    async def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode = WAL;")
            await db.execute("PRAGMA foreign_keys = ON;")

            # Sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );
            """)

            # Messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tier TEXT,
                    model TEXT,
                    created_at REAL NOT NULL,
                    tokens TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                );
            """)

            # FTS5 Virtual Table for full-text search
            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    message_id UNINDEXED,
                    content,
                    tokenize = 'porter unicode61'
                );
            """)

            # Trigger to insert into FTS index automatically
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_messages_ai AFTER INSERT ON messages
                BEGIN
                    INSERT INTO messages_fts(message_id, content)
                    VALUES (new.id, new.content);
                END;
            """)

            # Trigger to delete from FTS index automatically
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_messages_ad AFTER DELETE ON messages
                BEGIN
                    DELETE FROM messages_fts WHERE message_id = old.id;
                END;
            """)

            await db.commit()
            logger.info(f"SQLite FTS5 database initialized at {self.db_path}")

    async def create_session(self, title: str = "New Session") -> ChatSession:
        session = ChatSession(title=title)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at, metadata) VALUES (?, ?, ?, ?, ?)",
                (session.id, session.title, session.created_at, session.updated_at, json.dumps(session.metadata))
            )
            await db.commit()
        return session

    async def get_session(self, session_id: str) -> ChatSession | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return ChatSession(
                        id=row["id"],
                        title=row["title"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        metadata=json.loads(row["metadata"])
                    )
        return None

    async def list_sessions(self, limit: int = 50) -> list[ChatSession]:
        sessions = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
            ) as cursor:
                async for row in cursor:
                    sessions.append(
                        ChatSession(
                            id=row["id"],
                            title=row["title"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                            metadata=json.loads(row["metadata"])
                        )
                    )
        return sessions

    async def delete_session(self, session_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def save_message(self, message: ChatMessage) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            # Ensure session exists or create it
            async with db.execute("SELECT id FROM sessions WHERE id = ?", (message.session_id,)) as cur:
                if not await cur.fetchone():
                    await db.execute(
                        "INSERT INTO sessions (id, title, created_at, updated_at, metadata) VALUES (?, ?, ?, ?, ?)",
                        (message.session_id, "New Session", message.created_at, message.created_at, "{}")
                    )

            await db.execute(
                """
                INSERT OR REPLACE INTO messages 
                (id, session_id, role, content, tier, model, created_at, tokens, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.session_id,
                    message.role.value,
                    message.content,
                    message.tier.value if message.tier else None,
                    message.model,
                    message.created_at,
                    json.dumps(message.tokens) if message.tokens else None,
                    json.dumps(message.metadata)
                )
            )

            # Update session's updated_at
            await db.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (message.created_at, message.session_id)
            )
            await db.commit()

    async def get_messages(self, session_id: str, limit: int = 100) -> list[ChatMessage]:
        messages = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit)
            ) as cursor:
                async for row in cursor:
                    messages.append(
                        ChatMessage(
                            id=row["id"],
                            session_id=row["session_id"],
                            role=MessageRole(row["role"]),
                            content=row["content"],
                            tier=ModelTier(row["tier"]) if row["tier"] else None,
                            model=row["model"],
                            created_at=row["created_at"],
                            tokens=json.loads(row["tokens"]) if row["tokens"] else None,
                            metadata=json.loads(row["metadata"])
                        )
                    )
        return messages

    async def search_messages(self, query: str, limit: int = 20) -> list[ChatMessage]:
        clean_query = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not clean_query:
            return []

        # Use FTS5 prefix match
        fts_query = f"{clean_query}*"
        messages = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT m.* FROM messages m
                JOIN messages_fts f ON m.id = f.message_id
                WHERE messages_fts MATCH ?
                ORDER BY m.created_at DESC LIMIT ?
                """,
                (fts_query, limit)
            ) as cursor:
                async for row in cursor:
                    messages.append(
                        ChatMessage(
                            id=row["id"],
                            session_id=row["session_id"],
                            role=MessageRole(row["role"]),
                            content=row["content"],
                            tier=ModelTier(row["tier"]) if row["tier"] else None,
                            model=row["model"],
                            created_at=row["created_at"],
                            tokens=json.loads(row["tokens"]) if row["tokens"] else None,
                            metadata=json.loads(row["metadata"])
                        )
                    )
        return messages
