from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from app.benchmark import BenchmarkEngine
from app.models import AccountSummary, CharacterStat, RelicSummary
from app.paths import app_data_dir
from app.relics.models import StoredRelic


def default_relic_database_path() -> Path:
    return app_data_dir() / "relics.db"


class RelicDatabase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_relic_database_path()
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
                CREATE TABLE IF NOT EXISTS relic_inventory (
                    owner_id INTEGER NOT NULL,
                    uid TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    relic_json TEXT NOT NULL,
                    score REAL NOT NULL,
                    grade TEXT NOT NULL,
                    current_character_id TEXT NOT NULL DEFAULT '',
                    current_character_name TEXT NOT NULL DEFAULT '',
                    current_character_icon TEXT NOT NULL DEFAULT '',
                    previous_character_id TEXT NOT NULL DEFAULT '',
                    previous_character_name TEXT NOT NULL DEFAULT '',
                    previous_character_icon TEXT NOT NULL DEFAULT '',
                    first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (owner_id, uid, fingerprint)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_relic_inventory_owner_uid_score
                ON relic_inventory(owner_id, uid, score DESC)
                """
            )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _relic_payload(relic: RelicSummary) -> dict[str, Any]:
        return {
            "slot": relic.slot,
            "slot_key": relic.slot_key,
            "set_name": relic.set_name,
            "level": relic.level,
            "rarity": relic.rarity,
            "icon_url": relic.icon_url,
            "main_stat": asdict(relic.main_stat),
            "sub_stats": [asdict(stat) for stat in relic.sub_stats],
        }

    @classmethod
    def fingerprint(cls, relic: RelicSummary) -> str:
        canonical = json.dumps(
            cls._relic_payload(relic), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _stat(payload: dict[str, Any]) -> CharacterStat:
        return CharacterStat(
            key=str(payload.get("key", "")),
            name=str(payload.get("name", "")),
            value=float(payload.get("value", 0.0)),
            formatted_value=str(payload.get("formatted_value", "")),
            is_percentage=bool(payload.get("is_percentage", False)),
            icon_url=str(payload.get("icon_url", "")),
            upgrades=int(payload.get("upgrades", 0)),
        )

    @classmethod
    def _relic(cls, raw: str) -> RelicSummary:
        payload = json.loads(raw)
        return RelicSummary(
            slot=str(payload.get("slot", "")),
            set_name=str(payload.get("set_name", "")),
            level=int(payload.get("level", 0)),
            rarity=int(payload.get("rarity", 0)),
            icon_url=str(payload.get("icon_url", "")),
            main_stat=cls._stat(payload.get("main_stat", {})),
            sub_stats=[cls._stat(item) for item in payload.get("sub_stats", [])],
            slot_key=str(payload.get("slot_key", "")),
        )

    def sync_account(
        self,
        owner_id: int,
        account: AccountSummary,
        engine: BenchmarkEngine | None = None,
    ) -> int:
        if owner_id <= 0 or not account.uid or not account.characters:
            return 0
        scorer = engine or BenchmarkEngine()
        seen: list[str] = []
        connection = self.connect()
        try:
            for character in account.characters:
                for relic in character.relics:
                    fingerprint = self.fingerprint(relic)
                    seen.append(fingerprint)
                    rating = scorer.rate_relic(character, relic)
                    existing = connection.execute(
                        """
                        SELECT current_character_id, current_character_name,
                               current_character_icon, previous_character_id,
                               previous_character_name, previous_character_icon
                        FROM relic_inventory
                        WHERE owner_id = ? AND uid = ? AND fingerprint = ?
                        """,
                        (owner_id, account.uid, fingerprint),
                    ).fetchone()
                    previous_id = str(existing["previous_character_id"] if existing else "")
                    previous_name = str(existing["previous_character_name"] if existing else "")
                    previous_icon = str(existing["previous_character_icon"] if existing else "")
                    if existing and str(existing["current_character_id"]) not in {
                        "", character.avatar_id
                    }:
                        previous_id = str(existing["current_character_id"])
                        previous_name = str(existing["current_character_name"])
                        previous_icon = str(existing["current_character_icon"])
                    relic_json = json.dumps(
                        self._relic_payload(relic), ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    connection.execute(
                        """
                        INSERT INTO relic_inventory (
                            owner_id, uid, fingerprint, relic_json, score, grade,
                            current_character_id, current_character_name,
                            current_character_icon, previous_character_id,
                            previous_character_name, previous_character_icon
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(owner_id, uid, fingerprint) DO UPDATE SET
                            relic_json = excluded.relic_json,
                            score = excluded.score,
                            grade = excluded.grade,
                            current_character_id = excluded.current_character_id,
                            current_character_name = excluded.current_character_name,
                            current_character_icon = excluded.current_character_icon,
                            previous_character_id = excluded.previous_character_id,
                            previous_character_name = excluded.previous_character_name,
                            previous_character_icon = excluded.previous_character_icon,
                            last_seen = CURRENT_TIMESTAMP
                        """,
                        (
                            owner_id, account.uid, fingerprint, relic_json,
                            rating.score, rating.grade, character.avatar_id,
                            character.name, character.icon_url, previous_id,
                            previous_name, previous_icon,
                        ),
                    )

            placeholders = ",".join("?" for _ in seen)
            connection.execute(
                f"""
                UPDATE relic_inventory SET
                    previous_character_id = current_character_id,
                    previous_character_name = current_character_name,
                    previous_character_icon = current_character_icon,
                    current_character_id = '', current_character_name = '',
                    current_character_icon = ''
                WHERE owner_id = ? AND uid = ?
                  AND fingerprint NOT IN ({placeholders})
                  AND current_character_id <> ''
                """,
                (owner_id, account.uid, *seen),
            )
            connection.commit()
        finally:
            connection.close()
        return len(set(seen))

    def relics(self, owner_id: int, uid: str) -> list[StoredRelic]:
        if owner_id <= 0 or not uid:
            return []
        connection = self.connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM relic_inventory
                WHERE owner_id = ? AND uid = ?
                ORDER BY score DESC, last_seen DESC, fingerprint
                """,
                (owner_id, uid),
            ).fetchall()
        finally:
            connection.close()
        return [
            StoredRelic(
                fingerprint=str(row["fingerprint"]),
                uid=str(row["uid"]),
                relic=self._relic(str(row["relic_json"])),
                score=float(row["score"]),
                grade=str(row["grade"]),
                current_character_id=str(row["current_character_id"]),
                current_character_name=str(row["current_character_name"]),
                current_character_icon=str(row["current_character_icon"]),
                previous_character_id=str(row["previous_character_id"]),
                previous_character_name=str(row["previous_character_name"]),
                previous_character_icon=str(row["previous_character_icon"]),
                first_seen=str(row["first_seen"]),
                last_seen=str(row["last_seen"]),
            )
            for row in rows
        ]
