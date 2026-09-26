import tempfile
import unittest
import sqlite3
from pathlib import Path

from app.build_history import BuildHistoryDatabase
from app.ui.build_history import delta_kind, team_mode


def payload(score: float) -> dict[str, object]:
    return {
        "benchmark": {"score": score, "grade": "SS"},
        "stats": [{"key": "Attack", "value": 3000.0}],
    }


class BuildHistoryDatabaseTests(unittest.TestCase):
    def test_team_mode_and_delta_colors_are_classified(self) -> None:
        self.assertEqual(team_mode({"team": {"custom": False}}), "Padrão")
        self.assertEqual(team_mode({"team": {"custom": True}}), "Customizado")
        self.assertEqual(delta_kind(12.5), "gain")
        self.assertEqual(delta_kind(-0.1), "loss")
        self.assertEqual(delta_kind(0.0), "equal")

    def test_saves_lists_and_deletes_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = BuildHistoryDatabase(Path(directory) / "history.db")
            first = database.save(7, "600000001", "1505", "Evanescia", payload(120))
            second = database.save(7, "600000001", "1505", "Evanescia", payload(125))

            snapshots = database.snapshots(7, "600000001", "1505")
            self.assertEqual([item.id for item in snapshots], [second.id, first.id])
            self.assertEqual(snapshots[0].benchmark_score, 125)
            self.assertTrue(database.delete(7, first.id))
            self.assertEqual(len(database.snapshots(7, "600000001", "1505")), 1)

    def test_prunes_oldest_unfavorited_at_default_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = BuildHistoryDatabase(Path(directory) / "history.db")
            ids = []
            for index in range(5):
                saved = database.save(2, "600000001", "1505", "Evanescia", payload(index))
                ids.append(saved.id)
            database.update_metadata(2, ids[0], name="Primeira", note="Teste", favorite=True)
            newest = database.save(2, "600000001", "1505", "Evanescia", payload(6))
            result = database.snapshots(2, "600000001", "1505")
            self.assertEqual(len(result), 5)
            self.assertIn(ids[0], [item.id for item in result])
            self.assertNotIn(ids[1], [item.id for item in result])
            self.assertEqual(result[0].id, newest.id)
            self.assertEqual(result[-1].name, "Primeira")
            self.assertEqual(result[-1].note, "Teste")
            self.assertTrue(result[-1].favorite)

            # Outro personagem mantém seu próprio limite.
            database.save(2, "600000001", "1220", "Feixiao", payload(100))
            self.assertEqual(len(database.snapshots(2, "600000001", "1220")), 1)

    def test_limit_is_per_profile_and_favorites_block_automatic_pruning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = BuildHistoryDatabase(Path(directory) / "history.db")
            database.set_retention_limit(2, 2)
            self.assertEqual(database.retention_limit(2), 2)
            self.assertEqual(database.retention_limit(3), 5)
            first = database.save(2, "1", "a", "A", payload(1), favorite=True)
            second = database.save(2, "1", "a", "A", payload(2), favorite=True)
            with self.assertRaisesRegex(ValueError, "favoritas"):
                database.save(2, "1", "a", "A", payload(3))
            self.assertEqual([item.id for item in database.snapshots(2, "1", "a")],
                             [second.id, first.id])
            database.update_metadata(2, first.id, name="Livre", note="OK", favorite=False)
            database.save(2, "1", "a", "A", payload(3))
            self.assertEqual(len(database.snapshots(2, "1", "a")), 2)
            with self.assertRaises(ValueError):
                database.set_retention_limit(2, 0)

    def test_migrates_existing_schema_without_losing_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE build_snapshots (id INTEGER PRIMARY KEY, "
                               "owner_id INTEGER, uid TEXT, character_id TEXT, "
                               "character_name TEXT, payload_json TEXT, created_at TEXT)")
            connection.execute("INSERT INTO build_snapshots VALUES "
                               "(1, 2, '1', 'a', 'A', '{}', '2025-01-01')")
            connection.commit()
            connection.close()
            database = BuildHistoryDatabase(path)
            old = database.snapshots(2, "1", "a")[0]
            self.assertEqual((old.name, old.note, old.favorite), ("", "", False))
            self.assertTrue(database.update_metadata(2, old.id, name="Antiga",
                                                     note="Preservada", favorite=True))
            self.assertEqual(database.snapshots(2, "1", "a")[0].name, "Antiga")

    def test_does_not_mix_users_or_uids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = BuildHistoryDatabase(Path(directory) / "history.db")
            database.save(1, "600000001", "1505", "Evanescia", payload(100))
            self.assertEqual(database.snapshots(2, "600000001", "1505"), [])
            self.assertEqual(database.snapshots(1, "600000002", "1505"), [])


if __name__ == "__main__":
    unittest.main()
