from __future__ import annotations

from collections import OrderedDict

from PySide6.QtCore import QObject, QTimer, Signal


class BackgroundSyncManager(QObject):
    """Centraliza o estado visual das tarefas executadas em segundo plano."""

    changed = Signal(str, str, int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tasks: OrderedDict[str, str] = OrderedDict()
        self._notice_generation = 0

    @property
    def active_count(self) -> int:
        return len(self._tasks)

    def begin(self, key: str, message: str) -> None:
        self._notice_generation += 1
        self._tasks.pop(key, None)
        self._tasks[key] = message
        self._emit_active()

    def update(self, key: str, message: str) -> None:
        if key not in self._tasks:
            self.begin(key, message)
            return
        self._tasks[key] = message
        self._tasks.move_to_end(key)
        self._emit_active()

    def finish(self, key: str, message: str = "Sincronizado") -> None:
        self._tasks.pop(key, None)
        if self._tasks:
            self._emit_active()
        else:
            self._show_temporary("success", message)

    def fail(self, key: str, message: str = "Falha na sincronização") -> None:
        self._tasks.pop(key, None)
        if self._tasks:
            self._emit_active()
        else:
            self._show_temporary("error", message, duration=4500)

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
