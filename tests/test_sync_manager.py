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

    def test_keeps_finished_tasks_for_the_task_center(self) -> None:
        manager = BackgroundSyncManager()

        manager.begin("account", "Consultando conta…", retryable=True)
        manager.finish("account", "Conta sincronizada")

        self.assertEqual(len(manager.records), 1)
        record = manager.records[0]
        self.assertEqual(record.title, "Conta")
        self.assertEqual(record.state, "success")
        self.assertEqual(record.message, "Conta sincronizada")

    def test_late_finish_does_not_replace_failure(self) -> None:
        manager = BackgroundSyncManager()

        manager.begin("warp-import", "Importando…", retryable=True)
        manager.fail(
            "warp-import",
            "Falha ao importar",
            details="Cache de Saltos não encontrado",
        )
        manager.finish("warp-import", "Saltos sincronizados")

        record = manager.records[0]
        self.assertEqual(record.state, "error")
        self.assertEqual(record.details, "Cache de Saltos não encontrado")

    def test_clear_finished_preserves_failures_and_active_tasks(self) -> None:
        manager = BackgroundSyncManager()
        manager.begin("account", "Consultando…")
        manager.begin("catalog", "Atualizando…")
        manager.finish("catalog", "Catálogo sincronizado")
        manager.begin("warp-import", "Importando…")
        manager.fail("warp-import", "Falha ao importar")

        manager.clear_finished()

        self.assertEqual(
            {(record.key, record.state) for record in manager.records},
            {("account", "active"), ("warp-import", "error")},
        )


if __name__ == "__main__":
    unittest.main()
