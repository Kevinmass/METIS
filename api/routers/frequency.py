"""Router de análisis de frecuencia - Endpoints de ajuste de distribuciones.

Este módulo define los endpoints REST para ejecutar el análisis de
frecuencia hidrológica. Proporciona dos vías principales:

    1. POST /frequency/fit: Ajusta distribuciones a una serie.
    2. POST /frequency/design-event: Calcula evento de diseño.

Flujo de procesamiento (fit):
    1. Validación de entrada (vacío, longitud mínima)
    2. Conversión a pandas.Series
    3. Ejecución de core.frequency.fitting.fit_all_distributions()
    4. Serialización de FitResult a DistributionFitSchema
    5. Retorno de respuesta JSON estructurada

Flujo de procesamiento (design-event):
    1. Validación de entrada (parámetros, período de retorno)
    2. Reconstrucción de FitResult desde parámetros
    3. Ejecución de core.frequency.design_events.calculate_design_event()
    4. Serialización de DesignEvent a DesignEventResponse
    5. Retorno de respuesta JSON estructurada

Manejo de errores:
    - 400: Serie vacía, menos de 3 datos, período de retorno inválido
    - 422: Error en procesamiento (datos no numéricos, distribución inválida)
    - 200: Análisis completado

Nota de diseño:
    La API NUNCA retorna 500 por errores de datos del usuario.
    Todos los errores de validación se traducen en 400/422 con
    mensajes descriptivos.
"""

import math

import pandas as pd
from fastapi import APIRouter, HTTPException

from api.schemas.frequency import (
    DesignEventRequest,
    DesignEventResponse,
    DistributionFitSchema,
    FrequencyFitRequest,
    FrequencyFitResponse,
    GoodnessOfFitSchema,
)
from core.frequency.design_events import calculate_design_event
from core.frequency.fitting import fit_all_distributions
from core.shared.types import DesignEvent, FitResult, GoodnessOfFit


# Router de frecuencia
router = APIRouter()

# Constantes de validación
MIN_SERIES_LENGTH = 3


def sanitize_float(value: float) -> float:
    """Reemplaza inf/nan con valores finitos para JSON serialization.

    Args:
        value: Valor float a sanitizar.

    Returns:
        Valor finito (1e10 para inf, 0.0 para nan) o el valor original.
    """
    if not math.isfinite(value):
        return 1e10 if math.isinf(value) else 0.0
    return value


