import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.warp.database import WarpDatabase
from app.warp.models import WarpRecord
from app.ui.warp_panel import WarpPanel


def record(number, rank=3, banner="a", item="20001"):
    return WarpRecord(
        str(number), "600000001", "11", item, f"Item {item}",
        "Character" if rank == 5 else "Light Cone", rank,
        f"2026-01-01 00:{number:02d}:00", "Mesmo título", "", banner,
    )


class EditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_migration_reimport_and_backup_keep_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "warps.db"
            database = WarpDatabase(path)
            old = replace(record(1), banner_id="")
            database.add_records([old], 7)
            with database.connect() as connection:
                connection.execute("ALTER TABLE warps DROP COLUMN banner_id")
            connection.close()
            database = WarpDatabase(path)
            self.assertEqual(database.records(old.uid, 7)[0].banner_id, "")
            self.assertEqual(database.add_records([record(1)], 7), 0)
            database.add_records([old], 7)
            self.assertEqual(database.records(old.uid, 7)[0].banner_id, "a")
            target = WarpDatabase(Path(directory) / "restored.db")
            target.restore_owner(database.export_owner(7), 8)
            self.assertEqual(target.records(old.uid, 8)[0].banner_id, "a")
            self.assertEqual(target.records(old.uid, 7), [])

    def test_filter_preserves_pity_guarantee_and_separates_same_title(self):
        with tempfile.TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            with patch("app.ui.warp_panel.WarpDatabase", return_value=database):
                panel = WarpPanel()
            records = [record(1, 5, item="1003"), record(2), record(3)]
            records += [record(4, 5, "b", "1409"), record(5, 5, "b", "1409")]
            records += [record(6, banner="b"), record(7, banner="")]
            panel._render_records(records)
            self.assertEqual(panel.edition_selector.count(), 3)
            self.assertEqual(panel.edition_selector.itemData(0), "__all__")
            self.assertIn("Todos os saltos", panel.edition_selector.itemText(0))
            panel.edition_selector.setCurrentIndex(panel.edition_selector.findData("b"))
            self.assertEqual(panel.total_card.value.text(), "3")
            self.assertEqual(panel.table.rowCount(), 2)
            self.assertEqual(panel.table.item(1, 3).text(), "3")
            self.assertEqual(panel.table.item(1, 4).toolTip(), "GARANTIDO")
            self.assertEqual(panel.character_card.value.text(), "2/90")
            self.assertIn("3 tiros", panel.edition_selector.currentText())
            self.assertNotIn("Item 1409", panel.edition_selector.currentText())
            self.assertEqual(panel.edition_selector.findData("unknown"), -1)
            panel._select_banner("12")
            self.assertEqual(panel.edition_selector.currentData(), "__all__")
            panel.close()

    def test_lists_only_cone_editions_that_contain_a_five_star(self):
        with tempfile.TemporaryDirectory() as directory:
            database = WarpDatabase(Path(directory) / "warps.db")
            with patch("app.ui.warp_panel.WarpDatabase", return_value=database):
                panel = WarpPanel()
            panel._select_banner("12")
            records = [
                replace(record(1, banner="cone-a"), gacha_type="12"),
                replace(record(2, 5, "cone-a", "23000"), gacha_type="12", item_type="Light Cone"),
                replace(record(3, banner="cone-b"), gacha_type="12"),
                replace(record(4, 4, "cone-b"), gacha_type="12"),
            ]
            panel._render_records(records)
            self.assertEqual(panel.edition_selector.count(), 2)
            self.assertEqual(panel.edition_selector.findData("cone-b"), -1)
            panel.edition_selector.setCurrentIndex(
                panel.edition_selector.findData("cone-a")
            )
            self.assertEqual(panel.total_card.value.text(), "2")
            self.assertEqual(panel.table.rowCount(), 1)
            self.assertEqual(panel.table.item(0, 0).text(), "Item 23000")
            self.assertEqual(panel.table.item(0, 5).text(), "★★★★★")
            panel.close()

    def test_api_banner_id_is_optional(self):
        self.assertEqual(WarpRecord.from_api({"gacha_id": "2078"}).banner_id, "2078")
        self.assertEqual(WarpRecord.from_api({}).banner_id, "")


if __name__ == "__main__":
    unittest.main()
