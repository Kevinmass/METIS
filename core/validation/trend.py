import numpy as np
import pandas as pd
from scipy import stats

from core.shared.types import GroupVerdict, TestResult


def mann_kendall_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """
    Test de Mann-Kendall para detección de tendencia monótona.
    Prueba no paramétrica recomendada para series hidrológicas.
    """
    n = len(series)
    x = series.to_numpy()

    # Calcular signos de todas las diferencias
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += np.sign(x[j] - x[i])

    # Varianza de S
    var_s = n * (n - 1) * (2 * n + 5) / 18

    # Estadístico Z
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0

    critical_value = stats.norm.ppf(1 - alpha / 2)
    verdict = "REJECTED" if abs(z) > critical_value else "ACCEPTED"

    return TestResult(
        name="Mann-Kendall Trend Test",
        statistic=float(abs(z)),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "s_statistic": float(s),
            "variance_s": float(var_s),
            "trend_direction": "increasing"
            if z > 0
            else "decreasing"
            if z < 0
            else "none",
        },
    )


def kolmogorov_smirnov_trend_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """
    Test de Kolmogorov-Smirnov para detección de tendencia.
    Compara distribución de primera mitad vs segunda mitad.
    """
    n = len(series)
    mid = n // 2

    group1 = series.iloc[:mid]
    group2 = series.iloc[mid:]

    statistic, p_value = stats.ks_2samp(group1, group2, alternative="two-sided")

    critical_value = 1.36 * np.sqrt((n) / (mid * mid))  # Valor crítico para alpha=0.05
    verdict = "REJECTED" if statistic > critical_value else "ACCEPTED"

    return TestResult(
        name="Kolmogorov-Smirnov Trend Test",
        statistic=float(statistic),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={"p_value": float(p_value)},
    )


def run_trend(series: pd.Series) -> GroupVerdict:
    """
    Ejecuta las dos pruebas de tendencia.
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
