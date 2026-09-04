from __future__ import annotations

import unittest

from PySide6.QtCore import QCoreApplication

from app.sync_manager import BackgroundSyncManager


class BackgroundSyncManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_tracks_parallel_tasks_and_latest_message(self) -> None:
        manager = BackgroundSyncManager()
        changes: list[tuple[str, str, int]] = []
        manager.changed.connect(lambda state, message, count: changes.append(
            (state, message, count)
        ))

        manager.begin("account", "Consultando conta…")
        manager.begin("catalog", "Atualizando catálogo…")
        manager.finish("catalog", "Catálogo sincronizado")

        self.assertEqual(manager.active_count, 1)
        self.assertEqual(changes[-1], ("syncing", "Consultando conta…", 1))

        manager.finish("account", "Conta sincronizada")
        self.assertEqual(manager.active_count, 0)
        self.assertEqual(changes[-1], ("success", "Conta sincronizada", 0))

    def test_failure_does_not_hide_another_active_task(self) -> None:
        manager = BackgroundSyncManager()
        changes: list[tuple[str, str, int]] = []
        manager.changed.connect(lambda state, message, count: changes.append(
            (state, message, count)
        ))

        manager.begin("account", "Consultando conta…")
        manager.begin("drive", "Salvando backup…")
        manager.fail("drive", "Falha no backup")

        self.assertEqual(changes[-1], ("syncing", "Consultando conta…", 1))


if __name__ == "__main__":
    unittest.main()
