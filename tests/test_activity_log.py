from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from app.activity_log import ActivityLog
from app.ui.activity_history import ActivityHistoryButton


class ActivityLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_persists_events_and_filters_other_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "activity.db"
            log = ActivityLog(path=path)
            log.add("update", "App atualizado", "Versão 1.3.0", kind="success")
            log.add("account", "Conta sincronizada", "UID principal", owner_id=7)
            log.add("account", "Outra conta", "Outro perfil", owner_id=8)

            reopened = ActivityLog(path=path)
            titles = [event.title for event in reopened.events(owner_id=7)]

            self.assertEqual(titles, ["Conta sincronizada", "App atualizado"])
            self.assertNotIn("Outra conta", titles)

    def test_button_builds_rows_from_persisted_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = ActivityLog(path=Path(directory) / "activity.db")
            log.add(
                "warps",
                "Histórico de Saltos importado",
                "87 novos registros.",
                owner_id=3,
                kind="success",
            )
            button = ActivityHistoryButton(log, lambda: 3)
            row = button._event_row(log.events(3)[0])

            texts = [label.text() for label in row.findChildren(QLabel)]
            self.assertIn("Histórico de Saltos importado", texts)
            self.assertIn("87 novos registros.", texts)


if __name__ == "__main__":
    unittest.main()
