import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from app.models import CharacterStat
from app.ui.widgets import StatRow, stat_icon_path


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


if __name__ == "__main__":
    unittest.main()
