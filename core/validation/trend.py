"""Módulo de pruebas de tendencia para series hidrológicas.

Las pruebas de tendencia detectan cambios sistemáticos (crecientes o
decrecientes) en la serie temporal. La presencia de tendencia invalida
los supuestos de estacionariedad requeridos para análisis de frecuencia.

Ahora con soporte para frecuencia temporal:
    - Mann-Kendall: Se implementa la corrección Modified Mann-Kendall
      (Hamed & Rao, 1998) que ajusta la varianza de S considerando la
      autocorrelación serial. Para datos de alta frecuencia (mensual,
      diaria), donde hay autocorrelación por inercia natural, la varianza
      se infla apropiadamente para evitar falsos positivos.
    - Kolmogorov-Smirnov: Se reporta la frecuencia en detalles.

Referencias:
    Mann-Kendall es el estándar de la WMO para análisis de tendencia
    en datos hidrológicos y climáticos.
    Hamed, K.H. y Rao, A.R. (1998). "A modified Mann-Kendall trend
    test for autocorrelated data". Journal of Hydrology, 204(1-4), 182-196.
"""

import numpy as np
import pandas as pd
from scipy import stats

from core.shared.types import GroupVerdict, TestResult, get_scaled_sample_size


# Frecuencia temporal por defecto
DEFAULT_FREQUENCY = "yearly"


def mann_kendall_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de Mann-Kendall para detección de tendencia monótona.

    Implementa la versión MODIFICADA (Hamed & Rao, 1998) que corrige la
    varianza del estadístico S cuando hay autocorrelación serial. Esto es
    crucial para datos de alta frecuencia (mensuales, diarios, horarios)
    donde la autocorrelación natural inflaría la tasa de falsos positivos.

    Fórmula original:
        S = Σᵢ Σⱼ sign(xⱼ - xᵢ)  para i < j
        Var(S) = n(n-1)(2n+5) / 18

    Corrección Modified MK:
        Var*(S) = Var(S) * (n / n*)

        donde n* = n / (1 + 2 * sum(r_k))  (tamaño efectivo)
              r_k = autocorrelación en lag k

    Para datos anuales (sin autocorrelación significativa), la corrección
    es mínima y el resultado es equivalente al MK clásico.

    Args:
        series: Serie temporal de valores numéricos.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).
        temporal_frequency: Frecuencia temporal de la serie.
            "yearly", "monthly", "daily", "hourly", "minutes", "5min".

    Returns:
        TestResult con estadístico |Z|, valor crítico, veredicto y detalles
        incluyendo S, Var(S), Var corregida y dirección de la tendencia.

    Reference:
        Hamed, K.H. & Rao, A.R. (1998). A modified Mann-Kendall trend
        test for autocorrelated data. Journal of Hydrology, 204, 182-196.
    """
    n = len(series)
    x = series.to_numpy()

    if n < 3:  # noqa: PLR2004
        return TestResult(
            name="Mann-Kendall Trend Test",
            statistic=0.0,
            critical_value=stats.norm.ppf(1 - alpha / 2),
            alpha=alpha,
            verdict="ACCEPTED",
            detail={
                "note": "Insufficient data (n < 3)",
                "s_statistic": 0.0,
                "variance_s": 0.0,
                "corrected_variance_s": 0.0,
                "trend_direction": "none",
                "temporal_frequency": temporal_frequency,
            },
        )

    # Calcular signos de todas las diferencias
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += np.sign(x[j] - x[i])

    # Varianza de S (MK clásico)
    var_s = n * (n - 1) * (2 * n + 5) / 18

    (
        corrected_var_s,
        correction_factor,
        significant_lags,
    ) = _modified_mk_variance_correction(x, var_s, temporal_frequency)

    # Estadístico Z usando varianza corregida
    var_for_z = corrected_var_s
    if s > 0:
        z = (s - 1) / np.sqrt(var_for_z)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_for_z)
    else:
        z = 0

    critical_value = stats.norm.ppf(1 - alpha / 2)
    verdict = "REJECTED" if abs(z) > critical_value else "ACCEPTED"

    # Métricas escaladas
    scaled = get_scaled_sample_size(n, temporal_frequency)

    return TestResult(
        name="Mann-Kendall Trend Test (Modified)",
        statistic=float(abs(z)),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "s_statistic": float(s),
            "variance_s": float(var_s),
            "corrected_variance_s": float(corrected_var_s),
            "correction_factor": float(correction_factor),
            "significant_autocorrelations": len(significant_lags),
            "trend_direction": "increasing"
            if z > 0
            else "decreasing"
            if z < 0
            else "none",
            "temporal_frequency": temporal_frequency,
            "effective_years": scaled["effective_years"],
        },
    )


def _modified_mk_variance_correction(
    values: np.ndarray,
    variance_s: float,
    temporal_frequency: str,
) -> tuple[float, float, list[float]]:
    """Calcula la corrección de varianza del Modified Mann-Kendall."""
    if temporal_frequency == DEFAULT_FREQUENCY:
        return variance_s, 1.0, []

    n = len(values)
    mean = np.mean(values)
    significant_lags = []
    critical_r = 1.96 / np.sqrt(n)

    for lag in range(1, max(1, n // 4) + 1):
        numerator = np.sum((values[:-lag] - mean) * (values[lag:] - mean))
        denominator = np.sum((values - mean) ** 2)
        autocorrelation = numerator / denominator if denominator != 0 else 0

        if abs(autocorrelation) > critical_r:
            significant_lags.append(autocorrelation)

    if not significant_lags:
        return variance_s, 1.0, []

    correction_factor = 1 + 2 * sum(significant_lags)
    if correction_factor <= 0:
        return variance_s, 1.0, significant_lags

    return variance_s * correction_factor, correction_factor, significant_lags


def kolmogorov_smirnov_trend_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de Kolmogorov-Smirnov para detección de tendencia.

    Compara las funciones de distribución empíricas de la primera y
    segunda mitad de la serie. Detecta si la distribución ha cambiado
    sistemáticamente, lo cual indica tendencia o cambio de régimen.

    Fórmula:
        D = sup|F₁(x) - F₂(x)|
        Valor crítico: 1.36 * √(n / (mid²)) para alpha = 0.05

    Args:
        series: Serie temporal de valores numéricos.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).
        temporal_frequency: Frecuencia temporal de la serie.

    Returns:
        TestResult con estadístico D, valor crítico, veredicto y valor p.
    """
    n = len(series)
    mid = n // 2

    group1 = series.iloc[:mid]
    group2 = series.iloc[mid:]

    statistic, p_value = stats.ks_2samp(group1, group2, alternative="two-sided")

    critical_value = 1.36 * np.sqrt((n) / (mid * mid))  # Valor crítico para alpha=0.05
    verdict = "REJECTED" if statistic > critical_value else "ACCEPTED"

    # Métricas escaladas
    scaled = get_scaled_sample_size(n, temporal_frequency)

    return TestResult(
        name="Kolmogorov-Smirnov Trend Test",
        statistic=float(statistic),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "p_value": float(p_value),
            "temporal_frequency": temporal_frequency,
            "effective_years": scaled["effective_years"],
        },
    )


