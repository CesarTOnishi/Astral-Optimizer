from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from app.preferences import reduce_motion_enabled
from app.section_loading import SectionState


class SectionStatus(QFrame):
    retry_requested = Signal(str)

    def __init__(self, section: str, parent=None) -> None:
        super().__init__(parent)
        self.section = section
        self._frame = 0
        self.setObjectName("sectionLoadStatus")
        self.setFixedHeight(28)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 2, 4, 2)
        layout.setSpacing(6)
        self.indicator = QLabel("")
        self.indicator.setObjectName("sectionLoadIndicator")
        self.message = QLabel("")
        self.message.setObjectName("sectionLoadMessage")
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        self.message.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.retry = QPushButton("Tentar novamente")
        self.retry.setObjectName("sectionRetryButton")
        self.retry.clicked.connect(lambda: self.retry_requested.emit(self.section))
        layout.addWidget(self.indicator)
        layout.addWidget(self.message, 1)
        layout.addWidget(self.retry)
        self.timer = QTimer(self)
        self.timer.setInterval(360)
        self.timer.timeout.connect(self._advance)
        self.set_state(SectionState(section))

    def set_state(self, state: SectionState) -> None:
        self.setProperty("state", state.status)
        self.message.setText(state.message)
        self.message.setToolTip(state.details or state.message)
        self.retry.setVisible(state.status == "error" and state.retryable)
        if state.status == "pending":
            self.indicator.setText("◌")
            if not reduce_motion_enabled():
                self.timer.start()
        elif state.status == "error":
            self.timer.stop()
            self.indicator.setText("!")
        else:
            self.timer.stop()
            self.indicator.clear()
        self.setProperty("empty", state.status == "ready")
        self.style().unpolish(self)
        self.style().polish(self)

    def _advance(self) -> None:
        self._frame = (self._frame + 1) % 4
        self.indicator.setText(("◌", "◔", "◑", "◕")[self._frame])
