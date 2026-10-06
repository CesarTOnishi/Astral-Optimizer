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
    headline="Cartões e histórico de Saltos renovados",
    summary=(
        "Esta atualização melhora as imagens compartilhadas de builds e Saltos "
        "e esclarece os resultados de 50/50."
    ),
    highlights=(
        ReleaseHighlight(
            title="Cartão de build renovado",
            description=(
                "A exportação da build apresenta a personagem, seus equipamentos "
                "e seus atributos em uma composição 1920 × 1080."
            ),
            details=(
                "Habilidades e Eidolons conforme os dados da personagem",
                "Relíquias e cone com atributos reais",
                "Benchmark e equipe integrados ao cartão",
            ),
            action_label="Abrir Builds",
            destination="Builds",
            artwork="experience",
        ),
        ReleaseHighlight(
            title="Histórico de Saltos para compartilhar",
            description=(
                "O relatório exportado reúne resultados 5★ em tickets compactos "
                "com retrato, data e número de saltos."
            ),
            details=(
                "Resultados em ordem cronológica inversa",
                "Páginas adicionais quando há muitos resultados",
                "Vitória, derrota e garantia identificadas por texto e símbolo",
            ),
            action_label="Abrir Saltos",
            destination="Saltos",
            artwork="warps",
        ),
        ReleaseHighlight(
            title="Totais corretos por edição",
            description=(
                "Ao exportar uma edição específica, o cabeçalho agora usa "
                "somente seus saltos, Jades equivalentes e período."
            ),
            details=(
                "Filtro da edição aplicado aos totais",
                "Jades rotulados como valor equivalente",
                "Categoria inteira preservada em Todos os saltos",
            ),
            action_label="Abrir Saltos",
            destination="Saltos",
            artwork="import",
        ),
        ReleaseHighlight(
            title="Resultados de 50/50 mais claros",
            description=(
                "A classificação usa os dados do histórico e o destaque "
                "identificado para a edição do banner."
            ),
            details=(
                "Ganhou, perdeu e garantido exibidos separadamente",
                "Personagens repetidos permanecem individuais",
                "Retratos locais usados quando disponíveis",
            ),
            action_label="Abrir Saltos",
            destination="Saltos",
            artwork="backup",
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
