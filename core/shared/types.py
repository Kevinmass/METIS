"""Tipos compartidos del dominio de validación hidrológica.

Este módulo define las estructuras de datos fundamentales utilizadas
en todo el sistema METIS para representar resultados de pruebas
estadísticas y reportes de validación.

Las clases definidas aquí son inmutables (frozen dataclasses) y
serializables, permitiendo su uso tanto en el core estadístico
como en la capa de API y persistencia.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class TestResult:
    """Resultado de una prueba estadística individual.

    Representa el resultado de aplicar una prueba estadística específica
    (ej: Anderson, Mann-Kendall, Chow) sobre una serie hidrológica.

    Attributes:
        name: Nombre descriptivo de la prueba estadística.
            Ejemplo: "Anderson Autocorrelation Test"
        statistic: Valor numérico del estadístico calculado sobre la serie.
        critical_value: Valor de referencia para el nivel de significancia.
            Comparado contra el estadístico para determinar el veredicto.
        alpha: Nivel de significancia estadística. Siempre 0.05 en METIS.
        verdict: Veredicto binario de la prueba.
            "ACCEPTED": El estadístico no excede el valor crítico.
            "REJECTED": El estadístico excede el valor crítico.
        detail: Diccionario con datos adicionales específicos de la prueba.
            Ejemplo para Anderson: {"acf_lag1": 0.15, "acf_lag2": -0.08}
            Ejemplo para Chow: {"outliers_indices": [5, 23]}

    Example:
        >>> result = TestResult(
        ...     name="Mann-Kendall Trend Test",
        ...     statistic=1.94,
        ...     critical_value=1.96,
        ...     alpha=0.05,
        ...     verdict="ACCEPTED",
        ...     detail={"trend_direction": "none"}
        ... )
    """

    name: str
    statistic: float
    critical_value: float
    verdict: Literal["ACCEPTED", "REJECTED"]
    alpha: float = 0.05
    detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GroupVerdict:
    """Veredicto agrupado para una condición de validación.

    Agrupa los resultados de múltiples pruebas estadísticas que evalúan
    una misma condición sobre la serie hidrológica (independencia,
    homogeneidad, tendencia o atípicos).

    Nota sobre homogeneidad: Este grupo NO tiene veredicto resolutivo.
    Las tres pruebas (Helmert, t-Student, Cramer) se reportan
    individualmente sin colapsar en un único veredicto, evitando
    falsa seguridad ante resultados discordantes.

    Nota sobre independencia: Siempre se aplica jerarquía Anderson →
    Wald-Wolfowitz. Anderson es determinante; Wald-Wolfowitz actúa
    solo como verificación.

    Attributes:
        condition: Identificador de la condición validada.
            Valores permitidos: "independence", "homogeneity", "trend", "outliers"
        individual_results: Lista de resultados de cada prueba individual.
        resolved_verdict: Veredicto consolidado del grupo, si aplica.
            None para homogeneidad (no tiene veredicto agregado).
            "ACCEPTED" o "REJECTED" para independencia, tendencia y atípicos.
            "INCONCLUSIVE" si no se pudo determinar.
        hierarchy_applied: Indica si se aplicó una jerarquía entre pruebas.
            True solo para independencia cuando Anderson acepta pero
            Wald-Wolfowitz rechaza (Anderson prevalece).
            False en todos los demás casos.

    Example:
        >>> group = GroupVerdict(
        ...     condition="independence",
        ...     individual_results=[anderson_result, ww_result],
        ...     resolved_verdict="ACCEPTED",
        ...     hierarchy_applied=True
        ... )
    """

    condition: Literal["independence", "homogeneity", "trend", "outliers"]
    individual_results: list[TestResult]
    resolved_verdict: Literal["ACCEPTED", "REJECTED", "INCONCLUSIVE"] | None
    hierarchy_applied: bool


@dataclass(frozen=True)
class ValidationReport:
    """Reporte completo de validación de una serie hidrológica.

    Contiene los resultados de todas las pruebas estadísticas aplicadas
    sobre una serie, junto con advertencias de inconsistencias físicas
    detectadas en los datos de entrada.

    El pipeline de validación sigue el orden:
    1. Detección de inconsistencias físicas (ceros, negativos, NaN)
    2. Prueba de Independencia (Anderson + Wald-Wolfowitz)
    3. Prueba de Homogeneidad (Helmert + t-Student + Cramer)
    4. Prueba de Tendencia (Mann-Kendall + Kolmogorov-Smirnov)
    5. Detección de Atípicos (Chow)

    Attributes:
        n: Cantidad de observaciones válidas en la serie (después de
            eliminar valores nulos). Debe ser >= 3 para resultados válidos.
        warnings: Lista de advertencias sobre inconsistencias físicas.
            Cada advertencia es un dict con: code, message, indices afectados.
            Códigos posibles: "MISSING_VALUES", "ZERO_VALUES", "NEGATIVE_VALUES"
        independence: Resultados del grupo de pruebas de independencia.
        homogeneity: Resultados del grupo de pruebas de homogeneidad.
        trend: Resultados del grupo de pruebas de tendencia.
        outliers: Resultados del grupo de detección de atípicos.

    Example:
        >>> report = ValidationReport(
        ...     n=35,
        ...     warnings=[],
        ...     independence=independence_verdict,
        ...     homogeneity=homogeneity_verdict,
        ...     trend=trend_verdict,
        ...     outliers=outliers_verdict
        ... )
    """

    n: int
    warnings: list[dict]
    independence: GroupVerdict
    homogeneity: GroupVerdict
    trend: GroupVerdict
    outliers: GroupVerdict
