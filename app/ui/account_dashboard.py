from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from app.ui.image_loader import ImageLoader
from app.ui.widgets import AvatarLabel, FRIBBELS_ASSETS
from app.ui.warp_panel import BANNER_CONFIG, SummaryCard, WarpPanel
from app.warp.statistics import five_star_history, pity_state


class AccountDashboard(QWidget):
    def __init__(self, image_loader: ImageLoader | None = None):
        super().__init__()
        self.image_loader = image_loader or ImageLoader(self)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(14)

    def _label(self, text, layout, style="muted"):
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setObjectName(style)
        layout.addWidget(label)
        return label

    def _section(self, title):
        frame = QFrame()
        frame.setObjectName("accountProfilePanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        self._label(title, layout, "sectionTitle")
        self.body.addWidget(frame)
        return layout

    def _image_row(self, text, layout, *, icon_url="", icon_path=None, rounded=False):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 4, 0, 4)
        row_layout.setSpacing(12)
        icon = AvatarLabel(54, rounded=rounded)
        icon.setToolTip(text.split(" · ", 1)[0])
        row_layout.addWidget(icon)
        label = self._label(text, row_layout)
        row_layout.setStretchFactor(label, 1)
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
        grid = QGridLayout(metrics)
        grid.setContentsMargins(0, 0, 0, 0)
        self.metrics = {}
        for column, (title, value) in enumerate((
            ("Personagens públicos", str(len(characters)) if account else "—"),
            ("Tiros registrados", str(total) if records or summaries else "—"),
            ("Resultados 5★", str(five) if records or summaries else "—"),
            ("Relíquias salvas", str(len(relics))),
        )):
            card = SummaryCard(title)
            card.value.setText(value)
            self.metrics[title] = value
            grid.addWidget(card, 0, column)
        self.body.addWidget(metrics)
        self._label("Resumo da UID principal. Enka mostra apenas personagens públicos; Saltos e inventário refletem os dados salvos neste perfil.", self.body)

        layout = self._section("PITY E SALTOS")
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

        layout = self._section("ÚLTIMOS RESULTADOS 5★")
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

        layout = self._section("INVENTÁRIO DE RELÍQUIAS")
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
