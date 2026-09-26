import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMainWindow, QScrollArea

from app.section_loading import SectionLoadController
from app.ui.main_window import MainWindow, build_panel_proportions


class StatsPanelLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_stats_content_scrolls_instead_of_being_clipped(self):
        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window.section_loading = SectionLoadController(window)
        window.section_statuses = {}

        panel = window._build_stats_panel()
        panel.resize(238, 357)
        panel.show()
        self.app.processEvents()

        self.assertIsInstance(window.stats_scroll, QScrollArea)
        self.assertIs(window.stats_scroll.widget(), window.stats_content)
        self.assertGreater(window.stats_scroll.verticalScrollBar().maximum(), 0)
        self.assertEqual(
            window.stats_scroll.horizontalScrollBarPolicy().name,
            "ScrollBarAlwaysOff",
        )

        panel.close()
        window.deleteLater()

    def test_build_columns_reserve_readable_summary_and_relic_space(self):
        self.assertEqual(build_panel_proportions(776), (0.23, 0.31, 0.46))
        self.assertEqual(build_panel_proportions(1000), (0.32, 0.25, 0.43))
        self.assertEqual(build_panel_proportions(1500), (0.38, 0.22, 0.40))
        for width in (776, 1000, 1500):
            self.assertAlmostEqual(sum(build_panel_proportions(width)), 1.0)


if __name__ == "__main__":
    unittest.main()
