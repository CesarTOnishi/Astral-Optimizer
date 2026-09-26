import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QScrollArea, QWidget, QVBoxLayout

from app.benchmark import BenchmarkEngine
from app.benchmark.models import CombatStat
from app.preferences import THEMES, ExperiencePreferences, experience_stylesheet
from app.section_loading import SectionLoadController
from app.ui.build_layout import BuildDetailSplitter
from app.ui.main_window import MainWindow
from app.ui.widgets import RelicCard, TeamCard
from test_benchmark import evanescia_showcase_character


def build_preview():
    """Real production panels, isolated from databases and network workers."""
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.section_loading = SectionLoadController(window)
    window.section_statuses = {}
    window.current_relic_cards = []
    root = QWidget()
    root.setFont(QFont("Segoe UI", 10))
    layout = QVBoxLayout(root)
    window.content_splitter = BuildDetailSplitter()
    window.art_panel = window._build_art_panel()
    window.stats_panel = window._build_stats_panel()
    window.relics_panel = window._build_relics_panel()
    for panel in (window.art_panel, window.stats_panel, window.relics_panel):
        window.content_splitter.addWidget(panel)
    window.content_splitter.composition_changed.connect(window._reflow_relic_cards)
    window.content_splitter.composition_changed.connect(window._refresh_detail_name_layout)
    layout.addWidget(window.content_splitter)
    layout.addWidget(window._build_build_history_panel())
    layout.addWidget(window._build_benchmark_section())
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(root)
    character = evanescia_showcase_character()
    window.detail_name.setText("Evanescia · Nome longo para validação de quebra de linhas")
    window.light_cone_banner.set_info("Cone de Luz com um nome muito longo para validar a composição", 80, 1)
    window._display_stats(character)
    result = BenchmarkEngine().analyze(character)
    window.benchmark_card.set_result(result)
    window.combat_stats_card.set_result(result)
    window.relic_empty.hide()
    for relic in character.relics:
        card = RelicCard(
            relic, BenchmarkEngine().rate_relic(character, relic), expand_vertical=True
        )
        window.current_relic_cards.append(card)
    return window, scroll


class BuildRedesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # Qt's offscreen Windows plugin does not discover system fonts itself.
        from pathlib import Path
        font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf"
        cls.font_id = QFontDatabase.addApplicationFont(str(font)) if font.is_file() else -1

    @classmethod
    def tearDownClass(cls):
        if cls.font_id >= 0:
            QFontDatabase.removeApplicationFont(cls.font_id)

    def settle(self):
        for _ in range(8):
            self.app.processEvents()

    def test_all_themes_resize_without_horizontal_overflow_or_lost_widgets(self):
        window, scroll = build_preview()
        scroll.show()
        try:
            original_cards = tuple(window.current_relic_cards)
            for theme in THEMES:
                scroll.setStyleSheet(experience_stylesheet(ExperiencePreferences(theme)))
                for width, height in ((1500, 900), (600, 600), (760, 600), (1100, 720), (1500, 900)):
                    with self.subTest(theme=theme, width=width):
                        scroll.resize(width, height)
                        self.settle()
                        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
                        available = window.content_splitter.width()
                        self.assertEqual(window.content_splitter.orientation(), Qt.Orientation.Horizontal)
                        if available < 660:
                            self.assertIs(window.art_panel.parentWidget(), window.content_splitter._compact)
                            self.assertIs(window.stats_panel.parentWidget(), window.content_splitter._compact)
                            self.assertIs(window.relics_panel.parentWidget(), window.content_splitter._compact)
                        else:
                            self.assertIs(window.art_panel.parentWidget(), window.content_splitter)
                            self.assertIs(window.stats_panel.parentWidget(), window.content_splitter)
                            self.assertIs(window.relics_panel.parentWidget(), window.content_splitter)
                        self.assertEqual(tuple(window.current_relic_cards), original_cards)
                        self.assertEqual(window.relic_grid.count(), 6)
                        self.assertEqual(window.stats_scroll.horizontalScrollBar().maximum(), 0)
                        self.assertEqual(window.relic_scroll.horizontalScrollBar().maximum(), 0)
                        expected_avatar_size = 52 if window.team_card.width() >= 310 else 44
                        for _member, avatar, _eidolon, cone, _superimposition in window.team_card.member_visuals:
                            self.assertEqual(avatar.width(), expected_avatar_size)
                            self.assertEqual(cone.width(), 32 if expected_avatar_size == 52 else 28)
                        name = window.detail_name
                        self.assertGreaterEqual(name.height(), name.heightForWidth(name.width()))
                        cone = window.light_cone_banner.caption
                        self.assertGreaterEqual(cone.height(), cone.heightForWidth(cone.width()))
        finally:
            scroll.close()
            scroll.deleteLater()
            window.deleteLater()

    def test_column_dividers_cannot_be_dragged(self):
        window, scroll = build_preview()
        scroll.resize(900, 680)
        scroll.show()
        try:
            self.settle()
            splitter = window.content_splitter
            self.assertEqual(splitter._mode, "wide")
            original = splitter.sizes()
            handle = splitter.handle(1)
            self.assertEqual(handle.cursor().shape(), Qt.CursorShape.ArrowCursor)
            center = handle.rect().center()
            QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=center)
            QTest.mouseMove(handle, QPoint(center.x() + 70, center.y()))
            QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=QPoint(center.x() + 70, center.y()))
            self.settle()
            self.assertEqual(splitter.sizes(), original)
        finally:
            scroll.close()
            scroll.deleteLater()
            window.deleteLater()

    def test_team_portraits_grow_with_column_and_keep_loaded_images(self):
        card = TeamCard()
        avatar = card.member_visuals[0][1]
        cone = card.member_visuals[0][3]
        image = QPixmap(64, 64)
        image.fill(QColor("#bc6688"))
        avatar.set_image(image)
        card.resize(350, 200)
        card.show()
        try:
            self.settle()
            self.assertEqual((avatar.width(), cone.width()), (52, 32))
            self.assertEqual(avatar.pixmap().width(), 52)
            card.resize(240, 200)
            self.settle()
            self.assertEqual((avatar.width(), cone.width()), (44, 28))
            self.assertEqual(avatar.pixmap().width(), 44)
        finally:
            card.close()
            card.deleteLater()

    def test_restored_width_shows_two_relic_columns_and_single_line_stats(self):
        window, scroll = build_preview()
        scroll.resize(900, 680)
        scroll.show()
        try:
            self.settle()
            self.assertEqual(window.content_splitter._mode, "wide")
            self.assertEqual(window.relic_grid.getItemPosition(0)[:2], (0, 0))
            self.assertEqual(window.relic_grid.getItemPosition(1)[:2], (0, 1))
            self.assertEqual(window.relic_grid.getItemPosition(5)[:2], (2, 1))
            self.assertEqual(window.stats_scroll.horizontalScrollBar().maximum(), 0)
            self.assertEqual(window.relic_scroll.horizontalScrollBar().maximum(), 0)
            self.assertEqual(window.relic_scroll.verticalScrollBar().maximum(), 0)
            last_card = window.current_relic_cards[-1]
            bottom = last_card.mapTo(
                window.relic_scroll.viewport(), QPoint(0, last_card.height())
            ).y()
            self.assertLessEqual(window.relic_scroll.viewport().height() - bottom, 12)
            for card in window.current_relic_cards:
                for label in card.findChildren(QLabel):
                    if label.objectName() in {"rowName", "relicSub"}:
                        self.assertFalse(label.wordWrap(), label.text())
                        self.assertTrue(label.toolTip())
        finally:
            scroll.close()
            scroll.deleteLater()
            window.deleteLater()

    def test_short_character_with_extra_combat_stats_fits_at_700_height(self):
        window, scroll = build_preview()
        scroll.setStyleSheet(experience_stylesheet(ExperiencePreferences("astral")))
        scroll.resize(1009, 710)
        window.detail_name.setText("Saber")
        character = evanescia_showcase_character()
        character.element = "Físico"
        window._display_stats(character)
        result = BenchmarkEngine().analyze(character)
        result.combat_stats += (
            CombatStat("WindAddedRatio", "Dano Vento", "223,3%", True),
            CombatStat("ElationDamageAddedRatio", "Dano Euforia", "0,0%"),
        )
        window.combat_stats_card.set_result(result)
        window.benchmark_section_status.hide()
        scroll.show()
        try:
            for _ in range(40):
                self.app.processEvents()
            self.assertEqual(window.content_splitter.height(), 700)
            self.assertEqual(window.stats_scroll.verticalScrollBar().maximum(), 0)
            self.assertEqual(window.relic_scroll.verticalScrollBar().maximum(), 0)
        finally:
            scroll.close()
            scroll.deleteLater()
            window.deleteLater()

    def test_benchmark_loading_error_and_unsupported_never_show_old_combo(self):
        window, scroll = build_preview()
        try:
            result = BenchmarkEngine().analyze(evanescia_showcase_character())
            result.engine_source = "fribbels"
            card = window.benchmark_card
            card.set_result(result)
            self.assertNotIn("—", card.combo.text())
            card.set_loading()
            self.assertIn("—", card.combo.text())
            card.set_result(result)
            card.set_engine_error("Falha de conexão " * 20)
            self.assertIn("—", card.combo.text())
            result.engine_source = "unsupported"
            card.set_result(result)
            self.assertEqual(card.grade.text(), "N/A")
            self.assertIn("—", card.combo.text())
        finally:
            scroll.deleteLater()
            window.deleteLater()

    def test_name_height_does_not_accumulate_on_repeated_layout_updates(self):
        window, scroll = build_preview()
        scroll.resize(1500, 900)
        scroll.show()
        try:
            self.settle()
            for name in ("Evanescia", "Nome de personagem muito longo " * 4, "Evanescia"):
                window.detail_name.setText(name)
                window._refresh_detail_name_layout()
                initial_height = window.detail_name.height()
                for _ in range(30):
                    window._refresh_detail_name_layout()
                self.assertEqual(window.detail_name.height(), initial_height)
            self.assertLess(window.detail_name.height(), 50)
        finally:
            scroll.close()
            scroll.deleteLater()
            window.deleteLater()
