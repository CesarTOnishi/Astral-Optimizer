from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any


IMPORT_REMINDER_DAYS = 40
MAX_REMINDER_DAYS = 365


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def reminder_interval_days(state: dict[str, Any]) -> int:
    try:
        days = int(state.get("interval_days", IMPORT_REMINDER_DAYS))
    except (TypeError, ValueError):
        days = IMPORT_REMINDER_DAYS
    return min(max(days, 1), MAX_REMINDER_DAYS)


def next_import_reminder_at(state: dict[str, Any]) -> datetime | None:
    chosen_day = state.get("next_due_on")
    if isinstance(chosen_day, str) and chosen_day:
        try:
            selected = date.fromisoformat(chosen_day)
        except ValueError:
            pass
        else:
            return datetime.combine(selected, time.min).astimezone(timezone.utc)
    dates = [
        _parse_date(state.get(key))
        for key in ("started_at", "last_imported_at", "last_reminded_at")
    ]
    latest = max((date for date in dates if date is not None), default=None)
    if latest is None:
        return None
    return latest + timedelta(days=reminder_interval_days(state))


def import_reminder_due(state: dict[str, Any], now: datetime | None = None) -> bool:
    due_at = next_import_reminder_at(state)
    if due_at is None:
        return False
    current = now or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc) >= due_at
