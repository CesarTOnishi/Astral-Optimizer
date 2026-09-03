from __future__ import annotations

from math import ceil, floor

from app.benchmark.models import (
    AbilityDamageStep,
    BenchmarkResult,
    CombatStat,
    RelicRating,
    UpgradeComparison,
)
from app.benchmark.catalog import load_catalog
from app.benchmark.profiles import scoring_profile
from app.benchmark.teams import apply_team_buffs, default_team
from app.models import CharacterSummary, RelicSummary


HIGH_ROLLS = {
    "HPDelta": 42.3375, "AttackDelta": 21.16875, "DefenceDelta": 21.16875,
    "HPAddedRatio": 0.0432, "AttackAddedRatio": 0.0432,
    "DefenceAddedRatio": 0.054, "SpeedDelta": 2.6,
    "CriticalChance": 0.0324, "CriticalDamage": 0.0648,
    "StatusProbability": 0.0432, "StatusResistance": 0.0432,
    "BreakDamageAddedRatio": 0.0648,
}

LOW_ROLLS = {
    "HPDelta": 33.87, "AttackDelta": 16.935, "DefenceDelta": 16.935,
    "HPAddedRatio": 0.03456, "AttackAddedRatio": 0.03456,
    "DefenceAddedRatio": 0.0432, "SpeedDelta": 2.0,
    "CriticalChance": 0.02592, "CriticalDamage": 0.05184,
    "StatusProbability": 0.03456, "StatusResistance": 0.03456,
    "BreakDamageAddedRatio": 0.05184,
}

MID_SPEED_ROLL = 2.3
POTENTIAL_UNIT = 0.0648
FLAT_STATS = {"HPDelta", "AttackDelta", "DefenceDelta"}
PERCENT_TO_TOTAL = {
    "HPAddedRatio": "MaxHP", "AttackAddedRatio": "Attack",
    "DefenceAddedRatio": "Defence",
}
FLAT_TO_TOTAL = {
    "HPDelta": "MaxHP", "AttackDelta": "Attack", "DefenceDelta": "Defence",
}

STAT_NAMES = {
    "HPAddedRatio": "PV %", "HPDelta": "PV", "AttackAddedRatio": "ATQ %",
    "AttackDelta": "ATQ", "DefenceAddedRatio": "DEF %", "DefenceDelta": "DEF",
    "CriticalChance": "Taxa Crítica", "CriticalDamage": "Dano Crítico",
    "BreakDamageAddedRatio": "Efeito de Quebra",
    "StatusProbability": "Acerto de Efeito", "StatusResistance": "RES a Efeito",
    "SpeedDelta": "VEL",
}

ELEMENT_KEYS = {
    "Físico": "PhysicalAddedRatio", "Fogo": "FireAddedRatio",
    "Gelo": "IceAddedRatio", "Raio": "ThunderAddedRatio",
    "Vento": "WindAddedRatio", "Quântico": "QuantumAddedRatio",
    "Imaginário": "ImaginaryAddedRatio",
}

PART_MAIN_STATS = {
    "BODY": {
        "HPAddedRatio", "AttackAddedRatio", "DefenceAddedRatio",
        "CriticalChance", "CriticalDamage", "StatusProbability", "HealRatio",
    },
    "FOOT": {"HPAddedRatio", "AttackAddedRatio", "DefenceAddedRatio", "SpeedDelta"},
    "ORBIT": {
        "HPAddedRatio", "AttackAddedRatio", "DefenceAddedRatio",
        "PhysicalAddedRatio", "FireAddedRatio", "IceAddedRatio",
        "ThunderAddedRatio", "WindAddedRatio", "QuantumAddedRatio",
        "ImaginaryAddedRatio",
    },
    "ROPE": {
        "HPAddedRatio", "AttackAddedRatio", "DefenceAddedRatio",
        "BreakDamageAddedRatio", "SPRatio",
    },
}

SLOT_ALIASES = {
    "HEAD": "HEAD", "HAND": "HAND", "BODY": "BODY", "FOOT": "FOOT",
    "ORBIT": "ORBIT", "ROPE": "ROPE", "CABEÇA": "HEAD", "MÃOS": "HAND",
    "CORPO": "BODY", "PÉS": "FOOT", "ESFERA PLANA": "ORBIT",
    "CORDA DE LIGAÇÃO": "ROPE",
}

GRADE_THRESHOLDS = (
    (150, "AEON"), (140, "WTF+"), (130, "WTF"), (121, "SSS+"),
    (113, "SSS"), (106, "SS+"), (100, "SS"), (95, "S+"),
    (90, "S"), (85, "A+"), (80, "A"), (75, "B+"),
    (70, "B"), (65, "C+"), (60, "C"), (55, "D+"),
    (50, "D"), (45, "F+"), (40, "F"),
)

