from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QSettings

from app.ui.warp_panel import WarpPanel
from app.ui.warp_import_tutorial import VIDEO_PATH
from app.warp.cache_settings import (
    import_tutorial_seen,
    set_import_tutorial_seen,
    set_webcaches_path,
    webcaches_path,
)
from app.warp.importer import find_latest_cache, latest_cache_candidates


def _data_2(root: Path, version: str) -> Path:
    path = root / version / "Cache" / "Cache_Data" / "data_2"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"cache")
    return path


class WarpCacheSettingsTests(unittest.TestCase):
    def test_tutorial_video_is_bundled_with_application_assets(self) -> None:
        self.assertTrue(VIDEO_PATH.is_file())
        self.assertGreater(VIDEO_PATH.stat().st_size, 1_000_000)

    def test_selected_webcaches_folder_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "webCaches"
            root.mkdir()
            settings = QSettings(
                str(Path(directory) / "warp-import.ini"),
                QSettings.Format.IniFormat,
            )

            set_webcaches_path(root, settings)
            self.assertEqual(webcaches_path(settings), root.resolve())
            set_webcaches_path(None, settings)
            self.assertIsNone(webcaches_path(settings))

    def test_highest_version_is_preferred_even_when_older_version_changed_later(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "webCaches"
            older = _data_2(root, "2.9.0.0")
            newest = _data_2(root, "2.10.0.0")
            older.touch()

            candidates = latest_cache_candidates(root)

            self.assertEqual(candidates, [newest, older])

    def test_version_folder_can_also_be_selected_directly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            version_root = Path(directory) / "webCaches" / "2.10.0.0"
            cache = _data_2(version_root.parent, version_root.name)

            self.assertEqual(latest_cache_candidates(version_root), [cache])

    def test_locator_follows_webcaches_to_cache_data_2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "webCaches"
            expected = _data_2(root, "2.42.0.0")

            self.assertEqual(find_latest_cache((root,)), expected)

    def test_import_tutorial_is_persisted_per_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(
                str(Path(directory) / "warp-import.ini"),
                QSettings.Format.IniFormat,
            )
            self.assertFalse(import_tutorial_seen(4, settings))
            set_import_tutorial_seen(4, settings=settings)
            self.assertTrue(import_tutorial_seen(4, settings))
            self.assertFalse(import_tutorial_seen(5, settings))

    @patch("app.ui.warp_panel.set_import_tutorial_seen")
    @patch("app.ui.warp_panel.WarpImportTutorialDialog")
    @patch("app.ui.warp_panel.import_tutorial_seen", return_value=False)
    def test_first_automatic_import_opens_tutorial_without_starting(
        self,
        _seen: Mock,
        dialog_class: Mock,
        save_seen: Mock,
    ) -> None:
        panel = Mock(owner_id=7)
        panel._show_import_tutorial = lambda: (
            WarpPanel._show_import_tutorial(panel)
        )
        dialog_class.return_value.exec.return_value = 1

        WarpPanel.import_automatically(panel)

        dialog_class.assert_called_once_with(panel)
        save_seen.assert_called_once_with(7)
        panel._start_import.assert_not_called()

    @patch("app.ui.warp_panel.WarpImportTutorialDialog")
    @patch("app.ui.warp_panel.import_tutorial_seen", return_value=True)
    def test_later_automatic_imports_start_directly(
        self,
        _seen: Mock,
        dialog_class: Mock,
    ) -> None:
        panel = Mock(owner_id=7)

        WarpPanel.import_automatically(panel)

        dialog_class.assert_not_called()
        panel._start_import.assert_called_once_with(None)

    @patch("app.ui.warp_panel.set_import_tutorial_seen")
    @patch("app.ui.warp_panel.WarpImportTutorialDialog")
    @patch("app.ui.warp_panel.import_tutorial_seen", return_value=False)
    def test_cancelled_tutorial_does_not_import_or_mark_as_seen(
        self,
        _seen: Mock,
        dialog_class: Mock,
        save_seen: Mock,
    ) -> None:
        panel = Mock(owner_id=7)
        panel._show_import_tutorial = lambda: (
            WarpPanel._show_import_tutorial(panel)
        )
        dialog_class.return_value.exec.return_value = 0

        WarpPanel.import_automatically(panel)

        panel._start_import.assert_not_called()
        save_seen.assert_not_called()

    def test_cache_error_offers_tutorial_again(self) -> None:
        panel = Mock()
        message = (
            "Cache de Saltos não encontrado. Abra o histórico de Saltos no jogo."
        )

        WarpPanel._import_failed(panel, message)

        panel._set_status.assert_called_once_with(
            message,
            "error",
            show_import_tutorial=True,
        )

    @patch("app.ui.warp_panel.QTimer.singleShot")
    def test_starting_import_preserves_scroll_position(
        self,
        single_shot: Mock,
    ) -> None:
        panel = Mock(
            owner_id=7,
            current_uid="",
            current_records=[],
        )
        scroll_bar = panel.page_scroll.verticalScrollBar.return_value
        scroll_bar.value.return_value = 184
        panel.auto_button.hasFocus.return_value = True
        panel.file_button.hasFocus.return_value = False
        single_shot.side_effect = lambda _delay, callback: callback()

        WarpPanel._set_busy(panel, True)

        panel.page_scroll.setFocus.assert_called_once()
        scroll_bar.setValue.assert_called_once_with(184)


if __name__ == "__main__":
    unittest.main()
