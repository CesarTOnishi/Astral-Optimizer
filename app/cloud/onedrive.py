from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, QThread, Signal

from app.auth import AuthUser


BACKUP_FORMAT = 1


def onedrive_settings() -> QSettings:
    return QSettings("Astral Optimizer", "OneDrive Backup")


def configured_backup_folder(settings: QSettings | None = None) -> Path | None:
    value = str((settings or onedrive_settings()).value("backup_folder", "")).strip()
    return Path(value) if value else None


def set_backup_folder(
    path: Path | None,
    settings: QSettings | None = None,
) -> None:
    target = settings or onedrive_settings()
    if path is None:
        target.remove("backup_folder")
    else:
        target.setValue("backup_folder", str(path.resolve()))
    target.sync()


def detected_onedrive_roots(
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    values = environ or os.environ
    roots: list[Path] = []
    for key in ("OneDriveConsumer", "OneDrive", "OneDriveCommercial"):
        value = values.get(key, "").strip()
        path = Path(value) if value else None
        if path and path.is_dir() and path not in roots:
            roots.append(path)
    return tuple(roots)


def automatic_backup_folder() -> Path | None:
    roots = detected_onedrive_roots()
    return roots[0] / "Astral Optimizer" / "Backups" if roots else None


class OneDriveBackupService:
    def __init__(self, user: AuthUser, folder: Path | None = None) -> None:
        self.user = user
        self.folder = folder or configured_backup_folder() or automatic_backup_folder()
        identity = user.email.strip().casefold() or user.username.strip().casefold()
        self.profile_key = sha256(identity.encode("utf-8")).hexdigest()[:24]

    @property
    def available(self) -> bool:
        return self.folder is not None

    def backup_files(self) -> list[Path]:
        if self.folder is None or not self.folder.is_dir():
            return []
        pattern = f"astral-optimizer-{self.profile_key}-*.astralbackup"
        return sorted(
            (path for path in self.folder.glob(pattern) if path.is_file()),
            key=lambda path: (path.stat().st_mtime, path.name),
            reverse=True,
        )

    def save_backup(self, payload: dict[str, Any]) -> str:
        if self.folder is None:
            raise RuntimeError(
                "OneDrive não encontrado. Selecione uma pasta sincronizada nas Configurações."
            )
        self.folder.mkdir(parents=True, exist_ok=True)
        serialized_payload = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        timestamp = datetime.now(timezone.utc)
        document = {
            "format": BACKUP_FORMAT,
            "app": "Astral Optimizer",
            "profile_key": self.profile_key,
            "created_at": timestamp.isoformat(),
            "checksum": sha256(serialized_payload.encode("utf-8")).hexdigest(),
            "payload": payload,
        }
        filename = (
            f"astral-optimizer-{self.profile_key}-"
            f"{timestamp.strftime('%Y%m%d-%H%M%S-%f')}.astralbackup"
        )
        destination = self.folder / filename
        temporary = destination.with_suffix(".tmp")
        try:
            temporary.write_text(
                json.dumps(document, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary, destination)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Não foi possível salvar no OneDrive: {error}") from error
        return f"Backup salvo no OneDrive: {destination.name}"

    def load_latest_backup(self) -> dict[str, Any]:
        files = self.backup_files()
        if not files:
            raise RuntimeError("Nenhum backup deste perfil foi encontrado no OneDrive.")
        errors: list[str] = []
        for path in files:
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                payload = document["payload"]
                if document.get("format") != BACKUP_FORMAT or not isinstance(payload, dict):
                    raise ValueError("formato incompatível")
                serialized = json.dumps(
                    payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                checksum = sha256(serialized.encode("utf-8")).hexdigest()
                if checksum != document.get("checksum"):
                    raise ValueError("verificação de integridade falhou")
                return payload
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                errors.append(f"{path.name}: {error}")
        raise RuntimeError("Os backups encontrados estão inválidos. " + "; ".join(errors))

    def status_text(self) -> str:
        if self.folder is None:
            return "OneDrive não detectado. Selecione uma pasta sincronizada."
        files = self.backup_files()
        if not files:
            return f"Pasta: {self.folder} · nenhum backup deste perfil."
        modified = datetime.fromtimestamp(files[0].stat().st_mtime).strftime("%d/%m/%Y %H:%M")
        return f"Pasta: {self.folder} · {len(files)} backup(s) · último em {modified}."


class OneDriveWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, operation: Callable[[], object]) -> None:
        super().__init__()
        self.operation = operation

    def run(self) -> None:
        try:
            result = self.operation()
        except Exception as error:
            self.failed.emit(str(error))
            return
        self.succeeded.emit(result)
