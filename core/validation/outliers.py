"""Módulo de detección de valores atípicos (outliers) para series hidrológicas.

Los valores atípicos son observaciones que se desvían significativamente
del patrón general de la serie. En hidrología, pueden representar:
    - Eventos extremos reales (inundaciones, sequías)
    - Errores de medición o registro
    - Cambios en la estación de medición

Pruebas implementadas:
    - Chow: Detección basada en residuos studentizados de regresión lineal.
      Identifica puntos que rompen el patrón lineal de la serie.

Transformación logarítmica:
    El test de Chow aplica transformación logarítmica por defecto (use_log=True)
    para estabilizar la varianza y hacer la serie más simétrica. Si la serie
    contiene ceros o negativos, la transformación se omite automáticamente.

Tratamiento de outliers:
    METIS detecta y reporta outliers pero NUNCA los elimina automáticamente.
    El ingeniero decide si son eventos válidos a modelar (extremos) o
    errores que deben corregirse.
"""

import numpy as np
import pandas as pd
from scipy import stats

from core.shared.preprocessing import (
    apply_log_transform,
    detect_physical_inconsistencies,
)
from core.shared.types import GroupVerdict, TestResult


def chow_test(
    series: pd.Series, *, use_log: bool = True, alpha: float = 0.05
) -> TestResult:
    """Test de Chow para detección de valores atípicos (outliers).

    Detecta observaciones atípicas basándose en los residuos studentizados
    de una regresión lineal ajustada a la serie. Los puntos con residuos
    que exceden el valor crítico t de Student son marcados como atípicos.

    Fórmula:
        Residuos studentizados:
            t_i = e_i / √(MSE * (1 - h_ii))

        donde:
            e_i = residual del punto i (observado - predicho)
            MSE = error cuadrático medio de la regresión
            h_ii = elemento diagonal de la matriz hat (leverage)

        Valor crítico: t_(alpha/(2n), df=n-2) de distribución t de Student
        (corrección de Bonferroni para test múltiple)

    Interpretación:
        - |t_i| > t_crítico: Punto i marcado como atípico
        - Múltiples atípicos: Veredicto "REJECTED"
        - Sin atípicos: Veredicto "ACCEPTED"

    Args:
        series: Serie temporal de valores numéricos positivos.
        use_log: Si True, aplica ln(x) antes de la regresión. Default True.
            La transformación logarítmica estabiliza la varianza.
            Se omite automáticamente si hay ceros o negativos.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).

    Returns:
        TestResult con máximo residual absoluto, valor crítico, veredicto y
        detalles incluyendo índices de atípicos, cantidad, estado de la
        transformación logarítmica y advertencias de inconsistencias físicas.

    Note:
        La detección se realiza sobre residuos studentizados, no sobre
        valores brutos. Un valor extremo no siempre es atípico si se
        ajusta al patrón de la serie.

    Example:
        >>> # Serie con un valor claramente atípico
        >>> serie = pd.Series([10, 11, 12, 13, 100, 11, 12, 13])
        >>> result = chow_test(serie)
        >>> result.verdict
        'REJECTED'
        >>> 4 in result.detail["outliers_indices"]  # índice del valor 100
        True
    """
    n = len(series)
    x = np.arange(n)
    y = series.to_numpy()

    warnings = detect_physical_inconsistencies(series)

    if use_log:
        y, log_warnings = apply_log_transform(series)
        warnings.extend(log_warnings)
        y = y.to_numpy()

    # Ajuste de regresión lineal
    slope, intercept, _r_value, _p_value, _std_err = stats.linregress(x, y)
    y_pred = intercept + slope * x
    residuals = y - y_pred

    # Calcular studentized residuals
    mse = np.sum(residuals**2) / (n - 2)
    hat_matrix_diag = 1 / n + (x - np.mean(x)) ** 2 / np.sum((x - np.mean(x)) ** 2)
    studentized_residuals = residuals / np.sqrt(mse * (1 - hat_matrix_diag))

    # Valor crítico t de Student
    critical_value = stats.t.ppf(1 - alpha / (2 * n), df=n - 2)

    # Detectar outliers
    outliers_indices = np.where(np.abs(studentized_residuals) > critical_value)[
        0
    ].tolist()
    max_residual = np.max(np.abs(studentized_residuals))

    verdict = "REJECTED" if len(outliers_indices) > 0 else "ACCEPTED"

    return TestResult(
        name="Chow Outlier Test",
        statistic=float(max_residual),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "outliers_indices": outliers_indices,
            "outliers_count": len(outliers_indices),
            "log_transform_applied": use_log
            and not any(w["code"] == "LOG_TRANSFORM_SKIPPED" for w in warnings),
            "warnings": warnings,
        },
    )


