from pathlib import Path
import sqlite3
import tempfile
import unittest

from app.warp.database import WarpDatabase
from app.warp.importer import extract_warp_url
from app.warp.models import WarpRecord, WarpSummary
from app.warp.starrailstation import (
    MAX_XLSX_SIZE,
    _featured_name_for_record,
    import_starrailstation_xlsx,
)
from app.warp.statistics import (
    STANDARD_CHARACTER_IDS,
    classify_five_star_history,
    five_star_history,
    pity_state,
)


def warp(
    record_id: int,
    rank: int,
    item_id: str = "1001",
    gacha_type: str = "11",
    uid: str = "600000001",
) -> WarpRecord:
    return WarpRecord(
        id=str(record_id),
        uid=uid,
        gacha_type=gacha_type,
        item_id=item_id,
        name=f"Item {record_id}",
        item_type="Character",
        rank_type=rank,
        time=f"2026-01-01 00:{record_id:02d}:00",
    )


class WarpTests(unittest.TestCase):
    def test_rejects_xlsx_larger_than_five_megabytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large-backup.xlsx"
            with path.open("wb") as output:
                output.seek(MAX_XLSX_SIZE)
                output.write(b"\0")
            with self.assertRaisesRegex(ValueError, "limite de 5 MB"):
                import_starrailstation_xlsx(path, "600000001")

    def test_exports_and_restores_owner_cloud_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = WarpDatabase(Path(directory) / "source.db")
            target = WarpDatabase(Path(directory) / "target.db")
            source.add_records([warp(1, 5), warp(2, 3)], owner_id=7)
            summary = WarpSummary(
                uid="600000001", gacha_type="21", total=2,
                five_star_count=1, four_star_count=0,
                five_star_pity=1, four_star_pity=2,
                featured_item_id="1014", featured_item_name="Saber",
                featured_pity=1, featured_item_type="Character",
            )
            source.upsert_summary(summary, owner_id=7)
            source.save_planner_settings(
                7,
                {
                    "jades": 3200,
                    "passes": 10,
                    "starlight": 40,
                    "refund": "high",
                    "strategy": "E4",
                },
            )
            payload = source.export_owner(7)
            added, total = target.restore_owner(payload, owner_id=12)
            self.assertEqual((added, total), (2, 2))
            self.assertEqual(len(target.records("600000001", owner_id=12)), 2)
            self.assertEqual(
                target.summaries("600000001", owner_id=12)["21"], summary
            )
            self.assertEqual(target.planner_settings(12)["jades"], 3200)
            self.assertEqual(target.planner_settings(12)["refund"], "high")
            self.assertEqual(target.planner_settings(12)["strategy"], "E4")

    def test_resolves_reused_light_cone_banner_by_date_and_pulled_item(self) -> None:
        banners = {
            "Fixação Brilhante": [
                (100.0, 120.0, "Cone A"),
                (200.0, 220.0, "Cone B"),
                (200.0, 220.0, "Cone C"),
            ]
        }
        self.assertEqual(
            _featured_name_for_record(
                banners, "Fixação Brilhante", "Cone C", 5, 210.0
            ),
            "Cone C",
        )
        self.assertEqual(
            _featured_name_for_record(
                banners, "Fixação Brilhante", "Cone B", 5, 210.0
            ),
            "Cone B",
        )

    def test_stores_fate_summary_separately_from_detailed_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            summary = WarpSummary(
                uid="600000001", gacha_type="21", total=95,
                five_star_count=1, four_star_count=11,
                five_star_pity=19, four_star_pity=5,
                featured_item_id="1014", featured_item_name="Saber",
                featured_pity=76, featured_item_type="Character",
            )
            database.upsert_summary(summary, owner_id=1)
            self.assertEqual(database.records("600000001", owner_id=1), [])
            self.assertEqual(database.summaries("600000001", owner_id=1)["21"], summary)

    def test_extracts_authenticated_url_from_binary_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data_2"
            path.write_bytes(
                b"cache\x00https://example.test/getGachaLog?authkey=abc%2F123"
                b"\\u0026game_biz=hkrpg_global\x00end"
            )
            url = extract_warp_url(path)
        self.assertIn("authkey=abc%2F123", url)
        self.assertIn("game_biz=hkrpg_global", url)

    def test_database_deduplicates_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            records = [warp(1, 3), warp(2, 4)]
            self.assertEqual(database.add_records(records), 2)
            self.assertEqual(database.add_records(records), 0)
            self.assertEqual(len(database.records("600000001")), 2)

    def test_histories_are_isolated_by_profile_and_uid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            first_uid = [warp(1, 5)]
            second_uid = [warp(2, 5, uid="700000002")]
            self.assertEqual(database.add_records(first_uid, owner_id=10), 1)
            self.assertEqual(database.add_records(first_uid, owner_id=20), 1)
            self.assertEqual(database.add_records(second_uid, owner_id=10), 1)
            self.assertEqual(len(database.records("600000001", owner_id=10)), 1)
            self.assertEqual(len(database.records("600000001", owner_id=20)), 1)
            self.assertEqual(database.uids(owner_id=10), ["700000002", "600000001"])
            self.assertEqual(database.uids(owner_id=20), ["600000001"])

    def test_migrates_previous_global_history_without_losing_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "warps.db"
            connection = sqlite3.connect(path)
            connection.execute(
                """
                CREATE TABLE warps (
                    uid TEXT NOT NULL, id TEXT NOT NULL, gacha_type TEXT NOT NULL,
                    item_id TEXT NOT NULL, name TEXT NOT NULL, item_type TEXT NOT NULL,
                    rank_type INTEGER NOT NULL, time TEXT NOT NULL,
                    PRIMARY KEY (uid, id)
                )
                """
            )
            record = warp(1, 5)
            connection.execute(
                "INSERT INTO warps VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.uid, record.id, record.gacha_type, record.item_id,
                    record.name, record.item_type, record.rank_type, record.time,
                ),
            )
            connection.commit()
            connection.close()

            database = WarpDatabase(path)
            self.assertEqual(len(database.records("600000001", owner_id=0)), 1)
            self.assertEqual(database.records("600000001", owner_id=1), [])

    def test_pity_and_guarantee(self) -> None:
        records = [warp(index, 3) for index in range(1, 31)]
        records.append(warp(31, 5, "1003"))
        records.extend(warp(index, 3) for index in range(32, 39))
        state = pity_state(records, {"11"}, STANDARD_CHARACTER_IDS)
        self.assertEqual(state.five_star, 7)
        self.assertTrue(state.guaranteed)
        history = five_star_history(records)
        self.assertEqual(history[0][1], 31)

    def test_five_star_does_not_reset_four_star_pity(self) -> None:
        records = [warp(index, 3) for index in range(1, 10)]
        records.append(warp(10, 5, "1014"))
        state = pity_state(records, {"11"}, STANDARD_CHARACTER_IDS)
        self.assertEqual(state.four_star, 10)

    def test_classifies_lost_guaranteed_and_won_five_stars(self) -> None:
        records = [warp(1, 5, "1107"), warp(2, 5, "1409"), warp(3, 5, "1403")]
        outcomes = classify_five_star_history(
            five_star_history(records), STANDARD_CHARACTER_IDS, "50/50"
        )
        chronological = list(reversed(outcomes))
        self.assertEqual(
            [item.outcome for item in chronological],
            ["lost", "guaranteed", "won"],
        )

    def test_fate_and_regular_banners_have_separate_pity(self) -> None:
        regular = [warp(index, 3, gacha_type="11") for index in range(1, 11)]
        fate = [warp(100 + index, 3, gacha_type="21") for index in range(1, 6)]
        records = regular + fate
        self.assertEqual(pity_state(records, {"11"}).five_star, 10)
        self.assertEqual(pity_state(records, {"21"}).five_star, 5)


if __name__ == "__main__":
    unittest.main()
