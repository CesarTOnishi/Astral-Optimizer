"""Animated scrollbar painting without replacing native scrolling behavior."""
from PySide6.QtCore import QEvent, QEasingCurve, QObject, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QScrollBar, QStyle, QStyleOptionSlider

from app.preferences import reduce_motion_enabled, themed_color


class ScrollbarAppearance(QObject):
    def __init__(self, bar: QScrollBar):
        super().__init__(bar)
        self.bar = bar
        self.hovered = False
        self.activity = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._set_activity)
        self._refresh_colors()
        bar.installEventFilter(self)
        bar.sliderPressed.connect(self._update_activity)
        bar.sliderReleased.connect(self._update_activity)

    def _refresh_colors(self):
        self.color = QColor(themed_color("#819ab8"))
        self.accent = QColor(themed_color("#8bd9ef"))

    def _set_activity(self, value):
        self.activity = float(value)
        self.bar.update()

    def _target_activity(self):
        return 1.0 if self.hovered or self.bar.isSliderDown() or self.bar.hasFocus() else 0.0

    def _update_activity(self):
        self.animation.stop()
        target = self._target_activity()
        if reduce_motion_enabled() or not self.bar.isVisible():
            self._set_activity(target)
            return
        self.animation.setDuration(110 if target else 170)
        self.animation.setStartValue(self.activity)
        self.animation.setEndValue(target)
        self.animation.start()

    def finish_motion(self):
        self.animation.stop()
        self._set_activity(self._target_activity())

    def handle_rect(self):
        # Use the native style geometry, including RTL and inverted appearance.
        option = QStyleOptionSlider()
        self.bar.initStyleOption(option)
        return self.bar.style().subControlRect(
            QStyle.ComplexControl.CC_ScrollBar, option,
            QStyle.SubControl.SC_ScrollBarSlider, self.bar,
        )

    def eventFilter(self, watched, event):
        if not hasattr(self, "animation"):
            return False
        kind = event.type()
        if kind == QEvent.Type.Paint:
            self._paint()
            return True
        if kind == QEvent.Type.Enter:
            self.hovered = True
            self._update_activity()
        elif kind == QEvent.Type.Leave:
            self.hovered = False
            self._update_activity()
        elif kind in {QEvent.Type.FocusIn, QEvent.Type.FocusOut, QEvent.Type.EnabledChange}:
            self._update_activity()
        elif kind == QEvent.Type.Hide:
            self.hovered = False
            self.animation.stop()
            self.activity = 0.0
        elif kind in {QEvent.Type.StyleChange, QEvent.Type.PaletteChange}:
            self._refresh_colors()
            self.bar.update()
        return False

    def _paint(self):
        painter = QPainter(self.bar)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        vertical = self.bar.orientation() == Qt.Orientation.Vertical
        bounds = QRectF(self.bar.rect())
        if self.activity > 0:
            rail = QColor(self.color)
            rail.setAlpha(round(20 * self.activity))
            painter.setBrush(rail)
            painter.drawRoundedRect(bounds.adjusted(1, 1, -1, -1), 6, 6)
        handle = QRectF(self.handle_rect())
        if handle.isEmpty():
            return
        thickness = 4.0 + 3.0 * self.activity
        if vertical:
            thickness = min(thickness, handle.width())
            handle.setLeft(handle.center().x() - thickness / 2)
            handle.setWidth(thickness)
        else:
            thickness = min(thickness, handle.height())
            handle.setTop(handle.center().y() - thickness / 2)
            handle.setHeight(thickness)
        color = QColor(self.accent if self.bar.isSliderDown() else self.color)
        color.setAlpha(65 if not self.bar.isEnabled() else round(125 + 105 * self.activity))
        painter.setBrush(color)
        painter.drawRoundedRect(handle, thickness / 2, thickness / 2)


def enhance_scrollbar(bar: QScrollBar):
    if not hasattr(bar, "_astral_scrollbar"):
        # Qt can send Polish/Show recursively while attaching the controller.
        bar._astral_scrollbar = None
        try:
            bar._astral_scrollbar = ScrollbarAppearance(bar)
        except Exception:
            del bar._astral_scrollbar
            raise
