from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from app.config import APP_STYLESHEET
from app.ui.contextual_help import (
    BANNER_EDITION_HELP,
    BENCHMARK_HELP,
    BUILD_SOURCE_HELP,
    GUARANTEE_HELP,
    PITY_HELP,
    RATE_UP_HELP,
    RELIC_GRADE_HELP,
    ContextHelpButton,
    ContextHelpPopup,
)


class ContextualHelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_all_requested_topics_have_content(self) -> None:
        topics = (
            PITY_HELP,
            GUARANTEE_HELP,
            RATE_UP_HELP,
            RELIC_GRADE_HELP,
            BENCHMARK_HELP,
            BANNER_EDITION_HELP,
            BUILD_SOURCE_HELP,
        )
        self.assertEqual(len(topics), 7)
        self.assertTrue(all(title and len(text) > 80 for title, text in topics))

    def test_help_button_builds_compact_readable_popup(self) -> None:
        previous_style = self.app.styleSheet()
        self.app.setStyleSheet(APP_STYLESHEET)
        try:
            button = ContextHelpButton(*PITY_HELP)
            popup = ContextHelpPopup(*PITY_HELP, button)
            popup.adjustSize()
            labels = [label.text() for label in popup.findChildren(QLabel)]
            self.assertIn(PITY_HELP[0], labels)
            self.assertIn(PITY_HELP[1], labels)
            self.assertLess(popup.height(), 240)
            self.assertTrue(button.icon().isNull() is False)
            popup.deleteLater()
            button.deleteLater()
        finally:
            self.app.setStyleSheet(previous_style)


if __name__ == "__main__":
    unittest.main()
