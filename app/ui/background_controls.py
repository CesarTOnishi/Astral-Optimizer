"""Shared controls for launch-at-login and close-to-tray preferences."""

from __future__ import annotations

import sys

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QLabel, QSystemTrayIcon, QVBoxLayout,
)

from app.background import BackgroundSettings


class BackgroundControls(QFrame):
    close_to_tray_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsUpdatePanel")
        self.settings = BackgroundSettings()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 11, 13, 12)
        layout.setSpacing(7)

        title = QLabel("INICIALIZAÇÃO E SEGUNDO PLANO")
        title.setObjectName("metricTitle")
        layout.addWidget(title)

        self.autostart = QCheckBox("Iniciar com o Windows")
        self.autostart.setObjectName("experienceCheckBox")
        self.autostart.setChecked(self.settings.autostart_enabled())
        self.autostart.setEnabled(sys.platform == "win32")
        self.autostart.toggled.connect(self._set_autostart)
        layout.addWidget(self.autostart)

        self.close_to_tray = QCheckBox("Manter em segundo plano ao fechar")
        self.close_to_tray.setObjectName("experienceCheckBox")
        self.close_to_tray.setChecked(self.settings.close_to_tray())
        self.close_to_tray.toggled.connect(self._set_close_to_tray)
        layout.addWidget(self.close_to_tray)

        hint = QLabel(
            "Ao fechar, o app fica na bandeja do sistema. Use o ícone da bandeja "
            "para abrir a janela ou sair completamente."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def _set_autostart(self, enabled: bool) -> None:
        try:
            self.settings.set_autostart(enabled)
        except OSError as error:
            self.autostart.blockSignals(True)
            self.autostart.setChecked(self.settings.autostart_enabled())
            self.autostart.blockSignals(False)
            self.status.setText(f"Não foi possível alterar o início automático: {error}")
            return
        self.status.setText(
            "Início com o Windows ativado." if enabled
            else "Início com o Windows desativado."
        )

    def _set_close_to_tray(self, enabled: bool) -> None:
        self.settings.set_close_to_tray(enabled)
        self.close_to_tray_changed.emit()
        if enabled and not QSystemTrayIcon.isSystemTrayAvailable():
            self.status.setText(
                "Bandeja indisponível nesta sessão; ao fechar, o app será encerrado."
            )
        else:
            self.status.setText(
                "Fechar a janela manterá o app na bandeja." if enabled
                else "Fechar a janela encerrará o app."
            )