def run_outliers(series: pd.Series) -> GroupVerdict:
    """Ejecuta detección de atípicos sobre una serie.

    Orquesta la ejecución del test de Chow. Este grupo tiene un único
    resultado (Chow) que también determina el veredicto resolutivo.

    Args:
        series: Serie temporal de valores numéricos positivos.

    Returns:
        GroupVerdict con condition="outliers", resultado de Chow como
        único elemento de individual_results, resolved_verdict igual
        al veredicto de Chow, y hierarchy_applied=False.

    Example:
        >>> serie = pd.Series([10, 11, 12, 100, 11, 12])
        >>> group = run_outliers(serie)
        >>> group.resolved_verdict == group.individual_results[0].verdict
        True
    """
    chow = chow_test(series)

    return GroupVerdict(
        condition="outliers",
        individual_results=[chow],
        resolved_verdict=chow.verdict,
        hierarchy_applied=False,
    )


def kn_outlier_detection(series: pd.Series, *, alpha: float = 0.05) -> TestResult:
    """Detección de atípicos mediante método Kn.

    El método Kn usa límites dinámicos basados en el tamaño de muestra
    para detectar valores atípicos. Es un método estadístico simple
    basado en desvíos estándar ajustados por n.

    Fórmula:
        Kn = 0.4083 * ln(n) + 1.1584
        Límite superior = media + Kn * desv_estándar
        Límite inferior = media - Kn * desv_estándar

    Interpretación:
        - Valores fuera de [límite_inf, límite_sup] son marcados como atípicos
        - Si hay atípicos detectados: veredicto "REJECTED"
        - Sin atípicos: veredicto "ACCEPTED"

    Args:
        series: Serie temporal de valores numéricos.
        alpha: Nivel de significancia. Default 0.05 (no usado directamente
            en Kn pero mantenido por consistencia de API).

    Returns:
        TestResult con máximo residual absoluto, límites Kn, veredicto y
        detalles incluyendo índices de atípicos, cantidad, límites calculados.

    Note:
        Este método es complementario al test de Chow. Mientras Chow usa
        residuos studentizados de regresión, Kn usa límites simples basados
        en media y desvío estándar.

    Example:
        >>> serie = pd.Series([10, 11, 12, 13, 100, 11, 12, 13])
        >>> result = kn_outlier_detection(serie)
        >>> result.verdict
        'REJECTED'
        >>> 4 in result.detail["outliers_indices"]  # índice del valor 100
        True
    """
    n = len(series)
    x = series.to_numpy()

    # Calcular Kn
    kn = 0.4083 * np.log(n) + 1.1584

    media_val = float(np.mean(x))
    sd_val = float(np.std(x, ddof=1))

    limite_superior = media_val + kn * sd_val
    limite_inferior = media_val - kn * sd_val

    # Detectar outliers
    outliers_mask = (x > limite_superior) | (x < limite_inferior)
    outliers_indices = np.where(outliers_mask)[0].tolist()
    outliers_count = len(outliers_indices)

    # Calcular estadístico como distancia máxima al límite más cercano
    if outliers_count > 0:
        distances = np.array(
            [
                abs(x[i] - limite_superior)
                if x[i] > limite_superior
                else abs(x[i] - limite_inferior)
                if x[i] < limite_inferior
                else 0
                for i in range(n)
            ]
        )
        max_distance = np.max(distances[outliers_mask]) if outliers_count > 0 else 0
    else:
        max_distance = 0

    verdict = "REJECTED" if outliers_count > 0 else "ACCEPTED"

    return TestResult(
        name="Kn Outlier Detection",
        statistic=float(max_distance),
        critical_value=[float(limite_inferior), float(limite_superior)],
        alpha=alpha,
        verdict=verdict,
        detail={
            "outliers_indices": outliers_indices,
            "outliers_count": outliers_count,
            "kn_value": float(kn),
            "mean": media_val,
            "std_dev": sd_val,
            "lower_limit": float(limite_inferior),
            "upper_limit": float(limite_superior),
        },
    )


def run_outliers_with_kn(series: pd.Series) -> GroupVerdict:
    """Ejecuta detección de atípicos con ambos métodos (Chow y Kn).

    Orquesta la ejecución del test de Chow y la detección Kn sobre la serie.
    Este grupo reporta ambos métodos individualmente.

    Args:
        series: Serie temporal de valores numéricos positivos.

    Returns:
        GroupVerdict con condition="outliers", resultados de Chow y Kn,
        resolved_verdict igual a "REJECTED" si cualquiera detecta outliers,
        y hierarchy_applied=False.

    Example:
        >>> serie = pd.Series([10, 11, 12, 100, 11, 12])
        >>> group = run_outliers_with_kn(serie)
        >>> len(group.individual_results)
        2
    """
    chow = chow_test(series)
    kn = kn_outlier_detection(series)

    # Veredicto resolutivo: si cualquiera detecta outliers -> rechazado
    resolved_verdict = (
        "REJECTED"
        if (chow.verdict == "REJECTED" or kn.verdict == "REJECTED")
        else "ACCEPTED"
    )

    return GroupVerdict(
        condition="outliers",
        individual_results=[chow, kn],
        resolved_verdict=resolved_verdict,
        hierarchy_applied=False,
    )
