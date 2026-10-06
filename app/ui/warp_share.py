from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from pathlib import Path
from statistics import median

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from app.preferences import themed_color
from app.ui.widgets import FRIBBELS_ASSETS
from app.warp.analytics import analyze_warps
from app.warp.models import WarpRecord, WarpSummary
from app.warp.statistics import (
    FiveStarOutcome,
    STANDARD_CHARACTER_IDS,
    STANDARD_LIGHT_CONE_IDS,
    classify_five_star_history,
    five_star_history,
    pity_state,
)


CARD_SIZE = (1600, 372)
RESULTS_PER_PAGE = 60
_COLUMNS = 3
_CARD_WIDTH = 496
_CARD_HEIGHT = 106
_CARD_GAP_X = 12
_CARD_GAP_Y = 8
_GALLERY_X = 44
_GALLERY_Y = 201


@dataclass(frozen=True, slots=True)
class WarpShareData:
    uid: str
    banner_title: str
    scope_title: str
    edition_filtered: bool
    total: int
    five_star_count: int
    four_star_count: int
    five_star_pity: int
    four_star_pity: int
    cap: int
    guaranteed: bool
    average_pity: float | None
    median_pity: float | None
    best_pity: int | None
    worst_pity: int | None
    low_pity_count: int
    medium_pity_count: int
    high_pity_count: int
    wins: int
    losses: int
    guaranteed_results: int
    indeterminate_results: int
    win_rate: float | None
    period: str
    recent: tuple[FiveStarOutcome, ...]
    monthly: tuple[tuple[str, int], ...]
    contest: str


def _standard_ids(gacha_type: str) -> set[str] | None:
    if gacha_type in {"11", "21"}:
        return STANDARD_CHARACTER_IDS
    if gacha_type in {"12", "22"}:
        return STANDARD_LIGHT_CONE_IDS
    return None


def build_warp_share_data(
    records: list[WarpRecord],
    summaries: dict[str, WarpSummary],
    gacha_type: str,
    banner_title: str,
    cap: int,
    *,
    edition_id: str | None = None,
    edition_title: str = "Todos os saltos",
) -> WarpShareData:
    """Calcula os mesmos indicadores da tela para o relatório compartilhável."""
    selected = [record for record in records if record.gacha_type == gacha_type]
    visible_records = (
        [record for record in selected if (record.banner_id or "unknown") == edition_id]
        if edition_id else selected
    )
    standard_ids = _standard_ids(gacha_type)
    state = pity_state(selected, {gacha_type}, standard_ids)
    history = five_star_history(selected)
    contest = (
        "75/25" if gacha_type in {"12", "22"}
        else "50/50" if gacha_type in {"11", "21"}
        else "Sem disputa"
    )
    outcomes = classify_five_star_history(history, standard_ids, contest)
    recent = outcomes
    if edition_id:
        recent = [
            result for result in outcomes
            if (result.record.banner_id or "unknown") == edition_id
        ]

    summary = summaries.get(gacha_type)
    total = len(visible_records) if edition_id else (summary.total if summary is not None else len(selected))
    five_star_count = summary.five_star_count if summary is not None else len(history)
    four_star_count = (
        summary.four_star_count
        if summary is not None
        else sum(record.rank_type == 4 for record in selected)
    )
    five_star_pity = summary.five_star_pity if summary is not None else state.five_star
    four_star_pity = summary.four_star_pity if summary is not None else state.four_star
    pity_values = [pity for _record, pity in history]
    if summary is not None and not pity_values and summary.five_star_count:
        pity_values = [summary.featured_pity]
    analysis = analyze_warps(records, summaries, gacha_type)
    contested = analysis.wins + analysis.losses
    dated = sorted(record.time[:10] for record in visible_records if len(record.time) >= 10)
    period = f"{dated[0]} a {dated[-1]}" if dated else "Período não disponível"
    return WarpShareData(
        uid=selected[-1].uid if selected else (summary.uid if summary else ""),
        banner_title=banner_title,
        scope_title=edition_title,
        edition_filtered=bool(edition_id),
        total=total,
        five_star_count=five_star_count,
        four_star_count=four_star_count,
        five_star_pity=five_star_pity,
        four_star_pity=four_star_pity,
        cap=cap,
        guaranteed=state.guaranteed if standard_ids is not None else False,
        average_pity=(sum(pity_values) / len(pity_values)) if pity_values else None,
        median_pity=float(median(pity_values)) if pity_values else None,
        best_pity=min(pity_values) if pity_values else None,
        worst_pity=max(pity_values) if pity_values else None,
        low_pity_count=sum(pity <= cap * (2 / 3) for pity in pity_values),
        medium_pity_count=sum(cap * (2 / 3) < pity <= cap * (5 / 6) for pity in pity_values),
        high_pity_count=sum(pity > cap * (5 / 6) for pity in pity_values),
        wins=analysis.wins,
        losses=analysis.losses,
        guaranteed_results=analysis.guaranteed,
        indeterminate_results=sum(result.outcome == "neutral" for result in outcomes),
        win_rate=(analysis.wins / contested * 100) if contested else None,
        period=period,
        recent=tuple(recent),
        monthly=analysis.monthly[-8:],
        contest=contest,
    )


