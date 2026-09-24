from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabBar,
    QVBoxLayout,
)

from app.ui.icons import set_button_icon


def updated_at_text(value: str) -> str:
    if not value:
        return "Ainda não atualizado"
    try:
        parsed = datetime.fromisoformat(value)
        local = parsed.astimezone()
    except ValueError:
        return "Última atualização indisponível"
    return f"Atualizado em {local:%d/%m/%Y às %H:%M}"


class UidTabBar(QTabBar):
    order_changed = Signal(object)

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setObjectName("uidTabBar")
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setDocumentMode(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setExpanding(False)
        self.setIconSize(QSize(24, 24))
        self.setUsesScrollButtons(True)
        self.tabMoved.connect(lambda _from, _to: self.order_changed.emit(self.uids()))

    def uids(self) -> list[str]:
        return [str(self.tabData(index) or "") for index in range(self.count())]

    def index_for_uid(self, uid: str) -> int:
        for index in range(self.count()):
            if self.tabData(index) == uid:
                return index
        return -1

    def add_uid(self, uid: str, title: str, icon: QIcon | None = None) -> int:
        existing = self.index_for_uid(uid)
        if existing >= 0:
            self.setTabText(existing, title)
            if icon is not None:
                self.setTabIcon(existing, icon)
            return existing
        index = self.addTab(icon or QIcon(), title)
        self.setTabData(index, uid)
        self.setTabToolTip(index, f"UID {uid}")
        return index


class UidTabsWidget(QFrame):
    selected = Signal(str)
    close_requested = Signal(str)
    refresh_requested = Signal(str)
    order_changed = Signal(object)

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setObjectName("uidTabsPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(5)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.tabs = UidTabBar()
        self.tabs.currentChanged.connect(self._emit_selected)
        self.tabs.tabCloseRequested.connect(self._emit_close)
        self.tabs.order_changed.connect(self.order_changed.emit)
        row.addWidget(self.tabs, 1)

        self.refresh_button = QPushButton("")
        self.refresh_button.setObjectName("uidTabRefreshButton")
        self.refresh_button.setFixedSize(34, 34)
        self.refresh_button.setToolTip("Atualizar somente esta UID")
        set_button_icon(self.refresh_button, "refresh", 16)
        self.refresh_button.clicked.connect(self._emit_refresh)
        row.addWidget(self.refresh_button)
        layout.addLayout(row)

        self.meta_label = QLabel("Selecione uma aba")
        self.meta_label.setObjectName("uidTabMeta")
        layout.addWidget(self.meta_label)

    @property
    def current_uid(self) -> str:
        index = self.tabs.currentIndex()
        return str(self.tabs.tabData(index) or "") if index >= 0 else ""

    def add_or_update(self, uid: str, title: str, avatar: QPixmap | None = None) -> int:
        icon = QIcon(avatar) if avatar is not None and not avatar.isNull() else None
        return self.tabs.add_uid(uid, title, icon)

    def update_avatar(self, uid: str, pixmap: QPixmap) -> None:
        index = self.tabs.index_for_uid(uid)
        if index >= 0 and not pixmap.isNull():
            self.tabs.setTabIcon(index, QIcon(pixmap))

    def set_current_uid(self, uid: str, *, emit: bool = True) -> bool:
        index = self.tabs.index_for_uid(uid)
        if index < 0:
            return False
        previous = self.tabs.blockSignals(not emit)
        self.tabs.setCurrentIndex(index)
        self.tabs.blockSignals(previous)
        return True

    def remove_uid(self, uid: str) -> None:
        index = self.tabs.index_for_uid(uid)
        if index >= 0:
            self.tabs.removeTab(index)

    def set_session_status(
        self, *, updated_at: str = "", loading: bool = False, error: str = ""
    ) -> None:
        if loading:
            self.meta_label.setText("Atualizando esta UID… os dados anteriores continuam disponíveis.")
            self.meta_label.setProperty("state", "loading")
        elif error:
            preserved = " Dados salvos preservados." if updated_at else ""
            self.meta_label.setText(f"Falha na atualização.{preserved}")
            self.meta_label.setProperty("state", "error")
        else:
            self.meta_label.setText(updated_at_text(updated_at))
            self.meta_label.setProperty("state", "ready" if updated_at else "empty")
        self.meta_label.style().unpolish(self.meta_label)
        self.meta_label.style().polish(self.meta_label)
        self.refresh_button.setEnabled(not loading and bool(self.current_uid))

    def _emit_selected(self, index: int) -> None:
        if index >= 0:
            self.selected.emit(str(self.tabs.tabData(index) or ""))

    def _emit_close(self, index: int) -> None:
        if index >= 0:
            self.close_requested.emit(str(self.tabs.tabData(index) or ""))

    def _emit_refresh(self) -> None:
        if self.current_uid:
            self.refresh_requested.emit(self.current_uid)
