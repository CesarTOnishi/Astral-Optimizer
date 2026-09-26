from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any

from app.paths import app_data_dir


DEFAULT_RETENTION_LIMIT = 5
MAX_RETENTION_LIMIT = 50


def default_build_history_path() -> Path:
    return app_data_dir() / "build_history.db"


@dataclass(frozen=True, slots=True)
class BuildSnapshot:
    id: int
    owner_id: int
    uid: str
    character_id: str
    character_name: str
    payload: dict[str, Any]
    created_at: str
    name: str = ""
    note: str = ""
    favorite: bool = False

    @property
    def benchmark_score(self) -> float:
        benchmark = self.payload.get("benchmark", {})
        return float(benchmark.get("score", 0.0)) if isinstance(benchmark, dict) else 0.0

    @property
    def benchmark_grade(self) -> str:
        benchmark = self.payload.get("benchmark", {})
        return str(benchmark.get("grade", "N/A")) if isinstance(benchmark, dict) else "N/A"


class BuildHistoryDatabase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_build_history_path()
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
                CREATE TABLE IF NOT EXISTS build_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER NOT NULL,
                    uid TEXT NOT NULL,
                    character_id TEXT NOT NULL,
                    character_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    name TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    favorite INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(build_snapshots)")
            }
            for column, definition in (
                ("name", "TEXT NOT NULL DEFAULT ''"),
                ("note", "TEXT NOT NULL DEFAULT ''"),
                ("favorite", "INTEGER NOT NULL DEFAULT 0"),
            ):
                if column not in columns:
                    connection.execute(
                        f"ALTER TABLE build_snapshots ADD COLUMN {column} {definition}"
                    )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS build_history_settings (
                    owner_id INTEGER PRIMARY KEY,
                    retention_limit INTEGER NOT NULL DEFAULT 5
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_build_snapshots_character
                ON build_snapshots(owner_id, uid, character_id, created_at DESC, id DESC)
                """
            )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _snapshot(row: sqlite3.Row) -> BuildSnapshot:
        return BuildSnapshot(
            id=int(row["id"]),
            owner_id=int(row["owner_id"]),
            uid=str(row["uid"]),
            character_id=str(row["character_id"]),
            character_name=str(row["character_name"]),
            payload=json.loads(str(row["payload_json"])),
            created_at=str(row["created_at"]),
            name=str(row["name"]),
            note=str(row["note"]),
            favorite=bool(row["favorite"]),
        )

    def snapshots(
        self, owner_id: int, uid: str, character_id: str
    ) -> list[BuildSnapshot]:
        if owner_id <= 0 or not uid or not character_id:
            return []
        connection = self.connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM build_snapshots
                WHERE owner_id = ? AND uid = ? AND character_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (owner_id, uid, character_id),
            ).fetchall()
        finally:
            connection.close()
        return [self._snapshot(row) for row in rows]

    def save(
        self,
        owner_id: int,
        uid: str,
        character_id: str,
        character_name: str,
        payload: dict[str, Any],
        *,
        name: str = "",
        note: str = "",
        favorite: bool = False,
    ) -> BuildSnapshot:
        if owner_id <= 0:
            raise ValueError("Entre em um perfil para salvar builds.")
        if not uid or not character_id:
            raise ValueError("Carregue uma conta e selecione um personagem.")
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT id, favorite FROM build_snapshots
                WHERE owner_id = ? AND uid = ? AND character_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (owner_id, uid, character_id),
            ).fetchall()
            limit = self._retention_limit(connection, owner_id)
            to_remove = max(0, len(existing) - limit + 1)
            removable = [int(row["id"]) for row in existing if not row["favorite"]]
            if len(removable) < to_remove:
                raise ValueError(
                    "O limite de builds foi atingido e as versões antigas estão "
                    "marcadas como favoritas. Desmarque ou exclua uma para continuar."
                )
            for snapshot_id in removable[:to_remove]:
                connection.execute(
                    "DELETE FROM build_snapshots WHERE id = ?", (snapshot_id,)
                )
            cursor = connection.execute(
                """
                INSERT INTO build_snapshots (
                    owner_id, uid, character_id, character_name, payload_json,
                    name, note, favorite
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner_id, uid, character_id, character_name,
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    name.strip()[:80], note.strip()[:2000], int(favorite),
                ),
            )
            snapshot_id = int(cursor.lastrowid)
            connection.commit()
            row = connection.execute(
                "SELECT * FROM build_snapshots WHERE id = ?", (snapshot_id,)
            ).fetchone()
            if row is None:
                raise RuntimeError("Não foi possível recuperar a build salva.")
            return self._snapshot(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _retention_limit(connection: sqlite3.Connection, owner_id: int) -> int:
        row = connection.execute(
            "SELECT retention_limit FROM build_history_settings WHERE owner_id = ?",
            (owner_id,),
        ).fetchone()
        return int(row[0]) if row else DEFAULT_RETENTION_LIMIT

    def retention_limit(self, owner_id: int) -> int:
        connection = self.connect()
        try:
            return self._retention_limit(connection, owner_id)
        finally:
            connection.close()

    def set_retention_limit(self, owner_id: int, limit: int) -> None:
        if owner_id <= 0:
            raise ValueError("Entre em um perfil para configurar a retenção.")
        if not 1 <= limit <= MAX_RETENTION_LIMIT:
            raise ValueError(f"Escolha um limite entre 1 e {MAX_RETENTION_LIMIT}.")
        connection = self.connect()
        try:
            connection.execute(
                "INSERT INTO build_history_settings(owner_id, retention_limit) "
                "VALUES (?, ?) ON CONFLICT(owner_id) DO UPDATE SET "
                "retention_limit = excluded.retention_limit",
                (owner_id, limit),
            )
            connection.commit()
        finally:
            connection.close()

    def update_metadata(
        self, owner_id: int, snapshot_id: int, *,
        name: str, note: str, favorite: bool,
    ) -> bool:
        connection = self.connect()
        try:
            cursor = connection.execute(
                "UPDATE build_snapshots SET name = ?, note = ?, favorite = ? "
                "WHERE id = ? AND owner_id = ?",
                (name.strip()[:80], note.strip()[:2000], int(favorite),
                 snapshot_id, owner_id),
            )
            connection.commit()
            return cursor.rowcount > 0
        finally:
            connection.close()

    def delete(self, owner_id: int, snapshot_id: int) -> bool:
        connection = self.connect()
        try:
            cursor = connection.execute(
                "DELETE FROM build_snapshots WHERE id = ? AND owner_id = ?",
                (snapshot_id, owner_id),
            )
            connection.commit()
            return cursor.rowcount > 0
        finally:
            connection.close()
