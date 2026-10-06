from __future__ import annotations

from collections import Counter
from math import cos, pi, sin
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication

from app.benchmark.models import BenchmarkResult, RelicRating
from app.models import CharacterSummary, RelicSummary
from app.ui.widgets import FRIBBELS_ASSETS, stat_icon_path


CARD_SIZE = (1920, 1080)
SHARE_ICONS = Path(__file__).resolve().parents[1] / "assets" / "build_share_icons"

SKILL_ICON_SUFFIXES = ("Normal", "BP", "Ultra", "Passive")


def bundled_share_icon(url: str) -> QPixmap:
    if not url:
        return QPixmap()
    filename = url.rsplit("/", 1)[-1]
    enka_names = {
        "SkillIcon_1505_Normal.png": "1505_basic_atk.png",
        "SkillIcon_1505_BP.png": "1505_skill.png",
        "SkillIcon_1505_Ultra.png": "1505_ultimate.png",
        "SkillIcon_1505_Passive.png": "1505_talent.png",
        "SkillIcon_1505_Rank1.png": "1505_rank1.png",
        "SkillIcon_1505_Rank2.png": "1505_rank2.png",
        "SkillIcon_1505_Rank4.png": "1505_rank4.png",
        "SkillIcon_1505_Rank6.png": "1505_rank6.png",
    }
    filename = enka_names.get(filename, filename)
    if not filename.startswith("1505_"):
        return QPixmap()
    return QPixmap(str(SHARE_ICONS / filename))


def share_details(character: CharacterSummary, repository: Any = None) -> dict[str, Any]:
    """Extrai apenas dados reais do showcase e do catálogo local para a exportação."""
    raw = character.raw if isinstance(character.raw, dict) else {}
    traces = raw.get("traces") if isinstance(raw.get("traces"), list) else []
    ranks = raw.get("eidolons") if isinstance(raw.get("eidolons"), list) else []
    cone = raw.get("light_cone") if isinstance(raw.get("light_cone"), dict) else {}
    skills: list[dict[str, Any]] = []
    for suffix in SKILL_ICON_SUFFIXES:
        trace = next(
            (item for item in traces if isinstance(item, dict)
             and str(item.get("icon", "")).endswith(f"_{suffix}.png")
             and int(item.get("type", 0) or 0) == 2),
            None,
        )
        if trace is not None:
            skills.append({
                "url": str(trace.get("icon", "")),
                "level": int(trace.get("level", 0) or 0),
                "boosted": bool(trace.get("boosted", False)),
            })
        else:
            skills.append({"url": "", "level": 0, "boosted": False})
    eidolons = [
        str(item.get("icon", "")) if isinstance(item, dict) else ""
        for item in ranks[:6]
    ]
    from app.catalog.repository import CatalogRepository

    repository = repository or CatalogRepository()
    catalog_character = next(
        (item for item in repository.characters()
         if item.id == str(character.avatar_id).removesuffix("b1")),
        None,
    )
    if catalog_character is not None:
        catalog_skills = repository.skills_for(catalog_character)
        catalog_skill_source = repository._data.get("character_skills", {})
        for index, skill_type in enumerate(("Normal", "BPSkill", "Ultra", "Talent")):
            found = next((skill for skill in catalog_skills
                          if isinstance(catalog_skill_source.get(skill.id), dict)
                          and catalog_skill_source[skill.id].get("type") == skill_type), None)
            if found is not None and found.icon:
                skills[index]["url"] = repository.asset_url(found.icon)
        catalog_ranks = repository.ranks_for(catalog_character)
        eidolons.extend("" for _ in range(6 - len(eidolons)))
        for index in range(6):
            rank = next((item for item in catalog_ranks if item.rank == index + 1), None)
            if rank is not None and rank.icon:
                eidolons[index] = repository.asset_url(rank.icon)
    eidolons.extend("" for _ in range(6 - len(eidolons)))
    cone_stats = [
        stat for stat in cone.get("stats", [])
        if isinstance(stat, dict) and stat.get("type") in {
            "BaseHP", "BaseAttack", "BaseDefence",
        }
    ] if isinstance(cone.get("stats"), list) else []
    return {
        "skills": skills,
        "eidolons": eidolons,
        "cone_stats": cone_stats,
        "cone_rarity": int(cone.get("rarity", 0) or 0),
    }


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
    font = _font(size, QFont.Weight.Bold if bold else QFont.Weight.Normal)
    metrics = QFontMetrics(font)
    while metrics.horizontalAdvance(value) > rect.width() and font.pixelSize() > 11:
        font.setPixelSize(font.pixelSize() - 1)
        metrics = QFontMetrics(font)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(
        rect, int(alignment),
        metrics.elidedText(value, Qt.TextElideMode.ElideRight, int(rect.width())),
    )


