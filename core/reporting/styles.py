"""Configuración de estilos visuales para reportes METIS.

Define colores, fuentes y parámetros de diseño consistentes
para todas las visualizaciones y reportes generados por METIS.
"""

from dataclasses import dataclass


# Colores METIS
METIS_BLUE = "#1E40AF"  # Azul corporativo
METIS_DARK_BLUE = "#1E3A8A"
METIS_LIGHT_BLUE = "#3B82F6"
METIS_GREEN = "#10B981"
METIS_RED = "#EF4444"
METIS_GRAY = "#6B7280"
METIS_LIGHT_GRAY = "#E5E7EB"

# Colores para gráficos
COLOR_SERIE = "black"
COLOR_FILL = "grey"
COLOR_TREND = METIS_BLUE
COLOR_OUTLIER = METIS_RED
COLOR_BOXPLOT_BLUE = "#93C5FD"
COLOR_BOXPLOT_GREEN = "#86EFAC"
COLOR_NORMAL_CURVE = METIS_BLUE

# Nombres de meses en español
MONTH_NAMES = [
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
]

# Orden hidrológico (junio a mayo)
HYDROLOGICAL_ORDER = list(range(6, 13)) + list(range(1, 6))
HYDROLOGICAL_LABELS = [MONTH_NAMES[m - 1] for m in HYDROLOGICAL_ORDER]


@dataclass
class FigureConfig:
    """Configuración base para figuras matplotlib."""

    figsize: tuple[float, float] = (10, 6)
    dpi: int = 100
    facecolor: str = "white"
    edgecolor: str = "none"


@dataclass
class PlotStyle:
    """Estilos para elementos de gráficos."""

    linewidth: float = 0.8
    alpha_fill: float = 0.5
    marker_size: float = 10
    grid_alpha: float = 0.3
    label_fontsize: int = 10
    title_fontsize: int = 12
    tick_fontsize: int = 8


@dataclass
class PDFConfig:
    """Configuración para generación de PDFs."""

    figsize_pdf: tuple[float, float] = (14, 8)
    dpi_pdf: int = 100
    title_fontsize: int = 24
    subtitle_fontsize: int = 18
    text_fontsize: int = 11
    table_fontsize: int = 9

    # Colores para PDF
    border_color: str = METIS_DARK_BLUE
    title_color: str = METIS_BLUE
    subtitle_color: str = "black"
    author_color: str = "black"

    # Textos para carátula
    institution: str = "METIS - Sistema de Análisis Hidrológico"
    report_type: str = "REPORTE DE ANÁLISIS ESTADÍSTICO"
    author: str = "Proyecto Integrador ISI UCC"


# Instancias de configuración por defecto
DEFAULT_FIGURE_CONFIG = FigureConfig()
DEFAULT_PLOT_STYLE = PlotStyle()
DEFAULT_PDF_CONFIG = PDFConfig()


def get_y_range(series_values):
    """Calcula rango dinámico para eje Y basado en valores de la serie.

    Args:
        series_values: Array de valores numéricos.

    Returns:
        Tupla (min, max) para el rango del eje Y.
    """
    max_val = series_values.max()
    min_val = series_values.min()

    if min_val >= 0:
        return (0, max_val * 1.25)
    abs_max = max(abs(max_val), abs(min_val))
    return (-abs_max * 1.25, abs_max * 1.25)


def apply_metis_style(fig):
    """Aplica estilo METIS a una figura matplotlib.

    Args:
        fig: Figura matplotlib.
    """
    fig.patch.set_facecolor(DEFAULT_FIGURE_CONFIG.facecolor)
    for ax in fig.axes:
        ax.grid(visible=True, alpha=DEFAULT_PLOT_STYLE.grid_alpha, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
