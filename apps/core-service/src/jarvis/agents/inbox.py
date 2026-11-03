import json
import logging
from pathlib import Path
import time
import uuid
import aiosqlite
from pydantic import BaseModel, Field

from jarvis.config.settings import settings

logger = logging.getLogger("jarvis.agents.inbox")


class InboxTaskStatus(str):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InboxEntry(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_task_id: str | None = None
    agent_name: str
    status: str = InboxTaskStatus.PENDING
    input_payload: dict = Field(default_factory=dict)
    output_payload: dict = Field(default_factory=dict)
    artifacts: list[dict] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class AgentInbox:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.DATABASE_PATH)

    async def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_inbox (
                    task_id TEXT PRIMARY KEY,
                    parent_task_id TEXT,
                    agent_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_payload TEXT NOT NULL DEFAULT '{}',
                    output_payload TEXT NOT NULL DEFAULT '{}',
                    artifacts TEXT NOT NULL DEFAULT '[]',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)
            await db.commit()

    async def create_task(
        self,
        agent_name: str,
        input_payload: dict,
        parent_task_id: str | None = None
    ) -> InboxEntry:
        now = time.time()
        entry = InboxEntry(
            parent_task_id=parent_task_id,
            agent_name=agent_name,
            status=InboxTaskStatus.PENDING,
            input_payload=input_payload,
            created_at=now,
            updated_at=now
        )
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO agent_inbox 
                (task_id, parent_task_id, agent_name, status, input_payload, output_payload, artifacts, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.task_id,
                    entry.parent_task_id,
                    entry.agent_name,
                    entry.status,
                    json.dumps(entry.input_payload),
                    json.dumps(entry.output_payload),
                    json.dumps(entry.artifacts),
                    entry.created_at,
                    entry.updated_at
                )
            )
            await db.commit()
        logger.info(f"[INBOX] Created task {entry.task_id} for agent '{agent_name}'")
        return entry

    async def update_status(
        self,
        task_id: str,
        status: str,
        output_payload: dict | None = None,
        artifacts: list[dict] | None = None
    ) -> None:
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            if output_payload is not None and artifacts is not None:
                await db.execute(
                    """
                    UPDATE agent_inbox 
                    SET status = ?, output_payload = ?, artifacts = ?, updated_at = ?
                    WHERE task_id = ?
                    """,
                    (status, json.dumps(output_payload), json.dumps(artifacts), now, task_id)
                )
            elif output_payload is not None:
                await db.execute(
                    """
                    UPDATE agent_inbox 
                    SET status = ?, output_payload = ?, updated_at = ?
                    WHERE task_id = ?
                    """,
                    (status, json.dumps(output_payload), now, task_id)
                )
            else:
                await db.execute(
                    "UPDATE agent_inbox SET status = ?, updated_at = ? WHERE task_id = ?",
                    (status, now, task_id)
                )
            await db.commit()

    async def get_task(self, task_id: str) -> InboxEntry | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM agent_inbox WHERE task_id = ?", (task_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return InboxEntry(
                        task_id=row["task_id"],
                        parent_task_id=row["parent_task_id"],
                        agent_name=row["agent_name"],
                        status=row["status"],
                        input_payload=json.loads(row["input_payload"]),
                        output_payload=json.loads(row["output_payload"]),
                        artifacts=json.loads(row["artifacts"]),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"]
                    )
        return None

    async def list_tasks(
        self,
        limit: int = 50,
        agent_name: str | None = None,
        parent_task_id: str | None = None
    ) -> list[InboxEntry]:
        results = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM agent_inbox WHERE 1=1"
            params = []
            if agent_name:
                query += " AND agent_name = ?"
                params.append(agent_name)
            if parent_task_id:
                query += " AND parent_task_id = ?"
                params.append(parent_task_id)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            async with db.execute(query, tuple(params)) as cursor:
                async for row in cursor:
                    results.append(
                        InboxEntry(
                            task_id=row["task_id"],
                            parent_task_id=row["parent_task_id"],
                            agent_name=row["agent_name"],
                            status=row["status"],
                            input_payload=json.loads(row["input_payload"]),
                            output_payload=json.loads(row["output_payload"]),
                            artifacts=json.loads(row["artifacts"]),
                            created_at=row["created_at"],
                            updated_at=row["updated_at"]
                        )
                    )
        return results


agent_inbox = AgentInbox()
