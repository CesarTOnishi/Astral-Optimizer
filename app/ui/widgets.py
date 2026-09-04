from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QEasingCurve, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.benchmark.models import BenchmarkResult, RelicRating, UpgradeComparison
from app.models import CharacterStat, CharacterSummary, RelicSummary


COMPACT_STAT_NAMES = {
    "StatusProbability": "Acerto de Efeito",
    "SPRatio": "Regen de Energia",
}

FRIBBELS_ASSETS = (
    Path(__file__).resolve().parents[2]
    / "third_party"
    / "fribbels-hsr-optimizer"
    / "public"
    / "assets"
)


def rounded_pixmap(source: QPixmap, size: int, radius: int | None = None) -> QPixmap:
    if source.isNull():
        return QPixmap()
    radius = radius if radius is not None else size // 2
    scaled = source.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return result


class FadeComboItemDelegate(QStyledItemDelegate):
    """Desenha o hover de cada opção com uma transição gradual."""

    def __init__(self, combo: QComboBox) -> None:
        super().__init__(combo)
        self.combo = combo
        self.hover_row = -1
        self.hover_progress = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._set_progress)
        self.animation.finished.connect(self._animation_finished)
        self.popup_view = combo.view()
        self.popup_viewport = self.popup_view.viewport()
        self.popup_view.setMouseTracking(True)
        self.popup_viewport.setMouseTracking(True)
        self.popup_viewport.installEventFilter(self)

    def _animate(self, target: float) -> None:
        self.animation.stop()
        self.animation.setStartValue(self.hover_progress)
        self.animation.setEndValue(target)
        self.animation.start()

    def _set_progress(self, value: object) -> None:
        self.hover_progress = float(value)
        try:
            self.popup_viewport.update()
        except RuntimeError:
            self.animation.stop()

    def _animation_finished(self) -> None:
        if self.hover_progress <= 0.001:
            self.hover_row = -1
            try:
                self.popup_viewport.update()
            except RuntimeError:
                return

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        if watched is self.popup_viewport:
            if event.type() == QEvent.Type.MouseMove:
                index = self.popup_view.indexAt(event.position().toPoint())
                row = index.row() if index.isValid() else -1
                if row != self.hover_row:
                    self.hover_row = row
                    self.hover_progress = 0.0
                    self._animate(1.0 if row >= 0 else 0.0)
            elif event.type() == QEvent.Type.Leave and self.hover_row >= 0:
                self._animate(0.0)
        return super().eventFilter(watched, event)

    def paint(self, painter: QPainter, option, index) -> None:  # type: ignore[no-untyped-def]
        clean = type(option)(option)
        selected = bool(clean.state & QStyle.StateFlag.State_Selected)
        clean.state &= ~QStyle.StateFlag.State_MouseOver
        clean.state &= ~QStyle.StateFlag.State_Selected

        if index.row() == self.hover_row and self.hover_progress > 0:
            start = QColor("#17243a")
            end = QColor("#315f88")
            progress = self.hover_progress
            background = QColor(
                round(start.red() + (end.red() - start.red()) * progress),
                round(start.green() + (end.green() - start.green()) * progress),
                round(start.blue() + (end.blue() - start.blue()) * progress),
            )
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(background)
            painter.drawRoundedRect(option.rect.adjusted(3, 2, -3, -2), 6, 6)
            painter.restore()
        elif selected:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#233f61"))
            painter.drawRoundedRect(option.rect.adjusted(3, 2, -3, -2), 6, 6)
            painter.restore()
        super().paint(painter, clean, index)


