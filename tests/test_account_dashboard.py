import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel
from app.auth.service import AuthUser
from app.benchmark import BenchmarkEngine
from app.relics.database import RelicDatabase
from app.ui.account_dashboard import AccountDashboard
from app.preferences import THEMES, ExperiencePreferences, experience_stylesheet
from app.warp.database import WarpDatabase
from app.warp.models import WarpRecord, WarpSummary


class AccountDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_missing_data_and_long_names_fit_all_themes(self):
        from PySide6.QtWidgets import QScrollArea
        with tempfile.TemporaryDirectory() as directory:
            warps = WarpDatabase(Path(directory) / "warps.db")
            relics = RelicDatabase(Path(directory) / "relics.db")
            user = AuthUser(7, "test", "", "600000001")
            warps.add_records([WarpRecord("1", user.game_uid, "11", "1003",
                "Personagem com nome muito longo para testar o resumo da conta",
                "Character", 5, "2026-01-01 00:00:01")], user.id)
            panel = AccountDashboard()
            panel.refresh(user, None, warps, relics, BenchmarkEngine())
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(panel)
            scroll.show()
            try:
                for theme in THEMES:
                    scroll.setStyleSheet(experience_stylesheet(ExperiencePreferences(theme)))
                    for width in (480, 760, 1200):
                        with self.subTest(theme=theme, width=width):
                            scroll.resize(width, 650)
                            for _ in range(4):
                                self.app.processEvents()
                            self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
                            self.assertEqual(panel.metrics["Personagens públicos"], "—")
                            self.assertEqual(panel.metrics["Relíquias salvas"], "0")
            finally:
                scroll.close()
                scroll.deleteLater()

    def test_account_profile_long_name_and_signature_fit_narrow_page(self):
        from PySide6.QtWidgets import QMainWindow
        from app.ui.main_window import MainWindow
        from app.ui.image_loader import ImageLoader
        from app.section_loading import SectionLoadController
        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window.image_loader = ImageLoader(window)
        window.section_loading = SectionLoadController(window)
        window.section_statuses = {}
        scroll = window._build_account_page()
        window.account_profile_name.setText("Nome de perfil muito longo " * 4)
        window.account_profile_signature.setText("Assinatura pública com várias palavras " * 8)
        scroll.setStyleSheet(experience_stylesheet(ExperiencePreferences()))
        scroll.show()
        try:
            for width in (600, 900, 1300):
                scroll.resize(width, 620)
                for _ in range(4):
                    self.app.processEvents()
                self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
                for label in (window.account_profile_name, window.account_profile_signature):
                    self.assertGreaterEqual(label.height(), label.heightForWidth(label.width()))
        finally:
            scroll.close()
            scroll.deleteLater()
            window.deleteLater()

    def test_profile_isolation_summary_totals_and_guarantee(self):
        with tempfile.TemporaryDirectory() as directory:
            warps = WarpDatabase(Path(directory) / "warps.db")
            relics = RelicDatabase(Path(directory) / "relics.db")
            user = AuthUser(7, "test", "", "600000001")
            records = [WarpRecord(str(i), user.game_uid, "11", "1003", "Himeko", "Character", rank, f"2026-01-01 00:00:0{i}") for i, rank in ((1, 5), (2, 3))]
            warps.add_records(records, user.id)
            warps.add_records(records, 8)
            panel = AccountDashboard()
            engine = BenchmarkEngine()
            panel.refresh(user, None, warps, relics, engine)
            self.assertEqual(panel.metrics["Tiros registrados"], "2")
            self.assertIn("Pity 1/90", panel.banner_values["11"])
            self.assertIn("Garantido", panel.banner_values["11"])
            self.assertIn("Sem histórico", panel.banner_values["21"])
            panel.resize(1000, 700)
            panel.show()
            self.app.processEvents()
            self.assertEqual(panel._metric_columns, 4)
            self.assertEqual(panel._section_columns, 2)
            self.assertEqual(len(panel._metric_cards), 4)
            self.assertEqual(len(panel._section_frames), 3)
            panel.resize(700, 700)
            self.app.processEvents()
            self.assertEqual(panel._metric_columns, 2)
            self.assertEqual(panel._section_columns, 1)
            warps.upsert_summary(WarpSummary(user.game_uid, "11", 100, 3, 10, 7, 2, "", "", 0, ""), user.id)
            panel.refresh(user, None, warps, relics, engine)
            self.assertEqual(panel.metrics["Tiros registrados"], "100")
            self.assertEqual(panel.metrics["Resultados 5★"], "3")
            self.assertIn("Garantia desconhecida", panel.banner_values["11"])
            panel.refresh(AuthUser(9, "other", "", user.game_uid), None, warps, relics, engine)
            self.assertEqual(panel.metrics["Tiros registrados"], "—")
            panel.refresh(None, None, warps, relics, engine)
            self.assertEqual(panel.body.count(), 1)
            self.assertIn("Entre no seu perfil", panel.body.itemAt(0).widget().text())
            panel.close()
