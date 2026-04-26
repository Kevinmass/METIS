"""Módulo de agregación temporal para series hidrológicas.

Detecta automáticamente la frecuencia temporal de series y las agrega
a resoluciones apropiadas para análisis estadístico. Si una serie ya
está anualizada, la retorna sin modificaciones.
"""

from enum import Enum
from typing import Literal

import numpy as np
import pandas as pd


class FrequencyType(Enum):
    """Tipos de frecuencia temporal soportados."""

    MINUTES_5 = "5min"
    MINUTES = "minutes"
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    IRREGULAR = "irregular"


class AggregationMethod(Enum):
    """Métodos de agregación disponibles."""

    SUM = "sum"
    MEAN = "mean"
    MAX = "max"
    MIN = "min"


def _is_yearly_frequency(freq_code: str | None) -> bool:
    """Verifica si un código de frecuencia pandas representa datos anuales.

    Args:
        freq_code: Código de frecuencia de pandas (ej: 'Y', 'A-DEC', etc.)

    Returns:
        True si es una frecuencia anual.
    """
    if freq_code is None:
        return False
    freq_upper = freq_code.upper()
    return freq_upper.startswith(("Y", "A"))


def _check_interval_approximately_yearly(
    series: pd.Series, tolerance_days: float = 30.0
) -> bool:
    """Verifica si el intervalo entre observaciones es aproximadamente anual.

    Args:
        series: Serie con DatetimeIndex.
        tolerance_days: Tolerancia en días para considerar anual (default 30).

    Returns:
        True si el intervalo medio está entre 335 y 395 días.
    """
    if len(series) < 2:  # noqa: PLR2004
        return False

    index = series.index
    if not isinstance(index, pd.DatetimeIndex):
        return False

    # Calcular diferencias entre timestamps consecutivos
    diffs = index[1:] - index[:-1]
    mean_days = diffs.mean().total_seconds() / (24 * 3600)

    # Intervalo anual aproximado: 365 ± tolerance_days
    return (365 - tolerance_days) <= mean_days <= (365 + tolerance_days)


def _detect_frequency_from_two_points(series: pd.Series) -> FrequencyType:
    """Detecta frecuencia aproximada para series con solo 2 puntos.

    Args:
        series: Serie con exactamente 2 puntos y DatetimeIndex.

    Returns:
        FrequencyType estimado basado en el intervalo único.
    """
    if len(series) != 2:  # noqa: PLR2004
        return FrequencyType.IRREGULAR

    idx = series.index
    diff_seconds = (idx[1] - idx[0]).total_seconds()
    diff_days = diff_seconds / (24 * 3600)

    # Verificar si es aproximadamente anual
    if 335 <= diff_days <= 395:  # noqa: PLR2004
        return FrequencyType.YEARLY
    if 25 <= diff_days <= 35:  # Mensual aproximado  # noqa: PLR2004
        return FrequencyType.MONTHLY
    if 0.9 <= diff_days <= 1.1:  # Diario  # noqa: PLR2004
        return FrequencyType.DAILY
    if diff_seconds < 3600:  # Menos de 1 hora  # noqa: PLR2004
        return FrequencyType.HOURLY

    return FrequencyType.IRREGULAR


