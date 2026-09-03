from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QTimer,
    Qt,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RankRedirectDialog(QDialog):
    def __init__(self, uid: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rankRedirectDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(450)
        self._closing = False
        self._open_animation: QParallelAnimationGroup | None = None
        self._close_animation: QParallelAnimationGroup | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        modal = QFrame()
        modal.setObjectName("rankRedirectModal")
        layout = QVBoxLayout(modal)
        layout.setContentsMargins(25, 20, 25, 24)
        layout.setSpacing(13)

        header = QHBoxLayout()
        icon = QLabel("★")
        icon.setObjectName("rankRedirectIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(38, 38)
        title = QLabel("ABRIR RANKING")
        title.setObjectName("brandTitle")
        close = QPushButton("×")
        close.setObjectName("dialogCloseButton")
        close.setFixedSize(34, 30)
        close.clicked.connect(self.reject)
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)
        layout.addLayout(header)

        message = QLabel(
            "Você será redirecionado para o ranking no SeeleLand usando a UID "
            "associada ao seu perfil."
        )
        message.setObjectName("rankRedirectMessage")
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)

        uid_label = QLabel(uid)
        uid_label.setObjectName("rankRedirectUid")
        uid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(uid_label)

        note = QLabel("O endereço será aberto no seu navegador padrão.")
        note.setObjectName("muted")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)

        actions = QHBoxLayout()
        actions.setSpacing(9)
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("Continuar para o SeeleLand")
        confirm.setObjectName("primaryButton")
        confirm.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(confirm, 1)
        layout.addLayout(actions)

        outer.addWidget(modal)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().showEvent(event)
        QTimer.singleShot(0, self._animate_open)

    def _animate_open(self) -> None:
        if self._closing or not self.isVisible():
            return
        final_geometry = self.geometry()
        initial_geometry = final_geometry.adjusted(10, 8, -10, -8)
        self.setWindowOpacity(0.0)
        self.setGeometry(initial_geometry)

        group = QParallelAnimationGroup(self)
        opacity = QPropertyAnimation(self, b"windowOpacity", group)
        opacity.setDuration(260)
        opacity.setStartValue(0.0)
        opacity.setEndValue(1.0)
        opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        geometry = QPropertyAnimation(self, b"geometry", group)
        geometry.setDuration(300)
        geometry.setStartValue(initial_geometry)
        geometry.setEndValue(final_geometry)
        geometry.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(opacity)
        group.addAnimation(geometry)
        self._open_animation = group
        group.start()

    def reject(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self._open_animation is not None:
            self._open_animation.stop()

        initial_geometry = self.geometry()
        final_geometry = initial_geometry.adjusted(10, 8, -10, -8)
        group = QParallelAnimationGroup(self)
        opacity = QPropertyAnimation(self, b"windowOpacity", group)
        opacity.setDuration(170)
        opacity.setStartValue(self.windowOpacity())
        opacity.setEndValue(0.0)
        opacity.setEasingCurve(QEasingCurve.Type.InCubic)
        geometry = QPropertyAnimation(self, b"geometry", group)
        geometry.setDuration(190)
        geometry.setStartValue(initial_geometry)
        geometry.setEndValue(final_geometry)
        geometry.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(opacity)
        group.addAnimation(geometry)
        group.finished.connect(lambda: QDialog.reject(self))
        self._close_animation = group
        group.start()
