from __future__ import annotations

from dataclasses import dataclass


BANNER_NAMES = {
    "1": "Salto Estelar",
    "2": "Salto de Partida",
    "11": "Evento de Personagem",
    "12": "Evento de Cone de Luz",
    "21": "Salto Hiperespacial de Colaboração de Personagem",
    "22": "Salto Hiperespacial de Colaboração de Cone de Luz",
}


@dataclass(frozen=True, slots=True)
class WarpRecord:
    id: str
    uid: str
    gacha_type: str
    item_id: str
    name: str
    item_type: str
    rank_type: int
    time: str
    banner_title: str = ""
    featured_name: str = ""

    @property
    def banner_name(self) -> str:
        return BANNER_NAMES.get(self.gacha_type, f"Banner {self.gacha_type}")

    @classmethod
    def from_api(cls, data: dict[str, object]) -> "WarpRecord":
        return cls(
            id=str(data.get("id", "")),
            uid=str(data.get("uid", "")),
            gacha_type=str(data.get("gacha_type", "")),
            item_id=str(data.get("item_id", "")),
            name=str(data.get("name", "Item desconhecido")),
            item_type=str(data.get("item_type", "")),
            rank_type=int(data.get("rank_type", 0)),
            time=str(data.get("time", "")),
            banner_title=str(data.get("banner_title", "")),
            featured_name=str(data.get("featured_name", "")),
        )


@dataclass(frozen=True, slots=True)
class WarpSummary:
    uid: str
    gacha_type: str
    total: int
    five_star_count: int
    four_star_count: int
    five_star_pity: int
    four_star_pity: int
    featured_item_id: str
    featured_item_name: str
    featured_pity: int
    featured_item_type: str
