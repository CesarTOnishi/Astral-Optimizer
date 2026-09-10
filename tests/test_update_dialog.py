import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from app.ui.update_dialog import UpdateAvailableDialog, UpdateReadyDialog
from app.updater import ReleaseInfo


class UpdateDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_automatic_update_warns_not_to_reopen_application(self) -> None:
        release = ReleaseInfo(
            version="1.2.1",
            tag="v1.2.1",
            title="Astral Optimizer 1.2.1",
            notes="Correções.",
            page_url="https://example.invalid/release",
            download_url="https://example.invalid/app.zip",
        )
        dialog = UpdateAvailableDialog(release, True)
        text = " ".join(
            label.text() for label in dialog.findChildren(QLabel)
        )
        self.assertIn("Não abra o aplicativo manualmente", text)
        self.assertIn("iniciado novamente de forma automática", text)

    def test_ready_dialog_repeats_warning_before_closing(self) -> None:
        dialog = UpdateReadyDialog("1.2.1")
        text = " ".join(
            label.text() for label in dialog.findChildren(QLabel)
        )
        self.assertIn("NÃO ABRA O APLICATIVO MANUALMENTE", text)
        self.assertIn("abrirá sozinho", text)


if __name__ == "__main__":
    unittest.main()
