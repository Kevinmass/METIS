"""Funciones de visualización para análisis hidrológico.

Adaptado del sistema SAMHIA con estilo METIS. Proporciona funciones
para generar gráficos individuales de series temporales, boxplots,
histogramas, QQ plots y autocorrelación.
"""

import matplotlib as mpl
import numpy as np
import pandas as pd


mpl.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from scipy.stats import gaussian_kde

from core.reporting.styles import (
    COLOR_BOXPLOT_BLUE,
    COLOR_BOXPLOT_GREEN,
    COLOR_FILL,
    COLOR_NORMAL_CURVE,
    COLOR_OUTLIER,
    COLOR_SERIE,
    COLOR_TREND,
    DEFAULT_FIGURE_CONFIG,
    DEFAULT_PLOT_STYLE,
    HYDROLOGICAL_LABELS,
    HYDROLOGICAL_ORDER,
    METIS_BLUE,
    METIS_GRAY,
    METIS_GREEN,
    METIS_RED,
    MONTH_NAMES,
    apply_metis_style,
    get_y_range,
)


# Hydrological year starts in June (month 6)
HYDROLOGICAL_YEAR_START_MONTH = 6


def plot_time_series(  # noqa: PLR0913
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    title: str = "Serie Temporal",
    y_label: str | None = None,
    *,
    add_loess: bool = True,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera gráfico de serie temporal con suavizado LOESS opcional.

    Args:
        df: DataFrame con datos temporales.
        date_col: Nombre de columna de fechas.
        value_col: Nombre de columna de valores.
        title: Título del gráfico.
        y_label: Etiqueta del eje Y.
        add_loess: Si True, agrega curva LOESS.
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    valid = df.dropna(subset=[value_col]).copy()
    valid[date_col] = pd.to_datetime(valid[date_col])

    fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_CONFIG.figsize)

    # Serie completa con fill
    ax.fill_between(
        valid[date_col],
        valid[value_col],
        alpha=DEFAULT_PLOT_STYLE.alpha_fill,
        color=COLOR_FILL,
    )
    ax.plot(
        valid[date_col],
        valid[value_col],
        color=COLOR_SERIE,
        linewidth=DEFAULT_PLOT_STYLE.linewidth,
    )

    # LOESS smoothing
    if add_loess and len(valid) > 3:  # noqa: PLR2004
        x_vals = valid[date_col].astype(np.int64).to_numpy()
        y_vals = valid[value_col].to_numpy()
        lowess_result = sm.nonparametric.lowess(y_vals, x_vals, frac=0.3)
        ax.plot(
            valid[date_col],
            lowess_result[:, 1],
            color=COLOR_TREND,
            linewidth=1.5,
            label="Tendencia LOESS",
        )

    ax.set_title(title, fontsize=DEFAULT_PLOT_STYLE.title_fontsize)
    ax.set_xlabel("Fecha", fontsize=DEFAULT_PLOT_STYLE.label_fontsize)
    ax.set_ylabel(y_label or value_col, fontsize=DEFAULT_PLOT_STYLE.label_fontsize)

    y_range = get_y_range(df[value_col].dropna().to_numpy())
    ax.set_ylim(y_range)

    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_calendar_facets(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    year_col: str | None = None,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera gráfico facetado por año calendario.

    Args:
        df: DataFrame con datos temporales.
        date_col: Nombre de columna de fechas.
        value_col: Nombre de columna de valores.
        year_col: Nombre de columna de años (si None, se calcula desde date_col).
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    if year_col is None:
        df["year"] = df[date_col].dt.year
        year_col = "year"

    years = sorted(df[year_col].dropna().unique())
    ncols = min(4, len(years))
    nrows = int(np.ceil(len(years) / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(10, max(4, nrows * 2.5)))
    axes = np.array(axes).flatten()

    y_range = get_y_range(df[value_col].dropna().to_numpy())

    for i, yr in enumerate(years):
        ax = axes[i]
        sub = df[df[year_col] == yr].dropna(subset=[value_col])
        sub[date_col] = pd.to_datetime(sub[date_col])

        ax.fill_between(
            sub[date_col],
            sub[value_col],
            alpha=DEFAULT_PLOT_STYLE.alpha_fill,
            color=COLOR_FILL,
        )
        ax.plot(
            sub[date_col],
            sub[value_col],
            color=COLOR_SERIE,
            linewidth=DEFAULT_PLOT_STYLE.linewidth,
        )
        ax.set_title(f"Año {int(yr)}", fontsize=7)
        ax.set_ylim(y_range)
        ax.tick_params(labelsize=6)

    # Ocultar ejes vacíos
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        "Gráfico dividido por Año Calendario",
        fontsize=DEFAULT_PLOT_STYLE.title_fontsize,
    )
    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_hydrological_facets(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    hydro_year_col: str | None = None,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera gráfico facetado por año hidrológico (junio-mayo).

    Args:
        df: DataFrame con datos temporales.
        date_col: Nombre de columna de fechas.
        value_col: Nombre de columna de valores.
        hydro_year_col: Nombre de columna de años hidrológicos.
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    if hydro_year_col is None:
        # Año hidrológico: junio comienza año siguiente
        df["year_hydrological"] = np.where(
            df[date_col].dt.month >= HYDROLOGICAL_YEAR_START_MONTH,
            df[date_col].dt.year,
            df[date_col].dt.year - 1,
        )
        hydro_year_col = "year_hydrological"

    hydro_years = sorted(df[hydro_year_col].dropna().unique())
    ncols = min(4, len(hydro_years))
    nrows = int(np.ceil(len(hydro_years) / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(10, max(4, nrows * 2.5)))
    axes = np.array(axes).flatten()

    y_range = get_y_range(df[value_col].dropna().to_numpy())

    for i, hy in enumerate(hydro_years):
        ax = axes[i]
        sub = df[df[hydro_year_col] == hy].dropna(subset=[value_col])
        sub[date_col] = pd.to_datetime(sub[date_col])

        ax.fill_between(
            sub[date_col],
            sub[value_col],
            alpha=DEFAULT_PLOT_STYLE.alpha_fill,
            color=COLOR_FILL,
        )
        ax.plot(
            sub[date_col],
            sub[value_col],
            color=COLOR_SERIE,
            linewidth=DEFAULT_PLOT_STYLE.linewidth,
        )
        ax.set_title(f"H-{int(hy)}", fontsize=7)
        ax.set_ylim(y_range)
        ax.tick_params(labelsize=6)

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        "Gráfico dividido por Año Hidrológico",
        fontsize=DEFAULT_PLOT_STYLE.title_fontsize,
    )
    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_outliers(  # noqa: PLR0913
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    lower_limit: float,
    upper_limit: float,
    outliers_df: pd.DataFrame | None = None,
    y_label: str | None = None,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera gráfico de serie con límites de outliers marcados.

    Args:
        df: DataFrame con datos temporales.
        date_col: Nombre de columna de fechas.
        value_col: Nombre de columna de valores.
        lower_limit: Límite inferior para outliers.
        upper_limit: Límite superior para outliers.
        outliers_df: DataFrame con outliers detectados.
        y_label: Etiqueta del eje Y.
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    valid = df.dropna(subset=[value_col])

    fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_CONFIG.figsize)

    ax.plot(
        valid[date_col],
        valid[value_col],
        color=COLOR_SERIE,
        linewidth=DEFAULT_PLOT_STYLE.linewidth,
    )
    ax.axhline(upper_limit, linestyle="--", color=METIS_RED, label="Límite superior")
    ax.axhline(lower_limit, linestyle="--", color=METIS_RED, label="Límite inferior")

    if outliers_df is not None and not outliers_df.empty:
        outliers_df = outliers_df.copy()
        outliers_df[date_col] = pd.to_datetime(outliers_df[date_col])
        ax.scatter(
            outliers_df[date_col],
            outliers_df[value_col],
            color=COLOR_OUTLIER,
            zorder=5,
            s=20,
            label="Outliers",
        )

    ax.set_title(
        "Análisis de Datos Atípicos", fontsize=DEFAULT_PLOT_STYLE.title_fontsize
    )
    ax.set_xlabel("Fecha", fontsize=DEFAULT_PLOT_STYLE.label_fontsize)
    ax.set_ylabel(y_label or value_col, fontsize=DEFAULT_PLOT_STYLE.label_fontsize)

    y_range = get_y_range(df[value_col].dropna().to_numpy())
    ax.set_ylim(y_range)
    ax.legend()

    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_monthly_boxplots(  # noqa: PLR0913
    df: pd.DataFrame,
    value_col: str,
    month_col: str | None = None,
    *,
    hydrological: bool = False,
    y_label: str | None = None,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera boxplots mensuales (calendario o hidrológico).

    Args:
        df: DataFrame con datos.
        value_col: Nombre de columna de valores.
        month_col: Nombre de columna de meses (1-12).
        hydrological: Si True, usa orden hidrológico (jun-may).
        y_label: Etiqueta del eje Y.
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    df = df.copy()

    if month_col is None:
        df["month"] = pd.to_datetime(df["date"]).dt.month
        month_col = "month"

    if hydrological:
        order = HYDROLOGICAL_ORDER
        labels = HYDROLOGICAL_LABELS
        title = "Valores Mensuales (Año Hidrológico)"
        color = COLOR_BOXPLOT_GREEN
    else:
        order = list(range(1, 13))
        labels = MONTH_NAMES
        title = "Valores Mensuales (Año Calendario)"
        color = COLOR_BOXPLOT_BLUE

    fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_CONFIG.figsize)

    data_by_month = [
        df[df[month_col] == m][value_col].dropna().to_numpy() for m in order
    ]

    bp = ax.boxplot(data_by_month, tick_labels=labels, patch_artist=True, sym="")
    for patch in bp["boxes"]:
        patch.set_facecolor(color)

    ax.set_title(title, fontsize=DEFAULT_PLOT_STYLE.title_fontsize)
    ax.set_xlabel("Mes", fontsize=DEFAULT_PLOT_STYLE.label_fontsize)
    ax.set_ylabel(y_label or value_col, fontsize=DEFAULT_PLOT_STYLE.label_fontsize)
    ax.tick_params(labelsize=DEFAULT_PLOT_STYLE.tick_fontsize)

    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_annual_boxplots(
    df: pd.DataFrame,
    value_col: str,
    hydro_year_col: str | None = None,
    y_label: str | None = None,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera boxplots por año hidrológico.

    Args:
        df: DataFrame con datos.
        value_col: Nombre de columna de valores.
        hydro_year_col: Nombre de columna de años hidrológicos.
        y_label: Etiqueta del eje Y.
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    if hydro_year_col is None:
        df["year_hydrological"] = np.where(
            df["date"].dt.month >= HYDROLOGICAL_YEAR_START_MONTH,
            df["date"].dt.year,
            df["date"].dt.year - 1,
        )
        hydro_year_col = "year_hydrological"

    hydro_years = sorted(df[hydro_year_col].dropna().unique())
    hydro_labels = [str(int(y)) for y in hydro_years]

    fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_CONFIG.figsize)

    data_by_hydro = [
        df[df[hydro_year_col] == y][value_col].dropna().to_numpy() for y in hydro_years
    ]

    bp = ax.boxplot(data_by_hydro, tick_labels=hydro_labels, patch_artist=True, sym="")
    for patch in bp["boxes"]:
        patch.set_facecolor(COLOR_BOXPLOT_BLUE)

    ax.set_title(
        "Box-plot año hidrológico (Anual)", fontsize=DEFAULT_PLOT_STYLE.title_fontsize
    )
    ax.set_xlabel("Año Hidrológico", fontsize=DEFAULT_PLOT_STYLE.label_fontsize)
    ax.set_ylabel(y_label or value_col, fontsize=DEFAULT_PLOT_STYLE.label_fontsize)
    ax.tick_params(axis="x", rotation=90, labelsize=DEFAULT_PLOT_STYLE.tick_fontsize)

    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_histogram_normal(
    series: pd.Series,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera histograma con curva normal superpuesta.

    Args:
        series: Serie de valores numéricos.
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    values = series.dropna().to_numpy()
    media_val = float(np.mean(values))
    sd_val = float(np.std(values, ddof=1))

    fig, ax = plt.subplots(figsize=(6, 6))

    ax.hist(
        values,
        bins="auto",
        density=True,
        alpha=DEFAULT_PLOT_STYLE.alpha_fill,
        color=COLOR_FILL,
        edgecolor="white",
    )

    xmin, xmax = ax.get_xlim()
    x = np.linspace(xmin, xmax, 200)
    ax.plot(
        x,
        stats.norm.pdf(x, media_val, sd_val),
        color=COLOR_NORMAL_CURVE,
        linewidth=2,
        label="Normal",
    )

    ax.set_title("Histograma y Normal", fontsize=DEFAULT_PLOT_STYLE.title_fontsize)
    ax.set_xlabel("Variable", fontsize=DEFAULT_PLOT_STYLE.label_fontsize)
    ax.legend()

    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_qq(
    series: pd.Series,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera Q-Q plot para evaluación de normalidad.

    Args:
        series: Serie de valores numéricos.
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    values = series.dropna().to_numpy()

    fig, ax = plt.subplots(figsize=(6, 6))

    (osm, osr), (slope, intercept, _r) = stats.probplot(values, dist="norm")
    ax.scatter(osm, osr, color="black", s=10)
    ax.plot(
        osm, slope * np.array(osm) + intercept, color=COLOR_NORMAL_CURVE, linewidth=2
    )

    ax.set_title("Q-Q Plot - Normal", fontsize=DEFAULT_PLOT_STYLE.title_fontsize)
    ax.set_xlabel("Cuantiles Teóricos", fontsize=DEFAULT_PLOT_STYLE.label_fontsize)
    ax.set_ylabel("Cuantiles Observados", fontsize=DEFAULT_PLOT_STYLE.label_fontsize)

    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_acf(
    series: pd.Series,
    lags: int | None = None,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera gráfico de función de autocorrelación.

    Args:
        series: Serie de valores numéricos.
        lags: Número de lags a mostrar. Si None, usa min(40, n//2-1).
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    values = series.dropna().to_numpy()
    n = len(values)

    if lags is None:
        lags = min(40, n // 2 - 1)

    fig, ax = plt.subplots(figsize=(8, 6))

    sm.graphics.tsa.plot_acf(
        values, ax=ax, lags=lags, title="Función de Autocorrelación"
    )

    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_probability_plot(  # noqa: C901, PLR0913, PLR0915
    series: pd.Series,
    lower_limit: float | None = None,
    upper_limit: float | None = None,
    distribution: str = "lognormal",
    y_label: str | None = None,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera gráfico de probabilidad en escala logarítmica con límites Kn.

    Este gráfico es el compañero visual ideal del método Kn para detección
    de outliers. Muestra los datos ordenados en escala logarítmica vs su
    probabilidad de no excedencia, con la curva teórica de distribución
    y líneas horizontales marcando los umbrales calculados con Kn.

    Args:
        series: Serie de valores numéricos (caudales, precipitaciones).
        lower_limit: Límite inferior calculado con Kn (opcional).
        upper_limit: Límite superior calculado con Kn (opcional).
        distribution: Distribución teórica ('lognormal', 'pearson3', 'gumbel').
        y_label: Etiqueta del eje Y.
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    values = series.dropna().to_numpy()
    n = len(values)

    # Ordenar datos y calcular probabilidades empíricas (Weibull)
    sorted_values = np.sort(values)
    ranks = np.arange(1, n + 1)
    # Probabilidad de no excedencia: i/(n+1)
    empirical_prob = ranks / (n + 1)
    # Periodo de retorno: T = 1/(1-F)
    return_period = 1 / (1 - empirical_prob)

    # Calcular curva teórica según distribución
    log_values = np.log(sorted_values)
    mu = np.mean(log_values)
    sigma = np.std(log_values, ddof=1)

    # Generar curva teórica suave
    prob_smooth = np.linspace(0.001, 0.999, 500)
    return_smooth = 1 / (1 - prob_smooth)

    if distribution == "lognormal":
        # Log-Normal: ln(X) ~ Normal(mu, sigma)
        theoretical_quantiles = stats.norm.ppf(prob_smooth, loc=mu, scale=sigma)
        theoretical_values = np.exp(theoretical_quantiles)
    elif distribution == "pearson3":
        # Log-Pearson III aproximado usando gamma
        _skew = stats.skew(log_values)
        # Ajuste simplificado usando normal para el log
        theoretical_quantiles = stats.norm.ppf(prob_smooth, loc=mu, scale=sigma)
        theoretical_values = np.exp(theoretical_quantiles)
    elif distribution == "gumbel":
        # Gumbel para valores extremos
        # Parámetros de Gumbel
        beta = np.std(values, ddof=1) * np.sqrt(6) / np.pi
        mu_gumbel = np.mean(values) - 0.5772 * beta
        theoretical_values = mu_gumbel - beta * np.log(-np.log(prob_smooth))
    else:
        # Log-Normal por defecto
        theoretical_quantiles = stats.norm.ppf(prob_smooth, loc=mu, scale=sigma)
        theoretical_values = np.exp(theoretical_quantiles)

    # Crear figura
    fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_CONFIG.figsize)

    # Eje X: Período de retorno en escala logarítmica
    ax.set_xscale("log")
    ax.set_yscale("log")

    # Datos empíricos
    ax.scatter(
        return_period,
        sorted_values,
        color="black",
        s=30,
        zorder=3,
        label="Datos observados",
    )

    # Curva teórica
    ax.plot(
        return_smooth,
        theoretical_values,
        color=METIS_BLUE,
        linewidth=2,
        zorder=2,
        label=f"Distribución {distribution.title()}",
    )

    # Líneas de umbrales Kn
    if upper_limit is not None:
        ax.axhline(
            upper_limit,
            linestyle="--",
            color=METIS_RED,
            linewidth=2,
            zorder=4,
            label=f"Límite Superior Kn ({upper_limit:.2f})",
        )

    if lower_limit is not None:
        ax.axhline(
            lower_limit,
            linestyle="--",
            color=METIS_RED,
            linewidth=2,
            zorder=4,
            label=f"Límite Inferior Kn ({lower_limit:.2f})",
        )

    # Identificar outliers visuales (puntos fuera de límites)
    if upper_limit is not None or lower_limit is not None:
        outlier_mask = np.zeros(n, dtype=bool)
        if upper_limit is not None:
            outlier_mask = outlier_mask | (sorted_values > upper_limit)
        if lower_limit is not None:
            outlier_mask = outlier_mask | (sorted_values < lower_limit)

        if np.any(outlier_mask):
            ax.scatter(
                return_period[outlier_mask],
                sorted_values[outlier_mask],
                color=METIS_RED,
                s=60,
                zorder=5,
                marker="X",
                edgecolors="white",
                linewidths=1,
                label="Valores atípicos",
            )

    # Configuración de ejes
    ax.set_xlabel(
        "Período de Retorno (años)", fontsize=DEFAULT_PLOT_STYLE.label_fontsize
    )
    ax.set_ylabel(
        y_label or "Valor (escala log)", fontsize=DEFAULT_PLOT_STYLE.label_fontsize
    )
    ax.set_title(
        "Gráfico de Probabilidad con Límites Kn",
        fontsize=DEFAULT_PLOT_STYLE.title_fontsize,
    )

    # Grid
    ax.grid(visible=True, which="both", ls="-", alpha=0.2, color="gray")

    # Leyenda
    ax.legend(loc="upper left", fontsize=9)

    # Ajustar límites
    if len(sorted_values) > 0:
        y_min = sorted_values[0] * 0.8 if sorted_values[0] > 0 else 0.1
        y_max = sorted_values[-1] * 1.2
        ax.set_ylim(y_min, y_max)

    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig


def plot_fdp(  # noqa: PLR0913 - 6 args needed for flexibility
    series: pd.Series,
    lower_limit: float | None = None,
    upper_limit: float | None = None,
    outliers_indices: list[int] | None = None,
    y_label: str | None = None,
    output_path: str | None = None,
) -> plt.Figure:
    """Genera gráfico de Función de Densidad de Probabilidad (FDP/KDE).

    Muestra la distribución de los datos mediante Kernel Density Estimate (KDE)
    con histograma superpuesto. Incluye líneas verticales para los límites Kn
    y destaca visualmente los outliers detectados.

    Args:
        series: Serie temporal de valores numéricos.
        lower_limit: Límite inferior calculado con Kn (opcional).
        upper_limit: Límite superior calculado con Kn (opcional).
        outliers_indices: Índices de los outliers detectados (opcional).
        y_label: Etiqueta para el eje X (descripción de la variable).
        output_path: Si proporcionado, guarda el gráfico en esta ruta.

    Returns:
        Figura matplotlib.
    """
    values = series.dropna().to_numpy()
    n = len(values)

    # Calcular estadísticos
    media_val = float(np.mean(values))
    sd_val = float(np.std(values, ddof=1))

    fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_CONFIG.figsize)

    # Histograma con normalización de densidad
    _counts, _bins, _patches = ax.hist(
        values,
        bins="auto",
        density=True,
        alpha=DEFAULT_PLOT_STYLE.alpha_fill,
        color=COLOR_FILL,
        edgecolor="white",
        label="Histograma",
    )

    # KDE (Kernel Density Estimate)
    kde = gaussian_kde(values)
    x_range = np.linspace(values.min() * 0.9, values.max() * 1.1, 500)
    kde_values = kde(x_range)
    ax.plot(
        x_range,
        kde_values,
        color=METIS_BLUE,
        linewidth=2.5,
        label="Densidad KDE",
        zorder=3,
    )

    # Curva teórica Log-Normal (basada en los parámetros de los datos)
    if np.all(values > 0):
        log_values = np.log(values)
        mu = np.mean(log_values)
        sigma = np.std(log_values, ddof=1)
        theoretical_lognormal = stats.lognorm.pdf(x_range, s=sigma, scale=np.exp(mu))
        ax.plot(
            x_range,
            theoretical_lognormal,
            color=METIS_GREEN,
            linestyle="--",
            linewidth=2,
            label="Log-Normal teórica",
            zorder=2,
            alpha=0.8,
        )

    # Líneas verticales para límites Kn
    if lower_limit is not None:
        ax.axvline(
            lower_limit,
            color=METIS_RED,
            linestyle="--",
            linewidth=2,
            zorder=4,
            label=f"Límite Kn Inf ({lower_limit:.2f})",
        )
        # Sombrear área de rechazo inferior
        ax.fill_betweenx(
            [0, ax.get_ylim()[1] * 1.1],
            values.min() * 0.9,
            lower_limit,
            alpha=0.15,
            color=METIS_RED,
            zorder=1,
        )

    if upper_limit is not None:
        ax.axvline(
            upper_limit,
            color=METIS_RED,
            linestyle="--",
            linewidth=2,
            zorder=4,
            label=f"Límite Kn Sup ({upper_limit:.2f})",
        )
        # Sombrear área de rechazo superior
        ax.fill_betweenx(
            [0, ax.get_ylim()[1] * 1.1],
            upper_limit,
            values.max() * 1.1,
            alpha=0.15,
            color=METIS_RED,
            zorder=1,
        )

    # Marcar valores atípicos en la curva de densidad
    if outliers_indices and len(outliers_indices) > 0:
        outlier_values = values[outliers_indices]
        outlier_densities = kde(outlier_values)
        ax.scatter(
            outlier_values,
            outlier_densities,
            color=METIS_RED,
            s=80,
            zorder=5,
            marker="X",
            edgecolors="white",
            linewidths=1.5,
            label=f"Outliers ({len(outliers_indices)})",
        )

    # Anotar estadísticos clave

    stats_text = f"μ = {media_val:.2f}\nσ = {sd_val:.2f}\nn = {n}"  # noqa: RUF001
    ax.text(
        0.97,
        0.97,
        stats_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        horizontalalignment="right",
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": "white",
            "alpha": 0.8,
            "edgecolor": METIS_GRAY,
        },
    )

    ax.set_title(
        "Función de Densidad de Probabilidad (FDP)",
        fontsize=DEFAULT_PLOT_STYLE.title_fontsize,
    )
    ax.set_xlabel(
        y_label or "Valor",
        fontsize=DEFAULT_PLOT_STYLE.label_fontsize,
    )
    ax.set_ylabel(
        "Densidad de probabilidad",
        fontsize=DEFAULT_PLOT_STYLE.label_fontsize,
    )

    ax.legend(loc="upper left", fontsize=9)

    apply_metis_style(fig)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=DEFAULT_FIGURE_CONFIG.dpi, bbox_inches="tight")

    return fig
