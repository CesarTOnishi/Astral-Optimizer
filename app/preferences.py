from __future__ import annotations

import colorsys
from dataclasses import dataclass
from functools import lru_cache
import re
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QWidget

from app.config import APP_STYLESHEET


THEMES = {
    "astral": "Astral",
    "obsidian": "Obsidiana",
    "aurora": "Aurora",
    "jade": "Jade Estelar",
    "crimson": "Carmesim",
    "contrast": "Alto contraste",
}


@dataclass(frozen=True, slots=True)
class ExperiencePreferences:
    theme: str = "astral"
    reduce_motion: bool = False
    tutorial_completed: bool = False


class ExperienceSettings:
    def __init__(self, settings: QSettings | None = None) -> None:
        self.settings = settings or QSettings("AstralOptimizer", "Experience")

    def load(self) -> ExperiencePreferences:
        theme = str(self.settings.value("appearance/theme", "astral"))
        if theme not in THEMES:
            theme = "astral"
        return ExperiencePreferences(
            theme=theme,
            reduce_motion=self.settings.value(
                "accessibility/reduce_motion", False, type=bool
            ),
            tutorial_completed=self.settings.value(
                "tutorial/completed", False, type=bool
            ),
        )

    def save(self, preferences: ExperiencePreferences) -> None:
        self.settings.setValue("appearance/theme", preferences.theme)
        self.settings.remove("appearance/scale")
        self.settings.setValue(
            "accessibility/reduce_motion", preferences.reduce_motion
        )
        self.settings.sync()

    def complete_tutorial(self) -> None:
        self.settings.setValue("tutorial/completed", True)
        self.settings.sync()


def reduce_motion_enabled() -> bool:
    app = QApplication.instance()
    if app is not None:
        value = app.property("astralReduceMotion")
        if value is not None:
            return bool(value)
    return ExperienceSettings().load().reduce_motion


def motion_duration(duration: int) -> int:
    return 1 if reduce_motion_enabled() else duration


def themed_color(
    value: str, preferences: ExperiencePreferences | None = None
) -> str:
    current = preferences
    if current is None:
        app = QApplication.instance()
        theme = app.property("astralTheme") if app is not None else None
        current = (
            ExperiencePreferences(theme=str(theme))
            if theme in THEMES else ExperienceSettings().load()
        )
    if current.theme == "astral" or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value
    target_hues = {
        "obsidian": (0.61, 0.58),
        "aurora": (0.49, 0.47),
        "jade": (0.40, 0.38),
        "crimson": (0.96, 0.97),
        "contrast": (0.52, 0.52),
    }
    surface_hue, accent_hue = target_hues[current.theme]

    def recolor(source: str) -> str:
        red, green, blue = (
            int(source[index:index + 2], 16) / 255 for index in (1, 3, 5)
        )
        hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
        cool = 0.48 <= hue <= 0.82
        dark_surface = lightness < 0.34 and (cool or saturation < 0.28)
        if current.theme == "obsidian" and dark_surface:
            saturation = min(saturation * 0.16, 0.08)
            hue = surface_hue
        elif dark_surface:
            hue = surface_hue
            saturation = max(0.24, min(0.72, saturation * 0.82))
        elif cool:
            hue = accent_hue
            saturation = min(1.0, max(0.28, saturation))
        else:
            return source
        new_red, new_green, new_blue = colorsys.hls_to_rgb(
            hue, lightness, saturation
        )
        return "#{:02x}{:02x}{:02x}".format(
            round(new_red * 255), round(new_green * 255), round(new_blue * 255)
        )

    return recolor(value)


def experience_stylesheet(preferences: ExperiencePreferences | None = None) -> str:
    current = preferences or ExperienceSettings().load()
    return _theme_stylesheet(current.theme)


@lru_cache(maxsize=len(THEMES))
def _theme_stylesheet(theme: str) -> str:
    current = ExperiencePreferences(theme=theme)
    if current.theme == "astral":
        return APP_STYLESHEET

    stylesheet = re.sub(
        r"#[0-9a-fA-F]{6}",
        lambda match: themed_color(match.group(0), current),
        APP_STYLESHEET,
    )
    if current.theme == "contrast":
        stylesheet += """
QMainWindow, QWidget#appRoot, QWidget#appBody, QWidget#scrollContent {
    background-color: #000000; color: #ffffff;
}
QLabel { color: #ffffff; }
QFrame#sideBar, QFrame#customTitleBar, QFrame#panel,
QFrame#plannerSettingsCard, QFrame#warpAnalyticsPanel {
    background-color: #050505; border: 1px solid #ffffff;
}
QPushButton, QComboBox, QLineEdit, QSpinBox {
    color: #ffffff; background-color: #000000; border: 2px solid #70d8ff;
}
QPushButton:focus, QComboBox:focus, QLineEdit:focus, QSpinBox:focus {
    border-color: #ffff66;
}
"""
    return stylesheet


def apply_experience_preferences(
    app: QApplication | None = None,
    preferences: ExperiencePreferences | None = None,
) -> None:
    target = app or QApplication.instance()
    if target is None:
        return
    current = preferences or ExperienceSettings().load()
    if target.property("astralReduceMotion") != current.reduce_motion:
        target.setProperty("astralReduceMotion", current.reduce_motion)
    # Reducing motion and closing Settings must not repolish the whole app.
    stylesheet = experience_stylesheet(current)
    if target.property("astralAppliedTheme") == current.theme and target.styleSheet() == stylesheet:
        target.setProperty("astralTheme", current.theme)
        return
    target.setProperty("astralTheme", current.theme)
    windows = [window for window in target.topLevelWidgets() if window.updatesEnabled()]
    widgets = target.allWidgets()
    layouts = [layout for widget in widgets if (layout := QWidget.layout(widget)) is not None and layout.isEnabled()]
    controller = getattr(target, "_astral_motion", None)
    if controller is not None:
        target.removeEventFilter(controller)
    target.setProperty("astralApplyingTheme", True)
    try:
        for window in windows:
            window.setUpdatesEnabled(False)
        for layout in layouts:
            layout.setEnabled(False)
        target.setStyleSheet(stylesheet)
        target.setProperty("astralAppliedTheme", current.theme)
    finally:
        for layout in layouts:
            layout.setEnabled(True)
        target.setProperty("astralApplyingTheme", False)
        if controller is not None:
            target.installEventFilter(controller)
        for window in windows:
            window.setUpdatesEnabled(True)
    from app.ui.icons import set_button_icon
    for widget in widgets:
        name = widget.property("astralIcon")
        if name:
            set_button_icon(widget, str(name), widget.iconSize().width())
