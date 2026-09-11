from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
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


CARD_SIZE = (1200, 850)


@dataclass(frozen=True, slots=True)
class WarpShareData:
    uid: str
    banner_title: str
    scope_title: str
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
    """Calcula os mesmos indicadores da tela para o cartão compartilhável."""
    selected = [record for record in records if record.gacha_type == gacha_type]
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
    total = summary.total if summary is not None else len(selected)
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
    dated = sorted(record.time[:10] for record in selected if len(record.time) >= 10)
    period = f"{dated[0]} a {dated[-1]}" if dated else "Período não disponível"
    return WarpShareData(
        uid=selected[-1].uid if selected else (summary.uid if summary else ""),
        banner_title=banner_title,
        scope_title=edition_title,
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
        medium_pity_count=sum(
            cap * (2 / 3) < pity <= cap * (5 / 6) for pity in pity_values
        ),
        high_pity_count=sum(pity > cap * (5 / 6) for pity in pity_values),
        wins=analysis.wins,
        losses=analysis.losses,
        guaranteed_results=analysis.guaranteed,
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
        value, Qt.TextElideMode.ElideRight, max(1, int(rect.width()))
    )
    painter.drawText(rect, int(alignment), displayed)


def _panel(painter: QPainter, rect: QRectF, color: str = "#111c31") -> None:
    painter.setBrush(_color(color))
    painter.setPen(QPen(_color("#304b70"), 1.2))
    painter.drawRoundedRect(rect, 13, 13)


