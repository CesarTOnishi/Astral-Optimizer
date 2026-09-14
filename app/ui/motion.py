"""Lightweight, interruptible motion for the existing Qt Widgets interface."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QEasingCurve, QObject, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication, QDialog, QMenu, QProgressBar, QPushButton, QScrollBar, QStackedWidget,
    QStyle, QStyleOptionProgressBar, QWidget,
)

from app.preferences import reduce_motion_enabled, themed_color


class MotionLayer(QWidget):
    """Paint-only overlay: never replaces an existing graphics effect or eats input."""

    def __init__(self, parent, *, snapshot=None, dim=False):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self.setObjectName("astralMotionLayer")
        self.setStyleSheet("QWidget#astralMotionLayer { background: transparent; border: none; }")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.snapshot = snapshot
        self.dim = dim
        self.amount = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._value)
        self.animation.finished.connect(self._finished)
        self.setGeometry(parent.rect())
        self.hide()

    def _value(self, value):
        self.amount = float(value)
        self.update()

    def _finished(self):
        if self.amount <= 0.001:
            self.hide()

    def animate(self, target, duration=150):
        self.animation.stop()
        if reduce_motion_enabled():
            self._value(target)
            return
        self.animation.setDuration(duration)
        self.animation.setStartValue(self.amount)
        self.animation.setEndValue(float(target))
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.snapshot is not None:
            painter.setOpacity(self.amount)
            painter.drawPixmap(self.rect(), self.snapshot)
        else:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            if self.dim:
                painter.fillRect(self.rect(), QColor(0, 0, 0, round(75 * self.amount)))
                return
            color = QColor(themed_color("#79d8fa"))
            color.setAlphaF(max(0.0, min(0.45, self.amount * 0.45)))
            painter.setPen(color)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 7, 7)

    def finish(self):
        self.animation.stop()
        self.hide()


class AnimatedProgressBar(QProgressBar):
    """Keep the actual value/signals immediate; only interpolate the painted fill."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._painted_value = self.value()
        self._fill_animation = QVariantAnimation(self)
        self._fill_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fill_animation.setDuration(220)
        self._fill_animation.valueChanged.connect(self._paint_value)
        self.valueChanged.connect(self._changed)

    def _paint_value(self, value):
        self._painted_value = int(value)
        self.update()

    def _changed(self, value):
        self._fill_animation.stop()
        if not self.isVisible() or reduce_motion_enabled() or self.maximum() == self.minimum():
            self._paint_value(value)
            return
        self._fill_animation.setStartValue(max(self.minimum(), self._painted_value))
        self._fill_animation.setEndValue(value)
        self._fill_animation.start()

    def paintEvent(self, event):
        option = QStyleOptionProgressBar()
        self.initStyleOption(option)
        if self._fill_animation.state() == QVariantAnimation.State.Running:
            option.progress = self._painted_value
        painter = QPainter(self)
        self.style().drawControl(QStyle.ControlElement.CE_ProgressBar, option, painter, self)

    def hideEvent(self, event):
        self._fill_animation.stop()
        self._paint_value(self.value())
        super().hideEvent(event)


class AnimatedDialog(QDialog):
    """Finish a modal once, after a brief exit fade; reduced motion is immediate."""

    def done(self, result):
        if getattr(self, "_astral_closing", False):
            return
        if not self.isVisible() or reduce_motion_enabled():
            super().done(result)
            return
        self._astral_closing = True
        self._astral_dialog_result = result
        self._astral_was_enabled = self.isEnabled()
        self.setEnabled(False)
        entering = getattr(self, "_astral_window_animation", None)
        if entering is not None:
            entering.stop()
        animation = getattr(self, "_astral_exit_animation", None)
        if animation is None:
            animation = QVariantAnimation(self)
            animation.setEasingCurve(QEasingCurve.Type.InCubic)
            animation.valueChanged.connect(self.setWindowOpacity)
            animation.finished.connect(self._finish_done)
            self._astral_exit_animation = animation
        animation.setDuration(120)
        animation.setStartValue(self.windowOpacity())
        animation.setEndValue(0.0)
        animation.start()

    def _finish_done(self):
        self._astral_exit_animation.stop()
        super().done(self._astral_dialog_result)
        self._astral_closing = False
        self.setEnabled(self._astral_was_enabled)
        self.setWindowOpacity(1.0)

    def closeEvent(self, event):
        if self.isVisible() and not reduce_motion_enabled():
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)


