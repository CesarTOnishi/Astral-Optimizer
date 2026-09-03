from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models import CharacterSummary


DEFAULT_CRIT_WEIGHTS = {
    "AttackDelta": 0.30,
    "AttackAddedRatio": 0.75,
    "SpeedDelta": 1.0,
    "CriticalChance": 1.0,
    "CriticalDamage": 1.0,
}


@lru_cache(maxsize=1)
def load_profiles() -> dict[str, dict[str, Any]]:
    path = Path(__file__).with_name("fribbels_weights.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("characters", {})
    except (OSError, ValueError, TypeError):
        return {}


def scoring_profile(character: CharacterSummary) -> dict[str, Any]:
    profile = load_profiles().get(str(character.avatar_id))
    if profile:
        return profile
    return {
        "name": character.name,
        "weights": DEFAULT_CRIT_WEIGHTS,
        "main_stats": {},
    }
