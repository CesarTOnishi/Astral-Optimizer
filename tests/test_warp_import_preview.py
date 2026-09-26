import os
from unittest.mock import Mock
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.auth import AuthUser
from app.ui.warp_import_preview import WarpImportPreviewDialog
from app.ui.warp_panel import WarpPanel
from app.warp.database import WarpDatabase
from app.warp.importer import WarpImportBatch
from app.warp.models import WarpSummary
from app.warp.preview import preview_warp_import
from app.warp.starrailstation import StarRailStationImport, import_starrailstation_xlsx
from tests.test_warp import warp


class WarpImportPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_counts_new_existing_source_duplicates_and_rejected(self) -> None:
        uid = "600000001"
        incoming = [warp(1, 3), warp(2, 4), warp(2, 4), warp(3, 5)]
        incoming.append(replace(warp(4, 3), id=""))
        preview = preview_warp_import(
            incoming, {(uid, "1")}, rejected_count=2, duplicate_count=1
        )
        self.assertEqual(
            (preview.new_count, preview.duplicate_count, preview.rejected_count),
            (2, 3, 3),
        )
        self.assertEqual(len(preview.valid_records), 4)
        dialog = WarpImportPreviewDialog(preview, "data_2")
        try:
            self.assertTrue(dialog.add_button.isEnabled())
            self.assertEqual(dialog.add_button.text(), "Adicionar")
            self.assertEqual(dialog.cancel_button.text(), "Cancelar")
        finally:
            dialog.close()

    def test_xlsx_parser_reports_skipped_rows_as_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "history.xlsx"
            path.write_bytes(b"stub")
            reader = Mock()
            reader.sheets = {"Character Event Warp": "sheet.xml"}
            reader.rows.return_value = [
                {},
                {"B": "***", "C": "Cone", "E": "45000", "F": "Banner",
                 "G": "20001,manual,banner,1"},
                {"B": "***", "C": "Inválido", "E": "45001", "G": "incompleto"},
                {},
            ]
            with patch("app.warp.starrailstation._WorkbookReader", return_value=reader):
                result = import_starrailstation_xlsx(path, "600000001")
            self.assertEqual(len(result.records), 1)
            self.assertEqual(result.rejected_count, 1)
            reader.close.assert_called_once()

    def test_cancel_does_not_write_or_emit_import_completed(self) -> None:
        with TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            with patch("app.ui.warp_panel.WarpDatabase", return_value=database):
                panel = WarpPanel()
            panel.set_user(AuthUser(7, "Pessoa", "p@example.com", "600000001"))
            completed: list[int] = []
            panel.import_completed.connect(completed.append)
            summary = WarpSummary(
                uid="600000001", gacha_type="21", total=1,
                five_star_count=1, four_star_count=0,
                five_star_pity=0, four_star_pity=1,
                featured_item_id="1014", featured_item_name="Saber",
                featured_pity=1, featured_item_type="Character",
            )
            try:
                with patch.object(WarpImportPreviewDialog, "exec", return_value=0):
                    panel._import_succeeded(
                        StarRailStationImport("600000001", [warp(1, 3)], [summary], []),
                        "backup.xlsx",
                    )
                self.assertEqual(database.records("600000001", 7), [])
                self.assertEqual(database.summaries("600000001", 7), {})
                self.assertEqual(completed, [])
                self.assertIn("cancelada", panel.status.text())
            finally:
                panel.close()

    def test_confirm_adds_records_and_keeps_duplicate_metadata_updates(self) -> None:
        with TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            database.add_records([warp(1, 3)], 7)
            with patch("app.ui.warp_panel.WarpDatabase", return_value=database):
                panel = WarpPanel()
            panel.set_user(AuthUser(7, "Pessoa", "p@example.com", "600000001"))
            completed: list[int] = []
            panel.import_completed.connect(completed.append)
            incoming = [replace(warp(1, 3), banner_id="a"), warp(2, 4)]
            try:
                with patch.object(WarpImportPreviewDialog, "exec", return_value=1):
                    panel._import_succeeded(WarpImportBatch(incoming), "data_2")
                self.assertEqual(completed, [7])
                self.assertEqual(len(database.records("600000001", 7)), 2)
                self.assertEqual(
                    next(row for row in database.records("600000001", 7) if row.id == "1").banner_id,
                    "a",
                )
            finally:
                panel.close()


if __name__ == "__main__":
    unittest.main()
