import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget

from app.ui.build_history import BuildHistoryBar, BuildMetadataDialog
from app.ui.main_window import MainWindow


class BuildHistoryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_actions_reflow_without_stretching_across_wide_page(self) -> None:
        host = QWidget()
        layout = QVBoxLayout(host)
        bar = BuildHistoryBar()
        layout.addWidget(bar)
        layout.addStretch(1)
        host.show()
        for width, columns in ((320, 2), (600, 3), (1600, 6), (320, 2)):
            host.resize(width, 700)
            self.app.processEvents()
            self.assertEqual(bar._columns, columns)
            self.assertLessEqual(bar.minimumSizeHint().width(), width)
            self.assertLess(bar.save_button.width(), 120)
            self.assertLess(bar.height(), 200)
        host.close()

    def test_metadata_dialog_uses_themed_card_and_preserves_input(self) -> None:
        dialog = BuildMetadataDialog()
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(dialog.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertIsNotNone(dialog.findChild(QFrame, "buildMetadataCard"))
        dialog.name_edit.setText("Quebra")
        dialog.note_edit.setPlainText("Cone alternativo")
        dialog.favorite_check.setChecked(True)
        self.assertEqual(dialog.metadata(), {
            "name": "Quebra", "note": "Cone alternativo", "favorite": True,
        })

    def test_favorite_action_refreshes_without_using_save_state(self) -> None:
        updates = []
        statuses = []
        snapshot = SimpleNamespace(name="Teste", note="Nota")
        host = SimpleNamespace(
            _selected_saved_build=lambda _snapshot_id: snapshot,
            _history_context=lambda: (7, "1", "a"),
            build_history_database=SimpleNamespace(
                update_metadata=lambda *args, **kwargs: updates.append((args, kwargs))
            ),
            _refresh_build_history=lambda: updates.append("refreshed"),
            set_status=lambda message, kind: statuses.append((message, kind)),
        )
        MainWindow.set_saved_build_favorite(host, 4, True)
        self.assertEqual(updates[0], ((7, 4), {
            "name": "Teste", "note": "Nota", "favorite": True,
        }))
        self.assertEqual(updates[1], "refreshed")
        self.assertEqual(statuses[-1][1], "success")


if __name__ == "__main__":
    unittest.main()
