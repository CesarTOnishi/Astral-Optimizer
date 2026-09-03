from __future__ import annotations

from dataclasses import dataclass
import math


REFUND_MULTIPLIERS = {
    "none": 0.0,
    "low": 0.04,
    "average": 0.075,
    "high": 0.11,
}


@dataclass(frozen=True, slots=True)
class BannerProjection:
    pity: int
    guaranteed: bool
    chance: float
    expected_warps: float
    worst_case: int
    missing_warps: int


@dataclass(frozen=True, slots=True)
class PlannerResult:
    jade_warps: int
    starlight_warps: int
    refunded_warps: int
    total_warps: int
    character: BannerProjection
    light_cone: BannerProjection
    milestones: tuple["PlannerMilestone", ...]


@dataclass(frozen=True, slots=True)
class PlannerMilestone:
    label: str
    chance: float
    expected_warps: float


def _distribution(cap: int, base: float, soft_start: int, increment: float) -> list[float]:
    survival = 1.0
    result: list[float] = []
    for index in range(cap):
        chance = min(1.0, base + max(0, index - soft_start) * increment)
        result.append(survival * chance)
        survival *= 1.0 - chance
    if result:
        result[-1] += survival
    return result


CHARACTER_DISTRIBUTION = _distribution(90, 0.006, 72, 0.06)
LIGHT_CONE_DISTRIBUTION = _distribution(80, 0.008, 64, 0.07)


def _adjusted(distribution: list[float], pity: int, cap: int) -> list[float]:
    pity = min(max(0, pity), cap - 1)
    sliced = distribution[pity:cap]
    total = sum(sliced)
    return [0.0, *(value / total for value in sliced)]


def _convolve(left: list[float], right: list[float]) -> list[float]:
    result = [0.0] * (len(left) + len(right) - 1)
    for left_index, left_value in enumerate(left):
        for right_index, right_value in enumerate(right):
            result[left_index + right_index] += left_value * right_value
    return result


def _projection(
    budget: int,
    pity: int,
    guaranteed: bool,
    cap: int,
    rate_up: float,
    distribution: list[float],
) -> BannerProjection:
    start = _adjusted(distribution, pity, cap)
    if guaranteed:
        cost = start
    else:
        fresh = _adjusted(distribution, 0, cap)
        win = [value * rate_up for value in start]
        loss = [value * (1.0 - rate_up) for value in _convolve(start, fresh)]
        cost = [0.0] * max(len(win), len(loss))
        for index, value in enumerate(win):
            cost[index] += value
        for index, value in enumerate(loss):
            cost[index] += value
    chance = sum(cost[: min(budget + 1, len(cost))])
    expected = sum(index * probability for index, probability in enumerate(cost))
    worst_case = cap - min(max(0, pity), cap - 1)
    if not guaranteed:
        worst_case += cap
    return BannerProjection(
        pity=pity,
        guaranteed=guaranteed,
        chance=min(max(chance, 0.0), 1.0),
        expected_warps=expected,
        worst_case=worst_case,
        missing_warps=max(0, worst_case - budget),
    )


def _cost_pmf(
    pity: int,
    guaranteed: bool,
    cap: int,
    rate_up: float,
    distribution: list[float],
) -> list[float]:
    start = _adjusted(distribution, pity, cap)
    if guaranteed:
        return start
    fresh = _adjusted(distribution, 0, cap)
    win = [value * rate_up for value in start]
    loss = [value * (1.0 - rate_up) for value in _convolve(start, fresh)]
    result = [0.0] * max(len(win), len(loss))
    for index, value in enumerate(win):
        result[index] += value
    for index, value in enumerate(loss):
        result[index] += value
    return result


def _milestones(
    budget: int,
    strategy: str,
    character_pity: int,
    character_guaranteed: bool,
    light_cone_pity: int,
    light_cone_guaranteed: bool,
) -> tuple[PlannerMilestone, ...]:
    insertion = -1 if strategy == "S1" else min(max(int(strategy[1:]), 0), 6)
    path: list[str] = []
    inserted = False
    if insertion == -1:
        path.append("cone")
        inserted = True
    for eidolon in range(7):
        path.append("character")
        if eidolon == insertion:
            path.append("cone")
            inserted = True
    if not inserted:
        path.append("cone")
    path.extend(["cone"] * 4)

    cumulative = [1.0]
    character_level = -1
    cone_level = 0
    used_character_start = False
    used_cone_start = False
    results: list[PlannerMilestone] = []
    for warp_type in path:
        if warp_type == "character":
            character_level += 1
            cost = _cost_pmf(
                character_pity if not used_character_start else 0,
                character_guaranteed if not used_character_start else False,
                90,
                0.5625,
                CHARACTER_DISTRIBUTION,
            )
            used_character_start = True
        else:
            cone_level += 1
            cost = _cost_pmf(
                light_cone_pity if not used_cone_start else 0,
                light_cone_guaranteed if not used_cone_start else False,
                80,
                0.78125,
                LIGHT_CONE_DISTRIBUTION,
            )
            used_cone_start = True
        cumulative = _convolve(cumulative, cost)
        chance = sum(cumulative[: min(budget + 1, len(cumulative))])
        expected = sum(index * probability for index, probability in enumerate(cumulative))
        label = (
            f"E{character_level} S{cone_level}"
            if character_level >= 0 else f"S{cone_level}"
        )
        results.append(PlannerMilestone(label, min(max(chance, 0.0), 1.0), expected))
    return tuple(results)


def calculate_planner(
    *,
    jades: int,
    passes: int,
    starlight: int,
    refund: str,
    character_pity: int,
    character_guaranteed: bool,
    light_cone_pity: int,
    light_cone_guaranteed: bool,
    strategy: str = "E2",
) -> PlannerResult:
    jade_warps = max(0, int(jades)) // 160
    starlight_warps = max(0, int(starlight)) // 20
    initial = jade_warps + max(0, int(passes)) + starlight_warps
    refunded = math.floor(REFUND_MULTIPLIERS.get(refund, 0.075) * initial)
    total = initial + refunded
    return PlannerResult(
        jade_warps=jade_warps,
        starlight_warps=starlight_warps,
        refunded_warps=refunded,
        total_warps=total,
        character=_projection(
            total, character_pity, character_guaranteed, 90, 0.5625,
            CHARACTER_DISTRIBUTION,
        ),
        light_cone=_projection(
            total, light_cone_pity, light_cone_guaranteed, 80, 0.78125,
            LIGHT_CONE_DISTRIBUTION,
        ),
        milestones=_milestones(
            total,
            strategy,
            character_pity,
            character_guaranteed,
            light_cone_pity,
            light_cone_guaranteed,
        ),
    )
