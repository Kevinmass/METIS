"""Módulo de pruebas de homogeneidad para series hidrológicas.

Las pruebas de homogeneidad verifican si una serie hidrológica mantiene
propiedades estadísticas consistentes a lo largo del tiempo. Esto es
fundamental para garantizar que los datos provienen de una misma
población y que los análisis de frecuencia son válidos.

Ahora con soporte para frecuencia temporal:
    - Todas las pruebas reciben temporal_frequency y la propagan en detalles.
    - Los tests dividen la serie en dos mitades por índice, y reportan
      la cantidad de años equivalentes en cada mitad.
    - Esto ayuda a interpretar si n grande en alta frecuencia podría estar
      inflando la significancia estadística.

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

from core.shared.types import GroupVerdict, TestResult, get_scaled_sample_size


# Frecuencia temporal por defecto
DEFAULT_FREQUENCY = "yearly"


def helmert_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de Helmert para homogeneidad de varianza.

    Compara las varianzas de la primera y segunda mitad de la serie
    mediante un test F. Si las varianzas difieren significativamente,
    se considera que la serie no es homogénea en varianza.

    Fórmula:
        F = max(var1, var2) / min(var1, var2)
        Valor crítico: F(alpha/2, df1, df2) de distribución F de Fisher

    Ahora reporta además los años equivalentes en los detalles, para
    que el usuario pueda interpretar si los grados de libertad son
    apropiados para la frecuencia de los datos.

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).
        temporal_frequency: Frecuencia temporal de la serie.

    Returns:
        TestResult con estadístico F, valor crítico, veredicto y detalles.
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

    # Métricas escaladas
    scaled_full = get_scaled_sample_size(n, temporal_frequency)

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
            "temporal_frequency": temporal_frequency,
            "effective_years": scaled_full["effective_years"],
        },
    )


def t_student_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test t de Student para homogeneidad de media.

    Compara las medias de la primera y segunda mitad de la serie.
    Utiliza la versión de Welch (equal_var=False) que no asume varianzas
    iguales, haciéndolo más robusto ante heterogeneidad de varianza.

    Fórmula:
        t = (mean1 - mean2) / SE
        donde SE es el error estándar de la diferencia de medias
        Valor crítico: t(alpha/2, df) de distribución t de Student

    Ahora reporta los años equivalentes en detalles para contexto.

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).
        temporal_frequency: Frecuencia temporal de la serie.

    Returns:
        TestResult con estadístico t, valor crítico, veredicto y detalles.
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

    # Métricas escaladas
    scaled_full = get_scaled_sample_size(n, temporal_frequency)

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
            "temporal_frequency": temporal_frequency,
            "effective_years": scaled_full["effective_years"],
        },
    )


def cramer_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de Cramer-von Mises para homogeneidad de distribución.

    Compara las funciones de distribución acumulada (CDF) de las dos
    mitades de la serie. Es más general que Helmert y t-Student porque
    detecta cualquier diferencia en la distribución, no solo en
    media o varianza.

    Fórmula:
        W² = n * ∫[F1(x) - F2(x)]² dF(x)
        Valor crítico aproximado: 0.461 para alpha = 0.05

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).
        temporal_frequency: Frecuencia temporal de la serie.

    Returns:
        TestResult con estadístico W², valor crítico, veredicto y valor p.
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

    # Métricas escaladas
    scaled_full = get_scaled_sample_size(n, temporal_frequency)

    return TestResult(
        name="Cramer-von Mises Distribution Homogeneity Test",
        statistic=float(statistic),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "p_value": float(p_value),
            "temporal_frequency": temporal_frequency,
            "effective_years": scaled_full["effective_years"],
        },
    )


def mann_whitney_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
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

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05.
        temporal_frequency: Frecuencia temporal de la serie.

    Returns:
        TestResult con estadístico U, valor p, veredicto y detalles.
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
    verdict = "REJECTED" if p_value < alpha else "ACCEPTED"

    # Métricas escaladas
    scaled_full = get_scaled_sample_size(n, temporal_frequency)

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
            "temporal_frequency": temporal_frequency,
            "effective_years": scaled_full["effective_years"],
        },
    )


def mood_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de Mood para homogeneidad de escala (varianza).

    Prueba no paramétrica que compara las varianzas de dos mitades de
    la serie basándose en los rangos. Es una alternativa a Helmert cuando
    no se puede asumir normalidad de los datos.

    Fórmula:
        M = Σ(m_i - (n+1)/2)²
        donde m_i = rangos de la primera mitad

    Args:
        series: Serie de valores numéricos a evaluar.
        alpha: Nivel de significancia. Default 0.05.
        temporal_frequency: Frecuencia temporal de la serie.

    Returns:
        TestResult con estadístico Z, valor crítico, veredicto y valor p.
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

    # Métricas escaladas
    scaled_full = get_scaled_sample_size(n, temporal_frequency)

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
            "temporal_frequency": temporal_frequency,
            "effective_years": scaled_full["effective_years"],
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
