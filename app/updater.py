from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

from PySide6.QtCore import QThread, Signal

from app.config import APP_USER_AGENT, APP_VERSION, GITHUB_REPOSITORY
from app.paths import app_data_dir


RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
MAX_DOWNLOAD_SIZE = 1_500_000_000
MAX_EXTRACTED_SIZE = 2_000_000_000


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    tag: str
    title: str
    notes: str
    page_url: str
    download_url: str = ""
    asset_name: str = ""
    checksum_url: str = ""


@dataclass(frozen=True, slots=True)
class PreparedUpdate:
    version: str
    source_dir: Path
    update_dir: Path


def normalized_version(value: str) -> tuple[int, ...]:
    match = re.search(r"\d+(?:\.\d+){0,3}", value.strip())
    if match is None:
        return ()
    return tuple(int(part) for part in match.group(0).split("."))


def is_newer_version(candidate: str, current: str = APP_VERSION) -> bool:
    candidate_parts = normalized_version(candidate)
    current_parts = normalized_version(current)
    if not candidate_parts or not current_parts:
        return False
    width = max(len(candidate_parts), len(current_parts))
    return candidate_parts + (0,) * (width - len(candidate_parts)) > (
        current_parts + (0,) * (width - len(current_parts))
    )


def _request_json(url: str, timeout: int = 15) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": APP_USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return {}
        raise UpdateError(f"GitHub respondeu com o código {error.code}.") from error
    except (URLError, OSError, ValueError) as error:
        raise UpdateError(f"Não foi possível consultar o GitHub: {error}") from error
    return payload if isinstance(payload, dict) else {}


def check_latest_release() -> ReleaseInfo | None:
    payload = _request_json(RELEASE_API)
    if not payload:
        return None
    tag = str(payload.get("tag_name", "")).strip()
    version = ".".join(str(part) for part in normalized_version(tag))
    if not version:
        return None

    assets = payload.get("assets", [])
    zip_asset: dict[str, Any] | None = None
    checksum_asset: dict[str, Any] | None = None
    if isinstance(assets, list):
        for value in assets:
            if not isinstance(value, dict):
                continue
            name = str(value.get("name", ""))
            lowered = name.casefold()
            if lowered.endswith((".sha256", ".sha256.txt")):
                checksum_asset = value
            elif lowered.endswith(".zip") and "astral" in lowered:
                zip_asset = value

    return ReleaseInfo(
        version=version,
        tag=tag,
        title=str(payload.get("name") or f"Astral Optimizer {tag}"),
        notes=str(payload.get("body") or "Correções e melhorias do Astral Optimizer."),
        page_url=str(payload.get("html_url") or ""),
        download_url=str(zip_asset.get("browser_download_url", "")) if zip_asset else "",
        asset_name=str(zip_asset.get("name", "")) if zip_asset else "",
        checksum_url=(
            str(checksum_asset.get("browser_download_url", ""))
            if checksum_asset else ""
        ),
    )


def _download(url: str, target: Path, maximum: int = MAX_DOWNLOAD_SIZE) -> None:
    request = Request(url, headers={"User-Agent": APP_USER_AGENT})
    try:
        with urlopen(request, timeout=45) as response, target.open("wb") as output:
            expected = int(response.headers.get("Content-Length", "0") or 0)
            if expected > maximum:
                raise UpdateError("O arquivo de atualização é maior que o limite permitido.")
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > maximum:
                    raise UpdateError("O arquivo de atualização excedeu o limite permitido.")
                output.write(chunk)
    except (HTTPError, URLError, OSError) as error:
        target.unlink(missing_ok=True)
        raise UpdateError(f"Falha ao baixar a atualização: {error}") from error


def _expected_checksum(url: str, directory: Path) -> str:
    if not url:
        return ""
    checksum_file = directory / "release.sha256"
    _download(url, checksum_file, maximum=1_000_000)
    match = re.search(r"\b[a-fA-F0-9]{64}\b", checksum_file.read_text("utf-8"))
    return match.group(0).lower() if match else ""


