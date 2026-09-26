from __future__ import annotations

from collections import OrderedDict
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from app.models import AccountSummary, CharacterStat, CharacterSummary, RelicSummary
from app.paths import app_data_dir


def default_uid_tabs_path() -> Path:
    return app_data_dir() / "uid_tabs.db"


def _stat_from_dict(data: dict[str, Any]) -> CharacterStat:
    return CharacterStat(
        key=str(data.get("key", "")),
        name=str(data.get("name", "")),
        value=float(data.get("value", 0.0)),
        formatted_value=str(data.get("formatted_value", "")),
        is_percentage=bool(data.get("is_percentage", False)),
        icon_url=str(data.get("icon_url", "")),
        upgrades=int(data.get("upgrades", 0)),
    )


def account_from_dict(data: dict[str, Any]) -> AccountSummary:
    characters: list[CharacterSummary] = []
    for item in data.get("characters", []):
        if not isinstance(item, dict):
            continue
        relics: list[RelicSummary] = []
        for relic in item.get("relics", []):
            if not isinstance(relic, dict) or not isinstance(relic.get("main_stat"), dict):
                continue
            relics.append(
                RelicSummary(
                    slot=str(relic.get("slot", "")),
                    set_name=str(relic.get("set_name", "")),
                    level=int(relic.get("level", 0)),
                    rarity=int(relic.get("rarity", 0)),
                    icon_url=str(relic.get("icon_url", "")),
                    main_stat=_stat_from_dict(relic["main_stat"]),
                    sub_stats=[
                        _stat_from_dict(stat)
                        for stat in relic.get("sub_stats", [])
                        if isinstance(stat, dict)
                    ],
                    slot_key=str(relic.get("slot_key", "")),
                )
            )
        characters.append(
            CharacterSummary(
                name=str(item.get("name", "")),
                avatar_id=str(item.get("avatar_id", "")),
                level=int(item.get("level", 0)),
                eidolon=int(item.get("eidolon", 0)),
                light_cone=str(item.get("light_cone", "")),
                light_cone_level=int(item.get("light_cone_level", 0)),
                light_cone_rank=int(item.get("light_cone_rank", 0)),
                light_cone_icon_url=str(item.get("light_cone_icon_url", "")),
                relic_count=int(item.get("relic_count", 0)),
                rarity=int(item.get("rarity", 0)),
                element=str(item.get("element", "")),
                path=str(item.get("path", "")),
                icon_url=str(item.get("icon_url", "")),
                splash_url=str(item.get("splash_url", "")),
                stats=[
                    _stat_from_dict(stat)
                    for stat in item.get("stats", [])
                    if isinstance(stat, dict)
                ],
                relics=relics,
                raw=item.get("raw", {}) if isinstance(item.get("raw"), dict) else {},
            )
        )
    return AccountSummary(
        uid=str(data["uid"]),
        nickname=str(data.get("nickname", "")),
        level=int(data.get("level", 0)),
        world_level=int(data.get("world_level", 0)),
        signature=str(data.get("signature", "")),
        profile_icon_url=str(data.get("profile_icon_url", "")),
        characters=characters,
        ttl=int(data.get("ttl", 0)),
        achievement_count=int(data.get("achievement_count", 0)),
    )


@dataclass(slots=True)
class UidTabSession:
    uid: str
    nickname: str = ""
    avatar_url: str = ""
    selected_character_id: str = ""
    scroll_position: int = 0
    updated_at: str = ""
    source: str = "manual"
    account: AccountSummary | None = None
    loading: bool = False
    error: str = ""
    request_token: int = 0
    benchmark_results: dict[str, object] = field(default_factory=dict)
    fribbels_cache: dict[str, dict[str, object]] = field(default_factory=dict)
    unsupported_benchmark_characters: set[str] = field(default_factory=set)

    @property
    def title(self) -> str:
        return self.nickname or self.uid


class UidTabStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_uid_tabs_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._initialize()
        except sqlite3.DatabaseError:
            self._preserve_corrupted_database()
            self._initialize()

    def _preserve_corrupted_database(self) -> None:
        if not self.path.exists():
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.path.with_name(f"{self.path.name}.corrupt-{stamp}")
        suffix = 1
        while backup.exists():
            backup = self.path.with_name(
                f"{self.path.name}.corrupt-{stamp}-{suffix}"
            )
            suffix += 1
        self.path.replace(backup)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self.connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS uid_tabs (
                    owner_id INTEGER NOT NULL,
                    uid TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    nickname TEXT NOT NULL DEFAULT '',
                    avatar_url TEXT NOT NULL DEFAULT '',
                    selected_character_id TEXT NOT NULL DEFAULT '',
                    scroll_position INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'manual',
                    PRIMARY KEY (owner_id, uid)
                )
                """
            )
            connection.commit()
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS uid_tab_meta (
                    owner_id INTEGER PRIMARY KEY,
                    selected_uid TEXT NOT NULL DEFAULT ''
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS uid_account_cache (
                    owner_id INTEGER NOT NULL,
                    uid TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (owner_id, uid)
                )
                """
            )
            connection.commit()

    def load_tabs(self, owner_id: int) -> tuple[list[UidTabSession], str]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                """
                SELECT uid, nickname, avatar_url, selected_character_id,
                       scroll_position, updated_at, source
                FROM uid_tabs WHERE owner_id = ? ORDER BY position, uid
                """,
                (owner_id,),
            ).fetchall()
            meta = connection.execute(
                "SELECT selected_uid FROM uid_tab_meta WHERE owner_id = ?",
                (owner_id,),
            ).fetchone()
        sessions = [
            UidTabSession(
                uid=str(row["uid"]),
                nickname=str(row["nickname"]),
                avatar_url=str(row["avatar_url"]),
                selected_character_id=str(row["selected_character_id"]),
                scroll_position=max(int(row["scroll_position"]), 0),
                updated_at=str(row["updated_at"]),
                source=str(row["source"] or "manual"),
            )
            for row in rows
        ]
        return sessions, str(meta["selected_uid"]) if meta else ""

    def save_tabs(
        self, owner_id: int, sessions: list[UidTabSession], selected_uid: str
    ) -> None:
        with closing(self.connect()) as connection:
            connection.execute("DELETE FROM uid_tabs WHERE owner_id = ?", (owner_id,))
            connection.executemany(
                """
                INSERT INTO uid_tabs (
                    owner_id, uid, position, nickname, avatar_url,
                    selected_character_id, scroll_position, updated_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        owner_id,
                        session.uid,
                        position,
                        session.nickname,
                        session.avatar_url,
                        session.selected_character_id,
                        max(session.scroll_position, 0),
                        session.updated_at,
                        session.source,
                    )
                    for position, session in enumerate(sessions)
                ],
            )
            connection.execute(
                """
                INSERT INTO uid_tab_meta(owner_id, selected_uid) VALUES (?, ?)
                ON CONFLICT(owner_id) DO UPDATE SET selected_uid = excluded.selected_uid
                """,
                (owner_id, selected_uid),
            )
            connection.commit()

    def save_account(
        self, owner_id: int, account: AccountSummary, updated_at: str | None = None
    ) -> str:
        timestamp = updated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload = json.dumps(asdict(account), ensure_ascii=False, separators=(",", ":"))
        with closing(self.connect()) as connection:
            connection.execute(
                """
                INSERT INTO uid_account_cache(owner_id, uid, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(owner_id, uid) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (owner_id, account.uid, payload, timestamp),
            )
            connection.commit()
        return timestamp

    def load_account(
        self, owner_id: int, uid: str
    ) -> tuple[AccountSummary | None, str]:
        with closing(self.connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json, updated_at FROM uid_account_cache
                WHERE owner_id = ? AND uid = ?
                """,
                (owner_id, uid),
            ).fetchone()
        if row is None:
            return None, ""
        try:
            data = json.loads(str(row["payload_json"]))
            if not isinstance(data, dict) or str(data.get("uid", "")) != uid:
                raise ValueError("cache de UID inconsistente")
            return account_from_dict(data), str(row["updated_at"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None, ""


class UidTabWorkspace:
    """Estado testável das abas, independente dos widgets e das threads Qt."""

    def __init__(self, store: UidTabStore, owner_id: int = 0) -> None:
        self.store = store
        self.owner_id = owner_id
        self.sessions: OrderedDict[str, UidTabSession] = OrderedDict()
        self.selected_uid = ""
        self._request_sequence = 0
        self.restore(owner_id)

    def restore(self, owner_id: int) -> None:
        self.owner_id = owner_id
        sessions, selected_uid = self.store.load_tabs(owner_id)
        self.sessions = OrderedDict()
        for session in sessions:
            session.account, cache_updated_at = self.store.load_account(owner_id, session.uid)
            if cache_updated_at:
                session.updated_at = cache_updated_at
            self.sessions[session.uid] = session
        self.selected_uid = (
            selected_uid if selected_uid in self.sessions else next(iter(self.sessions), "")
        )

    def open(self, uid: str, *, source: str = "manual") -> tuple[UidTabSession, bool]:
        uid = uid.strip()
        existing = self.sessions.get(uid)
        if existing is not None:
            self.selected_uid = uid
            self.persist()
            return existing, False
        account, updated_at = self.store.load_account(self.owner_id, uid)
        session = UidTabSession(uid=uid, source=source, account=account, updated_at=updated_at)
        if account is not None:
            session.nickname = account.nickname
            session.avatar_url = account.profile_icon_url
        self.sessions[uid] = session
        self.selected_uid = uid
        self.persist()
        return session, True

    def close(self, uid: str) -> None:
        if uid not in self.sessions:
            return
        keys = list(self.sessions)
        index = keys.index(uid)
        del self.sessions[uid]
        if self.selected_uid == uid:
            remaining = list(self.sessions)
            self.selected_uid = remaining[min(index, len(remaining) - 1)] if remaining else ""
        self.persist()

    def select(self, uid: str, *, persist: bool = True) -> bool:
        if uid not in self.sessions:
            return False
        self.selected_uid = uid
        if persist:
            self.persist()
        return True

    def reorder(self, uids: list[str]) -> bool:
        if len(uids) != len(self.sessions) or set(uids) != set(self.sessions):
            return False
        self.sessions = OrderedDict((uid, self.sessions[uid]) for uid in uids)
        self.persist()
        return True

    def begin_request(self, uid: str) -> int:
        session = self.sessions.get(uid)
        if session is None:
            return 0
        self._request_sequence += 1
        session.request_token = self._request_sequence
        session.loading = True
        session.error = ""
        return session.request_token

    def complete_request(
        self, uid: str, token: int, account: AccountSummary
    ) -> bool:
        session = self.sessions.get(uid)
        if session is None or token <= 0 or session.request_token != token:
            return False
        if account.uid != uid:
            return False
        session.account = account
        session.nickname = account.nickname
        session.avatar_url = account.profile_icon_url
        session.updated_at = self.store.save_account(self.owner_id, account)
        session.benchmark_results.clear()
        session.fribbels_cache.clear()
        session.unsupported_benchmark_characters.clear()
        session.loading = False
        session.error = ""
        self.persist()
        return True

    def fail_request(self, uid: str, token: int, message: str) -> bool:
        session = self.sessions.get(uid)
        if session is None or token <= 0 or session.request_token != token:
            return False
        session.loading = False
        session.error = message
        self.persist()
        return True

    def persist(self) -> None:
        self.store.save_tabs(
            self.owner_id, list(self.sessions.values()), self.selected_uid
        )
