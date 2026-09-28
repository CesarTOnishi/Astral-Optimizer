from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time

import enka
from PySide6.QtCore import QObject, QThread, QTimer, Signal

from app.config import APP_USER_AGENT
from app.catalog.repository import CatalogRepository
from app.catalog.sync import ensure_relic_set_catalog
from app.models import AccountSummary
from app.parsers import account_from_showcase


@dataclass(frozen=True, slots=True)
class AccountFetchError:
    code: str
    title: str
    message: str
    details: str
    retryable: bool = True
    check_connection: bool = False

    @property
    def diagnostic_details(self) -> str:
        return (
            f"Categoria: {self.code}\n"
            f"Tipo técnico: {self.title}\n"
            f"Mensagem: {self.message}\n"
            f"Detalhes: {self.details or 'Não informados'}"
        )


def classify_account_error(error: BaseException) -> AccountFetchError:
    details = f"{type(error).__name__}: {error}"
    if isinstance(error, GameAssetsUnavailableError):
        return AccountFetchError(
            "game_assets_unavailable",
            "Dados do jogo ainda indisponíveis",
            str(error),
            details,
        )
    if isinstance(error, enka.errors.WrongUIDFormatError):
        return AccountFetchError(
            "invalid_uid",
            "UID inválida",
            "A UID precisa conter exatamente 9 números.",
            details,
            retryable=False,
        )
    if isinstance(error, enka.errors.PlayerDoesNotExistError):
        return AccountFetchError(
            "uid_not_found",
            "Conta não encontrada",
            "Confira a UID e confirme que o perfil existe no servidor selecionado.",
            details,
            retryable=False,
        )
    if isinstance(error, enka.errors.RateLimitedError):
        return AccountFetchError(
            "rate_limited",
            "Limite temporário atingido",
            "O Enka.Network recebeu consultas demais. Aguarde um pouco e tente novamente.",
            details,
        )
    if isinstance(
        error,
        (
            enka.errors.GameMaintenanceError,
            enka.errors.GatewayTimeoutError,
            enka.errors.GeneralServerError,
        ),
    ):
        return AccountFetchError(
            "service_unavailable",
            "Serviço temporariamente indisponível",
            "O Enka.Network ou o jogo está em manutenção ou instável. Seus dados salvos não foram alterados.",
            details,
        )
    if isinstance(error, enka.errors.APIRequestTimeoutError):
        return AccountFetchError(
            "timeout",
            "A consulta demorou demais",
            "O Enka.Network não respondeu a tempo. Verifique sua conexão ou tente novamente.",
            details,
            check_connection=True,
        )
    if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
        return AccountFetchError(
            "timeout",
            "A consulta demorou demais",
            "O Enka.Network não respondeu a tempo. Verifique sua conexão ou tente novamente.",
            details,
            check_connection=True,
        )
    error_chain: list[BaseException] = []
    current: BaseException | None = error
    while current is not None and current not in error_chain:
        error_chain.append(current)
        current = current.__cause__ or current.__context__
    network_hint = " ".join(
        f"{type(item).__name__} {item}" for item in error_chain
    ).casefold()
    if isinstance(error, (ConnectionError, OSError)) or any(
        marker in network_hint
        for marker in (
            "connectionerror",
            "connecterror",
            "clientconnector",
            "dns",
            "name resolution",
            "network is unreachable",
            "getaddrinfo",
        )
    ):
        return AccountFetchError(
            "network",
            "Sem conexão com o serviço",
            "Não foi possível alcançar o Enka.Network. Verifique sua conexão com a internet.",
            details,
            check_connection=True,
        )
    if isinstance(error, enka.errors.EnkaAPIError):
        return AccountFetchError(
            "service_unavailable",
            "Falha no serviço de consulta",
            "O Enka.Network retornou uma falha temporária. Seus dados salvos não foram alterados.",
            details,
        )
    return AccountFetchError(
        "unknown",
        "Não foi possível consultar a conta",
        "Ocorreu uma falha inesperada durante a consulta. Você pode tentar novamente ou copiar os detalhes.",
        details,
    )


def ensure_account_error(error: object) -> AccountFetchError:
    if isinstance(error, AccountFetchError):
        return error
    message = str(error).strip() or "Falha desconhecida durante a consulta."
    return AccountFetchError(
        "unknown",
        "Não foi possível consultar a conta",
        message,
        message,
    )


