from __future__ import annotations

import os
from pathlib import Path
import shutil


def app_data_dir() -> Path:
    configured = os.environ.get("ASTRAL_DATA_DIR") or os.environ.get("HONKAI_DATA_DIR")
    if configured:
        return Path(configured)
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    current = base / "AstralOptimizer"
    legacy = base / "HonkaiBuilds"
    if not current.exists() and legacy.exists():
        current.mkdir(parents=True, exist_ok=True)
        for name in ("accounts.db", "warps.db", "google_oauth_client.json"):
            source = legacy / name
            target = current / name
            if source.is_file() and not target.exists():
                shutil.copy2(source, target)
    current.mkdir(parents=True, exist_ok=True)
    return current
