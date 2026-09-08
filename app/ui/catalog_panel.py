from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.catalog import (
    CatalogCharacter,
    CatalogLightCone,
    CatalogRepository,
    CatalogSkill,
    CatalogSyncWorker,
    CatalogTrace,
)
from app.ui.image_loader import ImageLoader
from app.ui.widgets import FadeComboBox, FRIBBELS_ASSETS


CATALOG_PATH_ICONS = {
    "Knight": "Preservation", "Rogue": "Hunt", "Mage": "Erudition",
    "Shaman": "Harmony", "Warlock": "Nihility", "Warrior": "Destruction",
    "Priest": "Abundance", "Memory": "Remembrance", "Elation": "Elation",
}
CATALOG_ELEMENT_ICONS = {"Thunder": "Lightning"}


class CatalogCard(QFrame):
    clicked = Signal(object)

    def __init__(
        self,
        entry: CatalogCharacter | CatalogLightCone,
        image_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.entry = entry
        self.is_light_cone = isinstance(entry, CatalogLightCone)
        self.setObjectName("catalogCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(150)
        self.setMaximumWidth(220)
        self.setFixedHeight(218)
        self.setToolTip(entry.name)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        art = QFrame()
        art.setObjectName("catalogCardArt")
        art.setFixedHeight(151)
        art_layout = QGridLayout(art)
        art_layout.setContentsMargins(0, 0, 0, 0)
        self.image = QLabel()
        self.image.setObjectName("catalogCardImage")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setFixedHeight(151)
        self.image.setText("◇")
        self.image_loaded = False

        kind = QLabel("CONE" if self.is_light_cone else "PERSONAGEM")
        kind.setObjectName("catalogCardKind")
        rarity = QLabel(f"{max(entry.rarity, 0)}★")
        rarity.setObjectName("catalogCardRarity")
        art_layout.addWidget(self.image, 0, 0, 1, 2)
        art_layout.addWidget(
            kind, 0, 0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )
        art_layout.addWidget(
            rarity, 0, 1,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )

        footer = QFrame()
        footer.setObjectName("catalogCardFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(9, 7, 9, 8)
        footer_layout.setSpacing(3)
        name = QLabel(entry.name)
        name.setObjectName("catalogCardName")
        name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        name.setWordWrap(True)
        name.setFixedHeight(31)

        meta = QHBoxLayout()
        meta.setSpacing(5)
        path_icon = self._meta_icon(
            "path", CATALOG_PATH_ICONS.get(entry.path, entry.path), entry.path_name
        )
        path = QLabel(entry.path_name)
        path.setObjectName("catalogCardMeta")
        meta.addWidget(path_icon)
        meta.addWidget(path)
        meta.addStretch(1)
        if isinstance(entry, CatalogCharacter):
            element_key = CATALOG_ELEMENT_ICONS.get(entry.element, entry.element)
            meta.addWidget(self._meta_icon("element", element_key, entry.element_name))

        footer_layout.addWidget(name)
        footer_layout.addLayout(meta)
        layout.addWidget(art)
        layout.addWidget(footer, 1)

    @staticmethod
    def _meta_icon(kind: str, key: str, tooltip: str) -> QLabel:
        icon = QLabel()
        icon.setObjectName("catalogCardMetaIcon")
        icon.setFixedSize(18, 18)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setToolTip(tooltip)
        path = FRIBBELS_ASSETS / "icon" / kind / f"{key}.webp"
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            icon.setPixmap(pixmap.scaled(
                QSize(15, 15),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        return icon

    def set_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            self.image.setText("◇")
            return
        self.image.setPixmap(pixmap.scaled(
            QSize(218, 151),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        ))
        self.image_loaded = True

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - API Qt
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.entry)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class InfoCard(QFrame):
    def __init__(
        self,
        badge: str,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("catalogInfoCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(11, 10, 12, 11)
        layout.setSpacing(11)
        marker_text = badge if badge.startswith("E") else badge[:3]
        self.marker = QLabel(marker_text)
        self.marker.setObjectName("catalogInfoBadge")
        self.marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.marker.setFixedSize(46, 46)
        text = QVBoxLayout()
        text.setSpacing(3)
        kind = QLabel(badge)
        kind.setObjectName("catalogInfoKind")
        heading = QLabel(title)
        heading.setObjectName("catalogInfoTitle")
        heading.setWordWrap(True)
        body = QLabel(description or "Descrição indisponível nesta fonte.")
        body.setObjectName("catalogInfoText")
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text.addWidget(kind, alignment=Qt.AlignmentFlag.AlignLeft)
        text.addWidget(heading)
        text.addWidget(body)
        layout.addWidget(self.marker, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text, 1)

    def set_icon(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self.marker.setText("")
        self.marker.setPixmap(pixmap.scaled(
            QSize(34, 34),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))


class CatalogPanel(QWidget):
    background_sync_changed = Signal(bool, str)
    catalog_updated = Signal(str)

    def __init__(
        self,
        image_loader: ImageLoader,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("catalogPage")
        self.image_loader = image_loader
        self.repository = CatalogRepository()
        self.sync_worker: CatalogSyncWorker | None = None
        self.sync_failed = False
        self.mode = "characters"
        self.cards: list[CatalogCard] = []
        self.card_cache: dict[str, dict[str, CatalogCard]] = {
            "characters": {}, "light_cones": {},
        }
        self._image_queue: list[tuple[CatalogCard, Path, str]] = []
        self._queued_images: set[int] = set()
        self._active = False
        self._built_once = False
        self._selected_cone: CatalogLightCone | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 3, 6, 0)
        outer.setSpacing(10)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("PERSONAGENS E CONES")
        title.setObjectName("catalogTitle")
        subtitle = QLabel("Conheça habilidades, eidolons, atributos e efeitos.")
        subtitle.setObjectName("muted")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch(1)
        self.sync_button = QPushButton("↻  Atualizar catálogo")
        self.sync_button.setObjectName("secondaryButton")
        self.sync_button.clicked.connect(self.synchronize)
        header.addWidget(self.sync_button)
        outer.addLayout(header)

        self.status = QLabel("Catálogo básico local pronto.")
        self.status.setObjectName("statusInfo")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)

        self.stack = QStackedWidget()
        self.list_page = QWidget()
        list_layout = QVBoxLayout(self.list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(9)

        controls = QFrame(self.list_page)
        controls.setObjectName("catalogControls")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(10, 9, 10, 9)
        controls_layout.setSpacing(8)
        tabs = QHBoxLayout()
        tabs.setSpacing(5)
        self.character_button = QPushButton("Personagens")
        self.cone_button = QPushButton("Cones de Luz")
        for button in (self.character_button, self.cone_button):
            button.setObjectName("catalogTabButton")
            button.setCheckable(True)
            tabs.addWidget(button)
        self.character_button.setChecked(True)
        self.character_button.clicked.connect(lambda: self.set_mode("characters"))
        self.cone_button.clicked.connect(lambda: self.set_mode("light_cones"))
        self.search = QLineEdit()
        self.search.setObjectName("catalogSearch")
        self.search.setPlaceholderText("Pesquisar por nome…")
        self.path_filter = FadeComboBox(controls)
        self.rarity_filter = FadeComboBox(controls)
        self.rarity_filter.addItem("Todas as raridades", 0)
        self.rarity_filter.addItem("5 estrelas", 5)
        self.rarity_filter.addItem("4 estrelas", 4)
        self.rarity_filter.addItem("3 estrelas", 3)
        controls_layout.addLayout(tabs, 0, 0, 1, 2)
        controls_layout.addWidget(self.search, 0, 2, 1, 2)
        controls_layout.addWidget(self.path_filter, 1, 0, 1, 2)
        controls_layout.addWidget(self.rarity_filter, 1, 2, 1, 2)
        for column in range(4):
            controls_layout.setColumnStretch(column, 1)
        list_layout.addWidget(controls)

        self.result_count = QLabel()
        self.result_count.setObjectName("catalogResultCount")
        list_layout.addWidget(self.result_count)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("catalogScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.grid_content = QWidget()
        self.grid_content.setObjectName("catalogGridContent")
        self.grid = QGridLayout(self.grid_content)
        self.grid.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.grid.setContentsMargins(2, 2, 6, 12)
        self.grid.setSpacing(9)
        self.scroll.setWidget(self.grid_content)
        list_layout.addWidget(self.scroll, 1)
        self.stack.addWidget(self.list_page)

        self.detail_page = QWidget()
        detail_outer = QVBoxLayout(self.detail_page)
        detail_outer.setContentsMargins(0, 0, 0, 0)
        self.back_button = QPushButton("‹  Voltar ao catálogo")
        self.back_button.setObjectName("catalogBackButton")
        self.back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.list_page))
        detail_outer.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setObjectName("catalogDetailScroll")
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail_content = QWidget()
        self.detail_content.setObjectName("catalogDetailContent")
        self.detail_layout = QVBoxLayout(self.detail_content)
        self.detail_layout.setContentsMargins(4, 2, 8, 18)
        self.detail_layout.setSpacing(10)
        self.detail_scroll.setWidget(self.detail_content)
        detail_outer.addWidget(self.detail_scroll, 1)
        self.stack.addWidget(self.detail_page)
        outer.addWidget(self.stack, 1)

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(120)
        self._render_timer.timeout.connect(self._render)
        self._image_timer = QTimer(self)
        self._image_timer.setInterval(8)
        self._image_timer.timeout.connect(self._load_next_card_image)
        self.search.textChanged.connect(lambda: self._render_timer.start())
        self.path_filter.currentIndexChanged.connect(lambda: self._render_timer.start())
        self.rarity_filter.currentIndexChanged.connect(lambda: self._render_timer.start())

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            return
        if not self._built_once:
            self._built_once = True
            self._populate_filters()
            self._render()
            if not self.repository.has_details:
                QTimer.singleShot(250, self.synchronize)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.character_button.setChecked(mode == "characters")
        self.cone_button.setChecked(mode == "light_cones")
        self._populate_filters()
        self._render()

    def _populate_filters(self) -> None:
        selected = str(self.path_filter.currentData() or "all")
        entries = self.repository.characters() if self.mode == "characters" else self.repository.light_cones()
        paths = sorted({(entry.path, entry.path_name) for entry in entries}, key=lambda item: item[1])
        self.path_filter.blockSignals(True)
        self.path_filter.clear()
        self.path_filter.addItem("Todos os Caminhos", "all")
        for value, label in paths:
            self.path_filter.addItem(label, value)
        index = self.path_filter.findData(selected)
        self.path_filter.setCurrentIndex(index if index >= 0 else 0)
        self.path_filter.blockSignals(False)

    def _entries(self) -> list[CatalogCharacter | CatalogLightCone]:
        entries: list[CatalogCharacter | CatalogLightCone]
        entries = list(self.repository.characters() if self.mode == "characters" else self.repository.light_cones())
        query = self.search.text().strip().casefold()
        path = str(self.path_filter.currentData() or "all")
        rarity = int(self.rarity_filter.currentData() or 0)
        if query:
            entries = [entry for entry in entries if query in entry.name.casefold()]
        if path != "all":
            entries = [entry for entry in entries if entry.path == path]
        if rarity:
            entries = [entry for entry in entries if entry.rarity == rarity]
        return entries

    def _clear_layout(self, layout: QVBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child is not None:
                self._clear_layout(child)  # type: ignore[arg-type]

    def _render(self) -> None:
        if not self._active:
            return
        self._detach_grid_cards()
        self.cards.clear()
        entries = self._entries()
        label = "personagens" if self.mode == "characters" else "cones"
        self.result_count.setText(f"{len(entries)} {label} encontrados")
        if not entries:
            empty = QLabel("Nenhum resultado encontrado.")
            empty.setObjectName("catalogEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid.addWidget(empty, 0, 0)
            return
        available = max(self.scroll.viewport().width() - 12, 160)
        columns = max(1, min(6, available // 166))
        mode_cache = self.card_cache[self.mode]
        for index, entry in enumerate(entries):
            card = mode_cache.get(entry.id)
            if card is None:
                image_path = (
                    self.repository.character_image(entry.id)
                    if isinstance(entry, CatalogCharacter)
                    else self.repository.light_cone_image(entry.id)
                )
                if not image_path.is_file():
                    image_path = (
                        self.repository.character_icon(entry.id)
                        if isinstance(entry, CatalogCharacter)
                        else self.repository.light_cone_icon(entry.id)
                    )
                card = CatalogCard(entry, image_path)
                card.clicked.connect(self.open_entry)
                mode_cache[entry.id] = card
                self._queue_card_image(card, image_path, entry.preview or entry.icon)
            self.cards.append(card)
            self.grid.addWidget(card, index // columns, index % columns)
            card.show()
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)
        visible_cards = {id(card) for card in self.cards}
        self._image_queue.sort(
            key=lambda pending: 0 if id(pending[0]) in visible_cards else 1
        )

    def _detach_grid_cards(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()

    def _queue_card_image(self, card: CatalogCard, path: Path, remote: str) -> None:
        key = id(card)
        if card.image_loaded or key in self._queued_images:
            return
        self._queued_images.add(key)
        self._image_queue.append((card, path, remote))
        if not self._image_timer.isActive():
            self._image_timer.start()

    def _load_next_card_image(self) -> None:
        if not self._image_queue:
            self._image_timer.stop()
            return
        card, path, remote = self._image_queue.pop(0)
        self._queued_images.discard(id(card))
        try:
            if path.is_file():
                card.set_pixmap(QPixmap(str(path)))
            elif remote:
                self._load_remote(remote, card.set_pixmap)
        except RuntimeError:
            return

    def open_entry(self, value: object) -> None:
        self._clear_layout(self.detail_layout)
        if isinstance(value, CatalogCharacter):
            self._build_character_detail(value)
        elif isinstance(value, CatalogLightCone):
            self._build_cone_detail(value)
        else:
            return
        self.detail_layout.addStretch(1)
        self.detail_scroll.verticalScrollBar().setValue(0)
        self.stack.setCurrentWidget(self.detail_page)

    def _hero(
        self,
        name: str,
        meta: str,
        rarity: int,
        image_path: Path,
        remote: str,
        *,
        complete_art: bool = False,
    ) -> QFrame:
        hero = QFrame()
        hero.setObjectName("catalogHero")
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(12, 12, 16, 12)
        hero_image = QLabel("◇")
        hero_image.setObjectName("catalogConeHeroImage" if complete_art else "catalogHeroImage")
        hero_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_image.setFixedSize(210, 293 if complete_art else 230)
        pixmap = QPixmap(str(image_path)) if image_path.is_file() else QPixmap()
        self._set_detail_pixmap(hero_image, pixmap, expand=not complete_art)
        if pixmap.isNull():
            self._load_remote(
                remote,
                lambda loaded, target=hero_image, expand=not complete_art:
                self._set_detail_pixmap(target, loaded, expand=expand),
            )
        text = QVBoxLayout()
        title = QLabel(name)
        title.setObjectName("catalogDetailName")
        title.setWordWrap(True)
        stars = QLabel("★" * rarity)
        stars.setObjectName("catalogDetailStars")
        details = QLabel(meta)
        details.setObjectName("catalogDetailMeta")
        details.setWordWrap(True)
        text.addStretch(1)
        text.addWidget(title)
        text.addWidget(stars)
        text.addWidget(details)
        text.addStretch(1)
        layout.addWidget(hero_image, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(text, 1)
        return hero

    @staticmethod
    def _set_detail_pixmap(label: QLabel, pixmap: QPixmap, *, expand: bool) -> None:
        if pixmap.isNull():
            return
        label.setPixmap(pixmap.scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding
            if expand else Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def _build_character_detail(self, character: CatalogCharacter) -> None:
        skills = self._deduplicate_character_skills(
            self.repository.skills_for(character)
        )
        traces = self.repository.traces_for(character)
        ranks = self.repository.ranks_for(character)
        self.detail_layout.addWidget(self._character_hero(
            character, len(skills), len(traces), len(ranks)
        ))

        skill_cards: list[InfoCard] = []
        for skill in skills:
            params = skill.parameters[-1] if skill.parameters else []
            card = InfoCard(
                skill.type_name.upper(), skill.name,
                self.repository.format_description(skill.description, params),
            )
            self._load_remote(skill.icon, card.set_icon)
            skill_cards.append(card)
        skill_page = (
            self._info_section(
                "KIT PRINCIPAL",
                "Habilidades e variações do personagem no nível máximo.",
                skill_cards,
            ) if skill_cards else self._details_missing()
        )

        trace_page = QWidget()
        trace_layout = QVBoxLayout(trace_page)
        trace_layout.setContentsMargins(0, 0, 0, 0)
        trace_layout.setSpacing(9)
        major_trace_cards: list[InfoCard] = []
        stat_trace_cards: list[InfoCard] = []
        for trace in traces:
            card = InfoCard(
                "BÔNUS" if trace.is_stat_bonus else "RASTRO",
                trace.name,
                self._trace_description(trace),
            )
            self._load_remote(trace.icon, card.set_icon)
            (stat_trace_cards if trace.is_stat_bonus else major_trace_cards).append(card)
        if major_trace_cards:
            trace_layout.addWidget(self._info_section(
                "RASTROS PRINCIPAIS",
                "Novas passivas desbloqueadas durante a progressão.",
                major_trace_cards,
            ))
        if stat_trace_cards:
            trace_layout.addWidget(self._info_section(
                "BÔNUS DE ATRIBUTO",
                "Atributos permanentes concedidos pela árvore de Rastros.",
                stat_trace_cards,
            ))
        if not traces:
            trace_layout.addWidget(self._details_missing())

        rank_cards: list[InfoCard] = []
        for rank in ranks:
            params = rank.parameters[-1] if rank.parameters else []
            card = InfoCard(
                f"E{rank.rank}", rank.name,
                self.repository.format_description(rank.description, params),
            )
            self._load_remote(rank.icon, card.set_icon)
            rank_cards.append(card)
        rank_page = (
            self._info_section(
                "EIDOLONS",
                "Efeitos adicionais desbloqueados por Eidolon.",
                rank_cards,
            ) if rank_cards else self._details_missing()
        )

        self.detail_layout.addWidget(self._character_detail_tabs([
            ("Kit principal", skill_page),
            ("Rastros", trace_page),
            ("Eidolons", rank_page),
        ]))

    def _character_hero(
        self,
        character: CatalogCharacter,
        skill_count: int,
        trace_count: int,
        rank_count: int,
    ) -> QFrame:
        hero = QFrame()
        hero.setObjectName("characterAnalysisPanel")
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(14, 14, 18, 14)
        layout.setSpacing(18)

        art = QLabel("◇")
        art.setObjectName("characterAnalysisArt")
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art.setFixedSize(255, 335)
        image_path = self.repository.character_image(character.id, portrait=True)
        if not image_path.is_file():
            image_path = self.repository.character_image(character.id)
        pixmap = QPixmap(str(image_path)) if image_path.is_file() else QPixmap()
        self._set_detail_pixmap(art, pixmap, expand=True)
        if pixmap.isNull():
            self._load_remote(
                character.portrait or character.preview,
                lambda loaded, target=art: self._set_detail_pixmap(
                    target, loaded, expand=True
                ),
            )
        layout.addWidget(art, alignment=Qt.AlignmentFlag.AlignTop)

        information = QVBoxLayout()
        information.setSpacing(8)
        eyebrow = QLabel("ARQUIVO DO PERSONAGEM")
        eyebrow.setObjectName("characterAnalysisEyebrow")
        title = QLabel(character.name)
        title.setObjectName("catalogDetailName")
        title.setWordWrap(True)
        stars = QLabel("★" * character.rarity)
        stars.setObjectName("catalogDetailStars")
        information.addWidget(eyebrow)
        information.addWidget(title)
        information.addWidget(stars)

        identity = QHBoxLayout()
        identity.setSpacing(7)
        identity.addWidget(self._identity_chip(
            "element",
            CATALOG_ELEMENT_ICONS.get(character.element, character.element),
            character.element_name,
        ))
        identity.addWidget(self._identity_chip(
            "path",
            CATALOG_PATH_ICONS.get(character.path, character.path),
            character.path_name,
        ))
        identity.addStretch(1)
        information.addLayout(identity)

        summary = QGridLayout()
        summary.setSpacing(7)
        summary_items = [
            "NÍVEL 80",
            f"{skill_count} HABILIDADES",
            f"{trace_count} RASTROS",
            f"{rank_count} EIDOLONS",
            f"ID {character.id}",
        ]
        for index, text in enumerate(summary_items):
            badge = QLabel(text)
            badge.setObjectName("characterSummaryBadge")
            summary.addWidget(badge, index // 3, index % 3)
        summary.setColumnStretch(3, 1)
        information.addLayout(summary)

        stats_title = QLabel("ATRIBUTOS NO NÍVEL 80")
        stats_title.setObjectName("catalogSectionTitle")
        information.addWidget(stats_title)
        information.addWidget(self._stats_card(
            self.repository.character_stats(character.id), include_speed=True
        ))
        information.addStretch(1)
        layout.addLayout(information, 1)
        return hero

    @staticmethod
    def _identity_chip(kind: str, key: str, text: str) -> QFrame:
        chip = QFrame()
        chip.setObjectName("characterIdentityChip")
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(7, 4, 9, 4)
        layout.setSpacing(5)
        icon = QLabel()
        icon.setFixedSize(21, 21)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_path = FRIBBELS_ASSETS / "icon" / kind / f"{key}.webp"
        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            icon.setPixmap(pixmap.scaled(
                QSize(18, 18),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        label = QLabel(text)
        label.setObjectName("characterIdentityChipText")
        layout.addWidget(icon)
        layout.addWidget(label)
        return chip

    @staticmethod
    def _deduplicate_character_skills(
        skills: list[CatalogSkill],
    ) -> list[CatalogSkill]:
        """Preserva o kit completo, removendo apenas entradas idênticas."""
        unique: list[CatalogSkill] = []
        seen: set[tuple[str, str, str]] = set()
        for skill in skills:
            key = (
                skill.type_name.strip().casefold(),
                skill.name.strip().casefold(),
                " ".join(skill.description.split()).casefold(),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(skill)
        return unique

    def _trace_description(self, trace: CatalogTrace) -> str:
        params = trace.parameters[-1] if trace.parameters else []
        details = self.repository.format_description(trace.description, params).strip()
        if trace.properties:
            values = []
            for property_name, value in trace.properties:
                rendered = f"+{value:g}" if property_name == "SpeedDelta" else f"+{value * 100:g}%"
                values.append(rendered)
            details = f"Valor concedido: {' · '.join(values)}"

        requirements: list[str] = []
        if trace.promotion:
            requirements.append(f"Ascensão {trace.promotion}")
        if trace.required_level:
            requirements.append(f"Nível {trace.required_level}")
        unlock = " · ".join(requirements) if requirements else "Disponível inicialmente"
        return f"{details}\nDesbloqueio: {unlock}" if details else f"Desbloqueio: {unlock}"

    @staticmethod
    def _character_detail_tabs(
        pages: list[tuple[str, QWidget]],
    ) -> QFrame:
        container = QFrame()
        container.setObjectName("characterDetailTabs")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)

        navigation = QFrame()
        navigation.setObjectName("characterDetailTabBar")
        navigation_layout = QHBoxLayout(navigation)
        navigation_layout.setContentsMargins(5, 5, 5, 5)
        navigation_layout.setSpacing(5)
        buttons: list[QPushButton] = []

        def activate(selected: int) -> None:
            for index, ((_label, page), button) in enumerate(zip(pages, buttons)):
                active = index == selected
                page.setVisible(active)
                button.setChecked(active)
            container.updateGeometry()

        for index, (label, page) in enumerate(pages):
            button = QPushButton(label)
            button.setObjectName("characterDetailTab")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, selected=index: activate(selected)
            )
            navigation_layout.addWidget(button, 1)
            buttons.append(button)
            layout.addWidget(page)
            page.setVisible(index == 0)
        layout.insertWidget(0, navigation)
        if buttons:
            buttons[0].setChecked(True)
        return container

    @staticmethod
    def _info_section(
        title: str,
        subtitle: str,
        cards: list[InfoCard],
        *,
        collapsible: bool = False,
        expanded: bool = True,
    ) -> QFrame:
        section = QFrame()
        section.setObjectName("characterInfoSection")
        outer = QVBoxLayout(section)
        outer.setContentsMargins(12, 11, 12, 13)
        outer.setSpacing(9)
        header = QHBoxLayout()
        headings = QVBoxLayout()
        headings.setSpacing(1)
        name = QLabel(title)
        name.setObjectName("characterSectionTitle")
        hint = QLabel(subtitle)
        hint.setObjectName("characterSectionHint")
        count = QLabel(str(len(cards)))
        count.setObjectName("characterSectionCount")
        headings.addWidget(name)
        headings.addWidget(hint)
        header.addLayout(headings)
        header.addStretch(1)
        header.addWidget(count, alignment=Qt.AlignmentFlag.AlignTop)
        toggle: QPushButton | None = None
        if collapsible:
            toggle = QPushButton("▾  Recolher" if expanded else "›  Mostrar")
            toggle.setObjectName("characterSectionToggle")
            toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            header.addWidget(toggle, alignment=Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)

        content = QWidget()
        content.setObjectName("characterSectionContent")
        columns = QHBoxLayout(content)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(8)
        left = QVBoxLayout()
        right = QVBoxLayout()
        left.setSpacing(8)
        right.setSpacing(8)
        for index, card in enumerate(cards):
            (left if index % 2 == 0 else right).addWidget(card)
        left.addStretch(1)
        right.addStretch(1)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        outer.addWidget(content)
        content.setVisible(expanded)
        section.setProperty("collapsed", not expanded)

        if toggle is not None:
            def toggle_content() -> None:
                visible = not content.isVisible()
                content.setVisible(visible)
                toggle.setText("▾  Recolher" if visible else "›  Mostrar")
                section.setProperty("collapsed", not visible)
                section.style().unpolish(section)
                section.style().polish(section)

            toggle.clicked.connect(toggle_content)
        return section

    def _build_cone_detail(self, cone: CatalogLightCone) -> None:
        self._selected_cone = cone
        rank = self.repository.light_cone_rank(cone.id)

        analysis = QFrame()
        analysis.setObjectName("coneAnalysisPanel")
        analysis_layout = QHBoxLayout(analysis)
        analysis_layout.setContentsMargins(14, 14, 16, 14)
        analysis_layout.setSpacing(17)

        art_column = QVBoxLayout()
        art_column.setSpacing(7)
        cone_art = QLabel("◇")
        cone_art.setObjectName("coneAnalysisArt")
        cone_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cone_art.setFixedSize(230, 321)
        image_path = self.repository.light_cone_image(cone.id)
        pixmap = QPixmap(str(image_path)) if image_path.is_file() else QPixmap()
        self._set_detail_pixmap(cone_art, pixmap, expand=False)
        if pixmap.isNull():
            self._load_remote(
                cone.portrait or cone.preview,
                lambda loaded, target=cone_art:
                self._set_detail_pixmap(target, loaded, expand=False),
            )
        art_label = QLabel("ARTE DO CONE")
        art_label.setObjectName("coneAnalysisCaption")
        art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art_column.addWidget(cone_art)
        art_column.addWidget(art_label)
        art_column.addStretch(1)

        information = QVBoxLayout()
        information.setSpacing(9)
        eyebrow = QLabel("ANÁLISE DO CONE DE LUZ")
        eyebrow.setObjectName("coneAnalysisEyebrow")
        title = QLabel(cone.name)
        title.setObjectName("catalogDetailName")
        title.setWordWrap(True)
        stars = QLabel("★" * cone.rarity)
        stars.setObjectName("catalogDetailStars")
        meta = QLabel(f"{cone.path_name}  ·  Nível 80")
        meta.setObjectName("catalogDetailMeta")
        information.addWidget(eyebrow)
        information.addWidget(title)
        information.addWidget(stars)
        information.addWidget(meta)
        information.addWidget(self._stats_card(self.repository.light_cone_stats(cone.id)))

        rank_header = QHBoxLayout()
        rank_label = QLabel("NÍVEL DE SOBREPOSIÇÃO")
        rank_label.setObjectName("catalogSectionTitle")
        rank_header.addWidget(rank_label)
        rank_header.addStretch(1)
        information.addLayout(rank_header)

        rank_buttons = QHBoxLayout()
        rank_buttons.setSpacing(6)
        self.cone_rank_group = QButtonGroup(analysis)
        self.cone_rank_group.setExclusive(True)
        self.cone_rank_buttons: list[QPushButton] = []
        for value in range(1, 6):
            button = QPushButton(f"S{value}")
            button.setObjectName("coneRankButton")
            button.setCheckable(True)
            button.setChecked(value == 1)
            button.clicked.connect(
                lambda _checked=False, selected=value: self._update_cone_effect(selected)
            )
            self.cone_rank_group.addButton(button, value)
            self.cone_rank_buttons.append(button)
            rank_buttons.addWidget(button)
        information.addLayout(rank_buttons)

        effect = QFrame()
        effect.setObjectName("coneEffectAnalysisCard")
        effect_layout = QVBoxLayout(effect)
        effect_layout.setContentsMargins(12, 10, 12, 11)
        effect_layout.setSpacing(6)
        effect_title = QLabel(str(rank.get("skill") or "Efeito do Cone de Luz"))
        effect_title.setObjectName("coneEffectTitle")
        self.cone_effect = QLabel()
        self.cone_effect.setObjectName("catalogInfoText")
        self.cone_effect.setWordWrap(True)
        self.cone_effect.setTextFormat(Qt.TextFormat.RichText)
        self.cone_effect.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        effect_layout.addWidget(effect_title)
        effect_layout.addWidget(self.cone_effect)
        information.addWidget(effect)

        progression_title = QLabel("EVOLUÇÃO DOS VALORES")
        progression_title.setObjectName("catalogSectionTitle")
        information.addWidget(progression_title)
        progression = QHBoxLayout()
        progression.setSpacing(6)
        self.cone_progress_cards: list[QFrame] = []
        parameters = rank.get("params", [])
        changing = self._changing_parameters(parameters)
        for level in range(1, 6):
            values = (
                parameters[level - 1]
                if isinstance(parameters, list) and level <= len(parameters)
                and isinstance(parameters[level - 1], list)
                else []
            )
            card = QFrame()
            card.setObjectName("coneProgressCard")
            card.setProperty("selected", level == 1)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(7, 6, 7, 7)
            card_layout.setSpacing(2)
            stage = QLabel(f"S{level}")
            stage.setObjectName("coneProgressStage")
            stage.setAlignment(Qt.AlignmentFlag.AlignCenter)
            numbers = QLabel(self._progression_values(str(rank.get("desc", "")), values, changing))
            numbers.setObjectName("coneProgressValues")
            numbers.setAlignment(Qt.AlignmentFlag.AlignCenter)
            numbers.setWordWrap(True)
            card_layout.addWidget(stage)
            card_layout.addWidget(numbers)
            progression.addWidget(card, 1)
            self.cone_progress_cards.append(card)
        information.addLayout(progression)
        information.addStretch(1)

        analysis_layout.addLayout(art_column)
        analysis_layout.addLayout(information, 1)
        self.detail_layout.addWidget(analysis)

        lore = QLabel(cone.description)
        lore.setObjectName("catalogLore")
        lore.setWordWrap(True)
        lore.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detail_layout.addWidget(lore)
        self._update_cone_effect(1)
        if not rank:
            self.detail_layout.addWidget(self._details_missing())

    @staticmethod
    def _changing_parameters(parameters: object) -> set[int]:
        changing: set[int] = set()
        if not isinstance(parameters, list) or not parameters:
            return changing
        width = max(
            (len(row) for row in parameters if isinstance(row, list)), default=0
        )
        for parameter_index in range(width):
            seen = {
                row[parameter_index]
                for row in parameters
                if isinstance(row, list) and parameter_index < len(row)
            }
            if len(seen) > 1:
                changing.add(parameter_index)
        return changing

    @staticmethod
    def _progression_values(
        description: str, values: list[float], changing: set[int]
    ) -> str:
        import re

        rendered: list[str] = []
        for parameter_index in sorted(changing):
            if parameter_index >= len(values):
                continue
            percent = bool(re.search(
                rf"#{parameter_index + 1}\[i\]%", description
            ))
            value = values[parameter_index] * 100 if percent else values[parameter_index]
            rendered.append(f"{value:g}{'%' if percent else ''}")
        return " · ".join(rendered) if rendered else "—"

    def _update_cone_effect(self, level: int = 1) -> None:
        cone = self._selected_cone
        if cone is None:
            return
        rank = self.repository.light_cone_rank(cone.id)
        params = rank.get("params", [])
        index = max(1, min(level, 5)) - 1
        values = params[index] if isinstance(params, list) and 0 <= index < len(params) else []
        changing = self._changing_parameters(params)
        self.cone_effect.setText(self.repository.format_description_rich(
            str(rank.get("desc", "Descrição indisponível nesta fonte.")),
            values,
            changing,
        ))
        for button_index, button in enumerate(self.cone_rank_buttons, start=1):
            button.setChecked(button_index == level)
        for card_index, card in enumerate(self.cone_progress_cards, start=1):
            card.setProperty("selected", card_index == level)
            card.style().unpolish(card)
            card.style().polish(card)

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("catalogSectionTitle")
        return label

    @staticmethod
    def _details_missing() -> QLabel:
        label = QLabel("Atualize o catálogo para carregar as descrições detalhadas.")
        label.setObjectName("statusInfo")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _stats_card(stats: dict[str, float], *, include_speed: bool = False) -> QFrame:
        card = QFrame()
        card.setObjectName("catalogStatsCard")
        layout = QGridLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        names = [("hp", "PV"), ("atk", "ATQ"), ("def", "DEF")]
        if include_speed:
            names.append(("spd", "VEL"))
        for column, (key, title) in enumerate(names):
            label = QLabel(title)
            label.setObjectName("catalogStatName")
            value = QLabel(f"{stats[key]:.1f}" if key in stats else "—")
            value.setObjectName("catalogStatValue")
            layout.addWidget(label, 0, column)
            layout.addWidget(value, 1, column)
            layout.setColumnStretch(column, 1)
        return card

    def _load_remote(self, relative: str, callback: Callable[[QPixmap], None]) -> None:
        if relative:
            self.image_loader.load(self.repository.asset_url(relative), callback)

    def synchronize(self) -> None:
        if self.sync_worker is not None and self.sync_worker.isRunning():
            return
        self.sync_failed = False
        self.sync_button.setEnabled(False)
        self.background_sync_changed.emit(True, "Atualizando catálogo…")
        self.sync_button.setText("Atualizando…")
        self.sync_worker = CatalogSyncWorker(self)
        self.sync_worker.progress.connect(self._set_status)
        self.sync_worker.succeeded.connect(self._sync_succeeded)
        self.sync_worker.failed.connect(self._sync_failed)
        self.sync_worker.finished.connect(self._sync_finished)
        self.sync_worker.start()

    def _set_status(self, message: str, kind: str = "info") -> None:
        self.status.setObjectName({"success": "statusSuccess", "error": "statusError"}.get(kind, "statusInfo"))
        self.status.setText(message)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _sync_succeeded(self, sha: str) -> None:
        self.repository.reload()
        self._reset_card_cache()
        self._populate_filters()
        self._render()
        self._set_status(f"Catálogo em português atualizado · versão {sha[:8]}", "success")
        self.catalog_updated.emit(sha)

    def _sync_failed(self, message: str) -> None:
        self.sync_failed = True
        self._set_status(f"Não foi possível atualizar: {message}. Usando os dados locais.", "error")

    def _sync_finished(self) -> None:
        self.sync_button.setEnabled(True)
        self.sync_button.setText("↻  Atualizar catálogo")
        if self.sync_worker is not None:
            self.sync_worker.deleteLater()
        self.sync_worker = None
        message = "Falha ao atualizar o catálogo" if self.sync_failed else "Catálogo sincronizado"
        self.background_sync_changed.emit(False, message)

    def _reset_card_cache(self) -> None:
        self._image_timer.stop()
        self._image_queue.clear()
        self._queued_images.clear()
        self._detach_grid_cards()
        for cache in self.card_cache.values():
            for card in cache.values():
                card.deleteLater()
            cache.clear()
        self.cards.clear()

    def resizeEvent(self, event) -> None:  # noqa: N802 - API Qt
        super().resizeEvent(event)
        if self._active and self.stack.currentWidget() is self.list_page:
            self._render_timer.start()
