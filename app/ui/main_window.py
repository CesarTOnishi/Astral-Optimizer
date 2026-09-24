from __future__ import annotations

from collections.abc import Callable
import json
import time
import unicodedata

from PySide6.QtCore import QEvent, QSettings, QStandardPaths, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
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
from app.activity_log import ActivityLog
from app.auth import AuthService
from app.benchmark import BenchmarkEngine
from app.benchmark.fribbels_client import FribbelsBenchmarkWorker, engine_available
from app.benchmark.teams import default_team
from app.build_history import BuildHistoryDatabase
from app.catalog import CatalogVersionCheckWorker
from app.cloud import (
    OneDriveBackupService,
    OneDriveWorker,
)
from app.config import (
    APP_HOME_BACKGROUND,
    APP_ICON_ICO,
    APP_ICON_PNG,
    APP_VERSION,
)
from app.models import AccountSummary, CharacterStat, CharacterSummary
from app.preferences import ExperienceSettings, apply_experience_preferences
from app.privacy import hide_uid_in_shared_images
from app.relics import RelicDatabase
from app.sync_manager import BackgroundSyncManager
from app.ui.auth_dialogs import AuthDialog, SettingsDialog
from app.ui.activity_history import ActivityHistoryButton
from app.ui.build_history import (
    BuildComparisonDialog,
    BuildHistoryBar,
    ConfirmBuildDeleteDialog,
)
from app.ui.build_share import render_build_share_card
from app.ui.motion import AnimatedStack as QStackedWidget, animate_width, install_motion
from app.ui.account_dashboard import AccountDashboard
from app.ui.icons import set_button_icon
from app.ui.catalog_panel import CatalogPanel
from app.ui.contextual_help import (
    BENCHMARK_HELP,
    BUILD_SOURCE_HELP,
    RELIC_GRADE_HELP,
    ContextHelpButton,
)
from app.ui.friends_panel import FriendsPanel
from app.ui.experience import (
    DiagnosticsPanel, ExperienceDialog, GuidedTourOverlay, TourStep,
    copy_error_details,
)
from app.ui.home_panel import HomePanel
from app.ui.image_loader import ImageLoader
from app.ui.loading import LoadingOverlay, load_icon_pixmap
from app.ui.notifications import NotificationBell, NotificationCenter
from app.ui.task_center import BackgroundTaskButton
from app.ui.planner_panel import PlannerPanel
from app.ui.rank_dialog import RankRedirectDialog
from app.ui.team_dialog import CustomTeamDialog
from app.ui.update_dialog import UpdateAvailableDialog, UpdateReadyDialog
from app.ui.relic_inventory_panel import RelicInventoryPanel
from app.ui.warp_panel import WarpPanel
from app.ui.whats_new import WhatsNewPanel
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
from app.updater import (
    PreparedUpdate,
    ReleaseInfo,
    UpdateCheckWorker,
    UpdateDownloadWorker,
    consume_update_result,
    is_newer_version,
    launch_installer,
    running_from_bundle,
)
from app.whats_new import WhatsNewSettings


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

        self.notification_bell = NotificationBell(window.notification_center, self)
        layout.addWidget(self.notification_bell)

        self.activity_history_button = ActivityHistoryButton(
            window.activity_log,
            lambda: (
                window.auth_service.current_user.id
                if window.auth_service.current_user is not None else 0
            ),
            self,
        )
        layout.addWidget(self.activity_history_button)

        self.whats_new_button = QPushButton("✧")
        self.whats_new_button.setText("")
        set_button_icon(self.whats_new_button, "warp")
        self.whats_new_button.setObjectName("whatsNewTitleButton")
        self.whats_new_button.setFixedSize(36, 32)
        self.whats_new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.whats_new_button.setToolTip(
            f"Novidades da versão {APP_VERSION}"
        )
        self.whats_new_button.setProperty(
            "unseen", window.whats_new_settings.should_show()
        )
        self.whats_new_button.clicked.connect(
            lambda: window._navigate("Novidades")
        )
        layout.addWidget(self.whats_new_button)

        self.minimize_button = QPushButton("—")
        self.maximize_button = QPushButton("□")
        self.close_button = QPushButton("×")
        for button, icon_name in ((self.minimize_button, "minimize"), (self.maximize_button, "maximize"), (self.close_button, "close")):
            button.setText("")
            set_button_icon(button, icon_name, 16)
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
        self.maximize_button.setText("")
        set_button_icon(self.maximize_button, "restore" if maximized else "maximize", 16)
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
    initial_account_sync_finished = Signal()

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
        self.activity_log = ActivityLog(self)
        self.notification_center = NotificationCenter(self)
        self.benchmark_engine = BenchmarkEngine()
        self.image_loader = ImageLoader(self)
        self.relic_database = RelicDatabase()
        self.build_history_database = BuildHistoryDatabase()
        self.current_characters: list[CharacterSummary] = []
        self.current_character_id = ""
        self.current_uid = ""
        self.current_account: AccountSummary | None = None
        self.build_source: str | None = None
        self.own_account: AccountSummary | None = None
        self.own_account_user_id: int | None = None
        self.pending_account_target = "builds"
        self.sidebar_expanded = True
        self.account_sync_failed = False
        self.failed_sync_tasks: set[str] = set()
        self.sync_manager = BackgroundSyncManager(self)
        self.sync_state = "idle"
        self.sync_message = "Sincronizado"
        self.sync_task_count = 0
        self.sync_spinner_frame = 0
        self.benchmark_workers: set[FribbelsBenchmarkWorker] = set()
        self.drive_workers: set[OneDriveWorker] = set()
        self.update_check_worker: UpdateCheckWorker | None = None
        self.catalog_version_worker: CatalogVersionCheckWorker | None = None
        self.update_download_worker: UpdateDownloadWorker | None = None
        self.prepared_update: PreparedUpdate | None = None
        self.settings_dialog: SettingsDialog | None = None
        self.update_check_manual = False
        self.update_prompt_open = False
        self.benchmark_results = {}
        self.fribbels_cache: dict[str, dict[str, object]] = {}
        self.active_benchmark_ids: set[str] = set()
        self.unsupported_benchmark_characters: set[str] = set()
        self.team_settings = QSettings("Astral Optimizer", "Custom Teams")
        self.update_settings = QSettings("Astral Optimizer", "Updates")
        self.current_relic_cards: list[RelicCard] = []
        self._detail_request = 0
        self._initial_account_sync_active = False
        self.experience_settings = ExperienceSettings()
        self.whats_new_settings = WhatsNewSettings()
        self._shortcuts: list[QShortcut] = []
        self.tutorial_overlay: GuidedTourOverlay | None = None
        self._tutorial_original_page = 6
        self._tutorial_original_nav: tuple[str, ...] = ()
        self._tutorial_sidebar_was_expanded = True

        install_motion()
        self._build_ui()
        apply_experience_preferences()
        self._setup_shortcuts()
        self.sync_manager.changed.connect(self._sync_status_changed)
        self.sync_status.retry_requested.connect(self._retry_background_task)
        self.sync_spinner_timer = QTimer(self)
        self.sync_spinner_timer.setInterval(320)
        self.sync_spinner_timer.timeout.connect(self._advance_sync_spinner)
        self.sync_spinner_timer.start()
        self.enka_client.loading_changed.connect(self._set_loading)
        self.enka_client.request_failed.connect(self._request_failed)
        self.enka_client.account_loaded.connect(self._account_loaded)
        self.catalog_panel.background_sync_changed.connect(
            self._catalog_sync_changed
        )
        self.catalog_panel.background_sync_progress.connect(
            lambda message: self.sync_manager.update("catalog", message)
        )
        self.catalog_panel.background_sync_failed.connect(
            lambda message: self.sync_manager.fail(
                "catalog", "Falha ao atualizar o catálogo", details=message
            )
        )
        self.catalog_panel.catalog_updated.connect(self._catalog_updated)
        QTimer.singleShot(0, self._show_previous_update_result)
        QTimer.singleShot(0, self._check_soft_pity_notifications)
        QTimer.singleShot(2600, self._check_updates_automatically)
        QTimer.singleShot(3400, self._check_catalog_version)
        QTimer.singleShot(0, self._show_whats_new_if_needed)

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

        self.status_bar = QFrame()
        self.status_bar.setObjectName("statusBar")
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        self.status_label = QLabel("Digite seu UID para carregar as builds públicas.")
        self.status_label.setObjectName("statusInfo")
        self.copy_error_button = QPushButton("Copiar detalhes")
        self.copy_error_button.setObjectName("copyErrorButton")
        self.copy_error_button.setVisible(False)
        self.copy_error_button.clicked.connect(
            lambda: copy_error_details(self.status_label.text(), "Janela principal")
        )
        status_layout.addWidget(self.status_label, 1)
        status_layout.addWidget(self.copy_error_button)
        layout.addWidget(self.status_bar)
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
        build_layout.addWidget(self._build_build_history_panel())
        build_layout.addWidget(self._build_benchmark_section())
        self.build_scroll.setWidget(build_content)
        layout.addWidget(self.build_scroll, 1)
        self.page_stack.addWidget(content)
        self.warp_panel = WarpPanel()
        self.warp_panel.set_user(self.auth_service.current_user)
        self.warp_panel.import_activity.connect(self._record_warp_import)
        self.warp_panel.import_completed.connect(self._backup_warps_to_onedrive)
        self.warp_panel.import_completed.connect(lambda _owner: self._refresh_dashboard())
        self.warp_panel.import_completed.connect(
            lambda _owner: self._check_soft_pity_notifications()
        )
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
        self.diagnostics_panel = DiagnosticsPanel({
            "Contas": self.auth_service.path,
            "Saltos": self.warp_panel.database.path,
            "Relíquias": self.relic_database.path,
            "Histórico de builds": self.build_history_database.path,
            "Histórico de atividades": self.activity_log.path,
        })
        self.page_stack.addWidget(self.diagnostics_panel)
        self.whats_new_panel = WhatsNewPanel()
        self.whats_new_panel.resource_requested.connect(
            self._open_release_resource
        )
        self.page_stack.addWidget(self.whats_new_panel)
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
        self.warp_panel.background_progress.connect(
            lambda message: self.sync_manager.update("warp-import", message)
        )
        self.warp_panel.background_failed.connect(self._warp_import_failed)

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

        title = QLabel("Sua conta")
        title.setObjectName("brandTitle")
        subtitle = QLabel(
            "Seus personagens, Saltos e relíquias em um só lugar."
        )
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("accountProfilePanel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)
        self.account_profile_avatar = AvatarLabel(78)
        self.account_profile_avatar.setObjectName("accountProfileAvatar")
        self.account_profile_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_profile_avatar.setFixedSize(78, 78)
        self.account_profile_name = QLabel("Conta não carregada")
        self.account_profile_name.setObjectName("detailName")
        self.account_profile_name.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.account_profile_uid = QLabel("—")
        self.account_profile_uid.setObjectName("profileUid")
        self.account_profile_uid.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.account_profile_meta = QLabel(
            "Entre no perfil e defina uma UID principal nas configurações."
        )
        self.account_profile_meta.setObjectName("muted")
        self.account_profile_meta.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.account_profile_meta.setWordWrap(True)
        self.account_profile_signature = QLabel("")
        self.account_profile_signature.setObjectName("profileSignature")
        self.account_profile_signature.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.account_profile_signature.setWordWrap(True)
        self.account_load_button = QPushButton("Atualizar conta")
        set_button_icon(self.account_load_button, "refresh", 16)
        self.account_load_button.setObjectName("primaryButton")
        self.account_load_button.clicked.connect(
            lambda: self._load_saved_uid(force=True)
        )
        self.account_status = QLabel("")
        self.account_status.setObjectName("statusInfo")
        self.account_status.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.account_status.setWordWrap(True)
        identity_row = QHBoxLayout()
        identity_row.setSpacing(16)
        identity_row.addWidget(self.account_profile_avatar)
        identity = QVBoxLayout()
        identity.setSpacing(4)
        identity.addWidget(self.account_profile_name)
        identity.addWidget(self.account_profile_uid)
        identity.addWidget(self.account_profile_meta)
        identity_row.addLayout(identity, 1)
        identity_row.addWidget(self.account_load_button)
        card_layout.addLayout(identity_row)
        card_layout.addWidget(self.account_profile_signature)
        account_status_row = QHBoxLayout()
        self.account_copy_error = QPushButton("Copiar detalhes")
        self.account_copy_error.setObjectName("copyErrorButton")
        self.account_copy_error.setVisible(False)
        self.account_copy_error.clicked.connect(
            lambda: copy_error_details(self.account_status.text(), "Sincronização da conta")
        )
        account_status_row.addWidget(self.account_status, 1)
        account_status_row.addWidget(self.account_copy_error)
        card_layout.addLayout(account_status_row)
        layout.addWidget(card)
        self.account_dashboard = AccountDashboard(self.image_loader)
        layout.addWidget(self.account_dashboard)
        layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

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
        account_name_row = QHBoxLayout()
        account_name_row.setSpacing(6)
        account_name_row.addWidget(self.account_label)
        account_name_row.addWidget(
            ContextHelpButton(*BUILD_SOURCE_HELP),
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        account_name_row.addStretch(1)
        identity.addLayout(account_name_row)
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
        layout.setSpacing(4)

        self.sidebar_toggle = QPushButton("")
        set_button_icon(self.sidebar_toggle, "menu")
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
        shortcut_labels = {
            "Início": "Ctrl+1", "Builds": "Ctrl+2", "Conta": "Ctrl+3",
            "Relíquias": "Ctrl+4", "Saltos": "Ctrl+5",
            "Planejador": "Ctrl+6", "Personagens e Cones": "Ctrl+7",
        }
        for icon, text in (
            ("home", "Início"),
            ("build", "Builds"),
            ("profile", "Conta"),
            ("friends", "Amigos"),
            ("catalog", "Personagens e Cones"),
            ("relic", "Relíquias"),
            ("warp", "Saltos"),
            ("planner", "Planejador"),
            ("rank", "Rank"),
        ):
            button = QPushButton(text)
            set_button_icon(button, icon)
            button.setAccessibleName(text)
            button.setObjectName("navButton")
            button.setCheckable(text != "Rank")
            button.setToolTip(
                "Abrir o perfil da UID principal no SeeleLand"
                if text == "Rank" else (
                    f"{text}  ·  {shortcut_labels[text]}"
                    if text in shortcut_labels else text
                )
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

        self.sync_status = BackgroundTaskButton(self.sync_manager)
        self.sync_status.setText("●  Sincronizado")
        self.sync_status.setToolTip(
            "Nenhuma tarefa em segundo plano.\nClique para abrir a central."
        )
        layout.addWidget(self.sync_status)

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
        self.auth_avatar = AvatarLabel(34)
        self.auth_avatar.setObjectName("sidebarAvatar")
        self.auth_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auth_avatar.setFixedSize(34, 34)
        self.auth_user_info = QWidget()
        info_layout = QVBoxLayout(self.auth_user_info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)
        for profile_widget in (self.auth_user_frame, self.auth_avatar, self.auth_user_info):
            profile_widget.setCursor(Qt.CursorShape.PointingHandCursor)
            profile_widget.installEventFilter(self)
        self.auth_username = QLabel("Visitante")
        self.auth_username.setObjectName("sidebarUsername")
        self.auth_status = QLabel("Perfil local")
        self.auth_status.setObjectName("sidebarUserStatus")
        for profile_label in (self.auth_username, self.auth_status):
            profile_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info_layout.addWidget(self.auth_username)
        info_layout.addWidget(self.auth_status)
        self.settings_button = QPushButton("⚙")
        self.settings_button.setText("")
        set_button_icon(self.settings_button, "settings")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setFixedSize(36, 36)
        self.settings_button.setToolTip("Configurações do perfil  ·  Ctrl+,")
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
            self._load_saved_uid()
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

    def open_settings_dialog(
        self, _checked: bool = False, *, initial_page: int = 0
    ) -> None:
        user = self.auth_service.current_user
        if user is None:
            dialog = ExperienceDialog(self)
            try:
                dialog.exec()
                apply_experience_preferences()
                if dialog.replay_tutorial:
                    QTimer.singleShot(0, lambda: self.show_tutorial(force=True))
            finally:
                dialog.deleteLater()
            return
        dialog = SettingsDialog(
            user,
            self,
            warp_database=self.warp_panel.database,
            initial_page=initial_page,
        )
        try:
            self.settings_dialog = dialog
            dialog.update_requested.connect(lambda: self.check_for_updates(manual=True))
            dialog.exec()
            self.settings_dialog = None
            replay_tutorial = dialog.tutorial_requested
            open_diagnostics = dialog.diagnostics_requested
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
            if replay_tutorial:
                QTimer.singleShot(0, lambda: self.show_tutorial(force=True))
            elif open_diagnostics:
                self._navigate("Diagnóstico")
        finally:
            self.settings_dialog = None
            dialog.deleteLater()

    def _show_whats_new_if_needed(self) -> None:
        if self.whats_new_settings.should_show():
            self._navigate("Novidades")

    def _mark_whats_new_seen(self) -> None:
        self.whats_new_settings.mark_seen()
        button = getattr(self.title_bar, "whats_new_button", None)
        if button is None:
            return
        button.setProperty("unseen", False)
        button.style().unpolish(button)
        button.style().polish(button)

    def _open_release_resource(self, destination: str) -> None:
        if destination == "Backup":
            if self.auth_service.current_user is None:
                self.set_status(
                    "Entre em um perfil local para configurar o backup pelo OneDrive."
                )
                self.open_auth_dialog()
                return
            self.open_settings_dialog(initial_page=3)
            return
        if destination == "Configurações":
            self.open_settings_dialog(initial_page=1)
            return
        self._navigate(destination)

    def show_tutorial(self, *, force: bool = False) -> None:
        first_run = not self.experience_settings.load().tutorial_completed
        if not force and not first_run:
            return
        if self.tutorial_overlay is not None:
            self.tutorial_overlay.raise_()
            self.tutorial_overlay.setFocus(Qt.FocusReason.OtherFocusReason)
            return

        self._tutorial_original_page = self.page_stack.currentIndex()
        self._tutorial_original_nav = tuple(
            text for button, _icon, text in self.nav_buttons if button.isChecked()
        )
        self._tutorial_sidebar_was_expanded = self.sidebar_expanded
        if not self.sidebar_expanded:
            self.toggle_sidebar()

        steps = (
            TourStep(
                "Bem-vindo ao Astral Optimizer",
                "Este tour usa os controles reais do aplicativo. O restante da tela fica escurecido e o destaque mostra exatamente onde agir. Use Próximo, Voltar ou as setas do teclado.",
                lambda: None,
                lambda: self._show_tutorial_page(6, "Início"),
            ),
            TourStep(
                "Central de notificações",
                "O sino reúne avisos importantes: catálogo desatualizado, nova versão, resultado do backup, relíquias alteradas e pity próximo do soft pity.",
                lambda: self.title_bar.notification_bell,
            ),
            TourStep(
                "Histórico de atividades",
                "Este botão mostra acontecimentos recentes que continuam disponíveis após fechar o app: sincronizações, relíquias alteradas, Saltos importados, backups, builds e atualizações.",
                lambda: self.title_bar.activity_history_button,
            ),
            TourStep(
                "Tarefas em segundo plano",
                "Clique no indicador de sincronização para acompanhar conta, catálogo, benchmark, backup e importação de Saltos. Se algo falhar, você poderá tentar novamente ou copiar os detalhes.",
                lambda: self.sync_status,
            ),
            TourStep(
                "Navegação principal",
                "A barra lateral leva a todas as áreas. O botão no topo recolhe a barra; Ctrl+B faz a mesma coisa. A linha inferior mostra sincronizações e tarefas em andamento.",
                lambda: self.sidebar,
            ),
            TourStep(
                "Pesquisar uma UID",
                "Na tela Início, informe uma UID válida para consultar o perfil público e as builds exibidas no jogo. Ctrl+K traz o foco direto para este campo.",
                lambda: self.home_panel.search_group,
                lambda: self._show_tutorial_page(6, "Início"),
            ),
            TourStep(
                "Builds e benchmarks",
                "Depois de pesquisar uma UID, esta área permite escolher o personagem e analisar atributos, cone de luz, relíquias, equipe, histórico e comparação com o benchmark.",
                self._tutorial_build_anchor,
                lambda: self._show_tutorial_page(0, "Builds"),
            ),
            TourStep(
                "Dashboard da conta",
                "Conta concentra o perfil da sua UID principal, seus personagens com benchmark, resumo de Saltos e relíquias. Atualizar conta força uma nova sincronização.",
                lambda: self.account_load_button,
                lambda: self._show_tutorial_page(4, "Conta"),
            ),
            TourStep(
                "Amigos",
                "Salve perfis consultados para revisitá-los rapidamente. A lista permite abrir a UID do amigo e comparar as builds públicas disponíveis.",
                lambda: self.friends_panel.count,
                lambda: self._show_tutorial_page(5, "Amigos"),
            ),
            TourStep(
                "Personagens e Cones",
                "O catálogo reúne dados de personagens e cones de luz. Pesquise por nome, aplique filtros e abra um item para ver atributos, habilidades e progressões.",
                lambda: self.catalog_panel.search,
                lambda: self._show_tutorial_page(7, "Personagens e Cones"),
            ),
            TourStep(
                "Atualização do catálogo",
                "Use este botão quando quiser baixar dados novos. O sino avisará caso a versão local esteja desatualizada.",
                lambda: self.catalog_panel.sync_button,
            ),
            TourStep(
                "Inventário de relíquias",
                "Relíquias registra os equipamentos vistos na sua conta. Os filtros separam personagem, situação, slot e conjunto, inclusive peças movidas ou que deixaram de aparecer.",
                lambda: self.relic_inventory_panel.character_filter,
                lambda: self._show_tutorial_page(3, "Relíquias"),
            ),
            TourStep(
                "Importar o histórico de Saltos",
                "A importação automática localiza o histórico do jogo no computador. Também é possível importar um link ou arquivo e atualizar os registros existentes.",
                lambda: self.warp_panel.auto_button,
                lambda: self._show_tutorial_warp_section(self.warp_panel.auto_button),
            ),
            TourStep(
                "Pity por banner",
                "Os cartões resumem pity atual, garantia, 50/50, quantidade de tiros e o último 5 estrelas de cada banner.",
                lambda: self.warp_panel.banner_buttons["11"],
                lambda: self._show_tutorial_warp_section(
                    self.warp_panel.banner_buttons["11"]
                ),
            ),
            TourStep(
                "Análises do histórico",
                "Os gráficos mostram tiros por mês e por versão. A área também calcula média pessoal de pity, vitórias e derrotas no 50/50 e possíveis lacunas no histórico.",
                lambda: self.warp_panel.monthly_chart,
                lambda: self._show_tutorial_warp_section(self.warp_panel.monthly_chart),
            ),
            TourStep(
                "Planejamento de recursos",
                "Informe jades, passes, Luz Estelar, cashback e ganho diário. Escolha a estratégia de aquisição para priorizar S1 ou um Eidolon sem precisar digitar a ordem.",
                lambda: self.planner_panel.settings_card,
                lambda: self._show_tutorial_page(2, "Planejador"),
            ),
            TourStep(
                "Metas e simulação",
                "A tabela organiza metas sequenciais, data-alvo, custo estimado, chance acumulada e saldo projetado. Assim você pode testar cenários antes de gastar.",
                lambda: self.planner_panel.table,
            ),
            TourStep(
                "Ranking externo",
                "Rank abre o perfil da sua UID principal no SeeleLand. É necessário entrar no app e configurar uma UID antes de usar o atalho.",
                lambda: self._tutorial_nav_button("Rank"),
            ),
            TourStep(
                "Sincronização em segundo plano",
                "Este indicador informa quando conta, catálogo, backup ou outras tarefas estão trabalhando. A sincronização da conta começa durante a tela de carregamento ao abrir o app.",
                lambda: self.sync_status,
            ),
            TourStep(
                "Perfil e configurações",
                "Entre ou abra seu perfil aqui. Na engrenagem ficam tema, redução de animações, privacidade para ocultar a UID das imagens, backup, atualização e acesso ao diagnóstico.",
                self._tutorial_profile_anchor,
            ),
            TourStep(
                "Diagnóstico e erros",
                "O diagnóstico mostra versão, caminhos dos bancos e estado do motor de benchmark. Quando houver um erro, use Copiar detalhes para facilitar a investigação.",
                lambda: self.diagnostics_panel.copy_button,
                lambda: self._show_tutorial_page(8, "Diagnóstico"),
            ),
            TourStep(
                "Tudo pronto",
                "Você pode rever este tour a qualquer momento com F1 ou em Configurações. Atalhos úteis: Ctrl+1 a Ctrl+7 para navegar, Ctrl+, para Configurações e Ctrl+Shift+D para Diagnóstico.",
                lambda: self.title_bar,
                lambda: self._show_tutorial_page(6, "Início"),
            ),
        )
        root = self.centralWidget()
        if root is None:
            return
        self.tutorial_overlay = GuidedTourOverlay(root, steps, first_run=first_run)
        self.tutorial_overlay.finished.connect(self._tutorial_finished)
        self.tutorial_overlay.start()

    def _show_tutorial_page(self, index: int, destination: str) -> None:
        self.page_stack.setCurrentIndex(index)
        if destination == "Conta":
            self._refresh_account_page()
        elif destination == "Diagnóstico":
            self.diagnostics_panel.refresh()
        for button, _icon, text in self.nav_buttons:
            button.setChecked(text == destination)

    def _tutorial_nav_button(self, destination: str) -> QWidget | None:
        return next(
            (button for button, _icon, text in self.nav_buttons if text == destination),
            None,
        )

    def _show_tutorial_warp_section(self, widget: QWidget) -> None:
        self._show_tutorial_page(1, "Saltos")
        self.warp_panel.page_scroll.ensureWidgetVisible(widget, 16, 16)

    def _tutorial_build_anchor(self) -> QWidget:
        return self.selector_panel if self.selector_panel.isVisible() else self.build_empty_panel

    def _tutorial_profile_anchor(self) -> QWidget:
        return self.auth_user_frame if self.auth_user_frame.isVisible() else self.auth_guest_button

    def _tutorial_finished(self) -> None:
        self.page_stack.setCurrentIndex(self._tutorial_original_page)
        for button, _icon, text in self.nav_buttons:
            button.setChecked(text in self._tutorial_original_nav)
        if not self._tutorial_sidebar_was_expanded and self.sidebar_expanded:
            self.toggle_sidebar()
        self.tutorial_overlay = None

    def _setup_shortcuts(self) -> None:
        mappings = (
            ("Ctrl+1", lambda: self._navigate("Início")),
            ("Ctrl+2", lambda: self._navigate("Builds")),
            ("Ctrl+3", lambda: self._navigate("Conta")),
            ("Ctrl+4", lambda: self._navigate("Relíquias")),
            ("Ctrl+5", lambda: self._navigate("Saltos")),
            ("Ctrl+6", lambda: self._navigate("Planejador")),
            ("Ctrl+7", lambda: self._navigate("Personagens e Cones")),
            ("Ctrl+B", self.toggle_sidebar),
            ("Ctrl+,", self.open_settings_dialog),
            ("Ctrl+Shift+D", lambda: self._navigate("Diagnóstico")),
            ("F1", lambda: self.show_tutorial(force=True)),
            ("Ctrl+K", self._focus_uid_search),
        )
        for sequence, callback in mappings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _focus_uid_search(self) -> None:
        self._navigate("Início")
        self.uid_input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.uid_input.selectAll()

    def _check_updates_automatically(self) -> None:
        try:
            last_check = int(self.update_settings.value("last_check", 0) or 0)
        except (TypeError, ValueError):
            last_check = 0
        if int(time.time()) - last_check >= 6 * 60 * 60:
            self.check_for_updates(manual=False)

    def _show_previous_update_result(self) -> None:
        result = consume_update_result()
        if result is None:
            return
        if result.status == "success":
            self.activity_log.add(
                "update",
                f"Aplicativo atualizado para {APP_VERSION}",
                result.message,
                kind="success",
            )
            self.notification_center.add(
                "app-update-result",
                "Atualização concluída",
                result.message,
                "success",
            )
            self.set_status(result.message, "success")
            return
        detail = result.message
        if result.log_path:
            detail += f" Log: {result.log_path}"
        self.activity_log.add(
            "update",
            "Falha ao atualizar o aplicativo",
            detail,
            kind="error",
        )
        self.notification_center.add(
            "app-update-result",
            "Erro ao aplicar atualização",
            detail,
            "error",
        )
        self.set_status(f"Não foi possível aplicar a atualização: {detail}", "error")

    def check_for_updates(self, manual: bool = False) -> None:
        if self.update_check_worker and self.update_check_worker.isRunning():
            if manual and self.settings_dialog:
                self.settings_dialog.set_update_status(
                    "A verificação já está em andamento…", checking=True
                )
            return
        self.update_check_manual = manual
        if manual and self.settings_dialog:
            self.settings_dialog.set_update_status(
                "Consultando as Releases do GitHub…", checking=True
            )
        worker = UpdateCheckWorker(self)
        self.update_check_worker = worker
        self.sync_manager.begin(
            "update-check", "Verificando atualizações…", retryable=True
        )
        worker.succeeded.connect(self._update_check_succeeded)
        worker.failed.connect(self._update_check_failed)
        worker.finished.connect(self._update_check_finished)
        worker.start()

    def _update_check_succeeded(self, value: object) -> None:
        self.sync_manager.finish("update-check", "Atualizações verificadas")
        self.update_settings.setValue("last_check", int(time.time()))
        release = value if isinstance(value, ReleaseInfo) else None
        if release is None:
            if self.update_check_manual and self.settings_dialog:
                self.settings_dialog.set_update_status(
                    f"Versão {APP_VERSION} · Nenhuma Release publicada no GitHub."
                )
            return
        if not is_newer_version(release.version):
            if self.update_check_manual and self.settings_dialog:
                self.settings_dialog.set_update_status(
                    f"Versão {APP_VERSION} · Você está usando a versão mais recente."
                )
            return
        self.notification_center.add(
            "app-update",
            "Nova versão disponível",
            f"Astral Optimizer {release.version} já pode ser instalado.",
            "info",
        )
        if self.settings_dialog:
            self.settings_dialog.set_update_status(
                f"Nova versão {release.version} disponível."
            )
        self._show_update_available(release)

    def _update_check_failed(self, message: str) -> None:
        self.sync_manager.fail(
            "update-check",
            "Falha ao verificar atualizações",
            details=message,
        )
        if self.update_check_manual:
            if self.settings_dialog:
                self.settings_dialog.set_update_status(
                    "Não foi possível verificar atualizações."
                )
            self.set_status(message, "error")

    def _update_check_finished(self) -> None:
        if self.update_check_worker:
            self.update_check_worker.deleteLater()
        self.update_check_worker = None

    def _show_update_available(self, release: ReleaseInfo) -> None:
        if self.update_prompt_open:
            return
        self.update_prompt_open = True
        can_install = running_from_bundle() and bool(release.download_url)
        parent = self.settings_dialog or self
        dialog = UpdateAvailableDialog(release, can_install, parent)
        accepted = bool(dialog.exec())
        self.update_prompt_open = False
        if not accepted:
            return
        if not can_install:
            if release.page_url and not QDesktopServices.openUrl(QUrl(release.page_url)):
                self.set_status("Não foi possível abrir a Release no navegador.", "error")
            return
        if self.settings_dialog:
            self.settings_dialog.accept()
        self._download_update(release)

    def _download_update(self, release: ReleaseInfo) -> None:
        if self.update_download_worker and self.update_download_worker.isRunning():
            return
        self.loading_overlay.start(
            "app-update", f"Baixando o Astral Optimizer {release.version}…"
        )
        self.set_status(
            "Baixando e preparando a atualização. O app reiniciará ao concluir."
        )
        self.prepared_update = None
        worker = UpdateDownloadWorker(release)
        self.update_download_worker = worker
        worker.succeeded.connect(self._update_download_succeeded)
        worker.failed.connect(self._update_download_failed)
        worker.finished.connect(self._update_download_finished)
        worker.start()

    def _update_download_succeeded(self, value: object) -> None:
        if not isinstance(value, PreparedUpdate):
            self._update_download_failed("A atualização preparada é inválida.")
            return
        self.prepared_update = value

    def _update_download_failed(self, message: str) -> None:
        self.loading_overlay.stop("app-update")
        self.set_status(f"Não foi possível atualizar: {message}", "error")

    def _update_download_finished(self) -> None:
        prepared = self.prepared_update
        self.prepared_update = None
        if self.update_download_worker:
            self.update_download_worker.deleteLater()
        self.update_download_worker = None
        if prepared is None:
            return
        self.loading_overlay.stop("app-update")
        if not UpdateReadyDialog(prepared.version, self).exec():
            self.set_status(
                "Atualização baixada, mas a instalação foi adiada. "
                "Verifique novamente quando quiser instalar."
            )
            return
        try:
            launch_installer(prepared)
        except Exception as error:
            self._update_download_failed(str(error))
            return
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _backup_warps_to_onedrive(self, owner_id: int) -> None:
        user = self.auth_service.current_user
        if user is None or user.id != owner_id:
            return
        service = OneDriveBackupService(user)
        if not service.available:
            return
        payload = self.warp_panel.database.export_owner(owner_id)
        worker = OneDriveWorker(lambda: service.save_backup(payload))
        sync_key = f"onedrive-backup:{owner_id}"
        self.sync_manager.begin(
            sync_key,
            "Aguardando a pasta sincronizada do OneDrive…",
            retryable=True,
        )
        self.drive_workers.add(worker)
        worker.succeeded.connect(
            lambda message: self.warp_panel._set_status(
                f"{message} O OneDrive fará a sincronização com a nuvem.", "success"
            )
        )
        worker.succeeded.connect(
            lambda _message: self.sync_manager.finish(
                sync_key, "Backup salvo na pasta do OneDrive"
            )
        )
        worker.succeeded.connect(
            lambda _message: self.notification_center.add(
                f"backup:{owner_id}",
                "Backup concluído",
                "O histórico de Saltos foi salvo na pasta sincronizada do OneDrive.",
                "success",
            )
        )
        worker.succeeded.connect(
            lambda message: self.activity_log.add(
                "backup",
                "Backup concluído",
                f"{message} O OneDrive sincronizará o arquivo com a nuvem.",
                owner_id=owner_id,
                kind="success",
            )
        )
        worker.failed.connect(
            lambda message: self.warp_panel._set_status(
                f"Importação salva localmente, mas o backup falhou: {message}", "error"
            )
        )
        worker.failed.connect(
            lambda message: self.sync_manager.fail(
                sync_key, "Falha no backup do OneDrive", details=message
            )
        )
        worker.failed.connect(
            lambda message: self.notification_center.add(
                f"backup:{owner_id}",
                "Erro no backup",
                f"Os dados locais estão seguros, mas o OneDrive falhou: {message}",
                "error",
            )
        )
        worker.failed.connect(
            lambda message: self.activity_log.add(
                "backup",
                "Falha no backup do OneDrive",
                message,
                owner_id=owner_id,
                kind="error",
            )
        )
        worker.finished.connect(lambda: self._release_drive_worker(worker))
        worker.start()

    def _release_drive_worker(self, worker: OneDriveWorker) -> None:
        self.drive_workers.discard(worker)
        worker.deleteLater()

    def _load_saved_uid(self, *, force: bool = False) -> None:
        self.page_stack.setCurrentIndex(4)
        for button, _icon, _text in self.nav_buttons:
            button.setChecked(False)
        self._refresh_account_page()
        user = self.auth_service.current_user
        if user is None or not user.game_uid:
            return
        self.pending_account_target = "account"
        self.account_copy_error.setVisible(False)
        self.account_status.setObjectName("statusInfo")
        self.account_status.setText("Carregando sua conta principal…")
        self.account_status.style().unpolish(self.account_status)
        self.account_status.style().polish(self.account_status)
        self.enka_client.fetch_account(user.game_uid, force=force)

    def start_initial_account_sync(self) -> bool:
        user = self.auth_service.current_user
        if user is None or not user.game_uid or self.enka_client.is_busy:
            return False
        self._initial_account_sync_active = True
        self.pending_account_target = "auto_account"
        self.account_copy_error.setVisible(False)
        self.account_status.setObjectName("statusInfo")
        self.account_status.setText("Sincronizando sua conta automaticamente…")
        self.account_status.style().unpolish(self.account_status)
        self.account_status.style().polish(self.account_status)
        self.enka_client.fetch_account(user.game_uid, force=True)
        return True

    def refresh_loaded_account(self) -> None:
        user = self.auth_service.current_user
        if user is None or not user.game_uid:
            self.set_status("Defina sua UID principal nas configurações.", "error")
            return
        self.pending_account_target = "own_builds"
        self.set_status("Atualizando personagens e relíquias da sua conta…")
        self.enka_client.fetch_account(user.game_uid, force=True)

    def _refresh_auth_sidebar(self) -> None:
        user = self.auth_service.current_user
        logged_in = user is not None
        self.auth_guest_button.setVisible(not logged_in)
        self.auth_user_frame.setVisible(logged_in)
        self.auth_avatar.clear_image()
        if user is not None:
            self.auth_username.setText(user.username)
            self.auth_avatar.setText(user.username[:1].upper())
            self.auth_user_frame.setToolTip("Abrir dashboard da conta")
        set_button_icon(self.auth_guest_button, "profile")
        self._update_sidebar_profile_layout()
        if hasattr(self, "warp_panel"):
            self.warp_panel.set_user(user)
            self._check_soft_pity_notifications()
        if hasattr(self, "planner_panel"):
            self.planner_panel.set_user(user)
        if hasattr(self, "relic_inventory_panel"):
            self.relic_inventory_panel.set_user(user)
        if hasattr(self, "friends_panel"):
            self.friends_panel.set_user(user)
        if hasattr(self, "build_history_bar"):
            self._refresh_build_history()
        if hasattr(self, "add_friend_button"):
            self._refresh_friend_action()
        if hasattr(self, "account_page"):
            if user is None or self.own_account_user_id != user.id:
                self.own_account = None
                self.own_account_user_id = None
            self._refresh_account_page()

    def _update_sidebar_profile_layout(self) -> None:
        expanded = self.sidebar_expanded
        self.auth_guest_button.setText("Entrar / Cadastrar" if expanded else "")
        self.auth_user_info.setVisible(expanded)
        self.auth_avatar.setVisible(expanded)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if watched in (getattr(self, "auth_user_frame", None), getattr(self, "auth_avatar", None), getattr(self, "auth_user_info", None)):
                self._load_saved_uid()
                return True
        return super().eventFilter(watched, event)

    def _open_own_character_builds(self, character_id: str) -> None:
        user = self.auth_service.current_user
        account = self.own_account
        if user is None or account is None or account.uid != user.game_uid or self.own_account_user_id != user.id:
            return
        self.build_source = "own"
        self.display_account(account)
        self._show_build_content(bool(account.characters))
        for index, character in enumerate(account.characters):
            if character.avatar_id == character_id:
                self.character_list.setCurrentRow(index)
                break

    def _open_own_account_builds(self) -> None:
        user = self.auth_service.current_user
        if user is None:
            self.build_source = None
            self._show_build_content(False)
            self.set_status(
                "Entre em um perfil para carregar seus personagens e benchmarks.",
                "error",
            )
            return
        if not user.game_uid:
            self.build_source = None
            self._show_build_content(False)
            self.set_status(
                "Defina sua UID principal na engrenagem do perfil.", "error"
            )
            return
        if (
            self.own_account is not None
            and self.own_account_user_id == user.id
            and self.own_account.uid == user.game_uid
        ):
            self._open_own_character_builds(self.current_character_id)
            return
        self.pending_account_target = "own_builds"
        self.build_source = "own"
        self._show_build_content(False)
        self.set_status("Carregando seus personagens e benchmarks…")
        self.enka_client.fetch_account(user.game_uid)

    def _refresh_dashboard(self) -> None:
        self.account_dashboard.refresh(
            self.auth_service.current_user, self.own_account,
            self.warp_panel.database, self.relic_database, self.benchmark_engine,
        )

    def _refresh_account_page(self) -> None:
        user = self.auth_service.current_user
        if user is None or self.own_account_user_id != user.id or (self.own_account and self.own_account.uid != user.game_uid):
            self.own_account = None
            self.own_account_user_id = None
        self._refresh_dashboard()
        if self.own_account is None:
            self.account_profile_avatar.clear_image()
            self.auth_avatar.clear_image()
            self.account_profile_name.setText(user.username if user else "Conta não carregada")
            self.account_profile_uid.setText(f"UID {user.game_uid}" if user and user.game_uid else "—")
            self.account_profile_signature.clear()
            self.account_profile_meta.setText("Defina sua UID principal pela engrenagem do perfil.")
        if user is None:
            self.account_load_button.setEnabled(False)
            self.account_status.setText("Entre ou crie um perfil para abrir Conta.")
            return
        self.account_load_button.setEnabled(bool(user.game_uid))
        if self.own_account is not None and self.own_account_user_id == user.id:
            self._refresh_own_profile_icon()
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
        elif destination == "Novidades":
            self.page_stack.setCurrentWidget(self.whats_new_panel)
            self._mark_whats_new_seen()
        elif destination == "Diagnóstico":
            self.page_stack.setCurrentWidget(self.diagnostics_panel)
            self.diagnostics_panel.refresh()
        elif destination == "Conta":
            self._open_own_account_builds()
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
        self.sync_manager.begin(key, message)
        QTimer.singleShot(
            0, lambda: self._finish_loading_operation(key, operation)
        )

    def _finish_loading_operation(
        self, key: str, operation: Callable[[], None]
    ) -> None:
        try:
            operation()
        finally:
            self.sync_manager.finish(key)

    def _warp_busy_changed(self, busy: bool) -> None:
        if busy:
            self.sync_manager.begin(
                "warp-import",
                "Importando e organizando o histórico de Saltos…",
                retryable=True,
            )
        else:
            self.sync_manager.finish("warp-import", "Saltos sincronizados")

    def _warp_import_failed(self, message: str) -> None:
        self.sync_manager.fail(
            "warp-import",
            "Falha ao importar o histórico de Saltos",
            details=message,
        )

    def _record_warp_import(
        self, owner_id: int, added: int, total: int, source: str
    ) -> None:
        self.activity_log.add(
            "warps",
            "Histórico de Saltos importado",
            f"{added} novo{'s' if added != 1 else ''} de {total} registro{'s' if total != 1 else ''} lido{'s' if total != 1 else ''} · {source}.",
            owner_id=owner_id,
            kind="success",
        )

    def _catalog_sync_changed(self, busy: bool, message: str) -> None:
        if busy:
            self.sync_manager.begin("catalog", message, retryable=True)
        elif message.startswith("Falha"):
            self.sync_manager.fail("catalog", message, details=message)
        else:
            self.sync_manager.finish("catalog", message)

    def _check_catalog_version(self) -> None:
        if self.catalog_version_worker and self.catalog_version_worker.isRunning():
            return
        worker = CatalogVersionCheckWorker(self)
        self.catalog_version_worker = worker
        worker.succeeded.connect(self._catalog_version_checked)
        worker.finished.connect(self._catalog_version_check_finished)
        worker.start()

    def _catalog_version_checked(self, outdated: bool, sha: str) -> None:
        if outdated:
            self.notification_center.add(
                "catalog-outdated",
                "Catálogo desatualizado",
                f"Há novos dados do jogo disponíveis · versão {sha[:8]}.",
                "warning",
            )
        else:
            self.notification_center.remove("catalog-outdated")

    def _catalog_version_check_finished(self) -> None:
        if self.catalog_version_worker:
            self.catalog_version_worker.deleteLater()
        self.catalog_version_worker = None

    def _catalog_updated(self, sha: str) -> None:
        self.notification_center.remove("catalog-outdated")
        self.activity_log.add(
            "catalog",
            "Catálogo atualizado",
            f"Dados do jogo atualizados para a versão {sha[:8]}.",
            kind="success",
        )

    def _check_soft_pity_notifications(self) -> None:
        if not hasattr(self, "warp_panel"):
            return
        from app.warp.statistics import pity_state

        panel = self.warp_panel
        categories = {
            "1": ("Banner permanente", 70, 90),
            "11": ("Evento de personagem", 70, 90),
            "12": ("Evento de Cone de Luz", 60, 80),
            "21": ("Colaboração de personagem", 70, 90),
            "22": ("Colaboração de Cone de Luz", 60, 80),
        }
        for gacha_type, (name, alert_at, cap) in categories.items():
            key = f"soft-pity:{panel.owner_id}:{panel.current_uid}:{gacha_type}"
            summary = panel.current_summaries.get(gacha_type)
            if summary is not None:
                pity = summary.five_star_pity
            else:
                pity = pity_state(
                    panel.current_records,
                    {gacha_type},
                    panel._standard_ids(gacha_type),
                ).five_star
            if panel.owner_id is not None and panel.current_uid and alert_at <= pity < cap:
                message = f"{name}: pity {pity}/{cap}, perto da faixa de soft pity."
                current = next(
                    (item for item in self.notification_center.items if item.key == key),
                    None,
                )
                if current is None or current.message != message:
                    self.notification_center.add(
                        key, "Pity próximo do soft pity", message, "warning"
                    )
            else:
                self.notification_center.remove(key)

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
        animate_width(self.sidebar, 230 if expanded else 62)
        self.sidebar_toggle.setText("")
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
            button.setText(text if expanded else "")
        self._update_sidebar_profile_layout()
        self._render_sync_status()

    def _sync_status_changed(self, state: str, message: str, count: int) -> None:
        self.sync_state = state
        self.sync_message = message
        self.sync_task_count = count
        self._render_sync_status()

    def _retry_background_task(self, key: str) -> None:
        """Repete a operação que originou uma falha na central de tarefas."""
        family = key.split(":", 1)[0]
        if family == "account":
            self.refresh_loaded_account()
        elif family == "catalog":
            self.catalog_panel.synchronize()
        elif family == "warp-import":
            self.warp_panel.import_automatically()
        elif family == "onedrive-backup":
            try:
                owner_id = int(key.split(":", 1)[1])
            except (IndexError, ValueError):
                return
            self._backup_warps_to_onedrive(owner_id)
        elif family == "update-check":
            self.check_for_updates(manual=True)
        elif family == "benchmark":
            request_key = key.split(":", 1)[1] if ":" in key else ""
            request_parts = request_key.split(":", 2)
            character_id = request_parts[1] if len(request_parts) > 1 else ""
            character = next(
                (
                    item
                    for item in self.current_characters
                    if str(item.avatar_id) == character_id
                ),
                self._current_character(),
            )
            if character is not None:
                self._display_benchmark(character)

    def _advance_sync_spinner(self) -> None:
        if self.sync_state != "syncing":
            return
        self.sync_spinner_frame = (self.sync_spinner_frame + 1) % 4
        self._render_sync_status()

    def _render_sync_status(self) -> None:
        if not hasattr(self, "sync_status"):
            return
        if self.sync_state == "syncing":
            icon = ("◌", "◔", "◑", "◕")[self.sync_spinner_frame]
        else:
            icon = {"success": "✓", "error": "!"}.get(self.sync_state, "●")
        suffix = (
            f" · {self.sync_task_count} tarefas" if self.sync_task_count > 1 else ""
        )
        full_message = f"{self.sync_message}{suffix}"
        self.sync_status.setText(
            f"{icon}  {full_message}" if self.sidebar_expanded else icon
        )
        self.sync_status.setToolTip(
            f"{full_message}\nClique para abrir as tarefas em segundo plano."
        )
        self.sync_status.setProperty("status", self.sync_state)
        self.sync_status.style().unpolish(self.sync_status)
        self.sync_status.style().polish(self.sync_status)

    def _build_selector(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("selectorPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(7)
        character_row = QHBoxLayout()
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
        character_row.addWidget(title)
        character_row.addWidget(self.character_list, 1)
        layout.addLayout(character_row)
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

        header = QHBoxLayout()
        title = QLabel("RELÍQUIAS EQUIPADAS")
        title.setObjectName("sectionTitle")
        self.relic_count = QLabel("0/6")
        self.relic_count.setObjectName("badge")
        header.addWidget(title)
        header.addWidget(ContextHelpButton(*RELIC_GRADE_HELP))
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
        self.relic_empty = QLabel("As relíquias do personagem aparecerão aqui.")
        self.relic_empty.setObjectName("muted")
        self.relic_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.relic_grid.addWidget(self.relic_empty, 0, 0, 1, 2)
        self.relic_scroll.setWidget(content)
        outer.addWidget(self.relic_scroll, 1)
        return frame

    def _build_build_history_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("buildHistoryPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        self.build_history_bar = BuildHistoryBar(wide=True)
        self.build_history_bar.save_requested.connect(self.save_current_build)
        self.build_history_bar.export_requested.connect(self.export_current_build)
        self.build_history_bar.compare_requested.connect(self.compare_saved_build)
        self.build_history_bar.delete_requested.connect(self.delete_saved_build)
        layout.addWidget(self.build_history_bar)
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
        self.uid_input.setEnabled(True)
        self.search_button.setEnabled(True)
        user = self.auth_service.current_user
        self.account_load_button.setEnabled(
            not loading and bool(user and user.game_uid)
        )
        self.header_refresh_button.setEnabled(not loading)
        self.header_refresh_button.setText(
            "Atualizando…" if loading and self.build_source == "own"
            else "↻  Atualizar conta"
        )
        self.search_button.setText("Pesquisar UID")
        if loading:
            self.account_sync_failed = False
            self.sync_manager.begin(
                "account",
                "Consultando personagens, builds e relíquias…",
                retryable=True,
            )
        else:
            if self.account_sync_failed:
                self.account_sync_failed = False
            else:
                self.sync_manager.finish("account", "Conta sincronizada")
            if self._initial_account_sync_active:
                self._initial_account_sync_active = False
                self.initial_account_sync_finished.emit()

    def _request_failed(self, message: str) -> None:
        self.account_sync_failed = True
        self.sync_manager.fail(
            "account", "Falha ao sincronizar a conta", details=message
        )
        user = self.auth_service.current_user
        if user is not None and self.pending_account_target in {
            "account", "own_builds", "auto_account"
        }:
            self.activity_log.add(
                "account",
                "Falha ao sincronizar a conta",
                message,
                owner_id=user.id,
                kind="error",
            )
        if self.pending_account_target in {"account", "auto_account"}:
            self.account_status.setObjectName("statusError")
            self.account_status.setText(message)
            self.account_copy_error.setVisible(True)
            self.account_status.style().unpolish(self.account_status)
            self.account_status.style().polish(self.account_status)
        else:
            self.set_status(message, "error")

    def _account_loaded(self, account: AccountSummary, message: str) -> None:
        self.account_copy_error.setVisible(False)
        self._capture_relic_inventory(account)
        if self.pending_account_target in {"account", "own_builds", "auto_account"}:
            user = self.auth_service.current_user
            if user is None or account.uid != user.game_uid:
                return
            automatic = self.pending_account_target == "auto_account"
            self.activity_log.add(
                "account",
                "Conta sincronizada" if account.characters else "Conta sem personagens públicos",
                f"{len(account.characters)} personagem{'s' if len(account.characters) != 1 else ''} carregado{'s' if len(account.characters) != 1 else ''} da UID principal.",
                owner_id=user.id,
                kind="success" if account.characters else "warning",
            )
            self.own_account = account
            self.own_account_user_id = user.id
            self._render_own_account(account)
            self._refresh_dashboard()
            if self.pending_account_target == "own_builds":
                self._open_own_character_builds(self.current_character_id)
            if self.pending_account_target == "own_builds":
                for button, _icon, text in self.nav_buttons:
                    button.setChecked(text == "Conta")
            elif self.pending_account_target == "account":
                for button, _icon, _text in self.nav_buttons:
                    button.setChecked(False)
            self.account_status.setObjectName(
                "statusSuccess" if account.characters else "statusError"
            )
            self.account_status.setText(message)
            self.account_status.style().unpolish(self.account_status)
            self.account_status.style().polish(self.account_status)
            if not automatic and self.pending_account_target != "account":
                self.set_status(
                    "Seus personagens e benchmarks foram atualizados.",
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
        before = {
            item.fingerprint: item.current_character_id
            for item in self.relic_database.relics(user.id, account.uid)
            if item.current_character_id
        }
        self.relic_database.sync_account(user.id, account, self.benchmark_engine)
        after = {
            item.fingerprint: item.current_character_id
            for item in self.relic_database.relics(user.id, account.uid)
            if item.current_character_id
        }
        if before and before != after:
            added = len(after.keys() - before.keys())
            removed = len(before.keys() - after.keys())
            moved = sum(
                before[key] != after[key] for key in before.keys() & after.keys()
            )
            details = []
            if added:
                details.append(f"{added} nova{'s' if added != 1 else ''}")
            if removed:
                details.append(f"{removed} removida{'s' if removed != 1 else ''}")
            if moved:
                details.append(
                    f"{moved} trocada{'s' if moved != 1 else ''} de personagem"
                )
            self.notification_center.add(
                f"relics:{user.id}:{account.uid}",
                "Relíquias alteradas",
                "Após atualizar a conta: " + ", ".join(details) + ".",
                "info",
            )
            total_changes = added + removed + moved
            self.activity_log.add(
                "relics",
                f"{total_changes} relíquia{'s' if total_changes != 1 else ''} alterada{'s' if total_changes != 1 else ''}",
                "Após atualizar a conta: " + ", ".join(details) + ".",
                owner_id=user.id,
            )
        self.relic_inventory_panel.mark_dirty()

    def _render_own_account(self, account: AccountSummary) -> None:
        self.account_profile_name.setText(account.nickname)
        self.account_profile_uid.setText(f"UID {account.uid}")
        self.account_profile_meta.setText(
            f"Nível {account.level} · Equilíbrio {account.world_level} · "
            f"{account.achievement_count} conquistas · {len(account.characters)} personagens públicos"
        )
        self.account_profile_signature.setText(account.signature)
        self._refresh_own_profile_icon()

    def _refresh_own_profile_icon(self) -> None:
        user = self.auth_service.current_user
        account = self.own_account
        self.account_profile_avatar.clear_image()
        self.auth_avatar.clear_image()
        if user is None or account is None or self.own_account_user_id != user.id or account.uid != user.game_uid:
            return
        if account.profile_icon_url:
            self.image_loader.load(
                account.profile_icon_url,
                lambda pixmap, owner=user.id, uid=account.uid, url=account.profile_icon_url:
                    self._set_own_profile_icon_if_current(owner, uid, url, pixmap),
            )

    def _set_own_profile_icon_if_current(
        self, owner_id: int, uid: str, url: str, pixmap: QPixmap,
    ) -> None:
        user = self.auth_service.current_user
        account = self.own_account
        if (
            user is not None and user.id == owner_id and user.game_uid == uid
            and self.own_account_user_id == owner_id and account is not None
            and account.uid == uid and account.profile_icon_url == url
        ):
            self.account_profile_avatar.set_image(pixmap)
            self.auth_avatar.set_image(pixmap)

    def set_status(self, message: str, kind: str = "info") -> None:
        object_name = {"success": "statusSuccess", "error": "statusError"}.get(
            kind, "statusInfo"
        )
        self.status_label.setObjectName(object_name)
        self.status_label.setText(message)
        self.copy_error_button.setVisible(kind == "error")
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

    def _show_character_details(self, row: int) -> None:
        if row < 0 or row >= len(self.current_characters):
            return
        character = self.current_characters[row]
        self.current_character_id = character.avatar_id
        self._refresh_build_history()
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
            card = RelicCard(relic, rating, expand_vertical=True)
            self.current_relic_cards.append(card)
            self.image_loader.load(relic.icon_url, card.icon.set_image)
        self._reflow_relic_cards()

    def _reflow_relic_cards(self) -> None:
        if not self.current_relic_cards:
            return
        while self.relic_grid.count():
            self.relic_grid.takeAt(0)
        for row in range(6):
            self.relic_grid.setRowStretch(row, 0)
        available_width = self.relics_panel.width() - 24
        columns = 2 if available_width >= 417 else 1
        self.relic_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            if columns == 2 else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        for index, card in enumerate(self.current_relic_cards):
            self.relic_grid.addWidget(card, index // columns, index % columns)
        used_rows = (len(self.current_relic_cards) + columns - 1) // columns
        for row in range(used_rows):
            self.relic_grid.setRowStretch(row, 1)
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
            snapshots, logged_in=self.auth_service.current_user is not None
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
        try:
            self.build_history_database.save(
                owner_id, uid, character_id, character.name, payload
            )
        except (ValueError, RuntimeError) as error:
            self.set_status(str(error), "error")
            return
        self._refresh_build_history()
        self.set_status(
            f"Build de {character.name} salva com o DPS Benchmark atual.", "success"
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
        sync_key = f"benchmark:{cache_key}"
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
                self.failed_sync_tasks.add(sync_key)
                self.sync_manager.finish(sync_key, "Benchmark indisponível para esta build")
                self.unsupported_benchmark_characters.add(character_id)
                result = self.benchmark_results.get(character_id)
                if result is not None:
                    self._mark_benchmark_unsupported(result)
                    self._render_benchmark(result)
                return
            self.benchmark_card.set_engine_error(message)
            self.set_status(f"Motor Fribbels indisponível: {message}", "error")
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
