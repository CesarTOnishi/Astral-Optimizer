"""Responsive build composition without recreating data-bound panels."""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QGridLayout, QSplitter, QSplitterHandle, QWidget


def build_panel_proportions(width: int) -> tuple[float, float, float]:
    """Allocate readable columns as the detail view changes width."""
    if width < 980:
        return 0.23, 0.31, 0.46
    if width < 1200:
        return 0.32, 0.25, 0.43
    return 0.38, 0.22, 0.40


class FixedSplitterHandle(QSplitterHandle):
    """A visual separator that cannot change the automatic column widths."""

    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):  # noqa: N802 - Qt API
        event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt API
        event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt API
        event.accept()

    def mouseDoubleClickEvent(self, event):  # noqa: N802 - Qt API
        event.accept()


class BuildDetailSplitter(QSplitter):
    composition_changed = Signal()

    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)
        self._mode = ""
        self._panels = []
        self._compact = QWidget()
        self._compact_layout = QGridLayout(self._compact)
        self._compact_layout.setContentsMargins(0, 0, 0, 0)
        self._compact_layout.setSpacing(8)
        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.timeout.connect(self.reflow)

    def createHandle(self):  # noqa: N802 - Qt API
        return FixedSplitterHandle(self.orientation(), self)

    def addWidget(self, widget):  # noqa: N802 - Qt API
        self._panels.append(widget)
        return super().addWidget(widget)

    def resizeEvent(self, event):  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._reflow_timer.start(0)

    def reflow(self):
        if len(self._panels) != 3:
            return
        width = self.width()
        mode = "wide" if width >= 660 else "narrow"
        changed = mode != self._mode
        if changed:
            art, summary, relics = self._panels
            if self._mode == "narrow":
                # Preserve widgets, images and scroll positions while reparenting.
                QSplitter.addWidget(self, art)
                QSplitter.addWidget(self, summary)
                QSplitter.addWidget(self, relics)
                self._compact.hide()
                self._compact.setParent(None)
            self.setOrientation(Qt.Orientation.Horizontal)
            if mode == "narrow":
                for item in (art, summary, relics):
                    item.setMinimumHeight(0)
                self._compact_layout.addWidget(art, 0, 0)
                self._compact_layout.addWidget(summary, 1, 0)
                self._compact_layout.addWidget(relics, 2, 0)
                self._compact_layout.setColumnStretch(0, 1)
                self._compact_layout.setColumnStretch(1, 0)
                for row, height in enumerate((340, 640, 580)):
                    self._compact_layout.setRowMinimumHeight(row, height)
                self.setMinimumHeight(1576)
                QSplitter.addWidget(self, self._compact)
                self._compact.show()
            else:
                self.setMinimumHeight(700)
            self._mode = mode
        if mode == "wide":
            self.setSizes([round(width * p) for p in build_panel_proportions(width)])
        elif changed:
            self.setSizes([width])
        self.composition_changed.emit()
