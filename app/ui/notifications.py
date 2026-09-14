from __future__ import annotations

from dataclasses import dataclass
from app.ui.icons import set_button_icon

from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)


@dataclass(slots=True)
class AppNotification:
    key: str
    title: str
    message: str
    kind: str = "info"
    unread: bool = True


class NotificationCenter(QObject):
    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[AppNotification] = []

    @property
    def items(self) -> tuple[AppNotification, ...]:
        return tuple(self._items)

    @property
    def unread_count(self) -> int:
        return sum(item.unread for item in self._items)

    def add(self, key: str, title: str, message: str, kind: str = "info") -> None:
        self._items = [item for item in self._items if item.key != key]
        self._items.insert(0, AppNotification(key, title, message, kind))
        self._items = self._items[:30]
        self.changed.emit()

    def remove(self, key: str) -> None:
        remaining = [item for item in self._items if item.key != key]
        if len(remaining) != len(self._items):
            self._items = remaining
            self.changed.emit()

    def mark_all_read(self) -> None:
        if not self.unread_count:
            return
        for item in self._items:
            item.unread = False
        self.changed.emit()


class NotificationBell(QPushButton):
    def __init__(self, center: NotificationCenter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.center = center
        self.setObjectName("notificationBell")
        self.setFixedHeight(30)
        self.setMinimumWidth(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.open_menu)
        self.center.changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        count = self.center.unread_count
        self.setText(str(count) if count else "")
        set_button_icon(self, "bell")
        self.setProperty("unread", count > 0)
        self.setToolTip(
            f"{count} notificação{'ões' if count != 1 else ''} não lida{'s' if count != 1 else ''}"
            if count else "Nenhuma notificação nova"
        )
        self.style().unpolish(self)
        self.style().polish(self)

    def open_menu(self) -> None:
        menu = QMenu(self)
        menu.setObjectName("notificationMenu")
        items = self.center.items
        if not items:
            action = QWidgetAction(menu)
            empty = QLabel("Tudo em ordem por aqui.")
            empty.setObjectName("notificationEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFixedSize(330, 72)
            action.setDefaultWidget(empty)
            menu.addAction(action)
        else:
            for item in items:
                action = QWidgetAction(menu)
                action.setDefaultWidget(self._notification_row(item))
                menu.addAction(action)
        self.center.mark_all_read()
        anchor = self.mapToGlobal(QPoint(self.width(), self.height()))
        menu.popup(QPoint(anchor.x() - menu.sizeHint().width(), anchor.y() + 3))

    @staticmethod
    def _notification_row(item: AppNotification) -> QWidget:
        row = QFrame()
        row.setObjectName("notificationRow")
        row.setProperty("kind", item.kind)
        row.setFixedWidth(340)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(11, 9, 12, 9)
        layout.setSpacing(9)
        icon = QLabel({"success": "✓", "error": "!", "warning": "!"}.get(item.kind, "i"))
        icon.setObjectName("notificationIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(24, 24)
        copy = QVBoxLayout()
        copy.setSpacing(2)
        title = QLabel(item.title)
        title.setObjectName("notificationTitle")
        message = QLabel(item.message)
        message.setObjectName("notificationMessage")
        message.setWordWrap(True)
        copy.addWidget(title)
        copy.addWidget(message)
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(copy, 1)
        return row
