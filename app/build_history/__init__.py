"""Persistência das builds salvas para comparação."""

from app.build_history.database import BuildHistoryDatabase, BuildSnapshot

__all__ = ["BuildHistoryDatabase", "BuildSnapshot"]
