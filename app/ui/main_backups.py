"""Fluxo de backup do histórico de Saltos no OneDrive."""
from __future__ import annotations

from app.cloud import OneDriveBackupService, OneDriveWorker


class BackupActions:
    """Coordena o backup assíncrono dos Saltos e seu estado visual."""

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
