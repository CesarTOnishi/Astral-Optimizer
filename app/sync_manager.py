from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal


@dataclass(frozen=True, slots=True)
class BackgroundTask:
    """Snapshot de uma tarefa exibida na central de segundo plano."""

    key: str
    title: str
    message: str
    state: str
    details: str = ""
    retryable: bool = False
    sequence: int = 0


_TASK_TITLES = {
    "account": "Conta",
    "catalog": "Catálogo",
    "benchmark": "Benchmark",
    "onedrive-backup": "Backup",
    "warp-import": "Histórico de Saltos",
    "update-check": "Atualizações",
    "character": "Build do personagem",
    "page": "Aplicativo",
}


def _task_title(key: str) -> str:
    family = key.split(":", 1)[0]
    return _TASK_TITLES.get(family, family.replace("-", " ").title())


class BackgroundSyncManager(QObject):
    """Centraliza o estado e o histórico das tarefas em segundo plano."""

    changed = Signal(str, str, int)
    tasks_changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tasks: OrderedDict[str, str] = OrderedDict()
        self._records: OrderedDict[str, BackgroundTask] = OrderedDict()
        self._notice_generation = 0
        self._sequence = 0

    @property
    def active_count(self) -> int:
        return len(self._tasks)

    @property
    def records(self) -> tuple[BackgroundTask, ...]:
        records = sorted(
            self._records.values(),
            key=lambda item: (item.state == "active", item.sequence),
            reverse=True,
        )
        return tuple(records)

    def begin(
        self,
        key: str,
        message: str,
        *,
        title: str | None = None,
        details: str = "",
        retryable: bool = False,
    ) -> None:
        self._notice_generation += 1
        self._tasks.pop(key, None)
        self._tasks[key] = message
        previous = self._records.get(key)
        self._set_record(
            key,
            title or (previous.title if previous else _task_title(key)),
            message,
            "active",
            details,
            retryable or bool(previous and previous.retryable),
        )
        self._emit_active()

    def update(self, key: str, message: str, *, details: str = "") -> None:
        if key not in self._tasks:
            self.begin(key, message, details=details)
            return
        self._tasks[key] = message
        self._tasks.move_to_end(key)
        previous = self._records.get(key)
        self._set_record(
            key,
            previous.title if previous else _task_title(key),
            message,
            "active",
            details or (previous.details if previous else ""),
            bool(previous and previous.retryable),
        )
        self._emit_active()

    def finish(self, key: str, message: str = "Sincronizado") -> None:
        was_active = key in self._tasks
        self._tasks.pop(key, None)
        previous = self._records.get(key)
        # O encerramento do worker chega após o sinal de falha em alguns fluxos.
        if not was_active and previous is not None and previous.state == "error":
            return
        self._set_record(
            key,
            previous.title if previous else _task_title(key),
            message,
            "success",
            previous.details if previous else "",
            bool(previous and previous.retryable),
        )
        if self._tasks:
            self._emit_active()
        else:
            self._show_temporary("success", message)

    def fail(
        self,
        key: str,
        message: str = "Falha na sincronização",
        *,
        details: str = "",
        retryable: bool = True,
    ) -> None:
        was_active = key in self._tasks
        self._tasks.pop(key, None)
        previous = self._records.get(key)
        error_details = details or message
        if not was_active and previous is not None and previous.state == "error":
            error_details = previous.details or error_details
        self._set_record(
            key,
            previous.title if previous else _task_title(key),
            message,
            "error",
            error_details,
            retryable,
        )
        if self._tasks:
            self._emit_active()
        else:
            self._show_temporary("error", message, duration=4500)

    def clear_finished(self) -> None:
        active = set(self._tasks)
        self._records = OrderedDict(
            (key, record)
            for key, record in self._records.items()
            if key in active or record.state == "error"
        )
        self.tasks_changed.emit()

    def _set_record(
        self,
        key: str,
        title: str,
        message: str,
        state: str,
        details: str,
        retryable: bool,
    ) -> None:
        self._sequence += 1
        self._records.pop(key, None)
        self._records[key] = BackgroundTask(
            key, title, message, state, details, retryable, self._sequence
        )
        while len(self._records) > 20:
            removable = next(
                (
                    record_key
                    for record_key, record in self._records.items()
                    if record.state != "active"
                ),
                None,
            )
            if removable is None:
                break
            self._records.pop(removable, None)
        self.tasks_changed.emit()

    def _emit_active(self) -> None:
        if not self._tasks:
            self.changed.emit("idle", "Sincronizado", 0)
            return
        message = next(reversed(self._tasks.values()))
        self.changed.emit("syncing", message, len(self._tasks))

    def _show_temporary(
        self, state: str, message: str, duration: int = 1800
    ) -> None:
        self._notice_generation += 1
        generation = self._notice_generation
        self.changed.emit(state, message, 0)
        QTimer.singleShot(duration, lambda: self._clear_notice(generation))

    def _clear_notice(self, generation: int) -> None:
        if generation != self._notice_generation:
            return
        if self._tasks:
            self._emit_active()
        else:
            self.changed.emit("idle", "Sincronizado", 0)
