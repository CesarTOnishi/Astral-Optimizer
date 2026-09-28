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
    headline="Compatibilidade com os dados do jogo 4.6",
    summary=(
        "Esta atualização melhora a consulta de personagens e equipamentos "
        "novos e atualiza o motor de análise."
    ),
    highlights=(
        ReleaseHighlight(
            title="Consultas recuperadas",
            description=(
                "O app agora atualiza os dados da Enka quando encontra um ID "
                "novo e interpreta a resposta recebida novamente."
            ),
            details=(
                "Corrigida a falha ao ler alguns atributos",
                "Nomes complementados pelo catálogo quando necessário",
                "Aviso claro se os dados do jogo ainda estiverem indisponíveis",
            ),
            action_label="Abrir Conta",
            destination="Conta",
            artwork="warps",
        ),
        ReleaseHighlight(
            title="Pearl e novos equipamentos",
            description=(
                "Personagens, Cones de Luz e conjuntos de relíquias novos "
                "entram no catálogo assim que os dados públicos chegam."
            ),
            details=(
                "Pearl reconhecida pelo catálogo",
                "Nomes de conjuntos complementados pelo StarRailRes",
                "Dados essenciais ausentes são indicados na tela",
            ),
            action_label="Abrir Catálogo",
            destination="Personagens e Cones",
            artwork="import",
        ),
        ReleaseHighlight(
            title="Motor de análise atualizado",
            description=(
                "O motor Fribbels, os pesos de relíquias e os times padrão "
                "acompanham o catálogo recente."
            ),
            details=(
                "Fribbels atualizado para os dados recentes",
                "Pesos e times padrão sincronizados",
                "Sem alterações locais nas regras de pontuação",
            ),
            action_label="Abrir Builds",
            destination="Builds",
            artwork="backup",
        ),
        ReleaseHighlight(
            title="Imagens e janelas corrigidas",
            description=(
                "O retrato local aparece quando o CDN da Enka ainda não "
                "publicou o ícone de um personagem novo."
            ),
            details=(
                "Fallback local para imagens de personagens novos",
                "Botões de recuperação não abrem janelas extras",
                "Consulta preserva dados válidos quando possível",
            ),
            action_label="Abrir Builds",
            destination="Builds",
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