def _stat_icon(
    painter: QPainter, stat_key: str, rect: QRectF
) -> None:
    icon = QPixmap(str(stat_icon_path(stat_key)))
    if icon.isNull():
        return
    scaled = icon.scaled(
        int(rect.width()),
        int(rect.height()),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = rect.x() + (rect.width() - scaled.width()) / 2
    y = rect.y() + (rect.height() - scaled.height()) / 2
    painter.drawPixmap(int(x), int(y), scaled)


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


def share_uid_text(uid: str, hidden: bool) -> str:
    return "UID •••••••••" if hidden else f"UID {uid}"


def _glass(painter: QPainter, rect: QRectF, alpha: int = 222) -> None:
    painter.setPen(QPen(QColor(218, 204, 166, 76), 1))
    painter.setBrush(QColor(11, 17, 29, alpha))
    painter.drawRoundedRect(rect, 13, 13)


def _dashed_line(painter: QPainter, x: float, top: float, bottom: float) -> None:
    painter.save()
    painter.setPen(QPen(QColor(216, 206, 184, 100), 1, Qt.PenStyle.DashLine))
    painter.drawLine(int(x), int(top), int(x), int(bottom))
    painter.restore()


def _notches(painter: QPainter, x: float, top: float, bottom: float) -> None:
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#222c3d"))
    for y in (top, bottom):
        painter.drawEllipse(QRectF(x - 6, y - 6, 12, 12))
    painter.restore()


def _locked_mark(painter: QPainter, x: float, y: float) -> None:
    painter.save()
    painter.setPen(QPen(QColor("#d6d6d4"), 3))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(QRectF(x + 5, y, 16, 18), 0, 180 * 16)
    painter.setBrush(QColor("#d6d6d4"))
    painter.drawRoundedRect(QRectF(x + 2, y + 10, 22, 17), 2, 2)
    painter.restore()


def _round_badge(
    painter: QPainter, pixmap: QPixmap, x: float, y: float, *,
    active: bool, level: int | None = None, boosted: bool = False,
) -> None:
    diameter = 66
    circle = QRectF(x, y, diameter, diameter)
    painter.save()
    painter.setPen(QPen(QColor("#707686" if active else "#414652"), 2))
    painter.setBrush(QColor(9, 13, 22, 222))
    painter.drawEllipse(circle)
    clip = QPainterPath()
    clip.addEllipse(QRectF(x + 5, y + 5, diameter - 10, diameter - 10))
    painter.setClipPath(clip)
    if not pixmap.isNull():
        _art(painter, pixmap, QRectF(x + 7, y + 7, diameter - 14, diameter - 14))
    if not active:
        painter.fillRect(circle, QColor(2, 4, 9, 164))
    painter.restore()
    if not active:
        _locked_mark(painter, x + 38, y + 40)
    if level is not None:
        label = QRectF(x + 17, y + 59, 32, 21)
        painter.setPen(QPen(QColor("#625d60"), 1))
        painter.setBrush(QColor(25, 25, 30, 228))
        painter.drawRect(label)
        _text(painter, label, f"{level}{'+' if boosted else ''}" if level else "—",
              15, "#f1e7de", bold=True, alignment=Qt.AlignmentFlag.AlignCenter)


def _art(painter: QPainter, pixmap: QPixmap, rect: QRectF) -> None:
    if pixmap.isNull():
        return
    scaled = pixmap.scaled(
        int(rect.width()), int(rect.height()),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    painter.drawPixmap(
        int(rect.center().x() - scaled.width() / 2),
        int(rect.bottom() - scaled.height()), scaled,
    )


def _tinted(pixmap: QPixmap, color: str) -> QPixmap:
    if pixmap.isNull():
        return pixmap
    result = QPixmap(pixmap.size())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(result.rect(), QColor(color))
    painter.end()
    return result


def _stars(painter: QPainter, x: float, y: float, count: int) -> None:
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#e8c983"))
    for index in range(max(0, min(count, 5))):
        center_x = x + index * 19 + 8
        center_y = y + 8
        shape = QPainterPath()
        for point in range(10):
            angle = -pi / 2 + point * pi / 5
            radius = 8 if point % 2 == 0 else 3.6
            px = center_x + cos(angle) * radius
            py = center_y + sin(angle) * radius
            if point == 0:
                shape.moveTo(px, py)
            else:
                shape.lineTo(px, py)
        shape.closeSubpath()
        painter.drawPath(shape)
    painter.restore()


def _compact_stat_name(name: str) -> str:
    compact = name.strip()
    replacements = (
        ("Taxa de Acerto de Efeito", "Acerto Efeito"),
        ("Chance de CRIT", "Taxa CRIT"),
        ("Taxa Crítica", "Taxa CRIT"),
        ("Dano Crítico", "Dano CRIT"),
        ("Taxa de Regeneração de Energia", "Regen. Energia"),
        ("Bônus de Dano ", "Dano "),
        ("Efeito de Quebra", "Efeito Quebra"),
        ("Resistência a Efeito", "RES Efeito"),
    )
    for full, short in replacements:
        compact = compact.replace(full, short)
    return compact


def _relic_card(
    painter: QPainter,
    rect: QRectF,
    entry: tuple[RelicSummary, RelicRating, QPixmap] | None,
) -> None:
    x, y = rect.x(), rect.y()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(11, 14, 23, 237))
    painter.drawRoundedRect(rect, 11, 11)
    painter.setBrush(QColor(23, 25, 35, 239))
    painter.drawRect(QRectF(x + 216, y + 3, 207, rect.height() - 6))
    painter.setBrush(QColor(12, 14, 23, 246))
    painter.drawRoundedRect(QRectF(x + 424, y + 3, 101, rect.height() - 6), 8, 8)
    _dashed_line(painter, x + 218, y + 10, y + 151)
    _dashed_line(painter, x + 423, y + 10, y + 151)
    _notches(painter, x + 218, y + 3, y + 160)
    _notches(painter, x + 423, y + 3, y + 160)
    if entry is None:
        _text(painter, QRectF(x + 20, y + 56, 470, 38), "RELÍQUIA NÃO EQUIPADA", 19, "#a9b2c1")
        return

    relic, rating, icon = entry
    _text(painter, QRectF(x + 10, y + 6, 112, 19), relic.slot.upper(), 12, "#dfc88c", bold=True)
    painter.setPen(QPen(QColor("#8c8068"), 1))
    painter.setBrush(QColor(90, 83, 69, 173))
    painter.drawRect(QRectF(x + 171, y + 7, 37, 23))
    _text(painter, QRectF(x + 172, y + 8, 35, 21), f"+{relic.level}", 13,
          "#ead49b", bold=True, alignment=Qt.AlignmentFlag.AlignCenter)
    if not icon.isNull():
        _art(painter, icon, QRectF(x + 8, y + 29, 92, 93))
    _stat_icon(painter, relic.main_stat.key, QRectF(x + 104, y + 42, 21, 21))
    _text(painter, QRectF(x + 128, y + 41, 82, 24),
          _compact_stat_name(relic.main_stat.name), 14, "#f0f0f1")
    _text(painter, QRectF(x + 105, y + 66, 105, 37), relic.main_stat.formatted_value,
          29, "#ffffff", bold=True, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    _stars(painter, x + 13, y + 121, relic.rarity)
    _text(painter, QRectF(x + 12, y + 142, 198, 17), relic.set_name, 11, "#ccd0da")

    for index, stat in enumerate(relic.sub_stats[:4]):
        row_y = y + 13 + index * 36
        _stat_icon(painter, stat.key, QRectF(x + 230, row_y + 3, 20, 20))
        _text(painter, QRectF(x + 254, row_y, 103, 26),
              _compact_stat_name(stat.name), 14, "#e9e8ed")
        if stat.upgrades:
            _text(painter, QRectF(x + 357, row_y, 17, 25), f"+{stat.upgrades}",
                  10, "#89949e")
        _text(painter, QRectF(x + 374, row_y, 39, 26), stat.formatted_value,
              14, "#f5f6f9", bold=True,
              alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    _text(painter, QRectF(x + 432, y + 30, 85, 21), "PONTOS", 11, "#aeb5c2",
          alignment=Qt.AlignmentFlag.AlignCenter)
    _text(painter, QRectF(x + 429, y + 56, 90, 38), f"{rating.score:.1f}",
          28, "#e6cd94", bold=True, alignment=Qt.AlignmentFlag.AlignCenter)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(39, 40, 47, 248))
    painter.drawRoundedRect(QRectF(x + 441, y + 103, 67, 35), 3, 3)
    _text(painter, QRectF(x + 441, y + 103, 67, 35), rating.grade,
          23, _score_color(rating.grade), bold=True,
          alignment=Qt.AlignmentFlag.AlignCenter)


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
    hide_uid: bool = False,
    skills: list[tuple[int, bool, QPixmap]] | None = None,
    eidolons: list[QPixmap] | None = None,
    cone_stats: list[dict[str, Any]] | None = None,
    cone_rarity: int = 0,
) -> QPixmap:
    """Renderiza a build em uma composição ampla para exportação PNG."""
    canvas = QPixmap(*CARD_SIZE)
    canvas.fill(QColor("#0a101c"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    background = QLinearGradient(0, 0, CARD_SIZE[0], CARD_SIZE[1])
    background.setColorAt(0, QColor("#202638"))
    background.setColorAt(0.5, QColor("#293449"))
    background.setColorAt(1, QColor("#181b2a"))
    painter.fillRect(canvas.rect(), background)
    _art(painter, artwork, QRectF(368, -107, 1030, 950))

    left_fade = QLinearGradient(0, 0, 680, 0)
    left_fade.setColorAt(0, QColor(9, 15, 26, 218))
    left_fade.setColorAt(1, QColor(9, 15, 26, 0))
    painter.fillRect(QRectF(0, 0, 680, 1080), left_fade)
    right_fade = QLinearGradient(1270, 0, 1920, 0)
    right_fade.setColorAt(0, QColor(9, 15, 26, 0))
    right_fade.setColorAt(1, QColor(9, 15, 26, 180))
    painter.fillRect(QRectF(1270, 0, 650, 1080), right_fade)
    bottom_fade = QLinearGradient(0, 710, 0, 1080)
    bottom_fade.setColorAt(0, QColor(9, 15, 26, 0))
    bottom_fade.setColorAt(1, QColor(9, 15, 26, 225))
    painter.fillRect(QRectF(0, 710, 1920, 370), bottom_fade)

    _text(painter, QRectF(55, 19, 460, 60), character.name, 46, "#ffffff", bold=True)
    _text(painter, QRectF(62, 82, 112, 34), f"NV. {character.level}", 24,
          "#d9bf80", bold=True)
    element_keys = {
        "Físico": "Physical", "Fogo": "Fire", "Gelo": "Ice", "Raio": "Lightning",
        "Vento": "Wind", "Quântico": "Quantum", "Imaginário": "Imaginary",
    }
    path_keys = {
        "Preservação": "Preservation", "Caça": "Hunt", "Erudição": "Erudition",
        "Harmonia": "Harmony", "Inexistência": "Nihility", "Destruição": "Destruction",
        "Abundância": "Abundance", "Recordação": "Remembrance", "Euforia": "Elation",
    }
    for index, icon in enumerate((
        FRIBBELS_ASSETS / "icon" / "element" / f"{element_keys.get(character.element, character.element)}White.webp",
        FRIBBELS_ASSETS / "icon" / "path" / f"{path_keys.get(character.path, character.path)}.webp",
    )):
        pixmap = QPixmap(str(icon))
        if not pixmap.isNull():
            _art(painter, _tinted(pixmap, "#e8e9ea") if index else pixmap,
                 QRectF(194 + index * 49, 78, 38, 40))
    _text(painter, QRectF(296, 83, 63, 32), f"E{character.eidolon}", 21,
          "#d9bf80", bold=True)

    painter.setPen(QPen(QColor(211, 213, 217, 126), 2))
    painter.drawLine(45, 150, 45, 826)
    painter.drawLine(45, 826, 486, 826)
    painter.drawLine(45, 150, 57, 150)
    stat_panel = QRectF(57, 138, 443, 675)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(10, 15, 25, 208))
    painter.drawRoundedRect(stat_panel, 16, 16)
    stat_order = (
        "MaxHP", "Attack", "Defence", "Speed", "CriticalChance", "CriticalDamage",
        "BreakDamageAddedRatio", "HealRatio", "OutgoingHealingBoost", "SPRatio",
        "StatusProbability", "StatusResistance",
    )
    ordered_stats = sorted(
        stats,
        key=lambda item: stat_order.index(str(item.get("key")))
        if str(item.get("key")) in stat_order else len(stat_order),
    )
    if ordered_stats:
        row_height = min(56.0, 663.0 / len(ordered_stats))
        for index, stat in enumerate(ordered_stats):
            y = 149 + index * row_height
            if index % 2 == 0:
                painter.fillRect(QRectF(65, y, 426, row_height - 2), QColor(255, 255, 255, 10))
            stat_key = str(stat.get("key", ""))
            _stat_icon(painter, stat_key, QRectF(78, y + 11, 28, 28))
            _text(painter, QRectF(119, y + 5, 266, row_height - 8),
                  str(stat.get("name", "")), 20, "#f0f2f6")
            _text(
                painter, QRectF(390, y + 5, 88, row_height - 8),
                str(stat.get("formatted", "—")), 21, "#ffffff", bold=True,
                alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
    else:
        _text(painter, QRectF(78, 345, 400, 50), "Atributos indisponíveis", 19, "#aeb9c8")

    cone_panel = QRectF(43, 854, 470, 167)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(10, 13, 22, 229))
    painter.drawRoundedRect(cone_panel, 12, 12)
    _dashed_line(painter, 212, 869, 1008)
    _text(painter, QRectF(52, 862, 116, 27),
          f"NV. {character.light_cone_level}" if character.light_cone_level else "NV. —",
          17, "#dfc889", bold=True)
    if not cone_art.isNull():
        painter.save()
        painter.translate(121, 947)
        painter.rotate(10)
        _cover(painter, cone_art, QRectF(-62, -64, 124, 117), 4)
        painter.restore()
    if character.light_cone_rank:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(20, 22, 29, 233))
        painter.drawEllipse(QRectF(174, 879, 27, 27))
        _text(painter, QRectF(174, 879, 27, 27), f"{character.light_cone_rank}",
              14, "#dfc889", bold=True, alignment=Qt.AlignmentFlag.AlignCenter)
    _stars(painter, 61, 991, cone_rarity)
    _text(painter, QRectF(226, 864, 272, 46), character.light_cone,
          18, "#f5eee3", bold=True)
    cone_stat_keys = {"BaseHP": "MaxHP", "BaseAttack": "Attack", "BaseDefence": "Defence"}
    cone_stat_names = {"BaseHP": "PV", "BaseAttack": "ATQ", "BaseDefence": "DEF"}
    if cone_stats:
        ordered_cone_stats = sorted(
            cone_stats,
            key=lambda item: ("BaseHP", "BaseAttack", "BaseDefence").index(item["type"]),
        )
        for index, stat in enumerate(ordered_cone_stats[:3]):
            y = 913 + index * 30
            key = str(stat["type"])
            _stat_icon(painter, cone_stat_keys[key], QRectF(229, y + 2, 20, 20))
            _text(painter, QRectF(258, y, 143, 25), cone_stat_names[key],
                  16, "#e5e7eb")
            _text(painter, QRectF(403, y, 89, 25), str(stat.get("formatted_value", "—")),
                  17, "#f6f3ed", bold=True,
                  alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    else:
        _text(painter, QRectF(228, 930, 265, 45), "Atributos básicos indisponíveis",
              15, "#aeb8c6")
    _text(painter, QRectF(45, 1031, 465, 25), share_uid_text(uid, hide_uid),
          16, "#c2c4c9")

    ticket = QRectF(588, 746, 706, 273)
    painter.setPen(QPen(QColor(186, 172, 144, 54), 1))
    painter.setBrush(QColor(15, 16, 23, 236))
    painter.drawRoundedRect(ticket, 5, 5)
    _dashed_line(painter, 946, 761, 1005)
    _notches(painter, 946, 747, 1019)
    painter.setPen(QPen(QColor("#a5a7ad"), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawLine(1250, 750, 1280, 779)
    painter.drawArc(QRectF(1245, 744, 29, 28), 0, 170 * 16)
    _text(painter, QRectF(614, 761, 319, 28), "CONJUNTOS EQUIPADOS", 18,
          "#d8c18c", bold=True)
    sets = Counter(relic.set_name for relic, _rating, _icon in relics if relic.set_name)
    for index, (name, count) in enumerate(
        sorted(sets.items(), key=lambda item: (-item[1], item[0]))[:3]
    ):
        y = 799 + index * 38
        painter.setPen(QPen(QColor("#81735a"), 1))
        painter.setBrush(QColor(55, 51, 45, 190))
        painter.drawRect(QRectF(617, y + 2, 34, 25))
        _text(painter, QRectF(617, y + 2, 34, 25), str(count), 16,
              "#e3d0a0", bold=True, alignment=Qt.AlignmentFlag.AlignCenter)
        _text(painter, QRectF(664, y, 262, 29), name, 17, "#e9e5df")
    if not sets:
        _text(painter, QRectF(618, 803, 310, 30), "Nenhuma relíquia equipada",
              16, "#aeb9c8")
    _text(painter, QRectF(617, 927, 305, 25),
          "TIME CUSTOMIZADO" if custom_team else "TIME PADRÃO", 14,
          "#d8c18c", bold=True)
    for index, character_id in enumerate(result.team_character_ids[:3]):
        icon = QPixmap(str(FRIBBELS_ASSETS / "icon" / "avatar" / f"{character_id}.webp"))
        if not icon.isNull():
            _cover(painter, icon, QRectF(619 + index * 49, 958, 41, 41), 20)
    _text(painter, QRectF(775, 961, 155, 32), result.team_name,
          14, "#d6e0ec")

    _text(painter, QRectF(973, 761, 293, 30), "DPS BENCHMARK", 19,
          "#d8c18c", bold=True)
    _text(painter, QRectF(972, 800, 244, 96), f"{result.score:.1f}%",
          68, "#f4ebd5", bold=True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(57, 51, 44, 239))
    painter.drawRoundedRect(QRectF(1206, 838, 71, 48), 3, 3)
    _text(painter, QRectF(1206, 838, 71, 48), result.grade, 26,
          _score_color(result.grade), bold=True,
          alignment=Qt.AlignmentFlag.AlignCenter)
    combo = (
        f"Dano de combo · {result.damage_index:,.0f}".replace(",", ".")
        if result.engine_source == "fribbels" else "Dano de combo · indisponível"
    )
    _text(painter, QRectF(974, 943, 298, 25), combo, 16, "#c8c9cc")
    _text(painter, QRectF(974, 978, 298, 24),
          f"Relíquias avaliadas · {len(relics)}/6", 14, "#b4aea3")

    for index, skill in enumerate((skills or [])[:4]):
        level, boosted, icon = skill
        _round_badge(painter, icon, 535, 260 + index * 111,
                     active=True, level=level, boosted=boosted)
    for index in range(6):
        icon = eidolons[index] if eidolons and index < len(eidolons) else QPixmap()
        _round_badge(painter, icon, 1290, 42 + index * 111,
                     active=index < character.eidolon)

    for index in range(6):
        entry = relics[index] if index < len(relics) else None
        _relic_card(painter, QRectF(1376, 38 + index * 169, 526, 158), entry)

    _text(painter, QRectF(1374, 1053, 528, 20), "ASTRAL OPTIMIZER",
          12, "#c6b990", bold=True,
          alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    painter.end()
    return canvas
