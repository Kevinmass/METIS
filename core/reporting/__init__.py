"""Módulo de reportes y visualización para METIS.

Este módulo proporciona funcionalidades para generar visualizaciones
y reportes PDF basados en el análisis estadístico de series hidrológicas.
Incluye funciones adaptadas del sistema SAMHIA con estilo METIS.

Funcionalidades:
    - Generación de gráficos individuales (series temporales, boxplots, etc.)
    - Generación de PDFs multi-página con reportes completos
    - Estilos y configuración visual consistente con METIS
"""

from core.reporting.pdf_generator import (
    ReportConfig,
    generate_samhia_report_pdf,
)
from core.reporting.plots import (
    plot_acf,
    plot_annual_boxplots,
    plot_calendar_facets,
    plot_histogram_normal,
    plot_hydrological_facets,
    plot_monthly_boxplots,
    plot_outliers,
    plot_probability_plot,
    plot_qq,
    plot_time_series,
)


__all__ = [
    # PDF generation
    "ReportConfig",
    "generate_samhia_report_pdf",
    # Plotting functions
    "plot_acf",
    "plot_annual_boxplots",
    "plot_calendar_facets",
    "plot_histogram_normal",
    "plot_hydrological_facets",
    "plot_monthly_boxplots",
    "plot_outliers",
    "plot_probability_plot",
    "plot_qq",
    "plot_time_series",
]
