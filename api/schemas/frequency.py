"""Schemas Pydantic para análisis de frecuencia - Contratos de datos de la API METIS.

Este módulo define todos los modelos de datos utilizados para la
serialización/deserialización en la API REST para el módulo de
análisis de frecuencia.

Jerarquía de schemas:
    SeriesInput → FrequencyFitRequest → FrequencyFitResponse
    DesignEventRequest → DesignEventResponse

    FrequencyFitResponse contiene:
        - series_id, n
        - estimation_method
        - distributions: lista de DistributionFitSchema
            - distribution_name, parameters, goodness_of_fit, is_recommended

    DesignEventResponse contiene:
        - return_period, annual_probability, design_value
        - distribution_name, parameters

Notas de diseño:
    - Todos los campos tienen descripciones para documentación automática
    - Se incluyen ejemplos en json_schema_extra para Swagger UI
    - Los veredictos usan Literal para validación de tipo
    - Los schemas heredan de BaseModel para validación automática

Contrato de estabilidad:
    Estos schemas forman parte del contrato público de la API.
    Cambios aquí requieren incremento de versión y consideración
    de retrocompatibilidad para consumidores (frontend, GeoAI).
"""

from typing import Literal

from pydantic import BaseModel, Field


class GoodnessOfFitSchema(BaseModel):
    """Indicadores de bondad de ajuste para una distribución.

    Schema de serialización para objetos GoodnessOfFit del core.
    Contiene los resultados de las pruebas estadísticas de bondad de ajuste.

    Attributes:
        chi_square: Estadístico de prueba Chi Cuadrado.
        chi_square_p_value: Valor p asociado a la prueba Chi Cuadrado.
        chi_square_verdict: Veredicto de la prueba Chi Cuadrado.
        ks_statistic: Estadístico de Kolmogorov-Smirnov.
        ks_p_value: Valor p asociado a la prueba KS.
        ks_verdict: Veredicto de la prueba KS.
        eea: Error Estándar de Ajuste (Standard Error of Fit).
        eea_verdict: Veredicto basado en el EEA.

    Example:
        >>> gof = GoodnessOfFitSchema(
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

    chi_square: float = Field(
        description="Estadistico de prueba Chi Cuadrado",
        json_schema_extra={"example": 5.23},
    )
    chi_square_p_value: float = Field(
        description="Valor p asociado a la prueba Chi Cuadrado",
        json_schema_extra={"example": 0.73},
    )
    chi_square_verdict: Literal["ACCEPTED", "REJECTED"] = Field(
        description="Veredicto de la prueba Chi Cuadrado",
        json_schema_extra={"example": "ACCEPTED"},
    )
    ks_statistic: float = Field(
        description="Estadistico de Kolmogorov-Smirnov",
        json_schema_extra={"example": 0.08},
    )
    ks_p_value: float = Field(
        description="Valor p asociado a la prueba KS",
        json_schema_extra={"example": 0.92},
    )
    ks_verdict: Literal["ACCEPTED", "REJECTED"] = Field(
        description="Veredicto de la prueba KS",
        json_schema_extra={"example": "ACCEPTED"},
    )
    eea: float = Field(
        description="Error Estandar de Ajuste (Standard Error of Fit)",
        json_schema_extra={"example": 0.045},
    )
    eea_verdict: Literal["ACCEPTED", "REJECTED"] = Field(
        description="Veredicto basado en el EEA",
        json_schema_extra={"example": "ACCEPTED"},
    )


class DistributionFitSchema(BaseModel):
    """Resultado del ajuste de una distribución a una serie hidrológica.

    Schema de serialización para objetos FitResult del core.
    Contiene la distribución calibrada, sus parámetros y los indicadores
    de bondad de ajuste.

    Attributes:
        distribution_name: Nombre de la distribución ajustada.
        parameters: Diccionario con los parámetros estimados.
        estimation_method: Método utilizado para estimar parámetros.
        goodness_of_fit: Indicadores de bondad de ajuste.
        is_recommended: Indica si esta distribución es la recomendada.

    Example:
        >>> fit = DistributionFitSchema(
        ...     distribution_name="Log-Pearson III",
        ...     parameters={"mu": 2.3, "sigma": 0.45, "gamma": 0.12},
        ...     estimation_method="MOM",
        ...     goodness_of_fit=gof,
        ...     is_recommended=True
        ... )
    """

    distribution_name: str = Field(
        description="Nombre de la distribucion ajustada",
        json_schema_extra={"example": "Log-Pearson III"},
    )
    parameters: dict[str, float] = Field(
        description="Parametros estimados de la distribucion",
        json_schema_extra={"example": {"mu": 2.3, "sigma": 0.45, "gamma": 0.12}},
    )
    estimation_method: Literal["MOM", "MLE", "MEnt"] = Field(
        description="Metodo de estimacion de parametros",
        json_schema_extra={"example": "MOM"},
    )
    goodness_of_fit: GoodnessOfFitSchema = Field(
        description="Indicadores de bondad de ajuste",
    )
    is_recommended: bool = Field(
        description="Indica si esta distribucion es la recomendada",
        json_schema_extra={"example": True},
    )


class FrequencyFitRequest(BaseModel):
    """Solicitud para ajustar distribuciones a una serie hidrológica.

    Contiene la serie de datos y las opciones de configuración para el
    análisis de frecuencia.

    Attributes:
        series: Lista de valores numéricos de la serie hidrológica.
        estimation_method: Método de estimación de parámetros.
        distribution_names: Lista de distribuciones a ajustar.
            Si es None, ajusta todas las disponibles.

    Example:
        >>> request = FrequencyFitRequest(
        ...     series=[100.5, 120.3, 95.2, 110.8, 105.1],
        ...     estimation_method="MOM"
        ... )
    """

    series: list[float] = Field(
        description="Lista de valores numericos de la serie hidrologica",
        json_schema_extra={"example": [100.5, 120.3, 95.2, 110.8, 105.1]},
    )
    estimation_method: Literal["MOM", "MLE", "MEnt"] = Field(
        description="Metodo de estimacion de parametros",
        json_schema_extra={"example": "MOM"},
    )
    distribution_names: list[str] | None = Field(
        default=None,
        description="Lista de distribuciones a ajustar. Si es None, ajusta todas.",
        json_schema_extra={"example": ["Log-Pearson III", "Gumbel", "GEV"]},
    )


class FrequencyFitResponse(BaseModel):
    """Respuesta del ajuste de distribuciones a una serie hidrológica.

    Contiene todos los resultados del análisis de frecuencia para la
    serie proporcionada.

    Attributes:
        n: Cantidad de observaciones válidas en la serie.
        estimation_method: Método de estimación utilizado.
        distributions: Lista de distribuciones ajustadas con sus indicadores.
        recommended_distribution: La distribución recomendada (mejor ajuste).

    Example:
        >>> response = FrequencyFitResponse(
        ...     n=35,
        ...     estimation_method="MOM",
        ...     distributions=[fit1, fit2, fit3],
        ...     recommended_distribution=fit1
        ... )
    """

    n: int = Field(
        description="Cantidad de observaciones validas en la serie",
        json_schema_extra={"example": 35},
    )
    estimation_method: Literal["MOM", "MLE", "MEnt"] = Field(
        description="Metodo de estimacion utilizado",
        json_schema_extra={"example": "MOM"},
    )
    distributions: list[DistributionFitSchema] = Field(
        description="Lista de distribuciones ajustadas con sus indicadores",
    )
    recommended_distribution: DistributionFitSchema | None = Field(
        default=None,
        description="La distribucion recomendada (mejor ajuste)",
    )


class DesignEventRequest(BaseModel):
    """Solicitud para calcular un evento de diseño.

    Contiene los parámetros de la distribución ajustada y el período
    de retorno deseado.

    Attributes:
        distribution_name: Nombre de la distribución.
        parameters: Parámetros estimados de la distribución.
        return_period: Período de retorno en años.

    Example:
        >>> request = DesignEventRequest(
        ...     distribution_name="Log-Pearson III",
        ...     parameters={"mu": 2.3, "sigma": 0.45, "gamma": 0.12},
        ...     return_period=100.0
        ... )
    """

    distribution_name: str = Field(
        description="Nombre de la distribucion",
        json_schema_extra={"example": "Log-Pearson III"},
    )
    parameters: dict[str, float] = Field(
        description="Parametros estimados de la distribucion",
        json_schema_extra={"example": {"mu": 2.3, "sigma": 0.45, "gamma": 0.12}},
    )
    return_period: float = Field(
        description="Periodo de retorno en años",
        json_schema_extra={"example": 100.0},
    )


class DesignEventResponse(BaseModel):
    """Respuesta del cálculo de evento de diseño.

    Contiene el valor del evento de diseño y la probabilidad anual
    de no excedencia.

    Attributes:
        return_period: Período de retorno T en años.
        annual_probability: Probabilidad anual de no excedencia (1 - 1/T).
        design_value: Valor del evento de diseño (caudal extremo).
        distribution_name: Nombre de la distribución utilizada.
        parameters: Parámetros de la distribución utilizada.

    Example:
        >>> response = DesignEventResponse(
        ...     return_period=100.0,
        ...     annual_probability=0.99,
        ...     design_value=1250.5,
        ...     distribution_name="Log-Pearson III",
        ...     parameters={"mu": 2.3, "sigma": 0.45, "gamma": 0.12}
        ... )
    """

    return_period: float = Field(
        description="Periodo de retorno T en años",
        json_schema_extra={"example": 100.0},
    )
    annual_probability: float = Field(
        description="Probabilidad anual de no excedencia (1 - 1/T)",
        json_schema_extra={"example": 0.99},
    )
    design_value: float = Field(
        description="Valor del evento de diseño (caudal extremo)",
        json_schema_extra={"example": 1250.5},
    )
    distribution_name: str = Field(
        description="Nombre de la distribucion utilizada",
        json_schema_extra={"example": "Log-Pearson III"},
    )
    parameters: dict[str, float] = Field(
        description="Parametros de la distribucion utilizada",
        json_schema_extra={"example": {"mu": 2.3, "sigma": 0.45, "gamma": 0.12}},
    )
