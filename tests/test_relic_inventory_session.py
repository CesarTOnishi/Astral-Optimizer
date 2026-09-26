import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.auth import AuthUser
from app.models import CharacterStat, RelicSummary
from app.relics import StoredRelic
from app.ui.relic_inventory_panel import RelicInventoryPanel


def stored_relic(uid: str, fingerprint: str) -> StoredRelic:
    stat = CharacterStat("Attack", "ATQ", 352.0, "352", False)
    relic = RelicSummary(
        "Mãos", "Conjunto de teste", 15, 5, "", stat, [stat], "HAND"
    )
    return StoredRelic(fingerprint, uid, relic, 71.2, "SS")


class CountingDatabase:
    def __init__(self) -> None:
        self.calls = 0
        self.data: dict[tuple[int, str], list[StoredRelic]] = {}

    def relics(self, owner_id: int, uid: str) -> list[StoredRelic]:
        self.calls += 1
        return list(self.data.get((owner_id, uid), []))


class NoImages:
    def load(self, *_args) -> None:
        pass


class RelicInventorySessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_reopening_reuses_cards_until_data_or_profile_changes(self) -> None:
        database = CountingDatabase()
        first_user = AuthUser(1, "primeiro", "first@example.com", "601000001")
        second_user = AuthUser(2, "segundo", "second@example.com", "602000002")
        database.data[(1, first_user.game_uid)] = [
            stored_relic(first_user.game_uid, "first")
        ]
        database.data[(2, second_user.game_uid)] = [
            stored_relic(second_user.game_uid, "other")
        ]
        panel = RelicInventoryPanel(database, NoImages())
        try:
            panel.set_user(first_user)
            panel.set_active(True)
            self.assertEqual(database.calls, 1)
            self.assertTrue(panel.has_cached_view)
            panel.sort_filter.setCurrentIndex(1)
            first_card = panel.cards[0]

            panel.set_active(False)
            panel.set_active(True)
            panel.set_user(first_user)
            self.assertEqual(database.calls, 1)
            self.assertIs(panel.cards[0], first_card)
            self.assertEqual(panel.sort_filter.currentIndex(), 1)

            panel.set_active(False)
            database.data[(1, first_user.game_uid)].append(
                stored_relic(first_user.game_uid, "new")
            )
            panel.mark_dirty()
            self.assertFalse(panel.has_cached_view)
            panel.set_active(True)
            self.assertEqual(database.calls, 2)
            self.assertEqual(len(panel.cards), 2)
            self.assertIsNot(panel.cards[0], first_card)

            panel.set_user(second_user)
            self.assertEqual(database.calls, 3)
            self.assertEqual(len(panel.cards), 1)
            self.assertEqual(panel.items[0].uid, second_user.game_uid)
        finally:
            panel.close()


if __name__ == "__main__":
    unittest.main()