def detect_frequency(  # noqa: C901, PLR0911, PLR0912
    series: pd.Series,
) -> FrequencyType:
    """Detecta la frecuencia temporal de una serie.

    Usa pd.infer_freq() como primera aproximación, con fallback a análisis
    de diferencias entre índices. Detecta series anuales, mensuales, diarias,
    horarias y por minutos.

    Args:
        series: Serie de Pandas con DatetimeIndex.

    Returns:
        FrequencyType detectado.

    Example:
        >>> dates = pd.date_range("2020-01-01", periods=24, freq="h")
        >>> series = pd.Series(range(24), index=dates)
        >>> detect_frequency(series)
        <FrequencyType.HOURLY: 'hourly'>
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        return FrequencyType.IRREGULAR

    # Edge case: series vacía o con muy pocos puntos
    if len(series) < 3:  # noqa: PLR2004
        # Intentar detectar anual por intervalo entre los puntos disponibles
        if len(series) == 2:  # noqa: PLR2004
            return _detect_frequency_from_two_points(series)
        return FrequencyType.IRREGULAR

    # Intentar inferir frecuencia con pandas
    try:
        inferred_freq = pd.infer_freq(series.index)
    except ValueError:
        # Fall back a análisis manual si pandas falla
        inferred_freq = None

    if inferred_freq is not None:
        freq_upper = inferred_freq.upper()

        # Detectar series anuales primero (bypass)
        if _is_yearly_frequency(inferred_freq):
            return FrequencyType.YEARLY

        # Detectar otras frecuencias
        if "MIN" in freq_upper or "T" in freq_upper:
            # Minutos - diferenciar entre 5min y otros
            if "5" in freq_upper or freq_upper in ("5MIN", "5T"):
                return FrequencyType.MINUTES_5
            return FrequencyType.MINUTES
        if "H" in freq_upper or "HOURLY" in freq_upper:
            return FrequencyType.HOURLY
        if "D" in freq_upper or "DAY" in freq_upper:
            return FrequencyType.DAILY
        if "M" in freq_upper or "MONTH" in freq_upper or "BM" in freq_upper:
            return FrequencyType.MONTHLY
        if "Y" in freq_upper or "A" in freq_upper:
            return FrequencyType.YEARLY

    # Fallback: análisis de intervalos medios con desviación estándar
    if len(series) >= 3:  # noqa: PLR2004
        diffs = series.index[1:] - series.index[:-1]
        mean_seconds = diffs.mean().total_seconds()
        std_seconds = diffs.std().total_seconds() if len(diffs) > 1 else 0
        mean_days = mean_seconds / (24 * 3600)

        # Verificar consistencia de intervalos (cv < 0.5 para regular)
        cv = std_seconds / mean_seconds if mean_seconds > 0 else float("inf")
        if cv > 0.5:  # noqa: PLR2004
            return FrequencyType.IRREGULAR

        # Verificar si es anual primero
        if _check_interval_approximately_yearly(series):
            return FrequencyType.YEARLY

        # Clasificar por rangos
        if mean_seconds < 360:  # < 6 minutos  # noqa: PLR2004
            return FrequencyType.MINUTES_5
        if mean_seconds < 7200:  # < 2 horas  # noqa: PLR2004
            return FrequencyType.MINUTES
        if mean_seconds < 86400:  # < 1 día  # noqa: PLR2004
            return FrequencyType.HOURLY
        if mean_days < 30:  # < 1 mes aprox  # noqa: PLR2004
            return FrequencyType.DAILY
        if mean_days < 100:  # < ~3 meses (más estricto)  # noqa: PLR2004
            return FrequencyType.MONTHLY
        if mean_days < 366:  # < 1 año  # noqa: PLR2004
            return FrequencyType.MONTHLY  # Could be quarterly or bi-monthly

    return FrequencyType.IRREGULAR


def _get_year_from_hydrological(
    dates: pd.DatetimeIndex, start_month: int = 10
) -> pd.Series:
    """Calcula el año hidrológico para cada fecha.

    El año hidrológico se identifica por el año en que TERMINA.
    Ejemplo: año hidrológico 2021 va de start_month 2020 a start_month-1 2021.

    Args:
        dates: Índice de fechas.
        start_month: Mes de inicio del año hidrológico (default 10 = octubre).

    Returns:
        Serie con el año hidrológico de cada fecha.
    """
    year = dates.year
    month = dates.month
    # Meses desde start_month hasta diciembre: año + 1 (año hidrológico que comienza)
    # Meses desde enero hasta start_month-1: año actual (año hidrológico en curso)
    return pd.Series(np.where(month >= start_month, year + 1, year), index=dates)


def aggregate_monthly(
    series: pd.Series,
    method: Literal["sum", "mean", "max", "min"] = "sum",
    hydrological_year: bool = False,  # noqa: FBT001, FBT002
    hydrological_start_month: int = 10,
) -> pd.Series:
    """Agrega serie mensual a anual.

    Args:
        series: Serie con DatetimeIndex mensual.
        method: Método de agregación ("sum", "mean", "max", "min").
        hydrological_year: Si True, usa año hidrológico (oct-sep por default).
        hydrological_start_month: Mes de inicio del año hidrológico.

    Returns:
        Serie anual agregada.
    """
    if hydrological_year:
        # Crear índice de año hidrológico
        hydro_year = _get_year_from_hydrological(series.index, hydrological_start_month)
        # Agrupar por año hidrológico
        grouped = series.groupby(hydro_year.values)
        result = grouped.agg(method)
        result.index = pd.PeriodIndex(result.index, freq="Y")
    else:
        result = series.resample("YE").agg(method)

    result.index = result.index.year
    result.index.name = "year"
    return result


def aggregate_daily(
    series: pd.Series,
    target: Literal["annual_max", "annual_sum", "monthly_mean"] = "annual_max",
) -> pd.Series:
    """Agrega serie diaria.

    Args:
        series: Serie con DatetimeIndex diario.
        target: Tipo de agregación deseado:
            - "annual_max": Máximo anual diario
            - "annual_sum": Suma anual
            - "monthly_mean": Media mensual

    Returns:
        Serie agregada según el target especificado.
    """
    if target == "annual_max":
        result = series.resample("YE").max()
        result.index = result.index.year
        result.index.name = "year"
        return result
    if target == "annual_sum":
        result = series.resample("YE").sum()
        result.index = result.index.year
        result.index.name = "year"
        return result
    if target == "monthly_mean":
        result = series.resample("ME").mean()
        result.index = result.index.to_period("M")
        result.index.name = "month"
        return result

    msg = f"Target de agregación no soportado: {target}"
    raise ValueError(msg)


def aggregate_subdaily(
    series: pd.Series,
    target: Literal[
        "daily_max", "daily_sum", "monthly_sum", "annual_max", "annual_sum"
    ] = "annual_max",
) -> pd.Series:
    """Agrega serie horaria o por minutos.

    Args:
        series: Serie con DatetimeIndex horario o por minutos.
        target: Tipo de agregación deseado:
            - "daily_max": Máximo diario
            - "daily_sum": Acumulado diario
            - "monthly_sum": Acumulado mensual
            - "annual_max": Máximo anual
            - "annual_sum": Suma anual

    Returns:
        Serie agregada según el target especificado.
    """
    if target == "daily_max":
        result = series.resample("D").max()
        result.index.name = "date"
        return result
    if target == "daily_sum":
        result = series.resample("D").sum()
        result.index.name = "date"
        return result
    if target == "monthly_sum":
        result = series.resample("ME").sum()
        result.index = result.index.to_period("M")
        result.index.name = "month"
        return result
    if target == "annual_max":
        # Máximo anual: primero diario, luego anual
        daily_max = series.resample("D").max()
        result = daily_max.resample("YE").max()
        result.index = result.index.year
        result.index.name = "year"
        return result
    if target == "annual_sum":
        result = series.resample("YE").sum()
        result.index = result.index.year
        result.index.name = "year"
        return result

    msg = f"Target de agregación no soportado: {target}"
    raise ValueError(msg)


def auto_aggregate(  # noqa: C901
    series: pd.Series,
    target_frequency: Literal["yearly"] = "yearly",
    aggregation_method: Literal["sum", "mean", "max", "min"] = "sum",
    hydrological_year: bool = False,  # noqa: FBT001, FBT002
    hydrological_start_month: int = 10,
) -> pd.Series:
    """Agrega automáticamente una serie a la frecuencia objetivo.

    Detecta la frecuencia original y aplica la agregación apropiada.
    **Si la serie ya es anual (YEARLY), la retorna sin modificaciones.**

    Args:
        series: Serie con DatetimeIndex. Debe tener índice temporal válido.
        target_frequency: Frecuencia objetivo (solo "yearly" soportado actualmente).
        aggregation_method: Método de agregación para series mensuales.
        hydrological_year: Si True, usa año hidrológico para series mensuales.
        hydrological_start_month: Mes de inicio del año hidrológico (default 10).

    Returns:
        Serie agregada al target. Si la serie ya era anual, retorna
        la original con atributo `._aggregation_bypass = True`.

    Raises:
        ValueError: Si target_frequency no es "yearly" o si la serie no tiene
            DatetimeIndex.

    Example:
        >>> # Serie mensual
        >>> dates = pd.date_range("2020-01", periods=24, freq="ME")
        >>> series = pd.Series(range(24), index=dates)
        >>> annual = auto_aggregate(series)
        >>> len(annual)
        2

        >>> # Serie ya anual - retorna sin modificar
        >>> dates = pd.date_range("2020", periods=3, freq="YS")
        >>> series = pd.Series([100, 200, 150], index=dates)
        >>> result = auto_aggregate(series)
        >>> result is series  # Misma referencia
        True
    """
    if target_frequency != "yearly":
        msg = f"Solo target_frequency='yearly' está soportado, got {target_frequency}"
        raise ValueError(msg)

    if not isinstance(series.index, pd.DatetimeIndex):
        msg = "La serie debe tener un DatetimeIndex válido"
        raise TypeError(msg)

    # Manejar serie vacía
    if len(series) == 0:
        result = series.copy()
        result._aggregation_performed = True  # noqa: SLF001
        result._original_frequency = "empty"  # noqa: SLF001
        return result

    # Detectar frecuencia
    freq = detect_frequency(series)

    # BYPASS: Si ya es anual, retornar sin modificar
    if freq == FrequencyType.YEARLY:
        result = series.copy()
        result._aggregation_bypass = True  # noqa: SLF001
        result._original_frequency = freq.value  # noqa: SLF001
        return result

    # Agregar según frecuencia detectada
    if freq == FrequencyType.MONTHLY:
        result = aggregate_monthly(
            series,
            method=aggregation_method,
            hydrological_year=hydrological_year,
            hydrological_start_month=hydrological_start_month,
        )
    elif freq == FrequencyType.DAILY:
        # Para diaria, default es máximo anual (común en hidrología)
        if aggregation_method == "max":
            result = aggregate_daily(series, target="annual_max")
        elif aggregation_method == "sum":
            result = aggregate_daily(series, target="annual_sum")
        else:
            result = aggregate_daily(series, target="annual_max")
    elif freq in (FrequencyType.HOURLY, FrequencyType.MINUTES, FrequencyType.MINUTES_5):
        # Para subdiaria, ir a máximo anual (vía diario)
        result = aggregate_subdaily(series, target="annual_max")
    else:
        # Frecuencia irregular: intentar resample a anual con sum
        try:
            result = series.resample("YE").agg(aggregation_method)
            result.index = result.index.year
            result.index.name = "year"
        except Exception as e:
            msg = f"No se pudo agregar serie de frecuencia {freq.value}: {e!s}"
            raise ValueError(msg) from e

    # Agregar metadatos de transformación
    result._aggregation_performed = True  # noqa: SLF001
    result._original_frequency = freq.value  # noqa: SLF001
    result._aggregation_method = aggregation_method  # noqa: SLF001

    return result
