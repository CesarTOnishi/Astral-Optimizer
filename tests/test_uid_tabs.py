from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.models import AccountSummary, CharacterStat, CharacterSummary, RelicSummary
from app.uid_tabs import UidTabStore, UidTabWorkspace


def sample_account(uid: str, nickname: str = "Trailblazer") -> AccountSummary:
    stat = CharacterStat("Attack", "ATQ", 1234.0, "1234", False)
    relic = RelicSummary(
        "Corpo", "Mensageira", 15, 5, "relic.png", stat, [stat], "BODY"
    )
    character = CharacterSummary(
        "Março 7th", "1001", 80, 2, "Memórias", 80, 1,
        "cone.png", 1, 4, "Ice", "Preservation", "icon.png", "splash.png",
        [stat], [relic], {"fribbels_payload": {"avatarId": "1001"}},
    )
    return AccountSummary(
        uid, nickname, 70, 6, "Olá", "avatar.png", [character], 60, 777
    )


class UidTabPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.store = UidTabStore(Path(self.directory.name) / "uid_tabs.db")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_restores_order_selected_tab_state_and_cached_account(self) -> None:
        workspace = UidTabWorkspace(self.store, owner_id=4)
        first, _ = workspace.open("600000001")
        second, _ = workspace.open("600000002")
        token = workspace.begin_request(first.uid)
        self.assertTrue(
            workspace.complete_request(first.uid, token, sample_account(first.uid, "Asta"))
        )
        first.selected_character_id = "1001"
        first.scroll_position = 428
        workspace.reorder([second.uid, first.uid])
        workspace.select(first.uid)
        workspace.persist()

        restored = UidTabWorkspace(self.store, owner_id=4)
        self.assertEqual(list(restored.sessions), [second.uid, first.uid])
        self.assertEqual(restored.selected_uid, first.uid)
        self.assertEqual(restored.sessions[first.uid].selected_character_id, "1001")
        self.assertEqual(restored.sessions[first.uid].scroll_position, 428)
        self.assertEqual(restored.sessions[first.uid].account.nickname, "Asta")
        self.assertEqual(restored.sessions[first.uid].account.characters[0].relics[0].level, 15)

    def test_duplicate_uid_selects_existing_tab(self) -> None:
        workspace = UidTabWorkspace(self.store, owner_id=2)
        original, created = workspace.open("700000001")
        duplicate, created_again = workspace.open("700000001")
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertIs(duplicate, original)
        self.assertEqual(len(workspace.sessions), 1)
        self.assertEqual(workspace.selected_uid, original.uid)

    def test_profiles_are_isolated_and_close_keeps_cache(self) -> None:
        first_profile = UidTabWorkspace(self.store, owner_id=1)
        session, _ = first_profile.open("800000001")
        token = first_profile.begin_request(session.uid)
        first_profile.complete_request(session.uid, token, sample_account(session.uid))
        first_profile.close(session.uid)

        restored = UidTabWorkspace(self.store, owner_id=1)
        self.assertEqual(len(restored.sessions), 0)
        cached, _updated_at = self.store.load_account(1, session.uid)
        self.assertIsNotNone(cached)
        other_profile = UidTabWorkspace(self.store, owner_id=9)
        self.assertEqual(len(other_profile.sessions), 0)
        self.assertEqual(self.store.load_account(9, session.uid), (None, ""))

    def test_late_or_wrong_async_response_is_rejected(self) -> None:
        workspace = UidTabWorkspace(self.store, owner_id=3)
        first, _ = workspace.open("900000001")
        old_token = workspace.begin_request(first.uid)
        workspace.close(first.uid)
        reopened, _ = workspace.open(first.uid)
        new_token = workspace.begin_request(reopened.uid)
        second, _ = workspace.open("900000002")
        workspace.select(second.uid)

        self.assertFalse(
            workspace.complete_request(first.uid, old_token, sample_account(first.uid, "Antigo"))
        )
        self.assertFalse(
            workspace.complete_request(first.uid, new_token, sample_account("999999999"))
        )
        self.assertTrue(
            workspace.complete_request(first.uid, new_token, sample_account(first.uid, "Novo"))
        )
        self.assertEqual(workspace.selected_uid, second.uid)
        self.assertEqual(workspace.sessions[first.uid].account.nickname, "Novo")

    def test_corrupted_cached_json_is_ignored(self) -> None:
        connection = self.store.connect()
        try:
            connection.execute(
                """
                INSERT INTO uid_account_cache(owner_id, uid, payload_json, updated_at)
                VALUES (1, '600000009', '{broken', '2026-09-24T10:00:00+00:00')
                """
            )
            connection.commit()
        finally:
            connection.close()
        self.assertEqual(self.store.load_account(1, "600000009"), (None, ""))

    def test_corrupted_database_is_preserved_and_recreated(self) -> None:
        path = Path(self.directory.name) / "broken.db"
        path.write_bytes(b"not a sqlite database")
        recovered = UidTabStore(path)
        self.assertEqual(recovered.load_tabs(1), ([], ""))
        self.assertEqual(len(list(path.parent.glob("broken.db.corrupt-*"))), 1)


if __name__ == "__main__":
    unittest.main()
