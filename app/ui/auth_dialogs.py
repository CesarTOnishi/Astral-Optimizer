from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRegularExpression,
    QTimer,
    Qt,
)
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
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
from app.warp import WarpDatabase


class AuthDialog(QDialog):
    def __init__(self, service: AuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.user: AuthUser | None = None
        self.setObjectName("authDialog")
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
        shake.setDuration(390)
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
        flash.setDuration(520)
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


class SettingsDialog(QDialog):
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
        self.uid_to_save: str | None = None
        self.setObjectName("authDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        modal = QFrame()
        modal.setObjectName("authModal")
        content = QVBoxLayout(modal)
        content.setContentsMargins(24, 20, 24, 24)
        content.setSpacing(12)
        header = QHBoxLayout()
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
        content.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        content.addWidget(name)
        content.addWidget(detail)

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
        self.settings_message = QLabel("")
        self.settings_message.setObjectName("authMessage")
        self.settings_message.setWordWrap(True)
        content.addWidget(uid_label)
        content.addWidget(self.uid_input)
        content.addWidget(save_uid)
        content.addWidget(self.settings_message)

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
        content.addWidget(drive_label)
        content.addWidget(self.drive_status)
        content.addLayout(drive_actions)
        self._set_drive_checking()
        QTimer.singleShot(0, self._refresh_drive)

        logout = QPushButton("Sair da conta")
        logout.setObjectName("dangerButton")
        logout.clicked.connect(self._logout)
        content.addWidget(logout)
        layout.addWidget(modal)

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
