import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QVariantAnimation
from PySide6.QtWidgets import QApplication, QTabBar, QToolButton

from app.config import APP_STYLESHEET
from app.ui.uid_tabs import UidTabsWidget


class UidTabsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(APP_STYLESHEET)

    def setUp(self) -> None:
        self.widget = UidTabsWidget()
        for uid, title in (
            ("601647391", "Fulupetas"),
            ("602000001", "ItiroShin"),
            ("603000002", "Nome de personagem bastante comprido para testar a aba"),
        ):
            self.widget.add_or_update(uid, title)
        self.widget.resize(720, 78)
        self.widget.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.widget.close()
        self.app.setProperty("astralReduceMotion", None)

    def test_selection_animates_and_keeps_uid_navigation(self) -> None:
        selected = []
        self.widget.selected.connect(selected.append)
        self.assertTrue(self.widget.set_current_uid("603000002"))
        self.assertEqual(selected, ["603000002"])
        self.assertEqual(self.widget.current_uid, "603000002")
        self.assertEqual(
            self.widget.tabs._indicator_animation.state(),
            QVariantAnimation.State.Running,
        )
        self.widget.set_current_uid("603000002", emit=False)
        self.assertEqual(
            self.widget.tabs._indicator_animation.state(),
            QVariantAnimation.State.Running,
        )
        self.widget.tabs._indicator_animation.setCurrentTime(280)
        self.assertEqual(self.widget.tabs._indicator, self.widget.tabs._indicator_target())

    def test_selection_line_continues_through_layout_resize(self) -> None:
        start = self.widget.tabs._indicator
        self.widget.selected.connect(
            lambda uid: self.widget.set_current_uid(uid, emit=False)
        )
        self.widget.tabs.setCurrentIndex(2)
        self.assertEqual(self.widget.tabs._indicator_animation.state(), QVariantAnimation.State.Running)
        self.assertEqual(self.widget.tabs._indicator, start)
        self.widget.tabs._indicator_animation.setCurrentTime(90)
        middle = self.widget.tabs._indicator
        self.widget.resize(850, 78)
        self.app.processEvents()
        self.assertEqual(self.widget.tabs._indicator_animation.state(), QVariantAnimation.State.Running)
        self.assertLess(abs(self.widget.tabs._indicator.x() - middle.x()), 2)
        target = self.widget.tabs._indicator_target()
        self.assertGreater(middle.x(), start.x())
        self.assertLess(middle.x(), target.x())
        self.widget.tabs._indicator_animation.setCurrentTime(
            self.widget.tabs._indicator_animation.duration()
        )
        self.assertEqual(self.widget.tabs._indicator, target)

    def test_reduced_motion_and_silent_selection_snap_indicator(self) -> None:
        self.app.setProperty("astralReduceMotion", True)
        selected = []
        self.widget.selected.connect(selected.append)
        self.assertTrue(self.widget.set_current_uid("602000001"))
        self.assertEqual(self.widget.tabs._indicator_animation.state(), QVariantAnimation.State.Stopped)
        self.assertEqual(self.widget.tabs._indicator, self.widget.tabs._indicator_target())

        self.assertTrue(self.widget.set_current_uid("603000002", emit=False))
        self.assertEqual(selected, ["602000001"])
        self.assertEqual(self.widget.tabs._indicator, self.widget.tabs._indicator_target())
        self.widget.set_session_status(loading=True)
        self.assertEqual(self.widget._status_pulse.state(), QVariantAnimation.State.Stopped)

    def test_resize_and_status_keep_controls_visible(self) -> None:
        self.widget.resize(370, 78)
        self.app.processEvents()
        self.assertLessEqual(self.widget.refresh_button.geometry().right(), self.widget.width())
        self.assertEqual(self.widget.tabs._indicator, self.widget.tabs._indicator_target())
        self.widget.set_session_status(loading=True)
        self.assertEqual(self.widget.status_dot.property("state"), "loading")
        self.assertFalse(self.widget.refresh_button.isEnabled())
        self.assertEqual(self.widget._status_pulse.state(), QVariantAnimation.State.Running)
        self.widget.set_session_status(error="offline", updated_at="2026-09-24T10:00:00+00:00")
        self.assertEqual(self.widget.status_dot.property("state"), "error")
        self.assertEqual(self.widget._status_pulse.state(), QVariantAnimation.State.Stopped)

    def test_close_button_uses_uid_after_reorder(self) -> None:
        closed = []
        self.widget.close_requested.connect(closed.append)
        self.widget.tabs.moveTab(0, 2)
        index = self.widget.tabs.index_for_uid("601647391")
        slot = self.widget.tabs.tabButton(index, QTabBar.ButtonPosition.RightSide)
        button = slot.findChild(QToolButton)
        button_right = button.mapTo(self.widget.tabs, button.rect().topRight()).x()
        self.assertLessEqual(button_right, self.widget.tabs.tabRect(index).right() - 5)
        button.click()
        self.assertEqual(closed, ["601647391"])


if __name__ == "__main__":
    unittest.main()
