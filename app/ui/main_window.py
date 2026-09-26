from __future__ import annotations

from collections.abc import Callable
import time

from PySide6.QtCore import QEvent, QSettings, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMainWindow, QMenu, QPushButton, QSizePolicy, QSizeGrip, QScrollArea,
    QSystemTrayIcon, QVBoxLayout, QWidget,
)

from app.api.enka_client import AccountFetchError, AccountFetchWorker, EnkaClient
from app.activity_log import ActivityLog
from app.background import BackgroundSettings
from app.auth import AuthService
from app.benchmark import BenchmarkEngine
from app.benchmark.fribbels_client import FribbelsBenchmarkWorker
from app.build_history import BuildHistoryDatabase
from app.catalog import CatalogVersionCheckWorker
from app.cloud import OneDriveWorker
from app.config import APP_HOME_BACKGROUND, APP_ICON_ICO, APP_ICON_PNG, APP_VERSION
from app.models import AccountSummary, CharacterSummary
from app.performance import PERFORMANCE
from app.preferences import ExperienceSettings, apply_experience_preferences
from app.relics import RelicDatabase
from app.section_loading import LoadContext, RelicSyncWorker, SectionLoadController
from app.session_state import ResumeState, SessionStateStore
from app.sync_manager import BackgroundSyncManager
from app.uid_tabs import UidTabStore, UidTabWorkspace
from app.warp.reminder import import_reminder_due, reminder_interval_days, utc_now
from app.ui.activity_history import ActivityHistoryButton
from app.ui.auth_dialogs import AuthDialog, SettingsDialog
from app.ui.build_layout import BuildDetailSplitter, build_panel_proportions
from app.ui.catalog_panel import CatalogPanel
from app.ui.contextual_help import BUILD_SOURCE_HELP, ContextHelpButton
from app.ui.error_recovery import EnkaErrorRecoveryPanel
from app.ui.experience import (
    DiagnosticsPanel, ExperienceDialog, GuidedTourOverlay, TourStep,
    copy_error_details,
)
from app.ui.friends_panel import FriendsPanel
from app.ui.home_panel import HomePanel
from app.ui.icons import set_button_icon
from app.ui.image_loader import ImageLoader
from app.ui.loading import LoadingOverlay, load_icon_pixmap
from app.ui.main_accounts import AccountActions
from app.ui.main_backups import BackupActions
from app.ui.main_builds import BuildActions, ELEMENT_STATS, PRIMARY_STATS
from app.ui.main_updates import UpdateActions
from app.ui.motion import AnimatedStack as QStackedWidget, animate_width, install_motion
from app.ui.notifications import NotificationBell, NotificationCenter
from app.ui.planner_panel import PlannerPanel
from app.ui.rank_dialog import RankRedirectDialog
from app.ui.relic_inventory_panel import RelicInventoryPanel
from app.ui.section_loading import SectionStatus
from app.ui.task_center import BackgroundTaskButton
from app.ui.uid_tabs import UidTabsWidget
from app.ui.warp_panel import WarpPanel
from app.ui.whats_new import WhatsNewPanel
from app.ui.widgets import AvatarLabel, RelicCard, StatRow
from app.updater import PreparedUpdate, ReleaseInfo, UpdateCheckWorker, UpdateDownloadWorker
from app.whats_new import WhatsNewSettings


BUILD_SPLITTER_MIN_HEIGHT = 700


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


