from __future__ import annotations

from dataclasses import dataclass

from app.warp.models import WarpRecord


@dataclass(frozen=True, slots=True)
class WarpImportPreview:
    new_count: int
    duplicate_count: int
    rejected_count: int
    valid_records: tuple[WarpRecord, ...]


def preview_warp_import(
    records: list[object],
    existing_keys: set[tuple[str, str]],
    *,
    rejected_count: int = 0,
    duplicate_count: int = 0,
) -> WarpImportPreview:
    seen = set(existing_keys)
    valid: list[WarpRecord] = []
    new = 0
    duplicates = duplicate_count
    rejected = rejected_count
    for item in records:
        if not isinstance(item, WarpRecord) or not item.uid or not item.id:
            rejected += 1
            continue
        valid.append(item)
        key = (item.uid, item.id)
        if key in seen:
            duplicates += 1
        else:
            new += 1
            seen.add(key)
    return WarpImportPreview(new, duplicates, rejected, tuple(valid))