def sanitize_dict(data: dict) -> dict:
    """Sanitiza todos los valores float en un diccionario.

    Args:
        data: Diccionario con valores a sanitizar.

    Returns:
        Diccionario con valores inf/nan reemplazados.
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, float):
            result[key] = sanitize_float(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item)
                if isinstance(item, dict)
                else sanitize_float(item)
                if isinstance(item, float)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def convert_goodness_of_fit_to_schema(gof: GoodnessOfFit) -> GoodnessOfFitSchema:
    """Convierte GoodnessOfFit del core a schema Pydantic.

    Args:
        gof: Objeto GoodnessOfFit del core.

    Returns:
        Objeto GoodnessOfFitSchema para serialización.
    """
    return GoodnessOfFitSchema(
        chi_square=sanitize_float(gof.chi_square),
        chi_square_p_value=sanitize_float(gof.chi_square_p_value),
        chi_square_verdict=gof.chi_square_verdict,
        ks_statistic=sanitize_float(gof.ks_statistic),
        ks_p_value=sanitize_float(gof.ks_p_value),
        ks_verdict=gof.ks_verdict,
        eea=sanitize_float(gof.eea),
        eea_verdict=gof.eea_verdict,
    )


def convert_fit_result_to_schema(fit: FitResult) -> DistributionFitSchema:
    """Convierte FitResult del core a schema Pydantic.

    Args:
        fit: Objeto FitResult del core.

    Returns:
        Objeto DistributionFitSchema para serialización.
    """
    return DistributionFitSchema(
        distribution_name=fit.distribution_name,
        parameters=sanitize_dict(fit.parameters),
        estimation_method=fit.estimation_method,
        goodness_of_fit=convert_goodness_of_fit_to_schema(fit.goodness_of_fit),
        is_recommended=fit.is_recommended,
    )


def convert_design_event_to_schema(event: DesignEvent) -> DesignEventResponse:
    """Convierte DesignEvent del core a schema Pydantic.

    Args:
        event: Objeto DesignEvent del core.

    Returns:
        Objeto DesignEventResponse para serialización.
    """
    return DesignEventResponse(
        return_period=sanitize_float(event.return_period),
        annual_probability=sanitize_float(event.annual_probability),
        design_value=sanitize_float(event.design_value),
        distribution_name=event.distribution_name,
        parameters=sanitize_dict(event.parameters),
    )


def convert_schema_to_fit_result(
    distribution_name: str,
    parameters: dict[str, float],
    estimation_method: str = "MOM",
) -> FitResult:
    """Reconstruye un FitResult desde parámetros del schema.

    Nota: No se puede calcular la bondad de ajuste sin la serie original,
    por lo que se crea un objeto FitResult con valores placeholder.

    Args:
        distribution_name: Nombre de la distribución.
        parameters: Parámetros de la distribución.
        estimation_method: Método de estimación.

    Returns:
        Objeto FitResult con bondad de ajuste placeholder.
    """
    # Crear bondad de ajuste placeholder (no calculable sin serie)
    placeholder_gof = GoodnessOfFit(
        chi_square=0.0,
        chi_square_p_value=1.0,
        chi_square_verdict="ACCEPTED",
        ks_statistic=0.0,
        ks_p_value=1.0,
        ks_verdict="ACCEPTED",
        eea=0.0,
        eea_verdict="ACCEPTED",
    )

    return FitResult(
        distribution_name=distribution_name,
        parameters=parameters,
        estimation_method=estimation_method,  # type: ignore[arg-type]
        goodness_of_fit=placeholder_gof,
        is_recommended=True,
    )


@router.post("/fit", response_model=FrequencyFitResponse)
def fit_distributions(request: FrequencyFitRequest) -> FrequencyFitResponse:
    """Ajusta múltiples distribuciones a una serie hidrológica.

    Este endpoint ajusta las distribuciones de probabilidad especificadas
    a la serie de datos proporcionada, calculando los parámetros y los
    indicadores de bondad de ajuste para cada una.

    Args:
        request: Solicitud con la serie y opciones de configuración.

    Returns:
        Respuesta con todas las distribuciones ajustadas y la recomendada.

    Raises:
        HTTPException 400: Si la serie está vacía o tiene menos de 3 datos.
        HTTPException 422: Si hay errores en el procesamiento.
    """
    # Validar longitud mínima
    if len(request.series) < MIN_SERIES_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Series must have at least {MIN_SERIES_LENGTH} observations, "
                f"got {len(request.series)}"
            ),
        )

    # Convertir a pandas.Series
    try:
        series = pd.Series(request.series)
        # Eliminar NaN
        series = series.dropna()
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"Error processing series: {e!s}",
        ) from e

    # Validar después de eliminar NaN
    if len(series) < MIN_SERIES_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Series must have at least {MIN_SERIES_LENGTH} valid observations "
                f"after removing NaN, got {len(series)}"
            ),
        )

    # Ajustar distribuciones
    try:
        fit_results = fit_all_distributions(
            series=series,
            estimation_method=request.estimation_method,
            distribution_names=request.distribution_names,
        )
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"Error fitting distributions: {e!s}",
        ) from e

    # Convertir a schemas
    distribution_schemas = [convert_fit_result_to_schema(fit) for fit in fit_results]

    # Encontrar distribución recomendada
    recommended_schema = None
    for schema in distribution_schemas:
        if schema.is_recommended:
            recommended_schema = schema
            break

    return FrequencyFitResponse(
        n=len(series),
        estimation_method=request.estimation_method,
        distributions=distribution_schemas,
        recommended_distribution=recommended_schema,
    )


@router.post("/design-event", response_model=DesignEventResponse)
def calculate_design_event_endpoint(
    request: DesignEventRequest,
) -> DesignEventResponse:
    """Calcula un evento de diseño para un período de retorno dado.

    Este endpoint calcula el caudal extremo correspondiente a un período
    de retorno específico, utilizando una distribución previamente ajustada.

    Args:
        request: Solicitud con parámetros de distribución y período de retorno.

    Returns:
        Respuesta con el evento de diseño calculado.

    Raises:
        HTTPException 400: Si el período de retorno es inválido.
        HTTPException 422: Si la distribución es inválida o hay errores.
    """
    # Validar período de retorno
    if request.return_period <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Return period must be positive, got {request.return_period}",
        )

    # Reconstruir FitResult desde parámetros
    try:
        fit_result = convert_schema_to_fit_result(
            distribution_name=request.distribution_name,
            parameters=request.parameters,
            estimation_method="MOM",  # Placeholder, no afecta el cálculo
        )
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"Error reconstructing fit result: {e!s}",
        ) from e

    # Calcular evento de diseño
    try:
        design_event = calculate_design_event(
            fit_result=fit_result,
            return_period=request.return_period,
        )
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"Error calculating design event: {e!s}",
        ) from e

    # Convertir a schema
    return convert_design_event_to_schema(design_event)
