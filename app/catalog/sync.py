from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal

from app.paths import app_data_dir


CATALOG_FILES = (
    "characters.json",
    "character_skills.json",
    "character_ranks.json",
    "character_skill_trees.json",
    "character_promotions.json",
    "light_cones.json",
    "light_cone_ranks.json",
    "light_cone_promotions.json",
    "paths.json",
    "elements.json",
)
REPOSITORY = "Mar-7th/StarRailRes"
API_COMMIT_URL = f"https://api.github.com/repos/{REPOSITORY}/commits/master"


def catalog_cache_dir() -> Path:
    path = app_data_dir() / "catalog" / "pt"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _download_json(url: str) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "Astral-Optimizer/1.0"})
    with urlopen(request, timeout=35) as response:  # noqa: S310 - fonte fixa HTTPS
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("A fonte retornou um catálogo inválido.")
    return payload


def synchronize_catalog(progress: Callable[[str], None] | None = None) -> str:
    notify = progress or (lambda _message: None)
    notify("Verificando a versão mais recente do catálogo…")
    commit = _download_json(API_COMMIT_URL)
    sha = str(commit.get("sha", "")).strip()
    if len(sha) != 40:
        raise ValueError("Não foi possível identificar a versão do StarRailRes.")

    target = catalog_cache_dir()
    staging = target.parent / ".pt-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    base = f"https://raw.githubusercontent.com/{REPOSITORY}/{sha}/index_min/pt"
    try:
        for index, filename in enumerate(CATALOG_FILES, start=1):
            notify(f"Baixando dados do catálogo ({index}/{len(CATALOG_FILES)})…")
            payload = _download_json(f"{base}/{filename}")
            (staging / filename).write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
        metadata = {
            "source": REPOSITORY,
            "commit": sha,
            "language": "pt",
            "files": list(CATALOG_FILES),
        }
        (staging / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        for source in staging.iterdir():
            os.replace(source, target / source.name)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return sha


class CatalogSyncWorker(QThread):
    progress = Signal(str)
    succeeded = Signal(str)
    failed = Signal(str)

    def run(self) -> None:
        try:
            sha = synchronize_catalog(self.progress.emit)
        except Exception as error:  # noqa: BLE001 - erro exibido de forma amigável
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(sha)
