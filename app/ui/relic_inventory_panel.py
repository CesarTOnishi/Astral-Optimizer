from __future__ import annotations

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea,
    QVBoxLayout, QWidget,
)

from app.auth import AuthUser
from app.benchmark.models import RelicRating
from app.relics import RelicDatabase, StoredRelic
from app.ui.image_loader import ImageLoader
from app.ui.widgets import FadeComboBox, RelicCard, rounded_pixmap


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
        self.items: list[StoredRelic] = []
        self.cards: list[RelicCard] = []
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
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        outer.addLayout(header)

        # Os combos precisam nascer ligados ao painel para seus popups não
        # aparecerem como pequenas janelas na barra de tarefas do Windows.
        filters = QFrame(self)
        filters.setObjectName("relicFilterPanel")
        filter_layout = QGridLayout(filters)
        filter_layout.setContentsMargins(12, 9, 12, 9)
        filter_layout.setHorizontalSpacing(10)
        filter_layout.setVerticalSpacing(7)
        self.character_filter = FadeComboBox(filters)
        self.character_filter.setIconSize(QSize(26, 26))
        self.status_filter = FadeComboBox(filters)
        self.slot_filter = FadeComboBox(filters)
        self.relic_set_filter = FadeComboBox(filters)
        self.ornament_set_filter = FadeComboBox(filters)
        self.sort_filter = FadeComboBox(filters)
        self.relic_set_filter.setIconSize(QSize(26, 26))
        self.ornament_set_filter.setIconSize(QSize(26, 26))
        self.status_filter.addItem("Todas", "all")
        self.status_filter.addItem("Equipadas agora", "equipped")
        self.status_filter.addItem("Não vistas agora", "previous")
        self.status_filter.addItem("Movidas", "moved")
        self.sort_filter.addItem("Melhor pontuação", "score_desc")
        self.sort_filter.addItem("Menor pontuação", "score_asc")
        self.sort_filter.addItem("Atualizadas recentemente", "recent")
        self.sort_filter.addItem("Personagem A–Z", "character")
        filter_layout.addLayout(self._filter_box("PERSONAGEM", self.character_filter), 0, 0)
        filter_layout.addLayout(self._filter_box("SITUAÇÃO", self.status_filter), 0, 1)
        filter_layout.addLayout(
            self._filter_box("CONJUNTO DE RELÍQUIAS", self.relic_set_filter), 1, 0
        )
        filter_layout.addLayout(
            self._filter_box("CONJUNTO DE ORNAMENTOS", self.ornament_set_filter), 1, 1
        )
        filter_layout.addLayout(self._filter_box("PARTE", self.slot_filter), 2, 0)
        filter_layout.addLayout(self._filter_box("ORDENAR", self.sort_filter), 2, 1)
        for column in range(2):
            filter_layout.setColumnStretch(column, 1)
        outer.addWidget(filters)

        self.status = QLabel("Entre em uma conta para abrir o inventário.")
        self.status.setObjectName("statusInfo")
        outer.addWidget(self.status)
        self.result_count = QLabel("0 relíquias")
        self.result_count.setObjectName("relicResultCount")
        outer.addWidget(self.result_count)

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
            combo.currentIndexChanged.connect(self._render)

    @staticmethod
    def _filter_box(title: str, combo: QComboBox) -> QVBoxLayout:
        label = QLabel(title)
        label.setObjectName("metricTitle")
        box = QVBoxLayout()
        box.setSpacing(3)
        box.addWidget(label)
        box.addWidget(combo)
        return box

    def set_user(self, user: AuthUser | None) -> None:
        previous = (
            (self.user.id, self.user.game_uid) if self.user is not None else None
        )
        self.user = user
        current = (user.id, user.game_uid) if user is not None else None
        self._dirty = True
        if self._active:
            self.refresh()
        elif previous != current:
            self.items = []
            self._clear_grid()

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
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
        self._dirty = False
        self._populate_filters()
        self._render()

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
            self.grid.addWidget(empty, 0, 0)
            return
        for stored in items:
            card = RelicCard(
                stored.relic,
                RelicRating(stored.score, stored.grade),
                holder_name=stored.current_character_name,
                previous_holder_name=stored.previous_character_name,
            )
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
        available = max(self.scroll.viewport().width() - 8, 205)
        columns = max(1, min(4, available // 224))
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
        QTimer.singleShot(0, self._reflow)
