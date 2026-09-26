from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.warp.preview import WarpImportPreview


class WarpImportPreviewDialog(QDialog):
    """Confirm an import after the source has been read but before any write."""

    def __init__(
        self,
        preview: WarpImportPreview,
        source: str,
        *,
        summary_count: int = 0,
        warnings: tuple[str, ...] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("authDialog")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(480)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        modal = QFrame()
        modal.setObjectName("settingsModal")
        layout = QVBoxLayout(modal)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(12)

        heading = QLabel("Prévia da importação")
        heading.setObjectName("brandTitle")
        layout.addWidget(heading)
        description = QLabel(
            f"Fonte: {Path(source).name}\nConfira os registros antes de adicionar ao histórico."
        )
        description.setObjectName("muted")
        description.setWordWrap(True)
        layout.addWidget(description)

        counts = QHBoxLayout()
        counts.setSpacing(8)
        for number, label in (
            (preview.new_count, "Serão adicionados"),
            (preview.duplicate_count, "Duplicados"),
            (preview.rejected_count, "Rejeitados"),
        ):
            card = QFrame()
            card.setObjectName("settingsUpdatePanel")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 10, 8, 10)
            card_layout.setSpacing(3)
            value = QLabel(f"{number:,}".replace(",", "."))
            value.setObjectName("warpMetricValue")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption = QLabel(label)
            caption.setObjectName("muted")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setWordWrap(True)
            card_layout.addWidget(value)
            card_layout.addWidget(caption)
            counts.addWidget(card, 1)
        layout.addLayout(counts)

        if summary_count:
            summaries = QLabel(
                f"Também serão processados {summary_count} resumo(s) de colaboração."
            )
            summaries.setObjectName("muted")
            summaries.setWordWrap(True)
            layout.addWidget(summaries)
        if warnings:
            warning = QLabel("Avisos da fonte: " + "; ".join(warnings))
            warning.setObjectName("muted")
            warning.setWordWrap(True)
            layout.addWidget(warning)

        note = QLabel("Nenhum dado será gravado se você cancelar.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        actions = QHBoxLayout()
        actions.addStretch(1)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.clicked.connect(self.reject)
        self.add_button = QPushButton("Adicionar")
        self.add_button.setObjectName("primaryButton")
        self.add_button.setEnabled(bool(preview.valid_records) or summary_count > 0)
        self.add_button.clicked.connect(self.accept)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.add_button)
        layout.addLayout(actions)
        outer.addWidget(modal)
