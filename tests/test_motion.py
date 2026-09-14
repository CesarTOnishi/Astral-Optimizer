import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from app.ui.motion import AnimatedDialog, AnimatedProgressBar, AnimatedStack, animate_width, install_motion
from app.ui.widgets import AvatarLabel
from PySide6.QtGui import QPixmap


class MotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        install_motion()

    def setUp(self):
        self.previous = self.app.property("astralReduceMotion")
        self.app.setProperty("astralReduceMotion", False)
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()
        self.app.setProperty("astralReduceMotion", self.previous)
        self.app.processEvents()

    def show(self, widget):
        self.widgets.append(widget)
        widget.resize(360, 240)
        widget.show()
        self.app.processEvents()
        return widget

    def test_navigation_is_immediate_and_latest_click_wins(self):
        stack = AnimatedStack()
        for text in ("A", "B", "C"):
            stack.addWidget(QLabel(text))
        self.show(stack)
        stack.setCurrentIndex(1)
        stack.setCurrentWidget(stack.widget(2))
        self.assertEqual(stack.currentIndex(), 2)
        self.assertIsNotNone(stack._transition)
        QTest.qWait(260)
        self.assertIsNone(stack._transition)
        stack.setCurrentIndex(0)
        stack.resize(400, 280)
        self.assertIsNone(stack._transition)

    def test_reduce_motion_finishes_active_transitions_and_width(self):
        stack = AnimatedStack()
        stack.addWidget(QLabel("A"))
        stack.addWidget(QLabel("B"))
        self.show(stack)
        sidebar = self.show(QWidget())
        sidebar.setFixedWidth(230)
        animate_width(sidebar, 62)
        stack.setCurrentIndex(1)
        self.app.setProperty("astralReduceMotion", True)
        self.assertIsNone(stack._transition)
        self.assertEqual(sidebar.width(), 62)
        animate_width(sidebar, 230)
        stack.setCurrentIndex(0)
        self.assertEqual(sidebar.width(), 230)
        self.assertIsNone(stack._transition)

    def test_progress_keeps_real_value_and_signal_immediate(self):
        bar = self.show(AnimatedProgressBar())
        values = []
        bar.valueChanged.connect(values.append)
        bar.setValue(20)
        bar.setValue(80)
        self.assertEqual(bar.value(), 80)
        self.assertEqual(values, [20, 80])
        QTest.qWait(280)
        self.assertEqual(bar._painted_value, 80)

    def test_modal_finishes_once_and_clears_dim_after_repeated_accept(self):
        owner = self.show(QWidget())
        dialog = AnimatedDialog(owner)
        dialog.setModal(True)
        self.show(dialog)
        results = []
        dialog.finished.connect(results.append)
        dialog.accept()
        dialog.accept()
        QTest.qWait(200)
        self.assertEqual(results, [1])
        self.assertFalse(dialog.isVisible())
        self.assertIsNone(dialog._astral_dim)
        self.assertEqual(dialog.windowOpacity(), 1.0)
        self.app.setProperty("astralReduceMotion", True)
        dialog.show()
        dialog.reject()
        self.assertEqual(results, [1, 0])
        self.assertFalse(dialog.isVisible())

    def test_feedback_does_not_intercept_click_and_image_clear_removes_overlay(self):
        button = self.show(QPushButton("Test"))
        clicks = []
        button.clicked.connect(lambda: clicks.append(True))
        QTest.mouseMove(button, button.rect().center())
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.assertEqual(clicks, [True])
        avatar = self.show(AvatarLabel(54))
        pixmap = QPixmap(54, 54)
        pixmap.fill(Qt.GlobalColor.blue)
        avatar.set_image(pixmap)
        avatar.clear_image()
        self.assertTrue(avatar.pixmap().isNull())
        self.assertFalse(avatar._astral_image_layer.isVisible())

    def test_leaving_button_removes_hover_layer(self):
        button = self.show(QPushButton("Hover"))
        self.app.sendEvent(button, QEvent(QEvent.Type.Enter))
        QTest.qWait(130)
        layer = button._astral_feedback
        self.assertTrue(layer.isVisible())
        self.app.sendEvent(button, QEvent(QEvent.Type.Leave))
        QTest.qWait(180)
        self.assertFalse(layer.isVisible())
        self.assertEqual(layer.amount, 0.0)
