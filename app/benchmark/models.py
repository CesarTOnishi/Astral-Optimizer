from dataclasses import dataclass, field


@dataclass(slots=True)
class CombatStat:
    key: str
    name: str
    formatted_value: str
    changed: bool = False


@dataclass(slots=True)
class UpgradeComparison:
    stat_key: str
    stat_name: str
    roll_value: str
    damage_gain_percent: float
    projected_score: float
    damage_gain_value: float = 0.0
    score_gain_percent: float = 0.0
    part_key: str = ""


@dataclass(slots=True)
class AbilityDamageStep:
    action_type: str
    action_name: str
    label: str
    damage: float


@dataclass(slots=True)
class BenchmarkResult:
    archetype: str
    damage_index: float
    effective_rolls: float
    score: float
    grade: str
    upgrades: list[UpgradeComparison]
    main_upgrades: list[UpgradeComparison] = field(default_factory=list)
    baseline_value: float = 0.0
    benchmark_value: float = 0.0
    perfection_value: float = 0.0
    team_name: str = "Sem time padrão"
    team_members: tuple[str, ...] = ()
    team_details: tuple[str, ...] = ()
    team_character_ids: tuple[str, ...] = ()
    team_light_cone_ids: tuple[str, ...] = ()
    combat_stats: tuple[CombatStat, ...] = ()
    combat_focus: tuple[str, ...] = ()
    ability_breakdown: tuple[AbilityDamageStep, ...] = ()
    exact_simulation: bool = False
    engine_source: str = "local"


@dataclass(slots=True)
class RelicRating:
    score: float
    grade: str
