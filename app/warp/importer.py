from __future__ import annotations

import html
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal

from app.warp.models import WarpRecord
from app.warp.starrailstation import import_starrailstation_xlsx


GACHA_TYPES = ("11", "12", "1", "2", "21", "22")
DEFAULT_CACHE_ROOTS = tuple(
    root
    for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ"
    for root in (
        Path(fr"{drive}:\Program Files\Star Rail\Games\StarRail_Data\webCaches"),
        Path(fr"{drive}:\Program Files\Star Rail\Games\StarRail\_Data\webCaches"),
        Path(fr"{drive}:\Program Files\HoYoPlay\games\Star Rail Games\StarRail_Data\webCaches"),
        Path(fr"{drive}:\Star Rail\Games\StarRail_Data\webCaches"),
    )
)
URL_PATTERN = re.compile(r"https?://[^\x00\s\"'<>]+", re.IGNORECASE)


def cache_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    patterns = ("*/Cache/Cache_Data/data_*", "*/Cache/Cache/_Data/data_*")
    found: list[Path] = []
    for pattern in patterns:
        found.extend(path for path in root.glob(pattern) if path.is_file())
    return found


def find_latest_cache(extra_roots: tuple[Path, ...] = ()) -> Path | None:
    candidates: list[Path] = []
    for root in (*extra_roots, *DEFAULT_CACHE_ROOTS):
        candidates.extend(cache_files(root))
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for path in candidates:
        if extract_warp_url(path):
            return path
    return None


def extract_warp_url(path: Path) -> str:
    try:
        text = path.read_bytes().decode("utf-8", errors="ignore")
    except OSError:
        return ""
    text = html.unescape(text.replace(r"\u0026", "&").replace(r"\/", "/"))
    urls = []
    for match in URL_PATTERN.findall(text):
        candidate = match.rstrip("\\,]} )")
        if "getGachaLog" not in candidate or "authkey=" not in candidate:
            continue
        query = dict(parse_qsl(urlsplit(candidate).query, keep_blank_values=True))
        if query.get("authkey"):
            urls.append(candidate)
    return urls[-1] if urls else ""


def _page_url(base_url: str, gacha_type: str, page: int, end_id: str) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(
        gacha_type=gacha_type,
        page=str(page),
        size="20",
        end_id=end_id,
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def fetch_warp_history(base_url: str, progress=None) -> list[WarpRecord]:  # type: ignore[no-untyped-def]
    records: dict[tuple[str, str], WarpRecord] = {}
    for gacha_type in GACHA_TYPES:
        page = 1
        end_id = "0"
        while page <= 1000:
            if progress:
                progress(f"Lendo banner {gacha_type} · página {page}…")
            request = Request(
                _page_url(base_url, gacha_type, page, end_id),
                headers={"User-Agent": "AstralOptimizer/0.4"},
            )
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if int(payload.get("retcode", -1)) != 0:
                message = payload.get("message") or "A API recusou o link de Saltos."
                raise RuntimeError(str(message))
            items = (payload.get("data") or {}).get("list") or []
            if not items:
                break
            for item in items:
                record = WarpRecord.from_api(item)
                if record.id:
                    records[(record.uid, record.id)] = record
            last_id = str(items[-1].get("id", ""))
            if not last_id or last_id == end_id or len(items) < 20:
                break
            end_id = last_id
            page += 1
    return list(records.values())


class WarpImportWorker(QThread):
    progress = Signal(str)
    succeeded = Signal(object, str)
    failed = Signal(str)

    def __init__(self, cache_path: Path | None = None, target_uid: str = "") -> None:
        super().__init__()
        self.cache_path = cache_path
        self.target_uid = target_uid

    def run(self) -> None:
        try:
            path = self.cache_path or find_latest_cache()
            if path is None:
                raise RuntimeError(
                    "Cache de Saltos não encontrado. Abra o histórico de Saltos no jogo "
                    "e tente novamente."
                )
            if path.suffix.casefold() == ".xlsx":
                self.progress.emit(f"Lendo backup do Star Rail Station: {path.name}")
                result = import_starrailstation_xlsx(path, self.target_uid)
                self.succeeded.emit(result, str(path))
                return
            self.progress.emit(f"Cache encontrado: {path.name}")
            url = extract_warp_url(path)
            if not url:
                raise RuntimeError(
                    "O arquivo não contém um link válido. Abra o histórico de Saltos no jogo."
                )
            records = fetch_warp_history(url, self.progress.emit)
            self.succeeded.emit(records, str(path))
        except Exception as error:
            self.failed.emit(str(error))
