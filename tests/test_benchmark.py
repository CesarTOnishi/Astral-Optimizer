from __future__ import annotations

import unittest

from app.benchmark.engine import BenchmarkEngine, HIGH_ROLLS
from app.benchmark.teams import DEFAULT_TEAMS
from app.models import CharacterStat, CharacterSummary, RelicSummary
from app.ui.widgets import combat_stat_visible


def stat(key: str, value: float) -> CharacterStat:
    return CharacterStat(key, key, value, str(value), key not in {"Attack", "Speed"})


def character(
    relics: list[RelicSummary], avatar_id: str = "1220", name: str = "Feixiao"
) -> CharacterSummary:
    return CharacterSummary(
        name=name, avatar_id=avatar_id, level=80, eidolon=0,
        light_cone="Teste", light_cone_level=80, light_cone_rank=1,
        light_cone_icon_url="", relic_count=len(relics), rarity=5,
        element="Vento", path="Caça", icon_url="", splash_url="",
        stats=[
            stat("Attack", 2500), stat("MaxHP", 3000), stat("Defence", 900),
            stat("SpeedDelta", 134), stat("CriticalChance", 0.75),
            stat("CriticalDamage", 1.50), stat("WindAddedRatio", 0.388),
        ],
        relics=relics, raw={},
    )


def evanescia_showcase_character() -> CharacterSummary:
    relic_data = [
        ("HEAD", "HPDelta", 705.6, [("DefenceDelta", 19.051896), ("CriticalChance", 0.02592), ("CriticalDamage", 0.27864), ("StatusProbability", 0.08208)]),
        ("HAND", "AttackDelta", 352.8, [("HPDelta", 38.103795), ("CriticalChance", 0.06156), ("CriticalDamage", 0.22032), ("BreakDamageAddedRatio", 0.05832)]),
        ("BODY", "CriticalDamage", 0.648, [("HPAddedRatio", 0.0432), ("SpeedDelta", 2.6), ("CriticalChance", 0.18468), ("StatusProbability", 0.03888)]),
        ("FOOT", "AttackAddedRatio", 0.432, [("HPDelta", 38.103795), ("DefenceAddedRatio", 0.0972), ("CriticalChance", 0.05508), ("CriticalDamage", 0.2268)]),
        ("ORBIT", "PhysicalAddedRatio", 0.388803, [("AttackDelta", 21.168773), ("CriticalChance", 0.02592), ("CriticalDamage", 0.23328), ("StatusProbability", 0.0864)]),
        ("ROPE", "SPRatio", 0.194394, [("SpeedDelta", 2.3), ("CriticalChance", 0.05508), ("CriticalDamage", 0.24624), ("StatusResistance", 0.0432)]),
    ]
    relics = [
        RelicSummary(
            slot=slot, slot_key=slot, set_name="Referência", level=15, rarity=5,
            icon_url="", main_stat=stat(main_key, main_value),
            sub_stats=[stat(key, value) for key, value in substats],
        )
        for slot, main_key, main_value, substats in relic_data
    ]
    result = character(relics, "1505", "Evanescia")
    result.eidolon = 2
    result.stats = [
        stat("MaxHP", 2868.5998332), stat("Attack", 2339.234117),
        stat("Defence", 1032.74949), stat("Speed", 113.9),
        stat("CriticalChance", 0.645239998), stat("CriticalDamage", 3.11328),
        stat("BreakDamageAddedRatio", 0.05832), stat("SPRatio", 1.194394),
        stat("StatusProbability", 0.20736), stat("StatusResistance", 0.0432),
        stat("PhysicalAddedRatio", 0.388803), stat("ElationDamageAddedRatio", 0.26),
    ]
    result.raw = {
        "light_cone": {
            "stats": [{"type": "BaseAttack", "value": 635.04}],
        },
    }
    return result


