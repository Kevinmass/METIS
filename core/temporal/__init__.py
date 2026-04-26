"""Módulo de agregación temporal para series hidrológicas.

Proporciona funciones para detectar la frecuencia temporal de series
de datos y agregarlas a resoluciones apropiadas para análisis estadístico.

El módulo detecta automáticamente si una serie ya está anualizada
y la retorna sin modificaciones en ese caso.

Exports principales:
    - auto_aggregate: Función principal de agregación
    - detect_frequency: Detecta frecuencia temporal
    - FrequencyType: Enum con tipos de frecuencia soportados
    - AggregationMethod: Enum con métodos de agregación

Example:
    >>> from core.temporal import auto_aggregate, detect_frequency
    >>> import pandas as pd
    >>> # Serie diaria
    >>> dates = pd.date_range("2020-01-01", periods=365, freq="D")
    >>> series = pd.Series(range(365), index=dates)
    >>> freq = detect_frequency(series)
    >>> freq
    <FrequencyType.DAILY: 'daily'>
    >>> # Agregar a anual
    >>> annual = auto_aggregate(series, target_frequency="yearly")
"""

from core.temporal.aggregation import (
    AggregationMethod,
    FrequencyType,
    auto_aggregate,
    detect_frequency,
)


__all__ = [
    "AggregationMethod",
    "FrequencyType",
    "auto_aggregate",
    "detect_frequency",
]