class FadeComboBox(QComboBox):
    """ComboBox com uma transição suave de brilho ao passar o mouse."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hover_progress = 0.0
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setOffset(0, 0)
        self._glow.setBlurRadius(5)
        self._glow.setColor(QColor(100, 197, 238, 0))
        self.setGraphicsEffect(self._glow)
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(170)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_animation.valueChanged.connect(self._set_hover_progress)
        self._item_delegate = FadeComboItemDelegate(self)
        self.setItemDelegate(self._item_delegate)

    def _animate_hover(self, target: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(target)
        self._hover_animation.start()

    def _set_hover_progress(self, value: object) -> None:
        self._hover_progress = float(value)
        color = QColor(100, 197, 238)
        color.setAlpha(round(105 * self._hover_progress))
        self._glow.setColor(color)
        self._glow.setBlurRadius(5 + 8 * self._hover_progress)
        if self._hover_progress <= 0.001:
            self.setStyleSheet("")
            return
        background = self._mixed_color(
            QColor("#0d1729"), QColor("#172f4b"), self._hover_progress
        )
        border = self._mixed_color(
            QColor("#334967"), QColor("#69bde7"), self._hover_progress
        )
        self.setStyleSheet(
            "QComboBox {"
            f"background-color: {background.name()};"
            f"border: 1px solid {border.name()};"
            "}"
        )

    @staticmethod
    def _mixed_color(start: QColor, end: QColor, progress: float) -> QColor:
        progress = max(0.0, min(1.0, progress))
        return QColor(
            round(start.red() + (end.red() - start.red()) * progress),
            round(start.green() + (end.green() - start.green()) * progress),
            round(start.blue() + (end.blue() - start.blue()) * progress),
        )

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt API
        # Evita alterar a opção sem querer ao rolar a página. O popup possui
        # sua própria área de rolagem e continua respondendo à roda do mouse.
        if not self.view().isVisible():
            event.ignore()
            return
        super().wheelEvent(event)


class FadeSpinBox(QSpinBox):
    """Campo numérico sem aparência nativa e com brilho suave de interação."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._glow_progress = 0.0
        self._hovered = False
        self._focused = False
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setOffset(0, 0)
        self._glow.setBlurRadius(5)
        self._glow.setColor(QColor(105, 207, 250, 0))
        self.setGraphicsEffect(self._glow)
        self._glow_animation = QVariantAnimation(self)
        self._glow_animation.setDuration(170)
        self._glow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._glow_animation.valueChanged.connect(self._set_glow_progress)

    def _animate_glow(self) -> None:
        target = 1.0 if self._focused else (0.58 if self._hovered else 0.0)
        self._glow_animation.stop()
        self._glow_animation.setStartValue(self._glow_progress)
        self._glow_animation.setEndValue(target)
        self._glow_animation.start()

    def _set_glow_progress(self, value: object) -> None:
        self._glow_progress = float(value)
        color = QColor(105, 207, 250)
        color.setAlpha(round(115 * self._glow_progress))
        self._glow.setColor(color)
        self._glow.setBlurRadius(5 + 8 * self._glow_progress)

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._hovered = True
        self._animate_glow()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._hovered = False
        self._animate_glow()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._focused = True
        self._animate_glow()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._focused = False
        self._animate_glow()
        super().focusOutEvent(event)


