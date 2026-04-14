"""Módulo de validación hidrológica - Pipeline completo de análisis.

Este módulo implementa el pipeline de validación estadística para series
hidrológicas, conforme a las especificaciones del dominio y la tesis de
referencia del Mgter. Ing. Facundo Ganancias.

Pipeline de Validación (orden de ejecución):
    1. Preprocesamiento: Eliminación de valores nulos
    2. Inconsistencias físicas: Detección de ceros, negativos, NaN
    3. Independencia: Test de Anderson (principal) + Wald-Wolfowitz (verif.)
    4. Homogeneidad: Helmert + t-Student + Cramer (sin veredicto agregado)
    5. Tendencia: Mann-Kendall + Kolmogorov-Smirnov (con veredicto OR)
    6. Atípicos: Test de Chow con transformación logarítmica opcional

Principios de diseño aplicados:
    - Detectar y advertir, nunca bloquear: El pipeline siempre completa
      todas las pruebas, incluso si hay inconsistencias físicas.
    - Jerarquía explícita: Independencia resuelve por Anderson; otros
      grupos aplican reglas de resolución documentadas.
    - Sin falsas seguridades: Homogeneidad no colapsa tres pruebas en una.

Uso típico:
    >>> from core.validation import run_validation_pipeline
    >>> import pandas as pd
    >>> serie = pd.Series([12.5, 15.3, 14.8, 16.2, 13.9])
    >>> report = run_validation_pipeline(serie)
    >>> print(report.independence.resolved_verdict)
    'ACCEPTED'
"""

import pandas as pd

# Importaciones de submódulos (deben estar antes de re-exportaciones)
from core.shared.preprocessing import detect_physical_inconsistencies
from core.shared.types import ValidationReport

# Re-exportaciones para acceso directo desde core.validation
from core.validation.homogeneity import (
    cramer_test,
    helmert_test,
    run_homogeneity,
    t_student_test,
)
from core.validation.independence import (
    anderson_test,
    resolve_independence,
    wald_wolfowitz_test,
)
from core.validation.outliers import chow_test, run_outliers
from core.validation.trend import (
    kolmogorov_smirnov_trend_test,
    mann_kendall_test,
    run_trend,
)


def run_validation_pipeline(series: pd.Series) -> ValidationReport:
    """Ejecuta el pipeline completo de validación hidrológica.

    Orquesta la ejecución secuencial de todas las pruebas estadísticas
    sobre una serie hidrológica, siguiendo el orden establecido en el
    dominio: preprocesamiento → inconsistencias → independencia →
    homogeneidad → tendencia → atípicos.

    Flujo de ejecución:
        1. Preprocesamiento: Elimina valores nulos y resetea índice
        2. Inconsistencias físicas: Detecta ceros, negativos, NaN (no bloquea)
        3. Independencia: Anderson (determinante) + Wald-Wolfowitz (verif.)
        4. Homogeneidad: Tres pruebas sin veredicto agregado
        5. Tendencia: Dos pruebas con resolución OR conservadora
        6. Atípicos: Chow con transformación logarítmica automática

    Args:
        series: Serie de Pandas con valores numéricos. Puede contener
            valores nulos (se eliminan), pero debe tener al menos 3
            valores válidos después del preprocesamiento.

    Returns:
        ValidationReport completo con:
            - n: Cantidad de observaciones válidas
            - warnings: Advertencias de inconsistencias físicas
            - independence: Resultados del grupo de independencia
            - homogeneity: Resultados del grupo de homogeneidad
            - trend: Resultados del grupo de tendencia
            - outliers: Resultados del grupo de atípicos

    Raises:
        ValueError: Implícito via scipy si n < 3 (series muy cortas).

    Note:
        Este es el punto de entrada principal del core estadístico.
        La API REST consume esta función directamente. La UI la invoca
        para obtener resultados que luego visualiza en modo semáforo.

    Example:
        >>> # Serie de ejemplo (referencia_1 truncada)
        >>> serie = pd.Series([
        ...     45.0, 78.2, 120.5, 95.3, 62.1, 88.7, 105.4, 72.9,
        ...     55.6, 91.3, 110.8, 84.2, 68.5, 97.1, 115.9, 79.4,
        ...     50.2, 85.7, 125.3, 102.6
        ... ])
        >>> report = run_validation_pipeline(serie)
        >>> report.n
        20
        >>> report.independence.resolved_verdict in ["ACCEPTED", "REJECTED"]
        True
        >>> len(report.warnings) >= 0
        True
    """
    # Siempre eliminar valores nulos antes de procesar
    series = series.dropna().reset_index(drop=True)
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
