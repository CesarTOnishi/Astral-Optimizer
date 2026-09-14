from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRegularExpression,
    Signal,
    QTimer,
    Qt,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.motion import AnimatedDialog as QDialog
from app.ui.icons import set_button_icon
from app.ui.motion import AnimatedStack as QStackedWidget

from app.auth import AuthService, AuthUser
from app.cloud import (
    OneDriveBackupService,
    detected_onedrive_roots,
    set_backup_folder,
)
from app.config import APP_VERSION
from app.privacy import hide_uid_in_shared_images, set_hide_uid_in_shared_images
from app.preferences import (
    ExperiencePreferences, ExperienceSettings, THEMES,
    apply_experience_preferences, motion_duration, themed_color,
)
from app.ui.widgets import FadeComboBox
from app.warp import (
    WarpDatabase,
    latest_cache_candidates,
    set_webcaches_path,
    webcaches_path,
)


class AuthDialog(QDialog):
    def __init__(self, service: AuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.user: AuthUser | None = None
        self.setObjectName("settingsDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(410)
        self._login_error_animation: QParallelAnimationGroup | None = None
        self._login_anchor_pos: QPoint | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        self.auth_modal = QFrame()
        self.auth_modal.setObjectName("authModal")
        content = QVBoxLayout(self.auth_modal)
        content.setContentsMargins(24, 18, 24, 24)
        content.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("PERFIL HSR")
        title.setObjectName("brandTitle")
        close = QPushButton("×")
        close.setObjectName("dialogCloseButton")
        close.setFixedSize(34, 30)
        close.clicked.connect(self.reject)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)
        content.addLayout(header)

        tabs = QHBoxLayout()
        self.login_tab = QPushButton("Entrar")
        self.register_tab = QPushButton("Criar conta")
        for button in (self.login_tab, self.register_tab):
            button.setObjectName("authTabButton")
            button.setCheckable(True)
            tabs.addWidget(button)
        self.login_tab.setChecked(True)
        self.login_tab.clicked.connect(lambda: self._show_page(0))
        self.register_tab.clicked.connect(lambda: self._show_page(1))
        content.addLayout(tabs)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._login_page())
        self.pages.addWidget(self._register_page())
        content.addWidget(self.pages)

        self.message = QLabel("")
        self.message.setObjectName("authMessage")
        self.message.setWordWrap(True)
        content.addWidget(self.message)
        layout.addWidget(self.auth_modal)

        self.login_error_overlay = QFrame(self.auth_modal)
        self.login_error_overlay.setObjectName("loginErrorFlash")
        self.login_error_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self.login_error_opacity = QGraphicsOpacityEffect(self.login_error_overlay)
        self.login_error_opacity.setOpacity(0.0)
        self.login_error_overlay.setGraphicsEffect(self.login_error_opacity)
        self.login_error_overlay.hide()

    @staticmethod
    def _field(placeholder: str, password: bool = False) -> QLineEdit:
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        if password:
            field.setEchoMode(QLineEdit.EchoMode.Password)
        return field

    def _login_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)
        self.login_username = self._field("Nome de usuário ou e-mail")
        self.login_password = self._field("Senha", True)
        self.login_username.textEdited.connect(self._clear_login_error)
        self.login_password.textEdited.connect(self._clear_login_error)
        button = QPushButton("Entrar")
        button.setObjectName("primaryButton")
        button.clicked.connect(self._login)
        self.login_password.returnPressed.connect(self._login)
        layout.addWidget(self.login_username)
        layout.addWidget(self.login_password)
        layout.addWidget(button)
        return page

    def _register_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)
        self.register_username = self._field("Escolha um nome de usuário")
        self.register_email = self._field("Seu e-mail")
        self.register_password = self._field("Senha com pelo menos 8 caracteres", True)
        self.register_confirmation = self._field("Confirme a senha", True)
        button = QPushButton("Cadastrar e entrar")
        button.setObjectName("primaryButton")
        button.clicked.connect(self._register)
        self.register_confirmation.returnPressed.connect(self._register)
        layout.addWidget(self.register_username)
        layout.addWidget(self.register_email)
        layout.addWidget(self.register_password)
        layout.addWidget(self.register_confirmation)
        layout.addWidget(button)
        return page

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.login_tab.setChecked(index == 0)
        self.register_tab.setChecked(index == 1)
        self.message.clear()
        self._clear_login_error()

    def _login(self) -> None:
        try:
            self.user = self.service.login(
                self.login_username.text(), self.login_password.text()
            )
        except ValueError as error:
            self.message.setText(f"⚠  Não foi possível entrar. {error}")
            self._animate_login_error()
            return
        self.accept()

    def _animate_login_error(self) -> None:
        if self._login_error_animation is not None:
            self._login_error_animation.stop()
        if self._login_anchor_pos is not None:
            self.move(self._login_anchor_pos)
        for field in (self.login_username, self.login_password):
            field.setProperty("invalid", True)
            field.style().unpolish(field)
            field.style().polish(field)
        self.auth_modal.setProperty("loginError", True)
        self.auth_modal.style().unpolish(self.auth_modal)
        self.auth_modal.style().polish(self.auth_modal)
        self.login_error_overlay.setGeometry(self.auth_modal.rect())
        self.login_error_opacity.setOpacity(0.0)
        self.login_error_overlay.show()
        self.login_error_overlay.raise_()

        start = self.pos()
        self._login_anchor_pos = start
        shake = QPropertyAnimation(self, b"pos")
        shake.setDuration(motion_duration(390))
        shake.setEasingCurve(QEasingCurve.Type.OutCubic)
        shake.setStartValue(start)
        shake.setKeyValueAt(0.14, start + QPoint(-10, 0))
        shake.setKeyValueAt(0.28, start + QPoint(9, 0))
        shake.setKeyValueAt(0.43, start + QPoint(-7, 0))
        shake.setKeyValueAt(0.58, start + QPoint(6, 0))
        shake.setKeyValueAt(0.73, start + QPoint(-4, 0))
        shake.setKeyValueAt(0.86, start + QPoint(2, 0))
        shake.setEndValue(start)

        flash = QPropertyAnimation(self.login_error_opacity, b"opacity")
        flash.setDuration(motion_duration(520))
        flash.setStartValue(0.0)
        flash.setKeyValueAt(0.18, 0.72)
        flash.setKeyValueAt(0.42, 0.04)
        flash.setKeyValueAt(0.62, 0.56)
        flash.setEndValue(0.0)
        flash.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(shake)
        group.addAnimation(flash)
        group.finished.connect(self._finish_login_error_animation)
        self._login_error_animation = group
        group.start()

    def _finish_login_error_animation(self) -> None:
        if self._login_anchor_pos is not None:
            self.move(self._login_anchor_pos)
        self.login_error_opacity.setOpacity(0.0)
        self.login_error_overlay.hide()
        self.auth_modal.setProperty("loginError", False)
        self.auth_modal.style().unpolish(self.auth_modal)
        self.auth_modal.style().polish(self.auth_modal)

    def _clear_login_error(self, _text: str = "") -> None:
        if self._login_error_animation is not None:
            self._login_error_animation.stop()
        if self._login_anchor_pos is not None:
            self.move(self._login_anchor_pos)
        self.login_error_opacity.setOpacity(0.0)
        self.login_error_overlay.hide()
        self.auth_modal.setProperty("loginError", False)
        self.auth_modal.style().unpolish(self.auth_modal)
        self.auth_modal.style().polish(self.auth_modal)
        for field in (self.login_username, self.login_password):
            field.setProperty("invalid", False)
            field.style().unpolish(field)
            field.style().polish(field)
        if hasattr(self, "message") and self.pages.currentIndex() == 0:
            self.message.clear()

    def _register(self) -> None:
        if self.register_password.text() != self.register_confirmation.text():
            self.message.setText("As senhas não são iguais.")
            return
        try:
            self.user = self.service.register(
                self.register_username.text(),
                self.register_email.text(),
                self.register_password.text(),
            )
        except ValueError as error:
            self.message.setText(str(error))
            return
        self.accept()


