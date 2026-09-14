"""Original stroke icons, rendered from SVG at the requested resolution."""
from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from app.preferences import themed_color


PATHS = {
    "home": '<path d="m3 10 9-7 9 7v10H14v-6h-4v6H3z"/>',
    "build": '<path d="m12 3 9 5-9 5-9-5zM3 12l9 5 9-5M3 16l9 5 9-5"/>',
    "profile": '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    "friends": '<circle cx="9" cy="8" r="3"/><path d="M2 21v-3a7 7 0 0 1 14 0v3M16 5a3 3 0 0 1 0 6M18 14a5 5 0 0 1 4 5v2"/>',
    "catalog": '<path d="M12 5v16M3 3c4 0 6 0 9 2 3-2 5-2 9-2v16c-4 0-6 0-9 2-3-2-5-2-9-2z"/>',
    "relic": '<path d="m12 2 9 5v10l-9 5-9-5V7zM12 7l5 5-5 5-5-5z"/>',
    "warp": '<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3z"/>',
    "planner": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18m-14 5 3 3 6-5"/>',
    "rank": '<path d="M7 3h10v6a5 5 0 0 1-10 0zM7 5H3v3a4 4 0 0 0 4 4M17 5h4v3a4 4 0 0 1-4 4M12 14v7M8 21h8"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="m9 3 6 0 1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1z"/>',
    "appearance": '<circle cx="12" cy="12" r="9"/><path d="M12 3v18M12 7h6M12 12h9M12 17h6"/>',
    "privacy": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM9 12l2 2 4-4"/>',
    "backup": '<path d="M7 18H6a4 4 0 0 1-1-8 7 7 0 0 1 14-1 4.5 4.5 0 0 1-1 9h-1M12 21V11m-4 4 4-4 4 4"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v.5"/>',
    "bell": '<path d="M5 10a7 7 0 0 1 14 0v5l2 3H3l2-3zM9 21h6"/>',
    "refresh": '<path d="M20 10a8 8 0 0 0-14-5L3 8m0-5v5h5M4 14a8 8 0 0 0 14 5l3-3m0 5v-5h-5"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "minimize": '<path d="M5 12h14"/>',
    "maximize": '<rect x="5" y="5" width="14" height="14" rx="1"/>',
    "restore": '<path d="M9 7V4h11v11h-3"/><rect x="4" y="9" width="11" height="11" rx="1"/>',
}


class StrokeIcon(QIconEngine):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def clone(self):
        return StrokeIcon(self.name)

    def paint(self, painter, rect, mode, state):
        color = "#61738d" if mode == QIcon.Mode.Disabled else (
            "#89ddf3" if state == QIcon.State.On else "#b5c4d8"
        )
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{themed_color(color)}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS[self.name]}</svg>'
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        renderer.render(painter, QRectF(rect))

    def pixmap(self, size, mode, state):
        result = QPixmap(size)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        self.paint(painter, result.rect(), mode, state)
        painter.end()
        return result


def set_button_icon(button, name, size=18):
    button.setProperty("astralIcon", name)
    button.setIcon(QIcon(StrokeIcon(name)))
    button.setIconSize(QSize(size, size))
