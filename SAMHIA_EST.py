# ==============================================================================
# PROYECTO: SAMHIA - SISTEMA DE ANÁLISIS MULTIVARIABLE (VERSIÓN FINAL EXTENDIDA)
# AUTOR: Dr. Ing. Carlos G. Catalini
# TRADUCCIÓN A PYTHON: Claude (Anthropic)
# DESCRIPCIÓN: Análisis estadístico completo, explícito y detallado.
# ==============================================================================

import contextlib
import traceback
import warnings
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
from scipy.stats import kurtosis, mannwhitneyu, mood, pearsonr, skew, spearmanr
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson


# Optional: pymannkendall for Mann-Kendall test
try:
    import pymannkendall as mk

    HAS_MK = True
except ImportError:
    HAS_MK = False
    print(
        "Advertencia: 'pymannkendall' no está instalado. "
        "El test Mann-Kendall será omitido."
    )
    print("  Instalar con: pip install pymannkendall")

warnings.filterwarnings("ignore")


# ==============================================================================
# RUNS TEST (Wald-Wolfowitz) — implementación manual
# ==============================================================================
def runs_test(x):
    """
    Performs the Wald-Wolfowitz runs test for randomness.
    Returns a dict with 'statistic' (Z) and 'p_value'.
    """
    x = np.asarray(x)
    median_val = np.median(x)
    above = x > median_val
    # Build runs
    runs = 1
    for i in range(1, len(above)):
        if above[i] != above[i - 1]:
            runs += 1

    n1 = np.sum(above)
    n2 = np.sum(~above)
    n = n1 + n2

    if n1 == 0 or n2 == 0:
        return {"statistic": np.nan, "p_value": np.nan}

    mean_runs = (2 * n1 * n2) / n + 1
    var_runs = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n**2 * (n - 1))

    if var_runs <= 0:
        return {"statistic": np.nan, "p_value": np.nan}

    z = (runs - mean_runs) / np.sqrt(var_runs)
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"statistic": z, "p_value": p_value}


