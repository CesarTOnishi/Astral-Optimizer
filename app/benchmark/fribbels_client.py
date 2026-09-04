from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from app.models import CharacterSummary


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = PROJECT_ROOT / "third_party" / "fribbels-hsr-optimizer"
ENGINE_SCRIPT = ENGINE_ROOT / ".honkai-engine" / "benchmark-engine.js"


class FribbelsError(RuntimeError):
    pass


def engine_available() -> bool:
    return ENGINE_SCRIPT.is_file()


def _node_executable() -> str:
    bundled = PROJECT_ROOT / "runtime" / ("node.exe" if os.name == "nt" else "node")
    if bundled.is_file():
        return str(bundled)
    executable = shutil.which("node")
    if executable is None:
        raise FribbelsError("Node.js não foi encontrado no computador.")
    return executable


def _hidden_process_options() -> dict[str, Any]:
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startupinfo,
    }


def calculate(
    character: CharacterSummary,
    timeout: int = 180,
    teammates: list[dict[str, object]] | None = None,
) -> dict[str, Any]:
    if not engine_available():
        raise FribbelsError("O motor Fribbels ainda não foi compilado.")
    payload = character.raw.get("fribbels_payload")
    if not isinstance(payload, dict):
        raise FribbelsError("Recarregue o UID para obter os dados brutos da build.")
    request_payload: dict[str, object] = {
        "id": str(character.avatar_id), "character": payload,
    }
    if teammates is not None:
        request_payload["teammates"] = teammates
    request = json.dumps(
        request_payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    try:
        completed = subprocess.run(
            [_node_executable(), str(ENGINE_SCRIPT)],
            cwd=ENGINE_ROOT,
            input=request + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
            **_hidden_process_options(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FribbelsError(f"Falha ao executar o motor Fribbels: {exc}") from exc
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        detail = completed.stderr.strip() or f"processo finalizado com código {completed.returncode}"
        raise FribbelsError(detail)
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise FribbelsError("O motor Fribbels retornou uma resposta inválida.") from exc
    if not result.get("ok"):
        raise FribbelsError(str(result.get("error") or "Erro desconhecido no Fribbels."))
    return result


class FribbelsBenchmarkWorker(QThread):
    succeeded = Signal(str, object)
    failed = Signal(str, str)

    def __init__(
        self,
        character: CharacterSummary,
        teammates: list[dict[str, object]] | None = None,
        request_key: str | None = None,
    ) -> None:
        super().__init__()
        self.character = character
        self.teammates = teammates
        self.request_key = request_key or str(character.avatar_id)

    def run(self) -> None:
        try:
            result = calculate(self.character, teammates=self.teammates)
        except Exception as exc:
            self.failed.emit(self.request_key, str(exc))
        else:
            self.succeeded.emit(self.request_key, result)
