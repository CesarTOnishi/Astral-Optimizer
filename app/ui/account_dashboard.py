from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget

from app.ui.motion import AnimatedProgressBar as QProgressBar

from app.ui.image_loader import ImageLoader
from app.ui.contextual_help import GUARANTEE_HELP, PITY_HELP, ContextHelpButton
from app.ui.widgets import AvatarLabel, FRIBBELS_ASSETS
from app.ui.warp_panel import BANNER_CONFIG, WarpPanel
from app.warp.statistics import five_star_history, pity_state


class CompactMetricCard(QFrame):
    def __init__(self, title: str, value: str) -> None:
        super().__init__()
        self.setObjectName("accountMetricCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        label = QLabel(title)
        label.setObjectName("accountMetricTitle")
        label.setWordWrap(True)
        self.value = QLabel(value)
        self.value.setObjectName("accountMetricValue")
        layout.addWidget(self.value)
        layout.addWidget(label)


class AccountDashboard(QWidget):
    def __init__(self, image_loader: ImageLoader | None = None):
        super().__init__()
        self.image_loader = image_loader or ImageLoader(self)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(14)
        self.body.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._metric_cards: list[CompactMetricCard] = []
        self._section_frames: list[QFrame] = []
        self._metric_columns = 0
        self._section_columns = 0

    def _label(self, text, layout, style="muted"):
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setObjectName(style)
        layout.addWidget(label)
        return label

    def _section(self, title, helps=()):
        frame = QFrame()
        frame.setObjectName("accountDashboardSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        header = QHBoxLayout()
        section_title = QLabel(title)
        section_title.setObjectName("sectionTitle")
        section_title.setWordWrap(True)
        header.addWidget(section_title)
        for help_content in helps:
            header.addWidget(ContextHelpButton(*help_content))
        header.addStretch(1)
        layout.addLayout(header)
        return frame, layout

    def _image_row(self, text, layout, *, icon_url="", icon_path=None, rounded=False):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row.setObjectName("accountCompactRow")
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(8)
        icon = AvatarLabel(40, rounded=rounded)
        icon.setToolTip(text.split(" · ", 1)[0])
        row_layout.addWidget(icon)
        details = QVBoxLayout()
        details.setSpacing(1)
        name, _, metadata = text.partition(" · ")
        self._label(name, details, "characterName")
        self._label(metadata, details)
        row_layout.addLayout(details, 1)
        layout.addWidget(row)
        if icon_path is not None and icon_path.is_file():
            icon.set_image(QPixmap(str(icon_path)))
        elif icon_url:
            self.image_loader.load(icon_url, icon.set_image)

    def refresh(self, user, account, warp_database, relic_database, engine):
        while self.body.count():
            item = self.body.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self._metric_cards = []
        self._section_frames = []
        self._metric_columns = 0
        self._section_columns = 0
        if user is None:
            self._label("Entre no seu perfil para ver o resumo da conta.", self.body)
            return
        uid = user.game_uid
        account = account if account and account.uid == uid else None
        records = warp_database.records(uid, user.id) if uid else []
        summaries = warp_database.summaries(uid, user.id) if uid else {}
        relics = relic_database.relics(user.id, uid) if uid else []
        characters = account.characters if account else []
        # Resumos importados substituem os registros da categoria, sem duplicá-los.
        total = sum(s.total for s in summaries.values()) + sum(r.gacha_type not in summaries for r in records)
        five = sum(s.five_star_count for s in summaries.values()) + sum(r.rank_type == 5 and r.gacha_type not in summaries for r in records)
        metrics = QWidget()
        metrics.setObjectName("accountMetrics")
        self.metrics_grid = QGridLayout(metrics)
        self.metrics_grid.setContentsMargins(0, 0, 0, 0)
        self.metrics_grid.setSpacing(7)
        self.metrics = {}
        for title, value in (
            ("Personagens públicos", str(len(characters)) if account else "—"),
            ("Tiros registrados", str(total) if records or summaries else "—"),
            ("Resultados 5★", str(five) if records or summaries else "—"),
            ("Relíquias salvas", str(len(relics))),
        ):
            card = CompactMetricCard(title, value)
            self._metric_cards.append(card)
            self.metrics[title] = value
        self.body.addWidget(metrics)

        sections = QWidget()
        sections.setObjectName("accountSections")
        self.sections_grid = QGridLayout(sections)
        self.sections_grid.setContentsMargins(0, 0, 0, 0)
        self.sections_grid.setSpacing(9)

        pity_frame, layout = self._section("Pity e Saltos", (PITY_HELP, GUARANTEE_HELP))
        self._section_frames.append(pity_frame)
        self._label("Pity calculado pelo histórico disponível; importações incompletas podem omitir tiros anteriores.", layout)
        self.banner_values = {}
        for kind, title, cap in BANNER_CONFIG:
            selected = [r for r in records if r.gacha_type == kind]
            summary = summaries.get(kind)
            state = pity_state(records, {kind}, WarpPanel._standard_ids(kind))
            pity = summary.five_star_pity if summary else state.five_star
            count = summary.total if summary else len(selected)
            known = bool(selected or summary)
            guarantee = ""
            if kind in {"11", "12", "21", "22"} and known:
                if summary or not any(r.rank_type == 5 for r in selected):
                    guarantee = " · Garantia desconhecida"
                else:
                    guarantee = " · Garantido" if state.guaranteed else " · Sem garantia"
            text = f"{title} · Pity {pity}/{cap} · {count} tiros{guarantee}" if known else f"{title} · Sem histórico importado"
            self.banner_values[kind] = text
            self._label(text, layout)
            progress = QProgressBar()
            progress.setRange(0, cap)
            progress.setValue(min(pity, cap) if known else 0)
            progress.setTextVisible(False)
            progress.setFixedHeight(6)
            layout.addWidget(progress)

        history_frame, layout = self._section("Últimos resultados 5★")
        self._section_frames.append(history_frame)
        history = five_star_history(records)[:5]
        for record, pity in history:
            avatar_path = FRIBBELS_ASSETS / "icon" / "avatar" / f"{record.item_id}.webp"
            icon_path = avatar_path if avatar_path.is_file() else FRIBBELS_ASSETS / "icon" / "light_cone" / f"{record.item_id}.webp"
            self._image_row(
                f"{record.name} · {record.banner_name} · Pity {pity} · {record.time}",
                layout, icon_path=icon_path, rounded=avatar_path.is_file(),
            )
        if not history:
            self._label("Nenhum resultado 5★ individual salvo. Importe seu histórico em Saltos.", layout)

        relic_frame, layout = self._section("Inventário de relíquias")
        self._section_frames.append(relic_frame)
        equipped = sum(bool(r.current_character_id) for r in relics)
        maximum = sum(r.relic.level == 15 and r.relic.rarity == 5 for r in relics)
        self._label(f"{equipped} vinculadas ao showcase atual · {len(relics) - equipped} fora do showcase · {maximum} peças 5★ no nível +15", layout)
        for stored in relics[:3]:
            self._image_row(
                f"{stored.relic.set_name} · {stored.relic.slot} +{stored.relic.level} · {stored.score:.1f} pts ({stored.grade}) · {stored.current_character_name or 'Fora do showcase'}",
                layout, icon_url=stored.relic.icon_url,
            )
        if not relics:
            self._label("As relíquias são salvas ao consultar a UID principal. O inventário completo do jogo não é disponibilizado pelo Enka.", layout)
        self.body.addWidget(sections)
        self._reflow_dashboard()

    def _reflow_dashboard(self) -> None:
        if not self._metric_cards or not hasattr(self, "metrics_grid"):
            return
        width = max(self.width(), 1)
        metric_columns = 4 if width >= 760 else (2 if width >= 360 else 1)
        if metric_columns != self._metric_columns:
            self._metric_columns = metric_columns
            while self.metrics_grid.count():
                self.metrics_grid.takeAt(0)
            for index, card in enumerate(self._metric_cards):
                self.metrics_grid.addWidget(
                    card, index // metric_columns, index % metric_columns
                )
            for column in range(4):
                self.metrics_grid.setColumnStretch(
                    column, 1 if column < metric_columns else 0
                )

        section_columns = 3 if width >= 1200 else (2 if width >= 820 else 1)
        if section_columns == self._section_columns:
            return
        self._section_columns = section_columns
        while self.sections_grid.count():
            self.sections_grid.takeAt(0)
        if section_columns == 3:
            for column, frame in enumerate(self._section_frames):
                self.sections_grid.addWidget(frame, 0, column)
        elif section_columns == 2:
            self.sections_grid.addWidget(self._section_frames[0], 0, 0)
            self.sections_grid.addWidget(self._section_frames[1], 0, 1)
            self.sections_grid.addWidget(self._section_frames[2], 1, 0, 1, 2)
        else:
            for row, frame in enumerate(self._section_frames):
                self.sections_grid.addWidget(frame, row, 0)
        for column in range(3):
            self.sections_grid.setColumnStretch(
                column, 1 if column < section_columns else 0
            )

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._reflow_dashboard()
