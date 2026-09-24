from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMenu, QPushButton

from app.sync_manager import BackgroundSyncManager
from app.ui.task_center import BackgroundTaskButton


class BackgroundTaskButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_failed_task_offers_retry_and_copy_details(self) -> None:
        manager = BackgroundSyncManager()
        manager.begin("catalog", "Verificando catálogo…", retryable=True)
        manager.fail("catalog", "Falha ao atualizar", details="Sem conexão")
        button = BackgroundTaskButton(manager)
        menu = QMenu()
        retried: list[str] = []
        button.retry_requested.connect(retried.append)

        row = button._task_row(manager.records[0], menu)
        actions = {item.text(): item for item in row.findChildren(QPushButton)}

        self.assertIn("Tentar novamente", actions)
        self.assertIn("Copiar detalhes", actions)
        actions["Tentar novamente"].click()
        self.assertEqual(retried, ["catalog"])


if __name__ == "__main__":
    unittest.main()