class MainWindow(AccountActions, BuildActions, BackupActions, UpdateActions, QMainWindow):
    initial_account_sync_finished = Signal()

    def __init__(self) -> None:
        window_started_at = time.perf_counter()
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("Astral Optimizer")
        icon_path = APP_ICON_ICO if APP_ICON_ICO.is_file() else APP_ICON_PNG
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1280, 800)
        self.setMinimumSize(900, 620)

        self.enka_client = EnkaClient(self)
        self.auth_service = AuthService()
        self.uid_tab_store = UidTabStore()
        initial_owner = (
            self.auth_service.current_user.id
            if self.auth_service.current_user is not None else 0
        )
        self.uid_workspace = UidTabWorkspace(self.uid_tab_store, initial_owner)
        self.resume_store = SessionStateStore()
        self._session_owner_id = initial_owner
        self._restoring_resume_state = False
        self._session_closed = False
        self._quit_requested = False
        self.background_settings = BackgroundSettings()
        self._tray_icon: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None
        self._resume_generation = 0
        self._resume_save_timer = QTimer(self)
        self._resume_save_timer.setSingleShot(True)
        self._resume_save_timer.setInterval(350)
        self._resume_save_timer.timeout.connect(self._save_resume_state)
        self._uid_tab_persist_timer = QTimer(self)
        self._uid_tab_persist_timer.setSingleShot(True)
        self._uid_tab_persist_timer.setInterval(400)
        self._uid_tab_persist_timer.timeout.connect(self.uid_workspace.persist)
        self.uid_tab_workers: dict[str, AccountFetchWorker] = {}
        self.uid_tab_errors: dict[str, AccountFetchError] = {}
        self.active_uid_tab = ""
        self._last_account_error: AccountFetchError | None = None
        self._last_failed_account_target = "account"
        self._build_recovery_mode = "uid_tab"
        self.activity_log = ActivityLog(self)
        self.notification_center = NotificationCenter(self)
        self._reminder_owner_id: int | None = None
        self.benchmark_engine = BenchmarkEngine()
        self.image_loader = ImageLoader(self)
        self.section_loading = SectionLoadController(self)
        self.section_statuses: dict[str, SectionStatus] = {}
        self.relic_sync_workers: set[RelicSyncWorker] = set()
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
        self._own_request_owner_id: int | None = None
        self._own_request_uid = ""
        self.sidebar_expanded = True
        self._sidebar_user_choice = False
        self._sidebar_auto_collapsed = False
        self.account_sync_failed = False
        self.failed_sync_tasks: set[str] = set()
        self.sync_manager = BackgroundSyncManager(self)
        self.sync_state = "idle"
        self.sync_message = "Sincronizado"
        self.sync_task_count = 0
        self.sync_spinner_frame = 0
        self.benchmark_workers: set[FribbelsBenchmarkWorker] = set()
        self.benchmark_tab_contexts: dict[str, tuple[int, str]] = {}
        self.benchmark_section_contexts: dict[str, LoadContext] = {}
        self.drive_workers: set[OneDriveWorker] = set()
        self.update_check_worker: UpdateCheckWorker | None = None
        self.catalog_version_worker: CatalogVersionCheckWorker | None = None
        self.update_download_worker: UpdateDownloadWorker | None = None
        self.prepared_update: PreparedUpdate | None = None
        self.settings_dialog: SettingsDialog | None = None
        self.update_check_manual = False
        self.update_prompt_open = False
        self._pending_update_release: ReleaseInfo | None = None
        self.benchmark_results = {}
        self.fribbels_cache: dict[str, dict[str, object]] = {}
        self.active_benchmark_ids: set[str] = set()
        self.unsupported_benchmark_characters: set[str] = set()
        self.team_settings = QSettings("Astral Optimizer", "Custom Teams")
        self.update_settings = QSettings("Astral Optimizer", "Updates")
        self.current_relic_cards: list[RelicCard] = []
        self._uid_relic_cards: dict[
            tuple[int, str, str], tuple[AccountSummary, list[RelicCard]]
        ] = {}
        self._visible_relic_key: tuple[int, str, str] | None = None
        self._visible_relic_account: AccountSummary | None = None
        self._uid_stat_rows: dict[
            tuple[int, str, str], tuple[AccountSummary, list[StatRow]]
        ] = {}
        self._visible_stat_key: tuple[int, str, str] | None = None
        self._visible_stat_account: AccountSummary | None = None
        self._uid_character_lists: dict[
            tuple[int, str], tuple[AccountSummary, QListWidget]
        ] = {}
        self._reuse_session_benchmark = False
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
        self._refresh_notification_preferences()
        self._configure_tray()
        self.section_loading.changed.connect(self._section_state_changed)
        self.section_loading.retry_requested.connect(self._retry_section)
        self._connect_resume_state_signals()
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
        QTimer.singleShot(0, self._check_warp_import_reminder)
        self._warp_reminder_timer = QTimer(self)
        self._warp_reminder_timer.setInterval(6 * 60 * 60 * 1000)
        self._warp_reminder_timer.timeout.connect(self._check_warp_import_reminder)
        self._warp_reminder_timer.start()
        QTimer.singleShot(2600, self._check_updates_automatically)
        QTimer.singleShot(3400, self._check_catalog_version)
        QTimer.singleShot(0, self._show_whats_new_if_needed)
        QTimer.singleShot(0, self._restore_resume_state)
        PERFORMANCE.record_duration("Montagem da janela", window_started_at)

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
        layout.setSpacing(6)
        layout.addLayout(self._build_header())
        layout.addWidget(self._build_uid_query_bar())
        self.uid_tabs_widget = UidTabsWidget()
        self.uid_tabs_widget.selected.connect(self._select_uid_tab)
        self.uid_tabs_widget.close_requested.connect(self._close_uid_tab)
        self.uid_tabs_widget.refresh_requested.connect(self._refresh_uid_tab)
        self.uid_tabs_widget.order_changed.connect(self._reorder_uid_tabs)
        layout.addWidget(self.uid_tabs_widget)

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
        self.build_enka_recovery = EnkaErrorRecoveryPanel()
        self.build_enka_recovery.retry_requested.connect(
            lambda: self._retry_enka_failure("build")
        )
        self.build_enka_recovery.continue_requested.connect(
            lambda: self._continue_with_saved_enka_data("build")
        )
        self.build_enka_recovery.connection_requested.connect(
            self._open_network_settings
        )
        self.build_enka_recovery.copy_requested.connect(self._copy_enka_error)
        layout.addWidget(self.build_enka_recovery)
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
        build_layout.setSpacing(12)
        self.selector_panel = self._build_selector()
        build_layout.addWidget(self.selector_panel)

        self.content_splitter = BuildDetailSplitter()
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
        self.content_splitter.setSizes([380, 220, 400])
        self.content_splitter.setStretchFactor(0, 38)
        self.content_splitter.setStretchFactor(1, 22)
        self.content_splitter.setStretchFactor(2, 40)
        self.content_splitter.composition_changed.connect(self._reflow_relic_cards)
        self.content_splitter.composition_changed.connect(self._refresh_detail_name_layout)
        self.content_splitter.setMinimumHeight(BUILD_SPLITTER_MIN_HEIGHT)
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
            "Abas e cache de UID": self.uid_tab_store.path,
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
        self._restore_uid_tabs_ui()

    def _build_uid_query_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("uidQueryBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(6)
        label = QLabel("CONSULTAR UID")
        label.setObjectName("uidQueryLabel")
        layout.addWidget(label)
        self.build_uid_input = QLineEdit()
        self.build_uid_input.setObjectName("uidQueryInput")
        self.build_uid_input.setPlaceholderText("Digite os 9 números da UID")
        self.build_uid_input.setMaxLength(9)
        self.build_uid_input.returnPressed.connect(self.search_uid)
        layout.addWidget(self.build_uid_input, 1)
        self.build_uid_search_button = QPushButton("Abrir em nova aba")
        self.build_uid_search_button.setObjectName("uidQueryButton")
        self.build_uid_search_button.clicked.connect(self.search_uid)
        layout.addWidget(self.build_uid_search_button)
        return frame


    def _make_section_status(self, section: str) -> SectionStatus:
        status = SectionStatus(section)
        status.retry_requested.connect(self.section_loading.request_retry)
        self.section_statuses[section] = status
        return status

    def _section_state_changed(self, section: str, state: object) -> None:
        status = self.section_statuses.get(section)
        if status is not None:
            status.set_state(state)
            if section in {"art", "relics", "benchmark"}:
                status.setVisible(state.status != "ready")

    def _load_context_for(self, uid: str) -> LoadContext:
        owner_id = self._uid_owner_id()
        current = self.section_loading.context
        if current.owner_id == owner_id and current.uid == uid:
            return current
        return self.section_loading.begin_context(owner_id, uid)

    def _mark_account_sections_pending(self, uid: str) -> LoadContext:
        context = self._load_context_for(uid)
        self.section_loading.pending("profile", "Atualizando perfil…", context)
        self.section_loading.pending(
            "characters", "Atualizando personagens…", context
        )
        return context

    def _track_own_request(self) -> None:
        user = self.auth_service.current_user
        if user is None or not user.game_uid:
            self._own_request_owner_id = None
            self._own_request_uid = ""
            return
        self._own_request_owner_id = user.id
        self._own_request_uid = user.game_uid

    def _retry_section(self, section: str, context: object) -> None:
        if not isinstance(context, LoadContext) or not self.section_loading.is_current(context):
            return
        if section in {"profile", "characters"}:
            if context.uid in self.uid_workspace.sessions:
                self._request_uid_tab(context.uid)
            else:
                self.refresh_loaded_account()
            return
        if section == "inventory" and self.own_account is not None:
            user = self.auth_service.current_user
            if user is not None:
                self._start_relic_inventory_sync(user.id, self.own_account)
            return
        character = self._current_character()
        if character is None:
            return
        if section == "art":
            self._load_character_art(character, context)
        elif section == "relics":
            self._display_relics(character, context=context)
        elif section == "benchmark":
            self._display_benchmark(character)

    def _build_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        profile = QFrame()
        profile.setObjectName("buildProfileHeader")
        profile_layout = QHBoxLayout(profile)
        profile_layout.setContentsMargins(9, 6, 9, 6)
        profile_layout.setSpacing(8)

        self.profile_header_avatar = AvatarLabel(46)
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
        self.profile_section_status = self._make_section_status("profile")
        identity.addWidget(self.profile_section_status)
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
                dialog.close_to_tray_changed.connect(self._configure_tray)
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
            dialog.close_to_tray_changed.connect(self._configure_tray)
            dialog.notification_changed.connect(self._refresh_notification_preferences)
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
                "O sino reúne avisos de catálogo, atualizações, backup, relíquias, soft pity e importação de Saltos. Escolha os tipos de aviso em Configurações > Notificações.",
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


    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if watched in (getattr(self, "auth_user_frame", None), getattr(self, "auth_avatar", None), getattr(self, "auth_user_info", None)):
                self._load_saved_uid()
                return True
        return super().eventFilter(watched, event)


    def _resume_scroll_widgets(self) -> dict[str, QWidget]:
        widgets: dict[str, QWidget] = {
            "builds": self.build_scroll,
            "builds.characters": self.character_list,
            "warps.page": self.warp_panel.page_scroll,
            "warps.banners": self.warp_panel.banner_scroll,
            "warps.recent": self.warp_panel.recent_list,
            "warps.table": self.warp_panel.table,
            "planner": self.planner_panel.scroll,
            "relics": self.relic_inventory_panel.scroll,
            "dashboard": self.account_page_scroll,
            "friends": self.friends_panel.scroll,
            "catalog.list": self.catalog_panel.scroll,
            "catalog.detail": self.catalog_panel.detail_scroll,
        }
        news_scroll = self.whats_new_panel.findChild(QScrollArea, "whatsNewScroll")
        if news_scroll is not None:
            widgets["whats_new"] = news_scroll
        return widgets

    def _connect_resume_state_signals(self) -> None:
        self.page_stack.currentChanged.connect(self._schedule_resume_save)
        for widget in self._resume_scroll_widgets().values():
            widget.verticalScrollBar().valueChanged.connect(self._schedule_resume_save)
            widget.horizontalScrollBar().valueChanged.connect(self._schedule_resume_save)
        combos = (
            self.warp_panel.account_selector,
            self.warp_panel.edition_selector,
            self.planner_panel.strategy,
            self.relic_inventory_panel.character_filter,
            self.relic_inventory_panel.status_filter,
            self.relic_inventory_panel.slot_filter,
            self.relic_inventory_panel.relic_set_filter,
            self.relic_inventory_panel.ornament_set_filter,
            self.relic_inventory_panel.sort_filter,
            self.catalog_panel.path_filter,
            self.catalog_panel.rarity_filter,
        )
        for combo in combos:
            combo.currentIndexChanged.connect(self._schedule_resume_save)
        self.catalog_panel.search.textChanged.connect(self._schedule_resume_save)
        self.catalog_panel.character_button.clicked.connect(self._schedule_resume_save)
        self.catalog_panel.cone_button.clicked.connect(self._schedule_resume_save)
        for button in self.warp_panel.banner_buttons.values():
            button.clicked.connect(self._schedule_resume_save)

    def _schedule_resume_save(self, *_args) -> None:
        if not self._restoring_resume_state and not self._session_closed:
            self._resume_save_timer.start()

    def _visible_page_id(self) -> str:
        widget = self.page_stack.currentWidget()
        if widget is self.whats_new_panel:
            return "whats_new"
        if widget is self.diagnostics_panel:
            return "diagnostics"
        index = self.page_stack.currentIndex()
        if index == 0:
            return "own_builds" if self.build_source == "own" else "builds"
        return {
            1: "warps", 2: "planner", 3: "relics", 4: "dashboard",
            5: "friends", 6: "home", 7: "catalog",
        }.get(index, "home")

    @staticmethod
    def _combo_value(combo) -> str:
        value = combo.currentData()
        return "" if value is None else str(value)

    def _capture_resume_state(self) -> ResumeState:
        self._capture_active_uid_tab()
        values = {
            "warps.uid": self.warp_panel.current_uid,
            "warps.banner": self.warp_panel.selected_gacha_type,
            "warps.edition": self._combo_value(self.warp_panel.edition_selector),
            "planner.strategy": self._combo_value(self.planner_panel.strategy),
            "relics.character": self._combo_value(self.relic_inventory_panel.character_filter),
            "relics.status": self._combo_value(self.relic_inventory_panel.status_filter),
            "relics.slot": self._combo_value(self.relic_inventory_panel.slot_filter),
            "relics.relic_set": self._combo_value(self.relic_inventory_panel.relic_set_filter),
            "relics.ornament_set": self._combo_value(self.relic_inventory_panel.ornament_set_filter),
            "relics.sort": self._combo_value(self.relic_inventory_panel.sort_filter),
            "catalog.mode": self.catalog_panel.mode,
            "catalog.search": self.catalog_panel.search.text(),
            "catalog.path": self._combo_value(self.catalog_panel.path_filter),
            "catalog.rarity": self._combo_value(self.catalog_panel.rarity_filter),
        }
        scrolls: dict[str, int] = {}
        for name, widget in self._resume_scroll_widgets().items():
            scrolls[f"{name}.v"] = widget.verticalScrollBar().value()
            scrolls[f"{name}.h"] = widget.horizontalScrollBar().value()
        uid = self.active_uid_tab if self.active_uid_tab in self.uid_workspace.sessions else ""
        return ResumeState(
            page=self._visible_page_id(),
            uid=uid,
            character_id=str(self.current_character_id or ""),
            values=values,
            scrolls=scrolls,
        )

    def _save_resume_state(self) -> None:
        if self._restoring_resume_state or self._session_closed:
            return
        self.resume_store.save(self._session_owner_id, self._capture_resume_state())

    @staticmethod
    def _restore_combo(combo, value: str) -> bool:
        if not value:
            return False
        for index in range(combo.count()):
            if str(combo.itemData(index)) == value:
                if combo.currentIndex() != index:
                    combo.setCurrentIndex(index)
                return True
        return False

    def _restore_resume_state(self) -> None:
        self._resume_generation += 1
        generation = self._resume_generation
        if not self.resume_store.exists(self._session_owner_id):
            return
        state = self.resume_store.load(self._session_owner_id)
        self._pending_resume_state = state
        self._restoring_resume_state = True
        QTimer.singleShot(
            30_000, lambda: self._expire_pending_resume_state(generation)
        )

        if state.uid and state.uid in self.uid_workspace.sessions:
            self.uid_workspace.select(state.uid)
        destinations = {
            "home": "InÃ­cio", "builds": "Builds", "own_builds": "Conta",
            "warps": "Saltos", "planner": "Planejador", "relics": "RelÃ­quias",
            "friends": "Amigos", "catalog": "Personagens e Cones",
            "diagnostics": "DiagnÃ³stico", "whats_new": "Novidades",
        }
        if state.page == "dashboard":
            self.page_stack.setCurrentIndex(4)
            self._refresh_account_page()
            for button, _icon, _text in self.nav_buttons:
                button.setChecked(False)
        else:
            self._navigate(destinations.get(state.page, "InÃ­cio"))
        self._apply_resume_state(state, generation, 0)

    def _apply_resume_state(
        self, state: ResumeState, generation: int, attempt: int
    ) -> None:
        if generation != self._resume_generation:
            return
        values = state.values
        warp_uid = values.get("warps.uid", "")
        if warp_uid and self._restore_combo(self.warp_panel.account_selector, warp_uid):
            self.warp_panel.current_uid = warp_uid
        banner = values.get("warps.banner", "")
        if banner in self.warp_panel.banner_buttons:
            self.warp_panel._select_banner(banner)
        self._restore_combo(self.warp_panel.edition_selector, values.get("warps.edition", ""))
        self._restore_combo(self.planner_panel.strategy, values.get("planner.strategy", ""))

        relic_filters = (
            (self.relic_inventory_panel.character_filter, "relics.character"),
            (self.relic_inventory_panel.status_filter, "relics.status"),
            (self.relic_inventory_panel.slot_filter, "relics.slot"),
            (self.relic_inventory_panel.relic_set_filter, "relics.relic_set"),
            (self.relic_inventory_panel.ornament_set_filter, "relics.ornament_set"),
            (self.relic_inventory_panel.sort_filter, "relics.sort"),
        )
        for combo, key in relic_filters:
            self._restore_combo(combo, values.get(key, ""))

        mode = values.get("catalog.mode", "")
        if mode in {"characters", "light_cones"} and self.catalog_panel.mode != mode:
            self.catalog_panel.set_mode(mode)
        search = values.get("catalog.search", "")
        if self.catalog_panel.search.text() != search:
            self.catalog_panel.search.setText(search)
        self._restore_combo(self.catalog_panel.path_filter, values.get("catalog.path", ""))
        self._restore_combo(self.catalog_panel.rarity_filter, values.get("catalog.rarity", ""))

        if state.character_id and self.current_characters:
            for row, character in enumerate(self.current_characters):
                if character.avatar_id == state.character_id:
                    self.character_list.setCurrentRow(row)
                    break

        final_attempt = attempt >= 4
        for name, widget in self._resume_scroll_widgets().items():
            for suffix, bar in (
                ("v", widget.verticalScrollBar()),
                ("h", widget.horizontalScrollBar()),
            ):
                position = state.scrolls.get(f"{name}.{suffix}", 0)
                if final_attempt or position <= bar.maximum():
                    bar.setValue(min(position, bar.maximum()))
        if final_attempt:
            self._restoring_resume_state = False
            public_session = self.uid_workspace.sessions.get(state.uid)
            waiting_for_data = (
                state.page == "own_builds" and self.own_account is None
            ) or (
                state.page == "builds"
                and bool(state.uid)
                and (public_session is None or public_session.account is None)
            )
            if not waiting_for_data:
                self._pending_resume_state = None
            return
        delays = (0, 80, 180, 360, 700)
        QTimer.singleShot(
            delays[attempt + 1],
            lambda: self._apply_resume_state(state, generation, attempt + 1),
        )

    def _expire_pending_resume_state(self, generation: int) -> None:
        if generation == self._resume_generation:
            self._pending_resume_state = None

    def _apply_pending_resume_after_data(self) -> None:
        state = getattr(self, "_pending_resume_state", None)
        if state is None:
            return
        self._apply_resume_state(state, self._resume_generation, 4)
        self._pending_resume_state = None

    def _navigate(self, destination: str) -> None:
        if hasattr(self, "relic_inventory_panel") and destination != "Relíquias":
            self.relic_inventory_panel.set_active(False)
        if hasattr(self, "catalog_panel") and destination != "Personagens e Cones":
            self.catalog_panel.set_active(False)
        if destination == "Saltos":
            self.page_stack.setCurrentIndex(1)
        elif destination == "Planejador":
            self.page_stack.setCurrentIndex(2)
        elif destination == "Relíquias":
            self.page_stack.setCurrentIndex(3)
            if self.relic_inventory_panel.has_cached_view:
                self.relic_inventory_panel.set_active(True)
            else:
                self._defer_with_loading(
                    "page", "Organizando suas relíquias salvas…",
                    lambda: self.relic_inventory_panel.set_active(True),
                )
        elif destination == "Amigos":
            self.page_stack.setCurrentIndex(5)
        elif destination == "Início":
            self.page_stack.setCurrentIndex(6)
        elif destination == "Personagens e Cones":
            self.page_stack.setCurrentIndex(7)
            if self.catalog_panel.has_cached_view:
                self.catalog_panel.set_active(True)
            else:
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
            user = self.auth_service.current_user
            if (
                user is not None
                and self.own_account is not None
                and self.current_account is self.own_account
                and self.own_account_user_id == user.id
                and self.own_account.uid == user.game_uid
                and self.build_source == "own"
            ):
                self.page_stack.setCurrentIndex(0)
            else:
                self._open_own_account_builds()
        else:
            if destination == "Builds":
                self._set_public_uid_controls_visible(True)
                selected_uid = self.uid_workspace.selected_uid
                if selected_uid:
                    session = self.uid_workspace.sessions.get(selected_uid)
                    if (
                        session is not None
                        and session.account is not None
                        and session.account is self.current_account
                        and self.active_uid_tab == selected_uid
                        and self.build_source == session.source
                        and not session.loading
                        and not session.error
                    ):
                        self.page_stack.setCurrentIndex(0)
                    else:
                        self._activate_uid_tab(selected_uid)
                else:
                    self.build_source = None
                    self._clear_public_build_display()
                    self.set_status(
                        "Nenhuma UID pesquisada. Use a busca acima para abrir uma aba."
                    )
            else:
                loaded = bool(self.current_characters) and self.build_source is not None
                self._show_build_content(loaded)
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
        state = self.warp_panel.database.import_reminder(owner_id) or {
            "started_at": utc_now(),
        }
        state["last_imported_at"] = utc_now()
        state["last_reminded_at"] = ""
        state["next_due_on"] = ""
        self.warp_panel.database.save_import_reminder(owner_id, state)
        self.notification_center.remove(f"warp-import-reminder:{owner_id}")

    def _check_warp_import_reminder(self) -> None:
        if not hasattr(self, "warp_panel"):
            return
        user = self.auth_service.current_user
        owner_id = user.id if user is not None else None
        if self._reminder_owner_id is not None and self._reminder_owner_id != owner_id:
            self.notification_center.remove(
                f"warp-import-reminder:{self._reminder_owner_id}"
            )
        self._reminder_owner_id = owner_id
        if owner_id is None:
            return
        database = self.warp_panel.database
        state = database.import_reminder(owner_id)
        if state is None:
            previous_import = self.activity_log.latest_warp_import_at(owner_id)
            state = {
                "started_at": previous_import or utc_now(),
                "last_imported_at": previous_import or "",
                "last_reminded_at": "",
            }
            database.save_import_reminder(owner_id, state)
        key = f"warp-import-reminder:{owner_id}"
        if not database.notification_preferences(owner_id).get("warp_reminder", True):
            self.notification_center.remove(key)
            return
        if import_reminder_due(state):
            days = reminder_interval_days(state)
            self.notification_center.add(
                key,
                "Hora de atualizar os Saltos",
                "Chegou a data escolhida para atualizar o histórico. Abra Saltos para importar."
                if state.get("next_due_on") else
                f"Chegou o prazo de {days} {'dia' if days == 1 else 'dias'} para "
                "atualizar o histórico. Abra Saltos para importar.",
                "info",
            )
            state["last_reminded_at"] = utc_now()
            state["next_due_on"] = ""
            database.save_import_reminder(owner_id, state)

    def _refresh_notification_preferences(self) -> None:
        if not hasattr(self, "warp_panel"):
            return
        user = self.auth_service.current_user
        preferences = (
            self.warp_panel.database.notification_preferences(user.id)
            if user is not None else {}
        )
        self.notification_center.set_preferences(preferences)
        self._check_warp_import_reminder()

    def _catalog_sync_changed(self, busy: bool, message: str) -> None:
        if busy:
            self.sync_manager.begin("catalog", message, retryable=True)
        elif message.startswith("Falha"):
            self.sync_manager.fail("catalog", message, details=message)
        else:
            self.sync_manager.finish("catalog", message)


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


    def toggle_sidebar(self) -> None:
        self._sidebar_user_choice = True
        self._sidebar_auto_collapsed = False
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

    def _fit_sidebar_to_window(self) -> None:
        if not hasattr(self, "sidebar"):
            return
        if self.width() <= 1050 and self.sidebar_expanded and not self._sidebar_user_choice:
            self.toggle_sidebar()
            self._sidebar_user_choice = False
            self._sidebar_auto_collapsed = True
            animation = getattr(self.sidebar, "_astral_width_animation", None)
            if animation is not None:
                animation.stop()
            self.sidebar.setFixedWidth(62)
        elif self.width() >= 1250 and self._sidebar_auto_collapsed:
            self.toggle_sidebar()
            self._sidebar_user_choice = False
            animation = getattr(self.sidebar, "_astral_width_animation", None)
            if animation is not None:
                animation.stop()
            self.sidebar.setFixedWidth(230)

    def _sync_status_changed(self, state: str, message: str, count: int) -> None:
        self.sync_state = state
        self.sync_message = message
        self.sync_task_count = count
        self._render_sync_status()

    def _retry_background_task(self, key: str) -> None:
        """Repete a operação que originou uma falha na central de tarefas."""
        family = key.split(":", 1)[0]
        if family == "account":
            self._retry_enka_failure(
                "account"
                if self._last_failed_account_target in {"account", "auto_account"}
                else "build"
            )
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
        elif family == "uid-tab":
            parts = key.split(":", 3)
            if len(parts) >= 3 and parts[2] in self.uid_workspace.sessions:
                self._request_uid_tab(parts[2])

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


    def set_status(self, message: str, kind: str = "info") -> None:
        self.status_bar.show()
        object_name = {"success": "statusSuccess", "error": "statusError"}.get(
            kind, "statusInfo"
        )
        self.status_label.setObjectName(object_name)
        self.status_label.setText(message)
        self.copy_error_button.setVisible(kind == "error")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)


    def _configure_tray(self) -> None:
        enabled = (
            self.background_settings.close_to_tray()
            and QSystemTrayIcon.isSystemTrayAvailable()
        )
        if enabled and self._tray_icon is None:
            tray = QSystemTrayIcon(self.windowIcon(), self)
            tray.setToolTip("Astral Optimizer")
            menu = QMenu(self)
            open_action = QAction("Abrir Astral Optimizer", menu)
            open_action.triggered.connect(self._restore_from_tray)
            exit_action = QAction("Sair do Astral Optimizer", menu)
            exit_action.triggered.connect(self._quit_from_tray)
            menu.addAction(open_action)
            menu.addSeparator()
            menu.addAction(exit_action)
            tray.setContextMenu(menu)
            tray.activated.connect(self._tray_activated)
            self._tray_menu = menu
            self._tray_icon = tray
        if self._tray_icon is not None:
            self._tray_icon.setVisible(enabled)
        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(not enabled)
        self.title_bar.close_button.setToolTip(
            "Manter na bandeja" if enabled else "Fechar"
        )

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        self._quit_requested = True
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        release = self._pending_update_release
        if release is not None:
            QTimer.singleShot(
                0, lambda current=release: self._show_update_available(current)
            )

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if (
            not self._quit_requested
            and self.background_settings.close_to_tray()
            and self._tray_icon is not None
            and self._tray_icon.isVisible()
        ):
            event.ignore()
            self.hide()
            return
        self._resume_save_timer.stop()
        self._uid_tab_persist_timer.stop()
        self._restoring_resume_state = False
        self._save_resume_state()
        self._capture_active_uid_tab()
        self.uid_workspace.persist()
        self._session_closed = True
        if self._tray_icon is not None:
            self._tray_icon.hide()
        super().closeEvent(event)

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
        self._fit_sidebar_to_window()
        if not hasattr(self, "content_splitter"):
            return
        self.content_splitter.reflow()
        QTimer.singleShot(0, self._reflow_relic_cards)
        QTimer.singleShot(0, self._refresh_detail_name_layout)
