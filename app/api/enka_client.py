from __future__ import annotations

import asyncio
import time

import enka
from PySide6.QtCore import QObject, QThread, QTimer, Signal

from app.config import APP_USER_AGENT
from app.models import AccountSummary
from app.parsers import account_from_showcase


class AccountFetchWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, uid: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.uid = uid

    def run(self) -> None:
        try:
            account = asyncio.run(self._fetch())
        except enka.errors.WrongUIDFormatError:
            self.failed.emit("O UID informado não possui um formato válido.")
        except enka.errors.PlayerDoesNotExistError:
            self.failed.emit("Conta não encontrada ou UID incorreto.")
        except enka.errors.RateLimitedError:
            self.failed.emit("Limite de consultas atingido. Aguarde e tente novamente.")
        except enka.errors.GameMaintenanceError:
            self.failed.emit("O jogo ou o Enka está em manutenção após uma atualização.")
        except enka.errors.APIRequestTimeoutError:
            self.failed.emit("A consulta excedeu o tempo limite. Tente novamente.")
        except Exception as exc:  # Mantém a interface utilizável em falhas externas.
            self.failed.emit(f"Não foi possível consultar a conta: {exc}")
        else:
            self.succeeded.emit(account)

    async def _fetch(self) -> AccountSummary:
        headers = {"User-Agent": APP_USER_AGENT}
        async with enka.HSRClient(
            enka.hsr.Language.PORTUGUESE,
            headers=headers,
            timeout=15,
        ) as client:
            showcase = await client.fetch_showcase(self.uid)
        return account_from_showcase(showcase)


class EnkaClient(QObject):
    account_loaded = Signal(object, str)
    request_failed = Signal(str)
    loading_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.worker: AccountFetchWorker | None = None
        self.cache: dict[str, tuple[float, AccountSummary]] = {}
        self.pending_request: tuple[str, bool] | None = None

    @property
    def is_busy(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def fetch_account(self, uid: str, *, force: bool = False) -> None:
        if self.is_busy:
            if self.worker is not None and self.worker.uid == uid:
                return
            self.pending_request = (uid, force)
            return
        cached = None if force else self.cache.get(uid)
        if cached and cached[0] > time.time():
            remaining = max(round(cached[0] - time.time()), 1)
            self.loading_changed.emit(True)
            QTimer.singleShot(
                35,
                lambda: self._emit_cached_account(uid, cached[1], remaining),
            )
            return

        self.loading_changed.emit(True)
        self.worker = AccountFetchWorker(uid, self)
        self.worker.succeeded.connect(lambda account: self._account_ready(uid, account))
        self.worker.failed.connect(self.request_failed.emit)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _emit_cached_account(
        self, uid: str, account: AccountSummary, remaining: int
    ) -> None:
        current = self.cache.get(uid)
        if current is None or current[1] is not account:
            self.loading_changed.emit(False)
            return
        self.account_loaded.emit(
            account,
            f"Dados em cache. Atualização disponível em {remaining}s.",
        )
        self.loading_changed.emit(False)

    def _account_ready(self, uid: str, account: AccountSummary) -> None:
        self.cache[uid] = (time.time() + account.ttl, account)
        if self.pending_request is not None and self.pending_request[0] != uid:
            return
        if account.characters:
            message = f"{len(account.characters)} personagem(ns) carregado(s) do Showcase."
        else:
            message = "Conta encontrada, mas o Showcase não possui personagens públicos."
        self.account_loaded.emit(account, message)

    def _worker_finished(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        pending = self.pending_request
        self.pending_request = None
        if pending is not None:
            uid, force = pending
            self.fetch_account(uid, force=force)
            return
        self.loading_changed.emit(False)
