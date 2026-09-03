from __future__ import annotations

from collections.abc import Callable
import json
import unicodedata

from PySide6.QtCore import QSettings, QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSizeGrip,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.api.enka_client import EnkaClient
from app.auth import AuthService
from app.benchmark import BenchmarkEngine
from app.benchmark.fribbels_client import FribbelsBenchmarkWorker, engine_available
from app.benchmark.teams import default_team
from app.cloud import GoogleDriveService, GoogleDriveWorker
from app.config import (
    APP_HOME_BACKGROUND,
    APP_ICON_ICO,
    APP_ICON_PNG,
    APP_STYLESHEET,
)
from app.models import AccountSummary, CharacterStat, CharacterSummary
from app.relics import RelicDatabase
from app.ui.auth_dialogs import AuthDialog, SettingsDialog
from app.ui.catalog_panel import CatalogPanel
from app.ui.friends_panel import FriendsPanel
from app.ui.home_panel import HomePanel
from app.ui.image_loader import ImageLoader
from app.ui.loading import LoadingOverlay, load_icon_pixmap
from app.ui.planner_panel import PlannerPanel
from app.ui.rank_dialog import RankRedirectDialog
from app.ui.team_dialog import CustomTeamDialog
from app.ui.relic_inventory_panel import RelicInventoryPanel
from app.ui.warp_panel import WarpPanel
from app.ui.widgets import (
    AbilityBreakdownCard,
    AvatarLabel,
    BenchmarkCard,
    BenchmarkScale,
    CombatStatsCard,
    CharacterPortraitCard,
    LightConeBanner,
    RelicCard,
    ResponsiveImageLabel,
    StatRow,
    TeamCard,
    UpgradeComparisonTable,
    FRIBBELS_ASSETS,
)


