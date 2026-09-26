"""Computer-wide launch and window-close preferences."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import QSettings


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "AstralOptimizer"


class BackgroundSettings:
    def __init__(self, settings: QSettings | None = None) -> None:
        self.settings = settings or QSettings("AstralOptimizer", "Background")

    def close_to_tray(self) -> bool:
        return self.settings.value("close_to_tray", False, type=bool)

    def set_close_to_tray(self, enabled: bool) -> None:
        self.settings.setValue("close_to_tray", enabled)
        self.settings.sync()

    @staticmethod
    def launch_command() -> str:
        executable = Path(sys.executable).resolve()
        if getattr(sys, "frozen", False):
            arguments = [str(executable), "--autostart"]
        else:
            pythonw = executable.with_name("pythonw.exe")
            if sys.platform == "win32" and pythonw.is_file():
                executable = pythonw
            script = Path(__file__).resolve().parent.parent / "honkai.py"
            arguments = [str(executable), str(script), "--autostart"]
        return subprocess.list2cmdline(arguments)

    @staticmethod
    def autostart_enabled() -> bool:
        if sys.platform != "win32":
            return False
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _kind = winreg.QueryValueEx(key, RUN_VALUE)
                return bool(value)
        except FileNotFoundError:
            return False

    @staticmethod
    def set_autostart(enabled: bool) -> None:
        if sys.platform != "win32":
            raise OSError("O início automático está disponível apenas no Windows.")
        import winreg

        if enabled:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(
                    key, RUN_VALUE, 0, winreg.REG_SZ,
                    BackgroundSettings.launch_command(),
                )
        else:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.DeleteValue(key, RUN_VALUE)
            except FileNotFoundError:
                pass

    @classmethod
    def refresh_autostart_path(cls) -> None:
        if getattr(sys, "frozen", False) and cls.autostart_enabled():
            cls.set_autostart(True)