RELIC_GRADE_THRESHOLDS = (
    (90, "AEON"), (85, "WTF+"), (80, "WTF"), (75, "SSS+"),
    (70, "SSS"), (65, "SS+"), (60, "SS"), (55, "S+"),
    (50, "S"), (45, "A+"), (40, "A"), (35, "B+"),
    (30, "B"), (25, "C+"), (20, "C"), (15, "D+"),
    (10, "D"), (5, "F+"), (0, "F"),
)


class BenchmarkEngine:
    """Metodologia Fribbels com um simulador de combo local simplificado."""

    def __init__(self) -> None:
        self._simulation_character: CharacterSummary | None = None
        self._simulation_anchors: dict[str, float] = {}

    def analyze(self, character: CharacterSummary) -> BenchmarkResult:
        profile = scoring_profile(character)
        weights = self._effective_weights(profile.get("weights", {}))
        current = {stat.key: stat.value for stat in character.stats}
        baseline, anchors, relic_totals = self._baseline_stats(character, current)
        self._simulation_character = character
        self._simulation_anchors = anchors
        archetype = self._detect_archetype(weights)

        baseline_value = self._combo_value(baseline, character.element, archetype, weights)
        current_value = self._combo_value(current, character.element, archetype, weights)
        benchmark_stats = self._generated_build(
            character, baseline, anchors, relic_totals, weights, archetype, 48, False
        )
        perfection_stats = self._generated_build(
            character, baseline, anchors, relic_totals, weights, archetype, 54, True
        )
        benchmark_value = self._combo_value(
            benchmark_stats, character.element, archetype, weights
        )
        perfection_value = max(
            self._combo_value(perfection_stats, character.element, archetype, weights),
            benchmark_value,
        )
        score = self._normalized_score(
            current_value, baseline_value, benchmark_value, perfection_value
        )
        upgrades = self._compare_upgrades(
            current, anchors, character.element, archetype, weights,
            baseline_value, benchmark_value, perfection_value,
        )
        team = default_team(character)
        combat = apply_team_buffs(character, current, anchors)
        return BenchmarkResult(
            archetype=archetype,
            damage_index=current_value,
            effective_rolls=self._weighted_rolls(character, weights),
            score=score,
            grade=self.grade(score, character.relic_count == 6),
            upgrades=upgrades,
            baseline_value=baseline_value,
            benchmark_value=benchmark_value,
            perfection_value=perfection_value,
            team_name=team.name if team else "Sem time padrão configurado",
            team_members=tuple(member.name for member in team.members) if team else (),
            team_details=tuple(member.summary for member in team.members) if team else (),
            team_character_ids=(
                tuple(member.character_id for member in team.members) if team else ()
            ),
            team_light_cone_ids=(
                tuple(member.light_cone_id for member in team.members) if team else ()
            ),
            combat_stats=self._combat_stats(character, current, combat),
            combat_focus=self._combat_focus(weights),
            exact_simulation=str(character.avatar_id) == "1505",
        )

    def apply_fribbels_result(
        self,
        character: CharacterSummary,
        result: BenchmarkResult,
        payload: dict[str, object],
    ) -> BenchmarkResult:
        # O Fribbels trunca a primeira casa em vez de arredondar.
        result.score = floor(float(payload["score"]) * 10.0) / 10.0
        result.grade = str(payload["grade"])
        result.damage_index = float(payload["damage"])
        result.baseline_value = float(payload["baseline"])
        result.benchmark_value = float(payload["benchmark"])
        result.perfection_value = float(payload["perfection"])
        result.combat_stats = self._fribbels_combat_stats(character, payload)
        result.ability_breakdown = self._ability_breakdown(payload)
        raw_team = payload.get("teammates")
        if isinstance(raw_team, list):
            self.apply_team_details(result, raw_team, bool(payload.get("customTeam")))
        result.exact_simulation = True
        result.engine_source = "fribbels"
        # As melhorias locais usam a fórmula simplificada. Não as misturamos
        # com um resultado oficial do Fribbels.
        raw_upgrades = payload.get("substatUpgrades")
        result.upgrades = []
        if isinstance(raw_upgrades, list):
            for raw in raw_upgrades:
                if not isinstance(raw, dict):
                    continue
                stat_key = str(raw.get("stat", ""))
                result.upgrades.append(UpgradeComparison(
                    stat_key=stat_key,
                    stat_name=self._fribbels_stat_name(stat_key),
                    roll_value="+1x roll",
                    damage_gain_percent=float(raw.get("damageGainPercent", 0.0)),
                    projected_score=float(raw.get("projectedScore", result.score)),
                    damage_gain_value=float(raw.get("damageGain", 0.0)),
                    score_gain_percent=float(raw.get("scoreGainPercent", 0.0)),
                ))
        result.main_upgrades = []
        raw_main_upgrades = payload.get("mainStatUpgrades")
        if isinstance(raw_main_upgrades, list):
            for raw in raw_main_upgrades:
                if not isinstance(raw, dict):
                    continue
                stat_key = str(raw.get("stat", ""))
                part_key = str(raw.get("part", ""))
                result.main_upgrades.append(UpgradeComparison(
                    stat_key=stat_key,
                    stat_name=self._fribbels_stat_name(stat_key),
                    roll_value=f"{self._fribbels_part_name(part_key)} →",
                    damage_gain_percent=float(raw.get("damageGainPercent", 0.0)),
                    projected_score=float(raw.get("projectedScore", result.score)),
                    damage_gain_value=float(raw.get("damageGain", 0.0)),
                    score_gain_percent=float(raw.get("scoreGainPercent", 0.0)),
                    part_key=part_key,
                ))
        return result

    @classmethod
    def _ability_breakdown(
        cls, payload: dict[str, object]
    ) -> tuple[AbilityDamageStep, ...]:
        raw_steps = payload.get("abilityBreakdown")
        if not isinstance(raw_steps, list):
            return ()
        damage_types = {
            "BASIC", "SKILL", "ULT", "FUA", "DOT", "BREAK",
            "MEMO_SKILL", "MEMO_TALENT", "ELATION_SKILL", "UNIQUE",
        }
        steps: list[AbilityDamageStep] = []
        for raw in raw_steps:
            if not isinstance(raw, dict):
                continue
            action_type = str(raw.get("actionType", ""))
            if action_type not in damage_types:
                continue
            action_name = str(raw.get("actionName", action_type))
            steps.append(AbilityDamageStep(
                action_type=action_type,
                action_name=action_name,
                label=cls._ability_label(action_type, action_name),
                damage=float(raw.get("damage", 0.0)),
            ))
        return tuple(steps)

    @staticmethod
    def _ability_label(action_type: str, action_name: str) -> str:
        labels = {
            "BASIC": "Ataque Básico",
            "SKILL": "Perícia",
            "ULT": "Supremo",
            "FUA": "Ataque Extra",
            "DOT": "Dano Contínuo",
            "BREAK": "Quebra",
            "MEMO_SKILL": "Perícia do Memosprite",
            "MEMO_TALENT": "Talento do Memosprite",
            "ELATION_SKILL": "Perícia de Euforia",
            "UNIQUE": "Único",
        }
        label = labels.get(action_type, action_type.replace("_", " ").title())
        if action_name.startswith("START_"):
            return f"[ {label}"
        if action_name.startswith("END_"):
            return f"{label} ]"
        if action_name.startswith("WHOLE_"):
            return f"[ {label} ]"
        return label

    @staticmethod
    def apply_team_details(
        result: BenchmarkResult,
        raw_team: list[object],
        custom: bool = True,
    ) -> None:
        characters, light_cones, _relics, _ornaments = load_catalog()
        character_names = {item.id: item.name for item in characters}
        cone_names = {item.id: item.name for item in light_cones}
        valid_team = [item for item in raw_team if isinstance(item, dict)]
        result.team_name = "Time customizado" if custom else "Time padrão Fribbels"
        result.team_character_ids = tuple(
            str(item.get("characterId", "")) for item in valid_team
        )
        result.team_light_cone_ids = tuple(
            str(item.get("lightCone", "")) for item in valid_team
        )
        result.team_members = tuple(
            character_names.get(
                str(item.get("characterId", "")), str(item.get("characterId", ""))
            )
            for item in valid_team
        )
        result.team_details = tuple(
            f"E{int(item.get('characterEidolon', 0))} · "
            f"{cone_names.get(str(item.get('lightCone', '')), str(item.get('lightCone', '')))} "
            f"S{int(item.get('lightConeSuperimposition', 1))}\n"
            f"Relíquias: {item.get('teamRelicSet') or 'nenhuma'}\n"
            f"Ornamento: {item.get('teamOrnamentSet') or 'nenhum'}"
            for item in valid_team
        )

    @staticmethod
    def _fribbels_stat_name(key: str) -> str:
        names = {
            "HP%": "PV %", "HP": "PV", "ATK%": "ATQ %", "ATK": "ATQ",
            "DEF%": "DEF %", "DEF": "DEF", "SPD": "VEL",
            "CRIT Rate": "Taxa Crítica", "CRIT DMG": "Dano Crítico",
            "Break Effect": "Efeito de Quebra",
            "Effect Hit Rate": "Acerto de Efeito", "Effect RES": "RES a Efeito",
            "Energy Regeneration Rate": "Regen. de Energia",
            "Outgoing Healing Boost": "Bônus de Cura",
            "Physical DMG Boost": "Dano Físico", "Fire DMG Boost": "Dano de Fogo",
            "Ice DMG Boost": "Dano de Gelo", "Lightning DMG Boost": "Dano de Raio",
            "Wind DMG Boost": "Dano de Vento", "Quantum DMG Boost": "Dano Quântico",
            "Imaginary DMG Boost": "Dano Imaginário",
        }
        return names.get(key, key)

    @staticmethod
    def _fribbels_part_name(key: str) -> str:
        return {
            "Body": "Corpo", "Feet": "Pés",
            "PlanarSphere": "Esfera", "LinkRope": "Corda",
        }.get(key, key)

    @staticmethod
    def _fribbels_combat_stats(
        character: CharacterSummary,
        payload: dict[str, object],
    ) -> tuple[CombatStat, ...]:
        raw_stats = payload.get("combatStats")
        combat = raw_stats if isinstance(raw_stats, dict) else {}
        primary_raw = payload.get("primaryActionStats")
        primary = primary_raw if isinstance(primary_raw, dict) else {}
        element_keys = {
            "Físico": "Physical DMG Boost", "Fogo": "Fire DMG Boost",
            "Gelo": "Ice DMG Boost", "Raio": "Lightning DMG Boost",
            "Vento": "Wind DMG Boost", "Quântico": "Quantum DMG Boost",
            "Imaginário": "Imaginary DMG Boost",
        }
        element_key = element_keys.get(character.element, "")
        if primary:
            if primary.get("sourceEntityCR") is not None:
                combat["CRIT Rate"] = float(primary["sourceEntityCR"])
            if primary.get("sourceEntityCD") is not None:
                combat["CRIT DMG"] = float(primary["sourceEntityCD"])
            if element_key and primary.get("sourceEntityElementDmgBoost") is not None:
                combat[element_key] = (
                    float(primary["sourceEntityElementDmgBoost"])
                    + float(primary.get("BOOST", 0.0))
                )

        base_by_key = {stat.key: stat.value for stat in character.stats}
        definitions = (
            ("HP", "PV", "MaxHP", True),
            ("ATK", "ATQ", "Attack", True),
            ("DEF", "DEF", "Defence", True),
            ("SPD", "VEL", "Speed", True),
            ("CRIT Rate", "Taxa Crítica", "CriticalChance", False),
            ("CRIT DMG", "Dano Crítico", "CriticalDamage", False),
            ("Effect Hit Rate", "Acerto de Efeito", "StatusProbability", False),
            ("Effect RES", "RES a Efeito", "StatusResistance", False),
            ("Break Effect", "Efeito de Quebra", "BreakDamageAddedRatio", False),
            ("Energy Regeneration Rate", "Regen. de Energia", "SPRatio", False),
            (element_key, f"Dano {character.element}", element_key, False),
            ("Elation", "Dano de Euforia", "ElationDamageAddedRatio", False),
        )
        app_element_key = ELEMENT_KEYS.get(character.element, "")
        rows: list[CombatStat] = []
        for fribbels_key, label, app_key, flat in definitions:
            if not fribbels_key or fribbels_key not in combat:
                continue
            value = float(combat[fribbels_key])
            compare_key = app_element_key if fribbels_key == element_key else app_key
            base_value = base_by_key.get(compare_key, value)
            if app_key == "SPRatio":
                base_value -= 1.0
            formatted = f"{value:.0f}" if flat and fribbels_key != "SPD" else (
                f"{value:.1f}" if fribbels_key == "SPD" else f"{value * 100:.1f}%"
            )
            rows.append(CombatStat(
                key=fribbels_key,
                name=label,
                formatted_value=formatted.replace(".", ","),
                changed=abs(value - base_value) > 1e-4,
            ))
        return tuple(rows)

    @staticmethod
    def _combat_stats(
        character: CharacterSummary,
        base: dict[str, float],
        combat: dict[str, float],
    ) -> tuple[CombatStat, ...]:
        names = {
            "MaxHP": "PV", "Attack": "ATQ", "Defence": "DEF", "Speed": "VEL",
            "CriticalChance": "Taxa Crítica", "CriticalDamage": "Dano Crítico",
            "StatusProbability": "Acerto de Efeito",
            "StatusResistance": "RES a Efeito",
            "BreakDamageAddedRatio": "Efeito de Quebra",
            "SPRatio": "Regen. de Energia",
            "ElationDamageAddedRatio": "Dano de Euforia",
        }
        elemental_key = ELEMENT_KEYS.get(character.element, "")
        if elemental_key:
            names[elemental_key] = f"Dano {character.element}"
        order = (
            "MaxHP", "Attack", "Defence", "Speed", "CriticalChance",
            "CriticalDamage", "StatusProbability", "StatusResistance",
            "BreakDamageAddedRatio", "SPRatio", elemental_key,
            "ElationDamageAddedRatio",
        )
        percentage = {
            "CriticalChance", "CriticalDamage", "StatusProbability",
            "StatusResistance", "BreakDamageAddedRatio",
            "ElationDamageAddedRatio", elemental_key,
        }
        result: list[CombatStat] = []
        for key in order:
            if not key or key not in combat:
                continue
            value = combat[key]
            if key == "SPRatio":
                formatted = f"{(value - 1.0) * 100:.1f}%"
            elif key in percentage:
                formatted = f"{value * 100:.1f}%"
            elif key in {"MaxHP", "Attack", "Defence"}:
                formatted = f"{value:.0f}"
            else:
                formatted = f"{value:.1f}"
            result.append(CombatStat(
                key=key,
                name=names.get(key, key),
                formatted_value=formatted.replace(".", ","),
                changed=abs(value - base.get(key, value)) > 1e-7,
            ))
        return tuple(result)

    def rate_relic(self, character: CharacterSummary, relic: RelicSummary) -> RelicRating:
        profile = scoring_profile(character)
        weights = self._effective_weights(profile.get("weights", {}))
        part = self._part_key(relic)
        main_stat = relic.main_stat.key
        raw_score = sum(
            stat.value * weights.get(stat.key, 0.0) * self._potential_scale(stat.key)
            for stat in relic.sub_stats
        )
        ideal_score = self._ideal_relic_score(
            part, main_stat, weights, profile.get("main_stats", {})
        )
        score = 0.0 if ideal_score <= 0 else max(0.0, raw_score / ideal_score * 100.0)
        score = int(round(score, 8) * 10) / 10

        grade = self.relic_grade(score) if relic.rarity == 5 else "?"
        return RelicRating(score=score, grade=grade)

    @staticmethod
    def _effective_weights(raw: dict[str, float]) -> dict[str, float]:
        weights = {key: min(1.0, max(0.0, float(value))) for key, value in raw.items()}
        weights["HPDelta"] = weights.get("HPAddedRatio", 0.0) * 0.4
        weights["AttackDelta"] = weights.get("AttackAddedRatio", 0.0) * 0.4
        weights["DefenceDelta"] = weights.get("DefenceAddedRatio", 0.0) * 0.4
        return weights

    @staticmethod
    def _potential_scale(stat: str) -> float:
        maximum = HIGH_ROLLS.get(stat)
        return POTENTIAL_UNIT / maximum if maximum else 0.0

    def _ideal_relic_score(
        self, part: str, main_stat: str, weights: dict[str, float],
        main_stats: dict[str, list[str]],
    ) -> float:
        positive = sorted(
            ((key, value) for key, value in weights.items() if key in HIGH_ROLLS and value > 0),
            key=lambda item: item[1], reverse=True,
        )
        if not positive:
            return 0.0
        if len(positive) == 1:
            stat, weight = positive[0]
            return 0.0 if stat == main_stat else 6 * weight * POTENTIAL_UNIT

        only_pair = len(positive) == 2 and {positive[0][0], positive[1][0]} in (
            {"HPDelta", "HPAddedRatio"}, {"AttackDelta", "AttackAddedRatio"},
            {"DefenceDelta", "DefenceAddedRatio"},
        )
        if only_pair:
            available = [(key, weight) for key, weight in positive if key != main_stat]
            if not available:
                return 0.0
            if len(available) == 1:
                return 6 * available[0][1] * POTENTIAL_UNIT
            return (6 * available[0][1] + available[1][1]) * POTENTIAL_UNIT

        # A documentação pública define o potencial no contexto do atributo
        # principal da própria peça. Assim, somente esse atributo fica
        # indisponível como substatus ideal.
        optimal_main = main_stat
        potentials = sorted(
            (weight * POTENTIAL_UNIT for key, weight in positive if key != optimal_main),
            reverse=True,
        )
        potentials += [0.0] * (4 - len(potentials))
        return 6 * potentials[0] + potentials[1] + potentials[2] + potentials[3]

    @staticmethod
    def _resolve_optimal_main(
        part: str, main_stat: str, weights: dict[str, float],
        main_stats: dict[str, list[str]],
    ) -> str:
        allowed = set(main_stats.get(part, []))
        if part not in PART_MAIN_STATS or main_stat in allowed or weights.get(main_stat) == 1:
            return main_stat
        return max(
            PART_MAIN_STATS[part],
            key=lambda key: (
                1.0 if key in allowed or weights.get(key) == 1 else weights.get(key, 0.0),
                key in allowed, key not in HIGH_ROLLS,
            ),
        )

    @staticmethod
    def _part_key(relic: RelicSummary) -> str:
        key = (relic.slot_key or relic.slot).strip().upper()
        return SLOT_ALIASES.get(key, key)

    def _baseline_stats(
        self, character: CharacterSummary, current: dict[str, float]
    ) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
        totals = {key: 0.0 for key in HIGH_ROLLS}
        for relic in character.relics:
            for stat in relic.sub_stats:
                if stat.key in totals:
                    totals[stat.key] += stat.value

        baseline = dict(current)
        anchors: dict[str, float] = {}
        for percent_key, total_key in PERCENT_TO_TOTAL.items():
            flat_key = next(key for key, value in FLAT_TO_TOTAL.items() if value == total_key)
            total = current.get(total_key, 0.0)
            anchor = max((total - totals[flat_key]) / (1.0 + totals[percent_key]), 1.0)
            anchors[total_key] = anchor
            baseline[total_key] = anchor
        for key in HIGH_ROLLS:
            if key in FLAT_STATS or key in PERCENT_TO_TOTAL:
                continue
            baseline[key] = current.get(key, 0.0) - totals.get(key, 0.0)
        return baseline, anchors, totals

    def _generated_build(
        self, character: CharacterSummary, baseline: dict[str, float],
        anchors: dict[str, float], relic_totals: dict[str, float],
        weights: dict[str, float], archetype: str, total_rolls: int,
        maximum: bool,
    ) -> dict[str, float]:
        result = dict(baseline)
        counts = {key: 0.0 for key in HIGH_ROLLS}
        spent = 0.0
        candidates = [
            key for key in HIGH_ROLLS
            if key != "SpeedDelta" and weights.get(key, 0.0) > 0
        ]
        main_counts = self._main_stat_counts(character)

        if not maximum:
            for key in HIGH_ROLLS:
                if key == "SpeedDelta":
                    continue
                counts[key] = 2.0
                self._apply_stat(result, anchors, key, LOW_ROLLS[key] * 2.0)
                spent += 2.0
        else:
            # Uma peça +15 perfeita possui 4 rolls iniciais e 5 melhorias.
            # Os 24 rolls iniciais das seis peças precisam ocupar substatus
            # distintos e respeitar o bloqueio causado pelo atributo principal.
            initial_keys = sorted(
                candidates,
                key=lambda key: weights.get(key, 0.0),
                reverse=True,
            )[:4]
            allocated = 0.0
            for key in initial_keys:
                available_pieces = max(0, 6 - main_counts.get(key, 0))
                initial_count = min(float(available_pieces), 24.0 - allocated)
                counts[key] = initial_count
                self._apply_stat(result, anchors, key, HIGH_ROLLS[key] * initial_count)
                allocated += initial_count
            # Os espaços restantes são substatus sem peso, mas ainda fazem
            # parte dos 24 rolls iniciais da build perfeita.
            spent = 24.0

        target_speed = max(relic_totals.get("SpeedDelta", 0.0), 0.0)
        if target_speed:
            speed_roll = HIGH_ROLLS["SpeedDelta"] if maximum else MID_SPEED_ROLL
            speed_count = min(float(ceil(target_speed / speed_roll)), total_rolls - spent)
            counts["SpeedDelta"] = speed_count
            self._apply_stat(result, anchors, "SpeedDelta", target_speed)
            spent += speed_count

        while spent + 1 <= total_rolls and candidates:
            best_key = max(
                candidates,
                key=lambda key: self._roll_gain(
                    result, anchors, key, counts[key], main_counts.get(key, 0),
                    character.element, archetype, weights, maximum,
                ),
            )
            roll = HIGH_ROLLS[best_key] if maximum else LOW_ROLLS[best_key]
            if not maximum:
                roll *= self._effective_roll_delta(
                    counts[best_key], main_counts.get(best_key, 0), best_key
                )
            self._apply_stat(result, anchors, best_key, roll)
            counts[best_key] += 1.0
            spent += 1.0
        return result

    def _roll_gain(
        self, stats: dict[str, float], anchors: dict[str, float], key: str,
        count: float, matching_mains: int, element: str, archetype: str,
        weights: dict[str, float], maximum: bool,
    ) -> float:
        upgraded = dict(stats)
        roll = HIGH_ROLLS[key] if maximum else LOW_ROLLS[key]
        if not maximum:
            roll *= self._effective_roll_delta(count, matching_mains, key)
        self._apply_stat(upgraded, anchors, key, roll)
        return (
            self._combo_value(upgraded, element, archetype, weights)
            - self._combo_value(stats, element, archetype, weights)
        )

    @staticmethod
    def _effective_roll_delta(count: float, matching_mains: int, key: str) -> float:
        threshold = max(0.0, 12.0 - 2.0 * matching_mains)
        exponent = 0.90 if key == "SpeedDelta" else 0.75

        def effective(value: float) -> float:
            return value if value <= threshold else threshold + (value - threshold) ** exponent

        return effective(count + 1.0) - effective(count)

    @staticmethod
    def _main_stat_counts(character: CharacterSummary) -> dict[str, int]:
        counts: dict[str, int] = {}
        for relic in character.relics:
            key = relic.main_stat.key
            counts[key] = counts.get(key, 0) + 1
        return counts

    @staticmethod
    def _apply_stat(
        stats: dict[str, float], anchors: dict[str, float], key: str, value: float
    ) -> None:
        if key in PERCENT_TO_TOTAL:
            total_key = PERCENT_TO_TOTAL[key]
            stats[total_key] = stats.get(total_key, 0.0) + anchors.get(total_key, 1.0) * value
        elif key in FLAT_TO_TOTAL:
            total_key = FLAT_TO_TOTAL[key]
            stats[total_key] = stats.get(total_key, 0.0) + value
        else:
            stats[key] = stats.get(key, 0.0) + value

    @staticmethod
    def _detect_archetype(weights: dict[str, float]) -> str:
        if weights.get("BreakDamageAddedRatio", 0.0) >= max(
            weights.get("CriticalChance", 0.0), weights.get("CriticalDamage", 0.0), 0.5
        ):
            return "QUEBRA"
        if weights.get("StatusProbability", 0.0) > 0 and not (
            weights.get("CriticalChance", 0.0) or weights.get("CriticalDamage", 0.0)
        ):
            return "DOT"
        return "CRIT"

    @staticmethod
    def _combat_focus(weights: dict[str, float]) -> tuple[str, ...]:
        focus: list[str] = []
        if weights.get("CriticalChance", 0.0) > 0 or weights.get("CriticalDamage", 0.0) > 0:
            focus.append("CRIT")
        if weights.get("StatusProbability", 0.0) > 0:
            focus.append("EFFECT_HIT")
        if weights.get("BreakDamageAddedRatio", 0.0) > 0:
            focus.append("BREAK")
        return tuple(focus)

    @staticmethod
    def _primary_stat(stats: dict[str, float], weights: dict[str, float]) -> float:
        options = (
            (weights.get("HPAddedRatio", 0.0), stats.get("MaxHP", 0.0)),
            (weights.get("DefenceAddedRatio", 0.0), stats.get("Defence", 0.0)),
            (weights.get("AttackAddedRatio", 0.0), stats.get("Attack", 0.0)),
        )
        return max(options, key=lambda item: item[0])[1] or max(stats.get("Attack", 0.0), 1.0)

    def _combo_value(
        self, stats: dict[str, float], element: str, archetype: str,
        weights: dict[str, float],
    ) -> float:
        character = self._simulation_character
        if character is not None:
            stats = apply_team_buffs(character, stats, self._simulation_anchors)
            if str(character.avatar_id) == "1505":
                return self._evanescia_combo(stats, character.eidolon)

        primary = max(self._primary_stat(stats, weights), 1.0)
        damage_bonus = max(stats.get(ELEMENT_KEYS.get(element, ""), 0.0), 0.0)
        if archetype == "QUEBRA":
            break_effect = max(stats.get("BreakDamageAddedRatio", 0.0), 0.0)
            return primary**0.55 * (1.0 + break_effect) * (1.0 + damage_bonus * 0.25)
        if archetype == "DOT":
            effect_hit = max(stats.get("StatusProbability", 0.0), 0.0)
            return primary * (1.0 + damage_bonus) * (1.0 + min(effect_hit, 1.20) * 0.20)
        crit_rate = min(max(stats.get("CriticalChance", 0.0), 0.0), 1.0)
        crit_damage = max(stats.get("CriticalDamage", 0.0), 0.0)
        return primary * (1.0 + damage_bonus) * (1.0 + crit_rate * crit_damage)

    @staticmethod
    def _evanescia_combo(stats: dict[str, float], eidolon: int) -> float:
        """Rotação padrão da Evanescia com o time definido no Fribbels."""
        attack = max(stats.get("Attack", 0.0), 1.0)
        physical = max(stats.get("PhysicalAddedRatio", 0.0), 0.0)
        crit_rate = min(max(stats.get("CriticalChance", 0.0), 0.0), 1.0)
        crit_damage = max(stats.get("CriticalDamage", 0.0), 0.0)
        crit_multi = 1.0 + crit_rate * crit_damage

        vulnerability = 1.0 + stats.get("_Vulnerability", 0.0)
        resistance = 1.0 + stats.get("_ResistancePenetration", 0.0)
        defence_pen = min(max(stats.get("_DefencePenetration", 0.0), 0.0), 1.0)
        defence = 100.0 / ((95.0 + 20.0) * (1.0 - defence_pen) + 100.0)
        common = 0.90 * vulnerability * resistance * defence * crit_multi

        elation_def_pen = min(
            defence_pen + max(stats.get("_ElationDefencePenetration", 0.0), 0.0),
            1.0,
        )
        elation_defence = 100.0 / (
            (95.0 + 20.0) * (1.0 - elation_def_pen) + 100.0
        )
        elation_common = 0.90 * vulnerability * resistance * elation_defence * crit_multi

        # 1 Skill, 2 Supremos e 3 ataques do Mestre Raposa.
        standard_scaling = 3.30 + 2.0 * (1.76 + 1.296 * 9.0) + 3.0 * 1.10
        standard_damage = attack * standard_scaling * (1.0 + physical) * common

        def punchline(stacks: float) -> float:
            return 1.0 + (5.0 * stacks) / (stacks + 240.0)

        certified = punchline(600.0)
        skill_punchline = punchline(30.0)
        boon_punchline = punchline(90.0)
        elation_skill_multiplier = 2.0 if eidolon >= 1 else 1.0

        elation_scaling = (
            0.176 * certified
            + 2.0 * (0.264 + 0.308 * 9.0) * certified
            + 3.0 * 1.21 * elation_skill_multiplier * skill_punchline
            + 3.0 * 0.275 * certified
            + 10.0 * 0.22 * boon_punchline
        )
        elation = max(stats.get("ElationDamageAddedRatio", 0.0), 0.0)
        elation_damage = 7535.107 * elation_scaling * (1.0 + elation) * elation_common
        return standard_damage + elation_damage

    @staticmethod
    def _weighted_rolls(character: CharacterSummary, weights: dict[str, float]) -> float:
        total = 0.0
        for relic in character.relics:
            for stat in relic.sub_stats:
                low = LOW_ROLLS.get(stat.key)
                if low:
                    total += stat.value / low * weights.get(stat.key, 0.0)
        return total

    def _compare_upgrades(
        self, current: dict[str, float], anchors: dict[str, float], element: str,
        archetype: str, weights: dict[str, float], baseline_value: float,
        benchmark_value: float, perfection_value: float,
    ) -> list[UpgradeComparison]:
        current_value = self._combo_value(current, element, archetype, weights)
        comparisons: list[UpgradeComparison] = []
        for key, weight in weights.items():
            if key not in HIGH_ROLLS or weight <= 0:
                continue
            upgraded = dict(current)
            self._apply_stat(upgraded, anchors, key, HIGH_ROLLS[key])
            new_value = self._combo_value(upgraded, element, archetype, weights)
            gain = ((new_value / current_value) - 1.0) * 100 if current_value else 0.0
            comparisons.append(UpgradeComparison(
                stat_key=key, stat_name=STAT_NAMES.get(key, key),
                roll_value=self._format_roll(key, HIGH_ROLLS[key]),
                damage_gain_percent=gain,
                projected_score=self._normalized_score(
                    new_value, baseline_value, benchmark_value, perfection_value
                ),
                damage_gain_value=new_value - current_value,
            ))
            comparisons[-1].score_gain_percent = (
                comparisons[-1].projected_score
                - self._normalized_score(
                    current_value, baseline_value, benchmark_value, perfection_value
                )
            )
        comparisons.sort(key=lambda item: item.damage_gain_percent, reverse=True)
        return comparisons[:5]

    @staticmethod
    def _normalized_score(value: float, baseline: float, benchmark: float, perfection: float) -> float:
        perfection = max(perfection, benchmark)
        if value >= benchmark:
            span = perfection - benchmark
            score = 100.0 if span <= 0 else 100.0 + (value - benchmark) / span * 100.0
        else:
            span = benchmark - baseline
            score = 0.0 if span <= 0 else (value - baseline) / span * 100.0
        return max(0.0, score)

    @staticmethod
    def _format_roll(key: str, value: float) -> str:
        if key not in FLAT_STATS and key != "SpeedDelta":
            return f"+{value * 100:.2f}%"
        return f"+{value:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def grade(score: float, verified: bool = True) -> str:
        for threshold, grade in GRADE_THRESHOLDS:
            if score >= threshold and (grade != "AEON" or verified):
                return grade
        return "?"

    @staticmethod
    def relic_grade(score: float, verified: bool = True) -> str:
        for threshold, grade in RELIC_GRADE_THRESHOLDS:
            if score >= threshold and (grade != "AEON" or verified):
                return grade
        return "F"