PRIMARY_STATS = (
    "MaxHP",
    "Attack",
    "Defence",
    "Speed",
    "CriticalChance",
    "CriticalDamage",
    "StatusProbability",
    "StatusResistance",
    "BreakDamageAddedRatio",
    "SPRatio",
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


class AppTitleBar(QFrame):
    def __init__(self, window: "MainWindow") -> None:
        super().__init__()
        self.app_window = window
        self.setObjectName("customTitleBar")
        self.setFixedHeight(42)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 6, 0)
        layout.setSpacing(8)

        mark = QLabel()
        mark.setObjectName("titleBarMark")
        mark.setPixmap(load_icon_pixmap(APP_ICON_PNG, 28))
        mark.setFixedSize(28, 28)
        title = QLabel("ASTRAL OPTIMIZER")
        title.setObjectName("titleBarTitle")
        subtitle = QLabel("Builds · Catálogo · Benchmark · Saltos")
        subtitle.setObjectName("titleBarSubtitle")
        layout.addWidget(mark)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)

        self.minimize_button = QPushButton("—")
        self.maximize_button = QPushButton("□")
        self.close_button = QPushButton("×")
        for button, tooltip in (
            (self.minimize_button, "Minimizar"),
            (self.maximize_button, "Maximizar"),
            (self.close_button, "Fechar"),
        ):
            button.setObjectName("windowButton")
            button.setFixedSize(42, 30)
            button.setToolTip(tooltip)
            layout.addWidget(button)
        self.close_button.setObjectName("closeWindowButton")
        self.minimize_button.clicked.connect(window.showMinimized)
        self.maximize_button.clicked.connect(self.toggle_maximize)
        self.close_button.clicked.connect(window.close)

    def toggle_maximize(self) -> None:
        if self.app_window.isMaximized():
            self.app_window.showNormal()
        else:
            self.app_window.showMaximized()
        self.sync_state()

    def sync_state(self) -> None:
        maximized = self.app_window.isMaximized()
        self.maximize_button.setText("❐" if maximized else "□")
        self.maximize_button.setToolTip("Restaurar" if maximized else "Maximizar")

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.app_window.windowHandle()
            if handle is not None:
                handle.startSystemMove()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("Astral Optimizer")
        icon_path = APP_ICON_ICO if APP_ICON_ICO.is_file() else APP_ICON_PNG
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1280, 800)
        self.setMinimumSize(900, 620)

        self.enka_client = EnkaClient(self)
        self.auth_service = AuthService()
        self.benchmark_engine = BenchmarkEngine()
        self.image_loader = ImageLoader(self)
        self.relic_database = RelicDatabase()
        self.current_characters: list[CharacterSummary] = []
        self.current_character_id = ""
        self.current_uid = ""
        self.current_account: AccountSummary | None = None
        self.build_source: str | None = None
        self.own_account: AccountSummary | None = None
        self.own_account_user_id: int | None = None
        self.pending_account_target = "builds"
        self.sidebar_expanded = True
        self.benchmark_workers: set[FribbelsBenchmarkWorker] = set()
        self.drive_workers: set[GoogleDriveWorker] = set()
        self.benchmark_results = {}
        self.fribbels_cache: dict[str, dict[str, object]] = {}
        self.active_benchmark_ids: set[str] = set()
        self.unsupported_benchmark_characters: set[str] = set()
        self.team_settings = QSettings("Astral Optimizer", "Custom Teams")
        self.current_relic_cards: list[RelicCard] = []
        self._detail_request = 0

        self._build_ui()
        self.setStyleSheet(APP_STYLESHEET)
        self.enka_client.loading_changed.connect(self._set_loading)
        self.enka_client.request_failed.connect(self._request_failed)
        self.enka_client.account_loaded.connect(self._account_loaded)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.title_bar = AppTitleBar(self)
        root_layout.addWidget(self.title_bar)

        body = QWidget()
        body.setObjectName("appBody")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(12, 10, 12, 12)
        body_layout.setSpacing(10)
        body_layout.addWidget(self._build_sidebar())

        self.page_stack = QStackedWidget()

        content = QWidget()
        content.setObjectName("appRoot")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 3, 6, 0)
        layout.setSpacing(10)
        layout.addLayout(self._build_header())

        self.status_label = QLabel("Digite seu UID para carregar as builds públicas.")
        self.status_label.setObjectName("statusInfo")
        layout.addWidget(self.status_label)
        self.build_empty_panel = self._build_build_empty_panel()
        layout.addWidget(self.build_empty_panel, 1)

        self.build_scroll = QScrollArea()
        self.build_scroll.setObjectName("buildScroll")
        self.build_scroll.setWidgetResizable(True)
        self.build_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        build_content = QWidget()
        build_content.setObjectName("buildScrollContent")
        build_layout = QVBoxLayout(build_content)
        build_layout.setContentsMargins(0, 0, 4, 12)
        build_layout.setSpacing(10)
        self.selector_panel = self._build_selector()
        build_layout.addWidget(self.selector_panel)

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.art_panel = self._build_art_panel()
        self.stats_panel = self._build_stats_panel()
        self.relics_panel = self._build_relics_panel()
        for panel in (self.art_panel, self.stats_panel, self.relics_panel):
            panel.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
        self.content_splitter.addWidget(self.art_panel)
        self.content_splitter.addWidget(self.stats_panel)
        self.content_splitter.addWidget(self.relics_panel)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.setHandleWidth(6)
        self.content_splitter.setSizes([300, 240, 460])
        self.content_splitter.setStretchFactor(0, 3)
        self.content_splitter.setStretchFactor(1, 2)
        self.content_splitter.setStretchFactor(2, 5)
        self.content_splitter.splitterMoved.connect(
            lambda _position, _index: self._reflow_relic_cards()
        )
        self.content_splitter.setMinimumHeight(790)
        build_layout.addWidget(self.content_splitter)
        build_layout.addWidget(self._build_benchmark_section())
        self.build_scroll.setWidget(build_content)
        layout.addWidget(self.build_scroll, 1)
        self.page_stack.addWidget(content)
        self.warp_panel = WarpPanel()
        self.warp_panel.set_user(self.auth_service.current_user)
        self.warp_panel.import_completed.connect(self._backup_warps_to_drive)
        self.page_stack.addWidget(self.warp_panel)
        self.planner_panel = PlannerPanel(self.warp_panel.database)
        self.planner_panel.set_user(self.auth_service.current_user)
        self.warp_panel.import_completed.connect(
            lambda _owner_id: self.planner_panel.refresh()
        )
        self.page_stack.addWidget(self.planner_panel)
        self.relic_inventory_panel = RelicInventoryPanel(
            self.relic_database, self.image_loader
        )
        self.relic_inventory_panel.set_user(self.auth_service.current_user)
        self.page_stack.addWidget(self.relic_inventory_panel)
        self.account_page = self._build_account_page()
        self.page_stack.addWidget(self.account_page)
        self.friends_panel = FriendsPanel(self.auth_service, self.image_loader)
        self.friends_panel.set_user(self.auth_service.current_user)
        self.friends_panel.open_uid.connect(self._open_friend_profile)
        self.page_stack.addWidget(self.friends_panel)
        self.home_panel = HomePanel(APP_HOME_BACKGROUND)
        self.home_panel.search_requested.connect(self.search_uid)
        self.uid_input = self.home_panel.uid_input
        self.search_button = self.home_panel.search_button
        self.page_stack.addWidget(self.home_panel)
        self.catalog_panel = CatalogPanel(self.image_loader)
        self.page_stack.addWidget(self.catalog_panel)
        self._refresh_account_page()
        self._navigate("Início")
        body_layout.addWidget(self.page_stack, 1)
        root_layout.addWidget(body, 1)
        self.size_grip = QSizeGrip(root)
        self.size_grip.setObjectName("windowSizeGrip")
        self.size_grip.setFixedSize(18, 18)
        self.size_grip.raise_()
        self.loading_overlay = LoadingOverlay(root, APP_ICON_PNG)
        self.loading_overlay.setGeometry(root.rect())
        self.loading_overlay.raise_()
        self.warp_panel.busy_changed.connect(self._warp_busy_changed)

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

    def _build_account_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("accountPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(12)

        title = QLabel("CONTA")
        title.setObjectName("brandTitle")
        subtitle = QLabel(
            "Sua UID principal é consultada quando você abre esta opção."
        )
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("accountProfilePanel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(8)
        self.account_profile_avatar = QLabel("✦")
        self.account_profile_avatar.setObjectName("accountProfileAvatar")
        self.account_profile_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_profile_avatar.setFixedSize(78, 78)
        self.account_profile_name = QLabel("Conta não carregada")
        self.account_profile_name.setObjectName("detailName")
        self.account_profile_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_profile_uid = QLabel("—")
        self.account_profile_uid.setObjectName("profileUid")
        self.account_profile_uid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_profile_meta = QLabel(
            "Entre no perfil e defina uma UID principal nas configurações."
        )
        self.account_profile_meta.setObjectName("muted")
        self.account_profile_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_profile_meta.setWordWrap(True)
        self.account_profile_signature = QLabel("")
        self.account_profile_signature.setObjectName("profileSignature")
        self.account_profile_signature.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_profile_signature.setWordWrap(True)
        self.account_load_button = QPushButton("Atualizar conta")
        self.account_load_button.setObjectName("primaryButton")
        self.account_load_button.clicked.connect(
            lambda: self._load_saved_uid(force=True)
        )
        self.account_status = QLabel("")
        self.account_status.setObjectName("statusInfo")
        self.account_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_status.setWordWrap(True)
        card_layout.addWidget(
            self.account_profile_avatar, alignment=Qt.AlignmentFlag.AlignCenter
        )
        card_layout.addWidget(self.account_profile_name)
        card_layout.addWidget(self.account_profile_uid)
        card_layout.addWidget(self.account_profile_meta)
        card_layout.addWidget(self.account_profile_signature)
        card_layout.addWidget(
            self.account_load_button, alignment=Qt.AlignmentFlag.AlignCenter
        )
        card_layout.addWidget(self.account_status)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _build_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        profile = QFrame()
        profile.setObjectName("buildProfileHeader")
        profile_layout = QHBoxLayout(profile)
        profile_layout.setContentsMargins(12, 9, 12, 9)
        profile_layout.setSpacing(11)

        self.profile_header_avatar = AvatarLabel(58)
        profile_layout.addWidget(self.profile_header_avatar)

        identity = QVBoxLayout()
        identity.setSpacing(1)
        self.account_label = QLabel("Nenhuma conta sincronizada")
        self.account_label.setObjectName("profileHeaderName")
        self.profile_header_bio = QLabel("Pesquise uma UID para visualizar o perfil.")
        self.profile_header_bio.setObjectName("profileHeaderBio")
        self.profile_header_bio.setWordWrap(True)
        self.profile_header_meta = QLabel("Nível — · Equilíbrio — · — conquistas")
        self.profile_header_meta.setObjectName("profileHeaderMeta")
        identity.addWidget(self.account_label)
        identity.addWidget(self.profile_header_bio)
        identity.addWidget(self.profile_header_meta)
        profile_layout.addLayout(identity, 1)

        self.copy_uid_button = QPushButton("⧉  Copiar UID")
        self.copy_uid_button.setObjectName("copyUidButton")
        self.copy_uid_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_uid_button.setEnabled(False)
        self.copy_uid_button.clicked.connect(self.copy_current_uid)
        self.header_refresh_button = QPushButton("↻  Atualizar conta")
        self.header_refresh_button.setObjectName("headerRefreshButton")
        self.header_refresh_button.setToolTip(
            "Buscar novamente sua UID e sincronizar personagens e relíquias"
        )
        self.header_refresh_button.clicked.connect(self.refresh_loaded_account)
        self.header_refresh_button.setVisible(False)
        self.add_friend_button = QPushButton("♡  Adicionar amigo")
        self.add_friend_button.setObjectName("addFriendButton")
        self.add_friend_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_friend_button.clicked.connect(self.add_current_friend)
        self.add_friend_button.setVisible(False)
        profile_layout.addWidget(self.copy_uid_button)
        layout.addWidget(profile, 1)
        layout.addWidget(self.add_friend_button)
        layout.addWidget(self.header_refresh_button)
        return layout

    def copy_current_uid(self) -> None:
        account = self.current_account
        if account is None:
            return
        QApplication.clipboard().setText(account.uid)
        self.copy_uid_button.setText("✓  UID copiada")
        QTimer.singleShot(1400, self._reset_copy_uid_button)

    def _reset_copy_uid_button(self) -> None:
        if self.current_account is not None:
            self.copy_uid_button.setText("⧉  Copiar UID")

    def _build_sidebar(self) -> QFrame:
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sideBar")
        self.sidebar.setFixedWidth(230)
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        self.sidebar_toggle = QPushButton("☰")
        self.sidebar_toggle.setObjectName("sidebarToggle")
        self.sidebar_toggle.setToolTip("Fechar barra lateral")
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.sidebar_toggle)

        self.side_brand = QLabel("ASTRAL OPTIMIZER")
        self.side_brand.setObjectName("sideBrand")
        self.side_brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.side_brand)

        self.nav_section = QLabel("NAVEGAÇÃO")
        self.nav_section.setObjectName("sideSection")
        layout.addWidget(self.nav_section)
        self.nav_buttons: list[tuple[QPushButton, str, str]] = []
        for icon, text in (
            ("⌂", "Início"),
            ("◉", "Conta"),
            ("♧", "Amigos"),
            ("◈", "Personagens e Cones"),
            ("◆", "Builds"),
            ("⬡", "Relíquias"),
            ("✦", "Saltos"),
            ("◎", "Planejador"),
            ("★", "Rank"),
        ):
            button = QPushButton(f"{icon}   {text}")
            button.setObjectName("navButton")
            button.setCheckable(text != "Rank")
            button.setToolTip(
                "Abrir o perfil da UID principal no SeeleLand"
                if text == "Rank" else text
            )
            if text == "Início":
                button.setChecked(True)
            if text == "Rank":
                button.clicked.connect(self.open_seeleland_rank)
            else:
                button.clicked.connect(
                    lambda _checked=False, destination=text: self._navigate(destination)
                )
            layout.addWidget(button)
            self.nav_buttons.append((button, icon, text))
        layout.addStretch(1)

        self.side_source = QLabel("Dados públicos via\nEnka.Network")
        self.side_source.setObjectName("footer")
        self.side_source.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.side_source)

        self.auth_guest_button = QPushButton("◎   Entrar / Cadastrar")
        self.auth_guest_button.setObjectName("authButton")
        self.auth_guest_button.setToolTip("Entrar ou criar um perfil local")
        self.auth_guest_button.clicked.connect(self.open_auth_dialog)
        layout.addWidget(self.auth_guest_button)

        self.auth_user_frame = QFrame()
        self.auth_user_frame.setObjectName("sidebarUserPanel")
        user_layout = QHBoxLayout(self.auth_user_frame)
        user_layout.setContentsMargins(7, 7, 5, 7)
        user_layout.setSpacing(7)
        self.auth_avatar = QLabel("?")
        self.auth_avatar.setObjectName("sidebarAvatar")
        self.auth_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auth_avatar.setFixedSize(34, 34)
        self.auth_user_info = QWidget()
        info_layout = QVBoxLayout(self.auth_user_info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)
        self.auth_username = QLabel("Visitante")
        self.auth_username.setObjectName("sidebarUsername")
        self.auth_status = QLabel("Perfil local")
        self.auth_status.setObjectName("sidebarUserStatus")
        info_layout.addWidget(self.auth_username)
        info_layout.addWidget(self.auth_status)
        self.settings_button = QPushButton("⚙")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setFixedSize(36, 36)
        self.settings_button.setToolTip("Configurações do perfil")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        user_layout.addWidget(self.auth_avatar)
        user_layout.addWidget(self.auth_user_info, 1)
        user_layout.addWidget(self.settings_button)
        layout.addWidget(self.auth_user_frame)
        self._refresh_auth_sidebar()
        return self.sidebar

    def open_seeleland_rank(self) -> None:
        user = self.auth_service.current_user
        if user is None:
            self.set_status(
                "Entre em uma conta para abrir seu ranking no SeeleLand.", "error"
            )
            self.open_auth_dialog()
            return
        if not user.game_uid:
            self._navigate("Conta")
            self._refresh_account_page()
            self.account_status.setText(
                "Defina sua UID principal na engrenagem para abrir o ranking."
            )
            return
        dialog = RankRedirectDialog(user.game_uid, self)
        if not dialog.exec():
            return
        url = QUrl(f"https://seeleland.com/leaderboards/{user.game_uid}")
        if not QDesktopServices.openUrl(url):
            self.set_status("Não foi possível abrir o navegador padrão.", "error")

    def open_auth_dialog(self) -> None:
        dialog = AuthDialog(self.auth_service, self)
        if dialog.exec():
            self._refresh_auth_sidebar()

    def open_settings_dialog(self) -> None:
        user = self.auth_service.current_user
        if user is None:
            self.open_auth_dialog()
            return
        dialog = SettingsDialog(
            user,
            self,
            drive_service=GoogleDriveService(user),
            warp_database=self.warp_panel.database,
        )
        dialog.exec()
        if dialog.cloud_changed:
            self.warp_panel.refresh()
        if dialog.logout_requested:
            self.auth_service.logout()
            self._refresh_auth_sidebar()
        elif dialog.uid_to_save is not None:
            try:
                self.auth_service.update_game_uid(dialog.uid_to_save)
            except ValueError as error:
                self.set_status(str(error), "error")
                return
            self._refresh_auth_sidebar()
            if dialog.uid_to_save:
                self.set_status("UID principal salva. Abra Conta para carregá-la.")

    def _backup_warps_to_drive(self, owner_id: int) -> None:
        user = self.auth_service.current_user
        if user is None or user.id != owner_id:
            return
        service = GoogleDriveService(user)
        if not service.connected_email():
            return
        payload = self.warp_panel.database.export_owner(owner_id)
        worker = GoogleDriveWorker(lambda: service.upload_backup(payload))
        self.drive_workers.add(worker)
        worker.succeeded.connect(
            lambda message: self.warp_panel._set_status(
                f"{message} Importação e nuvem sincronizadas.", "success"
            )
        )
        worker.failed.connect(
            lambda message: self.warp_panel._set_status(
                f"Importação salva localmente, mas o backup falhou: {message}", "error"
            )
        )
        worker.finished.connect(lambda: self._release_drive_worker(worker))
        worker.start()

    def _release_drive_worker(self, worker: GoogleDriveWorker) -> None:
        self.drive_workers.discard(worker)
        worker.deleteLater()

    def _load_saved_uid(self, *, force: bool = False) -> None:
        self.page_stack.setCurrentIndex(4)
        self._refresh_account_page()
        user = self.auth_service.current_user
        if user is None or not user.game_uid:
            return
        self.pending_account_target = "account"
        self.account_status.setObjectName("statusInfo")
        self.account_status.setText("Carregando sua conta principal…")
        self.account_status.style().unpolish(self.account_status)
        self.account_status.style().polish(self.account_status)
        self.enka_client.fetch_account(user.game_uid, force=force)

    def refresh_loaded_account(self) -> None:
        user = self.auth_service.current_user
        if user is None or not user.game_uid:
            self.set_status("Defina sua UID principal nas configurações.", "error")
            return
        self.pending_account_target = "account"
        self.set_status("Atualizando personagens e relíquias da sua conta…")
        self.enka_client.fetch_account(user.game_uid, force=True)

    def _refresh_auth_sidebar(self) -> None:
        user = self.auth_service.current_user
        logged_in = user is not None
        self.auth_guest_button.setVisible(not logged_in)
        self.auth_user_frame.setVisible(logged_in)
        if user is not None:
            self.auth_username.setText(user.username)
            self.auth_avatar.setText(user.username[:1].upper())
            self.auth_user_frame.setToolTip(user.email or "Perfil local")
        expanded = self.sidebar_expanded
        self.auth_guest_button.setText("◎   Entrar / Cadastrar" if expanded else "◎")
        self.auth_user_info.setVisible(expanded)
        self.auth_avatar.setVisible(expanded)
        if hasattr(self, "warp_panel"):
            self.warp_panel.set_user(user)
        if hasattr(self, "planner_panel"):
            self.planner_panel.set_user(user)
        if hasattr(self, "relic_inventory_panel"):
            self.relic_inventory_panel.set_user(user)
        if hasattr(self, "friends_panel"):
            self.friends_panel.set_user(user)
        if hasattr(self, "add_friend_button"):
            self._refresh_friend_action()
        if hasattr(self, "account_page"):
            if user is None or self.own_account_user_id != user.id:
                self.own_account = None
                self.own_account_user_id = None
            self._refresh_account_page()

    def _refresh_account_page(self) -> None:
        user = self.auth_service.current_user
        if user is None:
            self.account_load_button.setEnabled(False)
            self.account_status.setText("Entre ou crie um perfil para abrir Conta.")
            return
        self.account_load_button.setEnabled(bool(user.game_uid))
        if self.own_account is not None and self.own_account_user_id == user.id:
            return
        self.account_profile_name.setText("Conta não carregada")
        self.account_profile_uid.setText("—")
        self.account_profile_meta.setText(
            "A UID principal será carregada automaticamente."
            if user.game_uid
            else "Defina sua UID principal pela engrenagem da sidebar."
        )
        self.account_profile_signature.clear()
        self.account_status.setText(
            f"UID principal configurada: {user.game_uid}"
            if user.game_uid else "Nenhuma UID principal configurada."
        )

    def _navigate(self, destination: str) -> None:
        if hasattr(self, "relic_inventory_panel") and destination != "Relíquias":
            self.relic_inventory_panel.set_active(False)
        if hasattr(self, "catalog_panel") and destination != "Personagens e Cones":
            self.catalog_panel.set_active(False)
        if destination == "Saltos":
            self.page_stack.setCurrentIndex(1)
            self._defer_with_loading(
                "page", "Organizando seu histórico de Saltos…",
                self.warp_panel.refresh,
            )
        elif destination == "Planejador":
            self.page_stack.setCurrentIndex(2)
            self._defer_with_loading(
                "page", "Calculando probabilidades e objetivos…",
                self.planner_panel.refresh,
            )
        elif destination == "Relíquias":
            self.page_stack.setCurrentIndex(3)
            self._defer_with_loading(
                "page", "Organizando suas relíquias salvas…",
                lambda: self.relic_inventory_panel.set_active(True),
            )
        elif destination == "Amigos":
            self.page_stack.setCurrentIndex(5)
            self.friends_panel.refresh()
        elif destination == "Início":
            self.page_stack.setCurrentIndex(6)
        elif destination == "Personagens e Cones":
            self.page_stack.setCurrentIndex(7)
            self._defer_with_loading(
                "page", "Abrindo o catálogo de personagens e cones…",
                lambda: self.catalog_panel.set_active(True),
            )
        elif destination == "Conta":
            self._load_saved_uid()
        else:
            if destination == "Builds" and self.build_source == "own":
                self.build_source = None
                self.current_uid = ""
                self.current_characters = []
                self.current_character_id = ""
            loaded = bool(self.current_characters) and self.build_source is not None
            self._show_build_content(loaded)
            if not loaded:
                self.set_status(
                    "Nenhuma UID pesquisada. Use a tela inicial para ver as builds."
                )
        for button, _icon, text in self.nav_buttons:
            button.setChecked(text == destination)

    def _defer_with_loading(
        self, key: str, message: str, operation: Callable[[], None]
    ) -> None:
        if not hasattr(self, "loading_overlay"):
            operation()
            return
        self.loading_overlay.start(key, message)
        QTimer.singleShot(
            35, lambda: self._finish_loading_operation(key, operation)
        )

    def _finish_loading_operation(
        self, key: str, operation: Callable[[], None]
    ) -> None:
        try:
            operation()
        finally:
            self.loading_overlay.stop(key)

    def _warp_busy_changed(self, busy: bool) -> None:
        if busy:
            self.loading_overlay.start(
                "warp-import", "Importando e organizando o histórico de Saltos…"
            )
        else:
            self.loading_overlay.stop("warp-import")

    def _show_build_content(self, loaded: bool) -> None:
        self.page_stack.setCurrentIndex(0)
        self.build_empty_panel.setVisible(not loaded)
        self.build_scroll.setVisible(loaded)
        self.header_refresh_button.setVisible(loaded and self.build_source == "own")
        self._refresh_friend_action(loaded)
        if not loaded:
            return
        self.content_splitter.widget(0).setVisible(True)
        self.content_splitter.widget(2).setVisible(True)
        self.content_splitter.setSizes([300, 240, 460])

    def toggle_sidebar(self) -> None:
        self.sidebar_expanded = not self.sidebar_expanded
        expanded = self.sidebar_expanded
        self.sidebar.setFixedWidth(230 if expanded else 62)
        self.sidebar_toggle.setText("☰" if expanded else "»")
        self.sidebar_toggle.setToolTip(
            "Fechar barra lateral" if expanded else "Abrir barra lateral"
        )
        for widget in (
            self.side_brand,
            self.nav_section,
            self.side_source,
        ):
            widget.setVisible(expanded)
        for button, icon, text in self.nav_buttons:
            button.setText(f"{icon}   {text}" if expanded else icon)
            button.setStyleSheet("text-align:left;" if expanded else "text-align:center;")
        self._refresh_auth_sidebar()

    def _build_selector(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("selectorPanel")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel("Personagens")
        title.setObjectName("sectionTitle")
        title.setFixedWidth(100)
        self.character_list = QListWidget()
        self.character_list.setObjectName("portraitList")
        self.character_list.setFlow(QListWidget.Flow.LeftToRight)
        self.character_list.setWrapping(False)
        self.character_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.character_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.character_list.currentRowChanged.connect(self.show_character_details)
        layout.addWidget(title)
        layout.addWidget(self.character_list, 1)
        return frame

    def _build_art_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("artPanel")
        frame.setMinimumWidth(180)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.character_art = ResponsiveImageLabel()
        layout.addWidget(self.character_art, 1)
        self.art_caption = QLabel("Selecione um personagem")
        self.art_caption.setObjectName("artCaption")
        self.art_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        content = QWidget()
        content.setObjectName("scrollContent")
        self.stats_layout = QVBoxLayout(content)
        self.stats_layout.setContentsMargins(8, 7, 8, 7)
        self.stats_layout.setSpacing(3)

        self.detail_name = QLabel("Personagem")
        self.detail_name.setObjectName("detailName")
        self.detail_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_name.setWordWrap(True)
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
        identity.addWidget(self.element_icon)
        identity.addWidget(self.detail_name, 1)
        identity.addWidget(self.path_icon)
        self.detail_rarity = QLabel("☆☆☆☆☆")
        self.detail_rarity.setObjectName("rarity")
        self.detail_rarity.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.stats_layout.addWidget(self.detail_rarity)
        self.stats_layout.addLayout(badges)

        section = QLabel("Atributos")
        section.setObjectName("sectionTitle")
        self.stats_layout.addWidget(section)
        self.stat_rows = QVBoxLayout()
        self.stat_rows.setSpacing(0)
        self.stats_layout.addLayout(self.stat_rows)

        self.benchmark_card = BenchmarkCard()
        self.stats_layout.addWidget(self.benchmark_card)
        self.team_card = TeamCard()
        self.team_card.custom_requested.connect(self.use_custom_team)
        self.team_card.edit_requested.connect(self.open_custom_team_dialog)
        self.team_card.default_requested.connect(self.use_default_team)
        self.stats_layout.addWidget(self.team_card)
        self.combat_stats_card = CombatStatsCard()
        self.stats_layout.addWidget(self.combat_stats_card)
        self.stats_layout.addStretch(1)
        outer.addWidget(content, 1)
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
        layout.addWidget(title)

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
        header = QHBoxLayout()
        title = QLabel("RELÍQUIAS EQUIPADAS")
        title.setObjectName("sectionTitle")
        self.relic_count = QLabel("0/6")
        self.relic_count.setObjectName("badge")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.relic_count)
        outer.addLayout(header)
        legend = QLabel("Cada < representa uma melhoria recebida pelo subatributo")
        legend.setObjectName("sectionHint")
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
        self.relic_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.relic_empty = QLabel("As relíquias do personagem aparecerão aqui.")
        self.relic_empty.setObjectName("muted")
        self.relic_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.relic_grid.addWidget(self.relic_empty, 0, 0, 1, 2)
        self.relic_scroll.setWidget(content)
        outer.addWidget(self.relic_scroll, 1)
        return frame

    def search_uid(self, requested_uid: str | None = None) -> None:
        uid = (requested_uid if requested_uid is not None else self.uid_input.text()).strip()
        if len(uid) != 9 or not uid.isdigit():
            self.home_panel.set_message(
                "O UID deve conter exatamente 9 números.", error=True
            )
            self.uid_input.setFocus()
            return
        self.home_panel.set_message("")
        self.pending_account_target = "builds"
        self._navigate("Builds")
        self.set_status("Carregando personagens, imagens e relíquias…")
        self.enka_client.fetch_account(uid)

    def add_current_friend(self) -> None:
        account = self.current_account
        if account is None or self.build_source == "own":
            return
        if self.auth_service.current_user is None:
            self.open_auth_dialog()
            self._refresh_friend_action()
            return
        try:
            self.auth_service.add_friend(
                account.uid,
                account.nickname,
                account.level,
                account.world_level,
                account.profile_icon_url,
            )
        except ValueError as error:
            self.set_status(str(error), "error")
            return
        self.friends_panel.refresh()
        self._navigate("Amigos")
        self.friends_panel.subtitle.setText(
            f"{account.nickname} foi adicionado à sua lista de amigos."
        )

    def _refresh_friend_action(self, loaded: bool | None = None) -> None:
        if not hasattr(self, "add_friend_button"):
            return
        account = self.current_account
        if loaded is None:
            loaded = bool(account and self.current_characters and self.build_source)
        user = self.auth_service.current_user
        visible = bool(
            loaded
            and account is not None
            and self.build_source in {"manual", "friend"}
            and (user is None or account.uid != user.game_uid)
        )
        self.add_friend_button.setVisible(visible)
        if not visible or account is None:
            return
        if user is None:
            self.add_friend_button.setText("♡  Entrar para adicionar")
            self.add_friend_button.setEnabled(True)
        elif self.auth_service.is_friend(account.uid):
            self.add_friend_button.setText("✓  Amigo adicionado")
            self.add_friend_button.setEnabled(False)
        else:
            self.add_friend_button.setText("♡  Adicionar amigo")
            self.add_friend_button.setEnabled(True)

    def _open_friend_profile(self, uid: str) -> None:
        self.pending_account_target = "friend"
        self._navigate("Builds")
        self.set_status("Carregando o perfil do amigo…")
        self.enka_client.fetch_account(uid)

    def _set_loading(self, loading: bool) -> None:
        self.uid_input.setEnabled(not loading)
        self.search_button.setEnabled(not loading)
        user = self.auth_service.current_user
        self.account_load_button.setEnabled(
            not loading and bool(user and user.game_uid)
        )
        self.header_refresh_button.setEnabled(not loading)
        self.header_refresh_button.setText(
            "Atualizando…" if loading and self.build_source == "own"
            else "↻  Atualizar conta"
        )
        self.search_button.setText("Carregando…" if loading else "Pesquisar UID")
        if loading:
            self.loading_overlay.start(
                "account", "Consultando personagens, builds e relíquias…"
            )
        else:
            self.loading_overlay.stop("account")

    def _request_failed(self, message: str) -> None:
        if self.pending_account_target == "account":
            self.account_status.setObjectName("statusError")
            self.account_status.setText(message)
            self.account_status.style().unpolish(self.account_status)
            self.account_status.style().polish(self.account_status)
        else:
            self.set_status(message, "error")

    def _account_loaded(self, account: AccountSummary, message: str) -> None:
        self._capture_relic_inventory(account)
        if self.pending_account_target == "account":
            self.own_account = account
            user = self.auth_service.current_user
            self.own_account_user_id = user.id if user else None
            self._render_own_account(account)
            self.build_source = "own"
            self.display_account(account)
            self._show_build_content(bool(account.characters))
            for button, _icon, text in self.nav_buttons:
                button.setChecked(text == "Conta")
            self.account_status.setObjectName(
                "statusSuccess" if account.characters else "statusError"
            )
            self.account_status.setText(message)
            self.account_status.style().unpolish(self.account_status)
            self.account_status.style().polish(self.account_status)
            self.set_status(
                "Builds da sua conta principal. Use Builds para pesquisar outras UIDs.",
                "success" if account.characters else "error",
            )
            return
        self.build_source = (
            "friend" if self.pending_account_target == "friend" else "manual"
        )
        if self.build_source == "friend" and self.auth_service.current_user is not None:
            self.auth_service.add_friend(
                account.uid,
                account.nickname,
                account.level,
                account.world_level,
                account.profile_icon_url,
            )
            self.friends_panel.refresh()
        self.display_account(account)
        self._show_build_content(bool(account.characters))
        self.set_status(message, "success" if account.characters else "error")

    def _capture_relic_inventory(self, account: AccountSummary) -> None:
        user = self.auth_service.current_user
        if user is None or not user.game_uid or account.uid != user.game_uid:
            return
        self.relic_database.sync_account(user.id, account, self.benchmark_engine)
        self.relic_inventory_panel.mark_dirty()

    def _render_own_account(self, account: AccountSummary) -> None:
        self.account_profile_name.setText(account.nickname)
        self.account_profile_uid.setText(f"UID {account.uid}")
        self.account_profile_meta.setText(
            f"Nível {account.level} · Equilíbrio {account.world_level} · "
            f"{len(account.characters)} personagens públicos"
        )
        self.account_profile_signature.setText(account.signature)
        self.account_profile_avatar.setText(account.nickname[:1].upper() if account.nickname else "✦")

    def set_status(self, message: str, kind: str = "info") -> None:
        object_name = {"success": "statusSuccess", "error": "statusError"}.get(
            kind, "statusInfo"
        )
        self.status_label.setObjectName(object_name)
        self.status_label.setText(message)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def display_account(self, account: AccountSummary) -> None:
        self.current_account = account
        self.current_uid = account.uid
        self.account_label.setText(account.nickname)
        self.profile_header_bio.setText(account.signature or "Sem biografia pública.")
        self.profile_header_meta.setText(
            f"Nível {account.level} · Equilíbrio {account.world_level} · "
            f"{account.achievement_count} conquistas"
        )
        self.copy_uid_button.setText("⧉  Copiar UID")
        self.copy_uid_button.setEnabled(True)
        self.copy_uid_button.setToolTip(f"Copiar UID {account.uid}")
        self.profile_header_avatar.clear_image()
        self.profile_header_avatar.setText(
            account.nickname[:1].upper() if account.nickname else "✦"
        )
        if account.profile_icon_url:
            self.image_loader.load(
                account.profile_icon_url,
                lambda pixmap, uid=account.uid: self._set_profile_icon_if_current(
                    uid, pixmap
                ),
            )
        self.uid_caption.setText(f"UID {account.uid}")
        self.current_characters = account.characters
        self.benchmark_results.clear()
        self.fribbels_cache.clear()
        self.active_benchmark_ids.clear()
        self.unsupported_benchmark_characters.clear()
        self.character_list.clear()
        for character in account.characters:
            item = QListWidgetItem()
            card = CharacterPortraitCard(character)
            item.setSizeHint(card.sizeHint())
            self.character_list.addItem(item)
            self.character_list.setItemWidget(item, card)
            self.image_loader.load(character.icon_url, card.avatar.set_image)
        if account.characters:
            self.character_list.setCurrentRow(0)

    def _set_profile_icon_if_current(self, uid: str, pixmap: QPixmap) -> None:
        if self.current_account is not None and self.current_account.uid == uid:
            self.profile_header_avatar.set_image(pixmap)

    def show_character_details(self, row: int) -> None:
        if row < 0 or row >= len(self.current_characters):
            return
        self._detail_request += 1
        request = self._detail_request
        self.loading_overlay.start(
            "character", f"Preparando a build de {self.current_characters[row].name}…"
        )
        QTimer.singleShot(
            35, lambda: self._finish_character_details(row, request)
        )

    def _finish_character_details(self, row: int, request: int) -> None:
        if request != self._detail_request:
            return
        try:
            self._show_character_details(row)
        finally:
            self.loading_overlay.stop("character")

    def _show_character_details(self, row: int) -> None:
        if row < 0 or row >= len(self.current_characters):
            return
        character = self.current_characters[row]
        self.current_character_id = character.avatar_id
        self.detail_name.setText(character.name)
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

        avatar_id = character.avatar_id
        self.image_loader.load(
            character.splash_url,
            lambda pixmap: self._set_art_if_current(avatar_id, pixmap),
        )
        self._display_light_cone_art(character)
        self._display_stats(character)
        self._display_relics(character)
        self._display_benchmark(character)

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

    def _display_light_cone_art(self, character: CharacterSummary) -> None:
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
            self.light_cone_banner.set_image,
        )

    def _set_art_if_current(self, avatar_id: str, pixmap: QPixmap) -> None:
        if avatar_id == self.current_character_id:
            self.character_art.set_image(pixmap)

    def _display_stats(self, character: CharacterSummary) -> None:
        self._clear_layout(self.stat_rows)
        by_key = {stat.key: stat for stat in character.stats}
        ordered: list[CharacterStat] = [
            by_key[key] for key in PRIMARY_STATS if key in by_key
        ]
        element_key = ELEMENT_STATS.get(character.element)
        if element_key and element_key in by_key:
            ordered.append(by_key[element_key])
        for stat in ordered:
            self.stat_rows.addWidget(StatRow(stat))

    def _display_relics(self, character: CharacterSummary) -> None:
        self._clear_layout(self.relic_grid)
        self.current_relic_cards = []
        if not character.relics:
            self.relic_empty = QLabel("Nenhuma relíquia pública encontrada.")
            self.relic_empty.setObjectName("muted")
            self.relic_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.relic_grid.addWidget(self.relic_empty, 0, 0, 1, 2)
            return
        for index, relic in enumerate(character.relics):
            rating = self.benchmark_engine.rate_relic(character, relic)
            card = RelicCard(relic, rating)
            self.current_relic_cards.append(card)
            self.image_loader.load(relic.icon_url, card.icon.set_image)
        self._reflow_relic_cards()

    def _reflow_relic_cards(self) -> None:
        if not self.current_relic_cards:
            return
        while self.relic_grid.count():
            self.relic_grid.takeAt(0)
        available_width = self.relics_panel.width() - 24
        columns = 2 if available_width >= 417 else 1
        self.relic_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            if columns == 2 else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        for index, card in enumerate(self.current_relic_cards):
            self.relic_grid.addWidget(card, index // columns, index % columns)
        self.relic_grid.setColumnStretch(0, 1)
        self.relic_grid.setColumnStretch(1, 1 if columns == 2 else 0)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        if hasattr(self, "size_grip"):
            self.size_grip.move(
                self.width() - self.size_grip.width(),
                self.height() - self.size_grip.height(),
            )
            self.size_grip.setVisible(not self.isMaximized())
            self.size_grip.raise_()
        if hasattr(self, "title_bar"):
            self.title_bar.sync_state()
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.setGeometry(self.centralWidget().rect())
            self.loading_overlay.raise_()
        if not hasattr(self, "content_splitter"):
            return
        available = max(1, self.content_splitter.width())
        if available < 780:
            proportions = (0.27, 0.30, 0.43)
        elif available < 1150:
            proportions = (0.30, 0.24, 0.46)
        else:
            proportions = (0.31, 0.23, 0.46)
        self.content_splitter.setSizes(
            [round(available * proportion) for proportion in proportions]
        )
        QTimer.singleShot(0, self._reflow_relic_cards)

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
        return team if isinstance(team, list) and len(team) == 3 else None

    def _uses_custom_team(self, character_id: str) -> bool:
        enabled = self.team_settings.value(
            self._team_settings_key(character_id, "custom"), False, type=bool
        )
        return bool(enabled and self._custom_team(character_id))

    def _default_team_for_editor(self, character: CharacterSummary) -> list[dict[str, object]]:
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

    def open_custom_team_dialog(self) -> None:
        character = next(
            (
                item for item in self.current_characters
                if str(item.avatar_id) == self.current_character_id
            ),
            None,
        )
        if character is None:
            return
        initial = self._custom_team(str(character.avatar_id))
        dialog = CustomTeamDialog(
            initial or self._default_team_for_editor(character),
            self,
            str(character.avatar_id),
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
            self.team_card.set_mode(False)
            self.set_status(
                "Nenhum time customizado salvo. Clique nas imagens do time para configurar."
            )
            return
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
        character_id = str(character.avatar_id)
        cache_key = self._benchmark_cache_key(character)
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
            return
        if not engine_available() or not isinstance(
            character.raw.get("fribbels_payload"), dict
        ):
            return
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

    def _fribbels_benchmark_ready(self, cache_key: str, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        character_id = str(payload.get("characterId", ""))
        character = next(
            (item for item in self.current_characters if str(item.avatar_id) == character_id),
            None,
        )
        if character is None:
            return
        self.fribbels_cache[cache_key] = payload
        if cache_key != self._benchmark_cache_key(character):
            return
        result = self.benchmark_results.get(character_id)
        if result is None:
            return
        self.benchmark_engine.apply_fribbels_result(character, result, payload)
        if self.current_character_id == character_id:
            self._render_benchmark(result)

    def _fribbels_benchmark_failed(self, cache_key: str, message: str) -> None:
        character = next(
            (
                item for item in self.current_characters
                if self._benchmark_cache_key(item) == cache_key
            ),
            None,
        )
        if character is not None and self.current_character_id == str(character.avatar_id):
            character_id = str(character.avatar_id)
            if "não possui DPS Benchmark" in message:
                self.unsupported_benchmark_characters.add(character_id)
                result = self.benchmark_results.get(character_id)
                if result is not None:
                    self._mark_benchmark_unsupported(result)
                    self._render_benchmark(result)
                return
            self.benchmark_card.set_engine_error(message)

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
        self.active_benchmark_ids.discard(worker.request_key)
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
                MainWindow._clear_layout(item.layout())
