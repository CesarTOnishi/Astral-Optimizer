from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRectF,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QProgressBar, QSplashScreen, QVBoxLayout, QWidget,
)

from app.config import APP_VERSION
from app.preferences import motion_duration, reduce_motion_enabled, themed_color


def load_icon_pixmap(path: Path, size: int) -> QPixmap:
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(
        size, size, Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class StartupSplash(QSplashScreen):
    def __init__(self, icon_path: Path) -> None:
        canvas = QPixmap(600, 380)
        canvas.fill(Qt.GlobalColor.transparent)
        super().__init__(canvas, Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(str(icon_path)))
        self._opening: QParallelAnimationGroup | None = None
        self._transition: QParallelAnimationGroup | None = None
        self._pulse_value = 0.0
        self._transition_started = False
        self._target_progress = 8
        self.setStyleSheet(
            "QSplashScreen { background: transparent; }"
            "QLabel { background: transparent; border: none; color: #edf6ff; }"
        )
        self.setFont(QFont("Segoe UI", 10))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 22, 34, 26)
        layout.setSpacing(8)
        header = QHBoxLayout()
        mark = QLabel("A S T R A L   /   S T A R   R A I L")
        mark.setStyleSheet("color:#8cabc5;font-size:9px;")
        version = QLabel(f"v{APP_VERSION}")
        version.setStyleSheet("color:#8cabc5;font-size:10px;")
        header.addWidget(mark)
        header.addStretch()
        header.addWidget(version)
        layout.addLayout(header)
        layout.addSpacing(6)
        self.emblem = QWidget()
        self.emblem.setFixedSize(144, 144)
        emblem_layout = QVBoxLayout(self.emblem)
        emblem_layout.setContentsMargins(25, 25, 25, 25)
        self.icon = QLabel()
        self.icon.setPixmap(load_icon_pixmap(icon_path, 90))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emblem_layout.addWidget(self.icon)
        layout.addWidget(self.emblem, alignment=Qt.AlignmentFlag.AlignHCenter)
        title = QLabel("ASTRAL OPTIMIZER")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:25px; font-weight:600; letter-spacing:3px;")
        layout.addWidget(title)
        subtitle = QLabel("Sua próxima jornada começa aqui.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color:#94a9c1;font-size:12px;")
        layout.addWidget(subtitle)
        layout.addStretch(1)
        self.message = QLabel("Preparando sua jornada astral…")
        self.message.setWordWrap(True)
        self.message.setMinimumHeight(34)
        self.message.setStyleSheet("color:#b8cbdf; font-size:11px;")
        self.percentage = QLabel("8%")
        self.percentage.setFixedWidth(40)
        self.percentage.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.percentage.setStyleSheet("color:#9cdef2;font-size:11px;font-weight:600;")
        status = QHBoxLayout()
        status.addWidget(self.message, 1)
        status.addWidget(self.percentage)
        layout.addLayout(status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(8)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet(
            "QProgressBar{background:#19263c;border:none;border-radius:2px;}"
            "QProgressBar::chunk{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {themed_color('#478cbf')},stop:1 {themed_color('#9be6f5')});"
            "border-radius:2px;}"
        )
        layout.addWidget(self.progress)
        self.progress.valueChanged.connect(lambda value: self.percentage.setText(f"{value}%"))

        self.pulse = QVariantAnimation(self)
        self.pulse.setStartValue(0.0)
        self.pulse.setEndValue(1.0)
        self.pulse.setDuration(7200)
        self.pulse.setLoopCount(-1)
        self.pulse.setEasingCurve(QEasingCurve.Type.Linear)
        self.pulse.valueChanged.connect(self._set_pulse)

    def show_animated(self) -> None:
        if self._opening is not None:
            self._opening.stop()
        if reduce_motion_enabled():
            self.setWindowOpacity(1.0)
            self.show()
            return
        self.setWindowOpacity(0.0)
        self.show()
        final_geometry = self.geometry()
        initial_geometry = final_geometry.translated(0, 10)
        self.setGeometry(initial_geometry)
        group = QParallelAnimationGroup(self)
        opacity = QPropertyAnimation(self, b"windowOpacity", group)
        opacity.setDuration(240)
        opacity.setStartValue(0.0)
        opacity.setEndValue(1.0)
        opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        geometry = QPropertyAnimation(self, b"geometry", group)
        geometry.setDuration(300)
        geometry.setStartValue(initial_geometry)
        geometry.setEndValue(final_geometry)
        geometry.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(opacity)
        group.addAnimation(geometry)
        self._opening = group
        self.pulse.start()
        group.start()

    def set_stage(self, message: str, progress: int) -> None:
        self.message.setText(message)
        self._target_progress = max(self._target_progress, min(100, progress))
        previous = getattr(self, "_progress_animation", None)
        if previous is not None:
            previous.stop()
            previous.deleteLater()
            self._progress_animation = None
        if reduce_motion_enabled():
            self.progress.setValue(self._target_progress)
            return
        animation = QPropertyAnimation(self.progress, b"value", self)
        animation.setDuration(220)
        animation.setStartValue(self.progress.value())
        animation.setEndValue(self._target_progress)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._progress_animation = animation
        animation.start()

    def transition_to(self, window: QWidget) -> None:
        if self._transition_started:
            return
        self._transition_started = True
        if self._opening is not None:
            self._opening.stop()
        self.set_stage("Tudo pronto. Bem-vindo a bordo!", 100)
        if reduce_motion_enabled():
            self.pulse.stop()
            self.hide()
            window.setWindowOpacity(1.0)
            window.show()
            window.raise_()
            return
        window.setWindowOpacity(0.0)
        window.show()
        group = QParallelAnimationGroup(self)
        splash_opacity = QPropertyAnimation(self, b"windowOpacity", group)
        splash_opacity.setDuration(220)
        splash_opacity.setStartValue(self.windowOpacity())
        splash_opacity.setEndValue(0.0)
        splash_opacity.setEasingCurve(QEasingCurve.Type.InCubic)
        window_opacity = QPropertyAnimation(window, b"windowOpacity", group)
        window_opacity.setDuration(320)
        window_opacity.setStartValue(0.0)
        window_opacity.setEndValue(1.0)
        window_opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(splash_opacity)
        group.addAnimation(window_opacity)
        group.finished.connect(lambda: self._finish_transition(window))
        self._transition = group
        group.start()

    def _finish_transition(self, window: QWidget) -> None:
        self.pulse.stop()
        self.hide()
        self.setWindowOpacity(1.0)
        window.setWindowOpacity(1.0)
        window.raise_()
        window.activateWindow()

    def _set_pulse(self, value: object) -> None:
        self._pulse_value = float(value)
        if reduce_motion_enabled():
            self.pulse.stop()
            self._pulse_value = 0.0
        self.update()

    def hideEvent(self, event) -> None:
        self.pulse.stop()
        super().hideEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        shape = QPainterPath()
        shape.addRoundedRect(bounds, 22, 22)
        painter.setClipPath(shape)
        background = QLinearGradient(0, 0, self.width(), self.height())
        background.setColorAt(0, QColor(themed_color("#101e33")))
        background.setColorAt(1, QColor(themed_color("#080e1c")))
        painter.fillPath(shape, background)
        center = self.emblem.geometry().center()
        glow = QRadialGradient(center, 195)
        glow.setColorAt(0, QColor(90, 155, 205, 32))
        glow.setColorAt(1, QColor(90, 155, 205, 0))
        painter.fillPath(shape, glow)
        # Fixed star positions keep the background calm and avoid random flicker.
        for x, y, radius in ((58, 96, 1), (127, 174, 1.3), (483, 88, 1.2), (537, 198, 1), (445, 236, 0.8)):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(157, 207, 238, 95))
            painter.drawEllipse(QRectF(x, y, radius * 2, radius * 2))
        ring = QRectF(self.emblem.geometry()).adjusted(6, 6, -6, -6)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(119, 173, 208, 30), 1))
        painter.drawEllipse(ring)
        painter.setPen(QPen(QColor(themed_color("#7acbe9")), 1.4))
        angle = round(self._pulse_value * 360 * 16)
        painter.drawArc(ring, angle, 48 * 16)
        painter.setPen(QPen(QColor(143, 166, 224, 85), 1))
        painter.drawArc(ring.adjusted(8, 8, -8, -8), -angle + 160 * 16, 74 * 16)
        painter.setPen(QPen(QColor(113, 153, 195, 65), 1))
        painter.drawPath(shape)


