import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

from app.auth.service import AuthUser
from app.preferences import ExperiencePreferences, apply_experience_preferences, experience_stylesheet
from app.ui.auth_dialogs import SettingsDialog
from app.warp.database import WarpDatabase


class ThemeApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.previous_style = self.app.styleSheet()
        self.previous_properties = {name: self.app.property(name) for name in (
            "astralAppliedTheme", "astralTheme", "astralReduceMotion",
        )}

    def tearDown(self):
        self.app.setStyleSheet(self.previous_style)
        for name, value in self.previous_properties.items():
            self.app.setProperty(name, value)

    def test_same_theme_and_motion_toggle_do_not_reapply_stylesheet(self):
        apply_experience_preferences(self.app, ExperiencePreferences("jade", True))
        with patch.object(QApplication, "setStyleSheet") as setter:
            apply_experience_preferences(self.app, ExperiencePreferences("jade", True))
            apply_experience_preferences(self.app, ExperiencePreferences("jade", False))
            setter.assert_not_called()
        self.assertFalse(self.app.property("astralReduceMotion"))
        self.assertIs(experience_stylesheet(ExperiencePreferences("jade")),
                      experience_stylesheet(ExperiencePreferences("jade", True, True)))

    def test_updates_and_layouts_are_restored_even_on_failure(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.app.setProperty("astralAppliedTheme", None)
        try:
            with patch.object(QApplication, "setStyleSheet", side_effect=RuntimeError("test")):
                with self.assertRaises(RuntimeError):
                    apply_experience_preferences(self.app, ExperiencePreferences("aurora", True))
            self.assertTrue(widget.updatesEnabled())
            self.assertTrue(layout.isEnabled())
            self.assertFalse(self.app.property("astralApplyingTheme"))
        finally:
            widget.deleteLater()

    def test_settings_coalesce_changes_and_flush_pending_choice_on_close(self):
        with tempfile.TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            store = Mock()
            store.load.return_value = ExperiencePreferences()
            with patch("app.ui.auth_dialogs.ExperienceSettings", return_value=store), patch(
                "app.ui.auth_dialogs.apply_experience_preferences"
            ) as apply:
                dialog = SettingsDialog(AuthUser(7, "Teste", ""), warp_database=database)
                try:
                    dialog.theme_selector.setCurrentIndex(1)
                    dialog.theme_selector.setCurrentIndex(2)
                    apply.assert_not_called()
                    self.app.processEvents()
                    apply.assert_called_once()
                    self.assertEqual(apply.call_args.kwargs["preferences"].theme,
                                     dialog.theme_selector.currentData())
                    dialog.theme_selector.setCurrentIndex(3)
                    dialog.reject()
                    self.assertEqual(apply.call_count, 2)
                    self.assertEqual(store.save.call_args.args[0].theme,
                                     dialog.theme_selector.currentData())
                    self.assertFalse(dialog._appearance_timer.isActive())
                finally:
                    dialog.deleteLater()
                    self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
