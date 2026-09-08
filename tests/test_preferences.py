from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QSettings

from app.preferences import (
    ExperiencePreferences, ExperienceSettings, experience_stylesheet,
)


class ExperienceSettingsTests(unittest.TestCase):
    def test_preferences_are_persisted_and_validated(self) -> None:
        with TemporaryDirectory() as directory:
            settings = QSettings(
                str(Path(directory) / "experience.ini"),
                QSettings.Format.IniFormat,
            )
            store = ExperienceSettings(settings)
            expected = ExperiencePreferences("contrast", True, False)
            store.save(expected)
            self.assertEqual(store.load(), expected)
            store.complete_tutorial()
            self.assertTrue(store.load().tutorial_completed)

    def test_additional_theme_changes_stylesheet(self) -> None:
        regular = experience_stylesheet(ExperiencePreferences(theme="astral"))
        jade = experience_stylesheet(ExperiencePreferences(theme="jade"))
        self.assertNotEqual(regular, jade)
        self.assertNotIn("background-color: #080d19", jade)

    def test_invalid_values_return_safe_defaults(self) -> None:
        with TemporaryDirectory() as directory:
            settings = QSettings(
                str(Path(directory) / "experience.ini"),
                QSettings.Format.IniFormat,
            )
            settings.setValue("appearance/theme", "unknown")
            result = ExperienceSettings(settings).load()
            self.assertEqual(result.theme, "astral")


if __name__ == "__main__":
    unittest.main()