class AnimatedStack(QStackedWidget):
    """Reveal the live destination beneath one cached frame of the outgoing page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._transition = None

    def _finish_transition(self):
        if self._transition is not None:
            self._transition.finish()
            self._transition.deleteLater()
            self._transition = None

    def setCurrentIndex(self, index):
        if index == self.currentIndex() or not 0 <= index < self.count():
            return
        self._finish_transition()
        old = self.currentWidget()
        snapshot = (
            old.grab() if old is not None and self.isVisible()
            and not reduce_motion_enabled() else None
        )
        super().setCurrentIndex(index)
        if snapshot is None or snapshot.isNull():
            return
        layer = MotionLayer(self, snapshot=snapshot)
        layer.amount = 1.0
        self._transition = layer
        layer.animation.finished.connect(self._finish_transition)
        layer.show()
        layer.raise_()
        layer.animate(0.0, 190)

    def setCurrentWidget(self, widget):
        self.setCurrentIndex(self.indexOf(widget))

    def resizeEvent(self, event):
        self._finish_transition()
        super().resizeEvent(event)

    def hideEvent(self, event):
        self._finish_transition()
        super().hideEvent(event)


def animate_width(widget, target):
    animation = getattr(widget, "_astral_width_animation", None)
    if animation is None:
        animation = QVariantAnimation(widget)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.valueChanged.connect(lambda value: widget.setFixedWidth(int(value)))
        widget._astral_width_animation = animation
    animation.stop()
    widget._astral_width_target = target
    if reduce_motion_enabled() or not widget.isVisible():
        widget.setFixedWidth(target)
        return
    animation.setDuration(150)
    animation.setStartValue(widget.width())
    animation.setEndValue(target)
    animation.start()


class MotionController(QObject):
    """Adds feedback to ordinary buttons and entry fades to dialogs/popups."""

    def eventFilter(self, watched, event):
        kind = event.type()
        if watched is self.parent() and kind == QEvent.Type.DynamicPropertyChange:
            if bytes(event.propertyName()) == b"astralReduceMotion" and reduce_motion_enabled():
                self.finish_all()
        if not isinstance(watched, QWidget):
            return False
        if isinstance(watched, QScrollBar) and kind in {QEvent.Type.Polish, QEvent.Type.Show}:
            from app.ui.scrollbars import enhance_scrollbar
            enhance_scrollbar(watched)
        if kind == QEvent.Type.Show and isinstance(watched, (QDialog, QMenu)):
            self._show_window(watched)
        elif kind == QEvent.Type.Hide:
            animation = getattr(watched, "_astral_window_animation", None)
            if animation is not None:
                animation.stop()
                watched.setWindowOpacity(1.0)
            dim = getattr(watched, "_astral_dim", None)
            if dim is not None:
                dim.finish()
                dim.deleteLater()
                watched._astral_dim = None
        if isinstance(watched, QPushButton):
            # These controls already have custom animated painting.
            if watched.__class__.__name__ in {"AnimatedSearchButton"}:
                return False
            layer = getattr(watched, "_astral_feedback", None)
            if kind in {QEvent.Type.Enter, QEvent.Type.MouseButtonPress, QEvent.Type.FocusIn}:
                if watched.isEnabled() and not reduce_motion_enabled():
                    if layer is None:
                        layer = MotionLayer(watched)
                        watched._astral_feedback = layer
                    layer.setGeometry(watched.rect())
                    layer.show()
                    layer.raise_()
                    layer.animate(1.0 if kind == QEvent.Type.MouseButtonPress else 0.5, 100)
            elif layer is not None:
                if kind == QEvent.Type.Leave:
                    layer.animate(0.0, 120)
                elif kind in {QEvent.Type.FocusOut, QEvent.Type.MouseButtonRelease}:
                    layer.animate(0.5 if watched.underMouse() else 0.0, 150)
                elif kind in {QEvent.Type.Hide, QEvent.Type.EnabledChange}:
                    layer.finish()
                    layer.amount = 0.0
                elif kind == QEvent.Type.Resize:
                    layer.setGeometry(watched.rect())
        return False

    def _show_window(self, window):
        if not window.isWindow() or reduce_motion_enabled() or hasattr(window, "_animate_open"):
            return
        owner = window.parentWidget()
        if isinstance(window, AnimatedDialog) and window.isModal() and owner is not None:
            owner = owner.window()
            if owner.isVisible():
                dim = MotionLayer(owner, dim=True)
                window._astral_dim = dim
                dim.show()
                dim.raise_()
                dim.animate(1.0, 170)
        # Popups retain their native focus, placement, and dismissal behavior.
        animation = getattr(window, "_astral_window_animation", None)
        if animation is None:
            animation = QVariantAnimation(window)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.valueChanged.connect(window.setWindowOpacity)
            window._astral_window_animation = animation
        animation.stop()
        window.setWindowOpacity(0.0)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setDuration(170)
        animation.start()

    def finish_all(self):
        for widget in QApplication.allWidgets():
            scrollbar = getattr(widget, "_astral_scrollbar", None)
            if scrollbar is not None:
                scrollbar.finish_motion()
            if isinstance(widget, MotionLayer):
                widget.finish()
            if isinstance(widget, AnimatedStack):
                widget._finish_transition()
            if isinstance(widget, AnimatedProgressBar):
                widget._fill_animation.stop()
                widget._paint_value(widget.value())
            if isinstance(widget, AnimatedDialog) and getattr(widget, "_astral_closing", False):
                widget._finish_done()
            animation = getattr(widget, "_astral_width_animation", None)
            if animation is not None:
                animation.stop()
                widget.setFixedWidth(widget._astral_width_target)
            animation = getattr(widget, "_astral_window_animation", None)
            if animation is not None:
                animation.stop()
                widget.setWindowOpacity(1.0)


def install_motion():
    app = QApplication.instance()
    if app is not None and not hasattr(app, "_astral_motion"):
        app._astral_motion = MotionController(app)
        app.installEventFilter(app._astral_motion)
        from app.ui.scrollbars import enhance_scrollbar
        for widget in app.allWidgets():
            if isinstance(widget, QScrollBar):
                enhance_scrollbar(widget)


def reveal_image(widget):
    """A short placeholder-to-image fade, without a second network request."""
    previous = getattr(widget, "_astral_image_layer", None)
    if previous is not None:
        previous.finish()
        previous.deleteLater()
        widget._astral_image_layer = None
    if not widget.isVisible() or reduce_motion_enabled():
        return
    # Capture the current placeholder before the caller applies the new pixmap.
    layer = MotionLayer(widget, snapshot=widget.grab())
    widget._astral_image_layer = layer
    layer.amount = 1.0
    layer.animation.finished.connect(layer.hide)
    layer.show()
    layer.raise_()
    layer.animate(0.0, 160)
