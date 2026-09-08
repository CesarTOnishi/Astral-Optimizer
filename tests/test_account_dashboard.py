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
from app.warp.database import WarpDatabase
from app.warp.models import WarpRecord, WarpSummary


class AccountDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

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
