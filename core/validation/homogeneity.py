import numpy as np
import pandas as pd
from scipy import stats

from core.shared.types import GroupVerdict, TestResult


def helmert_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """
    Test de Helmert para homogeneidad de varianza.
    Compara varianza de primera mitad vs segunda mitad de la serie.
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
    """
    Test t de Student para homogeneidad de media.
    Compara media de primera mitad vs segunda mitad de la serie.
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
    """
    Test de Cramer-von Mises para homogeneidad de distribución.
    Verifica si ambas mitades provienen de la misma distribución.
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
    """
    Ejecuta las tres pruebas de homogeneidad.
    NO existe veredicto agregado, se devuelven los tres resultados individuales.
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
