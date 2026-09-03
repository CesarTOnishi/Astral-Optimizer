from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.auth import AuthService, AuthUser, FriendProfile
from app.ui.image_loader import ImageLoader
from app.ui.widgets import AvatarLabel


class FriendsPanel(QWidget):
    open_uid = Signal(str)

    def __init__(
        self,
        auth_service: AuthService,
        image_loader: ImageLoader,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.auth_service = auth_service
        self.image_loader = image_loader
        self.user: AuthUser | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("friendsPage")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 18)
        outer.setSpacing(12)

        heading = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel("AMIGOS")
        title.setObjectName("brandTitle")
        self.subtitle = QLabel("Perfis salvos para você consultar rapidamente.")
        self.subtitle.setObjectName("muted")
        text.addWidget(title)
        text.addWidget(self.subtitle)
        heading.addLayout(text)
        heading.addStretch(1)
        self.count = QLabel("0 AMIGOS")
        self.count.setObjectName("friendsCount")
        heading.addWidget(self.count, alignment=Qt.AlignmentFlag.AlignVCenter)
        outer.addLayout(heading)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("friendsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.content.setObjectName("friendsContent")
        self.cards = QVBoxLayout(self.content)
        self.cards.setContentsMargins(0, 2, 0, 2)
        self.cards.setSpacing(9)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll, 1)

    def set_user(self, user: AuthUser | None) -> None:
        self.user = user
        self.refresh()

    def refresh(self) -> None:
        while self.cards.count():
            item = self.cards.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if self.user is None:
            self.count.setText("0 AMIGOS")
            self.subtitle.setText("Entre em uma conta para acessar sua lista de amigos.")
            self.cards.addWidget(
                self._empty_card(
                    "ENTRE PARA VER SEUS AMIGOS",
                    "Sua lista fica separada por conta do Astral Optimizer.",
                )
            )
            self.cards.addStretch(1)
            return

        friends = self.auth_service.friends()
        total = len(friends)
        self.count.setText(f"{total} AMIGO" if total == 1 else f"{total} AMIGOS")
        self.subtitle.setText("Selecione um perfil para consultar personagens e builds.")
        if not friends:
            self.cards.addWidget(
                self._empty_card(
                    "NENHUM AMIGO ADICIONADO",
                    "Pesquise outra UID em Builds e use o botão Adicionar amigo.",
                )
            )
        else:
            for friend in friends:
                self.cards.addWidget(self._friend_card(friend))
        self.cards.addStretch(1)

    def _friend_card(self, friend: FriendProfile) -> QFrame:
        card = QFrame()
        card.setObjectName("friendCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        avatar = AvatarLabel(56)
        avatar.setText(friend.nickname[:1].upper() if friend.nickname else "✦")
        if friend.profile_icon_url:
            self.image_loader.load(friend.profile_icon_url, avatar.set_image)
        layout.addWidget(avatar)

        information = QVBoxLayout()
        information.setSpacing(3)
        name = QLabel(friend.nickname)
        name.setObjectName("friendName")
        uid = QLabel(f"UID {friend.uid}")
        uid.setObjectName("profileUid")
        details = QLabel(
            f"Nível {friend.level}  ·  Equilíbrio {friend.world_level}"
        )
        details.setObjectName("muted")
        information.addWidget(name)
        information.addWidget(uid)
        information.addWidget(details)
        layout.addLayout(information, 1)

        view = QPushButton("Ver perfil")
        view.setObjectName("friendViewButton")
        view.setCursor(Qt.CursorShape.PointingHandCursor)
        view.clicked.connect(
            lambda _checked=False, uid_value=friend.uid: self.open_uid.emit(uid_value)
        )
        remove = QPushButton("×")
        remove.setObjectName("friendRemoveButton")
        remove.setFixedSize(34, 34)
        remove.setToolTip(f"Remover {friend.nickname} dos amigos")
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.clicked.connect(
            lambda _checked=False, uid_value=friend.uid: self._remove(uid_value)
        )
        layout.addWidget(view)
        layout.addWidget(remove)
        return card

    @staticmethod
    def _empty_card(title_text: str, detail_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("friendsEmptyCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 42, 24, 42)
        icon = QLabel("♧")
        icon.setObjectName("friendsEmptyIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel(title_text)
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail = QLabel(detail_text)
        detail.setObjectName("muted")
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setWordWrap(True)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(detail)
        return card

    def _remove(self, uid: str) -> None:
        self.auth_service.remove_friend(uid)
        self.refresh()
