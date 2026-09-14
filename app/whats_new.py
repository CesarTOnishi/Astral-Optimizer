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
    headline="Uma experiência mais visual, segura e completa",
    summary=(
        "Conheça as principais melhorias disponíveis nesta versão e abra cada "
        "recurso diretamente por esta central."
    ),
    highlights=(
        ReleaseHighlight(
            title="Cartão avançado de Saltos",
            description=(
                "Transforme seu histórico em uma imagem pronta para compartilhar, "
                "agora com estatísticas completas."
            ),
            details=(
                "Todos os resultados 5★ e seus pitys",
                "Média, mediana, melhor e pior pity",
                "Cores diferentes para pity baixo, médio e alto",
            ),
            action_label="Abrir Saltos",
            destination="Saltos",
            artwork="warps",
        ),
        ReleaseHighlight(
            title="Importação guiada do jogo",
            description=(
                "Um vídeo curto mostra como preparar o Histórico de Saltos antes "
                "de importar."
            ),
            details=(
                "Tutorial disponível sempre que precisar",
                "Seleção manual da pasta webCaches",
                "Detecção da versão de cache mais recente",
            ),
            action_label="Ver área de importação",
            destination="Saltos",
            artwork="import",
        ),
        ReleaseHighlight(
            title="Backup pelo OneDrive",
            description=(
                "Proteja seu histórico em uma pasta sincronizada, sem entregar sua "
                "senha da Microsoft ao Astral."
            ),
            details=(
                "Backup automático após cada importação",
                "Arquivos versionados e verificados por integridade",
                "Restauração do último backup válido",
            ),
            action_label="Configurar backup",
            destination="Backup",
            artwork="backup",
        ),
        ReleaseHighlight(
            title="Design e experiência renovados",
            description=(
                "A interface ganhou ícones próprios, movimentos mais suaves e uma "
                "organização visual mais consistente."
            ),
            details=(
                "Ícones reais para atributos e relíquias",
                "Cartões e barras de rolagem aprimorados",
                "Seis temas com aplicação imediata",
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