class AvatarLabel(QLabel):
    def __init__(self, size: int, rounded: bool = True) -> None:
        super().__init__("✦")
        self.image_size = size
        self.rounded = rounded
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background:#16243d; color:#6ed8ff; border:1px solid #35547c; "
            f"border-radius:{size // 2 if rounded else 12}px; font-size:{max(size // 3, 16)}px;"
        )

    def set_image(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        radius = self.image_size // 2 if self.rounded else 12
        self.setText("")
        self.setPixmap(rounded_pixmap(pixmap, self.image_size, radius))

    def clear_image(self) -> None:
        self.setPixmap(QPixmap())
        self.setText("✦")


class ResponsiveImageLabel(QLabel):
    def __init__(self) -> None:
        super().__init__("✦")
        self.source = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.setMinimumSize(180, 280)
        self.setStyleSheet("color:#e7b2ff; font-size:42px; background:transparent;")

    def set_image(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self.source = pixmap
        self.setText("")
        self.setPixmap(QPixmap())
        self.update()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.source.isNull() or self.width() < 1 or self.height() < 1:
            super().paintEvent(event)
            return

        zoom = 1.08
        image = self.source.scaled(
            max(1, round(self.width() * zoom)),
            max(1, round(self.height() * zoom)),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - image.width()) / 2.0
        y = self.height() - image.height()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setClipRect(self.rect())
        painter.drawPixmap(round(x), round(y), image)
        painter.end()


class LightConeBanner(QFrame):
    """Banner compacto com recorte da arte completa do cone equipado."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("lightConeBanner")
        self.source = QPixmap()
        self.setFixedHeight(132)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.addStretch(1)
        self.caption = QLabel("Sem Cone de Luz")
        self.caption.setObjectName("lightConeBannerCaption")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setWordWrap(False)
        layout.addWidget(self.caption, alignment=Qt.AlignmentFlag.AlignHCenter)

    def set_info(self, name: str, level: int, rank: int) -> None:
        prefix = f"S{rank}" if rank else "S—"
        self.caption.setText(f"{prefix} · {name}")
        self.caption.setToolTip(
            f"{name}\nNível {level or '—'} · Sobreposição {prefix}"
        )

    def set_image(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self.source = pixmap
        self.update()

    def clear_image(self) -> None:
        self.source = QPixmap()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        bounds = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(bounds, 9, 9)
        painter.setClipPath(clip)
        painter.fillPath(clip, QColor("#101a2d"))

        if not self.source.isNull():
            image = self.source.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - image.width()) // 2
            # As artes de cone são verticais e normalmente posicionam o rosto
            # acima do centro. O foco em 40% mantém essa região no banner.
            overflow_y = max(0, image.height() - self.height())
            y = -round(overflow_y * 0.40)
            painter.drawPixmap(x, y, image)

        shade = QLinearGradient(0, self.height() * 0.42, 0, self.height())
        shade.setColorAt(0, QColor(5, 9, 18, 0))
        shade.setColorAt(1, QColor(5, 9, 18, 205))
        painter.fillRect(self.rect(), shade)
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#687895"), 1))
        painter.drawRoundedRect(bounds, 9, 9)
        painter.end()


class MetricCard(QFrame):
    def __init__(self, title: str, value: str = "—") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class CharacterListCard(QWidget):
    def __init__(self, character: CharacterSummary) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(11)
        self.avatar = AvatarLabel(54)
        layout.addWidget(self.avatar)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        name = QLabel(character.name)
        name.setObjectName("characterName")
        meta = QLabel(f"{character.element} · {character.path}")
        meta.setObjectName("characterMeta")
        level = QLabel(f"Nv. {character.level}  •  {'★' * character.rarity}")
        level.setObjectName("characterMeta")
        text_layout.addWidget(name)
        text_layout.addWidget(meta)
        text_layout.addWidget(level)
        layout.addLayout(text_layout, 1)

        eidolon = QLabel(f"E{character.eidolon}")
        eidolon.setObjectName("eidolonBadge")
        layout.addWidget(eidolon)

    def sizeHint(self) -> QSize:
        return QSize(300, 82)


class CharacterPortraitCard(QWidget):
    def __init__(self, character: CharacterSummary) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 5)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar = AvatarLabel(54)
        name = QLabel(character.name)
        name.setObjectName("portraitName")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setMaximumWidth(82)
        layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)

    def sizeHint(self) -> QSize:
        return QSize(94, 91)


class StatRow(QFrame):
    def __init__(self, stat: CharacterStat) -> None:
        super().__init__()
        self.setObjectName("statRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(5)
        name = QLabel(COMPACT_STAT_NAMES.get(stat.key, stat.name))
        name.setObjectName("rowName")
        value = QLabel(stat.formatted_value)
        value.setObjectName("rowValue")
        layout.addWidget(name)
        layout.addStretch(1)
        layout.addWidget(value)


class BenchmarkCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("benchmarkCard")
        self.setMaximumHeight(112)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 10)
        layout.setSpacing(5)

        header = QHBoxLayout()
        title = QLabel("DPS BENCHMARK")
        title.setObjectName("benchmarkTitle")
        self.mode = QLabel("BETA")
        self.mode.setObjectName("betaBadge")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.mode, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        score_row = QHBoxLayout()
        self.score = QLabel("—%")
        self.score.setObjectName("benchmarkScore")
        self.grade = QLabel("—")
        self.grade.setObjectName("benchmarkGrade")
        score_row.addWidget(self.score)
        score_row.addStretch(1)
        score_row.addWidget(self.grade)
        layout.addLayout(score_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 200)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.meta = QLabel("Aguardando personagem")
        self.meta.setObjectName("sectionHint")
        self.meta.setWordWrap(True)
        layout.addWidget(self.meta)

    def set_result(self, result: BenchmarkResult) -> None:
        if result.engine_source == "unsupported":
            self.mode.setText("SUB DPS")
            self.score.setText("—")
            self.grade.setText("N/A")
            self.progress.setValue(0)
            self.meta.show()
            self.meta.setText(
                "Este personagem não possui DPS Benchmark no motor Fribbels."
            )
            return
        self.score.setText(f"{result.score:.1f}%")
        self.grade.setText(result.grade)
        self.progress.setValue(round(result.score))
        self.mode.setText(
            "FRIBBELS" if result.engine_source == "fribbels"
            else ("ESPECIALIZADO" if result.exact_simulation else "ESTIMATIVA")
        )
        self.meta.clear()
        self.meta.hide()

    def set_loading(self) -> None:
        self.meta.show()
        self.mode.setText("FRIBBELS")
        self.score.setText("…")
        self.grade.setText("…")
        self.progress.setValue(0)
        self.meta.setText("Calculando rotação, time e benchmarks 0/100/200%â€¦")

    def set_engine_error(self, message: str) -> None:
        self.meta.show()
        self.mode.setText("FALLBACK")
        self.meta.setText(f"Motor Fribbels indisponível: {message}")


class CombatStatsCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("combatStatsCard")
        self.setMaximumHeight(165)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(4)

        title = QLabel("ATRIBUTOS EM COMBATE")
        title.setObjectName("benchmarkTitle")
        self.layout.addWidget(title)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(1)
        self.layout.addLayout(self.rows)

    def set_result(self, result: BenchmarkResult) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
        for stat in result.combat_stats:
            if not combat_stat_visible(result.archetype, stat.key, result.combat_focus):
                continue
            row = QHBoxLayout()
            name = QLabel(f"{stat.name} ↑" if stat.changed else stat.name)
            name.setObjectName("combatStatName")
            value = QLabel(stat.formatted_value)
            value.setObjectName("combatStatBuffed" if stat.changed else "combatStatValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(name)
            row.addStretch(1)
            row.addWidget(value)
            self.rows.addLayout(row)


class AbilityBreakdownCard(QFrame):
    """Dano exato de cada ação da rotação simulada pelo Fribbels."""

    ACTION_ICONS = {
        "BASIC": "⚔", "SKILL": "✦", "ULT": "◆", "FUA": "↻",
        "DOT": "◌", "BREAK": "◇", "MEMO_SKILL": "M",
        "MEMO_TALENT": "M", "ELATION_SKILL": "★", "UNIQUE": "◎",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("abilityBreakdownCard")
        self.setMaximumWidth(520)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 13, 14, 14)
        root.setSpacing(8)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("DANO POR HABILIDADE · BUILD ATUAL")
        title.setObjectName("abilityBreakdownTitle")
        subtitle = QLabel("Rotação calculada pelo motor Fribbels")
        subtitle.setObjectName("abilityBreakdownSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        exact = QLabel("DANO EXATO")
        exact.setObjectName("abilityBreakdownExact")
        header.addLayout(titles)
        header.addStretch(1)
        header.addWidget(exact)
        root.addLayout(header)

        self.rows = QVBoxLayout()
        self.rows.setSpacing(2)
        root.addLayout(self.rows)
        self.total = QLabel("")
        self.total.setObjectName("abilityBreakdownTotal")
        self.total.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(self.total)
        self.hide()

    def set_result(self, result: BenchmarkResult) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        steps = result.ability_breakdown
        self.setVisible(bool(steps) and result.engine_source == "fribbels")
        if not steps:
            self.total.clear()
            return
        total_damage = 0.0
        for index, step in enumerate(steps, 1):
            total_damage += step.damage
            row = QFrame()
            row.setObjectName("abilityDamageRow")
            row.setProperty("alternate", index % 2 == 0)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 5, 9, 5)
            row_layout.setSpacing(8)
            number = QLabel(str(index))
            number.setObjectName("abilityDamageNumber")
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon = QLabel(self.ACTION_ICONS.get(step.action_type, "•"))
            icon.setObjectName("abilityDamageIcon")
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name = QLabel(step.label)
            name.setObjectName("abilityDamageName")
            value = QLabel(self._format_damage(step.damage))
            value.setObjectName("abilityDamageValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            row_layout.addWidget(number)
            row_layout.addWidget(icon)
            row_layout.addWidget(name)
            row_layout.addStretch(1)
            row_layout.addWidget(value)
            self.rows.addWidget(row)
        self.total.setText(f"DANO TOTAL DA ROTAÇÃO   {self._format_damage(total_damage)}")

    @staticmethod
    def _format_damage(value: float) -> str:
        if abs(value) >= 1_000:
            return f"{value / 1_000:.1f}K".replace(".", ",")
        return f"{value:.0f}".replace(".", ",")


def combat_stat_visible(
    archetype: str,
    key: str,
    focus: tuple[str, ...] = (),
) -> bool:
    """Seleciona os atributos úteis para crítico, DoT e quebra."""
    if key in {"HP", "MaxHP", "DEF", "Defence", "Effect RES", "StatusResistance"}:
        return False
    crit_stats = {"CRIT Rate", "CriticalChance", "CRIT DMG", "CriticalDamage"}
    effect_hit_stats = {"Effect Hit Rate", "StatusProbability"}
    break_stats = {"Break Effect", "BreakDamageAddedRatio"}
    active_focus = set(focus)
    if not active_focus:
        active_focus = {
            "EFFECT_HIT" if archetype == "DOT"
            else "BREAK" if archetype == "QUEBRA"
            else "CRIT"
        }
    if key in crit_stats:
        return "CRIT" in active_focus
    if key in effect_hit_stats:
        return "EFFECT_HIT" in active_focus
    if key in break_stats:
        return "BREAK" in active_focus
    return True


class TeamCard(QFrame):
    custom_requested = Signal()
    edit_requested = Signal()
    default_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("teamCard")
        self.setMaximumHeight(170)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 10)
        layout.setSpacing(6)

        self.title = QLabel("TIME PADRÃO")
        self.title.setObjectName("benchmarkTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        modes = QHBoxLayout()
        modes.setSpacing(4)
        self.default_mode = QPushButton("Padrão")
        self.custom_mode = QPushButton("Customizado")
        for button in (self.default_mode, self.custom_mode):
            button.setObjectName("teamModeButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            modes.addWidget(button)
        self.default_mode.clicked.connect(
            lambda _checked=False: self.default_requested.emit()
        )
        self.custom_mode.clicked.connect(
            lambda _checked=False: self.custom_requested.emit()
        )
        layout.addLayout(modes)

        members = QHBoxLayout()
        members.setSpacing(5)
        self.member_visuals: list[
            tuple[QWidget, AvatarLabel, QLabel, AvatarLabel, QLabel]
        ] = []
        self._edit_targets: list[QWidget] = []
        for _ in range(3):
            # O pai explícito impede que o Qt trate o membro como uma pequena
            # janela independente durante as atualizações assíncronas.
            member = QWidget(self)
            member.setObjectName("teamMemberClickable")
            member.setCursor(Qt.CursorShape.PointingHandCursor)
            column = QVBoxLayout(member)
            column.setContentsMargins(2, 2, 2, 2)
            column.setSpacing(2)
            avatar = AvatarLabel(38)
            cone = AvatarLabel(24, rounded=False)
            eidolon = QLabel("E—")
            eidolon.setObjectName("teamBuildBadge")
            eidolon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            superimposition = QLabel("S—")
            superimposition.setObjectName("teamBuildBadge")
            superimposition.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignCenter)
            column.addWidget(eidolon, alignment=Qt.AlignmentFlag.AlignCenter)
            column.addWidget(cone, alignment=Qt.AlignmentFlag.AlignCenter)
            column.addWidget(superimposition, alignment=Qt.AlignmentFlag.AlignCenter)
            members.addWidget(member, 1)
            self.member_visuals.append(
                (member, avatar, eidolon, cone, superimposition)
            )
            for target in (member, avatar, eidolon, cone, superimposition):
                target.setCursor(Qt.CursorShape.PointingHandCursor)
                target.installEventFilter(self)
                self._edit_targets.append(target)
        layout.addLayout(members)
        self.set_mode(False)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        if (
            watched in self._edit_targets
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.edit_requested.emit()
            return True
        return super().eventFilter(watched, event)

    def set_mode(self, custom: bool) -> None:
        self.default_mode.setChecked(not custom)
        self.custom_mode.setChecked(custom)

    def set_result(self, result: BenchmarkResult) -> None:
        self.title.setText(
            "TIME CUSTOMIZADO"
            if "customizado" in result.team_name.casefold()
            else ("TIME PADRÃO" if result.team_members else "SEM TIME PADRÃO")
        )
        self.title.setToolTip(result.team_name)
        for index, (member, avatar, eidolon, cone, superimposition) in enumerate(
            self.member_visuals
        ):
            has_member = index < len(result.team_members)
            member.setVisible(has_member)
            if has_member:
                tooltip = (
                    f"{result.team_members[index]}\n{result.team_details[index]}"
                    "\n\nClique para editar o time customizado."
                )
                for target in (member, avatar, eidolon, cone, superimposition):
                    target.setToolTip(tooltip)
                detail = result.team_details[index]
                eidolon.setText(detail.split(" · ", 1)[0])
                cone_detail = detail.splitlines()[0]
                superimposition.setText(
                    cone_detail.rsplit(" ", 1)[-1]
                    if " " in cone_detail else "S—"
                )
                avatar.clear_image()
                cone.clear_image()
                if index < len(result.team_character_ids):
                    avatar.set_image(QPixmap(str(
                        FRIBBELS_ASSETS / "icon" / "avatar"
                        / f"{result.team_character_ids[index]}.webp"
                    )))
                if index < len(result.team_light_cone_ids):
                    cone.set_image(QPixmap(str(
                        FRIBBELS_ASSETS / "icon" / "light_cone"
                        / f"{result.team_light_cone_ids[index]}.webp"
                    )))


class BenchmarkScale(QWidget):
    """Régua visual de 0–200% inspirada no benchmark do Fribbels."""

    TIERS = (
        (40, "F"), (45, "F+"), (50, "D"), (55, "D+"),
        (60, "C"), (65, "C+"), (70, "B"), (75, "B+"),
        (80, "A"), (85, "A+"), (90, "S"), (95, "S+"),
        (100, "SS"), (106, "SS+"), (113, "SSS"), (121, "SSS+"),
        (130, "WTF"), (140, "WTF+"), (150, "AEON"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("benchmarkScale")
        self.setMinimumHeight(150)
        self.setMaximumHeight(165)
        self.result: BenchmarkResult | None = None

    def set_result(self, result: BenchmarkResult) -> None:
        self.result = result
        self.update()

    @staticmethod
    def _compact_value(value: float) -> str:
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        if abs(value) >= 1_000:
            return f"{value / 1_000:.0f}K"
        return f"{value:.1f}"

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bounds = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        painter.setPen(QPen(QColor("#42466c"), 1))
        painter.setBrush(QColor("#171a35"))
        painter.drawRoundedRect(bounds, 9, 9)

        painter.setPen(QColor("#8fc2ff"))
        title_font = painter.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(
            QRectF(22, 10, self.width() - 44, 25),
            Qt.AlignmentFlag.AlignCenter,
            "DPS Benchmark Calculations",
        )

        margin = max(38, min(110, self.width() // 13))
        bar = QRectF(margin, 53, self.width() - margin * 2, 20)
        gradient = QLinearGradient(bar.left(), 0, bar.right(), 0)
        gradient.setColorAt(0.00, QColor("#ef655c"))
        gradient.setColorAt(0.19, QColor("#f0c33f"))
        gradient.setColorAt(0.33, QColor("#d9ec42"))
        gradient.setColorAt(0.52, QColor("#69dc45"))
        gradient.setColorAt(0.68, QColor("#17c77b"))
        gradient.setColorAt(0.75, QColor("#20bfc3"))
        gradient.setColorAt(0.82, QColor("#244360"))
        gradient.setColorAt(1.00, QColor("#2f2858"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRect(bar)

        small_font = painter.font()
        small_font.setPointSize(7)
        small_font.setBold(False)
        painter.setFont(small_font)
        if self.result is not None:
            damage_labels = (
                (bar.left(), self.result.baseline_value, Qt.AlignmentFlag.AlignLeft),
                (bar.center().x(), self.result.benchmark_value, Qt.AlignmentFlag.AlignCenter),
                (bar.right(), self.result.perfection_value, Qt.AlignmentFlag.AlignRight),
            )
            for x, value, alignment in damage_labels:
                painter.setPen(QColor("#aab3c7"))
                painter.drawText(
                    QRectF(x - 55, 34, 110, 16),
                    alignment,
                    f"{self._compact_value(value)} DANO",
                )
        for index, (score, grade) in enumerate(self.TIERS):
            x = bar.left() + bar.width() * score / 200.0
            painter.setPen(QPen(QColor(26, 35, 61, 145), 1))
            painter.drawLine(round(x), round(bar.top()), round(x), round(bar.bottom()))
            painter.setPen(QColor("#aab3c7"))
            y = 78 if index % 2 == 0 else 111
            painter.drawText(
                QRectF(x - 24, y, 48, 14),
                Qt.AlignmentFlag.AlignCenter,
                grade,
            )
            painter.drawText(
                QRectF(x - 24, y + 14, 48, 13),
                Qt.AlignmentFlag.AlignCenter,
                f"{score}%",
            )

        painter.setPen(QColor("#8994aa"))
        painter.drawText(QRectF(bar.left() - 18, 78, 36, 14), Qt.AlignmentFlag.AlignCenter, "0%")
        painter.drawText(QRectF(bar.right() - 24, 78, 48, 14), Qt.AlignmentFlag.AlignCenter, "200%")

        if self.result is not None:
            score = min(200.0, max(0.0, self.result.score))
            x = bar.left() + bar.width() * score / 200.0
            painter.setPen(QPen(QColor("#effcff"), 3))
            painter.drawLine(round(x), round(bar.top() - 4), round(x), round(bar.bottom() + 4))
        painter.end()


class UpgradeRow(QFrame):
    def __init__(self, comparison: UpgradeComparison) -> None:
        super().__init__()
        self.setObjectName("upgradeRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(7)

        name = QLabel(comparison.stat_name)
        name.setObjectName("rowName")
        roll = QLabel(comparison.roll_value)
        roll.setObjectName("rollValue")
        gain = QLabel(f"+{comparison.damage_gain_percent:.2f}%")
        gain.setObjectName("gainValue")
        projected = QLabel(f"{comparison.projected_score:.1f}%")
        projected.setObjectName("projectedValue")
        layout.addWidget(name, 1)
        layout.addWidget(roll)
        layout.addWidget(gain)
        layout.addWidget(projected)


class UpgradeComparisonTable(QFrame):
    def __init__(
        self,
        title_text: str = "COMPARAÇÃO DE MELHORIA DE SUBATRIBUTOS",
        first_header: str = "Melhoria do subatributo",
        show_part_icon: bool = False,
    ) -> None:
        super().__init__()
        self.show_part_icon = show_part_icon
        self.setObjectName("upgradeComparisonCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel(title_text)
        title.setObjectName("benchmarkSectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.table = QTableWidget(0, 5)
        self.table.setObjectName("upgradeComparisonTable")
        self.table.setHorizontalHeaderLabels((
            first_header,
            "Dano de combo Δ %",
            "Pontuação de DPS Δ %",
            "Dano de combo Δ",
            "Pontuação de DPS melhorada",
        ))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(34)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setMinimumHeight(42)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        self.set_comparisons([])

    @staticmethod
    def _number(value: float, decimals: int = 2) -> str:
        return f"{value:.{decimals}f}".replace(".", ",")

    def set_comparisons(self, comparisons: list[UpgradeComparison]) -> None:
        self.table.setRowCount(len(comparisons))
        for row, comparison in enumerate(comparisons):
            damage_arrow = "▲" if comparison.damage_gain_percent >= 0 else "▼"
            score_arrow = "▲" if comparison.score_gain_percent >= 0 else "▼"
            values = (
                "",
                f"{damage_arrow} {self._number(abs(comparison.damage_gain_percent))}%",
                f"{score_arrow} {self._number(abs(comparison.score_gain_percent))}%",
                self._number(comparison.damage_gain_value, 1),
                f"{self._number(comparison.projected_score, 1)}%",
            )
            for column, value in enumerate(values):
                if column == 0:
                    self.table.setCellWidget(row, column, self._comparison_label(comparison))
                    continue
                item = QTableWidgetItem(value)
                if column in (1, 2):
                    delta = (
                        comparison.damage_gain_percent
                        if column == 1 else comparison.score_gain_percent
                    )
                    item.setForeground(QColor("#82ec9d" if delta >= 0 else "#ff8092"))
                if column > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
        rows = max(1, len(comparisons))
        self.table.setFixedHeight(42 + rows * 34 + 2)

    @staticmethod
    def _icon_label(path: Path) -> QLabel:
        label = QLabel()
        label.setFixedSize(17, 17)
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            label.setPixmap(pixmap.scaled(
                16, 16,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        return label

    @staticmethod
    def _stat_icon_path(stat_key: str) -> Path:
        names = {
            "HP": "IconMaxHP.webp", "HP%": "IconMaxHP.webp",
            "HPDelta": "IconMaxHP.webp", "HPAddedRatio": "IconMaxHP.webp",
            "ATK": "IconAttack.webp", "ATK%": "IconAttack.webp",
            "AttackDelta": "IconAttack.webp", "AttackAddedRatio": "IconAttack.webp",
            "DEF": "IconDefence.webp", "DEF%": "IconDefence.webp",
            "DefenceDelta": "IconDefence.webp", "DefenceAddedRatio": "IconDefence.webp",
            "SPD": "IconSpeed.webp", "SPD%": "IconSpeed.webp",
            "SpeedDelta": "IconSpeed.webp",
            "CRIT Rate": "IconCriticalChance.webp",
            "CriticalChance": "IconCriticalChance.webp",
            "CRIT DMG": "IconCriticalDamage.webp",
            "CriticalDamage": "IconCriticalDamage.webp",
            "Effect Hit Rate": "IconStatusProbability.webp",
            "StatusProbability": "IconStatusProbability.webp",
            "Effect RES": "IconStatusResistance.webp",
            "StatusResistance": "IconStatusResistance.webp",
            "Break Effect": "IconBreakUp.webp",
            "BreakDamageAddedRatio": "IconBreakUp.webp",
            "Energy Regeneration Rate": "IconEnergyRecovery.webp",
            "Outgoing Healing Boost": "IconHealRatio.webp",
            "Physical DMG Boost": "IconPhysicalAddedRatio.webp",
            "Fire DMG Boost": "IconFireAddedRatio.webp",
            "Ice DMG Boost": "IconIceAddedRatio.webp",
            "Lightning DMG Boost": "IconThunderAddedRatio.webp",
            "Wind DMG Boost": "IconWindAddedRatio.webp",
            "Quantum DMG Boost": "IconQuantumAddedRatio.webp",
            "Imaginary DMG Boost": "IconImaginaryAddedRatio.webp",
        }
        return FRIBBELS_ASSETS / "icon" / "property" / names.get(stat_key, "")

    def _comparison_label(self, comparison: UpgradeComparison) -> QWidget:
        cell = QWidget()
        cell.setObjectName("comparisonCell")
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(7, 0, 4, 0)
        layout.setSpacing(5)
        if self.show_part_icon and comparison.part_key:
            part_icons = {
                "Body": "partBody.webp", "Feet": "partFeet.webp",
                "PlanarSphere": "partPlanarSphere.webp",
                "LinkRope": "partLinkRope.webp",
            }
            part_path = FRIBBELS_ASSETS / "misc" / part_icons.get(comparison.part_key, "")
            layout.addWidget(self._icon_label(part_path))
            arrow = QLabel("→")
            arrow.setObjectName("comparisonArrow")
            layout.addWidget(arrow)
        layout.addWidget(self._icon_label(self._stat_icon_path(comparison.stat_key)))
        text = QLabel(
            comparison.stat_name
            if self.show_part_icon else f"{comparison.roll_value} {comparison.stat_name}"
        )
        text.setObjectName("comparisonLabel")
        layout.addWidget(text)
        layout.addStretch(1)
        cell.setToolTip(
            f"{comparison.roll_value} {comparison.stat_name}" if self.show_part_icon else ""
        )
        return cell


class RelicCard(QFrame):
    def __init__(
        self,
        relic: RelicSummary,
        rating: RelicRating | None = None,
        *,
        holder_name: str = "",
        previous_holder_name: str = "",
        expand_vertical: bool = False,
    ) -> None:
        super().__init__()
        self.setObjectName("relicCard")
        has_history = previous_holder_name and previous_holder_name != holder_name
        card_height = (
            216 if holder_name and has_history else
            202 if holder_name or previous_holder_name else 176
        )
        self.setMinimumSize(205, card_height)
        if expand_vertical:
            # Na grade equipada, três linhas ocupam a coluna sem criar um
            # rodapé vazio, mas o limite evita cartões exageradamente altos.
            self.setMaximumHeight(max(card_height, 232))
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        else:
            self.setMaximumHeight(card_height)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(4)

        self.holder_icon: AvatarLabel | None = None
        visible_holder = holder_name or previous_holder_name
        if visible_holder:
            holder_row = QHBoxLayout()
            holder_row.setSpacing(6)
            self.holder_icon = AvatarLabel(27)
            holder_row.addWidget(self.holder_icon)
            holder_box = QVBoxLayout()
            holder_box.setSpacing(2)
            if holder_name:
                current_holder = QLabel(f"Equipado por {holder_name}")
                current_holder.setObjectName("relicHolderCurrent")
                current_holder.setToolTip(current_holder.text())
                holder_box.addWidget(current_holder)
            if has_history or not holder_name:
                previous_holder = QLabel(f"Anteriormente em {previous_holder_name}")
                previous_holder.setObjectName("relicHolderPrevious")
                previous_holder.setToolTip(previous_holder.text())
                holder_box.addWidget(previous_holder)
            holder_row.addLayout(holder_box, 1)
            layout.addLayout(holder_row)

        header = QHBoxLayout()
        self.icon = AvatarLabel(50, rounded=False)
        header.addWidget(self.icon)
        title = QVBoxLayout()
        slot = QLabel(relic.slot.upper())
        slot.setObjectName("relicSlot")
        set_name = QLabel(relic.set_name)
        set_name.setObjectName("relicSet")
        set_name.setWordWrap(True)
        stars = QLabel("★" * relic.rarity)
        stars.setObjectName("rarity")
        title.addWidget(slot)
        title.addWidget(set_name)
        title.addWidget(stars)
        header.addLayout(title, 1)
        level = QLabel(f"+{relic.level}")
        level.setObjectName("eidolonBadge")
        header.addWidget(level, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        main = QHBoxLayout()
        main_name = QLabel(relic.main_stat.name)
        main_name.setObjectName("rowName")
        main_value = QLabel(relic.main_stat.formatted_value)
        main_value.setObjectName("relicMainValue")
        main.addWidget(main_name)
        main.addStretch(1)
        main.addWidget(main_value)
        layout.addLayout(main)

        for stat in relic.sub_stats:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(3)
            name = QLabel(stat.name)
            name.setObjectName("relicSub")
            upgrades = QLabel("<" * stat.upgrades)
            upgrades.setObjectName("upgradeBadge")
            value = QLabel(stat.formatted_value)
            value.setObjectName("relicSubValue")
            row.addWidget(name)
            row.addStretch(1)
            row.addWidget(upgrades)
            row.addWidget(value)
            layout.addLayout(row)
            # Só altere a visibilidade depois que o QLabel já pertence ao
            # cartão. Antes disso, o Qt o trata como uma janela independente.
            upgrades.setVisible(stat.upgrades > 0)
        if rating is not None:
            if expand_vertical:
                layout.addStretch(1)
            score_band = QFrame()
            score_band.setObjectName("relicScoreBand")
            score_row = QHBoxLayout(score_band)
            score_row.setContentsMargins(7, 4, 5, 4)
            score_row.setSpacing(6)
            score_label = QLabel("Pontuação")
            score_label.setObjectName("relicScoreLabel")
            score_value = QLabel(f"{rating.score:.1f} ({rating.grade})")
            score_value.setObjectName("relicScoreValue")
            score_value.setProperty(
                "scoreTier", rating.grade.casefold().replace("+", "plus")
            )
            score_row.addWidget(score_label)
            score_row.addStretch(1)
            score_row.addWidget(score_value)
            layout.addWidget(score_band)


class StatCard(QFrame):
    STAT_SYMBOLS = {
        "MaxHP": "♥", "Attack": "⚔", "Defence": "◆", "Speed": "➤",
        "CriticalChance": "◎", "CriticalDamage": "✦",
        "BreakDamageAddedRatio": "◇", "StatusProbability": "⌁",
        "StatusResistance": "◈", "SPRatio": "↻",
    }

    def __init__(self, stat: CharacterStat) -> None:
        super().__init__()
        self.setObjectName("statCard")
        self.setMinimumHeight(76)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 11, 13, 11)
        layout.setSpacing(11)

        icon = QLabel(self.STAT_SYMBOLS.get(stat.key, "✧"))
        icon.setObjectName("statIcon")
        icon.setFixedSize(38, 38)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(1)
        name = QLabel(stat.name.upper())
        name.setObjectName("statName")
        value = QLabel(stat.formatted_value)
        value.setObjectName("statValue")
        text.addWidget(name)
        text.addWidget(value)
        layout.addLayout(text, 1)
