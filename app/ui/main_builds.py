"""Detalhamento de builds, equipes, relíquias e benchmark."""
from __future__ import annotations

from copy import deepcopy
import json
import unicodedata

from PySide6.QtCore import QRect, QStandardPaths, QTimer, QUrl, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from app.benchmark.fribbels_client import FribbelsBenchmarkWorker, engine_available
from app.benchmark.teams import default_team
from app.models import AccountSummary, CharacterStat, CharacterSummary
from app.performance import PERFORMANCE
from app.privacy import hide_uid_in_shared_images
from app.section_loading import LoadContext
from app.ui.build_history import (
    BuildComparisonDialog, BuildHistoryBar, BuildMetadataDialog, ConfirmBuildDeleteDialog,
)
from app.ui.build_share import render_build_share_card
from app.ui.contextual_help import BENCHMARK_HELP, RELIC_GRADE_HELP, ContextHelpButton
from app.ui.motion import AnimatedStack as QStackedWidget
from app.ui.team_dialog import CustomTeamDialog
from app.ui.widgets import (
    AbilityBreakdownCard, AvatarLabel, BenchmarkCard, BenchmarkScale,
    CombatStatsCard, FRIBBELS_ASSETS, LightConeBanner, RelicCard,
    ResponsiveImageLabel, StatRow, TeamCard, UpgradeComparisonTable,
)

PRIMARY_STATS = (
    "MaxHP", "Attack", "Defence", "Speed", "CriticalChance", "CriticalDamage",
    "StatusProbability", "StatusResistance", "BreakDamageAddedRatio", "SPRatio",
)

ELEMENT_STATS = {
    "Físico": "PhysicalAddedRatio",
    "Fogo": "FireAddedRatio",
    "Gelo": "IceAddedRatio",
    "Raio": "ThunderAddedRatio",
    "Vento": "WindAddedRatio",
    "Quântico": "QuantumAddedRatio",
    "Imaginário": "ImaginaryAddedRatio",
}


