from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.preferences import themed_color


def _color(value: str) -> QColor:
    return QColor(themed_color(value))


class WarpBarChart(QWidget):
    """Compact chart used by the warp-history dashboard."""

    def __init__(
        self, parent: QWidget | None = None, *, horizontal: bool = False
    ) -> None:
        super().__init__(parent)
        self._data: tuple[tuple[str, int], ...] = ()
        self._horizontal = horizontal
        self.setMinimumHeight(190 if horizontal else 175)

    def set_data(self, data: tuple[tuple[str, int], ...]) -> None:
        self._data = data[-8:]
        self.setToolTip("\n".join(
            f"{label}: {value} tiros" for label, value in self._data
        ))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - API Qt
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_background(painter)
        if not self._data:
            painter.setPen(_color("#7889a4"))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, "Sem dados para exibir"
            )
        elif self._horizontal:
            self._draw_horizontal(painter)
        else:
            self._draw_vertical(painter)
        painter.end()

    def _draw_background(self, painter: QPainter) -> None:
        background = QLinearGradient(0, 0, self.width(), self.height())
        background.setColorAt(0, _color("#0c1627"))
        background.setColorAt(1, _color("#101b31"))
        painter.setPen(QPen(_color("#304a70"), 1))
        painter.setBrush(background)
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 10, 10
        )

    @staticmethod
    def _month_label(label: str) -> str:
        try:
            value = datetime.strptime(label, "%Y-%m")
        except ValueError:
            return label
        months = (
            "jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez",
        )
        return f"{months[value.month - 1]}/{str(value.year)[2:]}"

    def _draw_vertical(self, painter: QPainter) -> None:
        maximum = max(value for _label, value in self._data) or 1
        left, right, top, bottom = 12.0, 12.0, 25.0, 31.0
        width = max(1.0, self.width() - left - right)
        height = max(1.0, self.height() - top - bottom)
        slot = width / len(self._data)

        painter.setPen(QPen(_color("#233753"), 1, Qt.PenStyle.DashLine))
        for fraction in (0.25, 0.5, 0.75):
            y = top + height * fraction
            painter.drawLine(int(left), int(y), int(left + width), int(y))

        metrics = painter.fontMetrics()
        for index, (label, value) in enumerate(self._data):
            bar_height = max(3.0, height * value / maximum)
            bar_width = max(10.0, min(38.0, slot * 0.56))
            x = left + index * slot + (slot - bar_width) / 2
            bar = QRectF(x, top + height - bar_height, bar_width, bar_height)
            gradient = QLinearGradient(bar.topLeft(), bar.bottomLeft())
            gradient.setColorAt(
                0, _color("#69c4e8" if index % 2 == 0 else "#9785ee")
            )
            gradient.setColorAt(
                1, _color("#388fc1" if index % 2 == 0 else "#6554ba")
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(bar, 5, 5)
            painter.setPen(_color("#f2f7ff"))
            painter.drawText(
                QRectF(x - 8, bar.top() - 20, bar_width + 16, 17),
                Qt.AlignmentFlag.AlignCenter,
                str(value),
            )
            month = self._month_label(label)
            short = metrics.elidedText(
                month, Qt.TextElideMode.ElideRight, max(12, int(slot - 4))
            )
            painter.setPen(_color("#9fb0ca"))
            painter.drawText(
                QRectF(left + index * slot + 2, top + height + 7, slot - 4, 18),
                Qt.AlignmentFlag.AlignCenter,
                short,
            )

    def _draw_horizontal(self, painter: QPainter) -> None:
        maximum = max(value for _label, value in self._data) or 1
        left = min(180.0, max(105.0, self.width() * 0.36))
        right, top, bottom = 45.0, 10.0, 10.0
        width = max(1.0, self.width() - left - right)
        height = max(1.0, self.height() - top - bottom)
        slot = height / len(self._data)
        metrics = painter.fontMetrics()

        for index, (label, value) in enumerate(self._data):
            y = top + index * slot
            bar_height = max(7.0, min(16.0, slot * 0.5))
            bar_y = y + (slot - bar_height) / 2
            short = metrics.elidedText(
                label, Qt.TextElideMode.ElideRight, max(40, int(left - 23))
            )
            painter.setPen(_color("#a9b8cf"))
            painter.drawText(
                QRectF(10, y, left - 20, slot),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                short,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_color("#182945"))
            painter.drawRoundedRect(QRectF(left, bar_y, width, bar_height), 4, 4)
            fill_width = max(3.0, width * value / maximum)
            gradient = QLinearGradient(left, 0, left + fill_width, 0)
            gradient.setColorAt(0, _color("#3ca1d0"))
            gradient.setColorAt(1, _color("#8572dc"))
            painter.setBrush(gradient)
            painter.drawRoundedRect(
                QRectF(left, bar_y, fill_width, bar_height), 4, 4
            )
            painter.setPen(_color("#eef6ff"))
            painter.drawText(
                QRectF(left + width + 7, y, right - 10, slot),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(value),
            )
