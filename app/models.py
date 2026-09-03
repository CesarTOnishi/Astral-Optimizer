from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CharacterStat:
    key: str
    name: str
    value: float
    formatted_value: str
    is_percentage: bool
    icon_url: str = ""
    upgrades: int = 0


@dataclass(slots=True)
class RelicSummary:
    slot: str
    set_name: str
    level: int
    rarity: int
    icon_url: str
    main_stat: CharacterStat
    sub_stats: list[CharacterStat]
    slot_key: str = ""


@dataclass(slots=True)
class CharacterSummary:
    name: str
    avatar_id: str
    level: int
    eidolon: int
    light_cone: str
    light_cone_level: int
    light_cone_rank: int
    light_cone_icon_url: str
    relic_count: int
    rarity: int
    element: str
    path: str
    icon_url: str
    splash_url: str
    stats: list[CharacterStat]
    relics: list[RelicSummary]
    raw: dict[str, Any]


@dataclass(slots=True)
class AccountSummary:
    uid: str
    nickname: str
    level: int
    world_level: int
    signature: str
    profile_icon_url: str
    characters: list[CharacterSummary]
    ttl: int
    achievement_count: int = 0
