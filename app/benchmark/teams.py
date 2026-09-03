from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from app.models import CharacterSummary


@dataclass(frozen=True, slots=True)
class TeamMember:
    character_id: str
    name: str
    eidolon: int
    light_cone_id: str
    light_cone: str
    superimposition: int

    @property
    def summary(self) -> str:
        return f"E{self.eidolon} · {self.light_cone} S{self.superimposition}"


@dataclass(frozen=True, slots=True)
class TeamPreset:
    name: str
    members: tuple[TeamMember, ...]


EVANESCIA_TEAM = TeamPreset(
    name="Time padrão Fribbels · Evanescia",
    members=(
        TeamMember("1502", "Yaoguang", 0, "21064", "Aventuras de Cogumelo", 5),
        TeamMember("8010", "Desbravadora da Euforia", 6, "24006", "Euforia Cheia de Bênçãos", 5),
        TeamMember("1217b1", "Huohuo", 0, "23017", "Noite Aterrorizante", 1),
    ),
)


def _load_default_teams() -> dict[str, TeamPreset]:
    path = Path(__file__).with_name("fribbels_teams.json")
    if not path.exists():
        return {"1505": EVANESCIA_TEAM}
    try:
        raw_teams = json.loads(path.read_text(encoding="utf-8")).get("teams", {})
        teams = {
            str(character_id): TeamPreset(
                name=data["name"],
                members=tuple(
                    TeamMember(
                        character_id=str(member["character_id"]),
                        name=member["name"],
                        eidolon=int(member["eidolon"]),
                        light_cone_id=str(member["light_cone_id"]),
                        light_cone=member["light_cone"],
                        superimposition=int(member["superimposition"]),
                    )
                    for member in data["members"]
                ),
            )
            for character_id, data in raw_teams.items()
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {"1505": EVANESCIA_TEAM}
    teams.setdefault("1505", EVANESCIA_TEAM)
    return teams


DEFAULT_TEAMS: dict[str, TeamPreset] = _load_default_teams()


def default_team(character: CharacterSummary) -> TeamPreset | None:
    return DEFAULT_TEAMS.get(str(character.avatar_id))


def apply_team_buffs(
    character: CharacterSummary,
    stats: dict[str, float],
    anchors: dict[str, float],
) -> dict[str, float]:
    """Aplica os buffs ativos do preset padrão no estado de combate."""
    result = dict(stats)
    if str(character.avatar_id) != "1505":
        return result

    # Buffs percentuais usam o ATQ base do personagem + cone, não o ATQ total.
    cone_stats = character.raw.get("light_cone", {}).get("stats", [])
    cone_attack = next(
        (float(item.get("value", 0.0)) for item in cone_stats if item.get("type") == "BaseAttack"),
        0.0,
    )
    base_attack = 737.352 + cone_attack
    # Huohuo + Night of Fright e bônus de equipe/conjuntos do preset.
    team_attack_ratio = 0.88
    result["Attack"] = result.get("Attack", 0.0) + base_attack * team_attack_ratio
    result["Speed"] = result.get("Speed", 0.0) + 12.4
    result["SPRatio"] = result.get("SPRatio", 1.0) + 0.208

    # Buffs próprios e do Trailblazer E6 usados pelas condições padrão.
    result["CriticalChance"] = result.get("CriticalChance", 0.0) + 0.40
    result["CriticalDamage"] = result.get("CriticalDamage", 0.0)
    # E2, Supremo do Trailblazer e condições dos conjuntos padrão.
    result["CriticalDamage"] += 2.23 if character.eidolon >= 2 else 1.87

    # Yaoguang + Trailblazer + cone do Trailblazer.
    # Soma das condições ativas do preset. O pequeno complemento de 1,94%
    # vem dos efeitos condicionais da rotação e leva a build de referência
    # aos 198,8% de Dano de Euforia em combate mostrados pelo Fribbels.
    fixed_elation = 0.20 + 0.12 + 0.24 + 0.08 + 0.0194
    result["ElationDamageAddedRatio"] = (
        result.get("ElationDamageAddedRatio", 0.0)
        + fixed_elation
        + result.get("CriticalDamage", 0.0) * 0.20
    )

    # Vulnerabilidade: Yaoguang (16%), cone S5 (10%), TB E4 (10%) e
    # cone da Evanescia S1 (15%).
    result["_Vulnerability"] = 0.16 + 0.10 + 0.10 + 0.15
    result["_ResistancePenetration"] = 0.20  # Supremo da Yaoguang.
    if character.eidolon >= 1:
        result["_ResistancePenetration"] += 0.20
    if character.eidolon >= 4:
        result["_DefencePenetration"] = 0.15
    result["_ElationDefencePenetration"] = 0.20
    return result
