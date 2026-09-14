from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import platform
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from app.ui.motion import AnimatedDialog as QDialog
from app.ui.motion import AnimatedStack as QStackedWidget

from app.benchmark.fribbels_client import ENGINE_ROOT, ENGINE_SCRIPT, engine_available
from app.config import APP_VERSION
from app.paths import app_data_dir
from app.preferences import (
    ExperiencePreferences, ExperienceSettings, THEMES,
    apply_experience_preferences, themed_color,
)
from app.ui.widgets import FadeComboBox


@dataclass(frozen=True, slots=True)
class TourStep:
    title: str
    text: str
    anchor: Callable[[], QWidget | None]
    action: Callable[[], None] | None = None


class GuidedTourOverlay(QWidget):
    """Interactive coach-mark overlay anchored to real interface controls."""

    finished = Signal()

    def __init__(
        self, parent: QWidget, steps: tuple[TourStep, ...], *, first_run: bool = False
    ) -> None:
        super().__init__(parent)
        self.steps = steps
        self.first_run = first_run
        self.index = 0
        self.target_rect = QRect()
        self.setObjectName("guidedTourOverlay")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        parent.installEventFilter(self)

        self.balloon = QFrame(self)
        self.balloon.setObjectName("tourBalloon")
        self.balloon.setFixedWidth(400)
        layout = QVBoxLayout(self.balloon)
        layout.setContentsMargins(20, 17, 20, 17)
        layout.setSpacing(8)
        self.counter = QLabel()
        self.counter.setObjectName("tourCounter")
        self.title = QLabel()
        self.title.setObjectName("tourTitle")
        self.text = QLabel()
        self.text.setObjectName("tourText")
        self.text.setWordWrap(True)
        layout.addWidget(self.counter)
        layout.addWidget(self.title)
        layout.addWidget(self.text)
        actions = QHBoxLayout()
        actions.setSpacing(7)
        self.skip = QPushButton("Encerrar tutorial")
        self.skip.setObjectName("tourSkipButton")
        self.skip.clicked.connect(self.finish)
        self.back = QPushButton("Voltar")
        self.back.setObjectName("secondaryButton")
        self.back.clicked.connect(lambda: self.move_step(-1))
        self.next = QPushButton("Próximo")
        self.next.setObjectName("primaryButton")
        self.next.clicked.connect(lambda: self.move_step(1))
        actions.addWidget(self.skip)
        actions.addStretch(1)
        actions.addWidget(self.back)
        actions.addWidget(self.next)
        layout.addLayout(actions)

    def start(self) -> None:
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self._show_step()

    def move_step(self, offset: int) -> None:
        target = self.index + offset
        if target >= len(self.steps):
            self.finish()
            return
        self.index = max(0, target)
        self._show_step()

    def _show_step(self) -> None:
        step = self.steps[self.index]
        if step.action is not None:
            step.action()
        self.counter.setText(f"ETAPA {self.index + 1} DE {len(self.steps)}")
        self.title.setText(step.title)
        self.text.setText(step.text)
        self.back.setEnabled(self.index > 0)
        self.next.setText("Concluir" if self.index == len(self.steps) - 1 else "Próximo")
        self.balloon.adjustSize()
        QTimer.singleShot(0, self._position_balloon)

    def _position_balloon(self) -> None:
        if not self.isVisible() or not self.steps:
            return
        anchor = self.steps[self.index].anchor()
        if anchor is not None and anchor.isVisible() and anchor.width() > 0:
            # The overlay and most targets are siblings below the central widget.
            # Mapping through global coordinates keeps the spotlight aligned at
            # every window size, DPI scale and maximized state.
            top_left = self.mapFromGlobal(anchor.mapToGlobal(QPoint(0, 0)))
            target = QRect(top_left, anchor.size()).adjusted(-6, -6, 6, 6)
            self.target_rect = target.intersected(self.rect().adjusted(5, 5, -5, -5))
        else:
            self.target_rect = QRect()

        width = self.balloon.width()
        height = self.balloon.sizeHint().height()
        self.balloon.setFixedHeight(height)
        margin, gap = 18, 22
        if self.target_rect.isValid():
            target = self.target_rect
            candidates = (
                QPoint(target.right() + gap, target.center().y() - height // 2),
                QPoint(target.left() - width - gap, target.center().y() - height // 2),
                QPoint(target.center().x() - width // 2, target.bottom() + gap),
                QPoint(target.center().x() - width // 2, target.top() - height - gap),
            )
            normalized = tuple(
                QPoint(
                    max(margin, min(point.x(), self.width() - width - margin)),
                    max(margin, min(point.y(), self.height() - height - margin)),
                )
                for point in candidates
            )
            protected_target = target.adjusted(-8, -8, 8, 8)
            position = next(
                (
                    point for point in normalized
                    if not QRect(point.x(), point.y(), width, height).intersects(
                        protected_target
                    )
                ),
                normalized[0],
            )
        else:
            position = QPoint((self.width() - width) // 2, (self.height() - height) // 2)
        position.setX(max(margin, min(position.x(), self.width() - width - margin)))
        position.setY(max(margin, min(position.y(), self.height() - height - margin)))
        self.balloon.move(position)
        self.balloon.raise_()
        self.raise_()
        self.update()

    def _fits(self, point: QPoint, width: int, height: int, margin: int) -> bool:
        return (
            point.x() >= margin and point.y() >= margin
            and point.x() + width <= self.width() - margin
            and point.y() + height <= self.height() - margin
        )

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        shade = QPainterPath()
        shade.setFillRule(Qt.FillRule.OddEvenFill)
        shade.addRect(QRectF(self.rect()))
        if self.target_rect.isValid():
            shade.addRoundedRect(QRectF(self.target_rect), 11, 11)
        painter.fillPath(shade, QColor(2, 6, 14, 205))
        if self.target_rect.isValid():
            accent = QColor(themed_color("#6bdcff"))
            painter.setPen(QPen(accent, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.target_rect, 11, 11)
            start = self._edge_point(self.balloon.geometry(), self.target_rect.center())
            end = self._edge_point(self.target_rect, self.balloon.geometry().center())
            painter.drawLine(start, end)
            painter.setBrush(accent)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(end, 4, 4)
        painter.end()

    @staticmethod
    def _edge_point(rect: QRect, toward: QPoint) -> QPoint:
        center = rect.center()
        dx, dy = toward.x() - center.x(), toward.y() - center.y()
        if abs(dx) * rect.height() > abs(dy) * rect.width():
            return QPoint(rect.right() if dx > 0 else rect.left(), center.y())
        return QPoint(center.x(), rect.bottom() if dy > 0 else rect.top())

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
            QTimer.singleShot(0, self._position_balloon)
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.key() == Qt.Key.Key_Escape:
            self.finish()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Right):
            self.move_step(1)
        elif event.key() == Qt.Key.Key_Left:
            self.move_step(-1)
        else:
            super().keyPressEvent(event)

    def finish(self) -> None:
        if self.first_run:
            ExperienceSettings().complete_tutorial()
        self.parentWidget().removeEventFilter(self)
        self.hide()
        self.finished.emit()
        self.deleteLater()


class ExperienceDialog(QDialog):
    preferences_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = ExperienceSettings()
        self.replay_tutorial = False
        self.setObjectName("experienceDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(430)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        card = QFrame()
        card.setObjectName("authModal")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("EXPERIÊNCIA E ACESSIBILIDADE")
        title.setObjectName("brandTitle")
        close = QPushButton("×")
        close.setObjectName("dialogCloseButton")
        close.setFixedSize(34, 30)
        close.clicked.connect(self.reject)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)
        layout.addLayout(header)

        current = self.store.load()
        self.theme = FadeComboBox()
        for key, label in THEMES.items():
            self.theme.addItem(label, key)
        self.theme.setCurrentIndex(max(0, self.theme.findData(current.theme)))
        fields = QGridLayout()
        fields.setHorizontalSpacing(12)
        fields.addWidget(self._label("TEMA"), 0, 0)
        fields.addWidget(self.theme, 1, 0)
        layout.addLayout(fields)

        self.reduce_motion = QCheckBox(
            "Reduzir animações e efeitos de movimento"
        )
        self.reduce_motion.setObjectName("experienceCheckBox")
        self.reduce_motion.setChecked(current.reduce_motion)
        self.reduce_motion.setToolTip(
            "Diminui transições, pulsos e efeitos animados em computadores mais fracos."
        )
        layout.addWidget(self.reduce_motion)
        hint = QLabel(
            "A alteração de tema é aplicada imediatamente em todo o aplicativo."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        tutorial = QPushButton("Rever tutorial interativo")
        tutorial.setObjectName("secondaryButton")
        tutorial.clicked.connect(self._request_tutorial)
        save = QPushButton("Aplicar preferências")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save)
        layout.addWidget(tutorial)
        layout.addWidget(save)
        outer.addWidget(card)

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("metricTitle")
        return label

    def _preferences(self) -> ExperiencePreferences:
        return ExperiencePreferences(
            theme=str(self.theme.currentData()),
            reduce_motion=self.reduce_motion.isChecked(),
            tutorial_completed=self.store.load().tutorial_completed,
        )

    def _save(self) -> None:
        preferences = self._preferences()
        self.store.save(preferences)
        apply_experience_preferences(preferences=preferences)
        self.preferences_changed.emit()
        self.accept()

    def _request_tutorial(self) -> None:
        self.replay_tutorial = True
        self.accept()


class TutorialDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, *, first_run: bool = False) -> None:
        super().__init__(parent)
        self.first_run = first_run
        self.store = ExperienceSettings()
        self.setObjectName("tutorialDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedSize(590, 430)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        card = QFrame()
        card.setObjectName("tutorialCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 28, 34, 26)
        layout.setSpacing(16)
        eyebrow = QLabel("PRIMEIROS PASSOS · ASTRAL OPTIMIZER")
        eyebrow.setObjectName("homeEyebrow")
        layout.addWidget(eyebrow)
        self.pages = QStackedWidget()
        for icon, title, text in (
            ("✦", "Bem-vindo a bordo", "O Astral reúne builds, benchmarks, relíquias, Saltos e planejamento em um único aplicativo local."),
            ("1", "Configure sua conta", "Entre ou crie um perfil e salve sua UID principal na engrenagem. Sua conta será sincronizada ao abrir o aplicativo."),
            ("2", "Explore pela barra lateral", "Início pesquisa qualquer UID. Conta mostra seu painel. Builds analisa personagens; Saltos e Planejador acompanham seus recursos."),
            ("3", "Privacidade e segurança", "Nas Configurações você pode ocultar a UID das imagens e salvar backups em uma pasta sincronizada pelo OneDrive."),
            ("⌨", "Use o teclado", "Ctrl+K pesquisa UID · Ctrl+1 a Ctrl+7 navegam · Ctrl+B recolhe a barra · Ctrl+, abre Configurações · F1 revê este tutorial."),
        ):
            self.pages.addWidget(self._page(icon, title, text))
        layout.addWidget(self.pages, 1)
        self.steps = QLabel()
        self.steps.setObjectName("tutorialSteps")
        self.steps.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.steps)
        actions = QHBoxLayout()
        self.skip = QPushButton("Pular tutorial")
        self.skip.setObjectName("subtleButton")
        self.skip.clicked.connect(self._finish)
        self.back = QPushButton("Voltar")
        self.back.setObjectName("secondaryButton")
        self.back.clicked.connect(lambda: self._move(-1))
        self.next = QPushButton("Continuar")
        self.next.setObjectName("primaryButton")
        self.next.clicked.connect(lambda: self._move(1))
        actions.addWidget(self.skip)
        actions.addStretch(1)
        actions.addWidget(self.back)
        actions.addWidget(self.next)
        layout.addLayout(actions)
        outer.addWidget(card)
        self._sync()

    @staticmethod
    def _page(icon: str, title: str, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(10)
        symbol = QLabel(icon)
        symbol.setObjectName("tutorialIcon")
        symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading = QLabel(title)
        heading.setObjectName("tutorialTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail = QLabel(text)
        detail.setObjectName("tutorialText")
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setWordWrap(True)
        layout.addStretch(1)
        layout.addWidget(symbol)
        layout.addWidget(heading)
        layout.addWidget(detail)
        layout.addStretch(1)
        return page

    def _move(self, offset: int) -> None:
        target = self.pages.currentIndex() + offset
        if target >= self.pages.count():
            self._finish()
            return
        self.pages.setCurrentIndex(max(0, target))
        self._sync()

    def _sync(self) -> None:
        index = self.pages.currentIndex()
        self.back.setEnabled(index > 0)
        self.next.setText("Começar" if index == self.pages.count() - 1 else "Continuar")
        self.steps.setText("  ".join(
            "●" if step == index else "○" for step in range(self.pages.count())
        ))

    def _finish(self) -> None:
        if self.first_run:
            self.store.complete_tutorial()
        self.accept()


class DiagnosticsPanel(QWidget):
    def __init__(self, paths: dict[str, Path], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.paths = paths
        self.setObjectName("diagnosticsPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)
        title = QLabel("DIAGNÓSTICO")
        title.setObjectName("brandTitle")
        subtitle = QLabel(
            "Informações técnicas para verificar a instalação ou pedir suporte."
        )
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.summary = QLabel()
        self.summary.setObjectName("diagnosticsSummary")
        self.summary.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary, 1)
        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar diagnóstico")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self.refresh)
        self.copy_button = QPushButton("Copiar detalhes")
        self.copy_button.setObjectName("primaryButton")
        self.copy_button.clicked.connect(self.copy_details)
        actions.addStretch(1)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.copy_button)
        layout.addLayout(actions)
        self.details = ""
        self.refresh()

    def refresh(self) -> None:
        node = shutil.which("node") or "Não encontrado no PATH"
        engine = "Disponível" if engine_available() else "Indisponível"
        path_lines = []
        for label, path in self.paths.items():
            state = "encontrado" if path.exists() else "ainda não criado"
            path_lines.append(f"{label}: {path} [{state}]")
        self.details = "\n".join((
            f"Astral Optimizer: {APP_VERSION}",
            f"Sistema: {platform.platform()}",
            f"Python: {platform.python_version()}",
            f"Qt/PySide: {self._qt_version()}",
            "",
            f"Motor Fribbels: {engine}",
            f"Script do motor: {ENGINE_SCRIPT}",
            f"Diretório do motor: {ENGINE_ROOT}",
            f"Node.js: {node}",
            "",
            f"Dados do aplicativo: {app_data_dir()}",
            *path_lines,
        ))
        self.summary.setText(self.details)

    @staticmethod
    def _qt_version() -> str:
        try:
            from PySide6 import __version__ as pyside_version
            return str(pyside_version)
        except ImportError:
            return "desconhecida"

    def copy_details(self) -> None:
        QApplication.clipboard().setText(self.details)


def copy_error_details(message: str, context: str = "Interface") -> None:
    details = "\n".join((
        f"Astral Optimizer {APP_VERSION}",
        f"Contexto: {context}",
        f"Erro: {message}",
        f"Sistema: {platform.platform()}",
        f"Python: {sys.version.split()[0]}",
    ))
    QApplication.clipboard().setText(details)
