from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QCompleter, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.ui.motion import AnimatedDialog as QDialog
from app.benchmark.catalog import ASSETS_PATH, CatalogEntry, load_catalog
from app.ui.widgets import AvatarLabel, FadeComboBox, FadeSpinBox


@lru_cache(maxsize=512)
def _icon(path: str) -> QIcon:
    return QIcon(path)


class SearchableComboBox(FadeComboBox):
    """Seletor com ícones, pesquisa parcial e sem criação de itens livres."""

    def __init__(self, placeholder: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.setMinimumContentsLength(12)
        self.setMinimumWidth(0)
        self.setIconSize(QSize(25, 25))
        self.setMaxVisibleItems(10)
        editor = self.lineEdit()
        if editor is not None:
            editor.setPlaceholderText(placeholder)
            editor.setClearButtonEnabled(True)
            editor.textEdited.connect(self._mark_unselected)
        self.search = QCompleter(self.model(), self)
        self.search.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.search.setMaxVisibleItems(10)
        self.setCompleter(self.search)
        self.search.activated.connect(self._select_completion)

    def _mark_unselected(self, text: str) -> None:
        index = self.currentIndex()
        if index < 0 or self.itemText(index).casefold() == text.casefold():
            return
        self.setCurrentIndex(-1)
        editor = self.lineEdit()
        if editor is not None:
            editor.setText(text)

    def _select_completion(self, text: str) -> None:
        for index in range(self.count()):
            if self.itemText(index).casefold() == text.casefold():
                self.setCurrentIndex(index)
                return

    def select_text(self, text: str) -> bool:
        """Seleciona uma opção pesquisada; útil também para testes da interface."""
        self._select_completion(text)
        return self.currentIndex() >= 0 and self.currentText().casefold() == text.casefold()


class DialogDragHeader(QFrame):
    """Cabeçalho integrado que também permite mover o modal sem barra nativa."""

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            handle = window.windowHandle() if window is not None else None
            if handle is not None:
                handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)


