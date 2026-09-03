from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from app.auth import AuthUser
from app.paths import app_data_dir


DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.appdata"
IDENTITY_SCOPES = ("openid", "https://www.googleapis.com/auth/userinfo.email")
TOKEN_SERVICE = "Astral Optimizer Google Drive"


def _data_dir() -> Path:
    return app_data_dir()


def google_credentials_path() -> Path:
    configured = os.environ.get("ASTRAL_GOOGLE_CREDENTIALS")
    if configured:
        return Path(configured)
    local = _data_dir() / "google_oauth_client.json"
    if local.exists():
        return local
    return Path(__file__).resolve().parents[2] / "google_oauth_client.json"


def install_google_credentials(source: Path) -> Path:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        installed = payload["installed"]
        if not installed.get("client_id") or not installed.get("auth_uri"):
            raise KeyError("client_id")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, AttributeError) as error:
        raise ValueError("Selecione um OAuth JSON do tipo Aplicativo para computador.") from error
    target = _data_dir() / "google_oauth_client.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return target


class GoogleDriveService:
    def __init__(self, user: AuthUser) -> None:
        self.user = user
        identity = user.email.strip().casefold() or user.username.strip().casefold()
        self.profile_key = sha256(identity.encode("utf-8")).hexdigest()[:24]
        self.backup_name = f"astral-optimizer-{self.profile_key}.json"

    @staticmethod
    def available() -> bool:
        try:
            import google_auth_oauthlib.flow  # noqa: F401
            import googleapiclient.discovery  # noqa: F401
            import keyring  # noqa: F401
        except ImportError:
            return False
        return google_credentials_path().is_file()

    def connected_email(self) -> str:
        bundle = self._load_bundle()
        return str(bundle.get("email", "")) if bundle else ""

    def connect(self) -> str:
        credentials_path = google_credentials_path()
        if not credentials_path.is_file():
            raise RuntimeError(
                "OAuth do Google não configurado. Adicione google_oauth_client.json."
            )
        try:
            from google.auth.transport.requests import AuthorizedSession
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as error:
            raise RuntimeError(
                "Instale as dependências do Google Drive pelo requirements.txt."
            ) from error
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), [DRIVE_SCOPE, *IDENTITY_SCOPES]
        )
        credentials = flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=True,
            authorization_prompt_message="Abrindo o Google para conectar o Drive…",
            success_message="Google Drive conectado. Você pode fechar esta janela.",
        )
        response = AuthorizedSession(credentials).get(
            "https://openidconnect.googleapis.com/v1/userinfo", timeout=20
        )
        response.raise_for_status()
        email = str(response.json().get("email", ""))
        self._save_bundle({"email": email, "credentials": credentials.to_json()})
        return email

    def disconnect(self) -> str:
        credentials = self._credentials()
        if credentials is not None:
            try:
                import requests

                token = credentials.refresh_token or credentials.token
                if token:
                    requests.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": token},
                        timeout=15,
                    )
            except Exception:
                pass
        self._delete_bundle()
        return "Google Drive desconectado."

    def upload_backup(self, payload: dict[str, Any]) -> str:
        credentials = self._require_credentials()
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseUpload
        except ImportError as error:
            raise RuntimeError("Dependências do Google Drive não instaladas.") from error
        document = dict(payload)
        document["app"] = "Astral Optimizer"
        document["profile"] = self.user.username
        document["updated_at"] = datetime.now(timezone.utc).isoformat()
        data = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        media = MediaIoBaseUpload(BytesIO(data), mimetype="application/json")
        drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
        escaped = self.backup_name.replace("'", "\\'")
        result = drive.files().list(
            spaces="appDataFolder",
            q=f"name = '{escaped}' and trashed = false",
            fields="files(id,name)",
            pageSize=1,
        ).execute()
        files = result.get("files", [])
        if files:
            drive.files().update(fileId=files[0]["id"], media_body=media).execute()
        else:
            drive.files().create(
                body={"name": self.backup_name, "parents": ["appDataFolder"]},
                media_body=media,
                fields="id",
            ).execute()
        return "Backup salvo no Google Drive."

    def download_backup(self) -> dict[str, Any]:
        credentials = self._require_credentials()
        try:
            from googleapiclient.discovery import build
        except ImportError as error:
            raise RuntimeError("Dependências do Google Drive não instaladas.") from error
        drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
        escaped = self.backup_name.replace("'", "\\'")
        result = drive.files().list(
            spaces="appDataFolder",
            q=f"name = '{escaped}' and trashed = false",
            fields="files(id,name,modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=1,
        ).execute()
        files = result.get("files", [])
        if not files:
            raise RuntimeError("Nenhum backup deste perfil foi encontrado no Drive.")
        raw = drive.files().get_media(fileId=files[0]["id"]).execute()
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("O backup encontrado é inválido.")
        return payload

    def _require_credentials(self):  # type: ignore[no-untyped-def]
        credentials = self._credentials()
        if credentials is None:
            raise RuntimeError("Conecte uma conta Google primeiro.")
        if credentials.expired and credentials.refresh_token:
            from google.auth.transport.requests import Request

            credentials.refresh(Request())
            bundle = self._load_bundle() or {}
            self._save_bundle(
                {
                    "email": bundle.get("email", ""),
                    "credentials": credentials.to_json(),
                }
            )
        return credentials

    def _credentials(self):  # type: ignore[no-untyped-def]
        bundle = self._load_bundle()
        if not bundle:
            return None
        try:
            from google.oauth2.credentials import Credentials

            return Credentials.from_authorized_user_info(
                json.loads(str(bundle["credentials"])),
                [DRIVE_SCOPE, *IDENTITY_SCOPES],
            )
        except (ImportError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _load_bundle(self) -> dict[str, Any] | None:
        try:
            import keyring

            value = keyring.get_password(TOKEN_SERVICE, self.profile_key)
            payload = json.loads(value) if value else None
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def _save_bundle(self, payload: dict[str, Any]) -> None:
        import keyring

        keyring.set_password(
            TOKEN_SERVICE, self.profile_key, json.dumps(payload, ensure_ascii=False)
        )

    def _delete_bundle(self) -> None:
        try:
            import keyring

            keyring.delete_password(TOKEN_SERVICE, self.profile_key)
        except Exception:
            pass


class GoogleDriveWorker(QThread):
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
