import tempfile
import unittest
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

    def test_enforces_five_build_limit_per_character(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = BuildHistoryDatabase(Path(directory) / "history.db")
            for index in range(5):
                database.save(2, "600000001", "1505", "Evanescia", payload(index))
            with self.assertRaisesRegex(ValueError, "limite é de 5"):
                database.save(2, "600000001", "1505", "Evanescia", payload(6))

            # Outro personagem mantém seu próprio limite.
            database.save(2, "600000001", "1220", "Feixiao", payload(100))
            self.assertEqual(len(database.snapshots(2, "600000001", "1220")), 1)

    def test_does_not_mix_users_or_uids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = BuildHistoryDatabase(Path(directory) / "history.db")
            database.save(1, "600000001", "1505", "Evanescia", payload(100))
            self.assertEqual(database.snapshots(2, "600000001", "1505"), [])
            self.assertEqual(database.snapshots(1, "600000002", "1505"), [])


if __name__ == "__main__":
    unittest.main()