class GameAssetsUnavailableError(RuntimeError):
    """Os dados locais do jogo não cobrem o personagem ou equipamento consultado."""


def _raw_has_unknown_assets(client: enka.HSRClient, payload: dict) -> bool:
    """Evita processar uma build com IDs que o cache do enka ainda não conhece."""
    assets = client._assets
    profile = payload.get("detailInfo") or {}
    for character in profile.get("avatarDetailList") or payload.get("avatarInfoList") or []:
        if assets.character_data.get(str(character.get("avatarId", ""))) is None:
            return True
        cone = character.get("equipment") or {}
        if cone and assets.light_cones_data.get(str(cone.get("tid", ""))) is None:
            return True
        for relic in character.get("relicList") or []:
            if assets.relic_data.get(str(relic.get("tid", ""))) is None:
                return True
    return False


def _showcase_has_missing_assets(showcase: object) -> bool:
    for character in showcase.characters:
        if not character.name or character.name.isdecimal() or not character.stats:
            return True
        if character.light_cone and (
            not character.light_cone.name
            or character.light_cone.name.isdecimal()
            or character.light_cone.icon.light_cone_id == 0
        ):
            return True
        if any(
            not relic.set_name or relic.set_name.isdecimal() or not relic.icon
            for relic in character.relics
        ):
            return True
    return False


async def _complete_showcase_names(showcase: object) -> None:
    """Complementa traduções ainda ausentes no mapa de texto do Enka."""
    if not any(
        character.name.isdecimal()
        or (character.light_cone and character.light_cone.name.isdecimal())
        or any(relic.set_name.isdecimal() for relic in character.relics)
        for character in showcase.characters
    ):
        return

    catalog = CatalogRepository()
    missing_sets = {
        str(relic.set_id)
        for character in showcase.characters
        for relic in character.relics
        if relic.set_name.isdecimal() and not catalog.relic_set_name(str(relic.set_id))
    }
    if missing_sets:
        try:
            await asyncio.to_thread(ensure_relic_set_catalog, missing_sets)
        except (OSError, ValueError):
            pass  # A validação abaixo informa que os dados continuam indisponíveis.
        catalog.reload()

    character_names = {item.id: item.name for item in catalog.characters()}
    cone_names = {item.id: item.name for item in catalog.light_cones()}
    for character in showcase.characters:
        if character.name.isdecimal():
            character.name = character_names.get(str(character.id), character.name)
        cone = character.light_cone
        if cone and cone.name.isdecimal():
            cone.name = cone_names.get(str(cone.id), cone.name)
        for relic in character.relics:
            if relic.set_name.isdecimal():
                relic.set_name = catalog.relic_set_name(str(relic.set_id)) or relic.set_name


class AccountFetchWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(object)

    def __init__(self, uid: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.uid = uid

    def run(self) -> None:
        try:
            account = asyncio.run(self._fetch())
        except Exception as exc:  # Mantém a interface utilizável em falhas externas.
            self.failed.emit(classify_account_error(exc))
        else:
            self.succeeded.emit(account)

    async def _fetch(self) -> AccountSummary:
        headers = {"User-Agent": APP_USER_AGENT}
        async with enka.HSRClient(
            enka.hsr.Language.PORTUGUESE,
            headers=headers,
            timeout=15,
        ) as client:
            raw = await client.fetch_showcase(self.uid, raw=True)
            refreshed = False
            if _raw_has_unknown_assets(client, raw):
                await client.update_assets()
                refreshed = True
            showcase = client.parse_showcase(raw)
            await _complete_showcase_names(showcase)
            if _showcase_has_missing_assets(showcase) and not refreshed:
                await client.update_assets()
                showcase = client.parse_showcase(raw)
                await _complete_showcase_names(showcase)
            if _showcase_has_missing_assets(showcase):
                raise GameAssetsUnavailableError(
                    "Os dados atuais do jogo ainda não incluem todos os personagens, "
                    "cones ou relíquias desta conta. Tente consultar novamente mais tarde."
                )
        return account_from_showcase(showcase)


class EnkaClient(QObject):
    account_loaded = Signal(object, str)
    request_failed = Signal(object)
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
        # Uma solicitação mais nova sempre vence, inclusive para a mesma UID
        # após troca de perfil. O resultado anterior não deve ser atribuído ao
        # novo contexto apenas porque os números da UID coincidem.
        if self.pending_request is not None:
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
