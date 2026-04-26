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
)


router = APIRouter(prefix="/temporal", tags=["temporal"])


class TemporalAggregateRequest(BaseModel):
    """Request para agregación temporal.

    Attributes:
        dates: Lista de fechas en formato ISO (YYYY-MM-DD).
        values: Lista de valores numéricos correspondientes.
        target_frequency: Frecuencia objetivo (solo "yearly" soportado).
        aggregation_method: Método de agregación ("sum", "mean", "max", "min").
        hydrological_year: Si True, usa año hidrológico.
        hydrological_start_month: Mes de inicio del año hidrológico (1-12).
    """

    dates: list[str]
    values: list[float]
    target_frequency: Literal["yearly"] = "yearly"
    aggregation_method: Literal["sum", "mean", "max", "min"] = "sum"
    hydrological_year: bool = False
    hydrological_start_month: int = 10


class TemporalAggregateResponse(BaseModel):
    """Response de agregación temporal.

    Attributes:
        original_frequency: Frecuencia detectada de la serie original.
        years: Lista de años resultantes.
        values: Lista de valores agregados.
        aggregation_performed: Si se realizó agregación (False si ya era anual).
        aggregation_bypass: True si la serie ya estaba anualizada.
        aggregation_method: Método usado para agregar.
        hydrological_year: Si se usó año hidrológico.
        n_original: Cantidad de puntos originales.
        n_result: Cantidad de puntos resultantes.
    """

    original_frequency: str
    years: list[int]
    values: list[float]
    aggregation_performed: bool
    aggregation_bypass: bool
    aggregation_method: str
    hydrological_year: bool
    n_original: int
    n_result: int


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
    Agrega una serie temporal a resolución anual.

    Detecta automáticamente la frecuencia original y aplica la agregación
    apropiada. Si la serie ya está anualizada, la retorna sin modificaciones.

    Soporta:
    - Datos mensuales → totales/promedios/máximos anuales
    - Datos diarios → máximos/sumas anuales
    - Datos horarios/minutales → máximos diarios → máximos anuales
    - Año hidrológico configurable (default octubre)
    """,
    response_description="Serie agregada con metadatos de transformación",
)
async def aggregate_temporal(
    request: TemporalAggregateRequest,
) -> TemporalAggregateResponse:
    """Agrega serie temporal a resolución anual.

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

        # Crear Serie de pandas con índice temporal
        try:
            dates = pd.to_datetime(request.dates)
        except ValueError as e:
            msg = f"Error en formato de fechas: {e!s}"
            raise HTTPException(status_code=400, detail=msg) from e

        series = pd.Series(request.values, index=dates)

        # Aplicar agregación
        result_series = auto_aggregate(
            series,
            target_frequency=request.target_frequency,
            aggregation_method=request.aggregation_method,
            hydrological_year=request.hydrological_year,
            hydrological_start_month=request.hydrological_start_month,
        )

        # Extraer metadatos
        aggregation_performed = getattr(result_series, "_aggregation_performed", False)
        aggregation_bypass = getattr(result_series, "_aggregation_bypass", False)
        original_frequency = getattr(result_series, "_original_frequency", "unknown")
        aggregation_method_used = getattr(
            result_series, "_aggregation_method", request.aggregation_method
        )

        # Convertir índice a lista de años
        years = result_series.index.tolist()
        values = result_series.to_numpy().tolist()

        return TemporalAggregateResponse(
            original_frequency=original_frequency,
            years=years,
            values=values,
            aggregation_performed=aggregation_performed,
            aggregation_bypass=aggregation_bypass,
            aggregation_method=aggregation_method_used,
            hydrological_year=request.hydrological_year,
            n_original=len(request.dates),
            n_result=len(years),
        )

    except HTTPException:
        raise
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
            dates = pd.to_datetime(request.dates)
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
