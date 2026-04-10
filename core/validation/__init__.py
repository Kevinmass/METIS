import pandas as pd

from core.shared.preprocessing import detect_physical_inconsistencies
from core.shared.types import ValidationReport
from core.validation.homogeneity import run_homogeneity
from core.validation.independence import (
    anderson_test,
    resolve_independence,
    wald_wolfowitz_test,
)
from core.validation.outliers import run_outliers
from core.validation.trend import run_trend


def run_validation_pipeline(series: pd.Series) -> ValidationReport:
    """
    Orquestador principal del pipeline de validación hidrológica.
    Ejecuta en orden los cuatro grupos de pruebas y devuelve el reporte completo.
    """
    n = len(series)

    # Paso 1: Detección de inconsistencias físicas
    warnings = detect_physical_inconsistencies(series)

    # Paso 2: Independencia
    anderson = anderson_test(series)
    ww = wald_wolfowitz_test(series)
    independence = resolve_independence(anderson, ww)

    # Paso 3: Homogeneidad
    homogeneity = run_homogeneity(series)

    # Paso 4: Tendencia
    trend = run_trend(series)

    # Paso 5: Outliers
    outliers = run_outliers(series)

    return ValidationReport(
        n=n,
        warnings=warnings,
        independence=independence,
        homogeneity=homogeneity,
        trend=trend,
        outliers=outliers,
    )


__all__ = [
    "anderson_test",
    "chow_test",
    "cramer_test",
    "helmert_test",
    "kolmogorov_smirnov_trend_test",
    "mann_kendall_test",
    "resolve_independence",
    "run_homogeneity",
    "run_outliers",
    "run_trend",
    "run_validation_pipeline",
    "t_student_test",
    "wald_wolfowitz_test",
]
