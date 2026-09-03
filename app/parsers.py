from __future__ import annotations

from typing import Any

from app.models import AccountSummary, CharacterStat, CharacterSummary, RelicSummary


ELEMENT_NAMES = {
    "Fire": "Fogo",
    "Ice": "Gelo",
    "Thunder": "Raio",
    "Lightning": "Raio",
    "Wind": "Vento",
    "Physical": "Físico",
    "Quantum": "Quântico",
    "Imaginary": "Imaginário",
}

PATH_NAMES = {
    "Warrior": "Destruição",
    "Rogue": "Caça",
    "Mage": "Erudição",
    "Shaman": "Harmonia",
    "Warlock": "Inexistência",
    "Knight": "Preservação",
    "Priest": "Abundância",
    "Memory": "Recordação",
    "Joy": "Euforia",
}

RELIC_SLOT_NAMES = {
    "HEAD": "Cabeça",
    "HAND": "Mãos",
    "BODY": "Corpo",
    "FOOT": "Pés",
    "ROPE": "Esfera Plana",
    "ORBIT": "Corda de Ligação",
}

RELIC_SLOT_KEYS = {
    "HEAD": "HEAD",
    "HAND": "HAND",
    "BODY": "BODY",
    "FOOT": "FOOT",
    "ROPE": "ORBIT",
    "ORBIT": "ROPE",
}

STAT_KEY_ALIASES = {
    "CriticalChanceBase": "CriticalChance",
    "CriticalDamageBase": "CriticalDamage",
    "StatusProbabilityBase": "StatusProbability",
    "StatusResistanceBase": "StatusResistance",
    "SPRatioBase": "SPRatio",
    "HealRatioBase": "HealRatio",
}


def normalized_stat_key(value: Any) -> str:
    key = str(getattr(value, "value", value))
    return STAT_KEY_ALIASES.get(key, key)


def first_dict(*values: Any) -> dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def first_list(*values: Any) -> list[Any]:
    for value in values:
        if isinstance(value, list):
            return value
    return []


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_account(payload: dict[str, Any], requested_uid: str) -> AccountSummary:
    """Normaliza formatos atuais e antigos de respostas do Enka."""
    profile = first_dict(
        payload.get("detailInfo"),
        payload.get("playerInfo"),
        payload.get("player"),
    )
    raw_characters = first_list(
        profile.get("avatarDetailList"),
        payload.get("avatarInfoList"),
        payload.get("characters"),
    )

    characters: list[CharacterSummary] = []
    for position, raw_character in enumerate(raw_characters, start=1):
        if not isinstance(raw_character, dict):
            continue

        avatar_id = str(
            raw_character.get("avatarId")
            or raw_character.get("id")
            or raw_character.get("tid")
            or "?"
        )
        name = str(
            raw_character.get("name")
            or raw_character.get("avatarName")
            or raw_character.get("characterName")
            or f"Personagem {avatar_id if avatar_id != '?' else position}"
        )
        equipment = first_dict(
            raw_character.get("equipment"),
            raw_character.get("lightCone"),
        )
        light_cone_id = equipment.get("name") or equipment.get("tid") or equipment.get("id")
        light_cone = str(light_cone_id) if light_cone_id else "Não informado"
        relics = first_list(
            raw_character.get("relicList"),
            raw_character.get("relics"),
            raw_character.get("equipments"),
        )

        characters.append(
            CharacterSummary(
                name=name,
                avatar_id=avatar_id,
                level=as_int(raw_character.get("level")),
                eidolon=as_int(raw_character.get("rank", raw_character.get("eidolon"))),
                light_cone=light_cone,
                light_cone_level=as_int(equipment.get("level")),
                light_cone_rank=as_int(equipment.get("rank")),
                light_cone_icon_url="",
                relic_count=len(relics),
                rarity=as_int(raw_character.get("rarity")),
                element=str(raw_character.get("element") or ""),
                path=str(raw_character.get("path") or ""),
                icon_url="",
                splash_url="",
                stats=[],
                relics=[],
                raw=raw_character,
            )
        )

    nickname = str(
        profile.get("nickname")
        or profile.get("name")
        or "Jogador sem nome público"
    )
    uid = str(payload.get("uid") or profile.get("uid") or requested_uid)

    return AccountSummary(
        uid=uid,
        nickname=nickname,
        level=as_int(profile.get("level")),
        world_level=as_int(profile.get("worldLevel", profile.get("world_level"))),
        signature=str(profile.get("signature") or ""),
        profile_icon_url="",
        characters=characters,
        ttl=max(as_int(payload.get("ttl"), 60), 1),
        achievement_count=as_int(
            first_dict(profile.get("recordInfo"), profile.get("record_info")).get(
                "achievementCount", profile.get("achievementCount", 0)
            )
        ),
    )


