import hashlib
import json
import logging
from pathlib import Path
import time
import uuid
import aiosqlite

from jarvis.config.settings import settings

logger = logging.getLogger("jarvis.security.audit_log")


class AuditLog:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.DATABASE_PATH)

    async def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    tool TEXT NOT NULL,
                    args_hash TEXT NOT NULL,
                    args_summary TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}'
                );
            """)
            await db.commit()

    def _hash_args(self, args: dict) -> str:
        serialized = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    async def record(
        self,
        tool: str,
        args: dict,
        risk_level: str,
        outcome: str,
        details: dict | None = None
    ) -> str:
        log_id = str(uuid.uuid4())
        now = time.time()
        args_hash = self._hash_args(args)
        args_summary = json.dumps(args, default=str)
        details_json = json.dumps(details or {}, default=str)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO audit_log (id, tool, args_hash, args_summary, risk_level, outcome, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (log_id, tool, args_hash, args_summary, risk_level, outcome, now, details_json)
            )
            await db.commit()

        logger.info(
            f"[AUDIT] Tool='{tool}' Risk='{risk_level}' Outcome='{outcome}' Hash='{args_hash}'"
        )
        return log_id

    async def list_logs(
        self, limit: int = 50, offset: int = 0, tool: str | None = None
    ) -> list[dict]:
        results = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if tool:
                query = "SELECT * FROM audit_log WHERE tool = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params = (tool, limit, offset)
            else:
                query = "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params = (limit, offset)

            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    results.append({
                        "id": row["id"],
                        "tool": row["tool"],
                        "args_hash": row["args_hash"],
                        "args_summary": json.loads(row["args_summary"]),
                        "risk_level": row["risk_level"],
                        "outcome": row["outcome"],
                        "timestamp": row["timestamp"],
                        "details": json.loads(row["details"])
                    })
        return results


audit_log = AuditLog()