class PrivacyCheckBox(QCheckBox):
    """Checkbox consistente com o tema, sem depender do indicador do Windows."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setMinimumHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:  # noqa: N802 - API Qt
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box_size = 18.0
        top = (self.height() - box_size) / 2.0
        border = QColor(themed_color("#8ddcf5" if self.isChecked() else "#527098"))
        if self.underMouse() or self.hasFocus():
            border = QColor(themed_color("#9be6ff"))
        painter.setPen(QPen(border, 1.2))
        painter.setBrush(QColor(themed_color(
            "#498dc2" if self.isChecked() else "#0b1424"
        )))
        painter.drawRoundedRect(1.0, top, box_size, box_size, 5.0, 5.0)

        if self.isChecked():
            check = QPainterPath()
            check.moveTo(5.0, top + 9.5)
            check.lineTo(8.5, top + 13.0)
            check.lineTo(15.2, top + 5.5)
            pen = QPen(QColor("#ffffff"), 2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(check)

        painter.setPen(QColor(themed_color(
            "#eaf2ff" if self.isEnabled() else "#718099"
        )))
        painter.setFont(self.font())
        painter.drawText(
            29,
            0,
            max(0, self.width() - 29),
            self.height(),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )
        painter.end()


class SettingsDialog(QDialog):
    update_requested = Signal()

    def __init__(
        self,
        user: AuthUser,
        parent: QWidget | None = None,
        warp_database: WarpDatabase | None = None,
        initial_page: int = 0,
    ) -> None:
        super().__init__(parent)
        self.user = user
        self.onedrive_service = OneDriveBackupService(user)
        self.warp_database = warp_database or WarpDatabase()
        self.cloud_changed = False
        self.logout_requested = False
        self.experience_changed = False
        self._appearance_timer = QTimer(self)
        self._appearance_timer.setSingleShot(True)
        self._appearance_timer.timeout.connect(self._commit_appearance)
        self.tutorial_requested = False
        self.diagnostics_requested = False
        self.uid_to_save: str | None = None
        self.setObjectName("authDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedSize(790, 590)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        modal = QFrame()
        modal.setObjectName("settingsModal")
        content = QVBoxLayout(modal)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(22, 14, 12, 12)
        title = QLabel("Configurações")
        title.setObjectName("brandTitle")
        close = QPushButton("×")
        close.setObjectName("dialogCloseButton")
        close.setFixedSize(34, 30)
        close.clicked.connect(self.accept)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)
        content.addLayout(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(178)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 15, 12, 16)
        side.setSpacing(6)
        self.settings_nav: list[QPushButton] = []
        for index, (icon, label) in enumerate((
            ("profile", "Perfil"), ("appearance", "Aparência"), ("privacy", "Privacidade"),
            ("backup", "Backup"), ("info", "Aplicativo"),
        )):
            button = QPushButton(label)
            set_button_icon(button, icon, 16)
            button.setObjectName("settingsNavButton")
            button.setCheckable(True)
            button.clicked.connect(
                lambda _checked=False, page=index: self._select_settings_page(page)
            )
            side.addWidget(button)
            self.settings_nav.append(button)
        side.addStretch(1)
        account_hint = QLabel(user.username)
        account_hint.setObjectName("settingsSidebarUser")
        account_hint.setWordWrap(True)
        side.addWidget(account_hint)
        body.addWidget(sidebar)

        right = QWidget()
        right.setObjectName("settingsContent")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(24, 18, 24, 22)
        right_layout.setSpacing(10)
        self.settings_stack = QStackedWidget()
        self.settings_stack.setObjectName("settingsStack")

        profile_page, profile = self._settings_page(
            "PERFIL", "Gerencie sua conta local e a UID principal do Honkai."
        )
        avatar = QLabel(user.username[:1].upper())
        avatar.setObjectName("settingsAvatar")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(58, 58)
        name = QLabel(user.username)
        name.setObjectName("detailName")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail = QLabel(user.email or "E-mail não cadastrado")
        detail.setObjectName("muted")
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profile.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        profile.addWidget(name)
        profile.addWidget(detail)

        uid_label = QLabel("UID PRINCIPAL DO HONKAI")
        uid_label.setObjectName("metricTitle")
        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText("UID de 9 dígitos")
        self.uid_input.setMaxLength(9)
        self.uid_input.setText(user.game_uid)
        self.uid_input.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{0,9}"), self)
        )
        save_uid = QPushButton("Salvar UID principal")
        save_uid.setObjectName("primaryButton")
        save_uid.clicked.connect(self._save_uid)
        profile.addSpacing(8)
        profile.addWidget(uid_label)
        profile.addWidget(self.uid_input)
        profile.addWidget(save_uid)
        profile.addStretch(1)
        logout = QPushButton("Sair da conta")
        logout.setObjectName("dangerButton")
        logout.clicked.connect(self._logout)
        profile.addWidget(logout)
        self.settings_stack.addWidget(profile_page)

        appearance_page, appearance = self._settings_page(
            "APARÊNCIA", "Escolha o visual e ajuste os efeitos para este computador."
        )
        current_experience = ExperienceSettings().load()
        theme_label = QLabel("TEMA DA INTERFACE")
        theme_label.setObjectName("metricTitle")
        self.theme_selector = FadeComboBox()
        self.theme_selector.setObjectName("settingsThemeSelector")
        for key, label in THEMES.items():
            self.theme_selector.addItem(label, key)
        self.theme_selector.setCurrentIndex(
            max(0, self.theme_selector.findData(current_experience.theme))
        )
        self.theme_selector.currentIndexChanged.connect(self._apply_appearance)
        self.reduce_motion_checkbox = QCheckBox(
            "Reduzir animações e efeitos de movimento"
        )
        self.reduce_motion_checkbox.setObjectName("experienceCheckBox")
        self.reduce_motion_checkbox.setChecked(current_experience.reduce_motion)
        self.reduce_motion_checkbox.toggled.connect(self._apply_appearance)
        appearance.addWidget(theme_label)
        appearance.addWidget(self.theme_selector)
        appearance.addWidget(self.reduce_motion_checkbox)
        appearance_hint = QLabel(
            "A redução de movimento é indicada para computadores mais fracos ou para quem prefere transições instantâneas."
        )
        appearance_hint.setObjectName("muted")
        appearance_hint.setWordWrap(True)
        appearance.addWidget(appearance_hint)
        appearance.addSpacing(10)
        tutorial = QPushButton("Rever tutorial interativo")
        tutorial.setObjectName("secondaryButton")
        tutorial.clicked.connect(self._request_tutorial)
        appearance.addWidget(tutorial)
        appearance.addStretch(1)
        self.settings_stack.addWidget(appearance_page)

        privacy_page, privacy = self._settings_page(
            "PRIVACIDADE", "Controle quais informações aparecem ao compartilhar imagens."
        )
        privacy_panel = QFrame()
        privacy_panel.setObjectName("settingsPrivacyPanel")
        privacy_layout = QVBoxLayout(privacy_panel)
        privacy_layout.setContentsMargins(13, 11, 13, 12)
        privacy_layout.setSpacing(7)
        privacy_title = QLabel("PRIVACIDADE")
        privacy_title.setObjectName("metricTitle")
        self.hide_uid_checkbox = PrivacyCheckBox(
            "Ocultar UID nas imagens compartilhadas"
        )
        self.hide_uid_checkbox.setObjectName("privacyCheckBox")
        self.hide_uid_checkbox.setChecked(hide_uid_in_shared_images(user.id))
        self.hide_uid_checkbox.setToolTip(
            "Substitui os números da UID por pontos no cartão exportado."
        )
        self.hide_uid_checkbox.toggled.connect(
            lambda hidden: set_hide_uid_in_shared_images(user.id, hidden)
        )
        privacy_hint = QLabel(
            "Quando ativado, o cartão e o nome sugerido do arquivo não expõem sua UID."
        )
        privacy_hint.setObjectName("privacyHint")
        privacy_hint.setWordWrap(True)
        privacy_hint.setMinimumHeight(28)
        privacy_hint.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        privacy_layout.addWidget(privacy_title)
        privacy_layout.addWidget(self.hide_uid_checkbox)
        privacy_layout.addWidget(privacy_hint)
        privacy.addWidget(privacy_panel)
        privacy.addStretch(1)
        self.settings_stack.addWidget(privacy_page)

        backup_page, backup = self._settings_page(
            "BACKUP", "Salve seu histórico em uma pasta sincronizada pelo OneDrive."
        )
        onedrive_panel = QFrame()
        onedrive_panel.setObjectName("settingsUpdatePanel")
        onedrive_layout = QVBoxLayout(onedrive_panel)
        onedrive_layout.setContentsMargins(13, 11, 13, 12)
        onedrive_layout.setSpacing(8)
        onedrive_label = QLabel("BACKUP NO ONEDRIVE")
        onedrive_label.setObjectName("metricTitle")
        self.onedrive_status = QLabel()
        self.onedrive_status.setObjectName("muted")
        self.onedrive_status.setWordWrap(True)
        folder_actions = QHBoxLayout()
        self.onedrive_select = QPushButton("Selecionar pasta")
        self.onedrive_select.setObjectName("secondaryButton")
        self.onedrive_select.clicked.connect(self._choose_onedrive_folder)
        self.onedrive_auto = QPushButton("Usar pasta automática")
        self.onedrive_auto.setObjectName("secondaryButton")
        self.onedrive_auto.clicked.connect(self._use_automatic_onedrive_folder)
        folder_actions.addWidget(self.onedrive_select)
        folder_actions.addWidget(self.onedrive_auto)
        folder_actions.addStretch(1)
        backup_actions = QHBoxLayout()
        self.onedrive_backup = QPushButton("Salvar agora")
        self.onedrive_backup.setObjectName("primaryButton")
        self.onedrive_backup.clicked.connect(self._backup_onedrive)
        self.onedrive_restore = QPushButton("Restaurar último backup")
        self.onedrive_restore.setObjectName("secondaryButton")
        self.onedrive_restore.clicked.connect(self._restore_onedrive)
        backup_actions.addWidget(self.onedrive_backup)
        backup_actions.addWidget(self.onedrive_restore)
        backup_actions.addStretch(1)
        onedrive_layout.addWidget(onedrive_label)
        onedrive_layout.addWidget(self.onedrive_status)
        onedrive_layout.addLayout(folder_actions)
        onedrive_layout.addLayout(backup_actions)
        backup.addWidget(onedrive_panel)
        backup_hint = QLabel(
            "O Astral não recebe sua senha da Microsoft. Ele grava o arquivo localmente e "
            "o aplicativo oficial do OneDrive faz a sincronização com a nuvem."
        )
        backup_hint.setObjectName("muted")
        backup_hint.setWordWrap(True)
        backup.addWidget(backup_hint)
        backup.addStretch(1)
        self.settings_stack.addWidget(backup_page)
        self._refresh_onedrive_status()

        app_page, application = self._settings_page(
            "APLICATIVO", "Atualizações, suporte e informações técnicas."
        )
        update_panel = QFrame()
        update_panel.setObjectName("settingsUpdatePanel")
        update_panel.setMinimumHeight(76)
        update_layout = QHBoxLayout(update_panel)
        update_layout.setContentsMargins(12, 10, 9, 10)
        update_layout.setSpacing(10)
        update_info = QVBoxLayout()
        update_info.setSpacing(3)
        update_title = QLabel("ASTRAL OPTIMIZER")
        update_title.setObjectName("metricTitle")
        self.update_status = QLabel(f"Versão {APP_VERSION}")
        self.update_status.setObjectName("settingsVersion")
        self.update_status.setWordWrap(True)
        self.update_status.setMinimumHeight(30)
        self.update_status.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        update_info.addWidget(update_title)
        update_info.addWidget(self.update_status)
        self.update_button = QPushButton("Verificar atualização")
        self.update_button.setObjectName("secondaryButton")
        self.update_button.clicked.connect(self._request_update)
        update_layout.addLayout(update_info, 1)
        update_layout.addWidget(
            self.update_button, alignment=Qt.AlignmentFlag.AlignVCenter
        )
        application.addWidget(update_panel)

        cache_panel = QFrame()
        cache_panel.setObjectName("settingsUpdatePanel")
        cache_layout = QVBoxLayout(cache_panel)
        cache_layout.setContentsMargins(12, 10, 12, 11)
        cache_layout.setSpacing(7)
        cache_title = QLabel("PASTA WEBCACHES DO HONKAI: STAR RAIL")
        cache_title.setObjectName("metricTitle")
        cache_layout.addWidget(cache_title)
        cache_row = QHBoxLayout()
        cache_row.setSpacing(7)
        self.webcaches_input = QLineEdit()
        self.webcaches_input.setReadOnly(True)
        self.webcaches_input.setPlaceholderText("Localização automática")
        configured_webcaches = webcaches_path()
        self.webcaches_input.setText(
            str(configured_webcaches) if configured_webcaches else ""
        )
        choose_webcaches = QPushButton("Selecionar pasta")
        choose_webcaches.setObjectName("secondaryButton")
        choose_webcaches.clicked.connect(self._choose_webcaches_folder)
        clear_webcaches = QPushButton("Usar automático")
        clear_webcaches.setObjectName("secondaryButton")
        clear_webcaches.clicked.connect(self._clear_webcaches_folder)
        cache_row.addWidget(self.webcaches_input, 1)
        cache_row.addWidget(choose_webcaches)
        cache_row.addWidget(clear_webcaches)
        cache_layout.addLayout(cache_row)
        self.webcaches_hint = QLabel()
        self.webcaches_hint.setObjectName("muted")
        self.webcaches_hint.setWordWrap(True)
        cache_layout.addWidget(self.webcaches_hint)
        self._refresh_webcaches_hint()
        application.addWidget(cache_panel)

        diagnostics = QPushButton("Diagnóstico")
        diagnostics.setObjectName("secondaryButton")
        diagnostics.clicked.connect(self._open_diagnostics)
        application.addWidget(diagnostics)
        application.addStretch(1)
        self.settings_stack.addWidget(app_page)

        self.settings_message = QLabel("")
        self.settings_message.setObjectName("authMessage")
        self.settings_message.setWordWrap(True)
        right_layout.addWidget(self.settings_stack, 1)
        right_layout.addWidget(self.settings_message)
        body.addWidget(right, 1)
        content.addLayout(body, 1)
        layout.addWidget(modal)
        self._select_settings_page(
            max(0, min(initial_page, self.settings_stack.count() - 1))
        )

    @staticmethod
    def _settings_page(title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("settingsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        heading = QLabel(title.capitalize())
        heading.setObjectName("settingsPageTitle")
        detail = QLabel(subtitle)
        detail.setObjectName("settingsPageSubtitle")
        detail.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(detail)
        layout.addSpacing(8)
        return page, layout

    def _select_settings_page(self, index: int) -> None:
        self.settings_stack.setCurrentIndex(index)
        for position, button in enumerate(self.settings_nav):
            button.setChecked(position == index)

    def _apply_appearance(self, _value: object = None) -> None:
        # Let the dropdown close first and collapse changes in the same event turn.
        self._appearance_timer.start(0)

    def _commit_appearance(self) -> None:
        current = ExperienceSettings().load()
        preferences = ExperiencePreferences(
            theme=str(self.theme_selector.currentData()),
            reduce_motion=self.reduce_motion_checkbox.isChecked(),
            tutorial_completed=current.tutorial_completed,
        )
        ExperienceSettings().save(preferences)
        apply_experience_preferences(preferences=preferences)
        self.experience_changed = True
        self.settings_message.setText("Aparência aplicada automaticamente.")

    def done(self, result: int) -> None:
        if self._appearance_timer.isActive():
            self._appearance_timer.stop()
            self._commit_appearance()
        super().done(result)

    def _request_tutorial(self) -> None:
        self.tutorial_requested = True
        self.accept()

    def _open_diagnostics(self) -> None:
        self.diagnostics_requested = True
        self.accept()

    def _request_update(self) -> None:
        self.update_button.setEnabled(False)
        self.update_status.setText("Verificando nova versão…")
        self.update_requested.emit()

    def _choose_webcaches_folder(self) -> None:
        current = webcaches_path()
        selected = QFileDialog.getExistingDirectory(
            self,
            "Selecione a pasta webCaches",
            str(current if current and current.exists() else Path.home()),
            QFileDialog.Option.ShowDirsOnly,
        )
        if not selected:
            return
        root = Path(selected)
        set_webcaches_path(root)
        self.webcaches_input.setText(str(root.resolve()))
        self._refresh_webcaches_hint()
        self.settings_message.setText("Pasta webCaches salva.")

    def _clear_webcaches_folder(self) -> None:
        set_webcaches_path(None)
        self.webcaches_input.clear()
        self._refresh_webcaches_hint()
        self.settings_message.setText("A localização automática foi restaurada.")

    def _refresh_webcaches_hint(self) -> None:
        root = webcaches_path()
        if root is None:
            self.webcaches_hint.setText(
                "O Astral procurará a instalação automaticamente em todos os discos."
            )
            return
        candidates = latest_cache_candidates(root)
        if candidates:
            self.webcaches_hint.setText(
                "Cache que será priorizado: " + str(candidates[0])
            )
        elif root.exists():
            self.webcaches_hint.setText(
                "Nenhum Cache\\Cache_Data\\data_2 foi encontrado nessa pasta. "
                "Abra o Histórico de Saltos, feche completamente o jogo e tente novamente."
            )
        else:
            self.webcaches_hint.setText(
                "A pasta configurada não existe mais. Selecione novamente."
            )

    def _choose_onedrive_folder(self) -> None:
        current = self.onedrive_service.folder
        roots = detected_onedrive_roots()
        initial = current if current and current.exists() else (
            roots[0] if roots else Path.home()
        )
        selected = QFileDialog.getExistingDirectory(
            self,
            "Selecione uma pasta sincronizada pelo OneDrive",
            str(initial),
            QFileDialog.Option.ShowDirsOnly,
        )
        if not selected:
            return
        set_backup_folder(Path(selected))
        self.onedrive_service = OneDriveBackupService(self.user)
        self._refresh_onedrive_status()
        self.settings_message.setText(
            "Pasta de backup do OneDrive salva."
        )

    def _use_automatic_onedrive_folder(self) -> None:
        set_backup_folder(None)
        self.onedrive_service = OneDriveBackupService(self.user)
        self._refresh_onedrive_status()
        self.settings_message.setText(
            "O Astral voltou a usar a pasta detectada automaticamente."
        )

    def _refresh_onedrive_status(self) -> None:
        available = self.onedrive_service.available
        files = self.onedrive_service.backup_files() if available else []
        self.onedrive_status.setText(self.onedrive_service.status_text())
        self.onedrive_backup.setEnabled(available)
        self.onedrive_restore.setEnabled(bool(files))
        self.onedrive_auto.setEnabled(bool(detected_onedrive_roots()))

    def _backup_onedrive(self) -> None:
        try:
            payload = self.warp_database.export_owner(self.user.id)
            message = self.onedrive_service.save_backup(payload)
        except (OSError, RuntimeError, ValueError) as error:
            self.settings_message.setText(str(error))
            return
        self.cloud_changed = True
        self.settings_message.setText(message)
        self._refresh_onedrive_status()

    def _restore_onedrive(self) -> None:
        try:
            payload = self.onedrive_service.load_latest_backup()
            added, total = self.warp_database.restore_owner(payload, self.user.id)
        except (OSError, RuntimeError, ValueError) as error:
            self.settings_message.setText(str(error))
            return
        self.cloud_changed = True
        self.settings_message.setText(
            f"Backup restaurado: {total} registros lidos, {added} novos."
        )
        self._refresh_onedrive_status()

    def set_update_status(self, message: str, checking: bool = False) -> None:
        self.update_status.setText(message)
        self.update_button.setEnabled(not checking)
        QTimer.singleShot(0, self.adjustSize)

    def _logout(self) -> None:
        self.logout_requested = True
        self.accept()

    def _save_uid(self) -> None:
        uid = self.uid_input.text().strip()
        if uid and len(uid) != 9:
            self.settings_message.setText("A UID precisa conter exatamente 9 números.")
            return
        self.uid_to_save = uid
        self.accept()
