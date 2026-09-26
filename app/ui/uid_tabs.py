from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QEasingCurve, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import set_button_icon
from app.preferences import reduce_motion_enabled, themed_color


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
        self.setMinimumHeight(46)
        self.setIconSize(QSize(24, 24))
        self.setUsesScrollButtons(True)
        self._indicator = QRectF()
        self._indicator_animation = QVariantAnimation(self)
        self._indicator_animation.setDuration(280)
        self._indicator_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._indicator_animation.valueChanged.connect(self._set_indicator)
        self.currentChanged.connect(self._animate_indicator)
        self.tabMoved.connect(self._tab_moved)

    def _indicator_target(self) -> QRectF:
        index = self.currentIndex()
        if index < 0:
            return QRectF()
        tab = self.tabRect(index)
        if not tab.isValid():
            return QRectF()
        return QRectF(tab.left() + 8, tab.bottom() - 2, max(0, tab.width() - 16), 3)

    def _set_indicator(self, rect: QRectF) -> None:
        self._indicator = QRectF(rect)
        self.update()

    def sync_indicator(self) -> None:
        self._indicator_animation.stop()
        self._set_indicator(self._indicator_target())

    def _animate_indicator(self, _index: int) -> None:
        target = self._indicator_target()
        if reduce_motion_enabled() or not self.isVisible() or self._indicator.isEmpty() or target.isEmpty():
            self.sync_indicator()
            return
        start = QRectF(self._indicator)
        self._indicator_animation.stop()
        self._indicator_animation.setDuration(280)
        self._indicator_animation.setStartValue(start)
        self._indicator_animation.setEndValue(target)
        self._indicator_animation.start()

    def _tab_moved(self, _from: int, _to: int) -> None:
        self.sync_indicator()
        self.order_changed.emit(self.uids())

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        self.sync_indicator()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        if self._indicator_animation.state() == QVariantAnimation.State.Running:
            target = self._indicator_target()
            if target.isEmpty():
                self.sync_indicator()
                return
            remaining = max(
                90,
                self._indicator_animation.duration() - self._indicator_animation.currentTime(),
            )
            start = QRectF(self._indicator)
            self._indicator_animation.stop()
            self._indicator_animation.setDuration(remaining)
            self._indicator_animation.setStartValue(start)
            self._indicator_animation.setEndValue(target)
            self._indicator_animation.start()
        else:
            self.sync_indicator()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().paintEvent(event)
        if self._indicator.isEmpty():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        glow = QColor(themed_color("#63d6ef"))
        glow.setAlpha(55)
        painter.setBrush(glow)
        painter.drawRoundedRect(self._indicator.adjusted(-2, -1, 2, 1), 3, 3)
        painter.setBrush(QColor(themed_color("#63d6ef")))
        painter.drawRoundedRect(self._indicator, 1.5, 1.5)

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
        close_slot = QWidget(self)
        close_slot.setObjectName("uidTabCloseSlot")
        close_slot.setFixedSize(28, 20)
        close_layout = QHBoxLayout(close_slot)
        close_layout.setContentsMargins(0, 0, 8, 0)
        close_layout.setSpacing(0)
        close_button = QToolButton(self)
        close_button.setObjectName("uidTabCloseButton")
        close_button.setFixedSize(20, 20)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setToolTip(f"Fechar UID {uid}")
        set_button_icon(close_button, "close", 12)
        close_button.clicked.connect(lambda: self._close_uid(uid))
        close_layout.addWidget(close_button)
        self.setTabButton(index, QTabBar.ButtonPosition.RightSide, close_slot)
        self.setTabData(index, uid)
        self.setTabToolTip(index, f"UID {uid}")
        return index

    def _close_uid(self, uid: str) -> None:
        index = self.index_for_uid(uid)
        if index >= 0:
            self.tabCloseRequested.emit(index)


class UidTabsWidget(QFrame):
    selected = Signal(str)
    close_requested = Signal(str)
    refresh_requested = Signal(str)
    order_changed = Signal(object)

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setObjectName("uidTabsPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(4)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.tabs = UidTabBar()
        self.tabs.currentChanged.connect(self._emit_selected)
        self.tabs.tabCloseRequested.connect(self._emit_close)
        self.tabs.order_changed.connect(self.order_changed.emit)
        row.addWidget(self.tabs, 1)

        self.refresh_button = QPushButton("")
        self.refresh_button.setObjectName("uidTabRefreshButton")
        self.refresh_button.setFixedSize(36, 36)
        self.refresh_button.setToolTip("Atualizar somente esta UID")
        set_button_icon(self.refresh_button, "refresh", 16)
        self.refresh_button.clicked.connect(self._emit_refresh)
        row.addWidget(self.refresh_button)
        layout.addLayout(row)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(4, 0, 0, 0)
        meta_row.setSpacing(7)
        self.status_dot = QLabel()
        self.status_dot.setObjectName("uidTabStatusDot")
        self.status_dot.setFixedSize(6, 6)
        self.status_dot.setProperty("state", "empty")
        self._status_opacity = QGraphicsOpacityEffect(self.status_dot)
        self.status_dot.setGraphicsEffect(self._status_opacity)
        self._status_pulse = QVariantAnimation(self)
        self._status_pulse.setStartValue(1.0)
        self._status_pulse.setKeyValueAt(0.5, 0.4)
        self._status_pulse.setEndValue(1.0)
        self._status_pulse.setDuration(1400)
        self._status_pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._status_pulse.setLoopCount(-1)
        self._status_pulse.valueChanged.connect(self._pulse_status)
        meta_row.addWidget(self.status_dot)
        self.meta_label = QLabel("Selecione uma aba")
        self.meta_label.setObjectName("uidTabMeta")
        meta_row.addWidget(self.meta_label, 1)
        layout.addLayout(meta_row)

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
        changed = self.tabs.currentIndex() != index
        previous = self.tabs.blockSignals(not emit)
        self.tabs.setCurrentIndex(index)
        self.tabs.blockSignals(previous)
        if not emit and changed:
            self.tabs._animate_indicator(index)
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
        self.status_dot.setProperty("state", self.meta_label.property("state"))
        for widget in (self.meta_label, self.status_dot):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        if loading and not reduce_motion_enabled():
            if self._status_pulse.state() != QVariantAnimation.State.Running:
                self._status_pulse.start()
        else:
            self._status_pulse.stop()
            self._status_opacity.setOpacity(1.0)
        self.refresh_button.setEnabled(not loading and bool(self.current_uid))

    def _pulse_status(self, value: float) -> None:
        if reduce_motion_enabled():
            self._status_pulse.stop()
            self._status_opacity.setOpacity(1.0)
        else:
            self._status_opacity.setOpacity(float(value))

    def _emit_selected(self, index: int) -> None:
        if index >= 0:
            self.selected.emit(str(self.tabs.tabData(index) or ""))

    def _emit_close(self, index: int) -> None:
        if index >= 0:
            self.close_requested.emit(str(self.tabs.tabData(index) or ""))

    def _emit_refresh(self) -> None:
        if self.current_uid:
            self.refresh_requested.emit(self.current_uid)
