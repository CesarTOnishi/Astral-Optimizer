from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRect,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QLabel,
    QProgressBar, QSplashScreen, QVBoxLayout, QWidget,
)


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
        canvas = QPixmap(520, 310)
        canvas.fill(Qt.GlobalColor.transparent)
        super().__init__(canvas, Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(str(icon_path)))
        self._opening: QParallelAnimationGroup | None = None
        self._transition: QParallelAnimationGroup | None = None
        self._pulse_value = 0.0
        self.setStyleSheet(
            "QSplashScreen {"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #081321,stop:0.48 #12162c,stop:1 #26173a);"
            "border:1px solid #7962a5;border-radius:20px;color:white;}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(46, 28, 46, 30)
        layout.setSpacing(10)
        self.icon = QLabel()
        self.icon.setPixmap(load_icon_pixmap(icon_path, 148))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_glow = QGraphicsDropShadowEffect(self.icon)
        self.icon_glow.setOffset(0, 0)
        self.icon_glow.setBlurRadius(18)
        self.icon_glow.setColor(QColor(224, 101, 236, 95))
        self.icon.setGraphicsEffect(self.icon_glow)
        title = QLabel("ASTRAL OPTIMIZER")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:22px; font-weight:900; letter-spacing:2px;")
        self.message = QLabel("Preparando sua jornada astral…")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setStyleSheet("color:#b8c4da; font-size:11px;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(8)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(7)
        self.progress.setStyleSheet(
            "QProgressBar{background:#161d31;border:none;border-radius:3px;}"
            "QProgressBar::chunk{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #53bde8,stop:0.52 #bd6cdb,stop:1 #ef7bb6);"
            "border-radius:3px;}"
        )
        layout.addWidget(self.icon)
        layout.addWidget(title)
        layout.addWidget(self.message)
        layout.addWidget(self.progress)

        self.pulse = QVariantAnimation(self)
        self.pulse.setStartValue(0.0)
        self.pulse.setEndValue(1.0)
        self.pulse.setDuration(1050)
        self.pulse.setLoopCount(-1)
        self.pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse.valueChanged.connect(self._set_pulse)

    def show_animated(self) -> None:
        self.setWindowOpacity(0.0)
        self.show()
        final_geometry = self.geometry()
        initial_geometry = self._scaled_geometry(final_geometry, 0.94)
        self.setGeometry(initial_geometry)
        group = QParallelAnimationGroup(self)
        opacity = QPropertyAnimation(self, b"windowOpacity", group)
        opacity.setDuration(300)
        opacity.setStartValue(0.0)
        opacity.setEndValue(1.0)
        opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        geometry = QPropertyAnimation(self, b"geometry", group)
        geometry.setDuration(360)
        geometry.setStartValue(initial_geometry)
        geometry.setEndValue(final_geometry)
        geometry.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(opacity)
        group.addAnimation(geometry)
        self._opening = group
        self.pulse.start()
        group.start()

    def set_stage(self, message: str, progress: int) -> None:
        self.message.setText(message)
        animation = QPropertyAnimation(self.progress, b"value", self)
        animation.setDuration(280)
        animation.setStartValue(self.progress.value())
        animation.setEndValue(max(0, min(100, progress)))
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._progress_animation = animation
        animation.start()

    def transition_to(self, window: QWidget) -> None:
        if self._opening is not None:
            self._opening.stop()
        self.set_stage("Tudo pronto. Bem-vindo a bordo!", 100)
        window.setWindowOpacity(0.0)
        window.show()
        group = QParallelAnimationGroup(self)
        splash_opacity = QPropertyAnimation(self, b"windowOpacity", group)
        splash_opacity.setDuration(300)
        splash_opacity.setStartValue(self.windowOpacity())
        splash_opacity.setEndValue(0.0)
        splash_opacity.setEasingCurve(QEasingCurve.Type.InCubic)
        window_opacity = QPropertyAnimation(window, b"windowOpacity", group)
        window_opacity.setDuration(480)
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
        self.icon_glow.setBlurRadius(16 + 12 * self._pulse_value)
        color = QColor(224, 101, 236)
        color.setAlpha(round(65 + 85 * self._pulse_value))
        self.icon_glow.setColor(color)

    @staticmethod
    def _scaled_geometry(rect: QRect, scale: float) -> QRect:
        width = round(rect.width() * scale)
        height = round(rect.height() * scale)
        return QRect(
            rect.center().x() - width // 2,
            rect.center().y() - height // 2,
            width,
            height,
        )


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
        self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self._animation_finished)
        self.hide()

    def start(self, key: str, message: str) -> None:
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
