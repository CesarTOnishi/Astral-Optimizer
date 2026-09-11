from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


VIDEO_PATH = Path(__file__).resolve().parents[1] / "assets" / "warp_import_tutorial.mp4"


class WarpImportTutorialDialog(QDialog):
    """Explica a importação automática antes da primeira tentativa."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("authDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedSize(880, 700)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        modal = QFrame()
        modal.setObjectName("settingsModal")
        layout = QVBoxLayout(modal)
        layout.setContentsMargins(22, 16, 22, 20)
        layout.setSpacing(11)

        header = QHBoxLayout()
        title = QLabel("COMO IMPORTAR SALTOS DO JOGO")
        title.setObjectName("brandTitle")
        close = QPushButton("×")
        close.setObjectName("dialogCloseButton")
        close.setFixedSize(34, 30)
        close.clicked.connect(self.reject)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)
        layout.addLayout(header)

        intro = QLabel(
            "O Astral não lê sua conta ou sua senha. Ele procura no cache do jogo "
            "o link temporário criado quando você abre o Histórico de Saltos. Depois "
            "disso, é necessário fechar completamente o jogo para liberar o cache."
        )
        intro.setObjectName("settingsPageSubtitle")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        steps = QHBoxLayout()
        steps.setSpacing(8)
        for number, text in (
            ("1", "Abra o Honkai: Star Rail"),
            ("2", "Entre em Salto → Ver detalhes"),
            ("3", "Abra o Histórico e espere a lista carregar"),
            ("4", "Feche completamente o jogo e volte ao Astral"),
        ):
            card = QFrame()
            card.setObjectName("settingsUpdatePanel")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(9, 8, 9, 8)
            badge = QLabel(number)
            badge.setObjectName("warpMetricValue")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedWidth(24)
            detail = QLabel(text)
            detail.setObjectName("muted")
            detail.setWordWrap(True)
            card_layout.addWidget(badge)
            card_layout.addWidget(detail, 1)
            steps.addWidget(card, 1)
        layout.addLayout(steps)

        self.video = QVideoWidget()
        self.video.setMinimumHeight(390)
        self.video.setStyleSheet("background: #050910; border-radius: 10px;")
        layout.addWidget(self.video, 1)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.65)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        if VIDEO_PATH.is_file():
            self.player.setSource(QUrl.fromLocalFile(str(VIDEO_PATH)))

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.play_button = QPushButton("Pausar vídeo")
        self.play_button.setObjectName("secondaryButton")
        self.play_button.clicked.connect(self._toggle_video)
        replay = QPushButton("Recomeçar")
        replay.setObjectName("secondaryButton")
        replay.clicked.connect(self._replay_video)
        controls.addWidget(self.play_button)
        controls.addWidget(replay)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.video_status = QLabel(
            "IMPORTANTE: depois que o Histórico de Saltos carregar, feche completamente "
            "o jogo antes de fazer a importação no Astral."
        )
        self.video_status.setObjectName("muted")
        self.video_status.setWordWrap(True)
        layout.addWidget(self.video_status)
        self.player.errorOccurred.connect(self._video_error)

        actions = QHBoxLayout()
        actions.addStretch(1)
        close_tutorial = QPushButton("Fechar")
        close_tutorial.setObjectName("primaryButton")
        close_tutorial.setMinimumWidth(130)
        close_tutorial.clicked.connect(self.accept)
        actions.addWidget(close_tutorial)
        layout.addLayout(actions)

        outer.addWidget(modal)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if VIDEO_PATH.is_file():
            QTimer.singleShot(80, self.player.play)
        else:
            self._video_error()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.player.stop()
        super().closeEvent(event)

    def accept(self) -> None:
        self.player.stop()
        super().accept()

    def reject(self) -> None:
        self.player.stop()
        super().reject()

    def _toggle_video(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_button.setText("Continuar vídeo")
        else:
            self.player.play()
            self.play_button.setText("Pausar vídeo")

    def _replay_video(self) -> None:
        self.player.setPosition(0)
        self.player.play()
        self.play_button.setText("Pausar vídeo")

    def _video_error(self, *_args: object) -> None:
        self.video_status.setText(
            "O vídeo não pôde ser reproduzido neste computador. Siga os quatro passos "
            "acima: abra o Histórico de Saltos e depois feche completamente o jogo antes de importar."
        )
        self.play_button.setEnabled(False)
