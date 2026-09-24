from __future__ import annotations

import math
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QGridLayout, QHeaderView, QHBoxLayout, QLabel,
    QProgressBar, QScrollArea, QSizePolicy, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.ui.motion import AnimatedProgressBar as QProgressBar
from app.ui.contextual_help import GUARANTEE_HELP, PITY_HELP, ContextHelpButton

from app.auth import AuthUser
from app.planner import calculate_planner, sequence_projections
from app.ui.widgets import FRIBBELS_ASSETS, FadeComboBox, FadeSpinBox
from app.warp import WarpDatabase
from app.warp.statistics import (
    STANDARD_CHARACTER_IDS, STANDARD_LIGHT_CONE_IDS, pity_state,
)


class PlannerPanel(QWidget):
    def __init__(self, database: WarpDatabase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.database = database
        self.user: AuthUser | None = None
        self._loading = False
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 3, 6, 0)
        outer.setSpacing(10)
        title = QLabel("Planejador de Tiros  ⓘ")
        title.setObjectName("plannerTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setToolTip("Estimativas baseadas nas distribuições do Fribbels.")
        outer.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setObjectName("plannerScroll")
        content = QWidget()
        content.setObjectName("scrollContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 8, 12, 14)
        layout.setSpacing(12)

        # O pai explícito impede que os popups dos QComboBox sejam registrados
        # temporariamente como janelas independentes pelo Windows.
        self.settings_card = QFrame(self)
        self.settings_card.setObjectName("plannerSettingsCard")
        self.settings_card.setMaximumWidth(920)
        self.settings_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        settings = QGridLayout(self.settings_card)
        settings.setContentsMargins(14, 12, 14, 12)
        settings.setHorizontalSpacing(24)
        settings.setVerticalSpacing(9)
        settings.addWidget(self._column_title("Configurações"), 0, 0, 1, 2)
        settings.addWidget(self._column_title("Personagem"), 0, 2)
        settings.addWidget(self._column_title("Cone de Luz"), 0, 3)

        self.jades = self._number_field(self.settings_card)
        self.passes = self._number_field(self.settings_card)
        self.starlight = self._number_field(self.settings_card)
        self.refund = FadeComboBox(self.settings_card)
        self.refund.addItem("Sem reembolso · 0%", "none")
        self.refund.addItem("Reembolso baixo · 4%", "low")
        self.refund.addItem("Reembolso médio · 7,5%", "average")
        self.refund.addItem("Reembolso alto · 11%", "high")
        settings.addLayout(
            self._resource_field_box(
                "JADES", self.jades, "jade.webp", "160 jades = 1 tiro"
            ),
            1, 0,
        )
        settings.addLayout(
            self._resource_field_box(
                "PASSES", self.passes, "pass.webp", "1 passe = 1 tiro"
            ),
            1, 1,
        )
        settings.addLayout(
            self._resource_field_box(
                "LUZ ESTELAR", self.starlight, "starlight.webp", "20 = 1 passe"
            ),
            2, 0,
        )
        settings.addLayout(self._field_box("CASHBACK", self.refund), 2, 1)

        self.character_pity = QLabel("0/90")
        self.cone_pity = QLabel("0/80")
        self.character_pity.setObjectName("plannerPityValue")
        self.cone_pity.setObjectName("plannerPityValue")
        self.character_guarantee = QLabel("✕  Disputa de rate-up")
        self.cone_guarantee = QLabel("✕  Disputa de rate-up")
        for badge in (self.character_guarantee, self.cone_guarantee):
            badge.setObjectName("plannerGuarantee")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings.addLayout(
            self._field_box("CONTADOR DE PITY", self.character_pity, PITY_HELP), 1, 2
        )
        settings.addLayout(
            self._field_box("CONTADOR DE PITY", self.cone_pity, PITY_HELP), 1, 3
        )
        settings.addLayout(
            self._field_box("GARANTIA", self.character_guarantee, GUARANTEE_HELP), 2, 2
        )
        settings.addLayout(
            self._field_box("GARANTIA", self.cone_guarantee, GUARANTEE_HELP), 2, 3
        )

        self.strategy = FadeComboBox(self.settings_card)
        self.strategy.setObjectName("plannerStrategySelect")
        self.strategy.addItem("S1 primeiro", "S1")
        for level in range(7):
            self.strategy.addItem(f"E{level} primeiro", f"E{level}")
        self.strategy.setMinimumWidth(210)
        self.strategy.setMaximumWidth(300)
        settings.addLayout(self._field_box("ESTRATÉGIA", self.strategy), 3, 0, 1, 2)
        for column in range(4):
            settings.setColumnStretch(column, 1)
        layout.addWidget(self.settings_card, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.resources_line = QLabel("0 tiros disponíveis")
        self.resources_line.setObjectName("plannerResourcesLine")
        self.resources_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resources_line.setMaximumWidth(920)
        layout.addWidget(self.resources_line, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.table = QTableWidget(0, 5)
        self.table.setObjectName("plannerGoalTable")
        self.table.setHorizontalHeaderLabels(
            ["Meta", "Chance atual", "Otimista", "Média", "Pessimista"]
        )
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setMaximumWidth(920)
        self.table.setMinimumWidth(560)
        header = self.table.horizontalHeader()
        for column in range(5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.status = QLabel("Entre em um perfil para usar o planejador.")
        self.status.setObjectName("statusInfo")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)
        layout.addStretch(1)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)
        self.scroll.viewport().installEventFilter(self)
        self._update_responsive_widths()

        for field in (self.jades, self.passes, self.starlight):
            field.valueChanged.connect(self._resources_changed)
        self.refund.currentIndexChanged.connect(self._resources_changed)
        self.strategy.currentIndexChanged.connect(self._resources_changed)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._update_responsive_widths()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        if (
            watched is self.scroll.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            self._update_responsive_widths()
        return super().eventFilter(watched, event)

    def _update_responsive_widths(self) -> None:
        available = max(560, min(920, self.scroll.viewport().width() - 24))
        self.settings_card.setFixedWidth(available)
        self.resources_line.setFixedWidth(available)
        self.table.setFixedWidth(available)

    @staticmethod
    def _column_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("plannerColumnTitle")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    @staticmethod
    def _number_field(parent: QWidget) -> QSpinBox:
        field = FadeSpinBox(parent)
        field.setObjectName("plannerResourceSpin")
        field.setRange(0, 999_999_999)
        field.setGroupSeparatorShown(True)
        field.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        field.setMinimumWidth(0)
        field.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        return field

    @staticmethod
    def _resource_field_box(
        title: str, field: QSpinBox, icon_name: str, hint: str
    ) -> QVBoxLayout:
        label = QLabel(title)
        label.setObjectName("metricTitle")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(7)
        icon = QLabel()
        icon.setObjectName("plannerResourceIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(FRIBBELS_ASSETS / "misc" / icon_name))
        if not pixmap.isNull():
            icon.setPixmap(
                pixmap.scaled(
                    22, 22,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        row.addWidget(icon)
        row.addWidget(field, 1)
        field.setToolTip(hint)

        box = QVBoxLayout()
        box.setSpacing(4)
        box.addWidget(label)
        box.addLayout(row)
        return box

    @staticmethod
    def _field_box(
        title: str,
        widget: QWidget,
        help_content: tuple[str, str] | None = None,
    ) -> QVBoxLayout:
        label = QLabel(title)
        label.setObjectName("metricTitle")
        box = QVBoxLayout()
        box.setSpacing(4)
        if help_content is None:
            box.addWidget(label)
        else:
            header = QHBoxLayout()
            header.setSpacing(5)
            header.addWidget(label)
            header.addWidget(ContextHelpButton(*help_content))
            header.addStretch(1)
            box.addLayout(header)
        box.addWidget(widget)
        return box

    def set_user(self, user: AuthUser | None) -> None:
        self.user = user
        self._loading = True
        values = self.database.planner_settings(user.id) if user else {
            "jades": 0, "passes": 0, "starlight": 0,
            "refund": "average", "strategy": "E2",
        }
        self.jades.setValue(int(values["jades"]))
        self.passes.setValue(int(values["passes"]))
        self.starlight.setValue(int(values["starlight"]))
        self.refund.setCurrentIndex(max(self.refund.findData(values["refund"]), 0))
        self.strategy.setCurrentIndex(max(self.strategy.findData(values["strategy"]), 0))
        self._loading = False
        self.refresh()

    def _settings(self) -> dict[str, object]:
        return {
            "jades": self.jades.value(), "passes": self.passes.value(),
            "starlight": self.starlight.value(),
            "refund": str(self.refund.currentData()),
            "strategy": str(self.strategy.currentData()),
        }

    def _resources_changed(self) -> None:
        if self._loading or self.user is None:
            return
        self.database.save_planner_settings(self.user.id, self._settings())
        self.refresh()

    def refresh(self) -> None:
        user = self.user
        for widget in (self.jades, self.passes, self.starlight, self.refund, self.strategy):
            widget.setEnabled(user is not None)
        if user is None:
            self.table.setRowCount(0)
            self.resources_line.setText("0 tiros disponíveis")
            self.status.setText(
                "Entre em um perfil; depois informe seus recursos e escolha uma estratégia."
            )
            return
        uids = self.database.uids(user.id)
        uid = user.game_uid if user.game_uid in uids else self.database.latest_uid(user.id)
        records = self.database.records(uid, user.id) if uid else []
        character = pity_state(records, {"11"}, STANDARD_CHARACTER_IDS)
        cone = pity_state(records, {"12"}, STANDARD_LIGHT_CONE_IDS)
        self.character_pity.setText(f"{character.five_star}/90")
        self.cone_pity.setText(f"{cone.five_star}/80")
        self._set_guarantee(self.character_guarantee, character.guaranteed)
        self._set_guarantee(self.cone_guarantee, cone.guaranteed)
        values = self._settings()
        result = calculate_planner(
            jades=int(values["jades"]), passes=int(values["passes"]),
            starlight=int(values["starlight"]), refund=str(values["refund"]),
            strategy=str(values["strategy"]),
            character_pity=character.five_star,
            character_guaranteed=character.guaranteed,
            light_cone_pity=cone.five_star,
            light_cone_guaranteed=cone.guaranteed,
        )
        self.resources_line.setText(
            f"{self.jades.value():,} jades = {result.jade_warps} tiros   +   "
            f"{self.passes.value():,} passes   +   {result.starlight_warps} da "
            f"Luz Estelar   +   {result.refunded_warps} cashback   =   "
            f"{result.total_warps} tiros".replace(",", ".")
        )
        projections = sequence_projections(
            self._strategy_goals(str(values["strategy"])), result.total_warps,
            character.five_star, character.guaranteed,
            cone.five_star, cone.guaranteed,
        )
        self._render_table(projections, result.total_warps)
        self.status.setText(
            f"Pity sincronizado da UID {uid}." if uid else
            "Nenhum histórico importado; pity considerado como zero."
        )

    @staticmethod
    def _set_guarantee(label: QLabel, guaranteed: bool) -> None:
        label.setText("✓  Garantido" if guaranteed else "✕  Disputa de rate-up")
        label.setProperty("guaranteed", guaranteed)
        label.style().unpolish(label)
        label.style().polish(label)

    @staticmethod
    def _strategy_goals(strategy: str) -> str:
        insertion = -1 if strategy == "S1" else int(strategy[1:])
        goals = ["S1"] if insertion == -1 else []
        for eidolon in range(7):
            goals.append(f"E{eidolon}")
            if eidolon == insertion:
                goals.append("S1")
        goals.extend(f"S{level}" for level in range(2, 6))
        return ",".join(goals)

    def _render_table(self, projections, budget: int) -> None:  # type: ignore[no-untyped-def]
        self.table.setRowCount(len(projections))
        for row, projection in enumerate(projections):
            chance = projection.chance * 100
            progress = QProgressBar()
            progress.setRange(0, 1000)
            progress.setValue(round(chance * 10))
            progress.setFormat(projection.label)
            progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
            progress.setProperty("chanceLevel", self._chance_level(chance))
            self.table.setCellWidget(row, 0, progress)
            chance_item = QTableWidgetItem(f"{chance:.1f}%".replace(".", ","))
            chance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, chance_item)
            values = (
                f"{projection.optimistic_warps} tiros",
                f"{math.ceil(projection.expected_warps)} tiros",
                f"{projection.pessimistic_warps} tiros",
            )
            for column, value in enumerate(values, start=2):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
            self.table.setRowHeight(row, 36)
        self.table.setFixedHeight(38 + 36 * max(1, len(projections)))
        self.table.horizontalHeaderItem(1).setText(
            f"Chance com {budget} tiros"
        )

    @staticmethod
    def _chance_level(chance: float) -> str:
        if chance >= 80:
            return "high"
        if chance >= 50:
            return "medium"
        if chance >= 15:
            return "low"
        return "critical"
