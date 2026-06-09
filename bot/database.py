"""SQLite-хранилище пользователей бота."""

from __future__ import annotations  # noqa: I001

import aiosqlite
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class UserStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"


@dataclass
class User:
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    status: UserStatus
    has_key: bool
    created_at: str
    approved_at: str | None
    approved_by: int | None

    @property
    def display_name(self) -> str:
        parts = [self.first_name, self.last_name]
        name = " ".join(p for p in parts if p)
        if name:
            return name
        if self.username:
            return f"@{self.username}"
        return str(self.telegram_id)


class Database:
    def __init__(self, path: Path):
        self.path = path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    has_key INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    approved_at TEXT,
                    approved_by INTEGER
                )
            """)
            await db.commit()

    def _row_to_user(self, row: aiosqlite.Row) -> User:
        return User(
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            status=UserStatus(row["status"]),
            has_key=bool(row["has_key"]),
            created_at=row["created_at"],
            approved_at=row["approved_at"],
            approved_by=row["approved_by"],
        )

    async def get_user(self, telegram_id: int) -> User | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return self._row_to_user(row) if row else None

    async def upsert_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> tuple[User, bool]:
        """Возвращает (user, is_new)."""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                existing = await cursor.fetchone()

            if existing:
                await db.execute(
                    """UPDATE users SET username = ?, first_name = ?, last_name = ?
                       WHERE telegram_id = ?""",
                    (username, first_name, last_name, telegram_id),
                )
                await db.commit()
                user = await self.get_user(telegram_id)
                assert user is not None
                return user, False

            await db.execute(
                """INSERT INTO users
                   (telegram_id, username, first_name, last_name, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (telegram_id, username, first_name, last_name, UserStatus.PENDING.value, now),
            )
            await db.commit()
            user = await self.get_user(telegram_id)
            assert user is not None
            return user, True

    async def set_status(
        self, telegram_id: int, status: UserStatus, approved_by: int | None = None
    ) -> User | None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.path) as db:
            if status == UserStatus.APPROVED:
                await db.execute(
                    """UPDATE users SET status = ?, approved_at = ?, approved_by = ?
                       WHERE telegram_id = ?""",
                    (status.value, now, approved_by, telegram_id),
                )
            else:
                await db.execute(
                    "UPDATE users SET status = ? WHERE telegram_id = ?",
                    (status.value, telegram_id),
                )
            await db.commit()
        return await self.get_user(telegram_id)

    async def set_has_key(self, telegram_id: int, has_key: bool) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE users SET has_key = ? WHERE telegram_id = ?",
                (int(has_key), telegram_id),
            )
            await db.commit()

    async def list_by_status(self, status: UserStatus) -> list[User]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE status = ? ORDER BY created_at",
                (status.value,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_user(r) for r in rows]

    async def list_all(self) -> list[User]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users ORDER BY created_at") as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_user(r) for r in rows]
