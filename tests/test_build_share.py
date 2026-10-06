import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

import app.ui.build_share as build_share
from app.benchmark.models import BenchmarkResult, RelicRating
from app.models import CharacterStat, CharacterSummary, RelicSummary
from app.ui.build_share import bundled_share_icon, render_build_share_card, share_details


class BuildShareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _character(self, name: str, relics: list[RelicSummary]) -> CharacterSummary:
        return CharacterSummary(
            name=name,
            avatar_id="test",
            level=80,
            eidolon=1,
            light_cone="Cone de Luz com um nome muito longo para testar o cartão exportado",
            light_cone_level=80,
            light_cone_rank=1,
            light_cone_icon_url="",
            relic_count=len(relics),
            rarity=5,
            element="Físico",
            path="Euforia",
            icon_url="",
            splash_url="",
            stats=[],
            relics=relics,
            raw={},
        )

    def _result(self) -> BenchmarkResult:
        return BenchmarkResult(
            archetype="test",
            damage_index=123456.0,
            effective_rolls=0.0,
            score=141.2,
            grade="WTF+",
            upgrades=[],
            team_name="Time de exemplo",
            engine_source="fribbels",
        )

    def test_export_handles_missing_assets_and_long_names(self) -> None:
        card = render_build_share_card(
            self._character("Personagem de teste com um nome excepcionalmente longo", []),
            self._result(),
            "600123456",
            QPixmap(),
            QPixmap(),
            [],
            [],
            custom_team=False,
            hide_uid=True,
        )

        self.assertFalse(card.isNull())
        self.assertEqual((card.width(), card.height()), (1920, 1080))
        self.assertNotEqual(card.toImage().pixelColor(60, 160), QColor("#0a101c"))

    def test_export_uses_relic_data_and_character_art(self) -> None:
        stat = CharacterStat("atk", "ATQ%", 43.2, "43.2%", True)
        relic = RelicSummary(
            slot="Cabeça",
            set_name="Conjunto de teste",
            level=15,
            rarity=5,
            icon_url="",
            main_stat=stat,
            sub_stats=[stat],
        )
        artwork = QPixmap(200, 300)
        artwork.fill(QColor("#e876a2"))
        character = self._character("Evanescia", [relic])
        args = (
            character, self._result(), "600123456", artwork, QPixmap(),
            [{"key": "atk", "name": "ATQ", "formatted": "2709"}],
        )
        with_relic = render_build_share_card(
            *args, [(relic, RelicRating(103.4, "SS"), QPixmap())], custom_team=True
        )
        without_relic = render_build_share_card(*args, [], custom_team=True)

        self.assertEqual((with_relic.width(), with_relic.height()), (1920, 1080))
        self.assertEqual(with_relic.toImage().pixelColor(800, 300), QColor("#e876a2"))
        self.assertNotEqual(
            with_relic.toImage().pixelColor(1397, 167),
            without_relic.toImage().pixelColor(1397, 167),
        )

    def test_eidolon_column_uses_character_unlock_count(self) -> None:
        icons = [QPixmap(48, 48) for _ in range(6)]
        for icon in icons:
            icon.fill(QColor("white"))
        character = self._character("Evanescia", [])
        character.eidolon = 2
        args = (character, self._result(), "600123456", QPixmap(), QPixmap(), [], [])
        e2 = render_build_share_card(*args, custom_team=False, eidolons=icons).toImage()
        character.eidolon = 6
        e6 = render_build_share_card(*args, custom_team=False, eidolons=icons).toImage()

        self.assertEqual(e2.pixelColor(1323, 75), e6.pixelColor(1323, 75))
        self.assertNotEqual(e2.pixelColor(1323, 297), e6.pixelColor(1323, 297))

    def test_share_details_keeps_effective_skill_levels_and_cone_base_stats(self) -> None:
        character = self._character("Evanescia", [])
        character.avatar_id = "1505"
        character.raw = {
            "traces": [
                {"type": 2, "icon": "https://example/SkillIcon_1505_Normal.png",
                 "level": 6, "boosted": False},
                {"type": 2, "icon": "https://example/SkillIcon_1505_BP.png",
                 "level": 12, "boosted": True},
            ],
            "eidolons": [{"icon": f"https://example/e{index}.png"} for index in range(6)],
            "light_cone": {"rarity": 5, "stats": [
                {"type": "BaseHP", "formatted_value": "952"},
                {"type": "BaseAttack", "formatted_value": "635"},
                {"type": "Attack", "formatted_value": "2339"},
            ]},
        }
        catalog = SimpleNamespace(
            id="1505",
        )
        repository = SimpleNamespace(
            characters=lambda: [catalog],
            skills_for=lambda _character: [],
            ranks_for=lambda _character: [],
            _data={"character_skills": {}},
        )
        with patch("app.catalog.repository.CatalogRepository", return_value=repository):
            details = share_details(character)

        self.assertEqual((details["skills"][0]["level"], details["skills"][1]["level"]), (6, 12))
        self.assertTrue(details["skills"][1]["boosted"])
        self.assertEqual(details["cone_rarity"], 5)
        self.assertEqual([item["type"] for item in details["cone_stats"]],
                         ["BaseHP", "BaseAttack"])

    def test_bundled_evanescia_icons_work_without_catalog_network(self) -> None:
        self.assertFalse(bundled_share_icon(
            "https://enka.network/SkillIcon_1505_Rank2.png"
        ).isNull())
        self.assertFalse(bundled_share_icon(
            "https://raw.githubusercontent.com/assets/1505_basic_atk.png"
        ).isNull())

    def test_total_score_displays_benchmark_instead_of_relic_sum(self) -> None:
        character = self._character("Evanescia", [])
        result = self._result()
        with patch.object(build_share, "_text", wraps=build_share._text) as draw:
            render_build_share_card(
                character, result, "600123456", QPixmap(), QPixmap(), [], [],
                custom_team=False,
            )
        labels = [call.args[2] for call in draw.call_args_list]

        self.assertIn("DPS BENCHMARK", labels)
        self.assertIn("141.2%", labels)
        self.assertIn("WTF+", labels)
        self.assertNotIn("PONTUAÇÃO TOTAL", labels)


if __name__ == "__main__":
    unittest.main()
