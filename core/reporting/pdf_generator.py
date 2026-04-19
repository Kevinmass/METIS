"""Generador de reportes PDF para análisis hidrológico.

Adaptado del sistema SAMHIA con estilo METIS. Genera reportes
multi-página con visualizaciones y resultados estadísticos.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd


mpl.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm
from matplotlib.backends.backend_pdf import PdfPages
from scipy import stats

from core.reporting.styles import (
    COLOR_BOXPLOT_BLUE,
    COLOR_BOXPLOT_GREEN,
    DEFAULT_PDF_CONFIG,
    HYDROLOGICAL_LABELS,
    HYDROLOGICAL_ORDER,
    METIS_BLUE,
    METIS_DARK_BLUE,
    METIS_RED,
    MONTH_NAMES,
    get_y_range,
)
from core.validation.homogeneity import (
    cramer_test,
    helmert_test,
    mann_whitney_test,
    mood_test,
    t_student_test,
)
from core.validation.independence import (
    anderson_test,
    durbin_watson_test,
    ljung_box_test,
    spearman_test,
    wald_wolfowitz_test,
)
from core.validation.outliers import (
    chow_test,
    kn_outlier_detection,
)
from core.validation.trend import (
    kolmogorov_smirnov_trend_test,
    mann_kendall_test,
)


@dataclass
class ReportConfig:
    """Configuración para generación de reporte PDF."""

    series_name: str
    reservoir_name: str
    output_path: str
    institution: str = DEFAULT_PDF_CONFIG.institution
    report_type: str = DEFAULT_PDF_CONFIG.report_type
    author: str = DEFAULT_PDF_CONFIG.author
    alpha: float = 0.05


def generate_samhia_report_pdf(  # noqa: C901, PLR0912, PLR0915
    df: pd.DataFrame,
    config: ReportConfig,
) -> str:
    """Genera reporte PDF completo de 10 páginas estilo METIS.

    Args:
        df: DataFrame con columnas 'date' y la variable a analizar.
        config: Configuración del reporte.

    Returns:
        Ruta del PDF generado.
    """
    # Preparar datos
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()].sort_values("date").reset_index(drop=True)

    variable_calc = df[config.series_name].dropna().to_numpy()

    if len(variable_calc) < 12:  # noqa: PLR2004
        msg = "Variable tiene menos de 12 datos válidos"
        raise ValueError(msg)

    # Variables temporales
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    # Hydrological year starts in June (month 6)
    df["year_hydrological"] = np.where(
        df["date"].dt.month >= 6,  # noqa: PLR2004 - June is hydrological year start
        df["date"].dt.year,
        df["date"].dt.year - 1,
    )
    df = df.sort_values("year_hydrological").reset_index(drop=True)

    # Límites dinámicos
    y_range = get_y_range(variable_calc)

    # Outliers Kn
    n_obs = len(variable_calc)
    kn_val = 0.4083 * np.log(n_obs) + 1.1584
    media_val = float(np.mean(variable_calc))
    sd_val = float(np.std(variable_calc, ddof=1))
    limite_superior = media_val + kn_val * sd_val
    limite_inferior = media_val - kn_val * sd_val

    # Detectar outliers
    outliers_df = df[
        (df[config.series_name] > limite_superior)
        | (df[config.series_name] < limite_inferior)
    ].dropna(subset=[config.series_name])

    # Ejecutar tests estadísticos
    independence_results = {
        "anderson": anderson_test(pd.Series(variable_calc), config.alpha),
        "wald_wolfowitz": wald_wolfowitz_test(pd.Series(variable_calc), config.alpha),
        "durbin_watson": durbin_watson_test(pd.Series(variable_calc), config.alpha),
        "ljung_box": ljung_box_test(pd.Series(variable_calc), alpha=config.alpha),
        "spearman": spearman_test(pd.Series(variable_calc), config.alpha),
    }

    homogeneity_results = {
        "helmert": helmert_test(pd.Series(variable_calc), config.alpha),
        "t_student": t_student_test(pd.Series(variable_calc), config.alpha),
        "cramer": cramer_test(pd.Series(variable_calc), config.alpha),
        "mann_whitney": mann_whitney_test(pd.Series(variable_calc), config.alpha),
        "mood": mood_test(pd.Series(variable_calc), config.alpha),
    }

    trend_results = {
        "mann_kendall": mann_kendall_test(pd.Series(variable_calc), config.alpha),
        "kolmogorov_smirnov": kolmogorov_smirnov_trend_test(
            pd.Series(variable_calc), config.alpha
        ),
    }

    # Outlier tests executed but results accessed via independence_results
    chow_test(pd.Series(variable_calc))
    kn_outlier_detection(pd.Series(variable_calc), alpha=config.alpha)

    # Estadísticos descriptivos
    asymmetry = float(stats.skew(variable_calc))
    kurt_val = float(stats.kurtosis(variable_calc, fisher=False))
    var_n_1 = float(np.var(variable_calc, ddof=1))
    coefficient_of_variation = (sd_val / media_val) * 100 if media_val != 0 else np.nan

    q25, q75 = float(np.percentile(variable_calc, 25)), float(
        np.percentile(variable_calc, 75)
    )
    summary_stats = {
        "Estadística": [
            "Mediana",
            "Media",
            "1er Cuartil",
            "3er Cuartil",
            "Mínimo",
            "Máximo",
            "Asimetría",
            "Kurtosis",
            "Desv. Estándar",
            "Varianza (n-1)",
            "N Datos",
            "Coef. Variación",
        ],
        "Valor": [
            round(v, 4)
            for v in [
                float(np.median(variable_calc)),
                media_val,
                q25,
                q75,
                float(variable_calc.min()),
                float(variable_calc.max()),
                asymmetry,
                kurt_val,
                sd_val,
                var_n_1,
                n_obs,
                coefficient_of_variation,
            ]
        ],
    }
    combined_stat_table = pd.DataFrame(summary_stats)

    # Tabla año hidrológico
    tabla_informacion = (
        df.groupby("year_hydrological")[config.series_name]
        .agg(Medio="mean", Maximo="max", Minimo="min")
        .reset_index()
        .round(4)
    )

    # Generar PDF
    pdf_filename = config.output_path
    Path(pdf_filename).parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(pdf_filename) as pdf:
        # PÁGINA 1: CARÁTULA
        fig = plt.figure(figsize=DEFAULT_PDF_CONFIG.figsize_pdf)
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        fig.patch.set_facecolor("white")

        # Marco exterior
        for lw, pad in [(4, 0.01), (1, 0.03)]:
            edge_color = METIS_DARK_BLUE if lw == 4 else "black"  # noqa: PLR2004
            rect = plt.Rectangle(
                (pad, pad),
                1 - 2 * pad,
                1 - 2 * pad,
                linewidth=lw,
                edgecolor=edge_color,
                facecolor="none",
                transform=fig.transFigure,
                figure=fig,
            )
            fig.add_artist(rect)

        texts = [
            (
                0.5,
                0.85,
                config.institution,
                DEFAULT_PDF_CONFIG.subtitle_fontsize,
                "bold",
                METIS_BLUE,
            ),
            (
                0.5,
                0.60,
                "SISTEMA METIS",
                DEFAULT_PDF_CONFIG.title_fontsize,
                "bold",
                METIS_DARK_BLUE,
            ),
            (
                0.5,
                0.53,
                config.report_type,
                DEFAULT_PDF_CONFIG.subtitle_fontsize,
                "normal",
                "black",
            ),
            (0.5, 0.40, f"Embalse: {config.reservoir_name}", 16, "normal", "black"),
            (
                0.5,
                0.35,
                f"Variable Analizada: {config.series_name}",
                16,
                "bold",
                "black",
            ),
            (0.5, 0.20, config.author, 14, "normal", "black", "italic"),
            (
                0.5,
                0.10,
                f"Fecha de Generación: {datetime.now(tz=timezone.utc).date()}",
                10,
                "normal",
                "grey",
            ),
        ]
        for item in texts:
            x, y, txt, fs, fw, fc = item[0], item[1], item[2], item[3], item[4], item[5]
            fontstyle = item[6] if len(item) > 6 else "normal"  # noqa: PLR2004
            fig.text(
                x,
                y,
                txt,
                ha="center",
                va="center",
                fontsize=fs,
                fontweight=fw,
                color=fc,
                fontstyle=fontstyle,
            )

        pdf.savefig(fig)
        plt.close(fig)

        # PÁGINA 2: GRÁFICOS COMBINADOS
        fig, axes = plt.subplots(2, 2, figsize=DEFAULT_PDF_CONFIG.figsize_pdf)

        def _plot_ts(ax, df_plot, title_plot):
            v = df_plot.dropna(subset=[config.series_name])
            ax.fill_between(v["date"], v[config.series_name], alpha=0.5, color="grey")
            ax.plot(v["date"], v[config.series_name], color="black", linewidth=0.8)
            ax.set_title(title_plot, fontsize=9)
            ax.set_ylim(y_range)

        _plot_ts(axes[0, 0], df, "Serie Temporal")
        _plot_ts(axes[0, 1], df, "Año Calendario (global)")
        _plot_ts(axes[1, 0], df, "Año Hidrológico (global)")

        # Atípicos
        ax4 = axes[1, 1]
        vv = df.dropna(subset=[config.series_name])
        ax4.plot(vv["date"], vv[config.series_name], color="black", linewidth=0.8)
        ax4.axhline(limite_superior, linestyle="--", color=METIS_RED)
        ax4.axhline(limite_inferior, linestyle="--", color=METIS_RED)
        if not outliers_df.empty:
            ax4.scatter(
                outliers_df["date"],
                outliers_df[config.series_name],
                color=METIS_RED,
                zorder=5,
                s=20,
            )
        ax4.set_title("Datos Atípicos", fontsize=9)
        ax4.set_ylim(y_range)

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # PÁGINA 3: RESUMEN ESTADÍSTICO Y OUTLIERS
        fig = plt.figure(figsize=DEFAULT_PDF_CONFIG.figsize_pdf)
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        ax.set_title("Resumen Estadístico Descriptivo", fontsize=12, loc="left", pad=10)

        col_labels = list(combined_stat_table.columns)
        cell_text = [
            [str(r["Estadística"]), str(r["Valor"])]
            for _, r in combined_stat_table.iterrows()
        ]
        tbl = ax.table(
            cellText=cell_text,
            colLabels=col_labels,
            cellLoc="center",
            loc="upper left",
            bbox=[0, 0.45, 0.45, 0.55],
        )
        tbl.auto_set_font_size(False)  # noqa: FBT003
        tbl.set_fontsize(DEFAULT_PDF_CONFIG.table_fontsize)

        if not outliers_df.empty:
            display_df = outliers_df.head(20)[["date", config.series_name]].copy()
            display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
            display_df = display_df.round(4)
            ax.text(
                0.5,
                0.98,
                "Datos Atípicos (primeros 20):",
                transform=ax.transAxes,
                fontsize=10,
                va="top",
            )
            tbl2 = ax.table(
                cellText=display_df.to_numpy().tolist(),
                colLabels=list(display_df.columns),
                cellLoc="center",
                loc="upper right",
                bbox=[0.5, 0.45, 0.48, 0.50],
            )
            tbl2.auto_set_font_size(False)  # noqa: FBT003
            tbl2.set_fontsize(8)
        else:
            ax.text(
                0.5,
                0.6,
                "Sin Datos Atípicos detectados bajo criterio normal.",
                transform=ax.transAxes,
                fontsize=10,
                ha="center",
            )

        pdf.savefig(fig)
        plt.close(fig)

        # PÁGINA 4: BOXPLOTS
        fig, axes = plt.subplots(1, 3, figsize=DEFAULT_PDF_CONFIG.figsize_pdf)

        # Mensual calendario
        data_bp = [
            df[df["month"] == m][config.series_name].dropna().to_numpy()
            for m in range(1, 13)
        ]
        bp = axes[0].boxplot(
            data_bp, tick_labels=MONTH_NAMES, patch_artist=True, sym=""
        )
        for p in bp["boxes"]:
            p.set_facecolor(COLOR_BOXPLOT_BLUE)
        axes[0].set_title("Mensual (Año Calendario)", fontsize=9)
        axes[0].tick_params(labelsize=7)

        # Mensual hidrológico
        data_bp_h = [
            df[df["month"] == m][config.series_name].dropna().to_numpy()
            for m in HYDROLOGICAL_ORDER
        ]
        bp2 = axes[1].boxplot(
            data_bp_h, tick_labels=HYDROLOGICAL_LABELS, patch_artist=True, sym=""
        )
        for p in bp2["boxes"]:
            p.set_facecolor(COLOR_BOXPLOT_GREEN)
        axes[1].set_title("Mensual (Año Hidrológico)", fontsize=9)
        axes[1].tick_params(labelsize=7)

        # Anual hidrológico
        hydro_years = sorted(df["year_hydrological"].dropna().unique())
        hydro_labels = [str(int(y)) for y in hydro_years]
        data_by_hydro = [
            df[df["year_hydrological"] == y][config.series_name].dropna().to_numpy()
            for y in hydro_years
        ]
        bp3 = axes[2].boxplot(
            data_by_hydro, tick_labels=hydro_labels, patch_artist=True, sym=""
        )
        for p in bp3["boxes"]:
            p.set_facecolor(COLOR_BOXPLOT_BLUE)
        axes[2].set_title("Anual Hidrológico", fontsize=9)
        axes[2].tick_params(axis="x", rotation=90, labelsize=6)

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # PÁGINA 5: TABLA AÑO HIDROLÓGICO
        fig = plt.figure(figsize=DEFAULT_PDF_CONFIG.figsize_pdf)
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        ax.set_title("Tablas Resumen Año Hidrológico", fontsize=12, loc="left")
        display_ti = tabla_informacion.head(25).round(4)
        display_ti["year_hydrological"] = display_ti["year_hydrological"].astype(int)
        tbl = ax.table(
            cellText=display_ti.to_numpy().tolist(),
            colLabels=list(display_ti.columns),
            cellLoc="center",
            loc="center",
            bbox=[0.05, 0.05, 0.9, 0.85],
        )
        tbl.auto_set_font_size(False)  # noqa: FBT003
        tbl.set_fontsize(DEFAULT_PDF_CONFIG.table_fontsize)
        if len(tabla_informacion) > 25:  # noqa: PLR2004
            ax.text(
                0.5,
                0.02,
                "(Tabla truncada a 25 filas por espacio)",
                transform=ax.transAxes,
                ha="center",
                fontsize=8,
                color="gray",
            )
        pdf.savefig(fig)
        plt.close(fig)

        # PÁGINA 6: NORMALIDAD VISUAL
        fig, axes = plt.subplots(1, 2, figsize=DEFAULT_PDF_CONFIG.figsize_pdf)
        fig.suptitle("Análisis de Normalidad Visual", fontsize=14)

        # Histograma inline
        axes[0].hist(
            variable_calc,
            bins="auto",
            density=True,
            color="grey",
            alpha=0.7,
            edgecolor="white",
        )
        xr = np.linspace(variable_calc.min(), variable_calc.max(), 200)
        axes[0].plot(
            xr, stats.norm.pdf(xr, media_val, sd_val), color=METIS_BLUE, linewidth=2
        )
        axes[0].set_title("Histograma y Normal")
        axes[0].set_xlabel("Variable")

        # QQ Plot inline
        (osm2, osr2), (slope2, intercept2, _) = stats.probplot(
            variable_calc, dist="norm"
        )
        axes[1].scatter(osm2, osr2, color="black", s=10)
        axes[1].plot(
            osm2, slope2 * np.array(osm2) + intercept2, color=METIS_BLUE, linewidth=2
        )
        axes[1].set_title("Q-Q Plot - Normal")
        axes[1].set_xlabel("Cuantiles Teóricos")
        axes[1].set_ylabel("Cuantiles Observados")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # PÁGINA 7: AUTOCORRELACIÓN
        fig, ax = plt.subplots(figsize=DEFAULT_PDF_CONFIG.figsize_pdf)
        fig.suptitle("Autocorrelación", fontsize=14)
        sm.graphics.tsa.plot_acf(variable_calc, ax=ax, lags=min(40, n_obs // 2 - 1))
        dw = independence_results["durbin_watson"]
        lb = independence_results["ljung_box"]
        txt_dw = f"Durbin-Watson: {round(dw.statistic, 4)}"
        lb_p_val = round(lb.detail["p_value"], 4)
        txt_lb = f"Ljung-Box stat: {round(lb.statistic, 4)}  (p: {lb_p_val})"
        fig.text(0.5, 0.02, f"{txt_dw}    |    {txt_lb}", ha="center", fontsize=10)
        plt.tight_layout(rect=[0, 0.05, 1, 1])
        pdf.savefig(fig)
        plt.close(fig)

        # PÁGINA 8: TEST DE INDEPENDENCIA
        fig = plt.figure(figsize=DEFAULT_PDF_CONFIG.figsize_pdf)
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        fig.text(
            0.5,
            0.95,
            "TEST DE INDEPENDENCIA",
            ha="center",
            fontsize=14,
            fontweight="bold",
        )

        anderson_txt = (
            f"Test de Independencia de Anderson:\n"
            f"  Estadístico: {independence_results['anderson'].statistic}\n"
            f"  Valor crítico: {independence_results['anderson'].critical_value}\n"
            f"  Veredicto: {independence_results['anderson'].verdict}"
        )
        dw_txt = (
            f"Test de Durbin-Watson:\n"
            f"  Estadístico: {independence_results['durbin_watson'].statistic}\n"
            f"  Rango crítico: {independence_results['durbin_watson'].critical_value}\n"
            f"  Veredicto: {independence_results['durbin_watson'].verdict}\n"
            "  Tipo: "
            f"{independence_results['durbin_watson'].detail['autocorrelation_type']}"
        )
        lb_txt = (
            f"Test de Ljung-Box:\n"
            f"  Estadístico: {independence_results['ljung_box'].statistic}\n"
            f"  Valor crítico: {independence_results['ljung_box'].critical_value}\n"
            f"  Veredicto: {independence_results['ljung_box'].verdict}\n"
            f"  p-value: {independence_results['ljung_box'].detail['p_value']}"
        )
        for y, txt in [(0.78, anderson_txt), (0.53, dw_txt), (0.28, lb_txt)]:
            fig.text(
                0.1,
                y,
                txt,
                va="top",
                fontsize=DEFAULT_PDF_CONFIG.text_fontsize,
                family="monospace",
            )

        pdf.savefig(fig)
        plt.close(fig)

        # PÁGINA 9: TEST DE HOMOGENEIDAD
        fig = plt.figure(figsize=DEFAULT_PDF_CONFIG.figsize_pdf)
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        fig.text(
            0.5,
            0.95,
            "TEST DE HOMOGENEIDAD",
            ha="center",
            fontsize=14,
            fontweight="bold",
        )

        helmert_txt = (
            f"Test de Helmert:\n"
            f"  Estadístico: {homogeneity_results['helmert'].statistic}\n"
            f"  Valor crítico: {homogeneity_results['helmert'].critical_value}\n"
            f"  Veredicto: {homogeneity_results['helmert'].verdict}"
        )
        t_student_txt = (
            f"Test t de Student:\n"
            f"  Estadístico: {homogeneity_results['t_student'].statistic}\n"
            f"  Valor crítico: {homogeneity_results['t_student'].critical_value}\n"
            f"  Veredicto: {homogeneity_results['t_student'].verdict}\n"
            f"  p-value: {homogeneity_results['t_student'].detail['p_value']}"
        )
        mw_txt = (
            f"Test de Mann-Whitney:\n"
            f"  Estadístico: {homogeneity_results['mann_whitney'].statistic}\n"
            f"  Veredicto: {homogeneity_results['mann_whitney'].verdict}\n"
            f"  p-value: {homogeneity_results['mann_whitney'].detail['p_value']}"
        )
        for y, txt in [(0.85, helmert_txt), (0.60, t_student_txt), (0.35, mw_txt)]:
            fig.text(
                0.1,
                y,
                txt,
                va="top",
                fontsize=DEFAULT_PDF_CONFIG.text_fontsize,
                family="monospace",
            )

        pdf.savefig(fig)
        plt.close(fig)

        # PÁGINA 10: TEST DE TENDENCIA
        fig = plt.figure(figsize=DEFAULT_PDF_CONFIG.figsize_pdf)
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        fig.text(
            0.5, 0.95, "TEST DE TENDENCIA", ha="center", fontsize=14, fontweight="bold"
        )

        mk_txt = (
            f"Test de Mann-Kendall:\n"
            f"  Estadístico Z: {trend_results['mann_kendall'].statistic}\n"
            f"  Valor crítico: {trend_results['mann_kendall'].critical_value}\n"
            f"  Veredicto: {trend_results['mann_kendall'].verdict}\n"
            f"  Dirección: {trend_results['mann_kendall'].detail['trend_direction']}"
        )
        ks_txt = (
            f"Test de Kolmogorov-Smirnov:\n"
            f"  Estadístico: {trend_results['kolmogorov_smirnov'].statistic}\n"
            f"  Valor crítico: {trend_results['kolmogorov_smirnov'].critical_value}\n"
            f"  Veredicto: {trend_results['kolmogorov_smirnov'].verdict}\n"
            f"  p-value: {trend_results['kolmogorov_smirnov'].detail['p_value']}"
        )
        for y, txt in [(0.75, mk_txt), (0.45, ks_txt)]:
            fig.text(
                0.1,
                y,
                txt,
                va="top",
                fontsize=DEFAULT_PDF_CONFIG.text_fontsize,
                family="monospace",
            )

        pdf.savefig(fig)
        plt.close(fig)

    return pdf_filename
