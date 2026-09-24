from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3

from PySide6.QtCore import QObject, Signal

from app.paths import app_data_dir


def default_activity_log_path() -> Path:
    return app_data_dir() / "activity.db"


@dataclass(frozen=True, slots=True)
class ActivityEvent:
    id: int
    owner_id: int
    category: str
    title: str
    message: str
    kind: str
    created_at: str


class ActivityLog(QObject):
    """Histórico local e persistente dos resultados importantes do app."""

    changed = Signal()

    def __init__(
        self, parent: QObject | None = None, path: Path | None = None
    ) -> None:
        super().__init__(parent)
        self.path = path or default_activity_log_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        connection = self.connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER NOT NULL DEFAULT 0,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'info',
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_activity_owner_created
                ON activity_events(owner_id, id DESC)
                """
            )
            connection.commit()
        finally:
            connection.close()

    def add(
        self,
        category: str,
        title: str,
        message: str,
        *,
        owner_id: int = 0,
        kind: str = "info",
    ) -> int:
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        connection = self.connect()
        try:
            cursor = connection.execute(
                """
                INSERT INTO activity_events
                    (owner_id, category, title, message, kind, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    max(0, int(owner_id)),
                    str(category),
                    str(title),
                    str(message),
                    str(kind),
                    created_at,
                ),
            )
            connection.execute(
                """
                DELETE FROM activity_events
                WHERE id NOT IN (
                    SELECT id FROM activity_events ORDER BY id DESC LIMIT 500
                )
                """
            )
            connection.commit()
            event_id = int(cursor.lastrowid or 0)
        finally:
            connection.close()
        self.changed.emit()
        return event_id

    def events(self, owner_id: int = 0, limit: int = 30) -> tuple[ActivityEvent, ...]:
        safe_limit = max(1, min(int(limit), 200))
        connection = self.connect()
        try:
            if owner_id > 0:
                rows = connection.execute(
                    """
                    SELECT * FROM activity_events
                    WHERE owner_id IN (0, ?)
                    ORDER BY id DESC LIMIT ?
                    """,
                    (owner_id, safe_limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM activity_events
                    WHERE owner_id = 0
                    ORDER BY id DESC LIMIT ?
                    """,
                    (safe_limit,),
                ).fetchall()
        finally:
            connection.close()
        return tuple(
            ActivityEvent(
                id=int(row["id"]),
                owner_id=int(row["owner_id"]),
                category=str(row["category"]),
                title=str(row["title"]),
                message=str(row["message"]),
                kind=str(row["kind"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        )
