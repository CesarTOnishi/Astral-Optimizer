from __future__ import annotations

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from app.auth import AuthUser
from app.relics import RelicDatabase, StoredRelic
from app.ui.image_loader import ImageLoader
from app.ui.contextual_help import RELIC_GRADE_HELP, ContextHelpButton
from app.ui.widgets import (
    AvatarLabel, ElidedLabel, FadeComboBox, compact_stat_name,
    rounded_pixmap, stat_icon_label,
)


class InventoryRelicCard(QFrame):
    """Readable inventory card with each piece of data in a clear group."""

    def __init__(self, stored: StoredRelic) -> None:
        super().__init__()
        relic = stored.relic
        self.setObjectName("inventoryRelicCard")
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        moved = (
            stored.is_equipped and stored.previous_character_id
            and stored.previous_character_id != stored.current_character_id
        )
        state_text = "MOVIDA" if moved else ("EQUIPADA" if stored.is_equipped else "ANTERIOR")
        self.setProperty("relicState", state_text.casefold())

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 9, 12, 9)
        root.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.icon = AvatarLabel(58, rounded=False)
        header.addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignTop)

        identity = QVBoxLayout()
        identity.setSpacing(2)
        slot_row = QHBoxLayout()
        slot_row.setSpacing(5)
        slot = QLabel(relic.slot.upper())
        slot.setObjectName("inventoryRelicSlot")
        level = QLabel(f"+{relic.level}")
        level.setObjectName("inventoryRelicLevel")
        slot_row.addWidget(slot)
        slot_row.addStretch(1)
        slot_row.addWidget(level)
        set_name = ElidedLabel(relic.set_name)
        set_name.setObjectName("inventoryRelicSet")
        rarity = QLabel("★" * relic.rarity)
        rarity.setObjectName("inventoryRelicMeta")
        identity.addLayout(slot_row)
        identity.addWidget(set_name)
        identity.addWidget(rarity)
        header.addLayout(identity, 1)

        score = QVBoxLayout()
        score.setSpacing(2)
        score.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        grade = QLabel(stored.grade)
        grade.setObjectName("inventoryRelicGrade")
        grade.setProperty("scoreTier", stored.grade.casefold().replace("+", "plus"))
        value = QLabel(f"{stored.score:.1f}")
        value.setObjectName("inventoryRelicScore")
        value.setAlignment(Qt.AlignmentFlag.AlignRight)
        score.addWidget(grade, alignment=Qt.AlignmentFlag.AlignRight)
        score.addWidget(value, alignment=Qt.AlignmentFlag.AlignRight)
        header.addLayout(score)
        root.addLayout(header)

        holder_band = QFrame()
        holder_band.setObjectName("inventoryRelicHolderBand")
        holder_row = QHBoxLayout(holder_band)
        holder_row.setContentsMargins(7, 5, 7, 5)
        holder_row.setSpacing(6)
        self.holder_icon: AvatarLabel | None = None
        holder_name = stored.holder_name
        if holder_name:
            self.holder_icon = AvatarLabel(26)
            holder_row.addWidget(self.holder_icon)
        holder = ElidedLabel(holder_name or "Sem portador")
        holder.setObjectName("inventoryRelicHolder")
        if moved:
            holder.setToolTip(
                f"{holder_name}\nAnteriormente: {stored.previous_character_name}"
            )
        holder_row.addWidget(holder, 1)
        state = QLabel(state_text)
        state.setObjectName("inventoryRelicState")
        state.setProperty("relicState", state_text.casefold())
        holder_row.addWidget(state)
        root.addWidget(holder_band)

        main_band = QFrame()
        main_band.setObjectName("inventoryRelicMain")
        main_row = QHBoxLayout(main_band)
        main_row.setContentsMargins(9, 7, 9, 7)
        main_row.setSpacing(7)
        main_row.addWidget(stat_icon_label(relic.main_stat.key, 19))
        main_name = ElidedLabel(compact_stat_name(relic.main_stat.key, relic.main_stat.name))
        main_name.setObjectName("inventoryMainName")
        main_name.setToolTip(relic.main_stat.name)
        main_row.addWidget(main_name, 1)
        main_value = QLabel(relic.main_stat.formatted_value)
        main_value.setObjectName("inventoryMainValue")
        main_row.addWidget(main_value)
        root.addWidget(main_band)

        subheading = QLabel("SUBATRIBUTOS")
        subheading.setObjectName("inventoryRelicSubheading")
        root.addWidget(subheading)
        substats = QGridLayout()
        substats.setContentsMargins(0, 0, 0, 0)
        substats.setHorizontalSpacing(7)
        substats.setVerticalSpacing(7)
        for index, stat in enumerate(relic.sub_stats):
            cell = QFrame()
            cell.setObjectName("inventoryRelicSubCell")
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(7, 5, 7, 5)
            cell_layout.setSpacing(2)
            name_row = QHBoxLayout()
            name_row.setSpacing(4)
            name_row.addWidget(stat_icon_label(stat.key, 13))
            name = ElidedLabel(compact_stat_name(stat.key, stat.name))
            name.setObjectName("inventorySubName")
            name.setToolTip(stat.name)
            name_row.addWidget(name, 1)
            cell_layout.addLayout(name_row)
            value_row = QHBoxLayout()
            value_row.setSpacing(4)
            if stat.upgrades:
                upgrades = QLabel(f"+{stat.upgrades}")
                upgrades.setObjectName("inventoryUpgrade")
                value_row.addWidget(upgrades)
            value_row.addStretch(1)
            stat_value = QLabel(stat.formatted_value)
            stat_value.setObjectName("inventorySubValue")
            value_row.addWidget(stat_value)
            cell_layout.addLayout(value_row)
            substats.addWidget(cell, index // 2, index % 2)
        if not relic.sub_stats:
            unavailable = QLabel("Sem subatributos disponíveis")
            unavailable.setObjectName("inventoryRelicSubEmpty")
            substats.addWidget(unavailable, 0, 0, 1, 2)
        substats.setColumnStretch(0, 1)
        substats.setColumnStretch(1, 1)
        root.addLayout(substats)


class RelicInventoryPanel(QWidget):
    def __init__(
        self,
        database: RelicDatabase,
        image_loader: ImageLoader,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.database = database
        self.image_loader = image_loader
        self.user: AuthUser | None = None
        self._user_key: tuple[int, str] | None = None
        self.items: list[StoredRelic] = []
        self.cards: list[InventoryRelicCard] = []
        self._active = False
        self._dirty = True
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 3, 6, 0)
        outer.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Inventário de Relíquias")
        title.setObjectName("relicInventoryTitle")
        self.subtitle = QLabel("As relíquias observadas na UID principal ficam salvas aqui.")
        self.subtitle.setObjectName("muted")
        self.subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)
        header.addLayout(title_box)
        header.addWidget(
            ContextHelpButton(*RELIC_GRADE_HELP),
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        header.addStretch(1)
        self.total_chip = QLabel("0 SALVAS")
        self.total_chip.setObjectName("relicSummaryChip")
        self.equipped_chip = QLabel("0 EQUIPADAS")
        self.equipped_chip.setObjectName("relicSummaryChip")
        header.addWidget(self.total_chip, alignment=Qt.AlignmentFlag.AlignTop)
        header.addWidget(self.equipped_chip, alignment=Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)

        # Os combos precisam nascer ligados ao painel para seus popups não
        # aparecerem como pequenas janelas na barra de tarefas do Windows.
        filters = QFrame(self)
        filters.setObjectName("relicFilterPanel")
        filter_layout = QGridLayout(filters)
        self._filter_layout = filter_layout
        filter_layout.setContentsMargins(9, 7, 9, 7)
        filter_layout.setHorizontalSpacing(7)
        filter_layout.setVerticalSpacing(6)
        self.character_filter = FadeComboBox(filters)
        self.character_filter.setIconSize(QSize(26, 26))
        self.status_filter = FadeComboBox(filters)
        self.slot_filter = FadeComboBox(filters)
        self.relic_set_filter = FadeComboBox(filters)
        self.ornament_set_filter = FadeComboBox(filters)
        self.sort_filter = FadeComboBox(filters)
        self.relic_set_filter.setIconSize(QSize(26, 26))
        self.ornament_set_filter.setIconSize(QSize(26, 26))
        for combo in (
            self.character_filter, self.status_filter, self.slot_filter,
            self.relic_set_filter, self.ornament_set_filter, self.sort_filter,
        ):
            combo.setMinimumContentsLength(8)
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.status_filter.addItem("Todas", "all")
        self.status_filter.addItem("Equipadas agora", "equipped")
        self.status_filter.addItem("Não vistas agora", "previous")
        self.status_filter.addItem("Movidas", "moved")
        self.sort_filter.addItem("Melhor pontuação", "score_desc")
        self.sort_filter.addItem("Menor pontuação", "score_asc")
        self.sort_filter.addItem("Atualizadas recentemente", "recent")
        self.sort_filter.addItem("Personagem A–Z", "character")
        self._filter_widgets = [
            self._filter_box("PERSONAGEM", self.character_filter, filters),
            self._filter_box("SITUAÇÃO", self.status_filter, filters),
            self._filter_box("PARTE", self.slot_filter, filters),
            self._filter_box("CONJUNTO", self.relic_set_filter, filters),
            self._filter_box("ORNAMENTOS", self.ornament_set_filter, filters),
            self._filter_box("ORDENAR", self.sort_filter, filters),
        ]
        self._filter_columns = 0
        # Comece com uma grade intermediária para não impor uma largura mínima
        # enorme antes do primeiro resizeEvent da janela.
        self._layout_filters(3)
        outer.addWidget(filters)

        self.status = QLabel("Entre em uma conta para abrir o inventário.")
        self.status.setObjectName("statusInfo")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.result_count = QLabel("0 relíquias")
        self.result_count.setObjectName("relicResultCount")
        result_bar = QHBoxLayout()
        result_bar.addWidget(self.result_count)
        result_bar.addStretch(1)
        self.clear_filters = QPushButton("Limpar filtros")
        self.clear_filters.setObjectName("relicClearFilters")
        self.clear_filters.setVisible(False)
        self.clear_filters.clicked.connect(self._reset_filters)
        result_bar.addWidget(self.clear_filters)
        outer.addLayout(result_bar)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("relicInventoryScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.content.setObjectName("scrollContent")
        self.grid = QGridLayout(self.content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid.setContentsMargins(2, 2, 2, 12)
        self.grid.setHorizontalSpacing(9)
        self.grid.setVerticalSpacing(9)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll, 1)

        for combo in (
            self.character_filter, self.status_filter, self.slot_filter,
            self.relic_set_filter, self.ornament_set_filter, self.sort_filter,
        ):
            combo.currentIndexChanged.connect(self._filters_changed)

    @staticmethod
    def _filter_box(title: str, combo: QComboBox, parent: QWidget) -> QWidget:
        widget = QWidget(parent)
        widget.setObjectName("relicFilterItem")
        widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        label = QLabel(title)
        label.setObjectName("metricTitle")
        box = QVBoxLayout(widget)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        box.addWidget(label)
        box.addWidget(combo)
        return widget

    def _layout_filters(self, columns: int) -> None:
        if columns == self._filter_columns:
            return
        self._filter_columns = columns
        while self._filter_layout.count():
            self._filter_layout.takeAt(0)
        for index, widget in enumerate(self._filter_widgets):
            self._filter_layout.addWidget(widget, index // columns, index % columns)
        for column in range(6):
            self._filter_layout.setColumnStretch(column, 1 if column < columns else 0)

    def _filters_changed(self, *_args) -> None:
        active = any(
            str(combo.currentData() or "all") != default
            for combo, default in (
                (self.character_filter, "all"), (self.status_filter, "all"),
                (self.slot_filter, "all"), (self.relic_set_filter, "all"),
                (self.ornament_set_filter, "all"),
                (self.sort_filter, "score_desc"),
            )
        )
        self.clear_filters.setVisible(active)
        self._render()

    def _reset_filters(self) -> None:
        filters = (
            (self.character_filter, "all"), (self.status_filter, "all"),
            (self.slot_filter, "all"), (self.relic_set_filter, "all"),
            (self.ornament_set_filter, "all"),
            (self.sort_filter, "score_desc"),
        )
        for combo, value in filters:
            combo.blockSignals(True)
            index = combo.findData(value)
            combo.setCurrentIndex(max(index, 0))
            combo.blockSignals(False)
        self._filters_changed()

    def set_user(self, user: AuthUser | None) -> None:
        previous = self._user_key
        current = (user.id, user.game_uid) if user is not None else None
        self.user = user
        self._user_key = current
        if previous == current:
            return
        self._dirty = True
        self.items = []
        self._clear_grid()
        if self._active:
            self.refresh()

    @property
    def has_cached_view(self) -> bool:
        return not self._dirty

    def set_active(self, active: bool) -> None:
        self._active = active
        if active and self._dirty:
            self.refresh()

    def mark_dirty(self) -> None:
        self._dirty = True
        if self._active:
            self.refresh()

    def refresh(self) -> None:
        if not self._active:
            self._dirty = True
            return
        user = self.user
        if user is None:
            self.items = []
            self.subtitle.setText("Inventário separado para cada perfil local.")
            self.status.setText("Entre em uma conta para abrir o inventário.")
        elif not user.game_uid:
            self.items = []
            self.subtitle.setText("Nenhuma UID principal configurada.")
            self.status.setText("Defina sua UID principal nas configurações.")
        else:
            self.items = self.database.relics(user.id, user.game_uid)
            equipped = sum(item.is_equipped for item in self.items)
            self.subtitle.setText(
                f"UID {user.game_uid} · {len(self.items)} peças salvas · "
                f"{equipped} equipadas no último Showcase"
            )
            self.status.setText(
                "Ordenadas da maior para a menor pontuação. "
                "Abra Conta para atualizar o Showcase."
                if self.items else
                "Abra Conta para registrar as relíquias dos personagens públicos."
            )
        equipped = sum(item.is_equipped for item in self.items)
        self.total_chip.setText(f"{len(self.items)} SALVAS")
        self.equipped_chip.setText(f"{equipped} EQUIPADAS")
        self.status.setVisible(not bool(self.items))
        self._dirty = False
        self._populate_filters()
        self._filters_changed()

    def _clear_grid(self) -> None:
        self._grid_signature = None
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.cards = []

    @staticmethod
    def _set_options(
        combo: QComboBox, options: list[tuple[str, str]], default: str
    ) -> None:
        selected = str(combo.currentData() or default)
        combo.blockSignals(True)
        combo.clear()
        for label, value in options:
            combo.addItem(label, value)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _populate_filters(self) -> None:
        characters: dict[str, tuple[str, str]] = {}
        slots: set[str] = set()
        relic_sets: dict[str, str] = {}
        ornament_sets: dict[str, str] = {}
        for item in self.items:
            if item.current_character_id:
                characters[item.current_character_id] = (
                    item.current_character_name, item.current_character_icon
                )
            if item.previous_character_id:
                characters[item.previous_character_id] = (
                    item.previous_character_name, item.previous_character_icon
                )
            slots.add(item.relic.slot)
            target = ornament_sets if self._is_ornament(item) else relic_sets
            target.setdefault(item.relic.set_name, item.relic.icon_url)
        self._set_options(
            self.character_filter,
            [("Todos os personagens", "all")] + [
                (data[0], character_id)
                for character_id, data in sorted(
                    characters.items(), key=lambda entry: entry[1][0].casefold()
                )
            ],
            "all",
        )
        for character_id, (_name, icon_url) in characters.items():
            self.image_loader.load(
                icon_url,
                lambda pixmap, current_id=character_id:
                self._set_character_filter_icon(current_id, pixmap),
            )
        self._set_options(
            self.slot_filter,
            [("Todas as partes", "all")] + [(name, name) for name in sorted(slots)],
            "all",
        )
        self._populate_set_filter(
            self.relic_set_filter, "Todos os conjuntos de relíquias", relic_sets
        )
        self._populate_set_filter(
            self.ornament_set_filter,
            "Todos os conjuntos de ornamentos",
            ornament_sets,
        )

    def _populate_set_filter(
        self, combo: QComboBox, default_label: str, sets: dict[str, str]
    ) -> None:
        self._set_options(
            combo,
            [(default_label, "all")] + [(name, name) for name in sorted(sets)],
            "all",
        )
        for set_name, icon_url in sets.items():
            self.image_loader.load(
                icon_url,
                lambda pixmap, target=combo, name=set_name:
                self._set_combo_icon(target, name, pixmap, 6),
            )

    def _set_character_filter_icon(
        self, character_id: str, pixmap: QPixmap
    ) -> None:
        if pixmap.isNull():
            return
        index = self.character_filter.findData(character_id)
        if index < 0:
            return
        circular = rounded_pixmap(pixmap, 26, 13)
        self.character_filter.setItemIcon(index, QIcon(circular))

    @staticmethod
    def _set_combo_icon(
        combo: QComboBox, value: str, pixmap: QPixmap, radius: int
    ) -> None:
        if pixmap.isNull():
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setItemIcon(index, QIcon(rounded_pixmap(pixmap, 26, radius)))

    @staticmethod
    def _is_ornament(item: StoredRelic) -> bool:
        return item.relic.slot_key.upper() in {"ORBIT", "ROPE"}

    def _filtered_items(self) -> list[StoredRelic]:
        character_id = str(self.character_filter.currentData() or "all")
        status = str(self.status_filter.currentData() or "all")
        slot = str(self.slot_filter.currentData() or "all")
        relic_set = str(self.relic_set_filter.currentData() or "all")
        ornament_set = str(self.ornament_set_filter.currentData() or "all")
        items = list(self.items)
        if character_id != "all":
            items = [
                item for item in items
                if character_id in {
                    item.current_character_id, item.previous_character_id,
                }
            ]
        if status == "equipped":
            items = [item for item in items if item.is_equipped]
        elif status == "previous":
            items = [item for item in items if not item.is_equipped]
        elif status == "moved":
            items = [
                item for item in items
                if item.is_equipped and item.previous_character_id
                and item.previous_character_id != item.current_character_id
            ]
        if slot != "all":
            items = [item for item in items if item.relic.slot == slot]
        selected_sets = {value for value in (relic_set, ornament_set) if value != "all"}
        if selected_sets:
            items = [item for item in items if item.relic.set_name in selected_sets]

        sorting = str(self.sort_filter.currentData() or "score_desc")
        if sorting == "score_asc":
            items.sort(key=lambda item: (item.score, item.last_seen))
        elif sorting == "recent":
            items.sort(key=lambda item: item.last_seen, reverse=True)
        elif sorting == "character":
            items.sort(key=lambda item: (item.holder_name.casefold(), -item.score))
        else:
            items.sort(key=lambda item: (item.score, item.last_seen), reverse=True)
        return items

    def _render(self) -> None:
        self._clear_grid()
        items = self._filtered_items()
        self.result_count.setText(
            f"{len(items)} de {len(self.items)} relíquias exibidas"
        )
        if not items:
            empty = QLabel(
                "Nenhuma relíquia encontrada. Ajuste os filtros ou atualize sua conta para importar o inventário."
            )
            empty.setObjectName("relicInventoryEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self.grid.addWidget(empty, 0, 0)
            return
        for stored in items:
            card = InventoryRelicCard(stored)
            card.setToolTip(
                f"Vista pela primeira vez: {stored.first_seen}\n"
                f"Última atualização: {stored.last_seen}"
            )
            self.cards.append(card)
            self.image_loader.load(stored.relic.icon_url, card.icon.set_image)
            if card.holder_icon is not None:
                self.image_loader.load(stored.holder_icon, card.holder_icon.set_image)
        self._reflow()

    def _reflow(self) -> None:
        if not self.cards:
            return
        margins = self.grid.contentsMargins()
        available = max(
            self.scroll.viewport().width() - margins.left() - margins.right(),
            300,
        )
        spacing = self.grid.horizontalSpacing()
        columns = max(1, min(4, (available + spacing) // (300 + spacing)))
        signature = (columns, tuple(id(card) for card in self.cards))
        if signature == getattr(self, "_grid_signature", None):
            return
        self._grid_signature = signature
        while self.grid.count():
            self.grid.takeAt(0)
        for column in range(4):
            self.grid.setColumnStretch(column, 0)
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns)
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        width = self.width()
        # Duas linhas no desktop mantêm os textos legíveis sem devolver ao
        # painel a altura das três linhas antigas.
        self._layout_filters(3 if width >= 680 else 2)
        QTimer.singleShot(0, self._reflow)
