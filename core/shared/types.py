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


@dataclass(frozen=True)
class GoodnessOfFit:
    """Indicadores de bondad de ajuste para una distribución.

    Contiene los resultados de las pruebas estadísticas que evalúan
    qué tan bien se ajusta una distribución teórica a los datos observados.

    Attributes:
        chi_square: Estadístico de prueba Chi Cuadrado.
        chi_square_p_value: Valor p asociado a la prueba Chi Cuadrado.
        chi_square_verdict: Veredicto de la prueba Chi Cuadrado.
        ks_statistic: Estadístico de Kolmogorov-Smirnov.
        ks_p_value: Valor p asociado a la prueba KS.
        ks_verdict: Veredicto de la prueba KS.
        eea: Error Estándar de Ajuste (Standard Error of Fit).
        eea_verdict: Veredicto basado en el EEA (aceptado si < umbral).

    Example:
        >>> gof = GoodnessOfFit(
        ...     chi_square=5.23,
        ...     chi_square_p_value=0.73,
        ...     chi_square_verdict="ACCEPTED",
        ...     ks_statistic=0.08,
        ...     ks_p_value=0.92,
        ...     ks_verdict="ACCEPTED",
        ...     eea=0.045,
        ...     eea_verdict="ACCEPTED"
        ... )
    """

    chi_square: float
    chi_square_p_value: float
    chi_square_verdict: Literal["ACCEPTED", "REJECTED"]
    ks_statistic: float
    ks_p_value: float
    ks_verdict: Literal["ACCEPTED", "REJECTED"]
    eea: float
    eea_verdict: Literal["ACCEPTED", "REJECTED"]


@dataclass(frozen=True)
class FitResult:
    """Resultado del ajuste de una distribución a una serie hidrológica.

    Contiene la distribución calibrada, sus parámetros estimados y los
    indicadores de bondad de ajuste.

    Attributes:
        distribution_name: Nombre de la distribución ajustada.
            Ejemplo: "Log-Pearson III", "Gumbel", "GEV"
        parameters: Diccionario con los parámetros estimados.
            Las claves dependen de la distribución:
            - Normal: {"mu": float, "sigma": float}
            - Log-Normal: {"mu": float, "sigma": float}
            - Gumbel: {"xi": float, "alpha": float}
            - GEV: {"xi": float, "alpha": float, "k": float}
            - Pearson III: {"mu": float, "sigma": float, "gamma": float}
            - Log-Pearson III: {"mu": float, "sigma": float, "gamma": float}
        estimation_method: Método utilizado para estimar parámetros.
            Valores: "MOM" (Método de Momentos), "MLE" (Máxima Verosimilitud),
            "MEnt" (Máxima Entropía)
        goodness_of_fit: Indicadores de bondad de ajuste.
        is_recommended: Indica si esta distribución es la recomendada
            según los criterios de bondad de ajuste.

    Example:
        >>> fit = FitResult(
        ...     distribution_name="Log-Pearson III",
        ...     parameters={"mu": 2.3, "sigma": 0.45, "gamma": 0.12},
        ...     estimation_method="MOM",
        ...     goodness_of_fit=gof,
        ...     is_recommended=True
        ... )
    """

    distribution_name: str
    parameters: dict[str, float]
    estimation_method: Literal["MOM", "MLE", "MEnt"]
    goodness_of_fit: GoodnessOfFit
    is_recommended: bool


@dataclass(frozen=True)
class DesignEvent:
    """Evento de diseño calculado a partir de una distribución ajustada.

    Representa el valor de caudal extremo correspondiente a un período
    de retorno dado, utilizado en ingeniería hidrológica para diseño
    de estructuras hidráulicas.

    Attributes:
        return_period: Período de retorno T en años.
            Ejemplo: 100 para evento centenario, 50 para evento quincuagenal.
        annual_probability: Probabilidad anual de ocurrencia, calculada como 1/T.
            Ejemplo: 0.01 para T=100, 0.02 para T=50.
        design_value: Valor del evento de diseño (caudal extremo) en las
            unidades de la serie original (ej: m³/s).
        distribution_name: Nombre de la distribución utilizada para el cálculo.
        parameters: Parámetros de la distribución utilizada.

    Example:
        >>> event = DesignEvent(
        ...     return_period=100.0,
        ...     annual_probability=0.01,
        ...     design_value=1250.5,
        ...     distribution_name="Log-Pearson III",
        ...     parameters={"mu": 2.3, "sigma": 0.45, "gamma": 0.12}
        ... )
    """

    return_period: float
    annual_probability: float
    design_value: float
    distribution_name: str
    parameters: dict[str, float]
