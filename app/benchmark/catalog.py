from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path


FRIBBELS_ROOT = Path(__file__).resolve().parents[2] / "third_party" / "fribbels-hsr-optimizer"
GAME_DATA_PATH = FRIBBELS_ROOT / "src" / "data" / "game_data.json"
PT_DATA_PATH = FRIBBELS_ROOT / "public" / "locales" / "pt_BR" / "gameData.yaml"
ASSETS_PATH = FRIBBELS_ROOT / "public" / "assets"


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    id: str
    name: str
    internal_name: str
    path: str = ""
    rarity: int = 0


def _localized_names() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {
        "Characters": {}, "RelicSets": {}, "Lightcones": {},
    }
    if not PT_DATA_PATH.is_file():
        return result
    section = ""
    current_id = ""
    for line in PT_DATA_PATH.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(" ") and line.endswith(":"):
            section = line[:-1]
            current_id = ""
        elif section in result and line.startswith("  ") and not line.startswith("    "):
            current_id = line.strip().rstrip(":").strip('"')
        elif section in result and current_id and line.startswith("    Name:"):
            result[section][current_id] = line.split(":", 1)[1].strip().strip('"')
    return result


@lru_cache(maxsize=1)
def load_catalog() -> tuple[list[CatalogEntry], list[CatalogEntry], list[CatalogEntry], list[CatalogEntry]]:
    data = json.loads(GAME_DATA_PATH.read_text(encoding="utf-8"))
    localized = _localized_names()
    characters = [
        CatalogEntry(
            str(key), localized["Characters"].get(str(key), value["name"]),
            value["name"], value.get("path", ""), int(value.get("rarity", 0)),
        )
        for key, value in data["characters"].items()
        if not value.get("unreleased", False)
    ]
    light_cones = [
        CatalogEntry(
            str(key), localized["Lightcones"].get(str(key), value["name"]),
            value["name"], value.get("path", ""), int(value.get("rarity", 0)),
        )
        for key, value in data["lightCones"].items()
        if not value.get("unreleased", False)
    ]
    relics = [
        CatalogEntry(
            str(value["id"]),
            localized["RelicSets"].get(str(value["id"]), value["name"]),
            value["name"],
        )
        for value in data["relics"]
    ]
    characters.sort(key=lambda item: item.name.casefold())
    light_cones.sort(key=lambda item: (-item.rarity, item.name.casefold()))
    teammate_relic_names = {
        "Messenger Traversing Hackerspace",
        "Watchmaker, Master of Dream Machinations",
        "Warrior Goddess of Sun and Thunder",
        "World-Remaking Deliverer",
        "Self-Enshrouded Recluse",
        "Diviner of Distant Reach",
        "Divine-Querying Master Smith",
        "Dreamlit Actor",
    }
    teammate_ornament_names = {
        "Broken Keel", "Fleet of the Ageless", "Penacony, Land of the Dreams",
        "Lushaka, the Sunken Seas", "Amphoreus, The Eternal Land",
        "City of Converging Stars",
    }
    relic_sets = [item for item in relics if item.internal_name in teammate_relic_names]
    sacerdos = next(
        (item for item in relics if item.internal_name == "Sacerdos' Relived Ordeal"),
        None,
    )
    if sacerdos:
        relic_sets.extend((
            CatalogEntry(sacerdos.id, f"{sacerdos.name} · 1 acúmulo", "Sacerdos' Relived Ordeal 1x"),
            CatalogEntry(sacerdos.id, f"{sacerdos.name} · 2 acúmulos", "Sacerdos' Relived Ordeal 2x"),
        ))
    relic_sets.sort(key=lambda item: item.name.casefold())
    ornament_sets = [
        item for item in relics if item.internal_name in teammate_ornament_names
    ]
    return characters, light_cones, relic_sets, ornament_sets
