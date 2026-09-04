from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any

from app.paths import app_data_dir


MAX_SNAPSHOTS_PER_CHARACTER = 5


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
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    ) -> BuildSnapshot:
        if owner_id <= 0:
            raise ValueError("Entre em um perfil para salvar builds.")
        if not uid or not character_id:
            raise ValueError("Carregue uma conta e selecione um personagem.")
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            count = int(connection.execute(
                """
                SELECT COUNT(*) FROM build_snapshots
                WHERE owner_id = ? AND uid = ? AND character_id = ?
                """,
                (owner_id, uid, character_id),
            ).fetchone()[0])
            if count >= MAX_SNAPSHOTS_PER_CHARACTER:
                raise ValueError(
                    "O limite é de 5 builds salvas por personagem. Exclua uma para continuar."
                )
            cursor = connection.execute(
                """
                INSERT INTO build_snapshots (
                    owner_id, uid, character_id, character_name, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    owner_id, uid, character_id, character_name,
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
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
