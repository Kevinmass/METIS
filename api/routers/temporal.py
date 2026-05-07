"""Router para agregación temporal de series hidrológicas.

Proporciona endpoints para:
    - Detectar frecuencia temporal de series
    - Agregar series a resolución anual
    - Bypass automático para series ya anualizadas

Endpoints:
    POST /temporal/aggregate: Agrega serie a anual
    POST /temporal/detect-frequency: Detecta frecuencia temporal
"""

from typing import Literal

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.temporal.aggregation import (
    auto_aggregate,
    detect_frequency,
    get_available_targets,
)


router = APIRouter(prefix="/temporal", tags=["temporal"])


class TemporalAggregateRequest(BaseModel):
    """Request para agregación temporal.

    Attributes:
        dates: Lista de fechas en formato ISO (YYYY-MM-DD).
        values: Lista de valores numéricos correspondientes.
        target_frequency: Frecuencia objetivo.
            Opciones: "hourly", "daily", "monthly", "yearly".
        aggregation_method: Método de agregación ("sum", "mean", "max", "min").
        hydrological_year: Si True, usa año hidrológico.
        hydrological_start_month: Mes de inicio del año hidrológico (1-12).
        daily_start_hour: Hora de inicio del período diario (0-23, default 0 = medianoche).
    """

    dates: list[str]
    values: list[float]
    target_frequency: Literal[
        "5min", "minutes", "hourly", "daily", "monthly", "yearly"
    ] = "yearly"
    aggregation_method: Literal["sum", "mean", "max", "min"] = "sum"
    hydrological_year: bool = False
    hydrological_start_month: int = 10
    daily_start_hour: int = 0


class TemporalAggregateResponse(BaseModel):
    """Response de agregación temporal.

    Attributes:
        original_frequency: Frecuencia detectada de la serie original.
        target_frequency: Frecuencia objetivo solicitada.
        index: Lista de índices resultantes (años, meses, fechas u horas).
        values: Lista de valores agregados.
        aggregation_performed: Si se realizó agregación (False si ya era del mismo tipo).
        aggregation_bypass: True si la serie ya estaba de la frecuencia solicitada.
        aggregation_method: Método usado para agregar.
        hydrological_year: Si se usó año hidrológico.
        daily_start_hour: Hora de inicio del período diario usado.
        n_original: Cantidad de puntos originales.
        n_result: Cantidad de puntos resultantes.
        available_targets: Lista de frecuencias objetivo disponibles desde la original.
    """

    original_frequency: str
    target_frequency: str
    index: list[str | int]
    values: list[float]
    aggregation_performed: bool
    aggregation_bypass: bool
    aggregation_method: str
    hydrological_year: bool
    daily_start_hour: int
    n_original: int
    n_result: int
    available_targets: list[str]


class AvailableTargetsRequest(BaseModel):
    """Request para obtener frecuencias objetivo disponibles.

    Attributes:
        dates: Lista de fechas en formato ISO.
        values: Lista de valores.
    """

    dates: list[str]
    values: list[float]


class AvailableTargetsResponse(BaseModel):
    """Response con frecuencias objetivo disponibles.

    Attributes:
        source_frequency: Frecuencia detectada de la serie original.
        available_targets: Lista de frecuencias a las que se puede agregar.
        description: Descripción de la frecuencia detectada.
    """

    source_frequency: str
    available_targets: list[str]
    description: str


class DetectFrequencyRequest(BaseModel):
    """Request para detección de frecuencia.

    Attributes:
        dates: Lista de fechas en formato ISO.
        values: Lista de valores (para mantener alineación con fechas).
    """

    dates: list[str]
    values: list[float]


class DetectFrequencyResponse(BaseModel):
    """Response de detección de frecuencia.

    Attributes:
        frequency: Tipo de frecuencia detectada.
        frequency_description: Descripción legible.
    """

    frequency: str
    frequency_description: str


