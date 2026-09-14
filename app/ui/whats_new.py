from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_ASSETS_DIR, APP_HOME_BACKGROUND
from app.whats_new import CURRENT_RELEASE, InstalledRelease, ReleaseHighlight


ARTWORK_PATHS = {
    "warps": APP_ASSETS_DIR / "news" / "warp_analytics.png",
    "import": APP_ASSETS_DIR / "news" / "guided_import.png",
    "backup": APP_ASSETS_DIR / "news" / "cloud_backup.png",
    "experience": APP_ASSETS_DIR / "news" / "personalization.png",
}


class FeatureArtwork(QWidget):
    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("releaseFeatureArtwork")
        self.source = QPixmap(str(ARTWORK_PATHS.get(kind, "")))
        self.setFixedSize(190, 124)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        target = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(target, 11, 11)
        painter.setClipPath(path)
        if self.source.isNull():
            painter.fillRect(target, QColor("#13243b"))
        else:
            scaled = self.source.scaled(
                target.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            source_x = max(0, (scaled.width() - target.width()) // 2)
            source_y = max(0, (scaled.height() - target.height()) // 2)
            painter.drawPixmap(
                target,
                scaled,
                scaled.rect().adjusted(
                    source_x,
                    source_y,
                    -(scaled.width() - target.width() - source_x),
                    -(scaled.height() - target.height() - source_y),
                ),
            )
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#496b91"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(target, 11, 11)
        painter.end()


class ReleaseFeatureCard(QFrame):
    requested = Signal(str)

    def __init__(self, feature: ReleaseHighlight, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.feature = feature
        self.setObjectName("releaseFeatureCard")
        self.setMinimumWidth(300)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 13, 13, 13)
        layout.setSpacing(10)

        body = QHBoxLayout()
        body.setSpacing(13)

        artwork = FeatureArtwork(feature.artwork)
        body.addWidget(artwork, alignment=Qt.AlignmentFlag.AlignTop)

        information = QVBoxLayout()
        information.setSpacing(5)
        categories = {
            "warps": "COMPARTILHAMENTO",
            "import": "IMPORTAÇÃO",
            "backup": "SEGURANÇA",
            "experience": "PERSONALIZAÇÃO",
        }
        category = QLabel(categories.get(feature.artwork, "NOVIDADE"))
        category.setObjectName("releaseFeatureCategory")
        information.addWidget(category)

        title = QLabel(feature.title)
        title.setObjectName("releaseFeatureTitle")
        description = QLabel(feature.description)
        description.setObjectName("releaseFeatureDescription")
        description.setWordWrap(True)
        information.addWidget(title)
        information.addWidget(description)

        for detail in feature.details:
            item = QLabel(f"✓  {detail}")
            item.setObjectName("releaseFeatureDetail")
            item.setWordWrap(True)
            information.addWidget(item)
        information.addStretch(1)
        body.addLayout(information, 1)
        layout.addLayout(body)

        action = QPushButton(feature.action_label)
        action.setObjectName("releaseFeatureButton")
        action.clicked.connect(lambda: self.requested.emit(feature.destination))
        layout.addWidget(action)


class WhatsNewPanel(QWidget):
    resource_requested = Signal(str)

    def __init__(
        self,
        release: InstalledRelease = CURRENT_RELEASE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.release = release
        self.setObjectName("whatsNewPage")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("whatsNewScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("whatsNewContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(22, 18, 22, 24)
        layout.setSpacing(15)

        hero = QFrame()
        hero.setObjectName("whatsNewHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 18, 22)
        hero_layout.setSpacing(20)
        copy = QVBoxLayout()
        badge = QLabel(f"NOVIDADES  ·  VERSÃO {release.version}")
        badge.setObjectName("whatsNewBadge")
        headline = QLabel(release.headline)
        headline.setObjectName("whatsNewHeadline")
        headline.setWordWrap(True)
        summary = QLabel(release.summary)
        summary.setObjectName("whatsNewSummary")
        summary.setWordWrap(True)
        copy.addWidget(badge)
        copy.addWidget(headline)
        copy.addWidget(summary)
        facts = QHBoxLayout()
        facts.setSpacing(7)
        for text in ("✓  VERSÃO INSTALADA", f"{len(release.highlights)}  DESTAQUES"):
            fact = QLabel(text)
            fact.setObjectName("whatsNewFact")
            facts.addWidget(fact)
        facts.addStretch(1)
        copy.addLayout(facts)
        copy.addStretch(1)
        hero_layout.addLayout(copy, 3)
        hero_image = QLabel()
        hero_image.setObjectName("whatsNewHeroImage")
        image = QPixmap(str(APP_HOME_BACKGROUND))
        if not image.isNull():
            hero_image.setPixmap(image)
        hero_image.setScaledContents(True)
        hero_image.setFixedSize(280, 132)
        hero_layout.addWidget(hero_image, 2)
        layout.addWidget(hero)

        section = QHBoxLayout()
        title = QLabel("O QUE MUDOU")
        title.setObjectName("brandTitle")
        hint = QLabel("Acesse cada novidade diretamente pelos cartões.")
        hint.setObjectName("muted")
        section.addWidget(title)
        section.addStretch(1)
        section.addWidget(hint)
        layout.addLayout(section)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        self.feature_cards: list[ReleaseFeatureCard] = []
        for index, feature in enumerate(release.highlights):
            card = ReleaseFeatureCard(feature)
            card.requested.connect(self.resource_requested)
            self.feature_cards.append(card)
        self.feature_grid = grid
        self._grid_columns = 0
        self._relayout_cards(2)
        layout.addLayout(grid)
        layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        columns = 2 if event.size().width() >= 900 else 1
        self._relayout_cards(columns)
        super().resizeEvent(event)

    def _relayout_cards(self, columns: int) -> None:
        if columns == self._grid_columns:
            return
        while self.feature_grid.count():
            item = self.feature_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().setParent(self)
        for index, card in enumerate(self.feature_cards):
            self.feature_grid.addWidget(card, index // columns, index % columns)
        for column in range(2):
            self.feature_grid.setColumnStretch(column, 1 if column < columns else 0)
        self._grid_columns = columns