def account_from_showcase(showcase: Any) -> AccountSummary:
    """Converte a resposta tipada do enka-py para os modelos da interface."""
    characters: list[CharacterSummary] = []
    for character in showcase.characters:
        stats: list[CharacterStat] = []
        for stat_type, stat in character.stats.items():
            key = normalized_stat_key(stat_type)
            stats.append(
                CharacterStat(
                    key=key,
                    name=str(stat.name),
                    value=float(stat.value),
                    formatted_value=str(stat.formatted_value),
                    is_percentage=bool(stat.is_percentage),
                    icon_url=str(stat.icon or ""),
                )
            )

        relics: list[RelicSummary] = []
        for relic in character.relics:
            main = relic.main_stat
            main_stat = CharacterStat(
                key=normalized_stat_key(main.type),
                name=str(main.name),
                value=float(main.value),
                formatted_value=str(main.formatted_value),
                is_percentage=bool(main.is_percentage),
                icon_url=str(main.icon or ""),
            )
            roll_data = list(relic.sub_affix_list)
            sub_stats = [
                CharacterStat(
                    key=normalized_stat_key(stat.type),
                    name=str(stat.name),
                    value=float(stat.value),
                    formatted_value=str(stat.formatted_value),
                    is_percentage=bool(stat.is_percentage),
                    icon_url=str(stat.icon or ""),
                    upgrades=max(int(roll_data[index].cnt) - 1, 0)
                    if index < len(roll_data)
                    else 0,
                )
                for index, stat in enumerate(relic.sub_stats)
            ]
            slot_key = str(getattr(relic.type, "name", relic.type))
            relics.append(
                RelicSummary(
                    slot=RELIC_SLOT_NAMES.get(slot_key, slot_key.title()),
                    set_name=str(relic.set_name),
                    level=int(relic.level),
                    rarity=int(relic.rarity),
                    icon_url=str(relic.icon),
                    main_stat=main_stat,
                    sub_stats=sub_stats,
                    slot_key=RELIC_SLOT_KEYS.get(slot_key, slot_key),
                )
            )

        light_cone = character.light_cone
        element_value = str(getattr(character.element, "value", character.element))
        path_value = str(getattr(character.path, "value", character.path))
        raw = character.model_dump(mode="json")
        fribbels_avatar_id = f"{character.id}b1" if character.enhanced else str(character.id)
        raw["fribbels_payload"] = {
            "avatarId": fribbels_avatar_id,
            "rank": int(character.eidolons_unlocked),
            "equipment": (
                {
                    "tid": str(light_cone.id),
                    "level": int(light_cone.level),
                    "rank": int(light_cone.superimpose),
                }
                if light_cone else None
            ),
            "relicList": [
                {
                    "tid": str(relic.id),
                    "level": int(relic.level),
                    "mainAffixId": int(relic.main_affix_id),
                    "subAffixList": [
                        {
                            "affixId": int(affix.id),
                            "cnt": int(affix.cnt),
                            "step": int(affix.step or 0),
                        }
                        for affix in relic.sub_affix_list
                    ],
                }
                for relic in character.relics
            ],
        }

        characters.append(
            CharacterSummary(
                name=str(character.name),
                avatar_id=str(character.id),
                level=int(character.level),
                eidolon=int(character.eidolons_unlocked),
                light_cone=str(light_cone.name) if light_cone else "Sem Cone de Luz",
                light_cone_level=int(light_cone.level) if light_cone else 0,
                light_cone_rank=int(light_cone.superimpose) if light_cone else 0,
                light_cone_icon_url=str(light_cone.icon.image) if light_cone else "",
                relic_count=len(character.relics),
                rarity=int(character.rarity),
                element=ELEMENT_NAMES.get(element_value, element_value),
                path=PATH_NAMES.get(path_value, path_value),
                icon_url=str(character.icon.round),
                splash_url=str(character.icon.gacha),
                stats=stats,
                relics=relics,
                raw=raw,
            )
        )

    player = showcase.player
    return AccountSummary(
        uid=str(showcase.uid),
        nickname=str(player.nickname),
        level=int(player.level),
        world_level=int(player.equilibrium_level),
        signature=str(player.signature or ""),
        profile_icon_url=str(player.icon or ""),
        characters=characters,
        ttl=max(int(showcase.ttl), 1),
        achievement_count=int(player.stats.achievement_count),
    )
