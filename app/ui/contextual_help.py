from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import StrokeIcon, set_button_icon


PITY_HELP = (
    "Como o pity é calculado",
    "O contador começa depois do último item 5★ da mesma categoria de banner. "
    "Cada tiro seguinte soma 1. Banners de personagem, Cone de Luz, permanente e "
    "colaboração mantêm contadores separados. Se o início do histórico não foi "
    "importado, o valor representa apenas os registros disponíveis.",
)

GUARANTEE_HELP = (
    "Por que a garantia pode ser desconhecida",
    "A garantia depende do resultado 5★ anterior. Ela fica desconhecida quando o "
    "app possui apenas um resumo, nenhum 5★ individual ou um histórico que começa "
    "depois desse resultado. Importe um histórico mais completo para identificá-la.",
)

RATE_UP_HELP = (
    "50/50 e 75/25",
    "No banner de personagem, um 5★ em disputa tem 50% de chance de ser o "
    "promocional. No banner de Cone de Luz, a chance é 75%. Ao perder a disputa, "
    "o próximo 5★ promocional da mesma categoria fica garantido.",
)

RELIC_GRADE_HELP = (
    "Classificação das relíquias",
    "A pontuação considera o atributo principal, os subatributos úteis e seus "
    "upgrades para o personagem analisado. Faixas: F/F+ de 0 a 9,9; D/D+ de 10 a "
    "19,9; C/C+ de 20 a 29,9; B/B+ de 30 a 39,9; A/A+ de 40 a 49,9; S/S+ de 50 "
    "a 59,9; SS/SS+ de 60 a 69,9; SSS/SSS+ de 70 a 79,9; WTF/WTF+ de 80 a "
    "89,9; e AEON a partir de 90. A mesma peça pode receber outra nota em outro "
    "personagem porque as prioridades de atributos mudam.",
)

BENCHMARK_HELP = (
    "Como o DPS Benchmark é calculado",
    "O app envia a build e o time selecionado ao motor adaptado do Fribbels, que "
    "simula rotações em níveis de investimento de referência. A pontuação compara "
    "o dano da sua build com o benchmark de 100%; ela não é uma previsão exata de "
    "todo combate e pode variar conforme inimigo, buffs e rotação.",
)

BANNER_EDITION_HELP = (
    "Por que uma edição pode não aparecer",
    "A separação por edição depende do identificador de banner presente em cada "
    "registro. Históricos antigos, resumos de XLSX ou arquivos incompletos podem não "
    "trazer esse identificador. Esses tiros continuam no total da categoria, mas "
    "podem aparecer como banner não identificado.",
)

BUILD_SOURCE_HELP = (
    "Build pública e build da conta principal",
    "A build pública é o personagem atualmente colocado no Showcase da UID "
    "pesquisada. A build da conta principal usa a UID salva no seu perfil local, "
    "alimenta Conta e o inventário de relíquias e pode ser atualizada pelo botão "
    "Atualizar conta. O app não acessa personagens privados fora do Showcase.",
)


class ContextHelpButton(QPushButton):
    """Pequeno botão de informação que abre uma explicação contextual."""

    def __init__(
        self, title: str, explanation: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.help_title = title
        self.explanation = explanation
        self.setObjectName("contextHelpButton")
        self.setText("")
        set_button_icon(self, "info", 16)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(title)
        self.setAccessibleName(f"Ajuda: {title}")
        self._popup: ContextHelpPopup | None = None
        self.clicked.connect(self.open_help)

    def open_help(self) -> None:
        if self._popup is not None and self._popup.isVisible():
            self._popup.close()
            return
        popup = ContextHelpPopup(self.help_title, self.explanation, self)
        self._popup = popup
        popup.destroyed.connect(
            lambda _object=None, current=popup: self._clear_popup(current)
        )
        popup.adjustSize()
        popup.move(self._popup_position(popup))
        popup.show()
        popup.raise_()

    def _clear_popup(self, popup: "ContextHelpPopup") -> None:
        if self._popup is popup:
            self._popup = None

    def _popup_position(self, popup: "ContextHelpPopup") -> QPoint:
        origin = self.mapToGlobal(QPoint(0, 0))
        screen = QGuiApplication.screenAt(origin)
        if screen is None:
            return QPoint(origin.x() + self.width() + 8, origin.y())
        available = screen.availableGeometry()
        right_x = origin.x() + self.width() + 8
        left_x = origin.x() - popup.width() - 8
        target_x = right_x if right_x + popup.width() <= available.right() else left_x
        target_x = max(available.left() + 6, min(target_x, available.right() - popup.width() - 6))
        target_y = origin.y() - 8
        target_y = max(available.top() + 6, min(target_y, available.bottom() - popup.height() - 6))
        return QPoint(target_x, target_y)


class ContextHelpPopup(QFrame):
    """Popover compacto, sem o espaçamento extra aplicado por QMenu."""

    def __init__(
        self,
        title: str,
        explanation: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self.setObjectName("contextHelpPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        content = QWidget()
        content.setObjectName("contextHelpContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(17, 16, 17, 17)
        content_layout.setSpacing(12)

        header_frame = QFrame()
        header_frame.setObjectName("contextHelpHeader")
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(11)
        icon_plate = QFrame()
        icon_plate.setObjectName("contextHelpIconPlate")
        icon_plate.setFixedSize(36, 36)
        icon_layout = QVBoxLayout(icon_plate)
        icon_layout.setContentsMargins(8, 8, 8, 8)
        badge = QLabel()
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(QIcon(StrokeIcon("info")).pixmap(QSize(20, 20)))
        icon_layout.addWidget(badge)

        heading_box = QVBoxLayout()
        heading_box.setContentsMargins(0, 0, 0, 0)
        heading_box.setSpacing(0)
        eyebrow = QLabel("AJUDA CONTEXTUAL")
        eyebrow.setObjectName("contextHelpEyebrow")
        heading = QLabel(title)
        heading.setObjectName("contextHelpTitle")
        heading.setWordWrap(True)
        heading_box.addWidget(eyebrow)
        heading_box.addWidget(heading)
        header.addWidget(icon_plate, alignment=Qt.AlignmentFlag.AlignVCenter)
        header.addLayout(heading_box, 1)

        close = QPushButton()
        close.setObjectName("contextHelpClose")
        close.setText("")
        close.setToolTip("Fechar ajuda")
        close.setFixedSize(26, 26)
        set_button_icon(close, "close", 13)
        close.clicked.connect(self.close)
        header.addWidget(close, alignment=Qt.AlignmentFlag.AlignVCenter)

        body = QFrame()
        body.setObjectName("contextHelpBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(13, 11, 13, 12)

        text = QLabel(explanation)
        text.setObjectName("contextHelpText")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text.setFixedWidth(360)
        body_layout.addWidget(text)

        content_layout.addWidget(header_frame)
        content_layout.addWidget(body)
        layout.addWidget(content)

        self.ensurePolished()
        text.adjustSize()
        text.setFixedHeight(text.sizeHint().height())
        layout.activate()
        self.setFixedHeight(layout.sizeHint().height())