def _cover(painter: QPainter, pixmap: QPixmap, rect: QRectF, rounded: bool) -> None:
    if pixmap.isNull():
        painter.setBrush(_color("#20314d"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 10, 10)
        return
    source = QRectF(pixmap.rect())
    target_ratio = rect.width() / rect.height()
    source_ratio = source.width() / max(source.height(), 1)
    if source_ratio > target_ratio:
        width = source.height() * target_ratio
        source.setLeft((source.width() - width) / 2)
        source.setWidth(width)
    else:
        height = source.width() / target_ratio
        source.setTop((source.height() - height) / 2)
        source.setHeight(height)
    path = QPainterPath()
    if rounded:
        path.addEllipse(rect)
    else:
        path.addRoundedRect(rect, 10, 10)
    painter.save()
    painter.setClipPath(path)
    painter.drawPixmap(rect, pixmap, source)
    painter.restore()


def _metric(
    painter: QPainter, rect: QRectF, label: str, value: str, detail: str = ""
) -> None:
    _panel(painter, rect, "#14233b")
    _text(painter, QRectF(rect.x() + 14, rect.y() + 8, rect.width() - 28, 18), label.upper(), 10, "#8fb1d5", bold=True)
    _text(painter, QRectF(rect.x() + 14, rect.y() + 27, rect.width() - 28, 32), value, 23, "#ffffff", bold=True)
    if detail:
        _text(painter, QRectF(rect.x() + 14, rect.y() + 57, rect.width() - 28, 17), detail, 9, "#9fb2cc")


def _format_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except ValueError:
        return value[:10] or "—"


def pity_color(pity: int, cap: int) -> str:
    if pity <= cap * (2 / 3):
        return "#70e0a3"
    if pity <= cap * (5 / 6):
        return "#ffb45c"
    return "#ff6f7d"


def pity_range_label(pity: int, cap: int) -> str:
    if pity <= cap * (2 / 3):
        return "PITY BAIXO"
    if pity <= cap * (5 / 6):
        return "PITY MÉDIO"
    return "PITY ALTO"


def _result_card(
    painter: QPainter,
    result: FiveStarOutcome,
    rect: QRectF,
    cap: int,
) -> None:
    record = result.record
    accent = pity_color(result.pity, cap)
    painter.setBrush(_color("#14233a"))
    painter.setPen(QPen(_color(accent), 2))
    painter.drawRoundedRect(rect, 12, 12)

    avatar_path = FRIBBELS_ASSETS / "icon" / "avatar" / f"{record.item_id}.webp"
    icon_path = avatar_path
    if not icon_path.exists():
        icon_path = FRIBBELS_ASSETS / "icon" / "light_cone" / f"{record.item_id}.webp"
    _cover(
        painter,
        QPixmap(str(icon_path)),
        QRectF(rect.x() + 10, rect.y() + 11, 68, 68),
        avatar_path.exists(),
    )
    _text(
        painter,
        QRectF(rect.x() + 91, rect.y() + 9, rect.width() - 184, 24),
        record.name,
        14,
        bold=True,
    )
    _text(
        painter,
        QRectF(rect.x() + 91, rect.y() + 33, rect.width() - 184, 18),
        _format_date(record.time),
        9,
        "#91a8c3",
    )
    outcome_colors = {
        "won": "#75e5a6",
        "guaranteed": "#75d8ff",
        "lost": "#ff8490",
        "neutral": "#aab6c8",
    }
    _text(
        painter,
        QRectF(rect.x() + 91, rect.y() + 54, rect.width() - 184, 18),
        result.label,
        9,
        outcome_colors[result.outcome],
        bold=True,
    )
    _text(
        painter,
        QRectF(rect.right() - 87, rect.y() + 13, 69, 38),
        str(result.pity),
        29,
        accent,
        bold=True,
        alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    _text(
        painter,
        QRectF(rect.right() - 105, rect.y() + 51, 87, 18),
        pity_range_label(result.pity, cap),
        8,
        accent,
        bold=True,
        alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )


def render_warp_share_card(data: WarpShareData, *, hide_uid: bool = False) -> QPixmap:
    columns = 3
    rows = max(1, ceil(len(data.recent) / columns))
    canvas_height = max(CARD_SIZE[1], 606 + rows * 102 + 48)
    canvas = QPixmap(CARD_SIZE[0], canvas_height)
    canvas.fill(_color("#070d18"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    background = QLinearGradient(0, 0, CARD_SIZE[0], canvas_height)
    background.setColorAt(0, _color("#071321"))
    background.setColorAt(0.62, _color("#111a31"))
    background.setColorAt(1, _color("#251936"))
    painter.fillRect(canvas.rect(), background)
    painter.setPen(QPen(_color("#42658e"), 2))
    painter.drawRoundedRect(QRectF(8, 8, 1184, canvas_height - 16), 20, 20)

    _text(painter, QRectF(32, 24, 700, 25), "ASTRAL OPTIMIZER  •  RELATÓRIO DE SALTOS", 12, "#77dcff", bold=True)
    _text(painter, QRectF(32, 51, 780, 38), data.banner_title.upper(), 25, bold=True)
    _text(painter, QRectF(32, 88, 780, 20), f"{data.scope_title}  •  {data.period}", 11, "#a9bad1")
    uid = "UID •••••••••" if hide_uid else f"UID {data.uid}"
    _text(painter, QRectF(890, 40, 270, 24), uid, 12, "#b9d8ee", bold=True, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    _text(painter, QRectF(850, 68, 310, 20), f"Categoria: {data.total:,} tiros  •  {data.total * 160:,} Jades".replace(",", "."), 10, "#91a7c3", alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    _text(painter, QRectF(32, 126, 730, 24), "ESTATÍSTICAS DO HISTÓRICO", 14, bold=True)
    metric_width = 168
    _metric(painter, QRectF(32, 159, metric_width, 82), "Pity 5★ atual", f"{data.five_star_pity}/{data.cap}", "acumulado da categoria")
    rate_up_detail = (
        "garantia ativa" if data.guaranteed
        else "banner permanente" if data.contest == "Sem disputa"
        else "sem garantia"
    )
    _metric(painter, QRectF(212, 159, metric_width, 82), "Situação do rate-up", "GARANTIDO" if data.guaranteed else data.contest.upper(), rate_up_detail)
    _metric(painter, QRectF(392, 159, metric_width, 82), "Média de pity", f"{data.average_pity:.1f}" if data.average_pity is not None else "—", f"mediana {data.median_pity:.1f}" if data.median_pity is not None else "sem resultados")
    _metric(painter, QRectF(32, 253, metric_width, 82), "Resultados 5★", str(data.five_star_count), f"{data.four_star_count} resultados 4★")
    _metric(painter, QRectF(212, 253, metric_width, 82), "Vitórias no rate-up", str(data.wins), f"{data.losses} derrota(s)")
    _metric(painter, QRectF(392, 253, metric_width, 82), "Taxa de vitória", f"{data.win_rate:.0f}%" if data.win_rate is not None else "—", f"{data.guaranteed_results} garantido(s)")

    chart = QRectF(584, 126, 568, 209)
    _panel(painter, chart, "#101c30")
    _text(painter, QRectF(602, 137, 300, 22), "TIROS POR MÊS", 11, "#bfd0e5", bold=True)
    if data.monthly:
        maximum = max(value for _label, value in data.monthly) or 1
        width = 516 / len(data.monthly)
        for index, (label, value) in enumerate(data.monthly):
            bar_height = max(5.0, value / maximum * 119)
            x = 606 + index * width
            y = 294 - bar_height
            painter.setBrush(_color("#5ccff1" if index % 2 == 0 else "#856fda"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, y, max(13, width - 11), bar_height), 4, 4)
            _text(painter, QRectF(x, y - 19, max(13, width - 11), 17), str(value), 9, "#ffffff", bold=True, alignment=Qt.AlignmentFlag.AlignCenter)
            _text(painter, QRectF(x - 4, 299, width - 3, 17), label[5:7] + "/" + label[2:4], 8, "#91a8c3", alignment=Qt.AlignmentFlag.AlignCenter)
    else:
        _text(painter, QRectF(602, 210, 532, 30), "Sem registros mensais disponíveis.", 12, "#98aac0", alignment=Qt.AlignmentFlag.AlignCenter)

    distribution = QRectF(32, 350, 1120, 90)
    _panel(painter, distribution, "#101c30")
    _text(painter, QRectF(49, 359, 260, 20), "DISTRIBUIÇÃO DOS PITYS 5★", 11, "#bfd0e5", bold=True)
    distribution_items = (
        ("Pity baixo", data.low_pity_count, "#70e0a3", f"até {int(data.cap * (2 / 3))}"),
        ("Pity médio", data.medium_pity_count, "#ffb45c", f"até {int(data.cap * (5 / 6))}"),
        ("Pity alto", data.high_pity_count, "#ff6f7d", f"até {data.cap}"),
    )
    for index, (label, count, accent, detail) in enumerate(distribution_items):
        x = 366 + index * 246
        painter.setBrush(_color(accent))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(x, 375, 13, 13))
        _text(painter, QRectF(x + 20, 361, 126, 24), label, 10, "#c8d5e6", bold=True)
        _text(painter, QRectF(x + 148, 360, 42, 27), str(count), 18, accent, bold=True, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        _text(painter, QRectF(x + 20, 386, 170, 18), detail, 9, "#8298b4")
    _text(painter, QRectF(49, 397, 278, 18), f"Melhor {data.best_pity or '—'}  •  Mediana {data.median_pity or '—'}  •  Pior {data.worst_pity or '—'}", 10, "#91a8c3")
    _text(painter, QRectF(49, 416, 278, 17), f"Pity 4★ atual: {data.four_star_pity}/10", 9, "#91a8c3")

    _text(painter, QRectF(32, 460, 750, 25), "HISTÓRICO COMPLETO DE RESULTADOS 5★", 14, bold=True)
    _text(painter, QRectF(32, 484, 950, 18), f"{len(data.recent)} resultado(s) no filtro selecionado  •  verde: baixo  •  laranja: médio  •  vermelho: alto", 10, "#91a8c3")
    if not data.recent:
        _panel(painter, QRectF(32, 518, 1120, 90), "#101c30")
        _text(painter, QRectF(48, 538, 1088, 40), "Nenhum resultado 5★ individual disponível.", 14, "#aabbd0", alignment=Qt.AlignmentFlag.AlignCenter)
    card_width = 360
    for index, result in enumerate(data.recent):
        column = index % columns
        row = index // columns
        _result_card(
            painter,
            result,
            QRectF(32 + column * 376, 518 + row * 102, card_width, 90),
            data.cap,
        )

    footer = "UID ocultada pelo modo Privacidade" if hide_uid else "Dados gerados a partir do histórico importado"
    _text(painter, QRectF(32, canvas_height - 35, 1128, 18), footer + "  •  astral optimizer", 9, "#7189a6", alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    painter.end()
    return canvas
