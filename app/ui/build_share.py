from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication

from app.benchmark.models import BenchmarkResult, RelicRating
from app.models import CharacterSummary, RelicSummary
from app.ui.widgets import FRIBBELS_ASSETS


CARD_SIZE = (1200, 675)


def _font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    application = QApplication.instance()
    family = application.font().family() if application is not None else "Segoe UI"
    font = QFont(family)
    font.setPixelSize(size)
    font.setWeight(weight)
    return font


def _panel(
    painter: QPainter,
    rect: QRectF,
    start: str,
    end: str,
    *,
    radius: float = 14,
    border: str = "#354b70",
) -> None:
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0, QColor(start))
    gradient.setColorAt(1, QColor(end))
    painter.setBrush(gradient)
    painter.setPen(QPen(QColor(border), 1.2))
    painter.drawRoundedRect(rect, radius, radius)


def _cover(painter: QPainter, pixmap: QPixmap, rect: QRectF, radius: float = 12) -> None:
    if pixmap.isNull():
        return
    target_ratio = rect.width() / rect.height()
    source_ratio = pixmap.width() / max(1, pixmap.height())
    if source_ratio > target_ratio:
        source_height = float(pixmap.height())
        source_width = source_height * target_ratio
        source = QRectF((pixmap.width() - source_width) / 2, 0, source_width, source_height)
    else:
        source_width = float(pixmap.width())
        source_height = source_width / target_ratio
        source = QRectF(0, (pixmap.height() - source_height) / 2, source_width, source_height)
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    painter.save()
    painter.setClipPath(path)
    painter.drawPixmap(rect, pixmap, source)
    painter.restore()


