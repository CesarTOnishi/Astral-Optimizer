import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from tests.test_uid_tabs import sample_account


class NavigationSessionCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_reopening_pages_keeps_their_views_without_refreshing(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ):
            window = MainWindow()
            try:
                with patch.object(window.warp_panel, "refresh") as warps, patch.object(
                    window.planner_panel, "refresh"
                ) as planner, patch.object(
                    window.friends_panel, "refresh"
                ) as friends, patch.object(
                    window.diagnostics_panel, "refresh"
                ) as diagnostics:
                    for destination in (
                        "Saltos", "Início", "Saltos", "Planejador", "Início",
                        "Planejador", "Amigos", "Início", "Amigos",
                        "Diagnóstico", "Início", "Diagnóstico",
                    ):
                        window._navigate(destination)
                    warps.assert_not_called()
                    planner.assert_not_called()
                    friends.assert_not_called()
                    diagnostics.assert_not_called()

                    # A fresh warp import still updates the planner immediately.
                    window.warp_panel.import_completed.emit(1)
                    planner.assert_called_once_with()

                with patch.object(window.catalog_panel, "synchronize"):
                    window._navigate("Personagens e Cones")
                    self.assertFalse(window.catalog_panel.has_cached_view)
                    window.catalog_panel.set_active(True)
                    self.assertTrue(window.catalog_panel.has_cached_view)
                    window._navigate("Início")
                    with patch.object(window, "_defer_with_loading") as loading:
                        window._navigate("Personagens e Cones")
                    loading.assert_not_called()
                    window.catalog_panel.set_active(False)
                    window.catalog_panel._reset_card_cache()
                    self.assertFalse(window.catalog_panel.has_cached_view)
            finally:
                window.close()

    def test_loaded_uid_does_not_rebuild_when_returning_to_builds(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ):
            window = MainWindow()
            try:
                account = sample_account("601000001", "Perfil salvo")
                session, _created = window.uid_workspace.open(account.uid)
                session.account = account
                window.uid_workspace.select(account.uid, persist=False)
                window.active_uid_tab = account.uid
                window.current_account = account
                window.build_source = session.source
                window._navigate("Início")
                with patch.object(window, "_activate_uid_tab") as activate:
                    window._navigate("Builds")
                activate.assert_not_called()
                self.assertEqual(window.page_stack.currentIndex(), 0)

                session.loading = True
                with patch.object(window, "_activate_uid_tab") as activate:
                    window._navigate("Builds")
                activate.assert_called_once_with(account.uid)
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
