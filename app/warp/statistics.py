from __future__ import annotations

from dataclasses import dataclass

from app.warp.models import WarpRecord


STANDARD_CHARACTER_IDS = {"1003", "1004", "1101", "1104", "1107", "1209", "1211"}
# Personagens opcionais da lista não promocional do Salto de Evento.
# Eles não fazem parte do Salto Estelar e também já tiveram banners próprios.
OPTIONAL_NON_FEATURED_CHARACTER_IDS = {
    "1102", "1205", "1208",  # Seele, Blade, Fu Xuan (3.2)
    "1006", "1221", "1302",  # Loba Prateada, Yunli, Argenti (4.2)
}
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


def featured_names_by_edition(records: list[WarpRecord]) -> dict[tuple[str, str], str]:
    """Recupera o destaque de uma edição quando o histórico não o informa.

    Um único 5★ fora das listas não promocionais identifica o destaque.
    Sem essa evidência, não adivinhamos o resultado de personagens opcionais.
    """
    groups: dict[tuple[str, str], list[WarpRecord]] = {}
    for record in records:
        if record.banner_id and record.rank_type == 5:
            groups.setdefault((record.gacha_type, record.banner_id), []).append(record)

    featured: dict[tuple[str, str], str] = {}
    for key, group in groups.items():
        explicit = {record.featured_name.strip() for record in group if record.featured_name.strip()}
        if len(explicit) == 1:
            featured[key] = next(iter(explicit))
            continue
        if explicit or key[0] not in {"11", "21"}:
            continue
        candidates = {
            record.item_id: record.name
            for record in group
            if record.item_id not in STANDARD_CHARACTER_IDS
            and record.item_id not in OPTIONAL_NON_FEATURED_CHARACTER_IDS
        }
        if len(candidates) == 1:
            featured[key] = next(iter(candidates.values()))
    return featured


def featured_name_for_record(
    record: WarpRecord, known: dict[tuple[str, str], str]
) -> str:
    return record.featured_name.strip() or known.get(
        (record.gacha_type, record.banner_id), ""
    )


def pity_state(
    records: list[WarpRecord],
    gacha_types: set[str],
    standard_ids: set[str] | None = None,
) -> PityState:
    selected = records_for(records, gacha_types)
    featured_by_edition = featured_names_by_edition(selected)
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
    latest_featured = (
        featured_name_for_record(latest_five, featured_by_edition)
        if latest_five else ""
    )
    guaranteed = bool(
        standard_ids
        and latest_five
        and (
            (
                latest_featured
                and latest_five.name.casefold()
                != latest_featured.casefold()
            )
            or (
                not latest_featured
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
    featured_by_edition = featured_names_by_edition(
        [record for record, _pity in history]
    )
    for record, pity in reversed(history):
        featured_name = featured_name_for_record(record, featured_by_edition)
        lost_rate_up = bool(
            featured_name
            and record.name.casefold() != featured_name.casefold()
        )
        if lost_rate_up or (
            not featured_name and record.item_id in standard_ids
        ):
            chronological.append(
                FiveStarOutcome(record, pity, "lost", f"PERDEU {contest}")
            )
            guaranteed = True
        elif (
            not featured_name
            and record.gacha_type in {"11", "21"}
            and record.item_id in OPTIONAL_NON_FEATURED_CHARACTER_IDS
        ):
            chronological.append(
                FiveStarOutcome(record, pity, "neutral", "RESULTADO INDETERMINADO")
            )
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