FREQUENCY_DESCRIPTIONS = {
    "5min": "Cada 5 minutos",
    "minutes": "Por minutos",
    "hourly": "Horaria",
    "daily": "Diaria",
    "monthly": "Mensual",
    "yearly": "Anual",
    "irregular": "Irregular",
}


@router.post(
    "/aggregate",
    response_model=TemporalAggregateResponse,
    summary="Agregar serie temporal",
    description="""
    Agrega una serie temporal a la frecuencia objetivo solicitada.

    Detecta automáticamente la frecuencia original y aplica la agregación
    apropiada. Solo permite agregación ascendente (menor a mayor frecuencia).

    Soporta:
    - Datos por minutos → horarios → diarios → mensuales → anuales
    - Datos horarios → diarios → mensuales → anuales
    - Datos diarios → mensuales → anuales
    - Datos mensuales → anuales
    - Período diario personalizado (ej: 09:00 a 09:00)
    - Año hidrológico configurable (default octubre)
    """,
    response_description="Serie agregada con metadatos de transformación",
)
async def aggregate_temporal(
    request: TemporalAggregateRequest,
) -> TemporalAggregateResponse:
    """Agrega serie temporal a la frecuencia objetivo.

    Args:
        request: Datos de la serie y configuración de agregación.

    Returns:
        TemporalAggregateResponse con la serie agregada.

    Raises:
        HTTPException: Si hay error en los datos o parámetros.
    """
    try:
        # Validar que hay datos
        if len(request.dates) == 0 or len(request.values) == 0:
            msg = "La serie está vacía"
            raise HTTPException(status_code=400, detail=msg)  # noqa: TRY301

        if len(request.dates) != len(request.values):
            msg = "La cantidad de fechas y valores debe coincidir"
            raise HTTPException(status_code=400, detail=msg)  # noqa: TRY301

        # Validar daily_start_hour
        if not 0 <= request.daily_start_hour <= 23:
            msg = "daily_start_hour debe estar entre 0 y 23"
            raise HTTPException(status_code=400, detail=msg)  # noqa: TRY301

        # Crear Serie de pandas con índice temporal
        try:
            dates = pd.to_datetime(request.dates, dayfirst=True)
        except ValueError as e:
            msg = f"Error en formato de fechas: {e!s}"
            raise HTTPException(status_code=400, detail=msg) from e

        series = pd.Series(request.values, index=dates)

        # Detectar frecuencia original para obtener targets disponibles
        source_freq = detect_frequency(series)
        available_targets = get_available_targets(source_freq)

        # Aplicar agregación
        result_series = auto_aggregate(
            series,
            target_frequency=request.target_frequency,
            aggregation_method=request.aggregation_method,
            hydrological_year=request.hydrological_year,
            hydrological_start_month=request.hydrological_start_month,
            daily_start_hour=request.daily_start_hour,
        )

        # Extraer metadatos
        aggregation_performed = getattr(result_series, "_aggregation_performed", False)
        aggregation_bypass = getattr(result_series, "_aggregation_bypass", False)
        original_frequency = getattr(result_series, "_original_frequency", "unknown")
        aggregation_method_used = getattr(
            result_series, "_aggregation_method", request.aggregation_method
        )
        target_frequency_used = getattr(
            result_series, "_target_frequency", request.target_frequency
        )
        daily_start_hour_used = getattr(
            result_series, "_daily_start_hour", request.daily_start_hour
        )

        # Convertir índice a lista (puede ser años, meses, fechas o horas)
        index_values = result_series.index.tolist()
        # Convertir a strings si son objetos complejos (Period, Timestamp)
        index_list = []
        for idx in index_values:
            if hasattr(idx, "strftime"):
                index_list.append(
                    idx.strftime("%Y-%m-%d %H:%M") if hasattr(idx, "hour") else str(idx)
                )
            else:
                index_list.append(str(idx))

        values = result_series.to_numpy().tolist()

        return TemporalAggregateResponse(
            original_frequency=original_frequency,
            target_frequency=target_frequency_used,
            index=index_list,
            values=values,
            aggregation_performed=aggregation_performed,
            aggregation_bypass=aggregation_bypass,
            aggregation_method=aggregation_method_used,
            hydrological_year=request.hydrological_year,
            daily_start_hour=daily_start_hour_used,
            n_original=len(request.dates),
            n_result=len(index_list),
            available_targets=available_targets,
        )

    except HTTPException:
        raise
    except ValueError as e:
        msg = f"Error en agregación: {e!s}"
        raise HTTPException(status_code=400, detail=msg) from e
    except Exception as e:
        msg = f"Error en agregación temporal: {e!s}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.post(
    "/detect-frequency",
    response_model=DetectFrequencyResponse,
    summary="Detectar frecuencia temporal",
    description="""
    Detecta la frecuencia temporal de una serie basándose en
    el intervalo entre observaciones.

    Detecta:
    - Minutos (5min, general)
    - Horaria
    - Diaria
    - Mensual
    - Anual
    - Irregular
    """,
    response_description="Tipo de frecuencia detectada",
)
async def detect_frequency_endpoint(
    request: DetectFrequencyRequest,
) -> DetectFrequencyResponse:
    """Detecta la frecuencia temporal de una serie.

    Args:
        request: Fechas y valores de la serie.

    Returns:
        DetectFrequencyResponse con la frecuencia detectada.

    Raises:
        HTTPException: Si hay error en los datos.
    """
    try:
        if len(request.dates) == 0:
            msg = "La serie está vacía"
            raise HTTPException(status_code=400, detail=msg)  # noqa: TRY301

        # Crear Serie de pandas
        try:
            dates = pd.to_datetime(request.dates, dayfirst=True)
        except ValueError as e:
            msg = f"Error en formato de fechas: {e!s}"
            raise HTTPException(status_code=400, detail=msg) from e

        series = pd.Series(request.values, index=dates)

        # Detectar frecuencia
        freq = detect_frequency(series)

        return DetectFrequencyResponse(
            frequency=freq.value,
            frequency_description=FREQUENCY_DESCRIPTIONS.get(freq.value, "Desconocida"),
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Error en detección de frecuencia: {e!s}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.post(
    "/available-targets",
    response_model=AvailableTargetsResponse,
    summary="Obtener frecuencias objetivo disponibles",
    description="""
    Detecta la frecuencia de la serie original y retorna las frecuencias
    a las que se puede agregar (agregación ascendente válida).

    Útil para poblar selectores de UI con opciones válidas.
    """,
    response_description="Frecuencias objetivo disponibles para agregación",
)
async def get_available_targets_endpoint(
    request: AvailableTargetsRequest,
) -> AvailableTargetsResponse:
    """Obtiene las frecuencias objetivo disponibles para agregación.

    Args:
        request: Fechas y valores de la serie.

    Returns:
        AvailableTargetsResponse con frecuencias disponibles.

    Raises:
        HTTPException: Si hay error en los datos.
    """
    try:
        if len(request.dates) == 0:
            msg = "La serie está vacía"
            raise HTTPException(status_code=400, detail=msg)  # noqa: TRY301

        # Crear Serie de pandas
        try:
            dates = pd.to_datetime(request.dates, dayfirst=True)
        except ValueError as e:
            msg = f"Error en formato de fechas: {e!s}"
            raise HTTPException(status_code=400, detail=msg) from e

        series = pd.Series(request.values, index=dates)

        # Detectar frecuencia y obtener targets disponibles
        freq = detect_frequency(series)
        available = get_available_targets(freq)

        return AvailableTargetsResponse(
            source_frequency=freq.value,
            available_targets=available,
            description=FREQUENCY_DESCRIPTIONS.get(freq.value, "Desconocida"),
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Error al obtener targets disponibles: {e!s}"
        raise HTTPException(status_code=500, detail=msg) from e
