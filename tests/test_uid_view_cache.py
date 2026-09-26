import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from tests.test_uid_tabs import sample_account


class UidViewCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_portraits_survive_tab_switch_and_refresh_invalidates_them(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ):
            window = MainWindow()
            try:
                self.assertEqual(window.character_list_stack.height(), 84)
                self.assertLessEqual(window.selector_panel.sizeHint().height(), 100)
                first = sample_account("601000001", "Primeira")
                second = sample_account("602000002", "Segunda")
                for account in (first, second):
                    session, _created = window.uid_workspace.open(account.uid)
                    session.account = account

                window.active_uid_tab = first.uid
                self.assertFalse(window._use_character_list(first))
                first_listing = window.character_list
                first_listing.addItem("Retrato pronto")

                window.active_uid_tab = second.uid
                self.assertFalse(window._use_character_list(second))
                window.active_uid_tab = first.uid
                self.assertTrue(window._use_character_list(first))
                self.assertIs(window.character_list, first_listing)
                self.assertEqual(first_listing.count(), 1)

                icon = QPixmap(1, 1)
                with patch.object(window.image_loader, "load", side_effect=lambda _url, callback: callback(icon)) as load_icon, patch.object(
                    window.benchmark_engine, "rate_relic", wraps=window.benchmark_engine.rate_relic
                ) as rate_relic:
                    for account in (first, second, first):
                        window.active_uid_tab = account.uid
                        window.current_account = account
                        window.current_character_id = account.characters[0].avatar_id
                        context = window.section_loading.begin_context(
                            window.uid_workspace.owner_id, account.uid
                        )
                        window._display_stats(account.characters[0])
                        window._display_relics(account.characters[0], context=context)
                        if account is first and rate_relic.call_count == 1:
                            first_card = window.current_relic_cards[0]
                            first_stat = window.stat_rows.itemAt(0).widget()
                    self.assertEqual(rate_relic.call_count, 2)
                    self.assertEqual(load_icon.call_count, 2)
                    self.assertIs(window.current_relic_cards[0], first_card)
                    self.assertIs(window.stat_rows.itemAt(0).widget(), first_stat)

                refreshed = sample_account(first.uid, "Atualizada")
                window.uid_workspace.sessions[first.uid].account = refreshed
                self.assertFalse(window._use_character_list(refreshed))
                self.assertIs(window.character_list, first_listing)
                self.assertEqual(first_listing.count(), 0)
                window.current_account = refreshed
                window._display_stats(refreshed.characters[0])
                self.assertIsNot(window.stat_rows.itemAt(0).widget(), first_stat)
                context = window.section_loading.begin_context(
                    window.uid_workspace.owner_id, refreshed.uid
                )
                with patch.object(window.image_loader, "load", side_effect=lambda _url, callback: callback(icon)):
                    window._display_relics(refreshed.characters[0], context=context)
                self.assertIsNot(window.current_relic_cards[0], first_card)

                window.benchmark_results = {"1001": object()}
                window._reuse_session_benchmark = True
                with patch.object(window.benchmark_engine, "analyze") as analyze, patch.object(
                    window, "_render_benchmark"
                ) as render, patch.object(window.section_loading, "ready"):
                    window._display_benchmark(refreshed.characters[0])
                analyze.assert_not_called()
                render.assert_called_once()
            finally:
                window.close()

    def test_closing_last_uid_releases_visible_widgets_and_saved_snapshot(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ):
            window = MainWindow()
            try:
                account = sample_account("601000003", "Fechada")
                session, _created = window.uid_workspace.open(account.uid)
                token = window.uid_workspace.begin_request(account.uid)
                self.assertTrue(
                    window.uid_workspace.complete_request(account.uid, token, account)
                )
                window.uid_tabs_widget.add_or_update(account.uid, session.title)
                window.active_uid_tab = account.uid
                window.build_source = "manual"
                window.current_account = account
                window.current_uid = account.uid
                window.current_character_id = account.characters[0].avatar_id
                window._use_character_list(account)
                context = window.section_loading.begin_context(
                    window.uid_workspace.owner_id, account.uid
                )
                with patch.object(
                    window.image_loader, "load",
                    side_effect=lambda _url, callback: callback(QPixmap(1, 1)),
                ):
                    window._display_stats(account.characters[0])
                    window._display_relics(account.characters[0], context=context)
                self.assertTrue(window.current_relic_cards)

                window._close_uid_tab(account.uid)

                self.assertEqual(window.uid_tabs_widget.tabs.count(), 0)
                self.assertEqual(window.current_relic_cards, [])
                self.assertEqual(window.relic_grid.count(), 0)
                self.assertEqual(window.stat_rows.count(), 0)
                self.assertIsNone(window.current_account)
                self.assertEqual(window.uid_workspace.store.load_account(
                    window.uid_workspace.owner_id, account.uid
                ), (None, ""))
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
