from __future__ import annotations

import csv
from dataclasses import asdict
import json
from pathlib import Path
from collections import Counter

from PySide6.QtCore import Signal, QSize, QTimer, Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.auth import AuthUser
from app.ui.charts import WarpBarChart
from app.ui.experience import copy_error_details
from app.ui.widgets import AvatarLabel, FadeComboBox, FRIBBELS_ASSETS
from app.warp import StarRailStationImport, WarpDatabase, WarpImportWorker
from app.warp.models import WarpRecord, WarpSummary
from app.warp.analytics import analyze_warps
from app.warp.statistics import (
    FiveStarOutcome,
    STANDARD_CHARACTER_IDS,
    STANDARD_LIGHT_CONE_IDS,
    classify_five_star_history,
    five_star_history,
    pity_state,
)


BANNER_CONFIG = (
    ("11", "Evento de Personagem", 90),
    ("12", "Evento de Cone de Luz", 80),
    ("1", "Salto Estelar", 90),
    ("2", "Salto de Novatos", 50),
    ("21", "Salto Hiperespacial de Colaboração de Personagem", 90),
    ("22", "Salto Hiperespacial de Colaboração de Cone de Luz", 80),
)
BANNER_CAPS = {gacha_type: cap for gacha_type, _name, cap in BANNER_CONFIG}
BANNER_TITLES = {gacha_type: name for gacha_type, name, _cap in BANNER_CONFIG}
ALL_BANNERS = "__all__"


def banner_button_name(name: str) -> str:
    if " de Colaboração de " in name:
        category = name.split(" de Colaboração de ", 1)[1]
        return f"Salto Hiperespacial\nde Colaboração\nde {category}"
    return name


def pity_level(pity: int, cap: int) -> str:
    ratio = pity / max(cap, 1)
    if ratio <= (2 / 3):
        return "low"
    if ratio <= (5 / 6):
        return "medium"
    return "high"


PITY_COLORS = {
    "low": (QColor("#183f32"), QColor("#72e6ae")),
    "medium": (QColor("#5a3518"), QColor("#ffb45c")),
    "high": (QColor("#5a2029"), QColor("#ff7b88")),
}
OUTCOME_ICONS = {
    "won": "✓",
    "guaranteed": "◆",
    "lost": "✕",
    "neutral": "—",
}


class SummaryCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("warpSummaryCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)
        self.title = QLabel(title.upper())
        self.title.setObjectName("metricTitle")
        self.title.setWordWrap(True)
        self.title.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.value = QLabel("—")
        self.value.setObjectName("warpMetricValue")
        self.detail = QLabel("")
        self.detail.setObjectName("sectionHint")
        self.detail.setWordWrap(True)
        self.detail.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)

    def set_title(self, title: str) -> None:
        self.title.setText(title.upper())


