"""Cálculo de eventos de diseño para análisis de frecuencia hidrológica.

Este módulo implementa el cálculo de eventos de diseño a partir de
distribuciones ajustadas, permitiendo estimar caudales extremos para
diferentes períodos de retorno.

El evento de diseño es el valor de caudal que tiene una probabilidad
de excedencia dada (1/T) donde T es el período de retorno.
"""


from core.frequency.distributions import get_distribution
from core.shared.types import DesignEvent, FitResult


def calculate_design_event(
    fit_result: FitResult,
    return_period: float,
) -> DesignEvent:
    """Calcula el evento de diseño para un período de retorno dado.

    El evento de diseño es el cuantil correspondiente a la probabilidad
    anual de no excedencia P = 1 - 1/T, donde T es el período de retorno.

    Args:
        fit_result: Resultado del ajuste de distribución con parámetros.
        return_period: Período de retorno T en años.
            Valores comunes: 2, 5, 10, 25, 50, 100, 200, 500.

    Returns:
        Objeto DesignEvent con el valor calculado y metadatos.

    Raises:
        ValueError: Si el período de retorno es inválido.
    """
    if return_period <= 0:
        msg = f"Return period must be positive, got {return_period}"
        raise ValueError(msg)

    # Calcular probabilidad anual de no excedencia
    # P(X <= x) = 1 - 1/T
    annual_probability = 1.0 - 1.0 / return_period

    # Obtener distribución y calcular cuantil (PPF)
    dist = get_distribution(fit_result.distribution_name)
    design_value = dist.ppf(annual_probability, fit_result.parameters)

    return DesignEvent(
        return_period=return_period,
        annual_probability=annual_probability,
        design_value=design_value,
        distribution_name=fit_result.distribution_name,
        parameters=fit_result.parameters,
    )


def calculate_multiple_design_events(
    fit_result: FitResult,
    return_periods: list[float],
) -> list[DesignEvent]:
    """Calcula múltiples eventos de diseño para diferentes períodos de retorno.

    Args:
        fit_result: Resultado del ajuste de distribución con parámetros.
        return_periods: Lista de períodos de retorno en años.
            Ejemplo: [2, 5, 10, 25, 50, 100, 200, 500]

    Returns:
        Lista de DesignEvent ordenada por período de retorno ascendente.
    """
    events = []
    for return_period in return_periods:
        try:
            event = calculate_design_event(fit_result, return_period)
            events.append(event)
        except ValueError:  # noqa: PERF203
            # Saltar períodos de retorno inválidos
            continue

    # Ordenar por período de retorno
    events.sort(key=lambda e: e.return_period)

    return events


def get_standard_return_periods() -> list[float]:
    """Retorna los períodos de retorno estándar en hidrología.

    Returns:
        Lista de períodos de retorno comunes en años.
    """
    return [2, 5, 10, 25, 50, 100, 200, 500]


def calculate_exceedance_probability(
    fit_result: FitResult,
    value: float,
) -> float:
    """Calcula la probabilidad de excedencia para un valor dado.

    P(X > x) = 1 - CDF(x)

    Args:
        fit_result: Resultado del ajuste de distribución con parámetros.
        value: Valor de caudal para el cual calcular la probabilidad.

    Returns:
        Probabilidad de excedencia anual (entre 0 y 1).
    """
    dist = get_distribution(fit_result.distribution_name)
    cdf_value = dist.cdf(value, fit_result.parameters)
    return 1.0 - cdf_value


def calculate_return_period_from_value(
    fit_result: FitResult,
    value: float,
) -> float:
    """Calcula el período de retorno correspondiente a un valor dado.

    T = 1 / P(X > x)

    Args:
        fit_result: Resultado del ajuste de distribución con parámetros.
        value: Valor de caudal.

    Returns:
        Período de retorno en años.

    Raises:
        ValueError: Si la probabilidad de excedencia es 0.
    """
    exceedance_prob = calculate_exceedance_probability(fit_result, value)

    if exceedance_prob <= 0:
        msg = (
            f"Value {value} has zero or negative exceedance probability, "
            "cannot compute return period"
        )
        raise ValueError(msg)

    return 1.0 / exceedance_prob
