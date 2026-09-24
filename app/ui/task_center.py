from __future__ import annotations

from functools import partial

from PySide6.QtCore import QPoint, Qt, Signal
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

from app.sync_manager import BackgroundSyncManager, BackgroundTask
from app.ui.experience import copy_error_details


class BackgroundTaskButton(QPushButton):
    """Indicador clicável que abre as tarefas da sessão atual."""

    retry_requested = Signal(str)

    def __init__(
        self, manager: BackgroundSyncManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setObjectName("syncStatus")
        self.setMinimumHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("status", "idle")
        self.clicked.connect(self.open_menu)

    def open_menu(self) -> None:
        menu = QMenu(self)
        menu.setObjectName("taskCenterMenu")
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._add_header(menu)
        records = self.manager.records
        if not records:
            action = QWidgetAction(menu)
            empty = QLabel(
                "Nenhuma tarefa executada nesta sessão.\n"
                "As sincronizações aparecerão aqui automaticamente."
            )
            empty.setObjectName("taskCenterEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFixedSize(420, 86)
            action.setDefaultWidget(empty)
            menu.addAction(action)
        else:
            for record in records[:10]:
                action = QWidgetAction(menu)
                action.setDefaultWidget(self._task_row(record, menu))
                menu.addAction(action)
        anchor = self.mapToGlobal(QPoint(0, self.height()))
        menu.popup(QPoint(anchor.x(), anchor.y() + 4))

    def _add_header(self, menu: QMenu) -> None:
        action = QWidgetAction(menu)
        header = QFrame()
        header.setObjectName("taskCenterHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(13, 10, 10, 8)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        title = QLabel("TAREFAS EM SEGUNDO PLANO")
        title.setObjectName("taskCenterTitle")
        count = self.manager.active_count
        summary = QLabel(
            f"{count} tarefa{'s' if count != 1 else ''} em andamento"
            if count else "Nenhuma tarefa em andamento"
        )
        summary.setObjectName("taskCenterSummary")
        copy.addWidget(title)
        copy.addWidget(summary)
        layout.addLayout(copy, 1)
        if any(record.state == "success" for record in self.manager.records):
            clear = QPushButton("Limpar concluídas")
            clear.setObjectName("taskCenterClear")
            clear.clicked.connect(self.manager.clear_finished)
            clear.clicked.connect(menu.close)
            layout.addWidget(clear)
        action.setDefaultWidget(header)
        menu.addAction(action)

    def _task_row(self, task: BackgroundTask, menu: QMenu) -> QWidget:
        row = QFrame()
        row.setObjectName("taskCenterRow")
        row.setProperty("state", task.state)
        row.setFixedWidth(430)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(11, 10, 11, 10)
        layout.setSpacing(10)

        icon = QLabel({"active": "↻", "success": "✓", "error": "!"}[task.state])
        icon.setObjectName("taskCenterIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(28, 28)
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)

        content = QVBoxLayout()
        content.setSpacing(3)
        heading = QHBoxLayout()
        title = QLabel(task.title)
        title.setObjectName("taskCenterTaskTitle")
        state = QLabel(
            {"active": "EM ANDAMENTO", "success": "CONCLUÍDO", "error": "FALHOU"}[
                task.state
            ]
        )
        state.setObjectName("taskCenterState")
        state.setProperty("state", task.state)
        heading.addWidget(title)
        heading.addStretch(1)
        heading.addWidget(state)
        message = QLabel(task.message)
        message.setObjectName("taskCenterMessage")
        message.setWordWrap(True)
        content.addLayout(heading)
        content.addWidget(message)

        if task.state == "error":
            actions = QHBoxLayout()
            actions.setSpacing(6)
            if task.retryable:
                retry = QPushButton("Tentar novamente")
                retry.setObjectName("taskCenterAction")
                retry.clicked.connect(partial(self.retry_requested.emit, task.key))
                retry.clicked.connect(menu.close)
                actions.addWidget(retry)
            copy = QPushButton("Copiar detalhes")
            copy.setObjectName("taskCenterAction")
            copy.clicked.connect(
                lambda _checked=False, current=task: copy_error_details(
                    current.details or current.message, current.title
                )
            )
            actions.addWidget(copy)
            actions.addStretch(1)
            content.addLayout(actions)

        layout.addLayout(content, 1)
        return row
