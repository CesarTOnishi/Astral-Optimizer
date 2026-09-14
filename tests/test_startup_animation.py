import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QAbstractAnimation
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from app.config import APP_ICON_PNG
from app.ui.loading import StartupSplash


class StartupAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.previous = self.app.property("astralReduceMotion")
        self.app.setProperty("astralReduceMotion", False)
        self.splash = StartupSplash(APP_ICON_PNG)
        self.window = QWidget()

    def tearDown(self):
        self.splash.close()
        self.window.close()
        self.splash.deleteLater()
        self.window.deleteLater()
        self.app.setProperty("astralReduceMotion", self.previous)

    def test_latest_progress_wins_without_going_backwards(self):
        self.splash.show_animated()
        self.splash.set_stage("Loading", 42)
        self.splash.set_stage("Account", 68)
        self.splash.set_stage("Late message", 20)
        QTest.qWait(350)
        self.assertEqual(self.splash.progress.value(), 68)
        self.assertEqual(self.splash.percentage.text(), "68%")
        self.assertEqual(self.splash.size().width(), 600)

    def test_transition_can_interrupt_entry_and_only_runs_once(self):
        self.splash.show_animated()
        self.splash.transition_to(self.window)
        transition = self.splash._transition
        self.splash.transition_to(self.window)
        self.assertIs(self.splash._transition, transition)
        QTest.qWait(420)
        self.assertFalse(self.splash.isVisible())
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.windowOpacity(), 1.0)
        self.assertEqual(self.splash.progress.value(), 100)
        self.assertEqual(self.splash.pulse.state(), QAbstractAnimation.State.Stopped)

    def test_reduced_motion_is_static_and_opens_immediately(self):
        self.app.setProperty("astralReduceMotion", True)
        self.splash.show_animated()
        self.splash.set_stage("Ready", 92)
        self.assertEqual(self.splash.progress.value(), 92)
        self.assertEqual(self.splash.pulse.state(), QAbstractAnimation.State.Stopped)
        self.splash.transition_to(self.window)
        self.assertFalse(self.splash.isVisible())
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.windowOpacity(), 1.0)
