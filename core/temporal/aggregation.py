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


def detect_frequency(  # noqa: PLR0912
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


def _get_day_period_from_hour(
    dates: pd.DatetimeIndex, start_hour: int = 0
) -> pd.Series:
    """Calcula el período diario personalizado para cada timestamp.

    Similar al año hidrológico pero para períodos de 24 horas.
    Ejemplo: período 2020-01-01 va de 09:00 del día anterior a 09:00 del día actual.

    Args:
        dates: Índice de timestamps.
        start_hour: Hora de inicio del período diario (default 0 = medianoche).

    Returns:
        Serie con la fecha del período diario de cada timestamp.
    """
    # Para timestamps antes de start_hour, pertenecen al día anterior
    # Para timestamps desde start_hour en adelante, pertenecen al día actual
    day = dates.day
    month = dates.month
    year = dates.year
    hour = dates.hour

    # Crear fechas base
    base_dates = pd.to_datetime(
        pd.DataFrame({"year": year, "month": month, "day": day})
    )

    # Ajustar: si hora < start_hour, restar un día
    adjustment = pd.Series(
        np.where(hour < start_hour, pd.Timedelta(days=-1), pd.Timedelta(days=0)),
        index=dates,
    )
    result = base_dates + adjustment

    return pd.Series(result, index=dates)


def _get_frequency_rank(freq: FrequencyType) -> int:
    """Retorna el ranking de frecuencia para comparaciones (menor = más frecuente).

    Args:
        freq: Tipo de frecuencia.

    Returns:
        Número indicando el nivel de agregación (1=5min, 7=yearly).
    """
    ranking = {
        FrequencyType.MINUTES_5: 1,
        FrequencyType.MINUTES: 2,
        FrequencyType.HOURLY: 3,
        FrequencyType.DAILY: 4,
        FrequencyType.MONTHLY: 5,
        FrequencyType.YEARLY: 6,
        FrequencyType.IRREGULAR: 99,
    }
    return ranking.get(freq, 99)


def can_aggregate_to(source_freq: FrequencyType, target_freq: str) -> bool:
    """Verifica si se puede agregar desde una frecuencia a otra.

    Solo permite agregación ascendente (de menor a mayor frecuencia).
    Ejemplo: minutos -> horas SI, horas -> minutos NO.
    Para frecuencias IRREGULAR, usa get_available_targets().

    Args:
        source_freq: Frecuencia de la serie original.
        target_freq: Frecuencia objetivo como string.

    Returns:
        True si la agregación es válida.
    """
    # Para IRREGULAR, usar get_available_targets en lugar de rank
    if source_freq == FrequencyType.IRREGULAR:
        return target_freq in get_available_targets(source_freq)

    target_enum = None
    try:
        target_enum = FrequencyType(target_freq)
    except ValueError:
        # Soportar aliases comunes
        aliases = {
            "yearly": FrequencyType.YEARLY,
            "annual": FrequencyType.YEARLY,
            "monthly": FrequencyType.MONTHLY,
            "daily": FrequencyType.DAILY,
            "hourly": FrequencyType.HOURLY,
            "5min": FrequencyType.MINUTES_5,
            "minutes": FrequencyType.MINUTES,
        }
        target_enum = aliases.get(target_freq.lower())

    if target_enum is None:
        return False

    source_rank = _get_frequency_rank(source_freq)
    target_rank = _get_frequency_rank(target_enum)

    # Solo permitir agregación ascendente (source más frecuente que target)
    return source_rank < target_rank


def aggregate_monthly(
    series: pd.Series,
    method: Literal["sum", "mean", "max", "min"] = "sum",
    hydrological_year: bool = False,
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
        "hourly_max",
        "hourly_sum",
        "hourly_mean",
        "daily_max",
        "daily_sum",
        "daily_mean",
        "monthly_max",
        "monthly_sum",
        "monthly_mean",
        "annual_max",
        "annual_sum",
        "annual_mean",
    ] = "annual_max",
    daily_start_hour: int = 0,
    hydrological_year: bool = False,
    hydrological_start_month: int = 10,
) -> pd.Series:
    """Agrega serie horaria o por minutos con soporte para período diario personalizado.

    Args:
        series: Serie con DatetimeIndex horario o por minutos.
        target: Tipo de agregación deseado:
            - "hourly_*": Agregación a nivel horario
            - "daily_*": Agregación a nivel diario con período 24hs personalizado
            - "monthly_*": Agregación mensual
            - "annual_*": Agregación anual
        daily_start_hour: Hora de inicio del período diario (0-23, default 0 = medianoche).
        hydrological_year: Si True, usa año hidrológico para agregación anual desde mensual.
        hydrological_start_month: Mes de inicio del año hidrológico.

    Returns:
        Serie agregada según el target especificado.
    """
    # Agregación horaria
    if target == "hourly_max":
        result = series.resample("h").max()
        result.index.name = "hour"
        return result
    if target == "hourly_sum":
        result = series.resample("h").sum()
        result.index.name = "hour"
        return result
    if target == "hourly_mean":
        result = series.resample("h").mean()
        result.index.name = "hour"
        return result

    # Agregación diaria con período personalizado
    if target in ("daily_max", "daily_sum", "daily_mean"):
        method = target.split("_")[1]  # max, sum, mean
        if daily_start_hour == 0:
            # Período estándar 00:00-00:00
            result = series.resample("D").agg(method)
        else:
            # Período personalizado: usar daily_start_hour como offset
            # Crear índice de período diario
            day_period = _get_day_period_from_hour(series.index, daily_start_hour)
            # Agrupar por período diario
            grouped = series.groupby(day_period.values)
            result = grouped.agg(method)
            # Convertir índice de strings a datetime
            result.index = pd.to_datetime(result.index)

        result.index.name = "date"
        return result

    # Agregación mensual
    if target == "monthly_max":
        result = series.resample("ME").max()
        result.index = result.index.to_period("M")
        result.index.name = "month"
        return result
    if target == "monthly_sum":
        result = series.resample("ME").sum()
        result.index = result.index.to_period("M")
        result.index.name = "month"
        return result
    if target == "monthly_mean":
        result = series.resample("ME").mean()
        result.index = result.index.to_period("M")
        result.index.name = "month"
        return result

    # Agregación anual
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
    if target == "annual_mean":
        result = series.resample("YE").mean()
        result.index = result.index.year
        result.index.name = "year"
        return result

    msg = f"Target de agregación no soportado: {target}"
    raise ValueError(msg)


