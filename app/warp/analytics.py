from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from app.planner.engine import CHARACTER_DISTRIBUTION, LIGHT_CONE_DISTRIBUTION
from app.warp.models import WarpRecord, WarpSummary
from app.warp.statistics import (
    STANDARD_CHARACTER_IDS,
    STANDARD_LIGHT_CONE_IDS,
    classify_five_star_history,
    five_star_history,
)


@dataclass(frozen=True, slots=True)
class HistoryGap:
    severity: str
    title: str
    detail: str


@dataclass(frozen=True, slots=True)
class WarpAnalytics:
    monthly: tuple[tuple[str, int], ...]
    editions: tuple[tuple[str, int], ...]
    personal_average: float | None
    theoretical_average: float
    wins: int
    losses: int
    guaranteed: int
    gaps: tuple[HistoryGap, ...]


def _expected(distribution: list[float]) -> float:
    return sum((index + 1) * probability for index, probability in enumerate(distribution))


def analyze_warps(
    records: list[WarpRecord],
    summaries: dict[str, WarpSummary],
    gacha_type: str,
) -> WarpAnalytics:
    selected = [record for record in records if record.gacha_type == gacha_type]
    months = Counter(record.time[:7] for record in selected if len(record.time) >= 7)
    editions: Counter[str] = Counter()
    for record in selected:
        title = record.banner_title or (
            f"Banner {record.banner_id[:8]}" if record.banner_id else "Não identificado"
        )
        label = (
            f"{title} · {record.banner_id[:6]}" if record.banner_id else title
        )
        editions[label] += 1

    history = five_star_history(selected)
    summary = summaries.get(gacha_type)
    pity_values = [pity for _record, pity in history]
    if summary is not None and not pity_values and summary.five_star_count:
        pity_values = [summary.featured_pity]
    standard = (
        STANDARD_CHARACTER_IDS if gacha_type in {"11", "21"}
        else STANDARD_LIGHT_CONE_IDS if gacha_type in {"12", "22"}
        else None
    )
    contest = "75/25" if gacha_type in {"12", "22"} else "50/50"
    outcomes = classify_five_star_history(history, standard, contest)
    counts = Counter(result.outcome for result in outcomes)
    distribution = (
        LIGHT_CONE_DISTRIBUTION if gacha_type in {"12", "22"}
        else CHARACTER_DISTRIBUTION
    )
    return WarpAnalytics(
        monthly=tuple(sorted(months.items())),
        editions=tuple(editions.most_common(8)),
        personal_average=(sum(pity_values) / len(pity_values)) if pity_values else None,
        theoretical_average=_expected(distribution),
        wins=counts["won"],
        losses=counts["lost"],
        guaranteed=counts["guaranteed"],
        gaps=detect_history_gaps(selected, summary),
    )


def detect_history_gaps(
    records: list[WarpRecord], summary: WarpSummary | None = None
) -> tuple[HistoryGap, ...]:
    gaps: list[HistoryGap] = []
    invalid_dates = sum(not _valid_time(record.time) for record in records)
    if invalid_dates:
        gaps.append(HistoryGap(
            "error", "Datas inválidas",
            f"{invalid_dates} registro(s) possuem data ausente ou inválida.",
        ))
    unidentified = sum(not record.banner_id for record in records)
    if unidentified:
        gaps.append(HistoryGap(
            "warning", "Edições não identificadas",
            f"{unidentified} registro(s) não possuem identificador de edição.",
        ))
    if summary is not None and summary.total > len(records):
        gaps.append(HistoryGap(
            "warning", "Somente resumo disponível",
            f"O resumo informa {summary.total} tiros, mas há {len(records)} registros individuais.",
        ))
    cap = 80 if records and records[0].gacha_type in {"12", "22"} else 90
    if len(records) >= cap and not any(record.rank_type == 5 for record in records):
        gaps.append(HistoryGap(
            "error", "5★ ausente além do limite",
            "Há tiros suficientes para atingir o hard pity, mas nenhum 5★ foi encontrado.",
        ))
    if not records and summary is not None:
        gaps.append(HistoryGap(
            "warning", "Histórico não reconstruível",
            "A planilha trouxe totais, mas não os tiros individuais desta categoria.",
        ))
    return tuple(gaps)


def _valid_time(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True