class LoadingOverlay(QFrame):
    def __init__(self, parent: QWidget, icon_path: Path) -> None:
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self._operations: dict[str, str] = {}
        self._hiding = False
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card = QFrame()
        card.setObjectName("loadingCard")
        card.setFixedSize(370, 235)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 24, 34, 25)
        layout.setSpacing(9)
        icon = QLabel()
        icon.setPixmap(load_icon_pixmap(icon_path, 105))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Carregando")
        title.setObjectName("loadingTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message = QLabel("Aguarde um instante…")
        self.message.setObjectName("loadingMessage")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setObjectName("loadingProgress")
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(self.message)
        layout.addWidget(self.progress)
        outer.addWidget(card)

        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.animation = QPropertyAnimation(self.opacity, b"opacity", self)
        self.animation.setDuration(motion_duration(180))
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self._animation_finished)
        self.hide()

    def start(self, key: str, message: str) -> None:
        self.animation.setDuration(motion_duration(180))
        self._operations[key] = message
        self.message.setText(message)
        self._hiding = False
        self.animation.stop()
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        if not self.isVisible():
            self.opacity.setOpacity(0.0)
            self.show()
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.start()
        else:
            self.opacity.setOpacity(1.0)

    def stop(self, key: str) -> None:
        self.animation.setDuration(motion_duration(180))
        self._operations.pop(key, None)
        if self._operations:
            self.message.setText(next(reversed(self._operations.values())))
            return
        if not self.isVisible():
            return
        self._hiding = True
        self.animation.stop()
        self.animation.setStartValue(self.opacity.opacity())
        self.animation.setEndValue(0.0)
        self.animation.start()

    def _animation_finished(self) -> None:
        if self._hiding and not self._operations:
            self.hide()
            self._hiding = False
