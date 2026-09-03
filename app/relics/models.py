from __future__ import annotations

from dataclasses import dataclass

from app.models import RelicSummary


@dataclass(slots=True)
class StoredRelic:
    fingerprint: str
    uid: str
    relic: RelicSummary
    score: float
    grade: str
    current_character_id: str = ""
    current_character_name: str = ""
    current_character_icon: str = ""
    previous_character_id: str = ""
    previous_character_name: str = ""
    previous_character_icon: str = ""
    first_seen: str = ""
    last_seen: str = ""

    @property
    def holder_name(self) -> str:
        return self.current_character_name or self.previous_character_name

    @property
    def holder_icon(self) -> str:
        return self.current_character_icon or self.previous_character_icon

    @property
    def is_equipped(self) -> bool:
        return bool(self.current_character_name)
