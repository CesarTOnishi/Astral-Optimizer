from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal


@dataclass(frozen=True, slots=True)
class LoadContext:
    owner_id: int
    uid: str
    generation: int


@dataclass(frozen=True, slots=True)
class SectionState:
    name: str
    status: str = "ready"
    message: str = ""
    details: str = ""
    retryable: bool = False


class SectionLoadController(QObject):
    changed = Signal(str, object)
    retry_requested = Signal(str, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._generation = 0
        self.context = LoadContext(0, "", 0)
        self.states: dict[str, SectionState] = {}

    def begin_context(self, owner_id: int, uid: str) -> LoadContext:
        previous_sections = tuple(self.states)
        self._generation += 1
        self.context = LoadContext(max(owner_id, 0), str(uid), self._generation)
        self.states.clear()
        for name in previous_sections:
            self.changed.emit(name, SectionState(name))
        return self.context

    def is_current(self, context: LoadContext) -> bool:
        return context == self.context

    def pending(
        self, name: str, message: str, context: LoadContext | None = None
    ) -> bool:
        return self._set(
            SectionState(name, "pending", message), context or self.context
        )

    def ready(self, name: str, context: LoadContext | None = None) -> bool:
        return self._set(SectionState(name), context or self.context)

    def fail(
        self,
        name: str,
        message: str,
        *,
        details: str = "",
        retryable: bool = True,
        context: LoadContext | None = None,
    ) -> bool:
        return self._set(
            SectionState(name, "error", message, details, retryable),
            context or self.context,
        )

    def request_retry(self, name: str) -> None:
        state = self.states.get(name)
        if state is not None and state.status == "error" and state.retryable:
            self.retry_requested.emit(name, self.context)

    def _set(self, state: SectionState, context: LoadContext) -> bool:
        if not self.is_current(context):
            return False
        self.states[state.name] = state
        self.changed.emit(state.name, state)
        return True


class RelicSyncWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, database: Any, engine: Any, owner_id: int, account: Any) -> None:
        super().__init__()
        self.database = database
        self.engine = engine
        self.owner_id = owner_id
        self.account = account

    def run(self) -> None:
        try:
            before = {
                item.fingerprint: item.current_character_id
                for item in self.database.relics(self.owner_id, self.account.uid)
                if item.current_character_id
            }
            self.database.sync_account(self.owner_id, self.account, self.engine)
            after = {
                item.fingerprint: item.current_character_id
                for item in self.database.relics(self.owner_id, self.account.uid)
                if item.current_character_id
            }
            self.succeeded.emit(
                {
                    "added": len(after.keys() - before.keys()),
                    "removed": len(before.keys() - after.keys()),
                    "moved": sum(
                        before[key] != after[key]
                        for key in before.keys() & after.keys()
                    ),
                    "had_previous": bool(before),
                }
            )
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")
