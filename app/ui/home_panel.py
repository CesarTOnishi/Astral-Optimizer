from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRegularExpression,
    QTimer,
    QVariantAnimation,
    Signal,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPixmap,
    QRegularExpressionValidator,
)
from PySide6.QtWidgets import (
    QBoxLayout,
    QGraphicsOpacityEffect,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.preferences import motion_duration, reduce_motion_enabled


class AnimatedSearchButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._hover_progress = 0.0
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(motion_duration(190))
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._set_hover)

    def _animate(self, target: float) -> None:
        if reduce_motion_enabled():
            self._set_hover(target)
            return
        self._animation.stop()
        self._animation.setStartValue(self._hover_progress)
        self._animation.setEndValue(target)
        self._animation.start()

    def _set_hover(self, value: object) -> None:
        self._hover_progress = float(value)
        if self._hover_progress <= 0.001:
            self.setStyleSheet("")
            return
        start = QColor("#238fc5")
        end = QColor("#43b8e4")
        progress = self._hover_progress
        color = QColor(
            round(start.red() + (end.red() - start.red()) * progress),
            round(start.green() + (end.green() - start.green()) * progress),
            round(start.blue() + (end.blue() - start.blue()) * progress),
        )
        self.setStyleSheet(
            "QPushButton#homeSearchButton {"
            f"background-color:{color.name()}; border-color:#9be8ff;"
            "}"
        )

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._animate(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._animate(0.0)
        super().leaveEvent(event)


class HomePanel(QWidget):
    search_requested = Signal(str)

    def __init__(self, background_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("homePage")
        self.background = QPixmap(str(background_path))
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(42, 34, 42, 42)
        outer.setSpacing(12)

        self.heading = QWidget()
        self.heading.setObjectName("homeHeading")
        heading = QVBoxLayout(self.heading)
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(4)
        eyebrow = QLabel("EXPRESSO ASTRAL · CONSULTA DE SHOWCASE")
        eyebrow.setObjectName("homeEyebrow")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Bem-vindo ao Astral Optimizer")
        title.setObjectName("homeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.addWidget(eyebrow)
        heading.addWidget(title)
        outer.addWidget(
            self.heading,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        outer.addStretch(1)

        self.search_group = QWidget()
        self.search_group.setObjectName("homeSearchGroup")
        self.search_group.setMaximumWidth(650)
        search_layout = QVBoxLayout(self.search_group)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)
        description = QLabel(
            'Insira seu UID para ver sua demonstração de personagens pelo '
            '<a style="color:#79d8fa;" href="https://enka.network/">'
            'Enka.Network</a>.'
        )
        description.setObjectName("homeDescription")
        description.setTextFormat(Qt.TextFormat.RichText)
        description.setOpenExternalLinks(True)
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.search_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.search_row.setContentsMargins(0, 3, 0, 0)
        self.search_row.setSpacing(9)
        self.uid_input = QLineEdit()
        self.uid_input.setObjectName("homeUidInput")
        self.uid_input.setPlaceholderText("UID de 9 dígitos")
        self.uid_input.setMaxLength(9)
        self.uid_input.setClearButtonEnabled(True)
        self.uid_input.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{0,9}"), self)
        )
        self.uid_input.returnPressed.connect(self._submit)
        self.search_button = AnimatedSearchButton("Pesquisar UID")
        self.search_button.setObjectName("homeSearchButton")
        self.search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_button.clicked.connect(self._submit)
        self.search_row.addWidget(self.uid_input, 1)
        self.search_row.addWidget(self.search_button)

        self.message = QLabel("")
        self.message.setObjectName("homeMessage")
        self.message.setWordWrap(True)

        search_layout.addWidget(description)
        search_layout.addLayout(self.search_row)
        search_layout.addWidget(self.message)
        outer.addWidget(
            self.search_group,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        )

        self._heading_opacity = QGraphicsOpacityEffect(self.heading)
        self._search_opacity = QGraphicsOpacityEffect(self.search_group)
        self.heading.setGraphicsEffect(self._heading_opacity)
        self.search_group.setGraphicsEffect(self._search_opacity)
        self._intro = QParallelAnimationGroup(self)
        self._heading_animation = QPropertyAnimation(
            self._heading_opacity, b"opacity", self
        )
        self._heading_animation.setDuration(motion_duration(220))
        self._heading_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._search_animation = QPropertyAnimation(
            self._search_opacity, b"opacity", self
        )
        self._search_animation.setDuration(motion_duration(280))
        self._search_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._intro.addAnimation(self._heading_animation)
        self._intro.addAnimation(self._search_animation)

    def _submit(self) -> None:
        self.search_requested.emit(self.uid_input.text().strip())

    def set_message(self, message: str, error: bool = False) -> None:
        self.message.setText(message)
        self.message.setProperty("error", error)
        self.message.style().unpolish(self.message)
        self.message.style().polish(self.message)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().showEvent(event)
        QTimer.singleShot(0, self._play_intro)

    def _play_intro(self) -> None:
        self._intro.stop()
        if reduce_motion_enabled():
            self._heading_opacity.setOpacity(1.0)
            self._search_opacity.setOpacity(1.0)
            return
        self._intro.stop()
        self._heading_opacity.setOpacity(0.0)
        self._search_opacity.setOpacity(0.0)
        self._heading_animation.setStartValue(0.0)
        self._heading_animation.setEndValue(1.0)
        self._search_animation.setStartValue(0.0)
        self._search_animation.setEndValue(1.0)
        self._intro.start()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.search_group.setFixedWidth(
            max(270, min(650, self.width() - 84))
        )
        compact = self.width() < 720
        direction = (
            QBoxLayout.Direction.TopToBottom
            if compact
            else QBoxLayout.Direction.LeftToRight
        )
        if self.search_row.direction() != direction:
            self.search_row.setDirection(direction)
        self.search_button.setMinimumHeight(42 if compact else 0)
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if not self.background.isNull():
            scaled = self.background.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(self.rect(), scaled, scaled.rect().adjusted(x, y, -x, -y))
        else:
            painter.fillRect(self.rect(), QColor("#080d19"))

        horizontal = QLinearGradient(0, 0, self.width(), 0)
        horizontal.setColorAt(0.0, QColor(4, 9, 18, 205))
        horizontal.setColorAt(0.48, QColor(5, 10, 20, 90))
        horizontal.setColorAt(1.0, QColor(5, 10, 20, 18))
        painter.fillRect(self.rect(), horizontal)

        vertical = QLinearGradient(0, 0, 0, self.height())
        vertical.setColorAt(0.0, QColor(5, 9, 18, 45))
        vertical.setColorAt(0.62, QColor(5, 9, 18, 35))
        vertical.setColorAt(1.0, QColor(5, 9, 18, 155))
        painter.fillRect(self.rect(), vertical)
        painter.end()
        super().paintEvent(event)
