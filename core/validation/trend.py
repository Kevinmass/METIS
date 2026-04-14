"""Módulo de pruebas de tendencia para series hidrológicas.

Las pruebas de tendencia detectan cambios sistemáticos (crecientes o
decrecientes) en la serie temporal. La presencia de tendencia invalida
los supuestos de estacionariedad requeridos para análisis de frecuencia.

Pruebas implementadas:
    - Mann-Kendall: No paramétrica, robusta ante valores atípicos.
      Detecta tendencias monótonas de cualquier tipo.
    - Kolmogorov-Smirnov (versión tendencia): Compara distribuciones
      de dos mitades de la serie. Detecta cambios en la distribución.

Resolución de grupo:
    A diferencia de homogeneidad, el grupo de tendencia SÍ tiene
    veredicto resolutivo. Si CUALQUIERA de las dos pruebas rechaza,
    el veredicto grupal es "REJECTED". Esto es conservador: ante duda,
    se asume tendencia presente.

Referencias:
    Mann-Kendall es el estándar de la WMO para análisis de tendencia
    en datos hidrológicos y climáticos.
"""

import numpy as np
import pandas as pd
from scipy import stats

from core.shared.types import GroupVerdict, TestResult


def mann_kendall_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """Test de Mann-Kendall para detección de tendencia monótona.

    Prueba no paramétrica que detecta tendencias sistemáticas (crecientes
    o decrecientes) en series temporales. Es robusta ante valores atípicos
    porque está basada en rangos, no en valores absolutos.

    Fórmula:
        S = Σᵢ Σⱼ sign(xⱼ - xᵢ)  para i < j
        Var(S) = n(n-1)(2n+5) / 18

        Z = (S - 1) / √Var(S)   si S > 0
        Z = (S + 1) / √Var(S)   si S < 0
        Z = 0                   si S = 0

        (Corrección de continuidad aplicada)

    Interpretación:
        - Z positivo: tendencia creciente
        - Z negativo: tendencia decreciente
        - |Z| > Z_alpha/2: Se rechaza hipótesis nula (hay tendencia)

    Args:
        series: Serie temporal de valores numéricos.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).

    Returns:
        TestResult con estadístico |Z|, valor crítico, veredicto y detalles
        incluyendo S, Var(S) y dirección de la tendencia.

    Note:
        Esta es la prueba estándar de la WMO para series hidrológicas.
        Es preferida sobre tests paramétricos por su robustez.

    Example:
        >>> # Serie con tendencia creciente
        >>> serie = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        >>> result = mann_kendall_test(serie)
        >>> result.detail["trend_direction"]
        'increasing'
        >>> result.verdict
        'REJECTED'  # Tendencia significativa detectada
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
    """Test de Kolmogorov-Smirnov para detección de tendencia.

    Compara las funciones de distribución empíricas de la primera y
    segunda mitad de la serie. Detecta si la distribución ha cambiado
    sistemáticamente, lo cual indica tendencia o cambio de régimen.

    Fórmula:
        D = sup|F₁(x) - F₂(x)|
        Valor crítico: 1.36 * √(n / (mid²)) para alpha = 0.05

    donde:
        D = máxima diferencia entre funciones de distribución acumuladas
        F₁, F₂ = distribuciones empíricas de primera y segunda mitad
        mid = n // 2 (tamaño de cada mitad)

    Interpretación:
        - D > D_alpha: Se rechaza igualdad de distribuciones (hay tendencia)
        - D <= D_alpha: Se aceptan distribuciones iguales (sin tendencia)

    Args:
        series: Serie temporal de valores numéricos.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).

    Returns:
        TestResult con estadístico D, valor crítico, veredicto y valor p.

    Note:
        Esta es una versión específica de KS para tendencia. No confundir
        con KS de bondad de ajuste (usado en frecuencia).

    Example:
        >>> # Serie con cambio de distribución en la mitad
        >>> serie = pd.Series([1, 2, 3, 4, 5, 100, 101, 102, 103, 104])
        >>> result = kolmogorov_smirnov_trend_test(serie)
        >>> result.verdict
        'REJECTED'  # Distribuciones diferentes
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
