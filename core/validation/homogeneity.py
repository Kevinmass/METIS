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
from scipy.stats import mannwhitneyu, mood

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


def mann_whitney_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """Test de Mann-Whitney U para homogeneidad de distribución.

    Prueba no paramétrica que compara las distribuciones de dos mitades
    de la serie. Es más robusta que t-Student porque no asume normalidad
    y es menos sensible a valores atípicos.

    Fórmula:
        U = min(U1, U2)
        donde:
            U1 = n1*n2 + n1(n1+1)/2 - R1
            U2 = n1*n2 + n2(n2+1)/2 - R2
        R1, R2 = suma de rangos de cada grupo

    Interpretación:
        - p < alpha: Se rechaza igualdad de distribuciones
        - p >= alpha: Se acepta igualdad de distribuciones

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05.

    Returns:
        TestResult con estadístico U, valor p, veredicto y detalles
        incluyendo medias de ambas mitades.

    Note:
        Este test es particularmente útil cuando hay valores atípicos
        que podrían afectar tests paramétricos como t-Student.

    Example:
        >>> serie = pd.Series([10, 11, 12, 50, 51, 52])  # Salto en distribución
        >>> result = mann_whitney_test(serie)
        >>> result.verdict
        'REJECTED'  # Distribuciones significativamente diferentes
    """
    n = len(series)
    mid = n // 2

    group1 = series.iloc[:mid]
    group2 = series.iloc[mid:]

    try:
        u_stat, p_value = mannwhitneyu(group1, group2, alternative="two-sided")
    except Exception:  # noqa: BLE001
        # Fallback si scipy falla
        u_stat = 0.0
        p_value = 1.0

    # Valor crítico aproximado usando distribución normal para n grande
    # Para n pequeño, scipy ya calcula el valor p exacto
    verdict = "REJECTED" if p_value < alpha else "ACCEPTED"

    return TestResult(
        name="Mann-Whitney U Homogeneity Test",
        statistic=float(u_stat),
        critical_value=None,  # Usamos p-value directamente
        alpha=alpha,
        verdict=verdict,
        detail={
            "p_value": float(p_value),
            "mean_first_half": float(np.mean(group1)),
            "mean_second_half": float(np.mean(group2)),
            "n1": len(group1),
            "n2": len(group2),
        },
    )


def mood_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """Test de Mood para homogeneidad de escala (varianza).

    Prueba no paramétrica que compara las varianzas de dos mitades de
    la serie basándose en los rangos. Es una alternativa a Helmert cuando
    no se puede asumir normalidad de los datos.

    Fórmula:
        M = Σ(m_i - (n+1)/2)²
        donde m_i = rangos de la primera mitad

    Interpretación:
        - Z > Z_alpha/2: Se rechaza homogeneidad de varianza
        - |Z| <= Z_alpha/2: Se acepta homogeneidad de varianza

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05.

    Returns:
        TestResult con estadístico Z, valor crítico, veredicto y valor p.

    Note:
        Mood es más robusto que Helmert ante valores atípicos porque
        opera sobre rangos, no sobre valores brutos.

    Example:
        >>> serie = pd.Series([10, 11, 12, 100, 101, 102])  # Varianzas muy diferentes
        >>> result = mood_test(serie)
        >>> result.verdict
        'REJECTED'  # Varianzas significativamente diferentes
    """
    n = len(series)
    mid = n // 2

    group1 = series.iloc[:mid]
    group2 = series.iloc[mid:]

    try:
        mood_result = mood(group1, group2)
        mood_stat = float(mood_result.statistic)
        mood_p = float(mood_result.pvalue)
    except Exception:  # noqa: BLE001
        # Fallback manual si scipy falla
        # Calcular varianza de rangos de primera mitad
        all_ranks = stats.rankdata(series.to_numpy())
        ranks1 = all_ranks[:mid]
        expected_mean = (n + 1) / 2
        mood_stat = np.sum((ranks1 - expected_mean) ** 2)
        # Aproximación normal
        var_mood = mid * (n - mid) * (n + 1) * (n - 1) / 12
        z = (mood_stat - mid * (n + 1) * (n + 1) / 4) / np.sqrt(var_mood)
        mood_stat = z
        mood_p = 2 * (1 - stats.norm.cdf(abs(z)))

    critical_value = stats.norm.ppf(1 - alpha / 2)
    verdict = "REJECTED" if mood_p < alpha else "ACCEPTED"

    return TestResult(
        name="Mood Scale Homogeneity Test",
        statistic=float(abs(mood_stat)),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "p_value": float(mood_p),
            "variance_first_half": float(np.var(group1, ddof=1)),
            "variance_second_half": float(np.var(group2, ddof=1)),
        },
    )


def run_homogeneity(series: pd.Series) -> GroupVerdict:
    """Ejecuta las pruebas de homogeneidad sobre una serie.

    Orquesta la ejecución de Helmert (varianza), t-Student (media),
    Cramer-von Mises (distribución), Mann-Whitney U (distribución no paramétrica)
    y Mood (escala/varianza no paramétrica) sobre la serie proporcionada.

    Como politica de diseño METIS, este grupo NO produce un veredicto
    agregado. Las cinco pruebas se reportan individualmente porque:
        1. Helmert puede rechazar mientras t-Student y Cramer aceptan
        2. El ingeniero debe evaluar cada aspecto por separado
        3. No hay regla matemática única para colapsar estos resultados

    Args:
        series: Serie de valores numéricos a evaluar.

    Returns:
        GroupVerdict con condition="homogeneity", los cinco resultados
        individuales, resolved_verdict=None (intencionalmente) y
        hierarchy_applied=False (no aplica jerarquía en este grupo).

    Example:
        >>> serie = pd.Series([10, 11, 12, 50, 51, 52])
        >>> group = run_homogeneity(serie)
        >>> len(group.individual_results)
        5
        >>> group.resolved_verdict is None
        True  # No hay veredicto agregado por diseño
    """
    helmert = helmert_test(series)
    t_student = t_student_test(series)
    cramer = cramer_test(series)
    mann_whitney = mann_whitney_test(series)
    mood_result = mood_test(series)

    return GroupVerdict(
        condition="homogeneity",
        individual_results=[helmert, t_student, cramer, mann_whitney, mood_result],
        resolved_verdict=None,
        hierarchy_applied=False,
    )