def get_available_targets(source_freq: FrequencyType) -> list[str]:
    """Retorna las frecuencias objetivo disponibles para agregación.

    Args:
        source_freq: Frecuencia de la serie original.

    Returns:
        Lista de frecuencias objetivo válidas para agregación ascendente.
    """
    targets_by_source = {
        FrequencyType.MINUTES_5: ["hourly", "daily", "monthly", "yearly"],
        FrequencyType.MINUTES: ["hourly", "daily", "monthly", "yearly"],
        FrequencyType.HOURLY: ["daily", "monthly", "yearly"],
        FrequencyType.DAILY: ["monthly", "yearly"],
        FrequencyType.MONTHLY: ["yearly"],
        FrequencyType.YEARLY: [],
        FrequencyType.IRREGULAR: ["yearly"],
    }
    return targets_by_source.get(source_freq, [])


def auto_aggregate(  # noqa: PLR0912, PLR0913
    series: pd.Series,
    target_frequency: Literal[
        "5min", "minutes", "hourly", "daily", "monthly", "yearly"
    ] = "yearly",
    aggregation_method: Literal["sum", "mean", "max", "min"] = "sum",
    hydrological_year: bool = False,
    hydrological_start_month: int = 10,
    daily_start_hour: int = 0,
) -> pd.Series:
    """Agrega automáticamente una serie a la frecuencia objetivo.

    Detecta la frecuencia original y aplica la agregación apropiada.
    Soporta agregación ascendente flexible (menor a mayor frecuencia).
    **Si la serie ya es de la frecuencia objetivo, la retorna sin modificaciones.**

    Args:
        series: Serie con DatetimeIndex. Debe tener índice temporal válido.
        target_frequency: Frecuencia objetivo.
            Opciones: "5min", "minutes", "hourly", "daily", "monthly", "yearly".
        aggregation_method: Método de agregación ("sum", "mean", "max", "min").
        hydrological_year: Si True, usa año hidrológico para agregación anual.
        hydrological_start_month: Mes de inicio del año hidrológico (default 10).
        daily_start_hour: Hora de inicio del período diario (0-23, default 0).

    Returns:
        Serie agregada al target con metadatos de transformación.

    Raises:
        ValueError: Si la agregación solicitada no es válida (ascendente).
        TypeError: Si la serie no tiene DatetimeIndex.

    Example:
        >>> # Serie mensual a anual
        >>> dates = pd.date_range("2020-01", periods=24, freq="ME")
        >>> series = pd.Series(range(24), index=dates)
        >>> annual = auto_aggregate(series, target_frequency="yearly")
        >>> len(annual)
        2

        >>> # Serie por minutos a diaria con período 09:00-09:00
        >>> dates = pd.date_range("2020-01-01", periods=1440, freq="min")
        >>> series = pd.Series(range(1440), index=dates)
        >>> daily = auto_aggregate(series, target_frequency="daily", daily_start_hour=9)
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        msg = "La serie debe tener un DatetimeIndex válido"
        raise TypeError(msg)

    # Manejar serie vacía
    if len(series) == 0:
        result = series.copy()
        result._aggregation_performed = True  # noqa: SLF001
        result._original_frequency = "empty"  # noqa: SLF001
        return result

    # Detectar frecuencia original
    source_freq = detect_frequency(series)

    # BYPASS: Si ya es de la frecuencia objetivo, retornar sin modificar
    target_enum = None
    try:
        target_enum = FrequencyType(target_frequency)
    except ValueError:
        aliases = {
            "yearly": FrequencyType.YEARLY,
            "annual": FrequencyType.YEARLY,
            "monthly": FrequencyType.MONTHLY,
            "daily": FrequencyType.DAILY,
            "hourly": FrequencyType.HOURLY,
            "5min": FrequencyType.MINUTES_5,
            "minutes": FrequencyType.MINUTES,
        }
        target_enum = aliases.get(target_frequency.lower())

    if target_enum == source_freq:
        result = series.copy()
        result._aggregation_bypass = True  # noqa: SLF001
        result._original_frequency = source_freq.value  # noqa: SLF001
        return result

    # Verificar que la agregación es ascendente (menor a mayor frecuencia)
    if not can_aggregate_to(source_freq, target_frequency):
        msg = f"No se puede agregar desde {source_freq.value} a {target_frequency}. "
        msg += f"Targets válidos: {get_available_targets(source_freq)}"
        raise ValueError(msg)

    # Construir target string para aggregate_subdaily
    target_str = f"{target_frequency}_{aggregation_method}"
    if target_frequency in ("yearly", "monthly", "daily", "hourly"):
        # Mapear a targets soportados por aggregate_subdaily
        target_mapping = {
            "yearly": "annual",
            "monthly": "monthly",
            "daily": "daily",
            "hourly": "hourly",
        }
        prefix = target_mapping.get(target_frequency, target_frequency)
        target_str = f"{prefix}_{aggregation_method}"

    # Agregar según frecuencia detectada
    if source_freq == FrequencyType.MONTHLY and target_frequency == "yearly":
        result = aggregate_monthly(
            series,
            method=aggregation_method,
            hydrological_year=hydrological_year,
            hydrological_start_month=hydrological_start_month,
        )
    elif source_freq == FrequencyType.DAILY:
        if target_frequency == "yearly":
            result = aggregate_daily(
                series,
                target=f"annual_{aggregation_method}"
                if aggregation_method != "mean"
                else "annual_max",
            )
        elif target_frequency == "monthly":
            result = series.resample("ME").agg(aggregation_method)
            result.index = result.index.to_period("M")
            result.index.name = "month"
        else:
            # Fallback a aggregate_subdaily
            result = aggregate_subdaily(
                series,
                target=target_str
                if target_frequency != "daily"
                else f"daily_{aggregation_method}",
                daily_start_hour=daily_start_hour,
                hydrological_year=hydrological_year,
                hydrological_start_month=hydrological_start_month,
            )
    elif source_freq in (
        FrequencyType.HOURLY,
        FrequencyType.MINUTES,
        FrequencyType.MINUTES_5,
    ):
        result = aggregate_subdaily(
            series,
            target=target_str,
            daily_start_hour=daily_start_hour,
            hydrological_year=hydrological_year,
            hydrological_start_month=hydrological_start_month,
        )
    else:
        # Frecuencia irregular: intentar resample directo
        try:
            freq_code = {
                "yearly": "YE",
                "monthly": "ME",
                "daily": "D",
                "hourly": "h",
            }.get(target_frequency, "YE")
            result = series.resample(freq_code).agg(aggregation_method)
            if target_frequency == "yearly":
                result.index = result.index.year
                result.index.name = "year"
            elif target_frequency == "monthly":
                result.index = result.index.to_period("M")
                result.index.name = "month"
            else:
                result.index.name = target_frequency
        except Exception as e:
            msg = f"No se pudo agregar serie de frecuencia {source_freq.value} a {target_frequency}: {e!s}"
            raise ValueError(msg) from e

    # Agregar metadatos de transformación
    result._aggregation_performed = True  # noqa: SLF001
    result._original_frequency = source_freq.value  # noqa: SLF001
    result._target_frequency = target_frequency  # noqa: SLF001
    result._aggregation_method = aggregation_method  # noqa: SLF001
    result._daily_start_hour = daily_start_hour  # noqa: SLF001

    return result
