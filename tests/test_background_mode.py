import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QScrollArea

from app.auth import AuthUser
from app.background import BackgroundSettings, RUN_VALUE
from app.ui.auth_dialogs import SettingsDialog
from app.ui.experience import ExperienceDialog
from app.ui.main_window import MainWindow


class BackgroundModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_preferences_are_independent_and_default_to_exiting(self) -> None:
        with TemporaryDirectory() as directory:
            settings = QSettings(
                str(Path(directory) / "background.ini"), QSettings.Format.IniFormat
            )
            preferences = BackgroundSettings(settings)
            self.assertFalse(preferences.close_to_tray())
            preferences.set_close_to_tray(True)
            self.assertTrue(BackgroundSettings(settings).close_to_tray())
            preferences.set_close_to_tray(False)
            self.assertFalse(preferences.close_to_tray())

    def test_autostart_writes_and_removes_only_its_run_value(self) -> None:
        registry = MagicMock()
        registry.HKEY_CURRENT_USER = object()
        registry.KEY_SET_VALUE = 2
        registry.REG_SZ = 1
        registry.QueryValueEx.return_value = ("C:\\AstralOptimizer.exe", 1)
        with patch.dict("sys.modules", {"winreg": registry}), patch(
            "app.background.sys.platform", "win32"
        ), patch.object(BackgroundSettings, "launch_command", return_value='"C:\\Astral Optimizer.exe" --autostart'):
            self.assertTrue(BackgroundSettings.autostart_enabled())
            BackgroundSettings.set_autostart(True)
            registry.SetValueEx.assert_called_once_with(
                registry.CreateKeyEx.return_value.__enter__.return_value,
                RUN_VALUE, 0, registry.REG_SZ,
                '"C:\\Astral Optimizer.exe" --autostart',
            )
            BackgroundSettings.set_autostart(False)
            registry.DeleteValue.assert_called_once_with(
                registry.OpenKey.return_value.__enter__.return_value,
                RUN_VALUE,
            )

    def test_launch_command_targets_the_current_executable(self) -> None:
        with TemporaryDirectory(prefix="Astral App ") as directory:
            executable = Path(directory) / "AstralOptimizer.exe"
            with patch("app.background.sys.executable", str(executable)), patch.object(
                __import__("sys"), "frozen", True, create=True
            ):
                command = BackgroundSettings.launch_command()
            self.assertIn(str(executable), command)
            self.assertTrue(command.endswith(" --autostart"))

    def test_settings_are_available_with_and_without_login(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ):
            user = AuthUser(1, "teste", "test@example.com", "601000001")
            signed_in = SettingsDialog(user, initial_page=4)
            guest = ExperienceDialog()
            try:
                signed_in.show()
                guest.show()
                self.app.processEvents()
                self.assertIsInstance(
                    signed_in.settings_stack.currentWidget(), QScrollArea
                )
                scroll = signed_in.settings_stack.currentWidget()
                scroll.ensureWidgetVisible(signed_in.background_controls)
                self.app.processEvents()
                self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
                self.assertEqual(
                    signed_in.background_controls.autostart.text(),
                    "Iniciar com o Windows",
                )
                self.assertEqual(
                    guest.background_controls.close_to_tray.text(),
                    "Manter em segundo plano ao fechar",
                )
            finally:
                signed_in.close()
                guest.close()

    def test_close_hides_window_until_explicit_tray_exit(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ), patch.object(BackgroundSettings, "close_to_tray", return_value=False):
            window = MainWindow()
            tray = MagicMock()
            tray.isVisible.return_value = True
            window.background_settings = MagicMock()
            window.background_settings.close_to_tray.return_value = True
            window._tray_icon = tray
            window.show()
            try:
                window.close()
                self.assertFalse(window.isVisible())
                self.assertFalse(window._session_closed)
                window._restore_from_tray()
                self.assertTrue(window.isVisible())
                window._quit_from_tray()
                self.assertTrue(window._session_closed)
                tray.hide.assert_called()
            finally:
                if not window._session_closed:
                    window._quit_requested = True
                    window.close()

    def test_tray_menu_can_be_enabled_and_disabled_immediately(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ), patch.object(BackgroundSettings, "close_to_tray", return_value=False):
            window = MainWindow()
            tray = MagicMock()
            try:
                window.background_settings = MagicMock()
                window.background_settings.close_to_tray.return_value = True
                with patch("app.ui.main_window.QSystemTrayIcon") as tray_class:
                    tray_class.isSystemTrayAvailable.return_value = True
                    tray_class.return_value = tray
                    window._configure_tray()
                self.assertFalse(self.app.quitOnLastWindowClosed())
                actions = tray.setContextMenu.call_args.args[0].actions()
                self.assertEqual(actions[0].text(), "Abrir Astral Optimizer")
                self.assertEqual(actions[-1].text(), "Sair do Astral Optimizer")

                window.background_settings.close_to_tray.return_value = False
                window._configure_tray()
                tray.setVisible.assert_any_call(False)
                self.assertTrue(self.app.quitOnLastWindowClosed())
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