class BuildActions:
    """Callbacks e composição da visualização detalhada de builds."""

    def _build_build_empty_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("buildEmptyPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)
        icon = QLabel("◇")
        icon.setObjectName("buildEmptyIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("NENHUMA BUILD CARREGADA")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel(
            "Pesquise uma UID para ver builds públicas ou abra Conta para carregar "
            "as builds da sua UID principal."
        )
        hint.setObjectName("muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addStretch(1)
        return frame

    def _show_build_content(self, loaded: bool) -> None:
        self.page_stack.setCurrentIndex(0)
        self.build_empty_panel.setVisible(not loaded)
        self.build_scroll.setVisible(loaded)
        self.header_refresh_button.setVisible(loaded and self.build_source == "own")
        self._refresh_friend_action(loaded)
        if not loaded:
            return
        self.art_panel.setVisible(True)
        self.relics_panel.setVisible(True)
        self.content_splitter.reflow()

    def _build_selector(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("selectorPanel")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(9, 5, 9, 5)
        layout.setSpacing(4)
        character_row = QHBoxLayout()
        title = QLabel("Personagens")
        title.setObjectName("sectionTitle")
        title.setFixedWidth(100)
        self.character_list_stack = QStackedWidget()
        self.character_list_stack.setObjectName("portraitListStack")
        self.character_list_stack.setFixedHeight(84)
        self.character_list = self._make_character_list()
        self._own_character_list = self.character_list
        self.character_list_stack.addWidget(self.character_list)
        character_row.addWidget(title)
        self.characters_section_status = self._make_section_status("characters")
        self.characters_section_status.setMaximumWidth(230)
        character_row.addWidget(self.characters_section_status)
        character_row.addWidget(self.character_list_stack, 1)
        layout.addLayout(character_row)
        return frame

    def _make_character_list(self) -> QListWidget:
        listing = QListWidget()
        listing.setObjectName("portraitList")
        listing.setFlow(QListWidget.Flow.LeftToRight)
        listing.setWrapping(False)
        listing.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        listing.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        listing.currentRowChanged.connect(
            lambda row, current=listing: self.show_character_details(row)
            if self.character_list is current else None
        )
        listing.currentRowChanged.connect(self._schedule_resume_save)
        listing.horizontalScrollBar().valueChanged.connect(self._schedule_resume_save)
        return listing

    def _use_character_list(self, account: AccountSummary) -> bool:
        session = self.uid_workspace.sessions.get(self.active_uid_tab)
        if session is not None and session.account is account:
            key = (self.uid_workspace.owner_id, session.uid)
            cached = self._uid_character_lists.get(key)
            if cached is None:
                listing = self._make_character_list()
                self.character_list_stack.addWidget(listing)
            else:
                previous_account, listing = cached
                if (
                    previous_account is account
                    and listing.count() == len(account.characters)
                ):
                    self.character_list = listing
                    self.character_list_stack.setCurrentWidget(listing)
                    return True
                listing.clear()
            self._uid_character_lists[key] = (account, listing)
        else:
            listing = self._own_character_list
        self.character_list = listing
        self.character_list_stack.setCurrentWidget(listing)
        return False

    def _drop_uid_character_list(self, uid: str, *, owner_id: int | None = None) -> None:
        key = (self.uid_workspace.owner_id if owner_id is None else owner_id, uid)
        cached = self._uid_character_lists.pop(key, None)
        if cached is None:
            return
        listing = cached[1]
        if self.character_list is listing:
            self.character_list = self._own_character_list
            self.character_list_stack.setCurrentWidget(self.character_list)
        self.character_list_stack.removeWidget(listing)
        listing.deleteLater()

    def _drop_uid_relic_cards(self, uid: str, *, owner_id: int | None = None) -> None:
        owner = self.uid_workspace.owner_id if owner_id is None else owner_id
        for key in list(self._uid_relic_cards):
            if key[0] == owner and key[1] == uid:
                _account, cards = self._uid_relic_cards.pop(key)
                for card in cards:
                    card.deleteLater()

    def _drop_uid_stat_rows(self, uid: str, *, owner_id: int | None = None) -> None:
        owner = self.uid_workspace.owner_id if owner_id is None else owner_id
        for key in list(self._uid_stat_rows):
            if key[0] == owner and key[1] == uid:
                _account, rows = self._uid_stat_rows.pop(key)
                for row in rows:
                    row.deleteLater()

    def _build_art_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("artPanel")
        frame.setMinimumWidth(180)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.character_art = ResponsiveImageLabel()
        layout.addWidget(self.character_art, 1)
        self.art_section_status = self._make_section_status("art")
        layout.addWidget(self.art_section_status)
        self.art_caption = QLabel("Selecione um personagem")
        self.art_caption.setObjectName("artCaption")
        self.art_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_caption.setWordWrap(True)
        layout.addWidget(self.art_caption)
        self.uid_caption = QLabel("UID —")
        self.uid_caption.setObjectName("muted")
        self.uid_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.uid_caption.setContentsMargins(0, 5, 0, 7)
        layout.addWidget(self.uid_caption)
        layout.addWidget(self._build_light_cone())
        return frame

    def _build_stats_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("statsPanel")
        frame.setMinimumWidth(205)
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(5, 5, 5, 5)
        outer.setSpacing(0)
        self.stats_scroll = QScrollArea()
        self.stats_scroll.setObjectName("statsScroll")
        self.stats_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.stats_scroll.setWidgetResizable(True)
        self.stats_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.stats_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        content = QWidget()
        content.setObjectName("scrollContent")
        self.stats_content = content
        self.stats_layout = QVBoxLayout(content)
        self.stats_layout.setContentsMargins(6, 5, 6, 6)
        self.stats_layout.setSpacing(3)

        self.detail_name = QLabel("Personagem")
        self.detail_name.setObjectName("detailName")
        self.detail_name.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.detail_name.setTextFormat(Qt.TextFormat.PlainText)
        self.detail_name.setWordWrap(True)
        self.detail_name.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        identity = QHBoxLayout()
        identity.setContentsMargins(3, 0, 3, 0)
        identity.setSpacing(7)
        self.element_icon = QLabel()
        self.element_icon.setObjectName("characterIdentityIcon")
        self.element_icon.setFixedSize(30, 30)
        self.element_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_icon = QLabel()
        self.path_icon.setObjectName("characterIdentityIcon")
        self.path_icon.setFixedSize(30, 30)
        self.path_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_rarity = QLabel("☆☆☆☆☆")
        self.detail_rarity.setObjectName("rarity")
        self.detail_rarity.setAlignment(Qt.AlignmentFlag.AlignCenter)
        identity.addWidget(self.element_icon)
        identity.addStretch(1)
        identity.addWidget(self.detail_rarity)
        identity.addStretch(1)
        identity.addWidget(self.path_icon)
        badges = QHBoxLayout()
        self.level_badge = QLabel("NV. —")
        self.level_badge.setObjectName("badge")
        self.eidolon_badge = QLabel("E—")
        self.eidolon_badge.setObjectName("eidolonBadge")
        badges.addStretch(1)
        badges.addWidget(self.level_badge)
        badges.addWidget(self.eidolon_badge)
        badges.addStretch(1)
        self.stats_layout.addLayout(identity)
        self.stats_layout.addWidget(self.detail_name)
        self.stats_layout.addLayout(badges)

        section = QLabel("Atributos")
        section.setObjectName("sectionTitle")
        self.stats_layout.addWidget(section)
        self.stat_rows = QGridLayout()
        self.stat_rows.setSpacing(0)
        self.stat_rows.setHorizontalSpacing(10)
        self.stats_layout.addLayout(self.stat_rows)

        self.benchmark_card = BenchmarkCard()
        self.benchmark_section_status = self._make_section_status("benchmark")
        self.stats_layout.addWidget(self.benchmark_section_status)
        self.stats_layout.addWidget(self.benchmark_card)
        self.team_card = TeamCard()
        self.team_card.custom_requested.connect(self.use_custom_team)
        self.team_card.edit_requested.connect(self.open_custom_team_dialog)
        self.team_card.default_requested.connect(self.use_default_team)
        self.stats_layout.addWidget(self.team_card)
        self.combat_stats_card = CombatStatsCard()
        self.stats_layout.addWidget(self.combat_stats_card)
        self.stats_layout.addStretch(1)
        self.stats_scroll.setWidget(content)
        outer.addWidget(self.stats_scroll, 1)
        return frame

    def _build_light_cone(self) -> QFrame:
        holder = QFrame()
        holder.setObjectName("lightConeBannerHolder")
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(9, 0, 9, 8)
        self.light_cone_banner = LightConeBanner()
        layout.addWidget(self.light_cone_banner)
        return holder

    def _build_benchmark_section(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("benchmarkAnalysisPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 18)
        layout.setSpacing(12)

        title = QLabel("DPS BENCHMARK")
        title.setObjectName("benchmarkPageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row = QHBoxLayout()
        title_row.addStretch(1)
        title_row.addWidget(title)
        title_row.addWidget(ContextHelpButton(*BENCHMARK_HELP))
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self.benchmark_scale = BenchmarkScale()
        layout.addWidget(self.benchmark_scale)
        self.upgrade_comparison_table = UpgradeComparisonTable()
        layout.addWidget(self.upgrade_comparison_table)
        self.main_upgrade_comparison_table = UpgradeComparisonTable(
            "COMPARAÇÃO DE MELHORIA DE ATRIBUTO PRINCIPAL",
            "Melhoria do atributo principal",
            show_part_icon=True,
        )
        layout.addWidget(self.main_upgrade_comparison_table)
        self.ability_breakdown_card = AbilityBreakdownCard()
        layout.addWidget(
            self.ability_breakdown_card,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        return frame

    def _build_relics_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("relicsPanel")
        frame.setMinimumWidth(225)
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("Relíquias e ornamentos")
        title.setWordWrap(False)
        title.setObjectName("sectionTitle")
        self.relic_count = QLabel("0/6")
        self.relic_count.setObjectName("badge")
        header.addWidget(title)
        header.addWidget(ContextHelpButton(*RELIC_GRADE_HELP))
        header.addStretch(1)
        header.addWidget(self.relic_count)
        outer.addLayout(header)
        self.relics_section_status = self._make_section_status("relics")
        outer.addWidget(self.relics_section_status)
        legend = QLabel("Cada < representa uma melhoria recebida pelo subatributo")
        legend.setObjectName("sectionHint")
        legend.setWordWrap(True)
        outer.addWidget(legend)

        self.relic_scroll = QScrollArea()
        self.relic_scroll.setWidgetResizable(True)
        self.relic_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("scrollContent")
        self.relic_grid = QGridLayout(content)
        self.relic_grid.setContentsMargins(0, 4, 0, 0)
        self.relic_grid.setHorizontalSpacing(7)
        self.relic_grid.setVerticalSpacing(7)
        self.relic_empty = QLabel("As relíquias do personagem aparecerão aqui.")
        self.relic_empty.setObjectName("muted")
        self.relic_empty.setWordWrap(True)
        self.relic_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.relic_grid.addWidget(self.relic_empty, 0, 0, 1, 2)
        self.relic_scroll.setWidget(content)
        outer.addWidget(self.relic_scroll, 1)
        return frame

    def _build_build_history_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("buildHistoryPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        self.build_history_bar = BuildHistoryBar(wide=False)
        self.build_history_bar.save_requested.connect(self.save_current_build)
        self.build_history_bar.export_requested.connect(self.export_current_build)
        self.build_history_bar.compare_requested.connect(self.compare_saved_build)
        self.build_history_bar.delete_requested.connect(self.delete_saved_build)
        self.build_history_bar.edit_requested.connect(self.edit_saved_build)
        self.build_history_bar.favorite_requested.connect(self.set_saved_build_favorite)
        self.build_history_bar.retention_changed.connect(self.set_build_retention)
        layout.addWidget(self.build_history_bar)
        return frame

    def show_character_details(self, row: int) -> None:
        if row < 0 or row >= len(self.current_characters):
            return
        self._detail_request += 1
        request = self._detail_request
        self.sync_manager.begin(
            "character", f"Preparando a build de {self.current_characters[row].name}…"
        )
        QTimer.singleShot(
            0, lambda: self._finish_character_details(row, request)
        )

    def _finish_character_details(self, row: int, request: int) -> None:
        if request != self._detail_request:
            return
        try:
            self._show_character_details(row)
        finally:
            self.sync_manager.finish("character", "Build preparada")

    def _refresh_detail_name_layout(self) -> None:
        if not hasattr(self, "detail_name"):
            return
        available = max(self.stats_panel.width() - 30, 120)
        reference_font = QFont(self.detail_name.font())
        reference_font.setPixelSize(24)
        text_width = QFontMetrics(reference_font).horizontalAdvance(
            self.detail_name.text()
        )
        wrapped = text_width > available
        compact = text_width > available * 1.55
        if self.detail_name.property("compactName") != compact:
            self.detail_name.setProperty("compactName", compact)
            self.detail_name.style().unpolish(self.detail_name)
            self.detail_name.style().polish(self.detail_name)
        # heightForWidth is bounded by the previous fixed height: adding padding
        # to it repeatedly made the header grow on every resize/character switch.
        metrics = self.detail_name.fontMetrics()
        text_height = metrics.boundingRect(
            QRect(0, 0, available, 10000),
            Qt.TextFlag.TextWordWrap, self.detail_name.text(),
        ).height()
        self.detail_name.setFixedHeight(max(metrics.lineSpacing(), text_height) + 4)
        self.detail_name.setToolTip(self.detail_name.text() if wrapped else "")
        self._reflow_stat_rows()

    def _reflow_stat_rows(self) -> None:
        if not hasattr(self, "stat_rows"):
            return
        rows = []
        while self.stat_rows.count():
            rows.append(self.stat_rows.takeAt(0).widget())
        columns = 1
        for index, row in enumerate(rows):
            self.stat_rows.addWidget(row, index // columns, index % columns)
        self.stat_rows.setColumnStretch(0, 1)
        self.stat_rows.setColumnStretch(1, 1 if columns == 2 else 0)

    def _show_character_details(self, row: int) -> None:
        if row < 0 or row >= len(self.current_characters):
            return
        character = self.current_characters[row]
        self.current_character_id = character.avatar_id
        self._schedule_resume_save()
        session = self.uid_workspace.sessions.get(self.active_uid_tab)
        if (
            session is not None
            and self.build_source in {"manual", "friend"}
            and self.current_account is not None
            and self.current_account.uid == session.uid
        ):
            session.selected_character_id = str(character.avatar_id)
            self.uid_workspace.persist()
        self.detail_name.setText(character.name)
        # Um personagem anterior pode ter deixado a coluna rolada para baixo.
        # Mostre sempre a identidade e os atributos ao trocar a seleção.
        QTimer.singleShot(
            0, lambda: self.stats_scroll.verticalScrollBar().setValue(0)
        )
        QTimer.singleShot(0, self._refresh_detail_name_layout)
        self.detail_rarity.setText("★" * character.rarity)
        self.level_badge.setText(f"NV. {character.level}")
        self.eidolon_badge.setText(f"E{character.eidolon}")
        self._display_identity_icons(character)
        self.art_caption.setText(character.name)
        self.light_cone_banner.set_info(
            character.light_cone,
            character.light_cone_level,
            character.light_cone_rank,
        )
        self.relic_count.setText(f"{character.relic_count}/6")

        context = self.section_loading.context
        self._load_character_art(character, context)
        self._display_light_cone_art(character, context)
        self._display_stats(character)
        self._display_relics(character, context=context)
        self._display_benchmark(character)

    def _load_character_art(
        self, character: CharacterSummary, context: LoadContext
    ) -> None:
        self.character_art.clear_image()
        self.section_loading.pending("art", "Carregando ilustração…", context)
        avatar_id = str(character.avatar_id)
        self.image_loader.load(
            character.splash_url,
            lambda pixmap, current=context, target=avatar_id:
            self._character_art_loaded(current, target, pixmap),
        )

    def _character_art_loaded(
        self, context: LoadContext, avatar_id: str, pixmap: QPixmap
    ) -> None:
        if (
            not self.section_loading.is_current(context)
            or avatar_id != str(self.current_character_id)
        ):
            return
        if pixmap.isNull():
            self.section_loading.fail(
                "art", "Não foi possível carregar a ilustração.",
                details=f"UID {context.uid} · personagem {avatar_id}",
                context=context,
            )
            return
        self.character_art.set_image(pixmap)
        self.section_loading.ready("art", context)

    @staticmethod
    def _identity_asset_key(value: str, kind: str) -> str:
        normalized = "".join(
            character for character in unicodedata.normalize("NFKD", value)
            if not unicodedata.combining(character)
        ).casefold()
        mappings = {
            "element": {
                "fisico": "Physical", "physical": "Physical",
                "fogo": "Fire", "fire": "Fire",
                "gelo": "Ice", "ice": "Ice",
                "raio": "Lightning", "lightning": "Lightning", "thunder": "Lightning",
                "vento": "Wind", "wind": "Wind",
                "quantico": "Quantum", "quantum": "Quantum",
                "imaginario": "Imaginary", "imaginary": "Imaginary",
            },
            "path": {
                "destruicao": "Destruction", "destruction": "Destruction", "warrior": "Destruction",
                "caca": "Hunt", "hunt": "Hunt", "rogue": "Hunt",
                "erudicao": "Erudition", "erudition": "Erudition", "mage": "Erudition",
                "harmonia": "Harmony", "harmony": "Harmony", "shaman": "Harmony",
                "inexistencia": "Nihility", "nihility": "Nihility", "warlock": "Nihility",
                "preservacao": "Preservation", "preservation": "Preservation", "knight": "Preservation",
                "abundancia": "Abundance", "abundance": "Abundance", "priest": "Abundance",
                "recordacao": "Remembrance", "remembrance": "Remembrance", "memory": "Remembrance",
                "euforia": "Elation", "elation": "Elation", "joy": "Elation",
            },
        }
        return mappings.get(kind, {}).get(normalized, "None")

    def _display_identity_icons(self, character: CharacterSummary) -> None:
        for label, kind, value in (
            (self.element_icon, "element", character.element),
            (self.path_icon, "path", character.path),
        ):
            key = self._identity_asset_key(value, kind)
            icon_path = FRIBBELS_ASSETS / "icon" / kind / f"{key}.webp"
            pixmap = QPixmap(str(icon_path))
            label.setPixmap(pixmap.scaled(
                26, 26,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            label.setToolTip(
                f"{'Elemento' if kind == 'element' else 'Caminho'}: {value}"
            )

    def _display_light_cone_art(
        self, character: CharacterSummary, context: LoadContext
    ) -> None:
        self.light_cone_banner.clear_image()
        payload = character.raw.get("fribbels_payload", {})
        equipment = payload.get("equipment", {}) if isinstance(payload, dict) else {}
        cone_id = str(equipment.get("tid", "")) if isinstance(equipment, dict) else ""
        if not cone_id and character.light_cone_icon_url:
            cone_id = QUrl(character.light_cone_icon_url).fileName().split(".", 1)[0]
        portrait = (
            FRIBBELS_ASSETS / "image" / "light_cone_portrait" / f"{cone_id}.webp"
        )
        if cone_id and portrait.is_file():
            self.light_cone_banner.set_image(QPixmap(str(portrait)))
            return
        self.image_loader.load(
            character.light_cone_icon_url,
            lambda pixmap, current=context, avatar_id=str(character.avatar_id):
            self._set_light_cone_if_current(current, avatar_id, pixmap),
        )

    def _set_light_cone_if_current(
        self, context: LoadContext, avatar_id: str, pixmap: QPixmap
    ) -> None:
        if (
            self.section_loading.is_current(context)
            and avatar_id == str(self.current_character_id)
        ):
            self.light_cone_banner.set_image(pixmap)

    def _display_stats(self, character: CharacterSummary) -> None:
        if not hasattr(self, "uid_workspace"):
            self._clear_layout(self.stat_rows)
            by_key = {stat.key: stat for stat in character.stats}
            ordered = [by_key[key] for key in PRIMARY_STATS if key in by_key]
            element_key = ELEMENT_STATS.get(character.element)
            if element_key and element_key in by_key:
                ordered.append(by_key[element_key])
            for index, stat in enumerate(ordered):
                self.stat_rows.addWidget(StatRow(stat), index, 0)
            self._reflow_stat_rows()
            return
        old_rows: list[StatRow] = []
        while self.stat_rows.count():
            item = self.stat_rows.takeAt(0)
            widget = item.widget()
            if isinstance(widget, StatRow):
                widget.hide()
                old_rows.append(widget)
            elif widget is not None:
                widget.deleteLater()
        old_key = self._visible_stat_key
        old_account = self._visible_stat_account
        old_session = (
            self.uid_workspace.sessions.get(old_key[1]) if old_key else None
        )
        if (
            old_rows and old_key is not None and old_account is not None
            and old_key[0] == self.uid_workspace.owner_id
            and old_session is not None and old_session.account is old_account
        ):
            previous = self._uid_stat_rows.pop(old_key, None)
            if previous is not None:
                for row in previous[1]:
                    row.deleteLater()
            self._uid_stat_rows[old_key] = (old_account, old_rows)
            while len(self._uid_stat_rows) > 8:
                oldest = next(iter(self._uid_stat_rows))
                _account, rows = self._uid_stat_rows.pop(oldest)
                for row in rows:
                    row.deleteLater()
        else:
            for row in old_rows:
                row.deleteLater()
        session = self.uid_workspace.sessions.get(self.active_uid_tab)
        public = session is not None and session.account is self.current_account
        key = (
            (self.uid_workspace.owner_id, session.uid, str(character.avatar_id))
            if public else None
        )
        self._visible_stat_key = key
        self._visible_stat_account = self.current_account if public else None
        cached = self._uid_stat_rows.pop(key, None) if key is not None else None
        if cached is not None and cached[0] is self.current_account:
            rows = cached[1]
        else:
            if cached is not None:
                for row in cached[1]:
                    row.deleteLater()
            rows = []
            by_key = {stat.key: stat for stat in character.stats}
            ordered: list[CharacterStat] = [
                by_key[key] for key in PRIMARY_STATS if key in by_key
            ]
            element_key = ELEMENT_STATS.get(character.element)
            if element_key and element_key in by_key:
                ordered.append(by_key[element_key])
            rows = [StatRow(stat) for stat in ordered]
        for index, row in enumerate(rows):
            self.stat_rows.addWidget(row, index, 0)
            row.show()
        self._reflow_stat_rows()

    def _display_relics(
        self, character: CharacterSummary, *, context: LoadContext | None = None
    ) -> None:
        context = context or self.section_loading.context
        old_cards = list(self.current_relic_cards)
        while self.relic_grid.count():
            item = self.relic_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                if widget not in old_cards:
                    widget.deleteLater()
        old_key = self._visible_relic_key
        old_account = self._visible_relic_account
        old_session = (
            self.uid_workspace.sessions.get(old_key[1]) if old_key else None
        )
        if (
            old_cards and old_key is not None and old_account is not None
            and old_key[0] == self.uid_workspace.owner_id
            and old_session is not None and old_session.account is old_account
        ):
            previous = self._uid_relic_cards.pop(old_key, None)
            if previous is not None:
                for card in previous[1]:
                    card.deleteLater()
            self._uid_relic_cards[old_key] = (old_account, old_cards)
            while len(self._uid_relic_cards) > 8:
                oldest = next(iter(self._uid_relic_cards))
                _account, cards = self._uid_relic_cards.pop(oldest)
                for card in cards:
                    card.deleteLater()
        else:
            for card in old_cards:
                card.deleteLater()
        self.current_relic_cards = []
        session = self.uid_workspace.sessions.get(self.active_uid_tab)
        public = session is not None and session.account is self.current_account
        key = (
            (self.uid_workspace.owner_id, session.uid, str(character.avatar_id))
            if public else None
        )
        self._visible_relic_key = key
        self._visible_relic_account = self.current_account if public else None
        if not character.relics:
            self.section_loading.ready("relics", context)
            self.relic_empty = QLabel("Nenhuma relíquia pública encontrada.")
            self.relic_empty.setObjectName("muted")
            self.relic_empty.setWordWrap(True)
            self.relic_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.relic_grid.addWidget(self.relic_empty, 0, 0, 1, 2)
            return
        cached = self._uid_relic_cards.pop(key, None) if key is not None else None
        restored_cards = cached is not None and cached[0] is self.current_account
        if restored_cards:
            self.current_relic_cards = cached[1]
        else:
            if cached is not None:
                for card in cached[1]:
                    card.deleteLater()
            for relic in character.relics:
                rating = self.benchmark_engine.rate_relic(character, relic)
                self.current_relic_cards.append(
                    RelicCard(relic, rating, expand_vertical=True)
                )
        pending_images = [
            (relic, card)
            for relic, card in zip(character.relics, self.current_relic_cards)
            if not restored_cards or card.icon.pixmap().isNull()
        ]
        if pending_images:
            self.section_loading.pending(
                "relics", "Carregando imagens das relíquias…", context
            )
        else:
            self.section_loading.ready("relics", context)
        batch = {
            "remaining": len(pending_images), "failed": 0,
            "avatar_id": str(character.avatar_id),
        }
        for relic, card in pending_images:
            self.image_loader.load(
                relic.icon_url,
                lambda pixmap, target=card.icon, current=context, state=batch:
                self._relic_image_loaded(current, state, target, pixmap),
            )
        self._reflow_relic_cards()

    def _relic_image_loaded(
        self, context: LoadContext, batch: dict[str, object],
        target: AvatarLabel, pixmap: QPixmap,
    ) -> None:
        if (
            not self.section_loading.is_current(context)
            or batch["avatar_id"] != str(self.current_character_id)
        ):
            return
        if pixmap.isNull():
            batch["failed"] = int(batch["failed"]) + 1
        else:
            target.set_image(pixmap)
        batch["remaining"] = int(batch["remaining"]) - 1
        if int(batch["remaining"]) > 0:
            return
        if int(batch["failed"]):
            self.section_loading.fail(
                "relics", "Algumas imagens não foram carregadas.",
                details=f"{batch['failed']} imagem(ns) indisponível(is).",
                context=context,
            )
        else:
            self.section_loading.ready("relics", context)

    def _reflow_relic_cards(self) -> None:
        if not self.current_relic_cards:
            return
        while self.relic_grid.count():
            self.relic_grid.takeAt(0)
        for row in range(6):
            self.relic_grid.setRowStretch(row, 0)
        available_width = self.relic_scroll.viewport().width()
        card_width = max(178, *(card.minimumSizeHint().width() for card in self.current_relic_cards))
        columns = 2 if available_width >= card_width * 2 + self.relic_grid.horizontalSpacing() else 1
        self.relic_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        for index, card in enumerate(self.current_relic_cards):
            self.relic_grid.addWidget(card, index // columns, index % columns)
            card.show()
        self.relic_grid.setAlignment(Qt.AlignmentFlag(0))
        for row in range((len(self.current_relic_cards) + columns - 1) // columns):
            self.relic_grid.setRowStretch(row, 1)
        self.relic_grid.setColumnStretch(0, 1)
        self.relic_grid.setColumnStretch(1, 1 if columns == 2 else 0)

    def _team_settings_key(self, character_id: str, suffix: str) -> str:
        uid = self.current_account.uid if self.current_account is not None else "global"
        return f"{uid}/{character_id}/{suffix}"

    def _custom_team(self, character_id: str) -> list[dict[str, object]] | None:
        raw = self.team_settings.value(self._team_settings_key(character_id, "members"), "")
        if not raw:
            return None
        try:
            team = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return team if isinstance(team, list) and len(team) == 3 and all(isinstance(member, dict) for member in team) else None

    def _uses_custom_team(self, character_id: str) -> bool:
        enabled = self.team_settings.value(
            self._team_settings_key(character_id, "custom"), False, type=bool
        )
        return bool(enabled and self._custom_team(character_id))

    def _default_team_for_editor(self, character: CharacterSummary) -> list[dict[str, object]]:
        uid = self.current_account.uid if self.current_account is not None else "global"
        cached = getattr(self, "fribbels_cache", {}).get(f"{uid}:{character.avatar_id}:default", {})
        teammates = cached.get("teammates") if isinstance(cached, dict) else None
        if isinstance(teammates, list) and len(teammates) == 3 and all(isinstance(member, dict) for member in teammates):
            return deepcopy(teammates)
        preset = default_team(character)
        if preset is None:
            return []
        return [
            {
                "characterId": member.character_id,
                "characterEidolon": member.eidolon,
                "lightCone": member.light_cone_id,
                "lightConeSuperimposition": member.superimposition,
                "teamRelicSet": None,
                "teamOrnamentSet": None,
            }
            for member in preset.members
        ]

    def open_custom_team_dialog(self, member_index: int | None = None) -> None:
        character = next(
            (
                item for item in self.current_characters
                if str(item.avatar_id) == self.current_character_id
            ),
            None,
        )
        if character is None:
            return
        character_id = str(character.avatar_id)
        initial = self._custom_team(character_id)
        if not self._uses_custom_team(character_id):
            initial = self._default_team_for_editor(character)
            if initial:
                self.team_settings.setValue(
                    self._team_settings_key(character_id, "members"),
                    json.dumps(initial, ensure_ascii=False),
                )
                self.team_settings.setValue(self._team_settings_key(character_id, "custom"), True)
                self.team_card.set_mode(True)
                self._display_benchmark(character)
        dialog = CustomTeamDialog(
            initial or self._default_team_for_editor(character),
            self,
            str(character.avatar_id),
            member_index=member_index if initial else None,
        )
        if not dialog.exec():
            self.team_card.set_mode(self._uses_custom_team(str(character.avatar_id)))
            return
        team = dialog.team()
        member_ids = [str(member.get("characterId", "")) for member in team]
        if len(set(member_ids)) != 3 or str(character.avatar_id) in member_ids:
            self.set_status(
                "O time customizado precisa ter três companheiros diferentes do DPS.",
                "error",
            )
            self.team_card.set_mode(self._uses_custom_team(str(character.avatar_id)))
            return
        character_id = str(character.avatar_id)
        self.team_settings.setValue(
            self._team_settings_key(character_id, "members"),
            json.dumps(team, ensure_ascii=False, separators=(",", ":")),
        )
        self.team_settings.setValue(self._team_settings_key(character_id, "custom"), True)
        self.team_card.set_mode(True)
        self.set_status("Time customizado salvo. Recalculando o DPS Benchmark…")
        self._display_benchmark(character)

    def use_default_team(self) -> None:
        character = next(
            (
                item for item in self.current_characters
                if str(item.avatar_id) == self.current_character_id
            ),
            None,
        )
        if character is None:
            return
        character_id = str(character.avatar_id)
        self.team_settings.setValue(self._team_settings_key(character_id, "custom"), False)
        self.team_card.set_mode(False)
        self.set_status("Time padrão selecionado. Recalculando o DPS Benchmark…")
        self._display_benchmark(character)

    def use_custom_team(self) -> None:
        character = next(
            (
                item for item in self.current_characters
                if str(item.avatar_id) == self.current_character_id
            ),
            None,
        )
        if character is None:
            return
        character_id = str(character.avatar_id)
        if not self._custom_team(character_id):
            initial = self._default_team_for_editor(character)
            if not initial:
                self.open_custom_team_dialog()
                return
            self.team_settings.setValue(
                self._team_settings_key(character_id, "members"),
                json.dumps(initial, ensure_ascii=False),
            )
        self.team_settings.setValue(self._team_settings_key(character_id, "custom"), True)
        self.team_card.set_mode(True)
        self.set_status("Time customizado selecionado. Recalculando o DPS Benchmark…")
        self._display_benchmark(character)

    def _benchmark_cache_key(self, character: CharacterSummary) -> str:
        character_id = str(character.avatar_id)
        team = self._custom_team(character_id) if self._uses_custom_team(character_id) else None
        team_key = json.dumps(team, sort_keys=True, separators=(",", ":")) if team else "default"
        uid = self.current_account.uid if self.current_account is not None else "global"
        return f"{uid}:{character_id}:{team_key}"

    def _display_benchmark(self, character: CharacterSummary) -> None:
        context = self.section_loading.context
        character_id = str(character.avatar_id)
        reused = self.benchmark_results.get(character_id) if self._reuse_session_benchmark else None
        self._reuse_session_benchmark = False
        if reused is not None:
            self._render_benchmark(reused)
            self.section_loading.ready("benchmark", context)
            return
        cache_key = self._benchmark_cache_key(character)
        with PERFORMANCE.time("Benchmark local"):
            result = self.benchmark_engine.analyze(character)
        teammates = (
            self._custom_team(character_id)
            if self._uses_custom_team(character_id) else None
        )
        if teammates:
            self.benchmark_engine.apply_team_details(result, teammates, custom=True)
        if character_id in self.unsupported_benchmark_characters:
            self._mark_benchmark_unsupported(result)
        cached = self.fribbels_cache.get(cache_key)
        if cached is not None:
            self.benchmark_engine.apply_fribbels_result(character, result, cached)
        self.benchmark_results[character_id] = result
        self._render_benchmark(result)
        if cached is not None or character_id in self.unsupported_benchmark_characters:
            self.section_loading.ready("benchmark", context)
            return
        if not engine_available() or not isinstance(
            character.raw.get("fribbels_payload"), dict
        ):
            self.section_loading.ready("benchmark", context)
            return
        self.section_loading.pending(
            "benchmark", "Aprimorando cálculo com o motor Fribbels…", context
        )
        if cache_key in self.active_benchmark_ids:
            self.benchmark_card.set_loading()
            return
        if self.benchmark_workers:
            # O otimizador é intensivo em CPU. A seleção atual será
            # calculada assim que o processo anterior terminar.
            self.benchmark_card.set_loading()
            return
        self.benchmark_card.set_loading()
        worker = FribbelsBenchmarkWorker(character, teammates, cache_key)
        tab_uid = (
            self.active_uid_tab
            if self.build_source in {"manual", "friend"}
            and self.current_account is not None
            and self.active_uid_tab == self.current_account.uid
            else ""
        )
        self.benchmark_tab_contexts[cache_key] = (self.uid_workspace.owner_id, tab_uid)
        self.benchmark_section_contexts[cache_key] = context
        self.sync_manager.begin(
            f"benchmark:{cache_key}",
            f"Calculando benchmark de {character.name}…",
            retryable=True,
        )
        self.benchmark_workers.add(worker)
        self.active_benchmark_ids.add(cache_key)
        worker.succeeded.connect(self._fribbels_benchmark_ready)
        worker.failed.connect(self._fribbels_benchmark_failed)
        worker.finished.connect(lambda current=worker: self._benchmark_worker_finished(current))
        worker.start()

    def _render_benchmark(self, result) -> None:  # type: ignore[no-untyped-def]
        self.team_card.set_result(result)
        self.team_card.set_mode(self._uses_custom_team(self.current_character_id))
        self.benchmark_card.set_result(result)
        self.combat_stats_card.set_result(result)
        self.benchmark_scale.set_result(result)
        self.upgrade_comparison_table.set_comparisons(result.upgrades)
        self.main_upgrade_comparison_table.set_comparisons(result.main_upgrades)
        self.ability_breakdown_card.set_result(result)
        self._refresh_build_history()

    def _current_character(self) -> CharacterSummary | None:
        return next(
            (
                item for item in self.current_characters
                if str(item.avatar_id) == self.current_character_id
            ),
            None,
        )

    def _build_snapshot_payload(self) -> dict[str, object] | None:
        character = self._current_character()
        result = self.benchmark_results.get(self.current_character_id)
        if character is None or result is None:
            return None
        stats_by_key = {stat.key: stat for stat in character.stats}
        snapshot_stats = [
            stats_by_key[key] for key in PRIMARY_STATS if key in stats_by_key
        ]
        element_key = ELEMENT_STATS.get(character.element)
        if element_key and element_key in stats_by_key:
            snapshot_stats.append(stats_by_key[element_key])
        return {
            "character": {
                "name": character.name,
                "level": character.level,
                "eidolon": character.eidolon,
            },
            "light_cone": {
                "name": character.light_cone,
                "level": character.light_cone_level,
                "rank": character.light_cone_rank,
            },
            "stats": [
                {
                    "key": stat.key,
                    "name": stat.name,
                    "value": stat.value,
                    "formatted": stat.formatted_value,
                    "percentage": stat.is_percentage,
                }
                for stat in snapshot_stats
            ],
            "relics": [
                {
                    "fingerprint": self.relic_database.fingerprint(relic),
                    "slot": relic.slot,
                    "set": relic.set_name,
                    "level": relic.level,
                    "main_stat": relic.main_stat.formatted_value,
                }
                for relic in character.relics
            ],
            "benchmark": {
                "score": result.score,
                "grade": result.grade,
                "damage_index": result.damage_index,
                "source": result.engine_source,
                "exact": result.exact_simulation,
            },
            "team": {
                "name": result.team_name,
                "custom": self._uses_custom_team(self.current_character_id),
                "members": list(result.team_members),
                "details": list(result.team_details),
            },
        }

    def _history_context(self) -> tuple[int, str, str]:
        user = self.auth_service.current_user
        uid = self.current_account.uid if self.current_account is not None else self.current_uid
        return (user.id if user is not None else 0, uid, self.current_character_id)

    def _refresh_build_history(self) -> None:
        if not hasattr(self, "build_history_bar"):
            return
        owner_id, uid, character_id = self._history_context()
        snapshots = self.build_history_database.snapshots(owner_id, uid, character_id)
        self.build_history_bar.set_snapshots(
            snapshots, logged_in=self.auth_service.current_user is not None,
            retention_limit=self.build_history_database.retention_limit(owner_id),
        )
        self.build_history_bar.export_button.setEnabled(
            bool(character_id and character_id in self.benchmark_results)
        )

    def save_current_build(self) -> None:
        character = self._current_character()
        payload = self._build_snapshot_payload()
        if character is None or payload is None:
            self.set_status("A build ainda não terminou de carregar.", "error")
            return
        cache_key = self._benchmark_cache_key(character)
        if cache_key in self.active_benchmark_ids:
            self.set_status(
                "Aguarde o DPS Benchmark terminar antes de salvar a build.", "error"
            )
            return
        owner_id, uid, character_id = self._history_context()
        dialog = BuildMetadataDialog(parent=self)
        if not dialog.exec():
            return
        previous_ids = {
            item.id for item in self.build_history_database.snapshots(
                owner_id, uid, character_id
            )
        }
        try:
            saved = self.build_history_database.save(
                owner_id, uid, character_id, character.name, payload,
                **dialog.metadata(),
            )
        except (ValueError, RuntimeError) as error:
            self.set_status(str(error), "error")
            return
        current_ids = {
            item.id for item in self.build_history_database.snapshots(
                owner_id, uid, character_id
            )
        }
        removed_count = len(previous_ids - current_ids)
        removal_notice = (
            " Uma versão antiga sem favorito foi removida."
            if removed_count == 1 else
            f" {removed_count} versões antigas sem favorito foram removidas."
            if removed_count else ""
        )
        self._refresh_build_history()
        selected_index = self.build_history_bar.selector.findData(saved.id)
        if selected_index >= 0:
            self.build_history_bar.selector.setCurrentIndex(selected_index)
        self.set_status(
            f"Build de {character.name} salva com o DPS Benchmark atual."
            + removal_notice,
            "success",
        )
        self.activity_log.add(
            "build",
            "Build salva",
            f"Build de {character.name} salva com o DPS Benchmark atual.",
            owner_id=owner_id,
            kind="success",
        )

    def export_current_build(self) -> None:
        character = self._current_character()
        payload = self._build_snapshot_payload()
        result = self.benchmark_results.get(self.current_character_id)
        if character is None or payload is None or result is None:
            self.set_status("A build atual ainda não terminou de carregar.", "error")
            return
        if self._benchmark_cache_key(character) in self.active_benchmark_ids:
            self.set_status(
                "Aguarde o DPS Benchmark terminar antes de exportar a imagem.", "error"
            )
            return

        relic_visuals = []
        for index, relic in enumerate(character.relics):
            icon = QPixmap()
            if index < len(self.current_relic_cards):
                current_icon = self.current_relic_cards[index].icon.pixmap()
                if current_icon is not None:
                    icon = current_icon
            relic_visuals.append(
                (relic, self.benchmark_engine.rate_relic(character, relic), icon)
            )
        user = self.auth_service.current_user
        privacy_enabled = bool(user and hide_uid_in_shared_images(user.id))
        card = render_build_share_card(
            character,
            result,
            self.current_uid,
            self.character_art.source,
            self.light_cone_banner.source,
            list(payload.get("stats", [])),
            relic_visuals,
            custom_team=self._uses_custom_team(self.current_character_id),
            hide_uid=privacy_enabled,
        )
        safe_name = "".join(
            value if value.isalnum() else "_" for value in character.name
        ).strip("_") or character.avatar_id
        pictures = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.PicturesLocation
        )
        suffix = "privada" if privacy_enabled else self.current_uid
        suggested = f"{pictures}/AstralOptimizer_{safe_name}_{suffix}.png"
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar build como imagem",
            suggested,
            "Imagem PNG (*.png)",
        )
        if not path:
            return
        if not path.casefold().endswith(".png"):
            path += ".png"
        if not card.save(path, "PNG"):
            self.set_status("Não foi possível salvar a imagem da build.", "error")
            return
        self.set_status("Cartão da build exportado e pronto para compartilhar.", "success")
        self.activity_log.add(
            "build",
            "Build exportada",
            f"Cartão de {character.name} salvo como imagem PNG.",
            owner_id=user.id if user is not None else 0,
            kind="success",
        )

    def compare_saved_build(self, snapshot_id: int) -> None:
        payload = self._build_snapshot_payload()
        owner_id, uid, character_id = self._history_context()
        if payload is None:
            self.set_status("A build atual ainda não terminou de carregar.", "error")
            return
        snapshot = next(
            (
                item for item in self.build_history_database.snapshots(
                    owner_id, uid, character_id
                )
                if item.id == snapshot_id
            ),
            None,
        )
        if snapshot is None:
            self._refresh_build_history()
            self.set_status("Essa build salva não foi encontrada.", "error")
            return
        BuildComparisonDialog(snapshot, payload, self).exec()

    def delete_saved_build(self, snapshot_id: int) -> None:
        owner_id, _uid, _character_id = self._history_context()
        if not ConfirmBuildDeleteDialog(self).exec():
            return
        if self.build_history_database.delete(owner_id, snapshot_id):
            self._refresh_build_history()
            self.set_status("Build salva excluída.", "success")
        else:
            self.set_status("Não foi possível encontrar a build salva.", "error")

    def _selected_saved_build(self, snapshot_id: int):
        owner_id, uid, character_id = self._history_context()
        return next(
            (item for item in self.build_history_database.snapshots(
                owner_id, uid, character_id) if item.id == snapshot_id),
            None,
        )

    def edit_saved_build(self, snapshot_id: int) -> None:
        snapshot = self._selected_saved_build(snapshot_id)
        if snapshot is None:
            self._refresh_build_history()
            self.set_status("Essa build salva não foi encontrada.", "error")
            return
        dialog = BuildMetadataDialog(snapshot, self)
        if not dialog.exec():
            return
        owner_id, _uid, _character_id = self._history_context()
        if self.build_history_database.update_metadata(
            owner_id, snapshot_id, **dialog.metadata()
        ):
            self._refresh_build_history()
            self.set_status("Nome, notas e favorito atualizados.", "success")

    def set_saved_build_favorite(self, snapshot_id: int, favorite: bool) -> None:
        snapshot = self._selected_saved_build(snapshot_id)
        if snapshot is None:
            self._refresh_build_history()
            return
        owner_id, _uid, _character_id = self._history_context()
        self.build_history_database.update_metadata(
            owner_id, snapshot_id, name=snapshot.name, note=snapshot.note,
            favorite=favorite,
        )
        self._refresh_build_history()
        self.set_status(
            "Build marcada como favorita." if favorite else "Favorito removido.",
            "success",
        )

    def set_build_retention(self, limit: int) -> None:
        owner_id, _uid, _character_id = self._history_context()
        try:
            self.build_history_database.set_retention_limit(owner_id, limit)
        except ValueError as error:
            self.set_status(str(error), "error")
            return
        self._refresh_build_history()
        self.set_status(
            f"Limite de {limit} versões por personagem salvo. "
            "O excedente sem favorito será removido ao salvar outra build.",
            "success",
        )

    def _fribbels_benchmark_ready(self, cache_key: str, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        character_id = str(payload.get("characterId", ""))
        uid = cache_key.partition(":")[0]
        owner_id, tab_uid = self.benchmark_tab_contexts.get(
            cache_key, (self.uid_workspace.owner_id, "")
        )
        if tab_uid and owner_id != self.uid_workspace.owner_id:
            return
        session = self.uid_workspace.sessions.get(tab_uid) if tab_uid else None
        if tab_uid and (session is None or tab_uid != uid):
            return
        if (
            not tab_uid
            and (
                self.build_source != "own"
                or self.current_account is None
                or self.current_account.uid != uid
            )
        ):
            return
        characters = (
            session.account.characters
            if session is not None and session.account is not None
            else self.current_characters
        )
        character = next(
            (item for item in characters if str(item.avatar_id) == character_id),
            None,
        )
        if character is None:
            return
        target_cache = session.fribbels_cache if session is not None else self.fribbels_cache
        target_results = (
            session.benchmark_results if session is not None else self.benchmark_results
        )
        target_cache[cache_key] = payload
        result = target_results.get(character_id)
        if result is None:
            return
        self.benchmark_engine.apply_fribbels_result(character, result, payload)
        is_visible_context = (
            self.active_uid_tab == uid and self.build_source in {"manual", "friend"}
            if session is not None else self.build_source == "own"
        )
        if (
            self.current_character_id == character_id
            and self.current_account is not None
            and self.current_account.uid == uid
            and is_visible_context
        ):
            self._render_benchmark(result)
        section_context = self.benchmark_section_contexts.get(cache_key)
        if section_context is not None:
            self.section_loading.ready("benchmark", section_context)

    def _fribbels_benchmark_failed(self, cache_key: str, message: str) -> None:
        sync_key = f"benchmark:{cache_key}"
        uid = cache_key.partition(":")[0]
        owner_id, tab_uid = self.benchmark_tab_contexts.get(
            cache_key, (self.uid_workspace.owner_id, "")
        )
        if tab_uid and owner_id != self.uid_workspace.owner_id:
            return
        session = self.uid_workspace.sessions.get(tab_uid) if tab_uid else None
        if tab_uid and (session is None or tab_uid != uid):
            return
        if (
            not tab_uid
            and (
                self.build_source != "own"
                or self.current_account is None
                or self.current_account.uid != uid
            )
        ):
            return
        characters = (
            session.account.characters
            if session is not None and session.account is not None
            else self.current_characters
        )
        character = next(
            (
                item for item in characters
                if f":{item.avatar_id}:" in cache_key
            ),
            None,
        )
        is_visible = bool(
            character is not None
            and self.current_character_id == str(character.avatar_id)
            and self.current_account is not None
            and self.current_account.uid == uid
            and (
                self.active_uid_tab == uid
                and self.build_source in {"manual", "friend"}
                if session is not None else self.build_source == "own"
            )
        )
        if character is not None:
            character_id = str(character.avatar_id)
            if "não possui DPS Benchmark" in message:
                self.failed_sync_tasks.add(sync_key)
                self.sync_manager.finish(sync_key, "Benchmark indisponível para esta build")
                unsupported = (
                    session.unsupported_benchmark_characters
                    if session is not None else self.unsupported_benchmark_characters
                )
                results = (
                    session.benchmark_results
                    if session is not None else self.benchmark_results
                )
                unsupported.add(character_id)
                result = results.get(character_id)
                if result is not None:
                    self._mark_benchmark_unsupported(result)
                    if is_visible:
                        self._render_benchmark(result)
                section_context = self.benchmark_section_contexts.get(cache_key)
                if section_context is not None:
                    self.section_loading.ready("benchmark", section_context)
                return
            if is_visible:
                self.benchmark_card.set_engine_error(message)
                self.set_status(f"Motor Fribbels indisponível: {message}", "error")
            section_context = self.benchmark_section_contexts.get(cache_key)
            if section_context is not None:
                self.section_loading.fail(
                    "benchmark", "Falha no cálculo avançado.",
                    details=message, context=section_context,
                )
        self.failed_sync_tasks.add(sync_key)
        self.sync_manager.fail(
            sync_key, "Falha ao calcular o benchmark", details=message
        )

    @staticmethod
    def _mark_benchmark_unsupported(result) -> None:  # type: ignore[no-untyped-def]
        result.score = 0.0
        result.grade = "N/A"
        result.damage_index = 0.0
        result.baseline_value = 0.0
        result.benchmark_value = 0.0
        result.perfection_value = 0.0
        result.upgrades = []
        result.main_upgrades = []
        result.exact_simulation = False
        result.engine_source = "unsupported"

    def _benchmark_worker_finished(self, worker: FribbelsBenchmarkWorker) -> None:
        sync_key = f"benchmark:{worker.request_key}"
        if sync_key in self.failed_sync_tasks:
            self.failed_sync_tasks.discard(sync_key)
        else:
            self.sync_manager.finish(sync_key, "Benchmark calculado")
        self.active_benchmark_ids.discard(worker.request_key)
        self.benchmark_tab_contexts.pop(worker.request_key, None)
        self.benchmark_section_contexts.pop(worker.request_key, None)
        self.benchmark_workers.discard(worker)
        worker.deleteLater()
        if not self.benchmark_workers:
            current = next(
                (
                    item for item in self.current_characters
                    if str(item.avatar_id) == self.current_character_id
                ),
                None,
            )
            if (
                current is not None
                and str(current.avatar_id) not in self.unsupported_benchmark_characters
                and self._benchmark_cache_key(current) not in self.fribbels_cache
            ):
                self._display_benchmark(current)

    @staticmethod
    def _clear_layout(layout) -> None:  # type: ignore[no-untyped-def]
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                BuildActions._clear_layout(item.layout())
