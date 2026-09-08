import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QSettings

from app.privacy import hide_uid_in_shared_images, set_hide_uid_in_shared_images
from app.ui.build_share import share_uid_text


class PrivacyTests(unittest.TestCase):
    def test_privacy_is_persisted_per_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(
                str(Path(directory) / "privacy.ini"), QSettings.Format.IniFormat
            )
            set_hide_uid_in_shared_images(7, True, settings)

            self.assertTrue(hide_uid_in_shared_images(7, settings))
            self.assertFalse(hide_uid_in_shared_images(8, settings))

    def test_shared_uid_is_masked_without_retaining_digits(self) -> None:
        uid = "600123456"
        self.assertEqual(share_uid_text(uid, False), f"UID {uid}")
        masked = share_uid_text(uid, True)
        self.assertEqual(masked, "UID •••••••••")
        self.assertNotIn(uid, masked)


if __name__ == "__main__":
    unittest.main()
