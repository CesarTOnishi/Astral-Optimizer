"""Fluxos de atualização do aplicativo e do catálogo."""
from __future__ import annotations

import time

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication

from app.catalog import CatalogVersionCheckWorker
from app.config import APP_VERSION
from app.ui.update_dialog import UpdateAvailableDialog, UpdateReadyDialog
from app.updater import (
    PreparedUpdate, ReleaseInfo, UpdateCheckWorker, UpdateDownloadWorker,
    consume_update_result, is_newer_version, launch_installer, running_from_bundle,
)


class UpdateActions:
    """Coordena a busca, download e apresentação de atualizações."""

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
        if not self.isVisible() and self.settings_dialog is None:
            self._pending_update_release = release
            return
        if self.update_prompt_open:
            return
        self._pending_update_release = None
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
