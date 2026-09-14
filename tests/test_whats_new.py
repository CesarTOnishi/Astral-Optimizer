import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QPushButton

from app.config import APP_VERSION
from app.ui.whats_new import ARTWORK_PATHS, FeatureArtwork, WhatsNewPanel
from app.whats_new import CURRENT_RELEASE, WhatsNewSettings


class WhatsNewSettingsTests(unittest.TestCase):
    def test_each_version_is_presented_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(
                str(Path(directory) / "whats-new.ini"),
                QSettings.Format.IniFormat,
            )
            store = WhatsNewSettings(settings)

            self.assertTrue(store.should_show("1.2.1"))
            store.mark_seen("1.2.1")
            self.assertFalse(store.should_show("1.2.1"))
            self.assertTrue(store.should_show("1.2.2"))

    def test_current_release_matches_installed_version(self) -> None:
        self.assertEqual(CURRENT_RELEASE.version, APP_VERSION)
        self.assertGreaterEqual(len(CURRENT_RELEASE.highlights), 4)
        self.assertTrue(all(item.destination for item in CURRENT_RELEASE.highlights))
        self.assertTrue(all(path.is_file() for path in ARTWORK_PATHS.values()))


class WhatsNewPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_cards_have_artwork_and_open_their_resource(self) -> None:
        panel = WhatsNewPanel()
        panel.resize(950, 720)
        panel.show()
        self.app.processEvents()

        self.assertEqual(len(panel.feature_cards), len(CURRENT_RELEASE.highlights))
        self.assertEqual(panel._grid_columns, 2)
        artwork = panel.feature_cards[0].findChild(
            FeatureArtwork, "releaseFeatureArtwork"
        )
        self.assertIsNotNone(artwork)
        self.assertFalse(artwork.source.isNull())

        requested: list[str] = []
        panel.resource_requested.connect(requested.append)
        action = panel.feature_cards[0].findChild(
            QPushButton, "releaseFeatureButton"
        )
        self.assertIsNotNone(action)
        action.click()
        self.assertEqual(requested, [CURRENT_RELEASE.highlights[0].destination])

        panel.resize(760, 720)
        self.app.processEvents()
        self.assertEqual(panel._grid_columns, 1)
        self.assertEqual(
            panel.feature_grid.getItemPosition(1)[:2], (1, 0)
        )
        panel.close()


if __name__ == "__main__":
    unittest.main()
