import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDate

from app.auth import AuthUser
from app.ui.auth_dialogs import SettingsDialog
from app.ui.main_window import MainWindow
from app.ui.notifications import NotificationCenter
from app.warp.database import WarpDatabase
from app.warp.reminder import import_reminder_due


class WarpImportReminderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_due_after_forty_days_and_repeats_only_after_another_forty(self) -> None:
        now = datetime(2026, 9, 26, tzinfo=timezone.utc)
        state = {
            "started_at": (now - timedelta(days=40)).isoformat(),
            "last_imported_at": "",
            "last_reminded_at": "",
        }
        self.assertFalse(import_reminder_due(state, now - timedelta(seconds=1)))
        self.assertTrue(import_reminder_due(state, now))
        state["last_reminded_at"] = now.isoformat()
        self.assertFalse(import_reminder_due(state, now + timedelta(days=39)))
        self.assertTrue(import_reminder_due(state, now + timedelta(days=40)))
        state["last_imported_at"] = (now + timedelta(days=41)).isoformat()
        self.assertFalse(import_reminder_due(state, now + timedelta(days=70)))
        state["interval_days"] = 30
        self.assertFalse(import_reminder_due(state, now + timedelta(days=70)))
        self.assertTrue(import_reminder_due(state, now + timedelta(days=71)))
        state["next_due_on"] = "2026-10-10"
        self.assertFalse(import_reminder_due(state, datetime(2026, 10, 9, tzinfo=timezone.utc)))
        self.assertTrue(import_reminder_due(state, datetime(2026, 10, 11, tzinfo=timezone.utc)))

    def test_existing_reminder_rows_receive_forty_day_default(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "warps.db"
            connection = sqlite3.connect(path)
            try:
                connection.execute(
                    "CREATE TABLE warp_import_reminders ("
                    "owner_id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, "
                    "last_imported_at TEXT NOT NULL DEFAULT '', "
                    "last_reminded_at TEXT NOT NULL DEFAULT '')"
                )
                connection.execute(
                    "INSERT INTO warp_import_reminders(owner_id, started_at) "
                    "VALUES (7, '2026-01-01T00:00:00+00:00')"
                )
                connection.commit()
            finally:
                connection.close()
            database = WarpDatabase(path)
            self.assertEqual(database.import_reminder(7)["interval_days"], 40)
            self.assertEqual(database.import_reminder(7)["next_due_on"], "")

    def test_settings_tab_controls_categories_independently(self) -> None:
        with TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            user = AuthUser(7, "Pessoa", "pessoa@example.com", "600000001")
            dialog = SettingsDialog(user, warp_database=database, initial_page=5)
            try:
                self.assertTrue(dialog.notification_checkboxes["warp_reminder"].isChecked())
                self.assertEqual(dialog.warp_reminder_days.value(), 40)
                self.assertTrue(dialog.warp_reminder_date.date().isValid())
                self.assertEqual(dialog.settings_stack.currentIndex(), 5)
                dialog.warp_reminder_days.setValue(25)
                self.assertEqual(database.import_reminder(7)["interval_days"], 25)
                chosen = QDate.currentDate().addDays(12)
                dialog.warp_reminder_date.setDate(chosen)
                self.assertEqual(
                    database.import_reminder(7)["next_due_on"],
                    chosen.toString("yyyy-MM-dd"),
                )
                dialog.notification_checkboxes["warp_reminder"].setChecked(False)
                self.assertFalse(dialog.warp_reminder_days.isEnabled())
                self.assertFalse(dialog.warp_reminder_date.isEnabled())
                dialog.notification_checkboxes["backup"].setChecked(False)
                self.assertEqual(database.notification_preferences(7), {
                    "warp_reminder": False, "backup": False,
                })
                self.assertEqual(database.notification_preferences(8), {})
                center = NotificationCenter()
                center.set_preferences(database.notification_preferences(7))
                center.add("backup:7", "Backup", "Concluído")
                center.add("catalog-outdated", "Catálogo", "Novo")
                self.assertEqual([item.key for item in center.items], ["catalog-outdated"])
                center.set_preferences({"catalog": False})
                self.assertEqual(center.items, ())
                exported = database.export_owner(7)
                restored = WarpDatabase(Path(directory) / "restored.db")
                restored.restore_owner(exported, 12)
                self.assertEqual(restored.notification_preferences(12), {
                    "warp_reminder": False, "backup": False,
                })
                self.assertEqual(restored.import_reminder(12)["interval_days"], 25)
                self.assertEqual(
                    restored.import_reminder(12)["next_due_on"],
                    chosen.toString("yyyy-MM-dd"),
                )
            finally:
                dialog.close()

    def test_main_window_reminds_then_clears_after_successful_import(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ):
            window = MainWindow()
            original_auth = window.auth_service
            user = AuthUser(9, "Pessoa", "pessoa@example.com", "600000009")
            window.auth_service = SimpleNamespace(current_user=user)
            database = window.warp_panel.database
            database.save_import_reminder(9, {
                "started_at": (datetime.now(timezone.utc) - timedelta(days=41)).isoformat(),
                "last_imported_at": "",
                "last_reminded_at": "",
                "interval_days": 1,
            })
            try:
                window._refresh_notification_preferences()
                key = "warp-import-reminder:9"
                self.assertIn(key, [item.key for item in window.notification_center.items])
                notice = next(item for item in window.notification_center.items if item.key == key)
                self.assertIn("1 dia", notice.message)
                window._check_warp_import_reminder()
                self.assertEqual(
                    [item.key for item in window.notification_center.items].count(key), 1
                )
                window._record_warp_import(9, 0, 10, "Cache")
                self.assertNotIn(key, [item.key for item in window.notification_center.items])
                self.assertFalse(import_reminder_due(database.import_reminder(9)))
                self.assertEqual(database.import_reminder(9)["interval_days"], 1)
                self.assertEqual(database.import_reminder(9)["next_due_on"], "")
                database.set_notification_enabled(9, "soft_pity", False)
                window._refresh_notification_preferences()
                window.notification_center.add("soft-pity:9:600000009:11", "Pity", "70")
                self.assertFalse(any(
                    item.key.startswith("soft-pity:") for item in window.notification_center.items
                ))
            finally:
                window.auth_service = original_auth
                window.close()


if __name__ == "__main__":
    unittest.main()
