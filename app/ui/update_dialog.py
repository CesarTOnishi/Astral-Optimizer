from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_VERSION
from app.updater import ReleaseInfo


class UpdateAvailableDialog(QDialog):
    def __init__(
        self,
        release: ReleaseInfo,
        automatic_install: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("authDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(510)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        card = QFrame()
        card.setObjectName("authModal")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 21, 25, 23)
        layout.setSpacing(12)

        eyebrow = QLabel("ATUALIZAÇÃO DISPONÍVEL")
        eyebrow.setObjectName("metricTitle")
        title = QLabel(release.title)
        title.setObjectName("detailName")
        title.setWordWrap(True)
        version = QLabel(f"Versão instalada: {APP_VERSION}   →   Nova versão: {release.version}")
        version.setObjectName("updateVersion")
        notes = QLabel(release.notes[:1200])
        notes.setObjectName("muted")
        notes.setWordWrap(True)
        notes.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(notes)

        actions = QHBoxLayout()
        later = QPushButton("Agora não")
        later.setObjectName("secondaryButton")
        later.clicked.connect(self.reject)
        confirm = QPushButton(
            "Baixar e atualizar" if automatic_install and release.download_url
            else "Abrir no GitHub"
        )
        confirm.setObjectName("primaryButton")
        confirm.clicked.connect(self.accept)
        actions.addStretch(1)
        actions.addWidget(later)
        actions.addWidget(confirm)
        layout.addLayout(actions)
        outer.addWidget(card)