class TeamMemberEditor(QFrame):
    def __init__(
        self,
        position: int,
        initial: dict[str, object] | None = None,
        excluded_character_id: str = "",
    ) -> None:
        super().__init__()
        self.setObjectName("teamEditorCard")
        self.characters, self.light_cones, self.relics, self.ornaments = load_catalog()
        self.initial = initial or {}
        layout = QGridLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(7)

        self.preview_avatar = AvatarLabel(46)
        self.preview_avatar.setObjectName("teamPreviewAvatar")
        position_badge = QLabel(f"{position:02d}")
        position_badge.setObjectName("teamPositionBadge")
        position_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        identity = QVBoxLayout()
        identity.setSpacing(0)
        self.preview_name = QLabel(f"Companheiro {position}")
        self.preview_name.setObjectName("teamEditorName")
        self.preview_path = QLabel("Selecione um personagem")
        self.preview_path.setObjectName("teamEditorPath")
        identity.addWidget(self.preview_name)
        identity.addWidget(self.preview_path)
        layout.addWidget(position_badge, 0, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.preview_avatar, 0, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(identity, 0, 2, 1, 6)

        self.character = SearchableComboBox("Pesquisar personagem…")
        self.eidolon = FadeSpinBox()
        self.eidolon.setRange(0, 6)
        self.eidolon.setPrefix("E")
        self.cone = SearchableComboBox("Pesquisar cone compatível…")
        self.superimposition = FadeSpinBox()
        self.superimposition.setRange(1, 5)
        self.superimposition.setPrefix("S")
        self.relic = SearchableComboBox("Pesquisar conjunto…")
        self.ornament = SearchableComboBox("Pesquisar ornamento…")

        identity_label = QLabel("PERSONAGEM")
        identity_label.setObjectName("teamGroupLabel")
        equipment_label = QLabel("EQUIPAMENTO")
        equipment_label.setObjectName("teamGroupLabel")
        bonus_label = QLabel("BÔNUS DE EQUIPE")
        bonus_label.setObjectName("teamGroupLabel")
        layout.addWidget(identity_label, 1, 0, 1, 8)
        self._add_label(layout, "Personagem", 2, 0)
        self._add_label(layout, "Eidolon", 2, 6)
        layout.addWidget(self.character, 3, 0, 1, 6)
        layout.addWidget(self.eidolon, 3, 6, 1, 2)
        layout.addWidget(equipment_label, 4, 0, 1, 8)
        self._add_label(layout, "Cone de Luz", 5, 0)
        self._add_label(layout, "Sobreposição", 5, 6)
        layout.addWidget(self.cone, 6, 0, 1, 6)
        layout.addWidget(self.superimposition, 6, 6, 1, 2)
        layout.addWidget(bonus_label, 7, 0, 1, 8)
        self._add_label(layout, "Conjunto de relíquias", 8, 0)
        self._add_label(layout, "Ornamento plano", 8, 4)
        layout.addWidget(self.relic, 9, 0, 1, 4)
        layout.addWidget(self.ornament, 9, 4, 1, 4)
        for column in range(8):
            layout.setColumnStretch(column, 1)

        for item in self.characters:
            if item.id == excluded_character_id:
                continue
            self.character.addItem(
                _icon(str(ASSETS_PATH / "icon" / "avatar" / f"{item.id}.webp")),
                item.name, item,
            )
        self._fill_sets(self.relic, self.relics)
        self._fill_sets(self.ornament, self.ornaments)
        self.character.currentIndexChanged.connect(self._refresh_cones)
        self.character.currentIndexChanged.connect(self._update_preview)
        if not self.initial and self.character.count() > position - 1:
            self.character.setCurrentIndex(position - 1)
        self._restore()
        self._update_preview()

    @staticmethod
    def _add_label(layout: QGridLayout, text: str, row: int, column: int) -> None:
        label = QLabel(text)
        label.setObjectName("metricTitle")
        layout.addWidget(label, row, column)

    @staticmethod
    def _fill_sets(combo: SearchableComboBox, entries: list[CatalogEntry]) -> None:
        combo.addItem("Nenhum", None)
        for item in entries:
            combo.addItem(
                _icon(str(ASSETS_PATH / "icon" / "relic" / f"{item.id}.webp")),
                item.name, item,
            )

    @staticmethod
    def _select_id(combo: SearchableComboBox, entry_id: str) -> None:
        for index in range(combo.count()):
            item = combo.itemData(index)
            if isinstance(item, CatalogEntry) and item.id == entry_id:
                combo.setCurrentIndex(index)
                return

    @staticmethod
    def _select_internal_name(combo: SearchableComboBox, name: str) -> None:
        for index in range(combo.count()):
            item = combo.itemData(index)
            if isinstance(item, CatalogEntry) and item.internal_name == name:
                combo.setCurrentIndex(index)
                return

    def _refresh_cones(self) -> None:
        selected = self.cone.currentData()
        selected_id = selected.id if isinstance(selected, CatalogEntry) else str(
            self.initial.get("lightCone", "")
        )
        character = self.character.currentData()
        path = character.path if isinstance(character, CatalogEntry) else ""
        self.cone.blockSignals(True)
        self.cone.clear()
        for item in self.light_cones:
            if item.path == path:
                self.cone.addItem(
                    _icon(str(ASSETS_PATH / "icon" / "light_cone" / f"{item.id}.webp")),
                    item.name, item,
                )
        self._select_id(self.cone, selected_id)
        self.cone.blockSignals(False)

    def _update_preview(self) -> None:
        character = self.character.currentData()
        self.preview_avatar.clear_image()
        if not isinstance(character, CatalogEntry):
            self.preview_name.setText("Pesquisar personagem")
            self.preview_path.setText("Digite parte do nome para filtrar")
            return
        self.preview_name.setText(character.name)
        self.preview_path.setText(
            f"{character.path.upper()}  ·  {character.rarity}★"
        )
        self.preview_avatar.set_image(QPixmap(str(
            ASSETS_PATH / "icon" / "avatar" / f"{character.id}.webp"
        )))

    def _restore(self) -> None:
        self._select_id(self.character, str(self.initial.get("characterId", "")))
        self._refresh_cones()
        self._select_id(self.cone, str(self.initial.get("lightCone", "")))
        self.eidolon.setValue(int(self.initial.get("characterEidolon", 0)))
        self.superimposition.setValue(int(self.initial.get("lightConeSuperimposition", 1)))
        self._select_internal_name(self.relic, str(self.initial.get("teamRelicSet", "")))
        self._select_internal_name(self.ornament, str(self.initial.get("teamOrnamentSet", "")))

    def value(self) -> dict[str, object]:
        character = self.character.currentData()
        cone = self.cone.currentData()
        relic = self.relic.currentData()
        ornament = self.ornament.currentData()
        return {
            "characterId": character.id if isinstance(character, CatalogEntry) else "",
            "characterEidolon": self.eidolon.value(),
            "lightCone": cone.id if isinstance(cone, CatalogEntry) else "",
            "lightConeSuperimposition": self.superimposition.value(),
            "teamRelicSet": relic.internal_name if isinstance(relic, CatalogEntry) else None,
            "teamOrnamentSet": ornament.internal_name if isinstance(ornament, CatalogEntry) else None,
        }


class CustomTeamDialog(QDialog):
    def __init__(
        self,
        initial: list[dict[str, object]],
        parent: QWidget | None = None,
        excluded_character_id: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Time customizado · Astral Optimizer")
        self.setObjectName("customTeamDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setModal(True)
        self.resize(920, 760)
        self.setMinimumSize(760, 610)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        header = DialogDragHeader()
        header.setObjectName("customTeamHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 12, 15, 12)
        mark = QLabel("✦")
        mark.setObjectName("customTeamMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("TIME CUSTOMIZADO")
        title.setObjectName("customTeamTitle")
        subtitle = QLabel(
            "Monte a composição usada no cálculo do DPS Benchmark."
        )
        subtitle.setObjectName("customTeamSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        self.team_status = QLabel("0/3 selecionados")
        self.team_status.setObjectName("teamSelectionStatus")
        close = QPushButton("×")
        close.setObjectName("dialogCloseButton")
        close.setFixedSize(34, 30)
        close.setToolTip("Fechar")
        close.clicked.connect(self.reject)
        for label in (mark, title, subtitle, self.team_status):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        header_layout.addWidget(mark)
        header_layout.addLayout(titles, 1)
        header_layout.addWidget(self.team_status)
        header_layout.addWidget(close)
        root.addWidget(header)

        search_tip = QLabel(
            "⌕  Clique em qualquer seletor e digite parte do nome para pesquisar."
        )
        search_tip.setObjectName("teamSearchTip")
        root.addWidget(search_tip)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("scrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(9)
        self.editors = [
            TeamMemberEditor(
                index + 1,
                initial[index] if index < len(initial) else None,
                excluded_character_id,
            )
            for index in range(3)
        ]
        for editor in self.editors:
            content_layout.addWidget(editor)
            editor.character.currentIndexChanged.connect(self._update_team_status)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("teamDialogFooter")
        actions = QHBoxLayout(footer)
        actions.setContentsMargins(12, 10, 12, 10)
        self.validation = QLabel("")
        self.validation.setObjectName("teamValidation")
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self.reject)
        self.apply_button = QPushButton("Aplicar e recalcular  →")
        self.apply_button.setObjectName("primaryButton")
        self.apply_button.clicked.connect(self._submit)
        actions.addWidget(self.validation, 1)
        actions.addStretch(1)
        actions.addWidget(cancel)
        actions.addWidget(self.apply_button)
        root.addWidget(footer)
        self._update_team_status()

    def _update_team_status(self) -> None:
        selected = [
            editor.character.currentData()
            for editor in self.editors
            if isinstance(editor.character.currentData(), CatalogEntry)
        ]
        unique = len({item.id for item in selected})
        if len(selected) == 3 and unique < 3:
            self.team_status.setText("Personagens repetidos")
        else:
            self.team_status.setText(f"{len(selected)}/3 selecionados")
        self.team_status.setProperty(
            "state", "ready" if len(selected) == unique == 3 else "pending"
        )
        self.team_status.style().unpolish(self.team_status)
        self.team_status.style().polish(self.team_status)

    def _submit(self) -> None:
        team = self.team()
        character_ids = [str(member.get("characterId", "")) for member in team]
        if not all(character_ids):
            self._show_validation("Selecione os três personagens.")
            return
        if len(set(character_ids)) != 3:
            self._show_validation("Cada posição precisa de um personagem diferente.")
            return
        if not all(member.get("lightCone") for member in team):
            self._show_validation("Selecione um cone compatível para cada personagem.")
            return
        self.validation.clear()
        self.accept()

    def _show_validation(self, message: str) -> None:
        self.validation.setText(f"⚠  {message}")

    def team(self) -> list[dict[str, object]]:
        return [editor.value() for editor in self.editors]
