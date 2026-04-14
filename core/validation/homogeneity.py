"""Módulo de pruebas de homogeneidad para series hidrológicas.

Las pruebas de homogeneidad verifican si una serie hidrológica mantiene
propiedades estadísticas consistentes a lo largo del tiempo. Esto es
fundamental para garantizar que los datos provienen de una misma
población y que los análisis de frecuencia son válidos.

Pruebas implementadas:
    - Helmert: Compara varianzas de dos mitades de la serie.
    - t-Student: Compara medias de dos mitades de la serie.
    - Cramer-von Mises: Compara distribuciones completas.

Nota de diseño METIS:
    Este grupo NO tiene veredicto agregado. Las tres pruebas se reportan
    individualmente porque pueden dar resultados discordantes. Un ingeniero
    puede encontrar varianza constante (Helmert acepta) pero cambio de
    media (t-Student rechaza). No colapsamos estos resultados en un único
    veredicto para evitar falsa seguridad.
"""

import numpy as np
import pandas as pd
from scipy import stats

from core.shared.types import GroupVerdict, TestResult


def helmert_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """Test de Helmert para homogeneidad de varianza.

    Compara las varianzas de la primera y segunda mitad de la serie
    mediante un test F. Si las varianzas difieren significativamente,
    se considera que la serie no es homogénea en varianza.

    Fórmula:
        F = max(var1, var2) / min(var1, var2)
        Valor crítico: F(alpha/2, df1, df2) de distribución F de Fisher

    Interpretación:
        - Si F > F_crítico: Se rechaza homogeneidad de varianza
        - Si F ≤ F_crítico: Se acepta homogeneidad de varianza

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).

    Returns:
        TestResult con estadístico F, valor crítico, veredicto y
        detalles incluyendo varianzas de ambas mitades y grados de libertad.

    Example:
        >>> serie = pd.Series([10, 12, 11, 13, 100, 105, 102, 108])
        >>> result = helmert_test(serie)
        >>> result.verdict
        'REJECTED'  # Varianzas muy diferentes entre mitades
    """
    n = len(series)
    mid = n // 2

    group1 = series.iloc[:mid]
    group2 = series.iloc[mid:]

    var1 = np.var(group1, ddof=1)
    var2 = np.var(group2, ddof=1)

    # Estadístico F = varianza mayor / varianza menor
    f_stat = max(var1, var2) / min(var1, var2)

    df1 = len(group1) - 1
    df2 = len(group2) - 1

    critical_value = stats.f.ppf(1 - alpha / 2, df1, df2)
    verdict = "REJECTED" if f_stat > critical_value else "ACCEPTED"

    return TestResult(
        name="Helmert Variance Homogeneity Test",
        statistic=float(f_stat),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "variance_first_half": float(var1),
            "variance_second_half": float(var2),
            "df1": int(df1),
            "df2": int(df2),
        },
    )


def t_student_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """Test t de Student para homogeneidad de media.

    Compara las medias de la primera y segunda mitad de la serie.
    Utiliza la versión de Welch (equal_var=False) que no asume varianzas
    iguales, haciéndolo más robusto ante heterogeneidad de varianza.

    Fórmula:
        t = (mean1 - mean2) / SE
        donde SE es el error estándar de la diferencia de medias
        Valor crítico: t(alpha/2, df) de distribución t de Student

    Interpretación:
        - Si |t| > t_crítico: Se rechaza igualdad de medias
        - Si |t| ≤ t_crítico: Se acepta igualdad de medias

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).

    Returns:
        TestResult con estadístico t, valor crítico, veredicto y
        detalles incluyendo medias de ambas mitades y valor p.

    Example:
        >>> serie = pd.Series([10, 11, 12, 50, 51, 52])  # Salto en media
        >>> result = t_student_test(serie)
        >>> result.verdict
        'REJECTED'  # Medias significativamente diferentes
    """
    n = len(series)
    mid = n // 2

    group1 = series.iloc[:mid]
    group2 = series.iloc[mid:]

    t_stat, p_value = stats.ttest_ind(
        group1, group2, equal_var=False, alternative="two-sided"
    )

    critical_value = stats.t.ppf(1 - alpha / 2, df=len(series) - 2)
    verdict = "REJECTED" if abs(t_stat) > critical_value else "ACCEPTED"

    return TestResult(
        name="Student t Mean Homogeneity Test",
        statistic=float(abs(t_stat)),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "mean_first_half": float(np.mean(group1)),
            "mean_second_half": float(np.mean(group2)),
            "p_value": float(p_value),
        },
    )


def cramer_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """Test de Cramer-von Mises para homogeneidad de distribución.

    Compara las funciones de distribución acumulada (CDF) de las dos
    mitades de la serie. Es más general que Helmert y t-Student porque
    detecta cualquier diferencia en la distribución, no solo en
    media o varianza.

    Fórmula:
        W² = n * ∫[F1(x) - F2(x)]² dF(x)
        Valor crítico aproximado: 0.461 para alpha = 0.05

    Interpretación:
        - Si W² > 0.461: Se rechaza igualdad de distribuciones
        - Si W² ≤ 0.461: Se acepta igualdad de distribuciones

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).

    Returns:
        TestResult con estadístico W², valor crítico, veredicto y
        valor p asociado.

    Note:
        Implementación basada en scipy.stats.cramervonmises_2samp,
        que calcula el estadístico de forma exacta.

    Example:
        >>> serie = pd.Series([1, 2, 3, 100, 101, 102])  # Distribuciones diferentes
        >>> result = cramer_test(serie)
        >>> result.verdict
        'REJECTED'  # Distribuciones significativamente diferentes
    """
    n = len(series)
    mid = n // 2

    group1 = series.iloc[:mid]
    group2 = series.iloc[mid:]

    result = stats.cramervonmises_2samp(group1, group2)
    statistic = result.statistic
    p_value = result.pvalue

    # Valor crítico para alpha=0.05 es aproximadamente 0.461
    critical_value = 0.461
    verdict = "REJECTED" if statistic > critical_value else "ACCEPTED"

    return TestResult(
        name="Cramer-von Mises Distribution Homogeneity Test",
        statistic=float(statistic),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={"p_value": float(p_value)},
    )


def run_homogeneity(series: pd.Series) -> GroupVerdict:
    """Ejecuta las tres pruebas de homogeneidad sobre una serie.

    Orquesta la ejecución de Helmert (varianza), t-Student (media) y
    Cramer-von Mises (distribución) sobre la serie proporcionada.

    Como politica de diseño METIS, este grupo NO produce un veredicto
    agregado. Las tres pruebas se reportan individualmente porque:
        1. Helmert puede rechazar mientras t-Student y Cramer aceptan
        2. El ingeniero debe evaluar cada aspecto por separado
        3. No hay regla matemática única para colapsar estos resultados

    Args:
        series: Serie de valores numéricos a evaluar.

    Returns:
        GroupVerdict con condition="homogeneity", los tres resultados
        individuales, resolved_verdict=None (intencionalmente) y
        hierarchy_applied=False (no aplica jerarquía en este grupo).

    Example:
        >>> serie = pd.Series([10, 11, 12, 50, 51, 52])
        >>> group = run_homogeneity(serie)
        >>> len(group.individual_results)
        3
        >>> group.resolved_verdict is None
        True  # No hay veredicto agregado por diseño
    """
    helmert = helmert_test(series)
    t_student = t_student_test(series)
    cramer = cramer_test(series)

    return GroupVerdict(
        condition="homogeneity",
        individual_results=[helmert, t_student, cramer],
        resolved_verdict=None,
        hierarchy_applied=False,
    )
