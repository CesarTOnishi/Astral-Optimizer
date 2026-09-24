from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QPoint, Qt
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

from app.activity_log import ActivityEvent, ActivityLog
from app.ui.icons import set_button_icon


_CATEGORY_ICONS = {
    "account": "↻",
    "relics": "◇",
    "warps": "✦",
    "backup": "☁",
    "build": "▣",
    "update": "↑",
    "catalog": "▤",
}


class ActivityHistoryButton(QPushButton):
    """Acesso ao histórico persistente de atividades recentes."""

    def __init__(
        self,
        activity_log: ActivityLog,
        owner_provider: Callable[[], int],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.activity_log = activity_log
        self.owner_provider = owner_provider
        self.setObjectName("activityHistoryButton")
        self.setFixedSize(36, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Histórico de atividades")
        set_button_icon(self, "history")
        self.clicked.connect(self.open_menu)

    def open_menu(self) -> None:
        menu = QMenu(self)
        menu.setObjectName("activityHistoryMenu")
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._add_header(menu)
        events = self.activity_log.events(self.owner_provider(), limit=10)
        if not events:
            action = QWidgetAction(menu)
            empty = QLabel(
                "Nenhuma atividade registrada ainda.\n"
                "Sincronizações, importações e exports aparecerão aqui."
            )
            empty.setObjectName("activityHistoryEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFixedSize(430, 90)
            action.setDefaultWidget(empty)
            menu.addAction(action)
        else:
            for event in events:
                action = QWidgetAction(menu)
                action.setDefaultWidget(self._event_row(event))
                menu.addAction(action)
        anchor = self.mapToGlobal(QPoint(self.width(), self.height()))
        menu.popup(QPoint(anchor.x() - menu.sizeHint().width(), anchor.y() + 4))

    @staticmethod
    def _add_header(menu: QMenu) -> None:
        action = QWidgetAction(menu)
        header = QFrame()
        header.setObjectName("activityHistoryHeader")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(13, 10, 13, 9)
        layout.setSpacing(2)
        title = QLabel("HISTÓRICO DE ATIVIDADES")
        title.setObjectName("activityHistoryTitle")
        summary = QLabel("Eventos recentes salvos neste computador")
        summary.setObjectName("activityHistorySummary")
        layout.addWidget(title)
        layout.addWidget(summary)
        action.setDefaultWidget(header)
        menu.addAction(action)

    @staticmethod
    def _event_row(event: ActivityEvent) -> QWidget:
        row = QFrame()
        row.setObjectName("activityHistoryRow")
        row.setProperty("kind", event.kind)
        row.setFixedWidth(440)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(11, 9, 12, 9)
        layout.setSpacing(10)

        icon = QLabel(_CATEGORY_ICONS.get(event.category, "•"))
        icon.setObjectName("activityHistoryIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(28, 28)
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)

        content = QVBoxLayout()
        content.setSpacing(2)
        heading = QHBoxLayout()
        title = QLabel(event.title)
        title.setObjectName("activityHistoryEventTitle")
        timestamp = QLabel(_format_timestamp(event.created_at))
        timestamp.setObjectName("activityHistoryTime")
        heading.addWidget(title)
        heading.addStretch(1)
        heading.addWidget(timestamp)
        message = QLabel(event.message)
        message.setObjectName("activityHistoryMessage")
        message.setWordWrap(True)
        content.addLayout(heading)
        content.addWidget(message)
        layout.addLayout(content, 1)
        return row


def _format_timestamp(value: str) -> str:
    try:
        moment = datetime.fromisoformat(value).astimezone()
    except (TypeError, ValueError):
        return value
    today = datetime.now().astimezone().date()
    if moment.date() == today:
        return f"Hoje, {moment:%H:%M}"
    if (today - moment.date()).days == 1:
        return f"Ontem, {moment:%H:%M}"
    return moment.strftime("%d/%m/%Y · %H:%M")
