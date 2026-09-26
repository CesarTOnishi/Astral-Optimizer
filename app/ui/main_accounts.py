"""Contas, abas de UID e sincronização de personagens."""
from __future__ import annotations

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidgetItem, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from app.api.enka_client import AccountFetchError, AccountFetchWorker, ensure_account_error
from app.benchmark import BenchmarkEngine
from app.models import AccountSummary
from app.section_loading import LoadContext, RelicSyncWorker
from app.uid_tabs import MAX_UID_TABS, UidTabLimitError, UidTabSession
from app.ui.account_dashboard import AccountDashboard
from app.ui.error_recovery import EnkaErrorRecoveryPanel
from app.ui.experience import copy_error_details
from app.ui.icons import set_button_icon
from app.ui.widgets import AvatarLabel, CharacterPortraitCard


class AccountActions:
    """Operações de contas e abas de UID ligadas ao estado da janela."""

    def _build_account_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("accountPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 9, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Sua conta")
        title.setObjectName("brandTitle")
        subtitle = QLabel(
            "Seus personagens, Saltos e relíquias em um só lugar."
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        heading = QHBoxLayout()
        heading.setSpacing(10)
        heading.addWidget(title)
        heading.addWidget(subtitle, 1, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(heading)

        card = QFrame()
        card.setObjectName("accountProfilePanel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(5)
        self.account_profile_avatar = AvatarLabel(58)
        self.account_profile_avatar.setObjectName("accountProfileAvatar")
        self.account_profile_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_profile_avatar.setFixedSize(58, 58)
        self.account_profile_name = QLabel("Conta não carregada")
        self.account_profile_name.setObjectName("detailName")
        self.account_profile_name.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.account_profile_name.setWordWrap(True)
        self.account_profile_name.setTextFormat(Qt.TextFormat.PlainText)
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
        identity_row.setSpacing(11)
        identity_row.addWidget(self.account_profile_avatar)
        identity = QVBoxLayout()
        identity.setSpacing(4)
        identity.addWidget(self.account_profile_name)
        identity.addWidget(self.account_profile_uid)
        identity.addWidget(self.account_profile_meta)
        identity.addWidget(self.account_profile_signature)
        identity_row.addLayout(identity, 1)
        identity_row.addWidget(self.account_load_button)
        card_layout.addLayout(identity_row)
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
        self.account_enka_recovery = EnkaErrorRecoveryPanel()
        self.account_enka_recovery.retry_requested.connect(
            lambda: self._retry_enka_failure("account")
        )
        self.account_enka_recovery.continue_requested.connect(
            lambda: self._continue_with_saved_enka_data("account")
        )
        self.account_enka_recovery.connection_requested.connect(
            self._open_network_settings
        )
        self.account_enka_recovery.copy_requested.connect(self._copy_enka_error)
        card_layout.addWidget(self.account_enka_recovery)
        layout.addWidget(card)
        self.inventory_section_status = self._make_section_status("inventory")
        layout.addWidget(self.inventory_section_status)
        self.account_dashboard = AccountDashboard(self.image_loader)
        layout.addWidget(self.account_dashboard)
        layout.addStretch(1)
        self.account_page_scroll = QScrollArea()
        self.account_page_scroll.setObjectName("accountPageScroll")
        self.account_page_scroll.setWidgetResizable(True)
        self.account_page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.account_page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.account_page_scroll.setWidget(page)
        return self.account_page_scroll

    def _load_saved_uid(self, *, force: bool = False) -> None:
        self.page_stack.setCurrentIndex(4)
        for button, _icon, _text in self.nav_buttons:
            button.setChecked(False)
        self._refresh_account_page()
        user = self.auth_service.current_user
        if user is None or not user.game_uid:
            return
        self._mark_account_sections_pending(user.game_uid)
        self.pending_account_target = "account"
        self.account_copy_error.setVisible(False)
        self.account_status.setObjectName("statusInfo")
        self.account_status.setText("Carregando sua conta principal…")
        self.account_status.style().unpolish(self.account_status)
        self.account_status.style().polish(self.account_status)
        self._track_own_request()
        self.enka_client.fetch_account(user.game_uid, force=force)

    def start_initial_account_sync(self) -> bool:
        user = self.auth_service.current_user
        if user is None or not user.game_uid or self.enka_client.is_busy:
            return False
        self._initial_account_sync_active = True
        self._mark_account_sections_pending(user.game_uid)
        self.pending_account_target = "auto_account"
        self.account_copy_error.setVisible(False)
        self.account_status.setObjectName("statusInfo")
        self.account_status.setText("Sincronizando sua conta automaticamente…")
        self.account_status.style().unpolish(self.account_status)
        self.account_status.style().polish(self.account_status)
        self._track_own_request()
        self.enka_client.fetch_account(user.game_uid, force=True)
        return True

    def refresh_loaded_account(self) -> None:
        user = self.auth_service.current_user
        if user is None or not user.game_uid:
            self.set_status("Defina sua UID principal nas configurações.", "error")
            return
        self.pending_account_target = "own_builds"
        self._mark_account_sections_pending(user.game_uid)
        self.set_status("Atualizando personagens e relíquias da sua conta…")
        self._track_own_request()
        self.enka_client.fetch_account(user.game_uid, force=True)

    def _refresh_auth_sidebar(self) -> None:
        user = self.auth_service.current_user
        next_owner_id = user.id if user is not None else 0
        if next_owner_id != self._session_owner_id:
            self._own_request_owner_id = None
            self._own_request_uid = ""
        if (
            next_owner_id != self._session_owner_id
            and hasattr(self, "page_stack")
            and not self._restoring_resume_state
        ):
            self._resume_save_timer.stop()
            self._save_resume_state()
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
            self._refresh_notification_preferences()
            self._check_soft_pity_notifications()
            self._check_warp_import_reminder()
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
        if hasattr(self, "uid_tabs_widget"):
            self._sync_uid_tab_owner()

    def _update_sidebar_profile_layout(self) -> None:
        expanded = self.sidebar_expanded
        self.auth_guest_button.setText("Entrar / Cadastrar" if expanded else "")
        self.auth_user_info.setVisible(expanded)
        self.auth_avatar.setVisible(expanded)

    def _open_own_character_builds(self, character_id: str) -> None:
        user = self.auth_service.current_user
        account = self.own_account
        if user is None or account is None or account.uid != user.game_uid or self.own_account_user_id != user.id:
            return
        self._capture_active_uid_tab()
        self.active_uid_tab = ""
        self._set_public_uid_controls_visible(False)
        self.build_enka_recovery.clear()
        self.build_source = "own"
        self.display_account(account)
        self._show_build_content(bool(account.characters))
        for index, character in enumerate(account.characters):
            if character.avatar_id == character_id:
                self.character_list.setCurrentRow(index)
                break

    def _open_own_account_builds(self) -> None:
        self._capture_active_uid_tab()
        self.active_uid_tab = ""
        self._set_public_uid_controls_visible(False)
        self.build_enka_recovery.clear()
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
        self._mark_account_sections_pending(user.game_uid)
        self._show_build_placeholders(user.game_uid)
        self.set_status("Carregando seus personagens e benchmarks…")
        self._track_own_request()
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

    def _uid_owner_id(self) -> int:
        user = self.auth_service.current_user
        return user.id if user is not None else 0

    def _restore_uid_tabs_ui(self) -> None:
        while self.uid_tabs_widget.tabs.count():
            self.uid_tabs_widget.tabs.removeTab(0)
        for session in self.uid_workspace.sessions.values():
            self.uid_tabs_widget.add_or_update(session.uid, session.title)
            self._load_uid_tab_avatar(session)
        selected = self.uid_workspace.selected_uid
        if selected:
            self.uid_tabs_widget.set_current_uid(selected, emit=False)
        self.uid_tabs_widget.setVisible(bool(self.uid_workspace.sessions))

    def _sync_uid_tab_owner(self) -> None:
        owner_id = self._uid_owner_id()
        if owner_id == self.uid_workspace.owner_id:
            return
        self._uid_tab_persist_timer.stop()
        self._capture_active_uid_tab()
        previous_owner = self.uid_workspace.owner_id
        for cached_owner, cached_uid in list(self._uid_character_lists):
            if cached_owner == previous_owner:
                self._drop_uid_character_list(cached_uid, owner_id=cached_owner)
                self._drop_uid_relic_cards(cached_uid, owner_id=cached_owner)
                self._drop_uid_stat_rows(cached_uid, owner_id=cached_owner)
        self._resume_generation += 1
        self._restoring_resume_state = False
        self._pending_resume_state = None
        self.active_uid_tab = ""
        self.uid_workspace.restore(owner_id)
        self._session_owner_id = owner_id
        if hasattr(self, "uid_tabs_widget"):
            self._restore_uid_tabs_ui()
            QTimer.singleShot(0, self._restore_resume_state)

    def _set_public_uid_controls_visible(self, visible: bool) -> None:
        self.build_uid_input.parentWidget().setVisible(visible)
        self.uid_tabs_widget.setVisible(visible and bool(self.uid_workspace.sessions))

    def _capture_active_uid_tab(self, *, persist: bool = True) -> None:
        session = self.uid_workspace.sessions.get(self.active_uid_tab)
        if (
            session is None
            or self.current_account is None
            or self.current_account.uid != session.uid
            or self.build_source not in {"manual", "friend"}
        ):
            return
        session.selected_character_id = self.current_character_id
        session.scroll_position = self.build_scroll.verticalScrollBar().value()
        session.benchmark_results = self.benchmark_results
        session.fribbels_cache = self.fribbels_cache
        session.unsupported_benchmark_characters = self.unsupported_benchmark_characters
        if persist:
            self.uid_workspace.persist()

    def _load_uid_tab_avatar(self, session: UidTabSession) -> None:
        if not session.avatar_url:
            return
        self.image_loader.load(
            session.avatar_url,
            lambda pixmap, uid=session.uid, url=session.avatar_url:
                self._set_uid_tab_avatar_if_current(uid, url, pixmap),
        )

    def _set_uid_tab_avatar_if_current(
        self, uid: str, url: str, pixmap: QPixmap
    ) -> None:
        session = self.uid_workspace.sessions.get(uid)
        if session is not None and session.avatar_url == url:
            self.uid_tabs_widget.update_avatar(uid, pixmap)

    def _open_public_uid(self, uid: str, *, source: str = "manual") -> None:
        uid = uid.strip()
        self._sync_uid_tab_owner()
        if (
            uid not in self.uid_workspace.sessions
            and len(self.uid_workspace.sessions) >= MAX_UID_TABS
        ):
            message = (
                f"O limite é de {MAX_UID_TABS} abas de UID. "
                "Feche uma aba para abrir outra."
            )
            self.set_status(message, "error")
            QMessageBox.information(self, "Limite de abas", message)
            return
        self._capture_active_uid_tab(persist=False)
        try:
            session, created = self.uid_workspace.open(uid, source=source)
        except UidTabLimitError as error:
            self.set_status(str(error), "error")
            QMessageBox.information(self, "Limite de abas", str(error))
            return
        if source == "friend":
            session.source = "friend"
            self.uid_workspace.persist()
        index = self.uid_tabs_widget.add_or_update(uid, session.title)
        self.uid_tabs_widget.tabs.setCurrentIndex(index)
        self.uid_tabs_widget.setVisible(True)
        if self.active_uid_tab != uid:
            self._activate_uid_tab(uid)
        if created or session.account is None:
            self._request_uid_tab(uid)

    def _select_uid_tab(self, uid: str) -> None:
        if uid:
            self._activate_uid_tab(uid)

    def _activate_uid_tab(self, uid: str) -> None:
        session = self.uid_workspace.sessions.get(uid)
        if session is None:
            self.active_uid_tab = ""
            self._clear_public_build_display()
            return
        if self.active_uid_tab != uid:
            self._capture_active_uid_tab(persist=False)
        self.uid_workspace.select(uid, persist=False)
        self._uid_tab_persist_timer.start()
        self.active_uid_tab = uid
        context = self._load_context_for(uid)
        self.build_source = session.source
        self._set_public_uid_controls_visible(True)
        self.uid_tabs_widget.set_current_uid(uid, emit=False)
        self.uid_tabs_widget.set_session_status(
            updated_at=session.updated_at,
            loading=session.loading,
            error=session.error,
        )
        self._build_recovery_mode = "uid_tab"
        if session.error:
            error = self.uid_tab_errors.get(session.uid) or ensure_account_error(
                session.error
            )
            self.build_enka_recovery.show_error(
                error, has_saved_data=session.account is not None
            )
            self.copy_error_button.setVisible(False)
        else:
            self.build_enka_recovery.clear()
        self.page_stack.setCurrentIndex(0)
        for button, _icon, text in self.nav_buttons:
            button.setChecked(text == "Builds")
        if session.account is None:
            self.section_loading.pending("profile", "Consultando perfil…", context)
            self.section_loading.pending(
                "characters", "Consultando personagens…", context
            )
            self._show_build_placeholders(uid)
            if session.loading:
                self.set_status(f"Consultando a UID {uid}…")
            elif session.error:
                self.set_status(session.error, "error")
            else:
                self.set_status(
                    "Nenhum dado salvo para esta UID. Use o botão atualizar para consultar.",
                    "error",
                )
            return
        self.benchmark_results = session.benchmark_results
        self.fribbels_cache = session.fribbels_cache
        self.unsupported_benchmark_characters = session.unsupported_benchmark_characters
        self._reuse_session_benchmark = True
        self.display_account(
            session.account,
            selected_character_id=session.selected_character_id,
            reset_benchmarks=False,
        )
        self._show_build_content(bool(session.account.characters))
        if session.error:
            error = self.uid_tab_errors.get(session.uid) or ensure_account_error(
                session.error
            )
            context = self.section_loading.context
            self.section_loading.fail(
                "profile", error.message, details=error.diagnostic_details,
                retryable=error.retryable, context=context,
            )
            self.set_status(
                f"{session.error} Os dados anteriores foram preservados.", "error"
            )
        else:
            self.status_bar.hide()
        QTimer.singleShot(
            0,
            lambda current_uid=uid, position=session.scroll_position:
                self._restore_uid_scroll(current_uid, position),
        )

    def _restore_uid_scroll(self, uid: str, position: int) -> None:
        if self.active_uid_tab == uid:
            self.build_scroll.verticalScrollBar().setValue(max(position, 0))

    def _clear_public_build_display(self) -> None:
        self._reuse_session_benchmark = False
        self.current_account = None
        self.current_uid = ""
        self.current_characters = []
        self.current_character_id = ""
        self._show_build_content(False)

    def _show_build_placeholders(self, uid: str) -> None:
        self._reuse_session_benchmark = False
        self.current_account = None
        self.current_uid = uid
        self.current_characters = []
        self.current_character_id = ""
        self.account_label.setText("Consultando conta…")
        self.profile_header_bio.setText("Os dados aparecerão por seção.")
        self.profile_header_meta.setText("Nível — · Equilíbrio — · — conquistas")
        self.profile_header_avatar.clear_image()
        self.copy_uid_button.setEnabled(False)
        self.character_list = self._own_character_list
        self.character_list_stack.setCurrentWidget(self.character_list)
        self.character_list.clear()
        self.detail_name.setText("Personagem")
        self.detail_rarity.setText("☆☆☆☆☆")
        self.level_badge.setText("NV. —")
        self.eidolon_badge.setText("E—")
        self.element_icon.clear()
        self.path_icon.clear()
        self.character_art.clear_image()
        self.art_caption.setText("Aguardando personagem")
        self.uid_caption.setText(f"UID {uid}")
        self.light_cone_banner.clear_image()
        self._clear_layout(self.stat_rows)
        self._clear_layout(self.relic_grid)
        placeholder = QLabel("As relíquias aparecerão assim que os dados chegarem.")
        placeholder.setObjectName("muted")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.relic_grid.addWidget(placeholder, 0, 0, 1, 2)
        context = self.section_loading.context
        self.section_loading.pending("art", "Aguardando personagem…", context)
        self.section_loading.pending("relics", "Aguardando relíquias…", context)
        self.section_loading.pending("benchmark", "Aguardando build…", context)
        self._show_build_content(True)

    def _close_uid_tab(self, uid: str) -> None:
        if uid not in self.uid_workspace.sessions:
            return
        if uid == self.active_uid_tab:
            self._capture_active_uid_tab()
        self._drop_uid_character_list(uid)
        self._drop_uid_relic_cards(uid)
        self._drop_uid_stat_rows(uid)
        self.uid_workspace.close(uid)
        self.uid_tab_errors.pop(uid, None)
        self.uid_tabs_widget.remove_uid(uid)
        self.active_uid_tab = ""
        next_uid = self.uid_workspace.selected_uid
        if next_uid:
            self.uid_tabs_widget.set_current_uid(next_uid, emit=False)
            self._activate_uid_tab(next_uid)
        else:
            self.uid_tabs_widget.setVisible(False)
            self._clear_layout(self.stat_rows)
            self._clear_layout(self.relic_grid)
            self.current_relic_cards = []
            self._visible_stat_key = None
            self._visible_stat_account = None
            self._visible_relic_key = None
            self._visible_relic_account = None
            self.benchmark_results = {}
            self.fribbels_cache = {}
            self.unsupported_benchmark_characters = set()
            self._clear_public_build_display()
            self.set_status("Nenhuma UID aberta. Pesquise uma UID para criar uma aba.")

    def _reorder_uid_tabs(self, ordered_uids: object) -> None:
        if isinstance(ordered_uids, list):
            self.uid_workspace.reorder([str(uid) for uid in ordered_uids])

    def _refresh_uid_tab(self, uid: str) -> None:
        if uid in self.uid_workspace.sessions:
            self._request_uid_tab(uid)

    def _request_uid_tab(self, uid: str) -> None:
        session = self.uid_workspace.sessions.get(uid)
        if session is None or session.loading:
            return
        token = self.uid_workspace.begin_request(uid)
        owner_id = self.uid_workspace.owner_id
        worker = AccountFetchWorker(uid, self)
        self.uid_tab_workers[uid] = worker
        worker.succeeded.connect(
            lambda account, owner=owner_id, current_uid=uid, request=token:
                self._uid_tab_account_ready(owner, current_uid, request, account)
        )
        worker.failed.connect(
            lambda message, owner=owner_id, current_uid=uid, request=token:
                self._uid_tab_account_failed(owner, current_uid, request, message)
        )
        worker.finished.connect(
            lambda current_uid=uid, current_worker=worker:
                self._uid_tab_worker_finished(current_uid, current_worker)
        )
        self.sync_manager.begin(
            f"uid-tab:{owner_id}:{uid}:{token}",
            f"Atualizando a UID {uid}…",
            retryable=True,
        )
        if self.active_uid_tab == uid:
            self._mark_account_sections_pending(uid)
            self.build_enka_recovery.clear()
            self.copy_error_button.setVisible(False)
            self.uid_tabs_widget.set_session_status(
                updated_at=session.updated_at, loading=True
            )
            self.set_status(f"Atualizando somente a UID {uid}…")
        worker.start()

    def _uid_tab_account_ready(
        self, owner_id: int, uid: str, token: int, account: AccountSummary
    ) -> None:
        sync_key = f"uid-tab:{owner_id}:{uid}:{token}"
        if owner_id != self.uid_workspace.owner_id:
            self.sync_manager.finish(sync_key, "Consulta descartada após trocar de perfil")
            return
        if not self.uid_workspace.complete_request(uid, token, account):
            self.sync_manager.finish(sync_key, "Resposta antiga descartada")
            return
        session = self.uid_workspace.sessions[uid]
        self.uid_tab_errors.pop(uid, None)
        self.uid_tabs_widget.add_or_update(uid, session.title)
        self._load_uid_tab_avatar(session)
        self.sync_manager.finish(sync_key, f"UID {uid} atualizada")
        if session.source == "friend" and self.auth_service.current_user is not None:
            try:
                self.auth_service.add_friend(
                    account.uid,
                    account.nickname,
                    account.level,
                    account.world_level,
                    account.profile_icon_url,
                )
            except ValueError:
                pass
            self.friends_panel.refresh()
        if self.active_uid_tab == uid:
            self._activate_uid_tab(uid)
            QTimer.singleShot(0, self._apply_pending_resume_after_data)

    def _uid_tab_account_failed(
        self, owner_id: int, uid: str, token: int, failure: object
    ) -> None:
        error = ensure_account_error(failure)
        message = error.message
        sync_key = f"uid-tab:{owner_id}:{uid}:{token}"
        if owner_id != self.uid_workspace.owner_id:
            self.sync_manager.finish(sync_key, "Consulta descartada após trocar de perfil")
            return
        if not self.uid_workspace.fail_request(uid, token, message):
            self.sync_manager.finish(sync_key, "Resposta antiga descartada")
            return
        self.uid_tab_errors[uid] = error
        self.sync_manager.fail(
            sync_key,
            f"Falha ao atualizar a UID {uid}",
            details=error.diagnostic_details,
            retryable=error.retryable,
        )
        if self.active_uid_tab == uid:
            session = self.uid_workspace.sessions[uid]
            self.uid_tabs_widget.set_session_status(
                updated_at=session.updated_at, error=message
            )
            suffix = " Os dados anteriores foram preservados." if session.account else ""
            self.set_status(f"{message}{suffix}", "error")
            self.copy_error_button.setVisible(False)
            self._build_recovery_mode = "uid_tab"
            self.build_enka_recovery.show_error(
                error, has_saved_data=session.account is not None
            )
            context = self._load_context_for(uid)
            self.section_loading.fail(
                "profile", error.message, details=error.diagnostic_details,
                retryable=error.retryable, context=context,
            )
            self.section_loading.fail(
                "characters", "Personagens não foram atualizados.",
                details=error.diagnostic_details,
                retryable=error.retryable, context=context,
            )
            for dependent in ("art", "relics", "benchmark"):
                self.section_loading.ready(dependent, context)

    def _uid_tab_worker_finished(
        self, uid: str, worker: AccountFetchWorker
    ) -> None:
        if self.uid_tab_workers.get(uid) is worker:
            del self.uid_tab_workers[uid]
        worker.deleteLater()

    def search_uid(self, requested_uid: str | None = None) -> None:
        if isinstance(requested_uid, str):
            raw_uid = requested_uid
        elif self.page_stack.currentIndex() == 0:
            raw_uid = self.build_uid_input.text()
        else:
            raw_uid = self.uid_input.text()
        uid = raw_uid.strip()
        if len(uid) != 9 or not uid.isdigit():
            self.home_panel.set_message(
                "O UID deve conter exatamente 9 números.", error=True
            )
            target = (
                self.build_uid_input
                if self.page_stack.currentIndex() == 0 else self.uid_input
            )
            target.setFocus()
            if self.page_stack.currentIndex() == 0:
                self.set_status("O UID deve conter exatamente 9 números.", "error")
                self.copy_error_button.setVisible(False)
                self._build_recovery_mode = "uid_tab"
                self.build_enka_recovery.show_error(
                    AccountFetchError(
                        "invalid_uid",
                        "UID inválida",
                        "A UID precisa conter exatamente 9 números.",
                        f"Valor recebido com {len(uid)} caractere(s).",
                        retryable=False,
                    ),
                    has_saved_data=False,
                )
            return
        self.home_panel.set_message("")
        self.build_uid_input.setText(uid)
        self._open_public_uid(uid)

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
        self._open_public_uid(uid, source="friend")

    def _copy_enka_error(self, error: object) -> None:
        current = ensure_account_error(error)
        copy_error_details(current.diagnostic_details, "Consulta ao Enka.Network")

    def _open_network_settings(self) -> None:
        if not QDesktopServices.openUrl(QUrl("ms-settings:network-status")):
            self.set_status(
                "Abra as configurações de Rede e Internet do Windows para verificar a conexão.",
                "error",
            )

    def _retry_enka_failure(self, location: str) -> None:
        own_account_failure = location == "account" or self._build_recovery_mode == "own_account"
        if own_account_failure:
            user = self.auth_service.current_user
            if user is None or not user.game_uid:
                return
            if self._last_failed_account_target == "own_builds":
                self.refresh_loaded_account()
            else:
                self._load_saved_uid(force=True)
            return
        uid = self.active_uid_tab
        if uid in self.uid_workspace.sessions:
            self._request_uid_tab(uid)

    def _continue_with_saved_enka_data(self, location: str) -> None:
        own_account_failure = location == "account" or self._build_recovery_mode == "own_account"
        if own_account_failure:
            account = self.own_account
            user = self.auth_service.current_user
            if (
                account is None
                or user is None
                or self.own_account_user_id != user.id
                or account.uid != user.game_uid
            ):
                return
            self.account_enka_recovery.clear()
            self.build_enka_recovery.clear()
            self.account_copy_error.setVisible(False)
            self.copy_error_button.setVisible(False)
            if self._last_failed_account_target == "own_builds":
                self._open_own_character_builds(self.current_character_id)
                self.set_status("Continuando com os últimos dados salvos da sua conta.")
            else:
                self._render_own_account(account)
                self._refresh_dashboard()
                self.account_status.setObjectName("statusInfo")
                self.account_status.setText(
                    "Exibindo os últimos dados carregados. Você pode atualizar novamente mais tarde."
                )
                self.account_status.style().unpolish(self.account_status)
                self.account_status.style().polish(self.account_status)
            return

        session = self.uid_workspace.sessions.get(self.active_uid_tab)
        if session is None or session.account is None:
            return
        session.error = ""
        self.uid_tab_errors.pop(session.uid, None)
        self.uid_workspace.persist()
        self.build_enka_recovery.clear()
        self.copy_error_button.setVisible(False)
        self._activate_uid_tab(session.uid)
        self.set_status("Continuando com os últimos dados salvos desta UID.")

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
            if self.pending_account_target in {"account", "auto_account"}:
                self.account_enka_recovery.clear()
                self.account_copy_error.setVisible(False)
            elif self.pending_account_target == "own_builds":
                self.build_enka_recovery.clear()
                self.copy_error_button.setVisible(False)
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

    def _request_failed(self, failure: object) -> None:
        error = ensure_account_error(failure)
        message = error.message
        user = self.auth_service.current_user
        if self.pending_account_target in {"account", "own_builds", "auto_account"}:
            if (
                user is None
                or self._own_request_owner_id != user.id
                or self._own_request_uid != user.game_uid
            ):
                return
        self.account_sync_failed = True
        self._last_account_error = error
        self._last_failed_account_target = self.pending_account_target
        self.sync_manager.fail(
            "account",
            "Falha ao sincronizar a conta",
            details=error.diagnostic_details,
            retryable=error.retryable,
        )
        if user is not None and self.pending_account_target in {
            "account", "own_builds", "auto_account"
        }:
            self.activity_log.add(
                "account",
                "Falha ao sincronizar a conta",
                error.diagnostic_details,
                owner_id=user.id,
                kind="error",
            )
        if self.pending_account_target in {"account", "auto_account"}:
            self.account_status.setObjectName("statusError")
            self.account_status.setText(message)
            self.account_copy_error.setVisible(False)
            self.account_status.style().unpolish(self.account_status)
            self.account_status.style().polish(self.account_status)
            self.account_enka_recovery.show_error(
                error, has_saved_data=self.own_account is not None
            )
        else:
            self._build_recovery_mode = "own_account"
            self.set_status(message, "error")
            self.copy_error_button.setVisible(False)
            self.build_enka_recovery.show_error(
                error, has_saved_data=self.own_account is not None
            )
        if user is not None and user.game_uid:
            context = self._load_context_for(user.game_uid)
            self.section_loading.fail(
                "profile", error.message, details=error.diagnostic_details,
                retryable=error.retryable, context=context,
            )
            self.section_loading.fail(
                "characters", "Personagens não foram atualizados.",
                details=error.diagnostic_details,
                retryable=error.retryable, context=context,
            )
            if self.current_account is None:
                for dependent in ("art", "relics", "benchmark"):
                    self.section_loading.ready(dependent, context)

    def _account_loaded(self, account: AccountSummary, message: str) -> None:
        if self.pending_account_target in {"account", "own_builds", "auto_account"}:
            current_user = self.auth_service.current_user
            if (
                current_user is None
                or self._own_request_owner_id != current_user.id
                or self._own_request_uid != current_user.game_uid
                or account.uid != current_user.game_uid
            ):
                return
        self.account_copy_error.setVisible(False)
        self.account_enka_recovery.clear()
        if self.pending_account_target == "own_builds":
            self.build_enka_recovery.clear()
        self._last_account_error = None
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
            if self.pending_account_target == "own_builds":
                self._open_own_character_builds(self.current_character_id)
            QTimer.singleShot(0, self._refresh_dashboard)
            self._start_relic_inventory_sync(user.id, account)
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
            QTimer.singleShot(0, self._apply_pending_resume_after_data)
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

    def _start_relic_inventory_sync(
        self, owner_id: int, account: AccountSummary
    ) -> None:
        if any(
            worker.isRunning()
            and worker.owner_id == owner_id
            and worker.account.uid == account.uid
            for worker in self.relic_sync_workers
        ):
            return
        context = self.section_loading.context
        if context.uid == account.uid:
            self.section_loading.pending(
                "inventory", "Salvando inventário em segundo plano…", context
            )
        worker = RelicSyncWorker(
            self.relic_database, BenchmarkEngine(), owner_id, account
        )
        self.relic_sync_workers.add(worker)
        worker.succeeded.connect(
            lambda changes, current=worker, load_context=context:
            self._relic_inventory_synced(current, owner_id, account.uid, changes, load_context)
        )
        worker.failed.connect(
            lambda message, current=worker, load_context=context:
            self._relic_inventory_sync_failed(current, owner_id, account.uid, message, load_context)
        )
        worker.finished.connect(lambda current=worker: self._release_relic_sync(current))
        worker.start()

    def _relic_inventory_synced(
        self, worker: RelicSyncWorker, owner_id: int, uid: str,
        changes: object, context: LoadContext,
    ) -> None:
        user = self.auth_service.current_user
        if user is None or user.id != owner_id or user.game_uid != uid:
            return
        self.relic_inventory_panel.mark_dirty()
        QTimer.singleShot(0, self._refresh_dashboard)
        if self.section_loading.is_current(context):
            self.section_loading.ready("inventory", context)
        if not isinstance(changes, dict) or not changes.get("had_previous"):
            return
        added = int(changes.get("added", 0))
        removed = int(changes.get("removed", 0))
        moved = int(changes.get("moved", 0))
        if not (added or removed or moved):
            return
        details = []
        if added:
            details.append(f"{added} nova{'s' if added != 1 else ''}")
        if removed:
            details.append(f"{removed} removida{'s' if removed != 1 else ''}")
        if moved:
            details.append(f"{moved} trocada{'s' if moved != 1 else ''} de personagem")
        message = "Após atualizar a conta: " + ", ".join(details) + "."
        self.notification_center.add(
            f"relics:{owner_id}:{uid}", "Relíquias alteradas", message, "info"
        )
        total_changes = added + removed + moved
        self.activity_log.add(
            "relics",
            f"{total_changes} relíquia{'s' if total_changes != 1 else ''} alterada{'s' if total_changes != 1 else ''}",
            message, owner_id=owner_id,
        )

    def _relic_inventory_sync_failed(
        self, worker: RelicSyncWorker, owner_id: int, uid: str,
        message: str, context: LoadContext,
    ) -> None:
        user = self.auth_service.current_user
        if user is None or user.id != owner_id or user.game_uid != uid:
            return
        self.section_loading.fail(
            "inventory", "Inventário não foi atualizado.",
            details=message, context=context,
        )

    def _release_relic_sync(self, worker: RelicSyncWorker) -> None:
        self.relic_sync_workers.discard(worker)
        worker.deleteLater()

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

    def display_account(
        self,
        account: AccountSummary,
        *,
        selected_character_id: str = "",
        reset_benchmarks: bool = True,
    ) -> None:
        session = self.uid_workspace.sessions.get(self.active_uid_tab)
        if session is None or session.account is not account:
            self._reuse_session_benchmark = False
        context = self.section_loading.begin_context(
            self.uid_workspace.owner_id, account.uid
        )
        self.section_loading.pending(
            "characters", "Preparando personagens…", context
        )
        self.section_loading.pending("art", "Aguardando personagem…", context)
        self.section_loading.pending("relics", "Aguardando relíquias…", context)
        self.section_loading.pending("benchmark", "Aguardando build…", context)
        self.current_account = account
        self.current_uid = account.uid
        self.current_characters = account.characters
        reused_list = self._use_character_list(account)
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
                lambda pixmap, uid=account.uid, current=context:
                self._set_profile_icon_if_current(
                    uid, pixmap, current
                ),
            )
        self.uid_caption.setText(f"UID {account.uid}")
        self.section_loading.ready("profile", context)
        if reset_benchmarks:
            self.benchmark_results = {}
            self.fribbels_cache = {}
            self.unsupported_benchmark_characters = set()
        self.active_benchmark_ids.clear()
        if reused_list:
            self.section_loading.ready("characters", context)
            selected_row = next(
                (
                    index for index, character in enumerate(account.characters)
                    if str(character.avatar_id) == selected_character_id
                ),
                0,
            )
            if self.character_list.currentRow() != selected_row:
                self.character_list.setCurrentRow(selected_row)
            elif account.characters:
                self.show_character_details(selected_row)
        else:
            self.character_list.clear()
            QTimer.singleShot(
                0,
                lambda current=context, selected=selected_character_id:
                self._populate_character_section(account, selected, current),
            )

    def _populate_character_section(
        self, account: AccountSummary, selected_character_id: str,
        context: LoadContext,
    ) -> None:
        if (
            not self.section_loading.is_current(context)
            or self.current_account is not account
        ):
            return
        for character in account.characters:
            item = QListWidgetItem()
            card = CharacterPortraitCard(character)
            item.setSizeHint(card.sizeHint())
            self.character_list.addItem(item)
            self.character_list.setItemWidget(item, card)
            self.image_loader.load(character.icon_url, card.avatar.set_image)
        self.section_loading.ready("characters", context)
        if account.characters:
            selected_row = next(
                (
                    index for index, character in enumerate(account.characters)
                    if str(character.avatar_id) == selected_character_id
                ),
                0,
            )
            self.character_list.setCurrentRow(selected_row)

    def _set_profile_icon_if_current(
        self, uid: str, pixmap: QPixmap, context: LoadContext
    ) -> None:
        if (
            self.section_loading.is_current(context)
            and self.current_account is not None
            and self.current_account.uid == uid
        ):
            self.profile_header_avatar.set_image(pixmap)
