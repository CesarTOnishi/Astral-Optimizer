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

        if automatic_install and release.download_url:
            warning = QFrame()
            warning.setObjectName("updateInstallWarning")
            warning_layout = QHBoxLayout(warning)
            warning_layout.setContentsMargins(12, 10, 12, 10)
            warning_layout.setSpacing(9)
            icon = QLabel("!")
            icon.setObjectName("updateWarningIcon")
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedSize(25, 25)
            message = QLabel(
                "Depois do download, o Astral será fechado para substituir os arquivos. "
                "Não abra o aplicativo manualmente: a operação pode levar alguns minutos "
                "e ele será iniciado novamente de forma automática."
            )
            message.setObjectName("updateWarningText")
            message.setWordWrap(True)
            warning_layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
            warning_layout.addWidget(message, 1)
            layout.addWidget(warning)

        actions = QHBoxLayout()
        later = QPushButton("Agora não")
        later.setObjectName("secondaryButton")
        later.clicked.connect(self.reject)
        confirm = QPushButton(
            "Baixar e instalar" if automatic_install and release.download_url
            else "Abrir no GitHub"
        )
        confirm.setObjectName("primaryButton")
        confirm.clicked.connect(self.accept)
        actions.addStretch(1)
        actions.addWidget(later)
        actions.addWidget(confirm)
        layout.addLayout(actions)
        outer.addWidget(card)


class UpdateReadyDialog(QDialog):
    """Final warning shown immediately before the application is closed."""

    def __init__(self, version: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("authDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(500)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        card = QFrame()
        card.setObjectName("authModal")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 22, 25, 23)
        layout.setSpacing(12)

        eyebrow = QLabel("ATUALIZAÇÃO PRONTA")
        eyebrow.setObjectName("metricTitle")
        title = QLabel(f"Instalar o Astral Optimizer {version}")
        title.setObjectName("detailName")
        title.setWordWrap(True)
        explanation = QLabel(
            "O download e a verificação terminaram. Ao continuar, esta janela será "
            "fechada e os arquivos serão substituídos automaticamente."
        )
        explanation.setObjectName("muted")
        explanation.setWordWrap(True)
        warning = QLabel(
            "NÃO ABRA O APLICATIVO MANUALMENTE\n"
            "Aguarde alguns minutos. O Astral abrirá sozinho quando a instalação terminar."
        )
        warning.setObjectName("updateReadyWarning")
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning.setWordWrap(True)
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(explanation)
        layout.addWidget(warning)

        actions = QHBoxLayout()
        cancel = QPushButton("Instalar depois")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self.reject)
        install = QPushButton("Fechar e instalar")
        install.setObjectName("primaryButton")
        install.clicked.connect(self.accept)
        actions.addStretch(1)
        actions.addWidget(cancel)
        actions.addWidget(install)
        layout.addLayout(actions)
        outer.addWidget(card)