def _color(value: str) -> QColor:
    return QColor(themed_color(value))


def _font(size: int, bold: bool = False) -> QFont:
    app = QApplication.instance()
    font = QFont(app.font().family() if app else "Segoe UI")
    font.setPixelSize(size)
    font.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
    return font


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
    font = _font(size, bold)
    painter.setFont(font)
    painter.setPen(_color(color))
    displayed = QFontMetrics(font).elidedText(
        str(value), Qt.TextElideMode.ElideRight, max(1, int(rect.width()))
    )
    painter.drawText(rect, int(alignment), displayed)


def _number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def pity_color(pity: int, cap: int) -> str:
    if pity <= cap * (2 / 3):
        return "#70e0a3"
    if pity <= cap * (5 / 6):
        return "#ffb45c"
    return "#ff6f7d"


def _format_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except ValueError:
        return value[:10] or "—"


def _period(value: str) -> str:
    if " a " not in value:
        return value
    start, end = value.split(" a ", 1)
    return f"{_format_date(start)} a {_format_date(end)}"


def _colorfulness(pixmap: QPixmap) -> float:
    image = pixmap.toImage()
    step_x = max(1, image.width() // 12)
    step_y = max(1, image.height() // 12)
    saturation = []
    for y in range(0, image.height(), step_y):
        for x in range(0, image.width(), step_x):
            pixel = image.pixelColor(x, y)
            if pixel.alpha() > 96:
                saturation.append(pixel.saturation())
    return sum(saturation) / len(saturation) if saturation else 0.0


def _portrait(record: WarpRecord, cache: dict[str, QPixmap]) -> QPixmap:
    if record.item_id not in cache:
        avatar = FRIBBELS_ASSETS / "icon" / "avatar" / f"{record.item_id}.webp"
        colored_variant = avatar.with_name(f"{record.item_id}b1.webp")
        base = QPixmap(str(avatar)) if avatar.is_file() else QPixmap()
        if not base.isNull() and colored_variant.is_file() and _colorfulness(base) < 18:
            colored = QPixmap(str(colored_variant))
            if not colored.isNull() and _colorfulness(colored) > _colorfulness(base) + 20:
                base = colored
        candidates = (
            FRIBBELS_ASSETS / "image" / "character_preview" / f"{record.item_id}.webp",
            FRIBBELS_ASSETS / "image" / "light_cone_portrait" / f"{record.item_id}.webp",
            FRIBBELS_ASSETS / "icon" / "light_cone" / f"{record.item_id}.webp",
        )
        cache[record.item_id] = base if not base.isNull() else next(
            (image for path in candidates if path.is_file() and not (image := QPixmap(str(path))).isNull()), QPixmap()
        )
    return cache[record.item_id]


def _draw_portrait(painter: QPainter, portrait: QPixmap, target: QRectF) -> None:
    if portrait.isNull():
        painter.fillRect(target, _color("#273447"))
        return
    source_width, source_height = portrait.width(), portrait.height()
    ratio = target.width() / target.height()
    if source_width / source_height < ratio:
        crop_height = source_width / ratio
        source = QRectF(0, (source_height - crop_height) * 0.13, source_width, crop_height)
    else:
        crop_width = source_height * ratio
        source = QRectF((source_width - crop_width) / 2, 0, crop_width, source_height)
    painter.drawPixmap(target, portrait, source)


def _draw_name(painter: QPainter, name: str, rect: QRectF) -> int:
    words = name.split()
    lines: list[str] = [name]
    size = 18
    three_line_fallback: tuple[int, list[str]] | None = None
    for candidate_size in (18, 17, 16, 15, 14, 13, 12):
        metrics = QFontMetrics(_font(candidate_size, True))
        wrapped: list[str] = []
        for word in words:
            if wrapped and metrics.horizontalAdvance(wrapped[-1] + " " + word) <= rect.width():
                wrapped[-1] += " " + word
            else:
                wrapped.append(word)
        if all(metrics.horizontalAdvance(line) <= rect.width() for line in wrapped):
            if len(wrapped) <= 2:
                lines, size = wrapped, candidate_size
                break
            if len(wrapped) == 3 and three_line_fallback is None:
                three_line_fallback = candidate_size, wrapped
    else:
        if three_line_fallback is not None:
            size, lines = three_line_fallback
    painter.setFont(_font(size, True))
    painter.setPen(_color("#f3f7fc"))
    line_height = 21 if len(lines) == 3 else 22
    for index, line in enumerate(lines):
        painter.drawText(QRectF(rect.x(), rect.y() + index * line_height, rect.width(), line_height),
                         int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), line)
    return len(lines)


def _outcome_label(result: FiveStarOutcome) -> str:
    if result.outcome == "neutral":
        return "Indeterminado" if "INDETERMINADO" in result.label.upper() else "Sem disputa"
    return result.label.capitalize() if result.label.isupper() else result.label


def _outcome_color(outcome: str) -> str:
    return {
        "won": "#63d5a0",
        "lost": "#ff827e",
        "guaranteed": "#78c9f1",
        "neutral": "#b2bdcb",
    }.get(outcome, "#b2bdcb")


def _outcome_symbol(painter: QPainter, x: float, y: float, outcome: str, color: str) -> None:
    pen = QPen(_color(color), 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if outcome == "won":
        painter.drawLine(int(x), int(y + 7), int(x + 4), int(y + 11))
        painter.drawLine(int(x + 4), int(y + 11), int(x + 13), int(y + 1))
    elif outcome == "lost":
        painter.drawLine(int(x + 1), int(y + 1), int(x + 12), int(y + 12))
        painter.drawLine(int(x + 12), int(y + 1), int(x + 1), int(y + 12))
    elif outcome == "guaranteed":
        shield = QPainterPath()
        shield.moveTo(x + 7, y)
        shield.lineTo(x + 13, y + 3)
        shield.lineTo(x + 12, y + 9)
        shield.quadTo(x + 10, y + 12, x + 7, y + 14)
        shield.quadTo(x + 4, y + 12, x + 2, y + 9)
        shield.lineTo(x + 1, y + 3)
        shield.closeSubpath()
        painter.drawPath(shield)
    else:
        painter.drawEllipse(QRectF(x + 1, y + 1, 12, 12))
        painter.drawPoint(int(x + 7), int(y + 7))


def _ticket_path(rect: QRectF, divider_x: float) -> QPainterPath:
    x, y, right, bottom = rect.x(), rect.y(), rect.right(), rect.bottom()
    middle = rect.center().y()
    path = QPainterPath()
    path.moveTo(x + 8, y)
    path.lineTo(right - 8, y)
    path.quadTo(right, y, right, y + 8)
    path.lineTo(right, middle - 9)
    path.cubicTo(right - 11, middle - 9, right - 11, middle + 9, right, middle + 9)
    path.lineTo(right, bottom - 8)
    path.quadTo(right, bottom, right - 8, bottom)
    path.lineTo(x + 8, bottom)
    path.quadTo(x, bottom, x, bottom - 8)
    path.lineTo(x, middle + 9)
    path.cubicTo(x + 11, middle + 9, x + 11, middle - 9, x, middle - 9)
    path.lineTo(x, y + 8)
    path.quadTo(x, y, x + 8, y)
    path.closeSubpath()
    notches = QPainterPath()
    notches.addEllipse(QRectF(divider_x - 6, y - 6, 12, 12))
    notches.addEllipse(QRectF(divider_x - 6, bottom - 6, 12, 12))
    return path.subtracted(notches)


def _result_card(
    painter: QPainter,
    result: FiveStarOutcome,
    rect: QRectF,
    cap: int,
    portraits: dict[str, QPixmap],
) -> None:
    del cap  # A cor do pity não participa da exportação.
    divider_x = rect.x() + 392
    shape = _ticket_path(rect, divider_x)
    painter.setPen(QPen(_color("#a88e62"), 1.1))
    painter.setBrush(_color("#0e1726"))
    painter.drawPath(shape)
    painter.setPen(QPen(_color("#a88e62"), 1, Qt.PenStyle.DashLine))
    painter.drawLine(int(divider_x), int(rect.y() + 12), int(divider_x), int(rect.bottom() - 12))

    portrait_rect = QRectF(rect.x() + 16, rect.y() + 18, 70, 70)
    clip = QPainterPath()
    clip.addEllipse(portrait_rect)
    painter.save()
    painter.setClipPath(clip)
    _draw_portrait(painter, _portrait(result.record, portraits), portrait_rect)
    painter.restore()
    painter.setPen(QPen(_color("#c8ad79"), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(portrait_rect)

    text_x = rect.x() + 102
    name_lines = _draw_name(painter, result.record.name, QRectF(text_x, rect.y() + 8, 273, 51))
    date_y = 55 if name_lines > 1 else 48
    _text(painter, QRectF(text_x, rect.y() + date_y, 268, 17), _format_date(result.record.time), 13, "#b8c4d3")
    accent = _outcome_color(result.outcome)
    tag = QRectF(text_x, rect.y() + 76, 156, 23)
    tag_color = _color(accent)
    tag_color.setAlpha(26)
    painter.setBrush(tag_color)
    painter.setPen(QPen(_color(accent), 0.9))
    painter.drawRoundedRect(tag, 5, 5)
    _outcome_symbol(painter, tag.x() + 9, tag.y() + 5, result.outcome, accent)
    _text(painter, QRectF(tag.x() + 30, tag.y() + 1, 119, 21), _outcome_label(result), 12, accent, bold=True)

    _text(painter, QRectF(divider_x + 10, rect.y() + 20, 83, 40), str(result.pity), 30, "#f5f4ef", bold=True,
          alignment=Qt.AlignmentFlag.AlignCenter)
    _text(painter, QRectF(divider_x + 10, rect.y() + 60, 83, 22), "saltos", 13, "#b8c4d3",
          alignment=Qt.AlignmentFlag.AlignCenter)


def _background(painter: QPainter, height: int) -> None:
    gradient = QLinearGradient(0, 0, CARD_SIZE[0], height)
    gradient.setColorAt(0, _color("#101b2b"))
    gradient.setColorAt(0.62, _color("#192335"))
    gradient.setColorAt(1, _color("#0c1422"))
    painter.fillRect(QRectF(0, 0, CARD_SIZE[0], height), gradient)
    painter.setPen(QPen(QColor(192, 164, 112, 38), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(QRectF(-170, -210, 380, 380), 16 * 4, 16 * 180)
    painter.drawArc(QRectF(1435, height - 180, 340, 340), 16 * 90, 16 * 150)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(212, 183, 125, 100))
    for x, y in ((19, 26), (87, 18), (1570, 35), (24, height - 39), (1580, height - 44)):
        painter.drawEllipse(QRectF(x, y, 3, 3))


def _render_page(
    data: WarpShareData,
    results: tuple[FiveStarOutcome, ...],
    page: int,
    page_count: int,
    portraits: dict[str, QPixmap],
    hide_uid: bool,
) -> QPixmap:
    rows = max(1, ceil(len(results) / _COLUMNS))
    tickets_bottom = _GALLERY_Y + rows * _CARD_HEIGHT + (rows - 1) * _CARD_GAP_Y
    footer_line = tickets_bottom + 22
    height = max(CARD_SIZE[1], footer_line + 43)
    canvas = QPixmap(CARD_SIZE[0], height)
    canvas.fill(_color("#0c1422"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    _background(painter, height)

    _text(painter, QRectF(45, 19, 720, 22), "ASTRAL OPTIMIZER  /  RELATÓRIO DE SALTOS", 13, "#d5bc8e", bold=True)
    _text(painter, QRectF(44, 47, 815, 49), data.banner_title, 38, "#fff9ec", bold=True)
    _text(painter, QRectF(45, 101, 840, 25), f"Período · {_period(data.period)}", 17, "#becada")
    uid = "UID •••••••••" if hide_uid else f"UID {data.uid}" if data.uid else "UID indisponível"
    _text(painter, QRectF(1300, 17, 254, 23), uid, 13, "#aab8ca",
          alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    resources = (
        ("passBig.webp", "SALTOS NA EDIÇÃO" if data.edition_filtered else "TOTAL DA CATEGORIA", _number(data.total), 916),
        ("jadeBig.webp", "JADES EQUIVALENTES", _number(data.total * 160), 1237),
    )
    for icon_name, label, value, x in resources:
        icon = QPixmap(str(FRIBBELS_ASSETS / "misc" / icon_name))
        if not icon.isNull():
            painter.drawPixmap(QRectF(x, 75, 40, 40), icon, QRectF(icon.rect()))
        _text(painter, QRectF(x + 48, 56, 250, 20), label, 13, "#c7ae82", bold=True)
        _text(painter, QRectF(x + 48, 75, 250, 42), value, 29, "#fff9ec", bold=True)

    painter.setPen(QPen(_color("#8b7656"), 1))
    painter.drawLine(44, 141, 1556, 141)
    _text(painter, QRectF(44, 155, 620, 30), "HISTÓRICO DE SALTOS · 5★", 22, "#e9d7b3", bold=True)
    detail = f"{len(data.recent)} obtenções"
    if data.scope_title != "Todos os saltos":
        detail += f" no filtro {data.scope_title}"
    if page_count > 1:
        detail += f" · {len(results)} nesta página"
    detail += "  ·  Mais recentes primeiro"
    _text(painter, QRectF(856, 158, 700, 24), detail, 14, "#b5c2d2",
          alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    if not results:
        _text(painter, QRectF(44, 226, 1512, 70), "Nenhum resultado 5★ disponível neste filtro.", 21, "#b5c2d2",
              alignment=Qt.AlignmentFlag.AlignCenter)
    for index, result in enumerate(results):
        column, row = index % _COLUMNS, index // _COLUMNS
        rect = QRectF(_GALLERY_X + column * (_CARD_WIDTH + _CARD_GAP_X),
                      _GALLERY_Y + row * (_CARD_HEIGHT + _CARD_GAP_Y),
                      _CARD_WIDTH, _CARD_HEIGHT)
        _result_card(painter, result, rect, data.cap, portraits)

    painter.setPen(QPen(_color("#6e624e"), 1))
    painter.drawLine(44, footer_line, 1556, footer_line)
    _text(painter, QRectF(44, footer_line + 8, 245, 24), "ASTRAL OPTIMIZER", 12, "#bea57a", bold=True)
    _text(painter, QRectF(285, footer_line + 8, 615, 24), "Saltos = quantidade até obter aquele 5★", 13, "#aab8ca")
    if page_count > 1:
        _text(painter, QRectF(1360, footer_line + 8, 195, 24), f"Página {page} / {page_count}", 13, "#aab8ca",
              alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    painter.end()
    return canvas


def render_warp_share_pages(data: WarpShareData, *, hide_uid: bool = False) -> tuple[QPixmap, ...]:
    """Renderiza o histórico completo com altura adequada ao conteúdo."""
    page_count = max(1, ceil(len(data.recent) / RESULTS_PER_PAGE))
    portraits: dict[str, QPixmap] = {}
    base, extra = divmod(len(data.recent), page_count)
    pages: list[QPixmap] = []
    start = 0
    for index in range(page_count):
        count = base + (index < extra)
        pages.append(_render_page(data, data.recent[start:start + count], index + 1, page_count, portraits, hide_uid))
        start += count
    return tuple(pages)


def render_warp_share_card(data: WarpShareData, *, hide_uid: bool = False) -> QPixmap:
    """Compatibilidade para prévias que usam apenas a primeira página."""
    return render_warp_share_pages(data, hide_uid=hide_uid)[0]


def warp_share_page_paths(path: Path, page_count: int) -> tuple[Path, ...]:
    """Mantém o nome escolhido para uma página e numera todas quando há várias."""
    if page_count == 1:
        return (path,)
    return tuple(path.with_name(f"{path.stem}_{index:02d}{path.suffix}") for index in range(1, page_count + 1))