def _file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if len(entries) > 20_000:
            raise UpdateError("A atualização contém arquivos demais.")
        if sum(item.file_size for item in entries) > MAX_EXTRACTED_SIZE:
            raise UpdateError("A atualização descompactada excede o limite permitido.")
        for item in entries:
            path = PurePosixPath(item.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                raise UpdateError("O pacote de atualização contém um caminho inválido.")
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise UpdateError("Links simbólicos não são permitidos na atualização.")
        bundle.extractall(destination)


def _payload_root(staging: Path) -> Path:
    direct = staging / "AstralOptimizer.exe"
    if direct.is_file():
        return staging
    matches = list(staging.glob("*/AstralOptimizer.exe"))
    if len(matches) != 1:
        raise UpdateError("O ZIP não contém uma distribuição válida do aplicativo.")
    return matches[0].parent


def prepare_update(release: ReleaseInfo) -> PreparedUpdate:
    if not release.download_url:
        raise UpdateError("Esta Release não possui o ZIP do Astral Optimizer.")
    update_root = app_data_dir() / "updates" / f"v{release.version}"
    if update_root.exists():
        shutil.rmtree(update_root)
    update_root.mkdir(parents=True, exist_ok=True)
    archive = update_root / (release.asset_name or "AstralOptimizer.zip")
    _download(release.download_url, archive)

    expected = _expected_checksum(release.checksum_url, update_root)
    actual = _file_checksum(archive)
    if expected and actual != expected:
        raise UpdateError("A assinatura SHA-256 da atualização não confere.")

    staging = update_root / "staging"
    staging.mkdir()
    try:
        _safe_extract(archive, staging)
        source = _payload_root(staging)
    except (OSError, zipfile.BadZipFile) as error:
        raise UpdateError(f"Não foi possível extrair a atualização: {error}") from error
    return PreparedUpdate(release.version, source, update_root)


def running_from_bundle() -> bool:
    return bool(getattr(sys, "frozen", False))


def launch_installer(update: PreparedUpdate) -> None:
    if os.name != "nt" or not running_from_bundle():
        raise UpdateError("A instalação automática está disponível no executável Windows.")
    install_dir = Path(sys.executable).resolve().parent
    executable = install_dir / "AstralOptimizer.exe"
    if not executable.is_file() or not (update.source_dir / executable.name).is_file():
        raise UpdateError("Não foi possível confirmar a pasta de instalação.")

    script = update.update_dir / "apply-update.ps1"
    script.write_text(
        "param([int]$AppProcessId, [string]$Source, [string]$Target, "
        "[string]$Executable)\n"
        "$ErrorActionPreference = 'Stop'\n"
        "Wait-Process -Id $AppProcessId -ErrorAction SilentlyContinue\n"
        "Start-Sleep -Milliseconds 700\n"
        "& robocopy.exe $Source $Target /E /R:5 /W:1 /NFL /NDL /NJH /NJS /NP\n"
        "if ($LASTEXITCODE -gt 7) { exit $LASTEXITCODE }\n"
        "Start-Process -FilePath (Join-Path $Target $Executable) "
        "-WorkingDirectory $Target\n"
        "$cleanupRoot = Split-Path -Parent $PSCommandPath\n"
        "Start-Sleep -Milliseconds 700\n"
        "Remove-Item -LiteralPath $cleanupRoot -Recurse -Force "
        "-ErrorAction SilentlyContinue\n",
        encoding="utf-8-sig",
    )
    flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden", "-File", str(script),
            "-AppProcessId", str(os.getpid()), "-Source", str(update.source_dir),
            "-Target", str(install_dir), "-Executable", executable.name,
        ],
        creationflags=flags,
        close_fds=True,
    )


class UpdateCheckWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        try:
            self.succeeded.emit(check_latest_release())
        except Exception as error:
            self.failed.emit(str(error))


class UpdateDownloadWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, release: ReleaseInfo) -> None:
        super().__init__()
        self.release = release

    def run(self) -> None:
        try:
            self.succeeded.emit(prepare_update(self.release))
        except Exception as error:
            self.failed.emit(str(error))
