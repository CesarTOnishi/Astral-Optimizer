import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from app.models import CharacterStat
from app.ui.widgets import StatRow, compact_stat_name, stat_icon_path


class StatIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_main_relic_and_elemental_keys_have_local_icons(self) -> None:
        keys = (
            "MaxHP",
            "HPAddedRatio",
            "Attack",
            "AttackAddedRatio",
            "Defence",
            "SpeedDelta",
            "CriticalChance",
            "CriticalDamage",
            "StatusProbability",
            "StatusResistance",
            "BreakDamageAddedRatio",
            "SPRatio",
            "PhysicalAddedRatio",
            "FireAddedRatio",
            "IceAddedRatio",
            "ThunderAddedRatio",
            "WindAddedRatio",
            "QuantumAddedRatio",
            "ImaginaryAddedRatio",
            "Score",
            "Elation",
            "ElationAddedRatio",
            "ElationDamageAddedRatio",
        )
        self.assertTrue(all(stat_icon_path(key).is_file() for key in keys))

    def test_stat_row_uses_a_real_pixmap_icon(self) -> None:
        stat = CharacterStat(
            key="CriticalDamage",
            name="Dano Crítico",
            value=1.5,
            formatted_value="150,0%",
            is_percentage=True,
        )
        row = StatRow(stat)
        icon = row.findChild(QLabel, "statPropertyIcon")
        self.assertIsNotNone(icon)
        self.assertIsNotNone(icon.pixmap())
        self.assertFalse(icon.pixmap().isNull())

    def test_compact_names_cover_elements_and_effect_stats(self) -> None:
        expected = {
            "PhysicalAddedRatio": "Dano Fís.",
            "FireAddedRatio": "Dano Fogo",
            "IceAddedRatio": "Dano Gelo",
            "ThunderAddedRatio": "Dano Raio",
            "WindAddedRatio": "Dano Vento",
            "QuantumAddedRatio": "Dano Quânt.",
            "ImaginaryAddedRatio": "Dano Imag.",
            "ElationAddedRatio": "Dano Euforia",
            "BreakDamageAddedRatio": "Efeito Quebra",
            "StatusProbability": "Acerto Efeito",
            "SPRatio": "Regen. Energia",
        }
        for key, short_name in expected.items():
            with self.subTest(key=key):
                self.assertEqual(compact_stat_name(key, "Nome completo"), short_name)
        self.assertEqual(compact_stat_name("unknown", "Taxa de Acerto de Efeito"), "Acerto Efeito")


if __name__ == "__main__":
    unittest.main()
