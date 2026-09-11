from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings


def warp_import_settings() -> QSettings:
    return QSettings("Astral Optimizer", "Warp Import")


def webcaches_path(settings: QSettings | None = None) -> Path | None:
    value = str((settings or warp_import_settings()).value("webcaches_path", "")).strip()
    return Path(value) if value else None


def set_webcaches_path(
    path: Path | None,
    settings: QSettings | None = None,
) -> None:
    target = settings or warp_import_settings()
    if path is None:
        target.remove("webcaches_path")
    else:
        target.setValue("webcaches_path", str(path.resolve()))
    target.sync()


def import_tutorial_seen(
    user_id: int,
    settings: QSettings | None = None,
) -> bool:
    if user_id <= 0:
        return False
    value = (settings or warp_import_settings()).value(
        f"profiles/{user_id}/import_tutorial_seen", False
    )
    if isinstance(value, str):
        return value.casefold() in {"1", "true", "yes", "on"}
    return bool(value)


def set_import_tutorial_seen(
    user_id: int,
    seen: bool = True,
    settings: QSettings | None = None,
) -> None:
    if user_id <= 0:
        return
    target = settings or warp_import_settings()
    target.setValue(f"profiles/{user_id}/import_tutorial_seen", seen)
    target.sync()