class BenchmarkTests(unittest.TestCase):
    def test_combat_stats_follow_character_archetype_and_hybrid_weights(self) -> None:
        hysilens = BenchmarkEngine().analyze(character([], "1410", "Hysilens"))
        self.assertEqual(hysilens.archetype, "DOT")
        self.assertEqual(hysilens.combat_focus, ("EFFECT_HIT",))
        self.assertTrue(combat_stat_visible(
            hysilens.archetype, "Effect Hit Rate", hysilens.combat_focus
        ))
        self.assertFalse(combat_stat_visible(
            hysilens.archetype, "CRIT Rate", hysilens.combat_focus
        ))

        fugue = BenchmarkEngine().analyze(character([], "1225", "Fugue"))
        self.assertEqual(fugue.archetype, "QUEBRA")
        self.assertIn("EFFECT_HIT", fugue.combat_focus)
        self.assertIn("BREAK", fugue.combat_focus)
        self.assertTrue(combat_stat_visible(
            fugue.archetype, "Effect Hit Rate", fugue.combat_focus
        ))
        self.assertTrue(combat_stat_visible(
            fugue.archetype, "Break Effect", fugue.combat_focus
        ))

    def test_fribbels_default_teams_are_available(self) -> None:
        self.assertGreaterEqual(len(DEFAULT_TEAMS), 70)
        self.assertEqual(
            tuple(member.name for member in DEFAULT_TEAMS["1220"].members),
            ("Mortenax Blade", "Ashveil", "Hyacine"),
        )

    def test_official_grade_thresholds(self) -> None:
        self.assertEqual(BenchmarkEngine.grade(40), "F")
        self.assertEqual(BenchmarkEngine.grade(100), "SS")
        self.assertEqual(BenchmarkEngine.grade(150), "AEON")
        self.assertEqual(BenchmarkEngine.relic_grade(60), "SS")
        self.assertEqual(BenchmarkEngine.relic_grade(90), "AEON")

    def test_normalization_uses_baseline_benchmark_and_perfection(self) -> None:
        normalize = BenchmarkEngine._normalized_score
        self.assertEqual(normalize(10, 10, 20, 30), 0)
        self.assertEqual(normalize(20, 10, 20, 30), 100)
        self.assertEqual(normalize(30, 10, 20, 30), 200)
        self.assertEqual(normalize(25, 10, 20, 30), 150)

    def test_perfect_feixiao_hand_relic_scores_100(self) -> None:
        relic = RelicSummary(
            slot="Mãos", slot_key="HAND", set_name="Teste", level=15, rarity=5,
            icon_url="", main_stat=stat("AttackDelta", 352.8),
            sub_stats=[
                stat("CriticalDamage", HIGH_ROLLS["CriticalDamage"] * 6),
                stat("CriticalChance", HIGH_ROLLS["CriticalChance"]),
                stat("SpeedDelta", HIGH_ROLLS["SpeedDelta"]),
                stat("AttackAddedRatio", HIGH_ROLLS["AttackAddedRatio"]),
            ],
        )
        rating = BenchmarkEngine().rate_relic(character([relic]), relic)
        self.assertAlmostEqual(rating.score, 100.0, places=1)
        self.assertEqual(rating.grade, "AEON")

    def test_analysis_builds_three_reference_values(self) -> None:
        result = BenchmarkEngine().analyze(character([]))
        self.assertGreater(result.baseline_value, 0)
        self.assertGreaterEqual(result.benchmark_value, result.baseline_value)
        self.assertGreaterEqual(result.perfection_value, result.benchmark_value)

    def test_evanescia_reference_relics_match_showcase(self) -> None:
        sphere = RelicSummary(
            slot="Esfera Plana", slot_key="ORBIT", set_name="Teste", level=15,
            rarity=5, icon_url="", main_stat=stat("PhysicalAddedRatio", 0.388803),
            sub_stats=[
                stat("AttackDelta", 21.168773), stat("CriticalChance", 0.02592),
                stat("CriticalDamage", 0.23328), stat("StatusProbability", 0.0864),
            ],
        )
        rope = RelicSummary(
            slot="Corda de Ligação", slot_key="ROPE", set_name="Teste", level=15,
            rarity=5, icon_url="", main_stat=stat("SPRatio", 0.194394),
            sub_stats=[
                stat("SpeedDelta", 2.3), stat("CriticalChance", 0.05508),
                stat("CriticalDamage", 0.24624), stat("StatusResistance", 0.0432),
            ],
        )
        evanescia = character([sphere, rope], "1505", "Evanescia")
        engine = BenchmarkEngine()
        self.assertAlmostEqual(engine.rate_relic(evanescia, sphere).score, 61.2, places=1)
        self.assertEqual(engine.rate_relic(evanescia, sphere).grade, "SS")
        self.assertAlmostEqual(engine.rate_relic(evanescia, rope).score, 74.8, places=1)
        self.assertEqual(engine.rate_relic(evanescia, rope).grade, "SSS")

    def test_evanescia_default_team_benchmark_reference(self) -> None:
        result = BenchmarkEngine().analyze(evanescia_showcase_character())
        self.assertAlmostEqual(result.score, 144.3, delta=0.5)
        self.assertEqual(result.grade, "WTF+")
        combat = {stat.key: stat.formatted_value for stat in result.combat_stats}
        self.assertEqual(combat["Speed"], "126,3")
        self.assertEqual(combat["CriticalChance"], "104,5%")
        self.assertEqual(combat["CriticalDamage"], "534,3%")
        self.assertEqual(combat["SPRatio"], "40,2%")
        self.assertEqual(combat["ElationDamageAddedRatio"], "198,8%")

    def test_official_fribbels_result_replaces_local_estimate(self) -> None:
        character = evanescia_showcase_character()
        engine = BenchmarkEngine()
        result = engine.analyze(character)
        engine.apply_fribbels_result(character, result, {
            "score": 144.3813,
            "grade": "WTF+",
            "damage": 7_519_578.0,
            "baseline": 3_961_524.0,
            "benchmark": 6_309_674.0,
            "perfection": 9_035_830.0,
            "combatStats": {
                "HP": 2868.6, "ATK": 3382.25, "DEF": 1032.75,
                "SPD": 113.9, "CRIT Rate": 0.94524,
                "CRIT DMG": 4.33328, "Energy Regeneration Rate": 0.40239,
                "Physical DMG Boost": 0.3888, "Elation": 1.68666,
            },
            "primaryActionStats": None,
            "abilityBreakdown": [
                {"actionType": "ULT", "actionName": "START_ULT", "damage": 2_528_300.0},
                {"actionType": "UNIQUE", "actionName": "DEFAULT_UNIQUE", "damage": 297_600.0},
                {"actionType": "ELATION_SKILL", "actionName": "END_ELATION_SKILL", "damage": 651_800.0},
                {"actionType": "NULL", "actionName": "NULL", "damage": 0.0},
            ],
            "substatUpgrades": [{
                "stat": "CRIT DMG",
                "damageGainPercent": 1.69,
                "scoreGainPercent": 3.77,
                "damageGain": 10_329.8,
                "projectedScore": 148.15,
            }],
            "mainStatUpgrades": [{
                "part": "PlanarSphere",
                "stat": "ATK%",
                "damageGainPercent": -2.03,
                "scoreGainPercent": -5.59,
                "damageGain": -152_447.1,
                "projectedScore": 138.8,
            }],
            "customTeam": True,
            "teammates": [{
                "characterId": "1502",
                "characterEidolon": 1,
                "lightCone": "21064",
                "lightConeSuperimposition": 5,
                "teamRelicSet": "Messenger Traversing Hackerspace",
                "teamOrnamentSet": "Broken Keel",
            }],
        })
        self.assertEqual(result.score, 144.3)
        self.assertEqual(result.grade, "WTF+")
        self.assertTrue(result.exact_simulation)
        self.assertEqual(result.engine_source, "fribbels")
        self.assertEqual(len(result.upgrades), 1)
        self.assertEqual(result.upgrades[0].stat_name, "Dano Crítico")
        self.assertAlmostEqual(result.upgrades[0].damage_gain_value, 10_329.8)
        self.assertEqual(len(result.main_upgrades), 1)
        self.assertEqual(result.main_upgrades[0].roll_value, "Esfera →")
        self.assertEqual(result.main_upgrades[0].stat_name, "ATQ %")
        self.assertEqual(result.main_upgrades[0].part_key, "PlanarSphere")
        self.assertEqual(result.team_name, "Time customizado")
        self.assertEqual(result.team_members, ("Yao Guang",))
        self.assertIn("E1", result.team_details[0])
        self.assertIn("Messenger Traversing Hackerspace", result.team_details[0])
        self.assertIn("Broken Keel", result.team_details[0])
        self.assertEqual(len(result.ability_breakdown), 3)
        self.assertEqual(result.ability_breakdown[0].label, "[ Supremo")
        self.assertEqual(result.ability_breakdown[2].label, "Perícia de Euforia ]")
        self.assertEqual(result.ability_breakdown[0].damage, 2_528_300.0)
        combat = {stat.key: stat.formatted_value for stat in result.combat_stats}
        self.assertEqual(combat["ATK"], "3382")
        self.assertEqual(combat["Energy Regeneration Rate"], "40,2%")


if __name__ == "__main__":
    unittest.main()
