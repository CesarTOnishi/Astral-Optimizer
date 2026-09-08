from __future__ import annotations

from PySide6.QtCore import QSettings


def privacy_settings() -> QSettings:
    return QSettings("Astral Optimizer", "Privacy")


def _hide_uid_key(user_id: int) -> str:
    return f"profiles/{user_id}/hide_uid_in_shared_images"


def hide_uid_in_shared_images(
    user_id: int, settings: QSettings | None = None
) -> bool:
    if user_id <= 0:
        return False
    value = (settings or privacy_settings()).value(_hide_uid_key(user_id), False)
    if isinstance(value, str):
        return value.casefold() in {"1", "true", "yes", "on"}
    return bool(value)


def set_hide_uid_in_shared_images(
    user_id: int, hidden: bool, settings: QSettings | None = None
) -> None:
    if user_id <= 0:
        return
    target = settings or privacy_settings()
    target.setValue(_hide_uid_key(user_id), hidden)
    target.sync()
