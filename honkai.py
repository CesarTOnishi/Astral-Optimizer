import sys

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import (
    QApplication, QDialog, QMainWindow, QMenu, QSplashScreen, QWidget,
)

from app.config import APP_FONT_TTF, APP_ICON_ICO, APP_ICON_PNG
from app.preferences import apply_experience_preferences, motion_duration
from app.ui.loading import StartupSplash
from app.ui.main_window import MainWindow


class UnexpectedWindowGuard(QObject):
    """Impede que widgets internos apareçam como pequenas janelas soltas."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.Show or not isinstance(watched, QWidget):
            return super().eventFilter(watched, event)
        if not watched.isWindow():
            return super().eventFilter(watched, event)

        window_type = watched.windowType()
        allowed_type = window_type in (
            Qt.WindowType.ToolTip,
            Qt.WindowType.Popup,
        )
        allowed_widget = isinstance(
            watched, (QMainWindow, QDialog, QMenu, QSplashScreen)
        )
        if allowed_type or allowed_widget:
            return super().eventFilter(watched, event)

        watched.hide()
        return True


def main() -> int:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "AstralOptimizer.Desktop"
            )
        except (AttributeError, OSError):
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("Astral Optimizer")
    app.setOrganizationName("AstralOptimizer")
    font_family = "Segoe UI"
    if APP_FONT_TTF.is_file():
        font_id = QFontDatabase.addApplicationFont(str(APP_FONT_TTF))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            font_family = families[0]
    app.setFont(QFont(font_family, 10))
    apply_experience_preferences(app)
    icon_path = APP_ICON_ICO if APP_ICON_ICO.is_file() else APP_ICON_PNG
    app.setWindowIcon(QIcon(str(icon_path)))
    splash = StartupSplash(APP_ICON_PNG)
    splash.show_animated()
    splash.set_stage("Preparando os módulos do Astral Optimizer…", 20)
    app.processEvents()
    window_guard = UnexpectedWindowGuard(app)
    app.installEventFilter(window_guard)
    state: dict[str, MainWindow] = {}

    def open_main_window() -> None:
        splash.set_stage("Carregando sua interface e dados locais…", 42)
        app.processEvents()
        window = MainWindow()
        state["window"] = window

        def finish_opening() -> None:
            splash.set_stage("Finalizando os últimos detalhes…", 92)
            app.processEvents()
            splash.transition_to(window)
            QTimer.singleShot(motion_duration(700), window.show_tutorial)

        window.initial_account_sync_finished.connect(finish_opening)
        if window.start_initial_account_sync():
            splash.set_stage(
                "Sincronizando sua conta, personagens e relíquias…", 68
            )
            app.processEvents()
        else:
            finish_opening()

    # Deixa a primeira animação ser desenhada antes da inicialização mais pesada.
    QTimer.singleShot(180, open_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
