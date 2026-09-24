from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from PySide6.QtCore import QSettings


SESSION_SCHEMA_VERSION = 1
VALID_PAGES = frozenset(
    {
        "home",
        "builds",
        "own_builds",
        "warps",
        "planner",
        "relics",
        "dashboard",
        "friends",
        "catalog",
        "diagnostics",
        "whats_new",
    }
)
VALID_VALUE_KEYS = frozenset(
    {
        "warps.uid", "warps.banner", "warps.edition", "planner.strategy",
        "relics.character", "relics.status", "relics.slot",
        "relics.relic_set", "relics.ornament_set", "relics.sort",
        "catalog.mode", "catalog.search", "catalog.path", "catalog.rarity",
    }
)


@dataclass(frozen=True, slots=True)
class ResumeState:
    page: str = "home"
    uid: str = ""
    character_id: str = ""
    values: dict[str, str] = field(default_factory=dict)
    scrolls: dict[str, int] = field(default_factory=dict)


class SessionStateStore:
    """Persiste somente o estado de navegação, isolado por perfil local."""

    def __init__(self, settings: QSettings | None = None) -> None:
        self.settings = settings or QSettings("AstralOptimizer", "Session State")

    @staticmethod
    def _key(owner_id: int) -> str:
        return f"profiles/{max(int(owner_id), 0)}/resume"

    def load(self, owner_id: int) -> ResumeState:
        raw = self.settings.value(self._key(owner_id), "")
        if not raw or len(str(raw)) > 100_000:
            return ResumeState()
        try:
            payload = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return ResumeState()
        if not isinstance(payload, dict):
            return ResumeState()

        page = payload.get("page", "home")
        if not isinstance(page, str) or page not in VALID_PAGES:
            page = "home"
        uid = self._clean_text(payload.get("uid"), 12)
        if uid and (not uid.isdigit() or len(uid) != 9):
            uid = ""
        character_id = self._clean_text(payload.get("character_id"), 80)
        return ResumeState(
            page=page,
            uid=uid,
            character_id=character_id,
            values=self._clean_values(payload.get("values")),
            scrolls=self._clean_scrolls(payload.get("scrolls")),
        )

    def exists(self, owner_id: int) -> bool:
        return bool(self.settings.value(self._key(owner_id), ""))

    def save(self, owner_id: int, state: ResumeState) -> None:
        payload = {
            "schema": SESSION_SCHEMA_VERSION,
            "page": state.page if state.page in VALID_PAGES else "home",
            "uid": (
                state.uid
                if isinstance(state.uid, str)
                and state.uid.isdigit()
                and len(state.uid) == 9
                else ""
            ),
            "character_id": self._clean_text(state.character_id, 80),
            "values": self._clean_values(state.values),
            "scrolls": self._clean_scrolls(state.scrolls),
        }
        self.settings.setValue(
            self._key(owner_id),
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        )
        self.settings.sync()

    @staticmethod
    def _clean_text(value: Any, limit: int) -> str:
        return value[:limit] if isinstance(value, str) else ""

    @classmethod
    def _clean_values(cls, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        clean: dict[str, str] = {}
        for key, item in value.items():
            if key not in VALID_VALUE_KEYS or not isinstance(item, str):
                continue
            safe_key = cls._clean_text(key, 80)
            safe_value = cls._clean_text(item, 500)
            if safe_key:
                clean[safe_key] = safe_value
        return clean

    @staticmethod
    def _clean_scrolls(value: Any) -> dict[str, int]:
        if not isinstance(value, dict):
            return {}
        clean: dict[str, int] = {}
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 80 or isinstance(item, bool):
                continue
            try:
                position = int(item)
            except (TypeError, ValueError):
                continue
            clean[key] = min(max(position, 0), 10_000_000)
        return clean
