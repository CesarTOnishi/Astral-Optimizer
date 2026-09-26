import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from app.auth import AuthUser
from app.planner import calculate_planner
from app.ui.planner_panel import PlannerPanel
from app.warp.database import WarpDatabase
from tests.test_warp import warp


class PlannerManualPityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_switching_source_restores_imported_values_and_keeps_manual_plan(self) -> None:
        with TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            uid = "600000001"
            database.add_records([
                warp(1, 5, "1003", "11", uid),
                warp(2, 3, "1001", "11", uid),
                warp(3, 5, "23000", "12", uid),
                warp(4, 3, "1001", "12", uid),
            ], owner_id=7)
            panel = PlannerPanel(database)
            try:
                panel.set_user(AuthUser(7, "Pessoa", "pessoa@example.com", uid))
                self.assertTrue(panel.use_imported_pity.isChecked())
                self.assertEqual(panel.character_pity.text(), "1/90")
                self.assertEqual(panel.cone_pity.text(), "1/80")
                self.assertEqual(panel.character_pity_stack.currentIndex(), 0)
                self.assertIn("histórico importado", panel.pity_source.text())

                with patch(
                    "app.ui.planner_panel.calculate_planner", wraps=calculate_planner
                ) as calculate:
                    panel.use_imported_pity.setChecked(False)
                    panel.character_pity_input.setValue(67)
                    panel.cone_pity_input.setValue(22)
                    panel.character_guarantee_input.setChecked(False)
                    panel.cone_guarantee_input.setChecked(True)
                    panel.refresh()
                    self.assertEqual(panel.character_pity_stack.currentIndex(), 1)
                    self.assertEqual(calculate.call_args.kwargs["character_pity"], 67)
                    self.assertEqual(calculate.call_args.kwargs["light_cone_pity"], 22)
                    self.assertFalse(calculate.call_args.kwargs["character_guaranteed"])
                    self.assertTrue(calculate.call_args.kwargs["light_cone_guaranteed"])
                    self.assertIn("ajuste manual", panel.pity_source.text())

                    database.add_records(
                        [warp(5, 3, "1001", "11", uid)], owner_id=7
                    )
                    panel.refresh()
                    self.assertEqual(panel.character_pity_input.value(), 67)

                    panel.use_imported_pity.setChecked(True)
                    panel.refresh()
                    self.assertEqual(calculate.call_args.kwargs["character_pity"], 2)
                    self.assertEqual(calculate.call_args.kwargs["light_cone_pity"], 1)
                    self.assertTrue(calculate.call_args.kwargs["character_guaranteed"])
                    self.assertTrue(calculate.call_args.kwargs["light_cone_guaranteed"])

                reopened = PlannerPanel(database)
                try:
                    reopened.set_user(AuthUser(7, "Pessoa", "pessoa@example.com", uid))
                    self.assertTrue(reopened.use_imported_pity.isChecked())
                    reopened.use_imported_pity.setChecked(False)
                    self.assertEqual(reopened.character_pity_input.value(), 67)
                    self.assertEqual(reopened.cone_pity_input.value(), 22)
                    self.assertFalse(reopened.character_guarantee_input.isChecked())
                    self.assertTrue(reopened.cone_guarantee_input.isChecked())
                finally:
                    reopened.close()
            finally:
                panel.close()

    def test_manual_values_are_isolated_by_profile_and_uid(self) -> None:
        with TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            panel = PlannerPanel(database)
            try:
                panel.set_user(AuthUser(1, "Um", "um@example.com", "600000001"))
                panel.use_imported_pity.setChecked(False)
                panel.character_pity_input.setValue(41)
                panel.set_user(AuthUser(2, "Dois", "dois@example.com", "600000001"))
                self.assertTrue(panel.use_imported_pity.isChecked())
                panel.set_user(AuthUser(1, "Um", "um@example.com", "600000002"))
                self.assertTrue(panel.use_imported_pity.isChecked())
                panel.set_user(AuthUser(1, "Um", "um@example.com", "600000001"))
                self.assertFalse(panel.use_imported_pity.isChecked())
                self.assertEqual(panel.character_pity_input.value(), 41)
            finally:
                panel.close()

    def test_manual_planning_works_without_imported_history(self) -> None:
        with TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            panel = PlannerPanel(database)
            try:
                panel.set_user(AuthUser(3, "Sem histórico", "sem@example.com", "600000003"))
                self.assertTrue(panel.use_imported_pity.isChecked())
                self.assertIn("sem histórico importado", panel.pity_source.text())
                with patch(
                    "app.ui.planner_panel.calculate_planner", wraps=calculate_planner
                ) as calculate:
                    panel.use_imported_pity.setChecked(False)
                    panel.character_pity_input.setValue(38)
                    panel.character_guarantee_input.setChecked(True)
                    panel.refresh()
                    self.assertEqual(calculate.call_args.kwargs["character_pity"], 38)
                    self.assertTrue(calculate.call_args.kwargs["character_guaranteed"])
                    panel.use_imported_pity.setChecked(True)
                    panel.refresh()
                    self.assertEqual(calculate.call_args.kwargs["character_pity"], 0)
                    self.assertFalse(calculate.call_args.kwargs["character_guaranteed"])
            finally:
                panel.close()

    def test_rapid_resource_edits_trigger_one_recalculation_and_save(self) -> None:
        with TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            panel = PlannerPanel(database)
            try:
                panel.set_user(AuthUser(4, "Teste", "teste@example.com", "600000004"))
                with patch("app.ui.planner_panel.calculate_planner", wraps=calculate_planner) as calculate:
                    panel.jades.setValue(1)
                    panel.jades.setValue(16)
                    panel.jades.setValue(160)
                    self.assertEqual(calculate.call_count, 0)
                    QTest.qWait(240)
                    self.assertEqual(calculate.call_count, 1)
                    self.assertEqual(database.planner_settings(4)["jades"], 160)
                panel.use_imported_pity.setChecked(False)
                self.assertEqual(panel.character_pity_stack.currentIndex(), 1)
                panel.character_pity_input.setValue(54)
                panel.set_user(AuthUser(5, "Outro", "outro@example.com", "600000005"))
                self.assertEqual(
                    database.planner_pity_override(4, "600000004")["character_pity"], 54
                )
            finally:
                panel.close()


if __name__ == "__main__":
    unittest.main()