def _text(
    painter: QPainter,
    rect: QRectF,
    value: str,
    size: int,
    color: str = "#edf4ff",
    *,
    bold: bool = False,
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
) -> None:
    painter.setFont(_font(size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    painter.setPen(QColor(color))
    painter.drawText(rect, int(alignment), value)


def _score_color(grade: str) -> str:
    normalized = grade.casefold()
    if "wtf" in normalized or "aeon" in normalized:
        return "#ff8dc9"
    if normalized.startswith("sss"):
        return "#f7bb72"
    if normalized.startswith("ss"):
        return "#77dffc"
    if normalized.startswith("s"):
        return "#8ee6ad"
    return "#c5cde0"


def render_build_share_card(
    character: CharacterSummary,
    result: BenchmarkResult,
    uid: str,
    artwork: QPixmap,
    cone_art: QPixmap,
    stats: list[dict[str, Any]],
    relics: list[tuple[RelicSummary, RelicRating, QPixmap]],
    *,
    custom_team: bool,
) -> QPixmap:
    """Renderiza um cartão 16:9 pronto para compartilhar no Discord."""
    canvas = QPixmap(*CARD_SIZE)
    canvas.fill(QColor("#070c17"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    background = QLinearGradient(0, 0, CARD_SIZE[0], CARD_SIZE[1])
    background.setColorAt(0, QColor("#091321"))
    background.setColorAt(0.55, QColor("#111831"))
    background.setColorAt(1, QColor("#29183b"))
    painter.fillRect(canvas.rect(), background)
    painter.setPen(QPen(QColor("#50698e"), 2))
    painter.drawRoundedRect(QRectF(8, 8, 1184, 659), 20, 20)

    art_rect = QRectF(24, 24, 370, 627)
    _panel(painter, art_rect, "#443b68", "#20243f", border="#75638d")
    _cover(painter, artwork, art_rect, 14)
    overlay = QLinearGradient(0, art_rect.top() + 360, 0, art_rect.bottom())
    overlay.setColorAt(0, QColor(7, 12, 23, 0))
    overlay.setColorAt(0.55, QColor(7, 12, 23, 160))
    overlay.setColorAt(1, QColor(7, 12, 23, 240))
    painter.setBrush(overlay)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(art_rect, 14, 14)
    _text(painter, QRectF(44, 493, 330, 45), character.name, 29, bold=True)
    _text(
        painter, QRectF(44, 532, 330, 25),
        f"Nível {character.level}  ·  E{character.eidolon}  ·  {character.element}  ·  {character.path}",
        13, "#bcd0e9",
    )
    _text(painter, QRectF(44, 557, 330, 22), f"UID {uid}", 12, "#80cfee")

    cone_rect = QRectF(40, 586, 338, 51)
    painter.setBrush(QColor(10, 18, 33, 220))
    painter.setPen(QPen(QColor("#435d7f"), 1))
    painter.drawRoundedRect(cone_rect, 9, 9)
    if not cone_art.isNull():
        _cover(painter, cone_art, QRectF(44, 590, 66, 43), 6)
    _text(painter, QRectF(119, 588, 247, 21), "CONE DE LUZ", 9, "#8ca6c6", bold=True)
    _text(
        painter, QRectF(119, 606, 247, 26),
        f"{character.light_cone}  ·  S{character.light_cone_rank}",
        12, "#ffffff", bold=True,
    )

    info_rect = QRectF(410, 24, 306, 627)
    _panel(painter, info_rect, "#101c31", "#211b3c")
    _text(painter, QRectF(430, 39, 266, 22), "ASTRAL OPTIMIZER", 11, "#83ddfa", bold=True)
    _text(painter, QRectF(430, 61, 266, 24), "BUILD ATUAL", 17, bold=True)

    benchmark_rect = QRectF(428, 98, 270, 103)
    _panel(painter, benchmark_rect, "#25264e", "#4a2d60", radius=11, border="#77648b")
    _text(painter, QRectF(444, 108, 238, 20), "DPS BENCHMARK", 10, "#cfd9ef", bold=True)
    _text(painter, QRectF(444, 132, 152, 43), f"{result.score:.1f}%", 30, "#ffca78", bold=True)
    _text(
        painter, QRectF(590, 136, 92, 35), result.grade, 22,
        _score_color(result.grade), bold=True, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    _text(
        painter, QRectF(444, 174, 238, 18),
        "Time customizado" if custom_team else "Time padrão",
        10, "#a8b8d1",
    )

    _text(painter, QRectF(430, 215, 266, 24), "ATRIBUTOS", 12, "#dce7f7", bold=True)
    y = 243.0
    for stat in stats[:10]:
        _text(painter, QRectF(434, y, 163, 23), str(stat.get("name", "")), 11, "#c3cde0")
        _text(
            painter, QRectF(594, y, 100, 23), str(stat.get("formatted", "—")),
            11, "#ffffff", bold=True,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        painter.setPen(QPen(QColor(255, 255, 255, 24), 1))
        painter.drawLine(434, int(y + 23), 694, int(y + 23))
        y += 27

    _text(painter, QRectF(430, 522, 266, 22), "TIME DO BENCHMARK", 11, "#dce7f7", bold=True)
    team_ids = list(result.team_character_ids)
    for index in range(3):
        x = 446 + index * 83
        icon = QPixmap()
        if index < len(team_ids):
            icon = QPixmap(str(FRIBBELS_ASSETS / "icon" / "avatar" / f"{team_ids[index]}.webp"))
        painter.setBrush(QColor("#15253e"))
        painter.setPen(QPen(QColor("#426489"), 1))
        painter.drawEllipse(QRectF(x, 553, 54, 54))
        if not icon.isNull():
            path = QPainterPath()
            path.addEllipse(QRectF(x + 2, 555, 50, 50))
            painter.save()
            painter.setClipPath(path)
            _cover(painter, icon, QRectF(x + 2, 555, 50, 50), 25)
            painter.restore()
    _text(
        painter, QRectF(430, 615, 266, 20), result.team_name, 9, "#91a8c5",
        alignment=Qt.AlignmentFlag.AlignCenter,
    )

    relic_panel = QRectF(732, 24, 444, 627)
    _panel(painter, relic_panel, "#151d38", "#292044")
    _text(painter, QRectF(750, 39, 270, 27), "RELÍQUIAS EQUIPADAS", 16, bold=True)
    _text(
        painter, QRectF(1082, 40, 72, 25), f"{len(relics)}/6", 11, "#91e5ff", bold=True,
        alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    for index, (relic, rating, icon) in enumerate(relics[:6]):
        column = index % 2
        row = index // 2
        x = 750 + column * 205
        y = 78 + row * 183
        rect = QRectF(x, y, 194, 171)
        _panel(painter, rect, "#35365f", "#673b68", radius=10, border="#71678d")
        if not icon.isNull():
            _cover(painter, icon, QRectF(x + 10, y + 10, 46, 46), 8)
        _text(painter, QRectF(x + 64, y + 9, 91, 19), relic.slot.upper(), 9, bold=True)
        _text(
            painter, QRectF(x + 155, y + 9, 30, 19), f"+{relic.level}", 9,
            "#ffd77e", bold=True, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        _text(painter, QRectF(x + 64, y + 27, 121, 28), relic.set_name, 8, "#cbd1e4")
        _text(painter, QRectF(x + 10, y + 60, 105, 20), relic.main_stat.name, 10, "#ffffff", bold=True)
        _text(
            painter, QRectF(x + 112, y + 60, 72, 20), relic.main_stat.formatted_value,
            10, "#ffd1ef", bold=True,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        sub_y = y + 83
        for substat in relic.sub_stats[:4]:
            _text(painter, QRectF(x + 10, sub_y, 115, 15), substat.name, 7, "#d7dceb")
            _text(
                painter, QRectF(x + 124, sub_y, 60, 15), substat.formatted_value,
                7, "#ffffff", bold=True,
                alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
            sub_y += 15
        _text(painter, QRectF(x + 10, y + 147, 90, 17), "PONTUAÇÃO", 7, "#aebbd1", bold=True)
        _text(
            painter, QRectF(x + 99, y + 145, 85, 20), f"{rating.score:.1f} · {rating.grade}",
            9, _score_color(rating.grade), bold=True,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

    painter.end()
    return canvas