class RecentWarpCard(QFrame):
    def __init__(self, result: FiveStarOutcome, cap: int) -> None:
        super().__init__()
        record = result.record
        pity = result.pity
        self.setObjectName("recentWarpCard")
        self.setToolTip(f"{record.name} · pity {pity} · {result.label}")
        self.setFixedWidth(88)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        visual = QWidget(self)
        visual.setFixedSize(58, 58)
        visual_layout = QGridLayout(visual)
        visual_layout.setContentsMargins(0, 0, 0, 0)
        avatar_path = FRIBBELS_ASSETS / "icon" / "avatar" / f"{record.item_id}.webp"
        icon_path = avatar_path
        if not icon_path.exists():
            icon_path = FRIBBELS_ASSETS / "icon" / "light_cone" / f"{record.item_id}.webp"
        icon = AvatarLabel(54, rounded=avatar_path.exists())
        if icon_path.exists():
            icon.set_image(QPixmap(str(icon_path)))
        badge = QLabel(str(pity))
        badge.setObjectName("recentPityBadge")
        badge.setProperty("pityLevel", pity_level(pity, cap))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setMinimumWidth(24)
        visual_layout.addWidget(icon, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        visual_layout.addWidget(
            badge,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        outcome = QLabel(OUTCOME_ICONS[result.outcome])
        outcome.setObjectName("recentOutcomeBadge")
        outcome.setProperty("outcome", result.outcome)
        outcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outcome.setFixedSize(21, 21)
        outcome.setToolTip(result.label)
        visual_layout.addWidget(
            outcome,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )
        name = QLabel(record.name)
        name.setObjectName("recentWarpName")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        name.setFixedWidth(76)
        name.setMaximumHeight(28)
        layout.addWidget(visual, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)


class WarpPanel(QWidget):
    import_completed = Signal(int)
    busy_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("warpPage")
        self.database = WarpDatabase()
        self.worker: WarpImportWorker | None = None
        self.owner_id: int | None = None
        self.game_uid = ""
        self._user_initialized = False
        self.current_uid = ""
        self.current_records: list[WarpRecord] = []
        self.current_summaries: dict[str, WarpSummary] = {}
        self.selected_gacha_type = "11"
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.page_scroll = QScrollArea()
        self.page_scroll.setObjectName("warpPageScroll")
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        content = QWidget()
        content.setObjectName("warpPageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 3, 6, 0)
        layout.setSpacing(10)

        title = QLabel("ACOMPANHAMENTO DE SALTOS")
        title.setObjectName("brandTitle")
        subtitle = QLabel(
            "Importe o cache do jogo ou um backup XLSX do Star Rail Station para "
            "acompanhar pity, garantidos e personagens obtidos."
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Mantém a janela interna do seletor associada ao painel desde a criação.
        controls = QFrame(self)
        controls.setObjectName("warpControlPanel")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(12, 10, 12, 10)
        controls_layout.setHorizontalSpacing(8)
        controls_layout.setVerticalSpacing(8)
        self.auto_button = QPushButton("Localizar e importar")
        self.auto_button.setObjectName("primaryButton")
        self.auto_button.clicked.connect(self.import_automatically)
        self.file_button = QPushButton("Importar arquivo")
        self.file_button.setObjectName("secondaryButton")
        self.file_button.clicked.connect(self.choose_cache_file)
        self.refresh_button = QPushButton("Atualizar tela")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self.refresh)
        self.csv_button = QPushButton("Exportar CSV")
        self.csv_button.setObjectName("secondaryButton")
        self.csv_button.clicked.connect(lambda: self._export_history("csv"))
        self.json_button = QPushButton("Exportar JSON")
        self.json_button.setObjectName("secondaryButton")
        self.json_button.clicked.connect(lambda: self._export_history("json"))
        account_label = QLabel("CONTA DO JOGO")
        account_label.setObjectName("metricTitle")
        self.account_selector = FadeComboBox(controls)
        self.account_selector.setObjectName("accountSelector")
        self.account_selector.setMinimumWidth(145)
        self.account_selector.currentIndexChanged.connect(self._account_changed)
        for column, button in enumerate(
            (self.auto_button, self.file_button, self.refresh_button)
        ):
            button.setMinimumWidth(0)
            button.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
            )
            controls_layout.addWidget(button, 0, column)
            controls_layout.setColumnStretch(column, 1)
        export_row = QHBoxLayout()
        export_row.setSpacing(8)
        export_row.addWidget(self.csv_button)
        export_row.addWidget(self.json_button)
        export_row.addStretch(1)
        controls_layout.addLayout(export_row, 1, 0, 1, 2)
        account_row = QHBoxLayout()
        account_row.setSpacing(8)
        account_row.addStretch(1)
        account_row.addWidget(account_label)
        account_row.addWidget(self.account_selector)
        controls_layout.addLayout(account_row, 1, 2)
        layout.addWidget(controls)

        self.status = QLabel(
            "Abra o histórico de Saltos dentro do jogo antes de fazer a importação."
        )
        self.status.setObjectName("statusInfo")
        self.status.setWordWrap(True)
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(8)
        self.copy_error_button = QPushButton("Copiar detalhes")
        self.copy_error_button.setObjectName("copyErrorButton")
        self.copy_error_button.setVisible(False)
        self.copy_error_button.clicked.connect(
            lambda: copy_error_details(self.status.text(), "Histórico de Saltos")
        )
        status_row.addWidget(self.status, 1)
        status_row.addWidget(self.copy_error_button)
        layout.addLayout(status_row)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setObjectName("warpContentSplitter")

        banner_panel = QFrame()
        banner_panel.setObjectName("warpBannerPanel")
        banner_layout = QVBoxLayout(banner_panel)
        banner_layout.setContentsMargins(8, 8, 8, 8)
        banner_layout.setSpacing(7)
        banner_title = QLabel("BANNERS")
        banner_title.setObjectName("sectionTitle")
        banner_layout.addWidget(banner_title)
        self.banner_scroll = QScrollArea()
        self.banner_scroll.setObjectName("warpBannerScroll")
        self.banner_scroll.setWidgetResizable(True)
        self.banner_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        banner_content = QWidget()
        banner_content.setObjectName("warpBannerContent")
        banner_buttons_layout = QVBoxLayout(banner_content)
        banner_buttons_layout.setContentsMargins(0, 0, 3, 0)
        banner_buttons_layout.setSpacing(5)
        self.banner_buttons: dict[str, QPushButton] = {}
        for gacha_type, name, cap in BANNER_CONFIG:
            button = QPushButton(
                f"{banner_button_name(name)}\nPity 5★ 0/{cap}  ·  Pity 4★ 0/10"
            )
            button.setObjectName("warpBannerButton")
            button.setCheckable(True)
            button.setChecked(gacha_type == self.selected_gacha_type)
            button.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
            )
            button.setMinimumHeight(62 if gacha_type in {"21", "22"} else 46)
            button.clicked.connect(
                lambda _checked=False, selected=gacha_type: self._select_banner(selected)
            )
            banner_buttons_layout.addWidget(button)
            self.banner_buttons[gacha_type] = button
        banner_buttons_layout.addStretch(1)
        self.banner_scroll.setWidget(banner_content)
        banner_layout.addWidget(self.banner_scroll, 1)
        content_splitter.addWidget(banner_panel)

        details = QFrame()
        details.setObjectName("warpDetailsPanel")
        self.details_panel = details
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(10, 8, 10, 8)
        details_layout.setSpacing(8)
        self.selected_banner_title = QLabel(BANNER_TITLES[self.selected_gacha_type].upper())
        self.selected_banner_title.setObjectName("sectionTitle")
        self.selected_banner_title.setWordWrap(True)
        details_layout.addWidget(self.selected_banner_title)

        edition_label = QLabel("EDIÇÃO DO BANNER")
        edition_label.setObjectName("metricTitle")
        details_layout.addWidget(edition_label)
        self.edition_selector = FadeComboBox(details)
        self.edition_selector.setMinimumWidth(0)
        self.edition_selector.setIconSize(QSize(36, 36))
        self.edition_selector.setMinimumHeight(46)
        self.edition_selector.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.edition_selector.currentIndexChanged.connect(
            lambda _index: self._render_records(self.current_records)
        )
        self._edition_context = None
        details_layout.addWidget(self.edition_selector)
        self.edition_hint = QLabel()
        self.edition_hint.setObjectName("sectionHint")
        self.edition_hint.setWordWrap(True)
        details_layout.addWidget(self.edition_hint)

        summary = QGridLayout()
        summary.setHorizontalSpacing(8)
        summary.setVerticalSpacing(8)
        self.total_card = SummaryCard("Total de Saltos")
        self.character_card = SummaryCard("Pity 5★")
        self.cone_card = SummaryCard("Pity 4★")
        self.guarantee_card = SummaryCard("Próximo 5★")
        for index, card in enumerate(
            (self.total_card, self.character_card, self.cone_card, self.guarantee_card)
        ):
            row, column = divmod(index, 2)
            summary.addWidget(card, row, column)
            summary.setColumnStretch(column, 1)
        details_layout.addLayout(summary)

        self.recent_title = QLabel("5★ OBTIDOS")
        self.recent_title.setObjectName("sectionTitle")
        details_layout.addWidget(self.recent_title)
        self.recent_list = QListWidget()
        self.recent_list.setObjectName("recentWarpsList")
        self.recent_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.recent_list.setFlow(QListWidget.Flow.LeftToRight)
        self.recent_list.setWrapping(True)
        self.recent_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.recent_list.setMovement(QListWidget.Movement.Static)
        self.recent_list.setSpacing(5)
        self.recent_list.setGridSize(QSize(96, 108))
        self.recent_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.recent_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.recent_list.setMinimumHeight(126)
        self.recent_list.setMaximumHeight(340)
        details_layout.addWidget(self.recent_list)

        self.history_title = QLabel("HISTÓRICO DE 5★")
        self.history_title.setObjectName("sectionTitle")
        details_layout.addWidget(self.history_title)
        self.table = QTableWidget(0, 6)
        self.table.setMinimumHeight(180)
        self.table.setObjectName("warpTable")
        self.table.setHorizontalHeaderLabels(
            ["Item", "Banner", "Data", "Pity", "Resultado", "Raridade"]
        )
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(44)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        details_layout.addWidget(self.table, 1)
        content_splitter.addWidget(details)
        content_splitter.setSizes([230, 760])
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)
        banner_panel.setMinimumWidth(200)
        banner_panel.setMaximumWidth(270)
        layout.addWidget(content_splitter, 1)

        analytics_panel = QFrame()
        analytics_panel.setObjectName("warpAnalyticsPanel")
        analytics_layout = QVBoxLayout(analytics_panel)
        analytics_layout.setContentsMargins(12, 11, 12, 12)
        analytics_layout.setSpacing(9)
        analytics_title = QLabel("ANÁLISES DO HISTÓRICO")
        analytics_title.setObjectName("sectionTitle")
        analytics_layout.addWidget(analytics_title)
        charts = QHBoxLayout()
        charts.setSpacing(9)
        monthly_box = QVBoxLayout()
        monthly_label = QLabel("TIROS POR MÊS")
        monthly_label.setObjectName("metricTitle")
        self.monthly_chart = WarpBarChart()
        monthly_box.addWidget(monthly_label)
        monthly_box.addWidget(self.monthly_chart)
        edition_box = QVBoxLayout()
        chart_edition_label = QLabel("TIROS POR VERSÃO / EDIÇÃO")
        chart_edition_label.setObjectName("metricTitle")
        self.edition_chart = WarpBarChart(horizontal=True)
        edition_box.addWidget(chart_edition_label)
        edition_box.addWidget(self.edition_chart)
        charts.addLayout(monthly_box, 1)
        charts.addLayout(edition_box, 1)
        analytics_layout.addLayout(charts)
        metrics = QHBoxLayout()
        self.pity_comparison = QLabel("Média de pity: —")
        self.pity_comparison.setObjectName("warpAnalyticsMetric")
        self.outcome_summary = QLabel("50/50: —")
        self.outcome_summary.setObjectName("warpAnalyticsMetric")
        metrics.addWidget(self.pity_comparison, 1)
        metrics.addWidget(self.outcome_summary, 1)
        analytics_layout.addLayout(metrics)
        self.gap_report = QLabel("Qualidade do histórico: aguardando dados.")
        self.gap_report.setObjectName("warpGapReport")
        self.gap_report.setWordWrap(True)
        analytics_layout.addWidget(self.gap_report)
        layout.addWidget(analytics_panel)
        self.page_scroll.setWidget(content)
        outer.addWidget(self.page_scroll)

    def import_automatically(self) -> None:
        self._start_import(None)

    def choose_cache_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Escolha o cache ou backup do Star Rail Station",
            str(Path.home() / "Downloads"),
            "Backup Star Rail Station (*.xlsx);;Arquivos de cache (data_*);;Todos os arquivos (*)",
        )
        if path:
            self._start_import(Path(path))

    def _start_import(self, cache_path: Path | None) -> None:
        if self.owner_id is None:
            self._set_status("Entre em um perfil para importar Saltos.", "error")
            return
        if self.worker and self.worker.isRunning():
            return
        target_uid = self.current_uid or self.game_uid
        if cache_path and cache_path.suffix.casefold() == ".xlsx" and not target_uid:
            self._set_status(
                "Defina sua UID principal nas configurações antes de importar o Excel.",
                "error",
            )
            return
        self._set_busy(True)
        self._set_status(
            "Lendo backup do Star Rail Station…"
            if cache_path and cache_path.suffix.casefold() == ".xlsx"
            else "Procurando o link do histórico de Saltos…"
        )
        self.worker = WarpImportWorker(cache_path, target_uid)
        self.worker.progress.connect(self._set_status)
        self.worker.succeeded.connect(self._import_succeeded)
        self.worker.failed.connect(self._import_failed)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _import_succeeded(self, payload: object, source: str) -> None:
        spreadsheet = payload if isinstance(payload, StarRailStationImport) else None
        records = spreadsheet.records if spreadsheet else payload if isinstance(payload, list) else []
        valid_records = [record for record in records if isinstance(record, WarpRecord)]
        if self.owner_id is None:
            self._set_status("A sessão foi encerrada durante a importação.", "error")
            return
        added = self.database.add_records(valid_records, self.owner_id)
        if spreadsheet is not None:
            for summary in spreadsheet.summaries:
                self.database.upsert_summary(summary, self.owner_id)
        if valid_records:
            self.current_uid = valid_records[0].uid
        elif spreadsheet is not None:
            self.current_uid = spreadsheet.uid
        self.refresh()
        summary_count = len(spreadsheet.summaries) if spreadsheet else 0
        warning = (
            f" Avisos: {'; '.join(spreadsheet.warnings)}"
            if spreadsheet and spreadsheet.warnings else ""
        )
        self._set_status(
            f"Importação concluída: {len(valid_records)} registros lidos, "
            f"{added} novos, {summary_count} resumo(s) de colaboração. "
            f"Fonte: {Path(source).name}.{warning}",
            "success",
        )
        self.import_completed.emit(self.owner_id)

    def _import_failed(self, message: str) -> None:
        self._set_status(message, "error")

    def _worker_finished(self) -> None:
        self._set_busy(False)
        if self.worker:
            self.worker.deleteLater()
        self.worker = None

    def _set_busy(self, busy: bool) -> None:
        can_import = self.owner_id is not None and not busy
        self.auto_button.setEnabled(can_import)
        self.file_button.setEnabled(can_import)
        can_export = bool(can_import and self.current_uid and self.current_records)
        self.csv_button.setEnabled(can_export)
        self.json_button.setEnabled(can_export)
        self.auto_button.setText("Importando…" if busy else "Localizar e importar")
        self.busy_changed.emit(busy)

    def _set_status(self, message: str, kind: str = "info") -> None:
        object_name = {"success": "statusSuccess", "error": "statusError"}.get(
            kind, "statusInfo"
        )
        self.status.setObjectName(object_name)
        self.status.setText(message)
        self.copy_error_button.setVisible(kind == "error")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def set_user(self, user: AuthUser | None) -> None:
        owner_id = user.id if user else None
        self.game_uid = user.game_uid if user else ""
        if self._user_initialized and owner_id == self.owner_id:
            self.refresh()
            return
        self._user_initialized = True
        self.owner_id = owner_id
        self.current_uid = ""
        self._set_busy(False)
        self.refresh()
        if user is None:
            self._set_status(
                "Entre ou crie uma conta para acessar seu acompanhamento de Saltos."
            )
        elif not self.current_uid:
            self._set_status(
                "Nenhum histórico importado. Abra o histórico de Saltos no jogo e clique em Localizar e importar."
            )
        else:
            self._set_status(f"Histórico separado do perfil {user.username}.", "success")

    def _account_changed(self, index: int) -> None:
        uid = self.account_selector.itemData(index) if index >= 0 else ""
        if uid and str(uid) != self.current_uid:
            self.current_uid = str(uid)
            self.refresh(update_selector=False)

    def _select_banner(self, gacha_type: str) -> None:
        self.selected_gacha_type = gacha_type
        for key, button in self.banner_buttons.items():
            button.setChecked(key == gacha_type)
        self._render_records(self.current_records)

    def refresh(self, update_selector: bool = True) -> None:
        if self.owner_id is None:
            self.current_uid = ""
            self.current_summaries = {}
            self.account_selector.clear()
            self.account_selector.setEnabled(False)
            self._render_records([])
            return
        uids = self.database.uids(self.owner_id)
        if self.current_uid not in uids:
            self.current_uid = self.database.latest_uid(self.owner_id)
        if update_selector:
            self.account_selector.blockSignals(True)
            self.account_selector.clear()
            for uid in uids:
                self.account_selector.addItem(f"UID {uid}", uid)
            if self.current_uid:
                index = self.account_selector.findData(self.current_uid)
                self.account_selector.setCurrentIndex(max(index, 0))
            self.account_selector.blockSignals(False)
        self.account_selector.setEnabled(bool(uids))
        records = self.database.records(self.current_uid, self.owner_id)
        self.current_summaries = self.database.summaries(
            self.current_uid, self.owner_id
        )
        self._render_records(records)

    def _render_records(self, records: list[WarpRecord]) -> None:
        self.current_records = records
        for gacha_type, name, cap in BANNER_CONFIG:
            summary = self.current_summaries.get(gacha_type)
            if summary is not None:
                five_star_pity = summary.five_star_pity
                four_star_pity = summary.four_star_pity
            else:
                standard_ids = self._standard_ids(gacha_type)
                state = pity_state(records, {gacha_type}, standard_ids)
                five_star_pity = state.five_star
                four_star_pity = state.four_star
            self.banner_buttons[gacha_type].setText(
                f"{banner_button_name(name)}\nPity 5★ {five_star_pity}/{cap}  ·  "
                f"Pity 4★ {four_star_pity}/10"
            )

        selected = [
            record for record in records
            if record.gacha_type == self.selected_gacha_type
        ]
        context = (self.owner_id, self.current_uid, self.selected_gacha_type)
        edition = (
            self.edition_selector.currentData()
            if context == self._edition_context
            else ALL_BANNERS
        )
        self._edition_context = context
        groups: dict[str, list[WarpRecord]] = {}
        for record in selected:
            groups.setdefault(record.banner_id or "unknown", []).append(record)
        self.edition_selector.blockSignals(True)
        self.edition_selector.clear()
        category_summary = self.current_summaries.get(self.selected_gacha_type)
        total_in_category = category_summary.total if category_summary else len(selected)
        self.edition_selector.addItem(
            f"Todos os saltos · {total_in_category} tiros",
            ALL_BANNERS,
        )
        for key, group in sorted(
            groups.items(),
            key=lambda pair: max(r.time for r in pair[1]),
            reverse=True,
        ):
            five_stars = [
                record
                for record in group
                if record.rank_type == 5
            ]
            if not five_stars:
                continue
            sample = next((r for r in group if r.banner_title), group[0])
            title = sample.banner_title or f"Banner {key}"
            featured_names = list(dict.fromkeys(
                record.featured_name for record in group if record.featured_name
            ))
            names = Counter(record.name for record in five_stars)
            obtained_names = ", ".join(
                f"{name} ×{count}" if count > 1 else name
                for name, count in names.items()
            )
            if key == "unknown":
                title = "Banner não identificado"
            focus = (
                ""
                if self.selected_gacha_type in {"11", "21"}
                else ", ".join(featured_names) or obtained_names
            )
            label = " · ".join(part for part in (
                focus,
                title,
                min(r.time for r in group)[:10],
                f"{len(group)} tiros",
            ) if part)
            portrait = next(
                (record for record in five_stars if record.name == record.featured_name),
                five_stars[0],
            )
            icon_path = FRIBBELS_ASSETS / "icon" / "avatar" / f"{portrait.item_id}.webp"
            if not icon_path.exists():
                icon_path = (
                    FRIBBELS_ASSETS / "icon" / "light_cone" / f"{portrait.item_id}.webp"
                )
            self.edition_selector.addItem(
                QIcon(str(icon_path)) if icon_path.exists() else QIcon(),
                label,
                key,
            )
        index = self.edition_selector.findData(edition)
        self.edition_selector.setCurrentIndex(max(index, 0))
        self.edition_selector.blockSignals(False)
        edition = self.edition_selector.currentData()
        filtered = selected if edition == ALL_BANNERS else groups.get(edition, [])
        cap = BANNER_CAPS[self.selected_gacha_type]
        summary = self.current_summaries.get(self.selected_gacha_type)
        if summary is not None:
            total = summary.total
            five_star_pity = summary.five_star_pity
            four_star_pity = summary.four_star_pity
            four_star_count = summary.four_star_count
            guaranteed = False
            featured = WarpRecord(
                id=f"summary-{summary.gacha_type}-{summary.featured_item_id}",
                uid=summary.uid,
                gacha_type=summary.gacha_type,
                item_id=summary.featured_item_id,
                name=summary.featured_item_name,
                item_type=summary.featured_item_type,
                rank_type=5,
                time="Resumo do Excel",
            )
            history = [(featured, summary.featured_pity)]
        else:
            total = len(selected)
            state = pity_state(
                selected,
                {self.selected_gacha_type},
                self._standard_ids(self.selected_gacha_type),
            )
            five_star_pity = state.five_star
            four_star_pity = state.four_star
            four_star_count = sum(record.rank_type == 4 for record in selected)
            guaranteed = state.guaranteed
            history = five_star_history(selected)
        average = (
            sum(pity for _record, pity in history) / len(history) if history else 0.0
        )

        self.selected_banner_title.setText(
            BANNER_TITLES[self.selected_gacha_type].upper()
        )
        if self.selected_gacha_type in {"11", "21"}:
            self.recent_title.setText("PERSONAGENS 5★ OBTIDOS")
        elif self.selected_gacha_type in {"12", "22"}:
            self.recent_title.setText("CONES DE LUZ 5★ OBTIDOS")
        else:
            self.recent_title.setText("ITENS 5★ OBTIDOS")
        self.total_card.value.setText(str(total))
        self.total_card.detail.setText(
            f"Equivalente a {total * 160:,} Jades".replace(",", ".")
        )
        self.character_card.value.setText(f"{five_star_pity}/{cap}")
        self.character_card.detail.setText(
            f"Média 5★: {average:.1f}" if history else "Nenhum 5★ salvo"
        )
        self.cone_card.value.setText(f"{four_star_pity}/10")
        self.cone_card.detail.setText(f"{four_star_count} itens 4★")
        if self.selected_gacha_type in {"11", "12", "21", "22"}:
            self.guarantee_card.value.setText("GARANTIDO" if guaranteed else "50/50")
            self.guarantee_card.detail.setText(
                "Próximo promocional" if guaranteed else "Não garantido"
            )
        else:
            self.guarantee_card.value.setText("—")
            self.guarantee_card.detail.setText("Banner sem 50/50")
        contest = "75/25" if self.selected_gacha_type in {"12", "22"} else "50/50"
        outcomes = classify_five_star_history(
            history,
            self._standard_ids(self.selected_gacha_type),
            contest,
        )
        self.character_card.set_title("Pity 5★ atual")
        self.cone_card.set_title("Pity 4★ atual")
        self.total_card.set_title(
            "Total de Saltos" if edition == ALL_BANNERS else "Tiros na edição"
        )
        self.edition_selector.setEnabled(
            self.edition_selector.count() > 1 and summary is None
        )
        if summary is not None:
            self.edition_hint.setText(
                "Resumo do Excel: não há registros individuais para separar as edições e cópias."
            )
        else:
            self.edition_hint.setText(
                "Selecione Todos os saltos ou uma edição que contenha um 5★. "
                "Pity atual e garantia consideram todo o histórico da categoria."
            )
        if edition != ALL_BANNERS and summary is None:
            outcomes = [result for result in outcomes if (result.record.banner_id or "unknown") == edition]
            self.total_card.value.setText(str(len(filtered)))
            five_count = sum(r.rank_type == 5 for r in filtered)
            four_count = sum(r.rank_type == 4 for r in filtered)
            self.total_card.detail.setText(f"{five_count} itens 5★ · {four_count} itens 4★")
            self.character_card.detail.setText("Acumulado da categoria, após todos os tiros")
            self.cone_card.detail.setText("Acumulado da categoria, após todos os tiros")
        self._fill_recent(outcomes, cap)
        self._fill_history(outcomes)
        self._render_analytics(records)

    def _render_analytics(self, records: list[WarpRecord]) -> None:
        analysis = analyze_warps(
            records, self.current_summaries, self.selected_gacha_type
        )
        self.monthly_chart.set_data(analysis.monthly)
        self.edition_chart.set_data(analysis.editions)
        personal = (
            f"{analysis.personal_average:.1f}".replace(".", ",")
            if analysis.personal_average is not None else "—"
        )
        theoretical = f"{analysis.theoretical_average:.1f}".replace(".", ",")
        self.pity_comparison.setText(
            f"Média pessoal de pity: {personal}  ·  média teórica: {theoretical}"
        )
        if self.selected_gacha_type in {"11", "12", "21", "22"}:
            contest = "75/25" if self.selected_gacha_type in {"12", "22"} else "50/50"
            self.outcome_summary.setText(
                f"{contest}: {analysis.wins} vitória(s) · {analysis.losses} derrota(s) · "
                f"{analysis.guaranteed} garantido(s)"
            )
        else:
            self.outcome_summary.setText("Banner sem disputa de rate-up.")
        if analysis.gaps:
            self.gap_report.setProperty("warning", True)
            self.gap_report.setText(
                "Possíveis lacunas: " + "  •  ".join(
                    f"{gap.title}: {gap.detail}" for gap in analysis.gaps
                )
            )
        else:
            self.gap_report.setProperty("warning", False)
            self.gap_report.setText(
                "Histórico individual consistente nos dados disponíveis."
            )
        self.gap_report.style().unpolish(self.gap_report)
        self.gap_report.style().polish(self.gap_report)
        can_export = bool(self.owner_id is not None and self.current_uid and records)
        self.csv_button.setEnabled(can_export)
        self.json_button.setEnabled(can_export)

    def _export_history(self, format_name: str) -> None:
        if self.owner_id is None or not self.current_uid or not self.current_records:
            self._set_status("Nenhum histórico selecionado para exportar.", "error")
            return
        suffix = format_name.casefold()
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "Exportar histórico de Saltos",
            f"AstralOptimizer_Saltos_{self.current_uid}.{suffix}",
            "CSV (*.csv)" if suffix == "csv" else "JSON (*.json)",
        )
        if not path:
            return
        if not path.casefold().endswith(f".{suffix}"):
            path += f".{suffix}"
        try:
            if suffix == "csv":
                fields = list(asdict(self.current_records[0]))
                with open(path, "w", encoding="utf-8-sig", newline="") as output:
                    writer = csv.DictWriter(output, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(asdict(record) for record in self.current_records)
            else:
                payload = {
                    "version": 1,
                    "uid": self.current_uid,
                    "records": [asdict(record) for record in self.current_records],
                    "summaries": [
                        asdict(value) for value in self.current_summaries.values()
                    ],
                }
                Path(path).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        except OSError as error:
            self._set_status(f"Não foi possível exportar: {error}", "error")
            return
        self._set_status(f"Histórico exportado em {suffix.upper()}.", "success")

    @staticmethod
    def _standard_ids(gacha_type: str) -> set[str] | None:
        if gacha_type in {"11", "21"}:
            return STANDARD_CHARACTER_IDS
        if gacha_type in {"12", "22"}:
            return STANDARD_LIGHT_CONE_IDS
        return None

    def _fill_recent(
        self, history: list[FiveStarOutcome], cap: int
    ) -> None:
        self.recent_list.clear()
        for result in history:
            item = QListWidgetItem()
            item.setSizeHint(QSize(90, 104))
            self.recent_list.addItem(item)
            self.recent_list.setItemWidget(item, RecentWarpCard(result, cap))
        if not history:
            item = QListWidgetItem("Os 5★ deste banner aparecerão aqui.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setSizeHint(QSize(360, 70))
            self.recent_list.addItem(item)
        QTimer.singleShot(0, self._resize_recent_list)

    def _resize_recent_list(self) -> None:
        available = max(self.recent_list.viewport().width(), 96)
        columns = max(available // 96, 1)
        rows = max((self.recent_list.count() + columns - 1) // columns, 1)
        # Reserva espaço para resumo, títulos e histórico. Quando há muitos
        # personagens, a lista passa a rolar internamente em vez de invadir a
        # tabela que vem logo abaixo.
        details_height = max(self.details_panel.height(), 389)
        available_height = max(details_height - 265, 124)
        rows_that_fit = max((available_height - 16) // 108, 1)
        # Duas linhas mantêm a vitrine compacta mesmo em contas com muitos 5★.
        # Os demais itens continuam acessíveis pela rolagem vertical da lista.
        visible_rows = min(rows, rows_that_fit, 2)
        self.recent_list.setFixedHeight(visible_rows * 108 + 16)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        if hasattr(self, "recent_list"):
            QTimer.singleShot(0, self._resize_recent_list)

    def _fill_history(self, history: list[FiveStarOutcome]) -> None:
        self.table.setRowCount(len(history))
        for row, result in enumerate(history):
            record = result.record
            pity = result.pity
            item = QTableWidgetItem(record.name)
            icon_path = FRIBBELS_ASSETS / "icon" / "avatar" / f"{record.item_id}.webp"
            if not icon_path.exists():
                icon_path = (
                    FRIBBELS_ASSETS / "icon" / "light_cone" / f"{record.item_id}.webp"
                )
            if icon_path.exists():
                item.setIcon(QIcon(str(icon_path)))
            self.table.setItem(row, 0, item)
            self.table.setItem(
                row,
                1,
                QTableWidgetItem(
                    record.banner_title or BANNER_TITLES.get(record.gacha_type, record.banner_name)
                ),
            )
            self.table.setItem(row, 2, QTableWidgetItem(record.time))
            pity_item = QTableWidgetItem(str(pity))
            pity_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            background, foreground = PITY_COLORS[pity_level(
                pity, BANNER_CAPS[self.selected_gacha_type]
            )]
            pity_item.setBackground(background)
            pity_item.setForeground(foreground)
            self.table.setItem(row, 3, pity_item)
            outcome = result.outcome
            outcome_item = QTableWidgetItem(OUTCOME_ICONS[outcome])
            outcome_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            outcome_item.setToolTip(result.label)
            _background, outcome_color = {
                "won": (QColor(), QColor("#72e6ae")),
                "guaranteed": (QColor(), QColor("#ffc866")),
                "lost": (QColor(), QColor("#ff7b88")),
                "neutral": (QColor(), QColor("#8d9ab0")),
            }[outcome]
            outcome_item.setForeground(outcome_color)
            self.table.setItem(row, 4, outcome_item)
            rarity = QTableWidgetItem("★★★★★")
            rarity.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, rarity)
        self.table.resizeRowsToContents()
