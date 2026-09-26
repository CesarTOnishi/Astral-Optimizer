"""Keep one Astral Optimizer process per local data directory."""

from __future__ import annotations

import hashlib
import sys
import time

from PySide6.QtCore import QLockFile, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from app.paths import app_data_dir


ACTIVATE = b"ACTIVATE\n"


def server_name() -> str:
    """Use a stable, short name shared by launches of this user's installation."""
    data_path = str(app_data_dir().resolve())
    if sys.platform == "win32":
        data_path = data_path.casefold()
    digest = hashlib.sha256(data_path.encode("utf-8")).hexdigest()[:24]
    return f"AstralOptimizer-{digest}"


class SingleInstance(QObject):
    activation_requested = Signal()

    def __init__(self, name: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.name = name or server_name()
        self.lock = QLockFile(str(app_data_dir() / f".{self.name}.lock"))
        self.server: QLocalServer | None = None

    def start_or_activate(self) -> bool:
        """Return True only for the process that owns the local server."""
        if not self.lock.tryLock(0):
            if self.lock.error() == QLockFile.LockError.PermissionError:
                raise RuntimeError(
                    "Não foi possível acessar o bloqueio da instância do Astral Optimizer."
                )
            # The first process might still be constructing its window or
            # temporarily busy. Never create a second UI while it owns the lock.
            for _attempt in range(20):
                if self._notify_existing(timeout_ms=200):
                    return False
                time.sleep(0.05)
            raise RuntimeError(
                "O Astral Optimizer já está aberto, mas não respondeu ao pedido "
                "para mostrar a janela. Tente novamente em alguns segundos."
            )
        server = QLocalServer(self)
        if server.listen(self.name):
            self._use_server(server)
            return True
        # A crashed Unix process can leave its local socket path behind.
        if sys.platform != "win32" and QLocalServer.removeServer(self.name):
            if server.listen(self.name):
                self._use_server(server)
                return True

        message = server.errorString()
        server.deleteLater()
        self.lock.unlock()
        raise RuntimeError(
            f"Não foi possível confirmar a instância ativa do Astral Optimizer: {message}"
        )

    def _use_server(self, server: QLocalServer) -> None:
        self.server = server
        server.newConnection.connect(self._accept_connections)

    def _notify_existing(self, timeout_ms: int = 150) -> bool:
        socket = QLocalSocket(self)
        try:
            socket.connectToServer(self.name)
            if not socket.waitForConnected(timeout_ms):
                return False
            if socket.write(ACTIVATE) < 0:
                return False
            socket.flush()
            if socket.bytesToWrite() and not socket.waitForBytesWritten(timeout_ms):
                return False
            socket.disconnectFromServer()
            return True
        finally:
            socket.close()
            socket.deleteLater()

    def _accept_connections(self) -> None:
        if self.server is None:
            return
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if socket is None:
                continue
            socket.readyRead.connect(lambda current=socket: self._read_command(current))
            # Keep the accepted socket owned by the server. Deleting it from
            # its disconnect callback can invalidate queued Qt events on Windows.
            self._read_command(socket)

    def _read_command(self, socket: QLocalSocket) -> None:
        if socket.property("astralActivated") or not socket.canReadLine():
            return
        command = bytes(socket.readLine()).strip()
        if command == ACTIVATE.strip():
            socket.setProperty("astralActivated", True)
            self.activation_requested.emit()

    def close(self) -> None:
        if self.server is not None:
            self.server.close()
            self.server = None
        if self.lock.isLocked():
            self.lock.unlock()
