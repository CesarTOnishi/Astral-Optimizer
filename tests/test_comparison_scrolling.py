import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QScrollArea, QVBoxLayout, QWidget

from app.benchmark.models import UpgradeComparison
from app.config import APP_STYLESHEET
from app.ui.widgets import UpgradeComparisonTable


class ComparisonScrollingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_both_comparisons_show_all_rows_and_wheel_scrolls_page(self):
        for main_stat in (False, True):
            with self.subTest(main_stat=main_stat):
                page = QScrollArea()
                page.setWidgetResizable(True)
                content = QWidget()
                layout = QVBoxLayout(content)
                table = UpgradeComparisonTable(show_part_icon=main_stat)
                comparisons = [UpgradeComparison(
                    "Attack", "ATQ", "+1", 1.2, 112.3,
                    part_key="Body" if main_stat else "",
                ) for _ in range(16)]
                table.set_comparisons(comparisons)
                layout.addWidget(table)
                page.setWidget(content)
                page.setStyleSheet(APP_STYLESHEET)
                page.resize(760, 420)
                page.show()
                try:
                    for _ in range(5):
                        self.app.processEvents()
                    self.assertEqual(table.table.verticalScrollBar().maximum(), 0)
                    self.assertEqual(table.table.horizontalScrollBar().maximum(), 0)
                    self.assertGreater(page.verticalScrollBar().maximum(), 0)
                    wheel = QWheelEvent(
                        QPointF(100, 100), QPointF(100, 100), QPoint(), QPoint(0, -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.ScrollUpdate, False,
                    )
                    QApplication.sendEvent(table.table.viewport(), wheel)
                    self.app.processEvents()
                    self.assertGreater(page.verticalScrollBar().value(), 0)
                finally:
                    page.close()
                    page.deleteLater()
