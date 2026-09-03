from __future__ import annotations

from dataclasses import dataclass, field


PATH_NAMES = {
    "Knight": "Preservação",
    "Rogue": "Caça",
    "Mage": "Erudição",
    "Shaman": "Harmonia",
    "Warlock": "Inexistência",
    "Warrior": "Destruição",
    "Priest": "Abundância",
    "Memory": "Recordação",
    "Elation": "Euforia",
}

ELEMENT_NAMES = {
    "Physical": "Físico",
    "Fire": "Fogo",
    "Ice": "Gelo",
    "Lightning": "Raio",
    "Thunder": "Raio",
    "Wind": "Vento",
    "Quantum": "Quântico",
    "Imaginary": "Imaginário",
}


def localized_path(value: str) -> str:
    return PATH_NAMES.get(value, value or "Desconhecido")


def localized_element(value: str) -> str:
    return ELEMENT_NAMES.get(value, value or "Desconhecido")


@dataclass(slots=True)
class CatalogCharacter:
    id: str
    name: str
    rarity: int
    path: str
    element: str
    icon: str = ""
    preview: str = ""
    portrait: str = ""
    skill_ids: list[str] = field(default_factory=list)
    rank_ids: list[str] = field(default_factory=list)

    @property
    def path_name(self) -> str:
        return localized_path(self.path)

    @property
    def element_name(self) -> str:
        return localized_element(self.element)


@dataclass(slots=True)
class CatalogLightCone:
    id: str
    name: str
    rarity: int
    path: str
    description: str = ""
    icon: str = ""
    preview: str = ""
    portrait: str = ""

    @property
    def path_name(self) -> str:
        return localized_path(self.path)


@dataclass(slots=True)
class CatalogSkill:
    id: str
    name: str
    type_name: str
    description: str
    parameters: list[list[float]] = field(default_factory=list)
    icon: str = ""


@dataclass(slots=True)
class CatalogRank:
    id: str
    name: str
    rank: int
    description: str
    parameters: list[list[float]] = field(default_factory=list)
    icon: str = ""
