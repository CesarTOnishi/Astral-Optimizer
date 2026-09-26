from __future__ import annotations


NOTIFICATION_CATEGORIES = (
    ("warp_reminder", "Lembrete de importação de Saltos", "Escolha o prazo após a última importação."),
    ("soft_pity", "Pity próximo do soft pity", "Avisos sobre banners próximos do soft pity."),
    ("catalog", "Catálogo desatualizado", "Novos dados do jogo disponíveis."),
    ("updates", "Atualizações do aplicativo", "Nova versão e resultado da atualização."),
    ("backup", "Backup do histórico", "Resultado do backup no OneDrive."),
    ("relics", "Mudanças nas relíquias", "Alterações detectadas após atualizar a conta."),
)

CATEGORY_IDS = frozenset(category for category, _, _ in NOTIFICATION_CATEGORIES)


def notification_category(key: str) -> str | None:
    if key.startswith("warp-import-reminder:"):
        return "warp_reminder"
    if key.startswith("soft-pity:"):
        return "soft_pity"
    if key == "catalog-outdated":
        return "catalog"
    if key in {"app-update", "app-update-result"}:
        return "updates"
    if key.startswith("backup:"):
        return "backup"
    if key.startswith("relics:"):
        return "relics"
    return None