# ==============================================================================
# FUNCIÓN PRINCIPAL DE ANÁLISIS
# ==============================================================================
def analizar_variable_samhia(  # noqa: C901, PLR0912, PLR0915
    datos_origen, nombre_variable, nombre_embalse, carpeta_raiz
):
    print(f"   -> Procesando variable: {nombre_variable} ...")

    # ==========================================================================
    # A. PREPARACIÓN, LIMPIEZA Y TRANSFORMACIÓN DE DATOS
    # ==========================================================================

    dir_salida = Path(carpeta_raiz) / nombre_variable
    dir_salida.mkdir(parents=True, exist_ok=True)

    # Selección y limpieza
    archivo = datos_origen[["date", nombre_variable]].copy()
    archivo.columns = ["date", "variable_raw"]
    archivo["date"] = pd.to_datetime(archivo["date"], errors="coerce")
    archivo["variable"] = pd.to_numeric(
        archivo["variable_raw"].astype(str).str.strip(), errors="coerce"
    )
    archivo = (
        archivo[archivo["date"].notna()].sort_values("date").reset_index(drop=True)
    )

    variable_calc = archivo["variable"].dropna().to_numpy()

    if len(variable_calc) < 12:
        print("      [AVISO] Variable saltada: Menos de 12 datos válidos.")
        return

    # Variables temporales
    archivo["month"] = archivo["date"].dt.month
    archivo["year"] = archivo["date"].dt.year
    archivo["year_hydrological"] = np.where(
        archivo["date"].dt.month >= 6,
        archivo["date"].dt.year,
        archivo["date"].dt.year - 1,
    )
    archivo = archivo.sort_values("year_hydrological").reset_index(drop=True)

    # Límites dinámicos eje Y
    max_serie = variable_calc.max()
    min_serie = variable_calc.min()
    if min_serie >= 0:
        rango_y = (0, max_serie * 1.25)
    else:
        abs_max = max(abs(max_serie), abs(min_serie))
        rango_y = (-abs_max * 1.25, abs_max * 1.25)

    n = len(variable_calc)
    kn = 0.4083 * np.log(n) + 1.1584
    media_val = float(np.mean(variable_calc))
    sd_val = float(np.std(variable_calc, ddof=1))
    limite_superior = media_val + kn * sd_val
    limite_inferior = media_val - kn * sd_val

    month_names = [
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

    # ==========================================================================
    # B. GENERACIÓN DE GRÁFICOS INDIVIDUALES (PNG)
    # ==========================================================================

    # G1: Serie Temporal Completa
    fig, ax = plt.subplots(figsize=(10, 6))
    valid = archivo.dropna(subset=["variable"])
    ax.fill_between(valid["date"], valid["variable"], alpha=0.5, color="grey")
    ax.plot(valid["date"], valid["variable"], color="black", linewidth=0.8)
    # LOESS via lowess
    if len(valid) > 3:
        lowess_result = sm.nonparametric.lowess(
            valid["variable"], valid["date"].astype(np.int64), frac=0.3
        )
        ax.plot(valid["date"], lowess_result[:, 1], color="blue", linewidth=1.5)
    ax.set_title("Serie Temporal")
    ax.set_xlabel("Fecha")
    ax.set_ylabel(nombre_variable)
    ax.set_ylim(rango_y)
    plt.tight_layout()
    fig.savefig(dir_salida / f"01_SerieTemporal_{nombre_variable}.png")
    plt.close(fig)

    # G2: Facet por Año Calendario
    years = sorted(archivo["year"].dropna().unique())
    ncols = min(4, len(years))
    nrows = int(np.ceil(len(years) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(10, max(4, nrows * 2.5)))
    axes = np.array(axes).flatten()
    for i, yr in enumerate(years):
        ax = axes[i]
        sub = archivo[archivo["year"] == yr].dropna(subset=["variable"])
        ax.fill_between(sub["date"], sub["variable"], alpha=0.5, color="grey")
        ax.plot(sub["date"], sub["variable"], color="black", linewidth=0.8)
        ax.set_title(f"Año {int(yr)}", fontsize=7)
        ax.set_ylim(rango_y)
        ax.tick_params(labelsize=6)
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    fig.suptitle("Gráfico dividido por Año Calendario")
    plt.tight_layout()
    fig.savefig(dir_salida / f"02_AnoCalendario_{nombre_variable}.png")
    plt.close(fig)

    # G3: Facet por Año Hidrológico
    hydro_years = sorted(archivo["year_hydrological"].dropna().unique())
    ncols_h = min(4, len(hydro_years))
    nrows_h = int(np.ceil(len(hydro_years) / ncols_h))
    fig, axes = plt.subplots(nrows_h, ncols_h, figsize=(10, max(4, nrows_h * 2.5)))
    axes = np.array(axes).flatten()
    for i, hy in enumerate(hydro_years):
        ax = axes[i]
        sub = archivo[archivo["year_hydrological"] == hy].dropna(subset=["variable"])
        ax.fill_between(sub["date"], sub["variable"], alpha=0.5, color="grey")
        ax.plot(sub["date"], sub["variable"], color="black", linewidth=0.8)
        ax.set_title(f"H-{int(hy)}", fontsize=7)
        ax.set_ylim(rango_y)
        ax.tick_params(labelsize=6)
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    fig.suptitle("Gráfico dividido por Año Hidrológico")
    plt.tight_layout()
    fig.savefig(dir_salida / f"03_AnoHidrologico_{nombre_variable}.png")
    plt.close(fig)

    # G4: Datos Atípicos
    datos_atipicos_df = archivo[
        (archivo["variable"] > limite_superior)
        | (archivo["variable"] < limite_inferior)
    ].dropna(subset=["variable"])
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(valid["date"], valid["variable"], color="black", linewidth=0.8)
    ax.axhline(limite_superior, linestyle="--", color="red", label="Límite superior")
    ax.axhline(limite_inferior, linestyle="--", color="red", label="Límite inferior")
    if not datos_atipicos_df.empty:
        ax.scatter(
            datos_atipicos_df["date"],
            datos_atipicos_df["variable"],
            color="red",
            zorder=5,
        )
    ax.set_title("Análisis de Datos Atípicos")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Valor")
    ax.set_ylim(rango_y)
    ax.legend()
    plt.tight_layout()
    fig.savefig(dir_salida / f"04_DatosAtipicos_{nombre_variable}.png")
    plt.close(fig)

    # Boxplot 1: Mensual Calendario (Ene-Dic)
    fig, ax = plt.subplots(figsize=(10, 6))
    data_by_month = [
        archivo[archivo["month"] == m]["variable"].dropna().to_numpy()
        for m in range(1, 13)
    ]
    bp = ax.boxplot(data_by_month, labels=month_names, patch_artist=True, sym="")
    for patch in bp["boxes"]:
        patch.set_facecolor("lightblue")
    ax.set_title("Valores Mensuales (Año Calendario)")
    ax.set_xlabel("Mes")
    ax.set_ylabel(nombre_variable)
    plt.tight_layout()
    fig.savefig(dir_salida / f"05_Boxplot_Mensual_{nombre_variable}.png")
    plt.close(fig)

    # Boxplot 2: Mensual Hidrológico (Jun-May)
    orden_hidro = list(range(6, 13)) + list(range(1, 6))
    labels_hidro = [month_names[m - 1] for m in orden_hidro]
    fig, ax = plt.subplots(figsize=(10, 6))
    data_by_month_h = [
        archivo[archivo["month"] == m]["variable"].dropna().to_numpy()
        for m in orden_hidro
    ]
    bp = ax.boxplot(data_by_month_h, labels=labels_hidro, patch_artist=True, sym="")
    for patch in bp["boxes"]:
        patch.set_facecolor("lightgreen")
    ax.set_title("Valores Mensuales (Año Hidrológico)")
    ax.set_xlabel("Mes (jun-may)")
    ax.set_ylabel(nombre_variable)
    plt.tight_layout()
    fig.savefig(dir_salida / f"06_Boxplot_Hidro_{nombre_variable}.png")
    plt.close(fig)

    # Boxplot 3: Anual Hidrológico
    fig, ax = plt.subplots(figsize=(10, 6))
    hydro_labels = [str(int(y)) for y in hydro_years]
    data_by_hydro = [
        archivo[archivo["year_hydrological"] == y]["variable"].dropna().to_numpy()
        for y in hydro_years
    ]
    bp = ax.boxplot(data_by_hydro, labels=hydro_labels, patch_artist=True, sym="")
    for patch in bp["boxes"]:
        patch.set_facecolor("lightblue")
    ax.set_title("Box-plot año hidrológico (Anual)")
    ax.set_xlabel("Año Hidrológico")
    ax.set_ylabel(nombre_variable)
    plt.xticks(rotation=90)
    plt.tight_layout()
    fig_boxplot_hydro = fig  # keep reference for PDF

    # Histograma
    png_file_hist = dir_salida / f"07_Histograma_{nombre_variable}.png"
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.hist(
        variable_calc,
        bins="auto",
        density=True,
        color="grey",
        alpha=0.7,
        edgecolor="white",
    )
    xmin, xmax = ax.get_xlim()
    x = np.linspace(xmin, xmax, 200)
    ax.plot(x, stats.norm.pdf(x, media_val, sd_val), color="blue", linewidth=2)
    ax.set_title("Histograma y Normal")
    ax.set_xlabel("Variable")
    plt.tight_layout()
    fig.savefig(png_file_hist)
    plt.close(fig)

    # QQ Plot
    png_file_qq = dir_salida / f"08_QQPlot_{nombre_variable}.png"
    fig, ax = plt.subplots(figsize=(6, 6))
    (osm, osr), (slope, intercept, _r) = stats.probplot(variable_calc, dist="norm")
    ax.scatter(osm, osr, color="black", s=10)
    ax.plot(osm, slope * np.array(osm) + intercept, color="blue", linewidth=2)
    ax.set_title("Q-Q Plot - Normal")
    ax.set_xlabel("Cuantiles Teóricos")
    ax.set_ylabel("Cuantiles Observados")
    plt.tight_layout()
    fig.savefig(png_file_qq)
    plt.close(fig)

    # ACF
    png_file_acf = dir_salida / f"09_Autocorrelacion_{nombre_variable}.png"
    fig, ax = plt.subplots(figsize=(8, 6))
    sm.graphics.tsa.plot_acf(
        variable_calc,
        ax=ax,
        lags=min(40, n // 2 - 1),
        title="Función de Autocorrelación",
    )
    plt.tight_layout()
    fig.savefig(png_file_acf)
    plt.close(fig)

    # ==========================================================================
    # D. CÁLCULOS ESTADÍSTICOS Y TESTS
    # ==========================================================================

    asymmetry = float(skew(variable_calc))
    kurt_val = float(
        kurtosis(variable_calc, fisher=False)
    )  # excess=False matches R's kurtosis
    var_n_1 = float(np.var(variable_calc, ddof=1))
    coefficient_of_variation = (sd_val / media_val) * 100 if media_val != 0 else np.nan

    # Tabla resumen descriptivo
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
                n,
                coefficient_of_variation,
            ]
        ],
    }
    combined_stat_table = pd.DataFrame(summary_stats)

    # Tabla resumen año hidrológico
    tabla_informacion = (
        archivo.groupby("year_hydrological")["variable"]
        .agg(Medio="mean", Maximo="max", Minimo="min")
        .reset_index()
        .round(4)
    )

    # Durbin-Watson
    dw_stat_val = np.nan
    with contextlib.suppress(Exception):
        dw_stat_val = float(durbin_watson(variable_calc))

    lb_stat_val, lb_p_val = np.nan, np.nan
    try:
        lb_result = acorr_ljungbox(variable_calc, lags=[12], return_df=True)
        lb_stat_val = float(lb_result["lb_stat"].iloc[0])
        lb_p_val = float(lb_result["lb_pvalue"].iloc[0])
    except Exception:  # noqa: S110, BLE001
        pass

    # Anderson (Pearson lag-1 serial correlation)
    result_anderson_stat, result_anderson_p = np.nan, np.nan
    conclusion_anderson = "Error o datos insuficientes"
    try:
        r_val, p_val = pearsonr(variable_calc[:-1], variable_calc[1:])
        result_anderson_stat = round(r_val, 4)
        result_anderson_p = round(p_val, 4)
        conclusion_anderson = (
            "Hay evidencia para rechazar la hipótesis nula de independencia."
            if p_val < 0.05
            else (
                "No hay suficiente evidencia para rechazar "
                "la hipótesis nula de independencia."
            )
        )
    except Exception:  # noqa: S110, BLE001
        pass

    ww_stat, ww_p = np.nan, np.nan
    conclusion_ww = "Error o datos insuficientes"
    conclusion_ww_trend = "Error o datos insuficientes"
    try:
        ww = runs_test(variable_calc)
        ww_stat = round(ww["statistic"], 4) if not np.isnan(ww["statistic"]) else np.nan
        ww_p = round(ww["p_value"], 4) if not np.isnan(ww["p_value"]) else np.nan
        if not np.isnan(ww_p):
            conclusion_ww = (
                "Hay evidencia para rechazar la hipótesis nula de independencia."
                if ww_p < 0.05
                else (
                    "No hay suficiente evidencia para rechazar "
                    "la hipótesis nula de independencia."
                )
            )
            conclusion_ww_trend = (
                "Hay evidencia de tendencia (no aleatoriedad)."
                if ww_p < 0.05
                else "No hay evidencia suficiente de tendencia."
            )
    except Exception:  # noqa: S110, BLE001
        pass

    # Spearman
    sp_stat, sp_p = np.nan, np.nan
    conclusion_spearman = "Error o datos insuficientes"
    try:
        sp_val, sp_p_val = spearmanr(variable_calc[:-1], variable_calc[1:])
        sp_stat = round(sp_val, 4)
        sp_p = round(sp_p_val, 4)
        conclusion_spearman = (
            "Hay evidencia para rechazar la hipótesis nula de independencia."
            if sp_p_val < 0.05
            else (
                "No hay suficiente evidencia para rechazar "
                "la hipótesis nula de independencia."
            )
        )
    except Exception:  # noqa: S110, BLE001
        pass

    # Mann-Whitney
    half_point = n // 2
    group1 = variable_calc[:half_point]
    group2 = variable_calc[half_point:]
    mw_stat, mw_p = np.nan, np.nan
    conclusion_mw = "Error o datos insuficientes"
    try:
        mw_res = mannwhitneyu(group1, group2, alternative="two-sided")
        mw_stat = round(float(mw_res.statistic), 4)
        mw_p = round(float(mw_res.pvalue), 4)
        conclusion_mw = (
            "Hay evidencia para rechazar la hipótesis nula de homogeneidad."
            if mw_p < 0.05
            else "No hay evidencia suficiente para rechazar homogeneidad."
        )
    except Exception:  # noqa: S110, BLE001
        pass

    # Mood test
    mood_stat, mood_p = np.nan, np.nan
    conclusion_mood = "Error o datos insuficientes"
    try:
        mood_res = mood(group1, group2)
        mood_stat = round(float(mood_res.statistic), 4)
        mood_p = round(float(mood_res.pvalue), 4)
        conclusion_mood = (
            "Hay evidencia para rechazar la hipótesis nula de homogeneidad."
            if mood_p < 0.05
            else "No hay evidencia suficiente para rechazar homogeneidad."
        )
    except Exception:  # noqa: S110, BLE001
        pass

    # Mann-Kendall
    mk_tau_val, mk_p_val = np.nan, np.nan
    conclusion_mk = "Error o datos insuficientes"
    if HAS_MK:
        try:
            mk_result = mk.original_test(variable_calc)
            mk_tau_val = round(float(mk_result.Tau), 4)
            mk_p_val = round(float(mk_result.p), 4)
            conclusion_mk = (
                "Hay evidencia significativa de tendencia."
                if mk_p_val < 0.05
                else "No hay evidencia suficiente de tendencia."
            )
        except Exception:  # noqa: S110, BLE001
            pass
    else:
        conclusion_mk = "Test omitido: módulo 'pymannkendall' no disponible."

    # ==========================================================================
    # E. GENERACIÓN DEL PDF (10 PÁGINAS)
    # ==========================================================================

    pdf_filename = dir_salida / f"REPORTE_FINAL_{nombre_embalse}_{nombre_variable}.pdf"

    with PdfPages(pdf_filename) as pdf:
        # --- PÁGINA 1: CARÁTULA ---
        fig = plt.figure(figsize=(14, 8))
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        fig.patch.set_facecolor("white")
        # Marco exterior
        for lw, pad in [(4, 0.01), (1, 0.03)]:
            rect = plt.Rectangle(
                (pad, pad),
                1 - 2 * pad,
                1 - 2 * pad,
                linewidth=lw,
                edgecolor="darkblue" if lw == 4 else "black",
                facecolor="none",
                transform=fig.transFigure,
                figure=fig,
            )
            fig.add_artist(rect)

        texts = [
            (0.5, 0.85, "UNIVERSIDAD CATÓLICA DE CÓRDOBA", 24, "bold", "darkred"),
            (
                0.5,
                0.73,
                "GRUPO DE ESTUDIOS HIDROLÓGICOS EN\n"
                "CUENCAS POBREMENTE AFORADAS (EHCPA)",
                18,
                "bold",
                "black",
            ),
            (0.5, 0.60, "SISTEMA SAMHIA", 32, "bold", "darkblue"),
            (0.5, 0.53, "REPORTE DE ANÁLISIS ESTADÍSTICO", 20, "normal", "black"),
            (0.5, 0.40, f"Embalse: {nombre_embalse}", 16, "normal", "black"),
            (0.5, 0.35, f"Variable Analizada: {nombre_variable}", 16, "bold", "black"),
            (0.5, 0.20, "Autor: Dr. Ing. Carlos G. Catalini", 14, "italic", "black"),
            (
                0.5,
                0.10,
                f"Fecha de Generación: {datetime.now(timezone.utc).date()}",
                10,
                "normal",
                "grey",
            ),
        ]
        for x, y, txt, fs, fw, fc in texts:
            fig.text(
                x,
                y,
                txt,
                ha="center",
                va="center",
                fontsize=fs,
                fontweight=fw,
                color=fc,
            )
        pdf.savefig(fig)
        plt.close(fig)

        # --- PÁGINA 2: GRÁFICOS COMBINADOS (G1-G4) ---
        fig, axes = plt.subplots(2, 2, figsize=(14, 8))

        def _plot_ts(ax, df, title):
            v = df.dropna(subset=["variable"])
            ax.fill_between(v["date"], v["variable"], alpha=0.5, color="grey")
            ax.plot(v["date"], v["variable"], color="black", linewidth=0.8)
            ax.set_title(title, fontsize=9)
            ax.set_ylim(rango_y)

        _plot_ts(axes[0, 0], archivo, "Serie Temporal")
        _plot_ts(axes[0, 1], archivo, "Año Calendario (global)")
        _plot_ts(axes[1, 0], archivo, "Año Hidrológico (global)")

        # Atípicos
        ax4 = axes[1, 1]
        vv = archivo.dropna(subset=["variable"])
        ax4.plot(vv["date"], vv["variable"], color="black", linewidth=0.8)
        ax4.axhline(limite_superior, linestyle="--", color="red")
        ax4.axhline(limite_inferior, linestyle="--", color="red")
        if not datos_atipicos_df.empty:
            ax4.scatter(
                datos_atipicos_df["date"],
                datos_atipicos_df["variable"],
                color="red",
                zorder=5,
                s=20,
            )
        ax4.set_title("Datos Atípicos", fontsize=9)
        ax4.set_ylim(rango_y)

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # --- PÁGINA 3: RESUMEN ESTADÍSTICO Y OUTLIERS ---
        fig = plt.figure(figsize=(14, 8))
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        ax.set_title("Resumen Estadístico Descriptivo", fontsize=12, loc="left", pad=10)

        # Tabla estadística
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
        tbl.auto_set_font_size(prop=False)
        tbl.set_fontsize(9)

        if not datos_atipicos_df.empty:
            display_df = datos_atipicos_df.head(20)[["date", "variable"]].copy()
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
            tbl2.auto_set_font_size(prop=False)
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

        # --- PÁGINA 4: BOXPLOTS ---
        fig, axes = plt.subplots(1, 3, figsize=(14, 6))

        # Mensual calendario
        data_bp = [
            archivo[archivo["month"] == m]["variable"].dropna().to_numpy()
            for m in range(1, 13)
        ]
        bp = axes[0].boxplot(data_bp, labels=month_names, patch_artist=True, sym="")
        for p in bp["boxes"]:
            p.set_facecolor("lightblue")
        axes[0].set_title("Mensual (Año Calendario)", fontsize=9)
        axes[0].tick_params(labelsize=7)

        # Mensual hidrológico
        data_bp_h = [
            archivo[archivo["month"] == m]["variable"].dropna().to_numpy()
            for m in orden_hidro
        ]
        bp2 = axes[1].boxplot(data_bp_h, labels=labels_hidro, patch_artist=True, sym="")
        for p in bp2["boxes"]:
            p.set_facecolor("lightgreen")
        axes[1].set_title("Mensual (Año Hidrológico)", fontsize=9)
        axes[1].tick_params(labelsize=7)

        # Anual hidrológico
        bp3 = axes[2].boxplot(
            data_by_hydro, labels=hydro_labels, patch_artist=True, sym=""
        )
        for p in bp3["boxes"]:
            p.set_facecolor("lightblue")
        axes[2].set_title("Anual Hidrológico", fontsize=9)
        axes[2].tick_params(axis="x", rotation=90, labelsize=6)

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)
        plt.close(fig_boxplot_hydro)

        # --- PÁGINA 5: TABLA AÑO HIDROLÓGICO ---
        fig = plt.figure(figsize=(14, 8))
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
        tbl.auto_set_font_size(prop=False)
        tbl.set_fontsize(9)
        if len(tabla_informacion) > 25:
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

        # --- PÁGINA 6: NORMALIDAD VISUAL ---
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
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
            xr, stats.norm.pdf(xr, media_val, sd_val), color="blue", linewidth=2
        )
        axes[0].set_title("Histograma y Normal")
        axes[0].set_xlabel("Variable")

        # QQ Plot inline
        (osm2, osr2), (slope2, intercept2, _) = stats.probplot(
            variable_calc, dist="norm"
        )
        axes[1].scatter(osm2, osr2, color="black", s=10)
        axes[1].plot(
            osm2, slope2 * np.array(osm2) + intercept2, color="blue", linewidth=2
        )
        axes[1].set_title("Q-Q Plot - Normal")
        axes[1].set_xlabel("Cuantiles Teóricos")
        axes[1].set_ylabel("Cuantiles Observados")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # --- PÁGINA 7: AUTOCORRELACIÓN ---
        fig, ax = plt.subplots(figsize=(14, 6))
        fig.suptitle("Autocorrelación", fontsize=14)
        sm.graphics.tsa.plot_acf(variable_calc, ax=ax, lags=min(40, n // 2 - 1))
        dw_str = round(dw_stat_val, 4) if not np.isnan(dw_stat_val) else "NA"
        lb_str = round(lb_stat_val, 4) if not np.isnan(lb_stat_val) else "NA"
        lb_p_str = round(lb_p_val, 4) if not np.isnan(lb_p_val) else "NA"
        txt_dw = f"Durbin-Watson: {dw_str}"
        txt_lb = f"Ljung-Box stat: {lb_str}  (p: {lb_p_str})"
        fig.text(0.5, 0.02, f"{txt_dw}    |    {txt_lb}", ha="center", fontsize=10)
        plt.tight_layout(rect=[0, 0.05, 1, 1])
        pdf.savefig(fig)
        plt.close(fig)

        # --- PÁGINA 8: TEST DE INDEPENDENCIA ---
        fig = plt.figure(figsize=(14, 8))
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
            f"Test de Independencia de Anderson (Pearson):\n"
            f"  Estadístico (r): {result_anderson_stat}\n"
            f"  p-value: {result_anderson_p}\n"
            f"  Conclusión: {conclusion_anderson}"
        )
        ww_txt = (
            f"Test de Independencia de Wald-Wolfowitz (Runs):\n"
            f"  Estadístico (Z): {ww_stat}\n"
            f"  p-value: {ww_p}\n"
            f"  Conclusión: {conclusion_ww}"
        )
        sp_txt = (
            f"Test de Coeficiente de Spearman:\n"
            f"  Estadístico (rho): {sp_stat}\n"
            f"  p-value: {sp_p}\n"
            f"  Conclusión: {conclusion_spearman}"
        )
        for y, txt in [(0.75, anderson_txt), (0.50, ww_txt), (0.25, sp_txt)]:
            fig.text(0.1, y, txt, va="top", fontsize=11, family="monospace")

        pdf.savefig(fig)
        plt.close(fig)

        # --- PÁGINA 9: TEST DE HOMOGENEIDAD ---
        fig = plt.figure(figsize=(14, 8))
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        fig.text(
            0.5,
            0.95,
            "TEST DE HOMOGENEIDAD (Mitad vs Mitad)",
            ha="center",
            fontsize=14,
            fontweight="bold",
        )

        mw_txt = (
            f"Test de Mann-Whitney:\n"
            f"  Estadístico (W): {mw_stat}\n"
            f"  p-value: {mw_p}\n"
            f"  Conclusión: {conclusion_mw}"
        )
        mood_txt = (
            f"Test de Mood:\n"
            f"  Estadístico (Z): {mood_stat}\n"
            f"  p-value: {mood_p}\n"
            f"  Conclusión: {conclusion_mood}"
        )
        for y, txt in [(0.78, mw_txt), (0.45, mood_txt)]:
            fig.text(0.1, y, txt, va="top", fontsize=11, family="monospace")

        pdf.savefig(fig)
        plt.close(fig)

        # --- PÁGINA 10: ESTACIONALIDAD / TENDENCIA ---
        fig = plt.figure(figsize=(14, 8))
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        fig.text(
            0.5,
            0.95,
            "TEST DE ESTACIONALIDAD / TENDENCIA",
            ha="center",
            fontsize=14,
            fontweight="bold",
        )

        mk_display = round(mk_tau_val, 4) if not np.isnan(mk_tau_val) else "NA"
        mk_p_display = round(mk_p_val, 4) if not np.isnan(mk_p_val) else "NA"
        mk_txt = (
            f"Prueba de Tendencia Mann-Kendall:\n"
            f"  Estadístico (tau): {mk_display}\n"
            f"  p-value: {mk_p_display}\n"
            f"  Conclusión: {conclusion_mk}"
        )
        ww_trend_txt = (
            f"Prueba de Tendencia Wald-Wolfowitz:\n"
            f"  Estadístico (Z): {ww_stat}\n"
            f"  p-value: {ww_p}\n"
            f"  Conclusión: {conclusion_ww_trend}"
        )
        for y, txt in [(0.78, mk_txt), (0.45, ww_trend_txt)]:
            fig.text(0.1, y, txt, va="top", fontsize=11, family="monospace")

        pdf.savefig(fig)
        plt.close(fig)

    print(f"      -> Reporte guardado con éxito: {pdf_filename}")


# ==============================================================================
# BUCLE PRINCIPAL DE EJECUCIÓN
# ==============================================================================

# LISTA DE ARCHIVOS (Agrega aquí tus archivos XLSX o CSV)
lista_archivos = [
    "UCC-DAT-ESR-AH-001-26-00.xlsx",
    "UCC-DAT-ELM-AH-001-26-00.xlsx",
    "UCC-DAT-EMB-AH-001-26-00.xlsx",
]

# Carpeta maestra de salida
ruta_resultados = Path.cwd() / "SAMHIA_Resultados_Est"
ruta_resultados.mkdir(parents=True, exist_ok=True)

print("=" * 56)
print(" SISTEMA SAMHIA: INICIANDO PROCESAMIENTO MASIVO ")
print("=" * 56)

for archivo in lista_archivos:
    archivo_path = Path(archivo)
    if not archivo_path.exists():
        print(f"\n[ERROR] El archivo no se encuentra: {archivo}")
        continue

    nombre_embalse = archivo_path.stem
    print(f"\n>> ANALIZANDO ARCHIVO: {archivo}")

    # Lectura inteligente (CSV o Excel)
    try:
        if archivo.lower().endswith(".csv"):
            try:
                datos = pd.read_csv(archivo, na_values=["NA", "nan", "NaN", ""])
            except Exception:  # noqa: BLE001
                datos = pd.read_csv(
                    archivo, sep=";", na_values=["NA", "nan", "NaN", ""]
                )
        else:
            datos = pd.read_excel(archivo)
    except Exception as e:  # noqa: BLE001
        print(f"   [ERROR] No se pudo leer el archivo: {e}")
        continue

    # Detección de columnas numéricas
    cols_excluir = {
        "date",
        "year",
        "month",
        "day",
        "fecha",
        "año",
        "mes",
        "year_hydrological",
    }
    cols_numericas = [
        c for c in datos.columns if pd.api.types.is_numeric_dtype(datos[c])
    ]

    # Fallback si hay pocos numéricos detectados (por 'nan' como string)
    if len(cols_numericas) < 2:
        cols_numericas = [c for c in datos.columns if c.lower() not in cols_excluir]

    cols_analisis = [c for c in cols_numericas if c.lower() not in cols_excluir]

    print(f"   Variables detectadas para análisis: {len(cols_analisis)}")

    for var in cols_analisis:
        try:
            analizar_variable_samhia(
                datos,
                var,
                nombre_embalse,
                ruta_resultados / nombre_embalse,
            )
        except Exception as e:  # noqa: BLE001, PERF203
            print(f"   [ERROR CRÍTICO] en variable {var}: {e}")
            traceback.print_exc()

print("\n" + "=" * 56)
print(" PROCESO SAMHIA FINALIZADO ")
print(f" Resultados en: {ruta_resultados}")
print("=" * 56)

# Requirements
# numpy
# Dependencies: pandas, matplotlib, scipy, statsmodels, openpyxl, pymannkendall
