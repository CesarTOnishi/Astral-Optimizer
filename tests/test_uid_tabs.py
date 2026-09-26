from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.models import AccountSummary, CharacterStat, CharacterSummary, RelicSummary
from app.uid_tabs import (
    MAX_UID_TABS, UidTabLimitError, UidTabSession, UidTabStore, UidTabWorkspace,
)


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

    def test_selection_can_wait_for_ui_animation_before_persisting(self) -> None:
        workspace = UidTabWorkspace(self.store, owner_id=2)
        first, _ = workspace.open("700000001")
        second, _ = workspace.open("700000002")
        self.assertTrue(workspace.select(first.uid, persist=False))
        self.assertEqual(workspace.selected_uid, first.uid)
        self.assertEqual(
            UidTabWorkspace(self.store, owner_id=2).selected_uid, second.uid
        )
        workspace.persist()
        self.assertEqual(
            UidTabWorkspace(self.store, owner_id=2).selected_uid, first.uid
        )

    def test_profiles_are_isolated_and_close_deletes_uid_cache(self) -> None:
        first_profile = UidTabWorkspace(self.store, owner_id=1)
        session, _ = first_profile.open("800000001")
        token = first_profile.begin_request(session.uid)
        first_profile.complete_request(session.uid, token, sample_account(session.uid))
        first_profile.close(session.uid)

        restored = UidTabWorkspace(self.store, owner_id=1)
        self.assertEqual(len(restored.sessions), 0)
        cached, _updated_at = self.store.load_account(1, session.uid)
        self.assertIsNone(cached)
        other_profile = UidTabWorkspace(self.store, owner_id=9)
        self.assertEqual(len(other_profile.sessions), 0)
        self.assertEqual(self.store.load_account(9, session.uid), (None, ""))

    def test_eight_tabs_limit_keeps_existing_tabs_selectable(self) -> None:
        workspace = UidTabWorkspace(self.store, owner_id=2)
        for index in range(MAX_UID_TABS):
            workspace.open(f"70000000{index}")
        selected_before = workspace.selected_uid
        with self.assertRaisesRegex(UidTabLimitError, "8 abas"):
            workspace.open("799999999")
        self.assertEqual(len(workspace.sessions), MAX_UID_TABS)
        self.assertEqual(workspace.selected_uid, selected_before)
        existing, created = workspace.open("700000000")
        self.assertFalse(created)
        self.assertEqual(existing.uid, workspace.selected_uid)
        workspace.close("700000000")
        new_session, created = workspace.open("799999999")
        self.assertTrue(created)
        self.assertEqual(new_session.uid, "799999999")

    def test_restoring_old_workspace_trims_excess_and_keeps_selected(self) -> None:
        sessions = []
        for index in range(MAX_UID_TABS + 2):
            uid = f"7000000{index:02d}"
            # Legacy data may contain more tabs than the new limit.
            sessions.append(UidTabSession(uid=uid))
            self.store.save_account(3, sample_account(uid))
        self.store.save_tabs(3, sessions, sessions[-1].uid)
        restored = UidTabWorkspace(self.store, owner_id=3)
        self.assertEqual(len(restored.sessions), MAX_UID_TABS)
        self.assertEqual(restored.selected_uid, sessions[-1].uid)
        self.assertIn(sessions[-1].uid, restored.sessions)
        self.assertEqual(self.store.load_account(3, sessions[-2].uid), (None, ""))
        self.assertEqual(len(UidTabWorkspace(self.store, owner_id=3).sessions), MAX_UID_TABS)

    def test_restore_prunes_closed_legacy_uid_only_for_current_profile(self) -> None:
        self.store.save_account(1, sample_account("701000001"))
        self.store.save_account(2, sample_account("701000001"))
        UidTabWorkspace(self.store, owner_id=1)
        self.assertEqual(self.store.load_account(1, "701000001"), (None, ""))
        self.assertIsNotNone(self.store.load_account(2, "701000001")[0])

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
