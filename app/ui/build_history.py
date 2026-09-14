from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.motion import AnimatedDialog as QDialog
from app.build_history import BuildSnapshot


def snapshot_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value


def team_mode(payload: dict[str, Any]) -> str:
    team = payload.get("team", {})
    return "Customizado" if isinstance(team, dict) and team.get("custom") else "Padrão"


def delta_kind(value: float) -> str:
    if abs(value) < 1e-9:
        return "equal"
    return "gain" if value > 0 else "loss"


class BuildHistoryBar(QFrame):
    save_requested = Signal()
    export_requested = Signal()
    compare_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None, *, wide: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("buildHistoryBar")
        title = QLabel("HISTÓRICO DE BUILDS")
        title.setObjectName("buildHistoryTitle")
        self.counter = QLabel("0/5")
        self.counter.setObjectName("buildHistoryCounter")
        self.selector = QComboBox()
        self.selector.setObjectName("buildHistorySelector")
        self.selector.currentIndexChanged.connect(self._sync_actions)
        self.save_button = QPushButton("＋ Salvar atual")
        self.save_button.setObjectName("buildHistorySave")
        self.export_button = QPushButton("↗ Exportar PNG")
        self.export_button.setObjectName("buildHistoryExport")
        self.compare_button = QPushButton("Comparar")
        self.compare_button.setObjectName("buildHistoryCompare")
        self.delete_button = QPushButton("Excluir")
        self.delete_button.setObjectName("buildHistoryDelete")
        self.save_button.clicked.connect(self.save_requested)
        self.export_button.clicked.connect(self.export_requested)
        self.compare_button.clicked.connect(self._compare)
        self.delete_button.clicked.connect(self._delete)

        actions = QHBoxLayout()
        actions.setSpacing(5)
        actions.addWidget(self.save_button, 1)
        actions.addWidget(self.export_button)
        actions.addWidget(self.compare_button)
        actions.addWidget(self.delete_button)

        if wide:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(12, 9, 12, 9)
            layout.setSpacing(10)
            heading = QVBoxLayout()
            heading.setSpacing(2)
            heading.addWidget(title)
            heading.addWidget(self.counter, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addLayout(heading)
            self.selector.setMinimumWidth(170)
            layout.addWidget(self.selector, 1)
            layout.addLayout(actions)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(9, 7, 9, 8)
            layout.setSpacing(6)
            heading = QHBoxLayout()
            heading.addWidget(title)
            heading.addStretch(1)
            heading.addWidget(self.counter)
            layout.addLayout(heading)
            layout.addWidget(self.selector)
            layout.addLayout(actions)
        self.set_snapshots([], logged_in=False)
        self.export_button.setEnabled(False)

    def set_snapshots(
        self, snapshots: list[BuildSnapshot], *, logged_in: bool = True
    ) -> None:
        selected = self.selected_id()
        self.selector.blockSignals(True)
        self.selector.clear()
        if snapshots:
            for index, snapshot in enumerate(snapshots, start=1):
                label = (
                    f"Build {len(snapshots) - index + 1} · "
                    f"{snapshot.benchmark_score:.1f}% {snapshot.benchmark_grade} · "
                    f"{team_mode(snapshot.payload)} · "
                    f"{snapshot_date(snapshot.created_at)}"
                )
                self.selector.addItem(label, snapshot.id)
            restored = self.selector.findData(selected)
            self.selector.setCurrentIndex(max(0, restored))
        else:
            self.selector.addItem("Nenhuma build salva", None)
        self.selector.blockSignals(False)
        self.counter.setText(f"{len(snapshots)}/5")
        self.save_button.setEnabled(logged_in and len(snapshots) < 5)
        self.save_button.setToolTip(
            "Salvar a build e o benchmark exibidos agora"
            if logged_in else "Entre em um perfil para salvar builds"
        )
        self._sync_actions()

    def selected_id(self) -> int:
        value = self.selector.currentData()
        return int(value) if value is not None else 0

    def _sync_actions(self) -> None:
        enabled = self.selected_id() > 0
        self.compare_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def _compare(self) -> None:
        if self.selected_id():
            self.compare_requested.emit(self.selected_id())

    def _delete(self) -> None:
        if self.selected_id():
            self.delete_requested.emit(self.selected_id())


class BuildComparisonDialog(QDialog):
    def __init__(
        self,
        snapshot: BuildSnapshot,
        current: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("buildComparisonDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(760, 640)
        self.setMinimumSize(640, 520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        modal = QFrame()
        modal.setObjectName("buildComparisonModal")
        layout = QVBoxLayout(modal)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(10)

        header_card = QFrame()
        header_card.setObjectName("buildComparisonHeader")
        header = QHBoxLayout(header_card)
        header.setContentsMargins(13, 9, 9, 9)
        header.setSpacing(11)
        icon = QLabel("⇄")
        icon.setObjectName("buildComparisonIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(38, 38)
        heading = QVBoxLayout()
        heading.setSpacing(1)
        title = QLabel(f"COMPARAÇÃO · {snapshot.character_name}")
        title.setObjectName("buildComparisonTitle")
        subtitle = QLabel(
            f"Build salva em {snapshot_date(snapshot.created_at)}  →  build atual"
        )
        subtitle.setObjectName("buildComparisonSubtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        close = QPushButton("×")
        close.setObjectName("dialogCloseButton")
        close.setFixedSize(34, 30)
        close.clicked.connect(self.accept)
        header.addWidget(icon)
        header.addLayout(heading, 1)
        header.addWidget(close)
        layout.addWidget(header_card)

        summary = QFrame()
        summary.setObjectName("buildComparisonSummary")
        summary_layout = QHBoxLayout(summary)
        old_benchmark = snapshot.payload.get("benchmark", {})
        new_benchmark = current.get("benchmark", {})
        old_score = float(old_benchmark.get("score", 0.0))
        new_score = float(new_benchmark.get("score", 0.0))
        score_delta = new_score - old_score
        delta_type = delta_kind(score_delta)
        for caption, value, object_name in (
            ("BUILD SALVA", f"{old_score:.1f}% · {old_benchmark.get('grade', 'N/A')}", "old"),
            ("DIFERENÇA", self._signed(score_delta, "%"), delta_type),
            ("BUILD ATUAL", f"{new_score:.1f}% · {new_benchmark.get('grade', 'N/A')}", "new"),
        ):
            block = QVBoxLayout()
            label = QLabel(caption)
            label.setObjectName("buildComparisonMetricLabel")
            metric = QLabel(value)
            metric.setObjectName("buildComparisonMetric")
            metric.setProperty("metricType", object_name)
            metric.setAlignment(Qt.AlignmentFlag.AlignCenter)
            block.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
            block.addWidget(metric)
            summary_layout.addLayout(block, 1)
        layout.addWidget(summary)

        cone_old = snapshot.payload.get("light_cone", {})
        cone_new = current.get("light_cone", {})
        cone = QLabel(
            "CONE DE LUZ   "
            f"{cone_old.get('name', '—')} S{cone_old.get('rank', 0)}  →  "
            f"{cone_new.get('name', '—')} S{cone_new.get('rank', 0)}"
        )
        cone.setObjectName("buildComparisonCone")
        modes = QLabel(
            f"TIME DO BENCHMARK   {team_mode(snapshot.payload)}  →  {team_mode(current)}"
        )
        modes.setObjectName("buildComparisonTeam")
        cone.setWordWrap(True)
        modes.setWordWrap(True)
        details = QHBoxLayout()
        details.setSpacing(8)
        details.addWidget(cone, 3)
        details.addWidget(modes, 2)
        layout.addLayout(details)

        self.table = QTableWidget(0, 4)
        self.table.setObjectName("buildComparisonTable")
        self.table.setHorizontalHeaderLabels(
            ["Atributo", "Build salva", "Build atual", "Diferença"]
        )
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            self.table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self._populate_stats(snapshot.payload, current)
        layout.addWidget(self.table, 1)

        old_relics = snapshot.payload.get("relics", [])
        new_relics = current.get("relics", [])
        old_fingerprints = {item.get("fingerprint") for item in old_relics}
        new_fingerprints = {item.get("fingerprint") for item in new_relics}
        changed = max(len(old_fingerprints - new_fingerprints), len(new_fingerprints - old_fingerprints))
        relic_text = (
            "Nenhuma relíquia foi alterada."
            if changed == 0 else f"{changed} relíquia(s) diferente(s) na build atual."
        )
        relics = QLabel(f"RELÍQUIAS   {relic_text}")
        relics.setObjectName("buildComparisonRelics")
        layout.addWidget(relics)

        done = QPushButton("Fechar comparação")
        done.setObjectName("primaryButton")
        done.clicked.connect(self.accept)
        layout.addWidget(done, alignment=Qt.AlignmentFlag.AlignRight)
        outer.addWidget(modal)

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.position().y() <= 82
        ):
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)

    @staticmethod
    def _signed(value: float, suffix: str = "") -> str:
        return f"{value:+.1f}{suffix}"

    def _populate_stats(self, saved: dict[str, Any], current: dict[str, Any]) -> None:
        old_stats = {
            str(item.get("key")): item for item in saved.get("stats", [])
            if isinstance(item, dict)
        }
        new_stats = {
            str(item.get("key")): item for item in current.get("stats", [])
            if isinstance(item, dict)
        }
        ordered_keys = list(old_stats)
        ordered_keys.extend(key for key in new_stats if key not in old_stats)
        self.table.setRowCount(len(ordered_keys))
        for row, key in enumerate(ordered_keys):
            old = old_stats.get(key, {})
            new = new_stats.get(key, {})
            old_value = float(old.get("value", 0.0))
            new_value = float(new.get("value", 0.0))
            percentage = bool(new.get("percentage", old.get("percentage", False)))
            suffix = "%" if percentage else ""
            values = (
                str(new.get("name") or old.get("name") or key),
                str(old.get("formatted", "—")),
                str(new.get("formatted", "—")),
                self._signed(new_value - old_value, suffix),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 3:
                    delta = new_value - old_value
                    item.setData(Qt.ItemDataRole.UserRole, delta)
                    kind = delta_kind(delta)
                    color = {
                        "gain": "#84e7aa", "loss": "#ff8795", "equal": "#8996aa"
                    }[kind]
                    item.setForeground(QBrush(QColor(color)))
                self.table.setItem(row, column, item)


class ConfirmBuildDeleteDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("buildDeleteDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(410)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        card = QFrame()
        card.setObjectName("buildDeleteCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 19, 22, 21)
        layout.setSpacing(11)
        title = QLabel("EXCLUIR BUILD SALVA")
        title.setObjectName("buildDeleteTitle")
        message = QLabel(
            "Deseja excluir esta build do histórico? Essa ação não pode ser desfeita."
        )
        message.setObjectName("buildDeleteMessage")
        message.setWordWrap(True)
        actions = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("Excluir build")
        confirm.setObjectName("dangerButton")
        confirm.clicked.connect(self.accept)
        actions.addWidget(cancel, 1)
        actions.addWidget(confirm, 1)
        layout.addWidget(title)
        layout.addWidget(message)
        layout.addLayout(actions)
        outer.addWidget(card)
