from pathlib import Path
import tempfile
import unittest

from PySide6.QtCore import QSettings

from app.auth import AuthUser
from app.cloud.onedrive import (
    OneDriveBackupService,
    configured_backup_folder,
    detected_onedrive_roots,
    set_backup_folder,
)


class OneDriveBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user = AuthUser(7, "Astral", "astral@example.com", "600000001")

    def test_detects_personal_onedrive_folder_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "OneDrive"
            root.mkdir()
            result = detected_onedrive_roots({
                "OneDriveConsumer": str(root),
                "OneDrive": str(root),
                "OneDriveCommercial": "",
            })
            self.assertEqual(result, (root,))

    def test_custom_folder_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "Astral Backups"
            settings = QSettings(
                str(Path(directory) / "onedrive.ini"),
                QSettings.Format.IniFormat,
            )
            set_backup_folder(folder, settings)
            self.assertEqual(configured_backup_folder(settings), folder.resolve())
            set_backup_folder(None, settings)
            self.assertIsNone(configured_backup_folder(settings))

    def test_saves_and_restores_integrity_checked_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = OneDriveBackupService(self.user, Path(directory))
            payload = {"version": 1, "records": [{"id": "1"}], "planner": {}}

            message = service.save_backup(payload)

            self.assertIn("Backup salvo no OneDrive", message)
            self.assertEqual(service.load_latest_backup(), payload)
            self.assertEqual(len(service.backup_files()), 1)
            self.assertFalse(list(Path(directory).glob("*.tmp")))

    def test_corrupted_latest_file_falls_back_to_previous_valid_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = OneDriveBackupService(self.user, Path(directory))
            first = {"version": 1, "records": [{"id": "first"}]}
            second = {"version": 1, "records": [{"id": "second"}]}
            service.save_backup(first)
            service.save_backup(second)
            latest = service.backup_files()[0]
            latest.write_text("{corrompido", encoding="utf-8")

            self.assertEqual(service.load_latest_backup(), first)

    def test_different_profiles_use_different_backup_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            first = OneDriveBackupService(self.user, folder)
            second = OneDriveBackupService(
                AuthUser(8, "Outro", "outro@example.com"), folder
            )
            first.save_backup({"version": 1, "records": []})
            second.save_backup({"version": 1, "records": []})

            self.assertNotEqual(first.profile_key, second.profile_key)
            self.assertEqual(len(first.backup_files()), 1)
            self.assertEqual(len(second.backup_files()), 1)


if __name__ == "__main__":
    unittest.main()
