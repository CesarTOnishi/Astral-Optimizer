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

from app.auth import AuthService, AuthUser
from app.cloud import (
    GoogleDriveService,
    GoogleDriveWorker,
    install_google_credentials,
)
from app.config import APP_VERSION
from app.privacy import hide_uid_in_shared_images, set_hide_uid_in_shared_images
from app.preferences import (
    ExperiencePreferences, ExperienceSettings, THEMES,
    apply_experience_preferences, motion_duration, themed_color,
)
from app.ui.widgets import FadeComboBox
from app.warp import WarpDatabase


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
        drive_service: GoogleDriveService | None = None,
        warp_database: WarpDatabase | None = None,
    ) -> None:
        super().__init__(parent)
        self.user = user
        self.drive_service = drive_service or GoogleDriveService(user)
        self.warp_database = warp_database or WarpDatabase()
        self.drive_worker: GoogleDriveWorker | None = None
        self.drive_status_worker: GoogleDriveWorker | None = None
        self._drive_configured = False
        self._drive_email = ""
        self.cloud_changed = False
        self.logout_requested = False
        self.experience_changed = False
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
        title = QLabel("CONFIGURAÇÕES")
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
            ("◉", "Perfil"), ("✦", "Aparência"), ("◈", "Privacidade"),
            ("☁", "Backup"), ("ⓘ", "Aplicativo"),
        )):
            button = QPushButton(f"{icon}   {label}")
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
            "BACKUP", "Proteja seu histórico de Saltos no espaço privado do Google Drive."
        )
        drive_label = QLabel("BACKUP NO GOOGLE DRIVE")
        drive_label.setObjectName("metricTitle")
        self.drive_status = QLabel()
        self.drive_status.setObjectName("muted")
        self.drive_status.setWordWrap(True)
        drive_actions = QHBoxLayout()
        self.drive_connect = QPushButton()
        self.drive_connect.setObjectName("secondaryButton")
        self.drive_connect.clicked.connect(self._toggle_drive)
        self.drive_backup = QPushButton("Salvar agora")
        self.drive_backup.setObjectName("secondaryButton")
        self.drive_backup.clicked.connect(self._backup_drive)
        self.drive_restore = QPushButton("Restaurar")
        self.drive_restore.setObjectName("secondaryButton")
        self.drive_restore.clicked.connect(self._restore_drive)
        drive_actions.addWidget(self.drive_connect)
        drive_actions.addWidget(self.drive_backup)
        drive_actions.addWidget(self.drive_restore)
        backup.addWidget(drive_label)
        backup.addWidget(self.drive_status)
        backup.addLayout(drive_actions)
        backup_hint = QLabel(
            "O Astral usa a área privada do aplicativo no Drive; outros arquivos da sua conta não ficam acessíveis."
        )
        backup_hint.setObjectName("muted")
        backup_hint.setWordWrap(True)
        backup.addWidget(backup_hint)
        backup.addStretch(1)
        self.settings_stack.addWidget(backup_page)
        self._set_drive_checking()
        QTimer.singleShot(0, self._refresh_drive)

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
        self._select_settings_page(0)

    @staticmethod
    def _settings_page(title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("settingsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        heading = QLabel(title)
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

    def _refresh_drive(self) -> None:
        if self.drive_status_worker and self.drive_status_worker.isRunning():
            return
        self._set_drive_checking()
        self.drive_status_worker = GoogleDriveWorker(self._read_drive_status)
        self.drive_status_worker.succeeded.connect(self._drive_status_ready)
        self.drive_status_worker.failed.connect(self._drive_status_failed)
        self.drive_status_worker.finished.connect(self._drive_status_finished)
        self.drive_status_worker.start()

    def _set_drive_checking(self) -> None:
        self.drive_status.setText("Verificando Google Drive…")
        self.drive_connect.setText("Verificando…")
        self.drive_connect.setEnabled(False)
        self.drive_backup.setEnabled(False)
        self.drive_restore.setEnabled(False)

    def _read_drive_status(self) -> dict[str, object]:
        configured = GoogleDriveService.available()
        email = self.drive_service.connected_email() if configured else ""
        return {"configured": configured, "email": email}

    def _drive_status_ready(self, result: object) -> None:
        status = result if isinstance(result, dict) else {}
        self._drive_configured = bool(status.get("configured"))
        self._drive_email = str(status.get("email", ""))
        connected = bool(self._drive_email)
        self.drive_status.setText(
            f"Conectado como {self._drive_email}. O backup automático está ativo."
            if connected
            else (
                "Nenhuma conta Google conectada."
                if self._drive_configured
                else "Google Drive ainda não configurado pelo desenvolvedor."
            )
        )
        self.drive_connect.setText(
            "Desconectar" if connected else (
                "Conectar Google" if self._drive_configured else "Configurar OAuth"
            )
        )
        self.drive_connect.setEnabled(True)
        self.drive_backup.setEnabled(connected)
        self.drive_restore.setEnabled(connected)

    def _drive_status_failed(self, message: str) -> None:
        self.drive_status.setText("Não foi possível verificar o Google Drive.")
        self.settings_message.setText(message)
        self.drive_connect.setText("Tentar novamente")
        self.drive_connect.setEnabled(True)

    def _drive_status_finished(self) -> None:
        if self.drive_status_worker:
            self.drive_status_worker.deleteLater()
        self.drive_status_worker = None

    def _toggle_drive(self) -> None:
        if not self._drive_configured:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Selecione o OAuth JSON do Google Cloud",
                "",
                "Credencial OAuth (*.json)",
            )
            if not path:
                return
            try:
                install_google_credentials(Path(path))
            except ValueError as error:
                self.settings_message.setText(str(error))
                return
            self.settings_message.setText(
                "OAuth configurado. Clique em Conectar Google para autorizar a conta."
            )
            self._drive_configured = True
            self._refresh_drive()
            return
        if self._drive_email:
            self._start_drive(self.drive_service.disconnect)
        else:
            self._start_drive(self.drive_service.connect)

    def _backup_drive(self) -> None:
        payload = self.warp_database.export_owner(self.user.id)
        self._start_drive(lambda: self.drive_service.upload_backup(payload))

    def _restore_drive(self) -> None:
        def restore() -> str:
            payload = self.drive_service.download_backup()
            added, total = self.warp_database.restore_owner(payload, self.user.id)
            return f"Backup restaurado: {total} registros lidos, {added} novos."

        self._start_drive(restore)

    def _start_drive(self, operation) -> None:  # type: ignore[no-untyped-def]
        if self.drive_worker and self.drive_worker.isRunning():
            return
        for button in (self.drive_connect, self.drive_backup, self.drive_restore):
            button.setEnabled(False)
        self.drive_status.setText("Aguarde…")
        self.drive_worker = GoogleDriveWorker(operation)
        self.drive_worker.succeeded.connect(self._drive_succeeded)
        self.drive_worker.failed.connect(self._drive_failed)
        self.drive_worker.finished.connect(self._drive_finished)
        self.drive_worker.start()

    def _drive_succeeded(self, result: object) -> None:
        self.cloud_changed = True
        self.settings_message.setText(str(result))

    def _drive_failed(self, message: str) -> None:
        self.settings_message.setText(message)

    def _drive_finished(self) -> None:
        if self.drive_worker:
            self.drive_worker.deleteLater()
        self.drive_worker = None
        self._refresh_drive()
