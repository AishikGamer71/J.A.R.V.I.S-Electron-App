import logging
from pathlib import Path
import time
import aiosqlite

from jarvis.config.settings import settings

logger = logging.getLogger("jarvis.security.permission_store")


class PermissionStore:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.DATABASE_PATH)

    async def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    tool TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT '*',
                    granted INTEGER NOT NULL,
                    granted_at REAL NOT NULL,
                    PRIMARY KEY (tool, scope)
                );
            """)
            await db.commit()

    async def check(self, tool: str, scope: str = "*") -> bool:
        """Check if permission is granted. Default-deny if no record exists."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Check specific scope or global '*'
            async with db.execute(
                "SELECT granted FROM permissions WHERE tool = ? AND (scope = ? OR scope = '*') ORDER BY scope DESC LIMIT 1",
                (tool, scope)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return bool(row["granted"])
        return False

    async def grant(self, tool: str, scope: str = "*") -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO permissions (tool, scope, granted, granted_at)
                VALUES (?, ?, 1, ?)
                """,
                (tool, scope, time.time())
            )
            await db.commit()
            logger.info(f"Granted permission for tool '{tool}' with scope '{scope}'")

    async def revoke(self, tool: str, scope: str = "*") -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM permissions WHERE tool = ? AND scope = ?",
                (tool, scope)
            )
            await db.commit()
            logger.info(f"Revoked permission for tool '{tool}' with scope '{scope}'")

    async def list_permissions(self) -> list[dict]:
        results = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM permissions ORDER BY granted_at DESC") as cursor:
                async for row in cursor:
                    results.append({
                        "tool": row["tool"],
                        "scope": row["scope"],
                        "granted": bool(row["granted"]),
                        "granted_at": row["granted_at"]
                    })
        return results


permission_store = PermissionStore()
