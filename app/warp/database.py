from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from app.paths import app_data_dir
from app.warp.models import WarpRecord, WarpSummary


def default_database_path() -> Path:
    return app_data_dir() / "warps.db"


class WarpDatabase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        connection = self.connect()
        try:
            table_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'warps'"
            ).fetchone()
            if not table_exists:
                self._create_table(connection)
            else:
                columns = {
                    str(row[1]) for row in connection.execute("PRAGMA table_info(warps)")
                }
                if "owner_id" not in columns:
                    connection.execute("ALTER TABLE warps RENAME TO warps_legacy")
                    self._create_table(connection)
                    connection.execute(
                        """
                        INSERT INTO warps
                            (owner_id, uid, id, gacha_type, item_id, name,
                             item_type, rank_type, time)
                        SELECT 0, uid, id, gacha_type, item_id, name,
                               item_type, rank_type, time
                        FROM warps_legacy
                        """
                    )
                    connection.execute("DROP TABLE warps_legacy")
                columns = {
                    str(row[1]) for row in connection.execute("PRAGMA table_info(warps)")
                }
                if "banner_id" not in columns:
                    connection.execute(
                        "ALTER TABLE warps ADD COLUMN banner_id TEXT NOT NULL DEFAULT ''"
                    )
                if "banner_title" not in columns:
                    connection.execute(
                        "ALTER TABLE warps ADD COLUMN banner_title TEXT NOT NULL DEFAULT ''"
                    )
                if "featured_name" not in columns:
                    connection.execute(
                        "ALTER TABLE warps ADD COLUMN featured_name TEXT NOT NULL DEFAULT ''"
                    )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_warps_owner_uid_type "
                "ON warps(owner_id, uid, gacha_type, time)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS warp_summaries (
                    owner_id INTEGER NOT NULL,
                    uid TEXT NOT NULL,
                    gacha_type TEXT NOT NULL,
                    total INTEGER NOT NULL,
                    five_star_count INTEGER NOT NULL,
                    four_star_count INTEGER NOT NULL,
                    five_star_pity INTEGER NOT NULL,
                    four_star_pity INTEGER NOT NULL,
                    featured_item_id TEXT NOT NULL,
                    featured_item_name TEXT NOT NULL,
                    featured_pity INTEGER NOT NULL,
                    featured_item_type TEXT NOT NULL,
                    PRIMARY KEY (owner_id, uid, gacha_type)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS planner_settings (
                    owner_id INTEGER PRIMARY KEY,
                    jades INTEGER NOT NULL DEFAULT 0,
                    passes INTEGER NOT NULL DEFAULT 0,
                    starlight INTEGER NOT NULL DEFAULT 0,
                    refund TEXT NOT NULL DEFAULT 'average',
                    strategy TEXT NOT NULL DEFAULT 'E2'
                )
                """
            )
            planner_columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(planner_settings)")
            }
            if "strategy" not in planner_columns:
                connection.execute(
                    "ALTER TABLE planner_settings ADD COLUMN strategy TEXT "
                    "NOT NULL DEFAULT 'E2'"
                )
            if "goal_sequence" not in planner_columns:
                connection.execute(
                    "ALTER TABLE planner_settings ADD COLUMN goal_sequence TEXT "
                    "NOT NULL DEFAULT 'E0,S1,E1'"
                )
            if "daily_jades" not in planner_columns:
                connection.execute(
                    "ALTER TABLE planner_settings ADD COLUMN daily_jades INTEGER "
                    "NOT NULL DEFAULT 60"
                )
            if "target_date" not in planner_columns:
                connection.execute(
                    "ALTER TABLE planner_settings ADD COLUMN target_date TEXT "
                    "NOT NULL DEFAULT ''"
                )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _create_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE warps (
                owner_id INTEGER NOT NULL DEFAULT 0,
                uid TEXT NOT NULL,
                id TEXT NOT NULL,
                gacha_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                rank_type INTEGER NOT NULL,
                time TEXT NOT NULL,
                banner_title TEXT NOT NULL DEFAULT '',
                featured_name TEXT NOT NULL DEFAULT '',
                banner_id TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (owner_id, uid, id)
            )
            """
        )

    def add_records(self, records: list[WarpRecord], owner_id: int = 0) -> int:
        if not records:
            return 0
        connection = self.connect()
        try:
            before_count = connection.execute(
                "SELECT COUNT(*) FROM warps WHERE owner_id = ?",
                (owner_id,),
            ).fetchone()[0]
            connection.executemany(
                """
                INSERT INTO warps
                    (owner_id, uid, id, gacha_type, item_id, name,
                     item_type, rank_type, time, banner_title, featured_name, banner_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_id, uid, id) DO UPDATE SET
                    banner_title = CASE WHEN excluded.banner_title <> ''
                        THEN excluded.banner_title ELSE warps.banner_title END,
                    featured_name = CASE WHEN excluded.featured_name <> ''
                        THEN excluded.featured_name ELSE warps.featured_name END,
                    banner_id = CASE WHEN excluded.banner_id <> ''
                        THEN excluded.banner_id ELSE warps.banner_id END
                """,
                [
                    (
                        owner_id,
                        record.uid,
                        record.id,
                        record.gacha_type,
                        record.item_id,
                        record.name,
                        record.item_type,
                        record.rank_type,
                        record.time,
                        record.banner_title,
                        record.featured_name,
                        record.banner_id,
                    )
                    for record in records
                    if record.uid and record.id
                ],
            )
            connection.commit()
            after_count = connection.execute(
                "SELECT COUNT(*) FROM warps WHERE owner_id = ?",
                (owner_id,),
            ).fetchone()[0]
            added = after_count - before_count
            return added
        finally:
            connection.close()

    def uids(self, owner_id: int = 0) -> list[str]:
        connection = self.connect()
        try:
            rows = connection.execute(
                """
                SELECT uid, MAX(time) AS latest FROM warps
                WHERE owner_id = ? GROUP BY uid ORDER BY latest DESC
                """,
                (owner_id,),
            ).fetchall()
        finally:
            connection.close()
        return [str(row["uid"]) for row in rows]

    def latest_uid(self, owner_id: int = 0) -> str:
        uids = self.uids(owner_id)
        return uids[0] if uids else ""

    def records(self, uid: str, owner_id: int = 0) -> list[WarpRecord]:
        if not uid:
            return []
        connection = self.connect()
        try:
            rows = connection.execute(
                """
                SELECT id, uid, gacha_type, item_id, name, item_type, rank_type,
                       time, banner_title, featured_name, banner_id
                FROM warps WHERE owner_id = ? AND uid = ?
                ORDER BY time ASC, length(id) ASC, id ASC
                """,
                (owner_id, uid),
            ).fetchall()
        finally:
            connection.close()
        return [WarpRecord(**dict(row)) for row in rows]

    def upsert_summary(self, summary: WarpSummary, owner_id: int = 0) -> None:
        connection = self.connect()
        try:
            connection.execute(
                """
                INSERT INTO warp_summaries
                    (owner_id, uid, gacha_type, total, five_star_count,
                     four_star_count, five_star_pity, four_star_pity,
                     featured_item_id, featured_item_name, featured_pity,
                     featured_item_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_id, uid, gacha_type) DO UPDATE SET
                    total = excluded.total,
                    five_star_count = excluded.five_star_count,
                    four_star_count = excluded.four_star_count,
                    five_star_pity = excluded.five_star_pity,
                    four_star_pity = excluded.four_star_pity,
                    featured_item_id = excluded.featured_item_id,
                    featured_item_name = excluded.featured_item_name,
                    featured_pity = excluded.featured_pity,
                    featured_item_type = excluded.featured_item_type
                """,
                (
                    owner_id, summary.uid, summary.gacha_type, summary.total,
                    summary.five_star_count, summary.four_star_count,
                    summary.five_star_pity, summary.four_star_pity,
                    summary.featured_item_id, summary.featured_item_name,
                    summary.featured_pity, summary.featured_item_type,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def summaries(self, uid: str, owner_id: int = 0) -> dict[str, WarpSummary]:
        if not uid:
            return {}
        connection = self.connect()
        try:
            rows = connection.execute(
                """
                SELECT uid, gacha_type, total, five_star_count, four_star_count,
                       five_star_pity, four_star_pity, featured_item_id,
                       featured_item_name, featured_pity, featured_item_type
                FROM warp_summaries WHERE owner_id = ? AND uid = ?
                """,
                (owner_id, uid),
            ).fetchall()
        finally:
            connection.close()
        summaries = [WarpSummary(**dict(row)) for row in rows]
        return {summary.gacha_type: summary for summary in summaries}

    def export_owner(self, owner_id: int) -> dict[str, Any]:
        connection = self.connect()
        try:
            records = connection.execute(
                """
                SELECT uid, id, gacha_type, item_id, name, item_type,
                       rank_type, time, banner_title, featured_name, banner_id
                FROM warps WHERE owner_id = ?
                ORDER BY time ASC, length(id) ASC, id ASC
                """,
                (owner_id,),
            ).fetchall()
            summaries = connection.execute(
                """
                SELECT uid, gacha_type, total, five_star_count, four_star_count,
                       five_star_pity, four_star_pity, featured_item_id,
                       featured_item_name, featured_pity, featured_item_type
                FROM warp_summaries WHERE owner_id = ?
                """,
                (owner_id,),
            ).fetchall()
        finally:
            connection.close()
        return {
            "version": 1,
            "records": [dict(row) for row in records],
            "summaries": [dict(row) for row in summaries],
            "planner": self.planner_settings(owner_id),
        }

    def restore_owner(self, payload: dict[str, Any], owner_id: int) -> tuple[int, int]:
        if int(payload.get("version", 0)) != 1:
            raise ValueError("Versão do backup do Google Drive incompatível.")
        raw_records = payload.get("records", [])
        raw_summaries = payload.get("summaries", [])
        if not isinstance(raw_records, list) or not isinstance(raw_summaries, list):
            raise ValueError("Backup do Google Drive inválido.")
        try:
            records = [WarpRecord(**item) for item in raw_records if isinstance(item, dict)]
            summaries = [
                WarpSummary(**item) for item in raw_summaries if isinstance(item, dict)
            ]
        except (TypeError, ValueError) as error:
            raise ValueError("Backup do Google Drive inválido.") from error
        added = self.add_records(records, owner_id)
        for summary in summaries:
            self.upsert_summary(summary, owner_id)
        planner = payload.get("planner")
        if isinstance(planner, dict):
            self.save_planner_settings(owner_id, planner)
        return added, len(records)

    def planner_settings(self, owner_id: int) -> dict[str, Any]:
        connection = self.connect()
        try:
            row = connection.execute(
                "SELECT jades, passes, starlight, refund, strategy, goal_sequence, "
                "daily_jades, target_date FROM planner_settings "
                "WHERE owner_id = ?",
                (owner_id,),
            ).fetchone()
        finally:
            connection.close()
        return dict(row) if row else {
            "jades": 0, "passes": 0, "starlight": 0,
            "refund": "average", "strategy": "E2",
            "goal_sequence": "E0,S1,E1", "daily_jades": 60,
            "target_date": "",
        }

    def save_planner_settings(self, owner_id: int, settings: dict[str, Any]) -> None:
        refund = str(settings.get("refund", "average"))
        if refund not in {"none", "low", "average", "high"}:
            refund = "average"
        strategy = str(settings.get("strategy", "E2"))
        if strategy not in {"S1", "E0", "E1", "E2", "E3", "E4", "E5", "E6"}:
            strategy = "E2"
        values = (
            max(0, int(settings.get("jades", 0))),
            max(0, int(settings.get("passes", 0))),
            max(0, int(settings.get("starlight", 0))),
            refund,
            strategy,
            str(settings.get("goal_sequence", "E0,S1,E1"))[:80],
            max(0, int(settings.get("daily_jades", 60))),
            str(settings.get("target_date", ""))[:10],
        )
        connection = self.connect()
        try:
            connection.execute(
                """
                INSERT INTO planner_settings(
                    owner_id, jades, passes, starlight, refund, strategy,
                    goal_sequence, daily_jades, target_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_id) DO UPDATE SET
                    jades = excluded.jades, passes = excluded.passes,
                    starlight = excluded.starlight, refund = excluded.refund,
                    strategy = excluded.strategy,
                    goal_sequence = excluded.goal_sequence,
                    daily_jades = excluded.daily_jades,
                    target_date = excluded.target_date
                """,
                (owner_id, *values),
            )
            connection.commit()
        finally:
            connection.close()