def run_trend(series: pd.Series) -> GroupVerdict:
    """Ejecuta las dos pruebas de tendencia sobre una serie.

    Orquesta la ejecución de Mann-Kendall y Kolmogorov-Smirnov.
    A diferencia de homogeneidad, este grupo SÍ produce un veredicto
    resolutivo mediante una regla OR conservadora.

    Regla de resolución:
        resolved_verdict = "REJECTED" si:
            MK.verdict == "REJECTED" OR KS.verdict == "REJECTED"
        resolved_verdict = "ACCEPTED" si ambas aceptan.

    Esta regla es conservadora: ante cualquier indicio de tendencia
    en cualquiera de las dos pruebas, se reporta tendencia presente.

    Args:
        series: Serie temporal de valores numéricos.

    Returns:
        GroupVerdict con condition="trend", ambos resultados individuales,
        resolved_verdict según la regla OR, y hierarchy_applied=False
        (no hay jerarquía en este grupo).

    Example:
        >>> serie = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        >>> group = run_trend(serie)
        >>> group.resolved_verdict
        'REJECTED'  # Al menos una prueba detectó tendencia
    """
    mk = mann_kendall_test(series)
    ks = kolmogorov_smirnov_trend_test(series)

    # Veredicto resolutivo: si cualquiera de las dos rechaza -> rechazado
    resolved_verdict = (
        "REJECTED"
        if (mk.verdict == "REJECTED" or ks.verdict == "REJECTED")
        else "ACCEPTED"
    )

    return GroupVerdict(
        condition="trend",
        individual_results=[mk, ks],
        resolved_verdict=resolved_verdict,
        hierarchy_applied=False,
    )
