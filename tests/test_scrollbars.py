import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QListWidget, QPushButton, QScrollArea, QScrollBar, QTableWidget, QTextEdit

from app.preferences import ExperiencePreferences, apply_experience_preferences
from app.ui.main_window import MainWindow
from app.ui.motion import install_motion
from app.ui.scrollbars import ScrollbarAppearance, enhance_scrollbar


class ScrollbarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        install_motion()

    def setUp(self):
        self.previous_style = self.app.styleSheet()
        self.previous = {key: self.app.property(key) for key in ("astralTheme", "astralAppliedTheme", "astralReduceMotion")}
        apply_experience_preferences(self.app, ExperiencePreferences(reduce_motion=False))
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.setStyleSheet(self.previous_style)
        for key, value in self.previous.items():
            self.app.setProperty(key, value)

    def test_native_bars_are_preserved_in_all_scroll_area_types(self):
        for cls in (QScrollArea, QListWidget, QTableWidget, QTextEdit):
            area = cls()
            self.widgets.append(area)
            before = (area.verticalScrollBar(), area.horizontalScrollBar())
            area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            area.resize(300, 200)
            area.show()
            self.app.processEvents()
            for bar, original in zip((area.verticalScrollBar(), area.horizontalScrollBar()), before):
                self.assertIs(bar, original)
                self.assertTrue(hasattr(bar, "_astral_scrollbar"))
                self.assertFalse(bar.grab().isNull())

    def test_reentrant_install_only_creates_one_controller(self):
        bar = QScrollBar()
        self.widgets.append(bar)
        refresh_colors = ScrollbarAppearance._refresh_colors

        def reentrant_refresh(appearance):
            enhance_scrollbar(bar)
            refresh_colors(appearance)

        with patch.object(ScrollbarAppearance, "_refresh_colors", reentrant_refresh):
            enhance_scrollbar(bar)
        self.assertIsInstance(bar._astral_scrollbar, ScrollbarAppearance)
        self.assertEqual(len(bar.findChildren(ScrollbarAppearance)), 1)

    def test_drag_keyboard_and_reduced_motion_in_both_orientations(self):
        for orientation in (Qt.Orientation.Vertical, Qt.Orientation.Horizontal):
            bar = QScrollBar(orientation)
            self.widgets.append(bar)
            bar.resize(12, 240) if orientation == Qt.Orientation.Vertical else bar.resize(240, 12)
            bar.setRange(0, 100)
            bar.setPageStep(10)
            bar.setValue(40)
            bar.show()
            self.app.processEvents()
            appearance = bar._astral_scrollbar
            center = appearance.handle_rect().center()
            end = bar.rect().center()
            end.setY(bar.height() - 3) if orientation == Qt.Orientation.Vertical else end.setX(bar.width() - 3)
            QTest.mousePress(bar, Qt.MouseButton.LeftButton, pos=center)
            QTest.mouseMove(bar, end)
            QTest.mouseRelease(bar, Qt.MouseButton.LeftButton, pos=end)
            self.assertGreater(bar.value(), 40)
            QTest.keyClick(bar, Qt.Key.Key_Home)
            self.assertEqual(bar.value(), 0)
            QTest.keyClick(bar, Qt.Key.Key_End)
            self.assertEqual(bar.value(), 100)
            self.app.sendEvent(bar, QEvent(QEvent.Type.Enter))
            self.app.setProperty("astralReduceMotion", True)
            self.assertEqual(appearance.activity, 1.0)
            self.app.sendEvent(bar, QEvent(QEvent.Type.Leave))
            self.assertEqual(appearance.activity, 0.0)

    def test_sidebar_toggle_does_not_refresh_account_or_restyle_buttons(self):
        widgets = [QFrame(), QPushButton(), QLabel(), QLabel(), QLabel(), QPushButton()]
        self.widgets.extend(widgets)
        sidebar, toggle, brand, section, source, button = widgets
        fake = SimpleNamespace(
            sidebar_expanded=True, sidebar=sidebar, sidebar_toggle=toggle,
            side_brand=brand, nav_section=section, side_source=source,
            nav_buttons=[(button, "home", "Início")],
            _refresh_auth_sidebar=Mock(side_effect=AssertionError("Data refresh during sidebar toggle")),
            _update_sidebar_profile_layout=Mock(), _render_sync_status=Mock(),
        )
        MainWindow.toggle_sidebar(fake)
        self.assertEqual(sidebar.width(), 62)
        self.assertEqual(button.text(), "")
        MainWindow.toggle_sidebar(fake)
        self.assertEqual(sidebar.width(), 230)
        self.assertEqual(button.text(), "Início")
        self.assertEqual(button.styleSheet(), "")
        fake._refresh_auth_sidebar.assert_not_called()

    def test_restored_window_collapses_sidebar_without_overriding_manual_choice(self):
        widgets = [QFrame(), QPushButton(), QLabel(), QLabel(), QLabel(), QPushButton()]
        self.widgets.extend(widgets)
        fake = SimpleNamespace(
            width=lambda: 900,
            sidebar_expanded=True, _sidebar_user_choice=False,
            _sidebar_auto_collapsed=False,
            sidebar=widgets[0], sidebar_toggle=widgets[1],
            side_brand=widgets[2], nav_section=widgets[3], side_source=widgets[4],
            nav_buttons=[(widgets[5], "home", "Início")],
            _update_sidebar_profile_layout=Mock(), _render_sync_status=Mock(),
        )
        fake.toggle_sidebar = lambda: MainWindow.toggle_sidebar(fake)
        MainWindow._fit_sidebar_to_window(fake)
        self.assertFalse(fake.sidebar_expanded)
        self.assertEqual(fake.sidebar.width(), 62)
        self.assertTrue(fake._sidebar_auto_collapsed)
        fake.toggle_sidebar()  # Explicit choice at the same window size.
        MainWindow._fit_sidebar_to_window(fake)
        self.assertTrue(fake.sidebar_expanded)
        fake._sidebar_user_choice = False
        MainWindow._fit_sidebar_to_window(fake)
        fake.width = lambda: 1280
        MainWindow._fit_sidebar_to_window(fake)
        self.assertTrue(fake.sidebar_expanded)
        self.assertEqual(fake.sidebar.width(), 230)
