from __future__ import annotations

from functools import lru_cache
import html
import json
from pathlib import Path
import re

from app.benchmark.catalog import ASSETS_PATH, GAME_DATA_PATH, load_catalog
from app.catalog.models import (
    CatalogCharacter,
    CatalogLightCone,
    CatalogRank,
    CatalogSkill,
    CatalogTrace,
)
from app.catalog.sync import catalog_cache_dir


RAW_ASSET_ROOT = "https://raw.githubusercontent.com/Mar-7th/StarRailRes"


class CatalogRepository:
    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or catalog_cache_dir()
        self._data: dict[str, dict[str, object]] = {}
        self.reload()

    def reload(self) -> None:
        self._data.clear()
        for path in self.cache_dir.glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(value, dict):
                self._data[path.stem] = value

    @property
    def has_details(self) -> bool:
        return all(
            key in self._data
            for key in ("characters", "character_skills", "light_cones")
        )

    @property
    def source_commit(self) -> str:
        metadata = self._data.get("metadata", {})
        return str(metadata.get("commit", "")) if isinstance(metadata, dict) else ""

    def characters(self) -> list[CatalogCharacter]:
        fallback = {item.id: item for item in self._fallback_characters()}
        source = self._data.get("characters")
        if source:
            items = [self._character(value) for value in source.values()]
            known = {item.id for item in items}
            items.extend(item for item_id, item in fallback.items() if item_id not in known)
        else:
            items = list(fallback.values())
        return sorted(items, key=lambda item: item.name.casefold())

    def light_cones(self) -> list[CatalogLightCone]:
        fallback = {item.id: item for item in self._fallback_light_cones()}
        source = self._data.get("light_cones")
        if source:
            items = [self._light_cone(value) for value in source.values()]
            known = {item.id for item in items}
            items.extend(item for item_id, item in fallback.items() if item_id not in known)
        else:
            items = list(fallback.values())
        return sorted(items, key=lambda item: (-item.rarity, item.name.casefold()))

    def skills_for(self, character: CatalogCharacter) -> list[CatalogSkill]:
        source = self._data.get("character_skills", {})
        result: list[CatalogSkill] = []
        for skill_id in character.skill_ids:
            value = source.get(skill_id)
            if not isinstance(value, dict):
                continue
            type_name = str(value.get("type_text") or value.get("type") or "Habilidade")
            if type_name == "MazeNormal":
                type_name = "Técnica"
            result.append(CatalogSkill(
                id=str(value.get("id", skill_id)),
                name=str(value.get("name", "Habilidade")),
                type_name=type_name,
                description=str(value.get("desc") or value.get("simple_desc") or ""),
                parameters=self._parameters(value.get("params")),
                icon=str(value.get("icon", "")),
            ))
        return result

    def ranks_for(self, character: CatalogCharacter) -> list[CatalogRank]:
        source = self._data.get("character_ranks", {})
        result: list[CatalogRank] = []
        for rank_id in character.rank_ids:
            value = source.get(rank_id)
            if not isinstance(value, dict):
                continue
            result.append(CatalogRank(
                id=str(value.get("id", rank_id)),
                name=str(value.get("name", f"Eidolon {len(result) + 1}")),
                rank=int(value.get("rank", len(result) + 1)),
                description=str(value.get("desc", "")),
                parameters=self._parameters(value.get("params")),
                icon=str(value.get("icon", "")),
            ))
        return sorted(result, key=lambda item: item.rank)

    def traces_for(self, character: CatalogCharacter) -> list[CatalogTrace]:
        source = self._data.get("character_skill_trees", {})
        result: list[CatalogTrace] = []
        for value in source.values():
            if not isinstance(value, dict):
                continue
            trace_id = str(value.get("id", ""))
            name = str(value.get("name", "")).strip()
            if not trace_id.startswith(character.id) or not name:
                continue
            levels = value.get("levels", [])
            unlock = next(
                (level for level in levels if isinstance(level, dict)), {}
            ) if isinstance(levels, list) else {}
            raw_properties = unlock.get("properties", [])
            properties: list[tuple[str, float]] = []
            if isinstance(raw_properties, list):
                for prop in raw_properties:
                    if not isinstance(prop, dict):
                        continue
                    try:
                        properties.append((
                            str(prop.get("type", "")), float(prop.get("value", 0))
                        ))
                    except (TypeError, ValueError):
                        continue
            result.append(CatalogTrace(
                id=trace_id,
                name=name,
                description=str(value.get("desc", "")),
                parameters=self._parameters(value.get("params")),
                icon=str(value.get("icon", "")),
                properties=properties,
                promotion=int(unlock.get("promotion", 0) or 0),
                required_level=int(unlock.get("level", 0) or 0),
            ))
        return sorted(
            result,
            key=lambda item: (
                item.is_stat_bonus,
                item.promotion,
                item.required_level,
                item.id,
            ),
        )

    def character_stats(self, character_id: str) -> dict[str, float]:
        return self._promotion_stats("character_promotions", character_id, 80)

    def light_cone_stats(self, light_cone_id: str) -> dict[str, float]:
        return self._promotion_stats("light_cone_promotions", light_cone_id, 80)

    def light_cone_rank(self, light_cone_id: str) -> dict[str, object]:
        value = self._data.get("light_cone_ranks", {}).get(light_cone_id, {})
        return value if isinstance(value, dict) else {}

    def asset_url(self, relative_path: str) -> str:
        if not relative_path:
            return ""
        commit = self.source_commit or "master"
        return f"{RAW_ASSET_ROOT}/{commit}/{relative_path}"

    @staticmethod
    def character_image(character_id: str, *, portrait: bool = False) -> Path:
        folder = "character_portrait" if portrait else "character_preview"
        return ASSETS_PATH / "image" / folder / f"{character_id}.webp"

    @staticmethod
    def character_icon(character_id: str) -> Path:
        return ASSETS_PATH / "icon" / "avatar" / f"{character_id}.webp"

    @staticmethod
    def light_cone_image(light_cone_id: str) -> Path:
        return ASSETS_PATH / "image" / "light_cone_portrait" / f"{light_cone_id}.webp"

    @staticmethod
    def light_cone_icon(light_cone_id: str) -> Path:
        return ASSETS_PATH / "icon" / "light_cone" / f"{light_cone_id}.webp"

    @staticmethod
    def format_description(text: str, parameters: list[float] | None) -> str:
        values = parameters or []

        def replace(match: re.Match[str]) -> str:
            index = int(match.group(1)) - 1
            if not 0 <= index < len(values):
                return match.group(0)
            value = values[index]
            if match.group(2):
                value *= 100
            return f"{value:g}{'%' if match.group(2) else ''}"

        return re.sub(r"#(\d+)\[i\](%)?", replace, text).replace("\\n", "\n")

    @staticmethod
    def format_description_rich(
        text: str,
        parameters: list[float] | None,
        highlighted: set[int] | None = None,
    ) -> str:
        values = parameters or []
        changing = highlighted or set()
        escaped = html.escape(text)

        def replace(match: re.Match[str]) -> str:
            index = int(match.group(1)) - 1
            if not 0 <= index < len(values):
                return match.group(0)
            value = values[index]
            if match.group(2):
                value *= 100
            rendered = f"{value:g}{'%' if match.group(2) else ''}"
            if index in changing:
                return f'<span style="color:#ffad5c; font-weight:800;">{rendered}</span>'
            return rendered

        return re.sub(r"#(\d+)\[i\](%)?", replace, escaped).replace("\n", "<br>")

    def _promotion_stats(self, key: str, item_id: str, level: int) -> dict[str, float]:
        value = self._data.get(key, {}).get(item_id, {})
        if not isinstance(value, dict):
            return {}
        levels = value.get("values", [])
        if not isinstance(levels, list) or not levels:
            return {}
        maximum = levels[-1]
        if not isinstance(maximum, dict):
            return {}
        result: dict[str, float] = {}
        for name, stat in maximum.items():
            if isinstance(stat, dict):
                result[name] = float(stat.get("base", 0)) + float(stat.get("step", 0)) * (level - 1)
        return result

    @staticmethod
    def _parameters(value: object) -> list[list[float]]:
        if not isinstance(value, list):
            return []
        return [
            [float(number) for number in row if isinstance(number, (int, float))]
            for row in value if isinstance(row, list)
        ]

    @staticmethod
    def _character(value: object) -> CatalogCharacter:
        data = value if isinstance(value, dict) else {}
        return CatalogCharacter(
            id=str(data.get("id", "")), name=str(data.get("name", "Desconhecido")),
            rarity=int(data.get("rarity", 0)), path=str(data.get("path", "")),
            element=str(data.get("element", "")), icon=str(data.get("icon", "")),
            preview=str(data.get("preview", "")), portrait=str(data.get("portrait", "")),
            skill_ids=[str(item) for item in data.get("skills", [])],
            rank_ids=[str(item) for item in data.get("ranks", [])],
        )

    @staticmethod
    def _light_cone(value: object) -> CatalogLightCone:
        data = value if isinstance(value, dict) else {}
        return CatalogLightCone(
            id=str(data.get("id", "")), name=str(data.get("name", "Desconhecido")),
            rarity=int(data.get("rarity", 0)), path=str(data.get("path", "")),
            description=str(data.get("desc", "")), icon=str(data.get("icon", "")),
            preview=str(data.get("preview", "")), portrait=str(data.get("portrait", "")),
        )

    @staticmethod
    @lru_cache(maxsize=1)
    def _fallback_data() -> dict[str, object]:
        return json.loads(GAME_DATA_PATH.read_text(encoding="utf-8"))

    def _fallback_characters(self) -> list[CatalogCharacter]:
        names = {item.id: item.name for item in load_catalog()[0]}
        source = self._fallback_data().get("characters", {})
        return [CatalogCharacter(
            id=str(item_id), name=names.get(str(item_id), str(value.get("name", item_id))),
            rarity=int(value.get("rarity", 0)), path=str(value.get("path", "")),
            element=str(value.get("element", "")),
        ) for item_id, value in source.items() if not value.get("unreleased", False)]

    def _fallback_light_cones(self) -> list[CatalogLightCone]:
        names = {item.id: item.name for item in load_catalog()[1]}
        source = self._fallback_data().get("lightCones", {})
        return [CatalogLightCone(
            id=str(item_id), name=names.get(str(item_id), str(value.get("name", item_id))),
            rarity=int(value.get("rarity", 0)), path=str(value.get("path", "")),
        ) for item_id, value in source.items() if not value.get("unreleased", False)]
