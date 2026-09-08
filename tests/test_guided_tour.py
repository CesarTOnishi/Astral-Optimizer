import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from app.ui.experience import GuidedTourOverlay, TourStep


class GuidedTourOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_moves_between_anchored_steps_and_finishes(self) -> None:
        parent = QWidget()
        parent.resize(900, 600)
        first = QPushButton("Primeiro", parent)
        first.setGeometry(30, 60, 130, 40)
        second = QPushButton("Segundo", parent)
        second.setGeometry(720, 490, 130, 40)
        parent.show()

        overlay = GuidedTourOverlay(
            parent,
            (
                TourStep("Introdução", "Primeira explicação", lambda: first),
                TourStep("Continuação", "Segunda explicação", lambda: second),
            ),
        )
        completed: list[bool] = []
        overlay.finished.connect(lambda: completed.append(True))
        overlay.start()
        self.app.processEvents()

        self.assertEqual(overlay.counter.text(), "ETAPA 1 DE 2")
        self.assertTrue(overlay.target_rect.isValid())
        self.assertTrue(overlay.balloon.isVisible())
        self.assertFalse(overlay.balloon.geometry().intersects(overlay.target_rect))

        overlay.move_step(1)
        self.app.processEvents()
        self.assertEqual(overlay.index, 1)
        self.assertEqual(overlay.next.text(), "Concluir")
        self.assertTrue(overlay.target_rect.contains(second.geometry().center()))
        self.assertFalse(overlay.balloon.geometry().intersects(overlay.target_rect))

        overlay.move_step(1)
        self.app.processEvents()
        self.assertEqual(completed, [True])
        parent.close()


if __name__ == "__main__":
    unittest.main()
