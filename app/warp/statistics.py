from __future__ import annotations

from dataclasses import dataclass

from app.warp.models import WarpRecord


STANDARD_CHARACTER_IDS = {"1003", "1004", "1101", "1104", "1107", "1209", "1211"}
STANDARD_LIGHT_CONE_IDS = {
    "23000", "23002", "23003", "23004", "23005", "23012", "23013"
}


@dataclass(frozen=True, slots=True)
class PityState:
    five_star: int
    four_star: int
    guaranteed: bool


@dataclass(frozen=True, slots=True)
class FiveStarOutcome:
    record: WarpRecord
    pity: int
    outcome: str
    label: str


def records_for(records: list[WarpRecord], gacha_types: set[str]) -> list[WarpRecord]:
    return [record for record in records if record.gacha_type in gacha_types]


def pity_state(
    records: list[WarpRecord],
    gacha_types: set[str],
    standard_ids: set[str] | None = None,
) -> PityState:
    selected = records_for(records, gacha_types)
    five_star = 0
    four_star = 0
    latest_five: WarpRecord | None = None
    for record in selected:
        five_star += 1
        four_star += 1
        if record.rank_type == 4:
            four_star = 0
        if record.rank_type == 5:
            latest_five = record
            five_star = 0
    guaranteed = bool(
        standard_ids
        and latest_five
        and (
            (
                latest_five.featured_name
                and latest_five.name.casefold()
                != latest_five.featured_name.casefold()
            )
            or (
                not latest_five.featured_name
                and latest_five.item_id in standard_ids
            )
        )
    )
    return PityState(five_star, four_star, guaranteed)


def five_star_history(records: list[WarpRecord]) -> list[tuple[WarpRecord, int]]:
    pity_by_type: dict[str, int] = {}
    history: list[tuple[WarpRecord, int]] = []
    for record in records:
        pity = pity_by_type.get(record.gacha_type, 0) + 1
        pity_by_type[record.gacha_type] = pity
        if record.rank_type == 5:
            history.append((record, pity))
            pity_by_type[record.gacha_type] = 0
    return list(reversed(history))


def classify_five_star_history(
    history: list[tuple[WarpRecord, int]],
    standard_ids: set[str] | None,
    contest: str,
) -> list[FiveStarOutcome]:
    if standard_ids is None:
        return [
            FiveStarOutcome(record, pity, "neutral", "SEM DISPUTA")
            for record, pity in history
        ]

    guaranteed = False
    chronological: list[FiveStarOutcome] = []
    for record, pity in reversed(history):
        lost_rate_up = bool(
            record.featured_name
            and record.name.casefold() != record.featured_name.casefold()
        )
        if lost_rate_up or (
            not record.featured_name and record.item_id in standard_ids
        ):
            chronological.append(
                FiveStarOutcome(record, pity, "lost", f"PERDEU {contest}")
            )
            guaranteed = True
        elif guaranteed:
            chronological.append(
                FiveStarOutcome(record, pity, "guaranteed", "GARANTIDO")
            )
            guaranteed = False
        else:
            chronological.append(
                FiveStarOutcome(record, pity, "won", f"GANHOU {contest}")
            )
    return list(reversed(chronological))
