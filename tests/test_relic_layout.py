import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QGridLayout, QWidget

from app.config import APP_STYLESHEET
from app.models import CharacterStat, RelicSummary
from app.benchmark.models import RelicRating
from app.ui.widgets import RelicCard


class RelicLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_long_names_and_holder_history_do_not_overlap_stats(self):
        relic = RelicSummary(
            "Esfera plana", "Menina Sempre Sorridente e o Caminho das Estrelas",
            15, 5, "", CharacterStat("crit", "Dano CRIT", 64.8, "64.8%", True),
            [CharacterStat("stat", name, 18.4, "18.4%", True, upgrades=4)
             for name in ("PV", "VEL", "Chance de CRIT", "Taxa de Acerto de Efeito")],
        )
        for width in (225, 260, 330):
            for equipped in (False, True):
                with self.subTest(width=width, equipped=equipped):
                    parent = QWidget()
                    parent.setFont(QFont("Segoe UI", 10))
                    parent.setStyleSheet(APP_STYLESHEET)
                    grid = QGridLayout(parent)
                    card = RelicCard(
                        relic, RelicRating(89.7, "WTF+"),
                        holder_name="Castorice" if not equipped else "",
                        previous_holder_name="Evanescia" if not equipped else "",
                        expand_vertical=equipped,
                    )
                    grid.addWidget(card, 0, 0)
                    parent.resize(width + 22, 200)
                    parent.show()
                    self.app.processEvents()
                    for label in card.findChildren(QLabel):
                        if label.text() and label.isVisible():
                            needed = label.heightForWidth(label.width()) if label.wordWrap() else label.minimumSizeHint().height()
                            self.assertGreaterEqual(label.height(), needed, label.text())
                    main = card.findChild(QLabel, "rowName")
                    header_bottom = card.icon.mapTo(card, QPoint(0, card.icon.height())).y()
                    main_top = main.mapTo(card, QPoint()).y()
                    self.assertGreaterEqual(main_top, header_bottom)
                    parent.close()
                    parent.deleteLater()
