from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from app.api.enka_client import AccountFetchError
from app.ui.icons import set_button_icon


class EnkaErrorRecoveryPanel(QFrame):
    retry_requested = Signal()
    continue_requested = Signal()
    connection_requested = Signal()
    copy_requested = Signal(object)

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setObjectName("enkaRecoveryPanel")
        self._error: AccountFetchError | None = None
        self.setVisible(False)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(13, 11, 13, 11)
        outer.setSpacing(11)

        self.icon = QLabel("!")
        self.icon.setObjectName("enkaRecoveryIcon")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setFixedSize(34, 34)
        outer.addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignTop)

        content = QVBoxLayout()
        content.setSpacing(5)
        heading = QHBoxLayout()
        heading.setSpacing(8)
        self.title = QLabel("Falha na consulta")
        self.title.setObjectName("enkaRecoveryTitle")
        self.category = QLabel("")
        self.category.setObjectName("enkaRecoveryCategory")
        heading.addWidget(self.title)
        heading.addWidget(self.category)
        heading.addStretch(1)
        content.addLayout(heading)

        self.message = QLabel("")
        self.message.setObjectName("enkaRecoveryMessage")
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content.addWidget(self.message)

        self.actions = QGridLayout()
        self.actions.setHorizontalSpacing(7)
        self.actions.setVerticalSpacing(6)
        self.retry_button = self._button("Tentar novamente", "refresh")
        self.continue_button = self._button("Continuar com dados salvos", "history")
        self.connection_button = self._button("Verificar conexão", "info")
        self.copy_button = self._button("Copiar detalhes", "build")
        self.retry_button.clicked.connect(self.retry_requested.emit)
        self.continue_button.clicked.connect(self.continue_requested.emit)
        self.connection_button.clicked.connect(self.connection_requested.emit)
        self.copy_button.clicked.connect(self._copy)
        self._arrange_actions()
        content.addLayout(self.actions)
        outer.addLayout(content, 1)

    @staticmethod
    def _button(text: str, icon: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("enkaRecoveryAction")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        set_button_icon(button, icon, 14)
        return button

    def show_error(self, error: AccountFetchError, *, has_saved_data: bool) -> None:
        self._error = error
        self.title.setText(error.title)
        self.message.setText(error.message)
        self.category.setText(
            {
                "invalid_uid": "UID",
                "uid_not_found": "UID",
                "rate_limited": "LIMITE TEMPORÁRIO",
                "service_unavailable": "SERVIÇO",
                "timeout": "TEMPO ESGOTADO",
                "network": "CONEXÃO",
                "unknown": "ERRO INESPERADO",
            }.get(error.code, "CONSULTA")
        )
        self.retry_button.setVisible(error.retryable)
        self.continue_button.setVisible(has_saved_data)
        self.connection_button.setVisible(error.check_connection)
        self.copy_button.setVisible(True)
        self._arrange_actions()
        self.setVisible(True)

    def clear(self) -> None:
        self._error = None
        self.setVisible(False)

    def _copy(self) -> None:
        if self._error is not None:
            self.copy_requested.emit(self._error)

    def _arrange_actions(self) -> None:
        while self.actions.count():
            self.actions.takeAt(0)
        visible = [
            button
            for button in (
                self.retry_button,
                self.continue_button,
                self.connection_button,
                self.copy_button,
            )
            if not button.isHidden()
        ]
        if len(visible) == 1:
            self.actions.addWidget(visible[0], 0, 0, 1, 2)
        else:
            for index, button in enumerate(visible):
                self.actions.addWidget(button, index // 2, index % 2)
        self.actions.setColumnStretch(0, 1)
        self.actions.setColumnStretch(1, 1)
