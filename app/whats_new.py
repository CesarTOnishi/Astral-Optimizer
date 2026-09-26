from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

from app.config import APP_VERSION


@dataclass(frozen=True, slots=True)
class ReleaseHighlight:
    title: str
    description: str
    details: tuple[str, ...]
    action_label: str
    destination: str
    artwork: str


@dataclass(frozen=True, slots=True)
class InstalledRelease:
    version: str
    headline: str
    summary: str
    highlights: tuple[ReleaseHighlight, ...]


CURRENT_RELEASE = InstalledRelease(
    version=APP_VERSION,
    headline="Mais controle e agilidade no seu dia a dia",
    summary=(
        "Conheça as principais melhorias disponíveis nesta versão e abra cada "
        "recurso diretamente por esta central."
    ),
    highlights=(
        ReleaseHighlight(
            title="Saltos sob seu controle",
            description=(
                "Confira os registros antes de importar e escolha quando receber "
                "o próximo lembrete de atualização."
            ),
            details=(
                "Prévia de novos, duplicados e rejeitados",
                "Confirmação antes de gravar o histórico",
                "Lembrete configurável, inicialmente em 40 dias",
            ),
            action_label="Abrir Saltos",
            destination="Saltos",
            artwork="warps",
        ),
        ReleaseHighlight(
            title="Planejamento mais flexível",
            description=(
                "Use o pity e a garantia importados ou informe valores manuais "
                "quando o histórico estiver incompleto."
            ),
            details=(
                "Alternância sem perder os dados importados",
                "Origem dos valores indicada na tela",
                "Edição de recursos com resposta mais rápida",
            ),
            action_label="Abrir Planejador",
            destination="Planejador",
            artwork="import",
        ),
        ReleaseHighlight(
            title="Builds e relíquias renovadas",
            description=(
                "Analise personagens e equipamentos em telas mais compactas, "
                "com navegação que preserva os dados durante a sessão."
            ),
            details=(
                "Histórico de builds com notas e favoritos",
                "Retenção configurável de versões salvas",
                "Inventário responsivo e acesso mais rápido",
            ),
            action_label="Abrir Builds",
            destination="Builds",
            artwork="backup",
        ),
        ReleaseHighlight(
            title="Mais conforto ao navegar",
            description=(
                "Abas de UID, tarefas em segundo plano e novas opções de "
                "inicialização deixam o aplicativo mais prático."
            ),
            details=(
                "Até oito abas de UID com cache de sessão",
                "Início com o Windows e permanência na bandeja opcionais",
                "Tempos e memória da sessão no Diagnóstico",
            ),
            action_label="Abrir configurações",
            destination="Configurações",
            artwork="experience",
        ),
    ),
)


class WhatsNewSettings:
    def __init__(self, settings: QSettings | None = None) -> None:
        self.settings = settings or QSettings("AstralOptimizer", "WhatsNew")

    def last_seen_version(self) -> str:
        return str(self.settings.value("last_seen_version", ""))

    def should_show(self, version: str = APP_VERSION) -> bool:
        return self.last_seen_version() != version

    def mark_seen(self, version: str = APP_VERSION) -> None:
        self.settings.setValue("last_seen_version", version)
        self.settings.sync()
