from __future__ import annotations

from collections.abc import Callable
import hashlib
from pathlib import Path
import re

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from app.paths import app_data_dir


class ImageLoader(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)
        self.cache: dict[str, QPixmap] = {}
        self.pending: dict[str, list[Callable[[QPixmap], None]]] = {}
        self.replies: dict[QNetworkReply, str] = {}
        self.disk_cache = app_data_dir() / "image_cache"
        self.disk_cache.mkdir(parents=True, exist_ok=True)

    def load(self, url: str, callback: Callable[[QPixmap], None]) -> None:
        if not url:
            callback(QPixmap())
            return
        if url in self.cache:
            callback(self.cache[url])
            return
        cached_path = self._disk_cache_path(url)
        if cached_path.is_file():
            cached = QPixmap(str(cached_path))
            if not cached.isNull():
                self.cache[url] = cached
                callback(cached)
                return
        if url in self.pending:
            self.pending[url].append(callback)
            return

        self.pending[url] = [callback]
        reply = self.network.get(QNetworkRequest(QUrl(url)))
        self.replies[reply] = url
        reply.finished.connect(lambda: self._finished(reply))

    def _finished(self, reply: QNetworkReply) -> None:
        url = self.replies.pop(reply, "")
        pixmap = QPixmap()
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = bytes(reply.readAll())
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                try:
                    self._disk_cache_path(url).write_bytes(data)
                except OSError:
                    pass
        if pixmap.isNull():
            fallback = self._profile_icon_fallback(url)
            if fallback is not None:
                pixmap.load(str(fallback))
        reply.deleteLater()
        if not pixmap.isNull():
            self.cache[url] = pixmap
        for callback in self.pending.pop(url, []):
            try:
                callback(pixmap)
            except RuntimeError:
                # O cartão pode ter sido removido enquanto a imagem era baixada.
                continue

    def _disk_cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.disk_cache / f"{digest}.img"

    @staticmethod
    def _profile_icon_fallback(url: str) -> Path | None:
        """Resolve avatares novos que ainda não foram publicados no CDN do Enka."""
        match = re.search(
            r"/AvatarRoundIcon/Avatar/(\d+)\.png(?:\?.*)?$",
            url,
            flags=re.IGNORECASE,
        )
        if match is None:
            return None
        asset = (
            Path(__file__).resolve().parents[2]
            / "third_party"
            / "fribbels-hsr-optimizer"
            / "public"
            / "assets"
            / "icon"
            / "avatar"
            / f"{match.group(1)}.webp"
        )
        return asset if asset.is_file() else None
