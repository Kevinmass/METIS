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
    """
    Test de Chow para detección de outliers puntuales.
    Detecta observaciones atípicas basado en residuos de regresión lineal.
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
    """
    Ejecuta detección de outliers con test de Chow.
    """
    chow = chow_test(series)

    return GroupVerdict(
        condition="outliers",
        individual_results=[chow],
        resolved_verdict=chow.verdict,
        hierarchy_applied=False,
    )
