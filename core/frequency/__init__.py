"""Módulo de análisis de frecuencia hidrológica.

Este módulo proporciona funcionalidad para:
    - Ajuste de distribuciones de probabilidad a series hidrológicas
    - Estimación de parámetros por diferentes métodos (MOM, MLE, MEnt)
    - Evaluación de bondad de ajuste (Chi-Square, KS, EEA)
    - Cálculo de eventos de diseño para diferentes períodos de retorno

Componentes principales:
    - distributions: Motor de 13 distribuciones de probabilidad
    - fitting: Métodos de estimación y pruebas de bondad de ajuste
    - design_events: Cálculo de eventos de diseño

Ejemplo de uso:
    >>> import pandas as pd
    >>> from core.frequency import fit_all_distributions, calculate_design_event
    >>>
    >>> series = pd.Series([100.0, 120.0, 95.0, 110.0, 105.0])
    >>> results = fit_all_distributions(series, estimation_method="MOM")
    >>>
    >>> best = results[0]  # La mejor distribución
    >>> event = calculate_design_event(best, return_period=100.0)
    >>> print(f"Evento centenario: {event.design_value}")
"""

from core.frequency.design_events import (
    calculate_design_event,
    calculate_exceedance_probability,
    calculate_multiple_design_events,
    calculate_return_period_from_value,
    get_standard_return_periods,
)
from core.frequency.distributions import (
    DISTRIBUTIONS,
    get_distribution,
    list_distributions,
)
from core.frequency.fitting import (
    calculate_goodness_of_fit,
    fit_all_distributions,
    fit_by_mentropy,
    fit_by_mle,
    fit_by_mom,
    fit_distribution,
    get_best_distribution,
)


__all__ = [
    "DISTRIBUTIONS",
    "calculate_design_event",
    "calculate_exceedance_probability",
    "calculate_goodness_of_fit",
    "calculate_multiple_design_events",
    "calculate_return_period_from_value",
    "fit_all_distributions",
    "fit_by_mentropy",
    "fit_by_mle",
    "fit_by_mom",
    "fit_distribution",
    "get_best_distribution",
    "get_distribution",
    "get_standard_return_periods",
    "list_distributions",
]
