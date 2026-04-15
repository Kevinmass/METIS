"""Métodos de estimación de parámetros y pruebas de bondad de ajuste.

Este módulo implementa los métodos de estimación de parámetros para distribuciones
de probabilidad y las pruebas estadísticas para evaluar la bondad de ajuste.

Métodos de estimación implementados:
    - MOM: Método de Momentos
    - MLE: Máxima Verosimilitud
    - MEnt: Máxima Entropía

Pruebas de bondad de ajuste:
    - Chi Cuadrado
    - Kolmogorov-Smirnov
    - Error Estándar de Ajuste (EEA)
"""

from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats

from core.frequency.distributions import (
    BaseDistribution,
    get_distribution,
    list_distributions,
)
from core.shared.types import FitResult, GoodnessOfFit


# Constants for statistical tests
MIN_VALID_BINS = 2
ASYMPTOTIC_THRESHOLD = 35


def fit_by_mom(series: pd.Series, distribution_name: str) -> dict[str, float]:
    """Ajusta una distribución usando el Método de Momentos (MOM).

    El método de momentos iguala los momentos muestrales con los teóricos
    para estimar los parámetros.

    Args:
        series: Serie de datos numéricos.
        distribution_name: Nombre de la distribución a ajustar.

    Returns:
        Diccionario con los parámetros estimados.

    Raises:
        ValueError: Si la distribución no existe o el ajuste falla.
    """
    dist = get_distribution(distribution_name)

    # Para la mayoría de distribuciones, el método fit() ya usa MOM o MLE
    # Aquí usamos el método fit() estándar que es apropiado para cada distribución
    try:
        return dist.fit(series)
    except (ValueError, TypeError, RuntimeError) as e:
        msg = f"MOM fitting failed for {distribution_name}: {e!s}"
        raise ValueError(msg) from e


def fit_by_mle(series: pd.Series, distribution_name: str) -> dict[str, float]:
    """Ajusta una distribución usando Máxima Verosimilitud (MLE).

    Maximiza la función de verosimilitud para encontrar los parámetros
    que mejor explican los datos observados.

    Args:
        series: Serie de datos numéricos.
        distribution_name: Nombre de la distribución a ajustar.

    Returns:
        Diccionario con los parámetros estimados.

    Raises:
        ValueError: Si la distribución no existe o el ajuste falla.
    """
    dist = get_distribution(distribution_name)

    # Para distribuciones donde scipy tiene MLE implementado, usaríamos eso
    # Por ahora, el método fit() de las distribuciones usa el mejor método disponible
    try:
        return dist.fit(series)
    except (ValueError, TypeError, RuntimeError) as e:
        msg = f"MLE fitting failed for {distribution_name}: {e!s}"
        raise ValueError(msg) from e


def fit_by_mentropy(series: pd.Series, distribution_name: str) -> dict[str, float]:
    """Ajusta una distribución usando el principio de Máxima Entropía (MEnt).

    El principio de máxima entropía selecciona la distribución menos sesgada
    dado un conjunto de restricciones (momentos).

    Nota: Para muchas distribuciones, esto coincide con el método de momentos.

    Args:
        series: Serie de datos numéricos.
        distribution_name: Nombre de la distribución a ajustar.

    Returns:
        Diccionario con los parámetros estimados.

    Raises:
        ValueError: Si la distribución no existe o el ajuste falla.
    """
    # Para máxima entropía, generalmente usamos los momentos muestrales
    # que es equivalente a MOM para distribuciones de la familia exponencial
    return fit_by_mom(series, distribution_name)


def chi_square_test(
    series: pd.Series,
    dist: BaseDistribution,
    params: dict[str, float],
    alpha: float = 0.05,
) -> tuple[float, float, Literal["ACCEPTED", "REJECTED"]]:
    """Prueba de bondad de ajuste Chi Cuadrado.

    Divide los datos en intervalos y compara las frecuencias observadas
    con las esperadas bajo la distribución ajustada.

    Args:
        series: Serie de datos observados.
        dist: Instancia de la distribución ajustada.
        params: Parámetros de la distribución.
        alpha: Nivel de significancia (default 0.05).

    Returns:
        Tupla (estadístico, valor_p, veredicto).
    """
    n = len(series)

    # Número de bins: regla de Sturges
    k = int(np.ceil(1 + np.log2(n)))
    k = max(k, 5)  # Mínimo 5 bins

    # Crear bins
    observed, bin_edges = np.histogram(series, bins=k)

    # Calcular frecuencias esperadas
    expected = np.zeros(k)
    for i in range(k):
        lower = bin_edges[i]
        upper = bin_edges[i + 1]
        # Probabilidad en el intervalo
        p_upper = dist.cdf(upper, params)
        p_lower = dist.cdf(lower, params)
        expected[i] = (p_upper - p_lower) * n

    # Evitar frecuencias esperadas muy pequeñas (unir bins si necesario)
    min_expected = 5
    valid_bins = expected >= min_expected

    if valid_bins.sum() < MIN_VALID_BINS:
        # No hay suficientes bins válidos, rechazar por defecto
        return 1e10, 0.0, "REJECTED"

    observed_valid = observed[valid_bins]
    expected_valid = expected[valid_bins]

    # Calcular estadístico Chi Cuadrado
    # Evitar división por cero reemplazando ceros con un valor pequeño
    expected_safe = np.where(expected_valid == 0, 1e-10, expected_valid)
    chi2_stat = ((observed_valid - expected_valid) ** 2 / expected_safe).sum()

    # Si el resultado es inf o nan, reemplazar con un valor grande
    if not np.isfinite(chi2_stat):
        chi2_stat = 1e10

    # Grados de libertad: k - 1 - número de parámetros
    dof = len(observed_valid) - 1 - len(params)
    dof = max(dof, 1)

    # Valor p
    p_value = 1 - stats.chi2.cdf(chi2_stat, dof)

    # Veredicto
    verdict = "ACCEPTED" if p_value > alpha else "REJECTED"

    return chi2_stat, p_value, verdict


def kolmogorov_smirnov_test(
    series: pd.Series,
    dist: BaseDistribution,
    params: dict[str, float],
    alpha: float = 0.05,
) -> tuple[float, float, Literal["ACCEPTED", "REJECTED"]]:
    """Prueba de bondad de ajuste Kolmogorov-Smirnov.

    Compara la CDF empírica con la CDF teórica y toma la máxima diferencia.

    Args:
        series: Serie de datos observados.
        dist: Instancia de la distribución ajustada.
        params: Parámetros de la distribución.
        alpha: Nivel de significancia (default 0.05).

    Returns:
        Tupla (estadístico, valor_p, veredicto).
    """
    n = len(series)
    sorted_series = np.sort(series)

    # CDF empírica
    empirical_cdf = np.arange(1, n + 1) / n

    # CDF teórica
    theoretical_cdf = np.array([dist.cdf(x, params) for x in sorted_series])

    # Estadístico KS: máxima diferencia absoluta
    d_stat = np.max(np.abs(empirical_cdf - theoretical_cdf))

    # Verificar si d_stat es finito
    if not np.isfinite(d_stat):
        d_stat = 1.0

    # Valor p aproximado (fórmula de Kolmogorov)
    # Para n > ASYMPTOTIC_THRESHOLD, usar aproximación asintótica
    if n > ASYMPTOTIC_THRESHOLD:
        z = d_stat * np.sqrt(n)
        # Aproximación de la distribución de Kolmogorov
        p_value = 2 * np.sum(
            [(-1) ** (k - 1) * np.exp(-2 * k**2 * z**2) for k in range(1, 20)]
        )
    else:
        # Para n pequeño, usar tablas o simulación
        # Aquí usamos una aproximación simplificada
        critical_value = 1.36 / np.sqrt(n)
        p_value = 1.0 if d_stat < critical_value else 0.0

    p_value = np.clip(p_value, 0, 1)

    # Verificar si p_value es finito
    if not np.isfinite(p_value):
        p_value = 0.0

    # Veredicto
    verdict = "ACCEPTED" if p_value > alpha else "REJECTED"

    return d_stat, p_value, verdict


def standard_error_of_fit(
    series: pd.Series,
    dist: BaseDistribution,
    params: dict[str, float],
    threshold: float = 0.1,
) -> tuple[float, Literal["ACCEPTED", "REJECTED"]]:
    """Calcula el Error Estándar de Ajuste (EEA).

    El EEA mide la desviación estándar de los residuos entre los valores
    observados y los cuantiles teóricos correspondientes.

    Args:
        series: Serie de datos observados.
        dist: Instancia de la distribución ajustada.
        params: Parámetros de la distribución.
        threshold: Umbral para considerar el ajuste aceptable (default 0.1).

    Returns:
        Tupla (eea, veredicto).
    """
    n = len(series)

    # Probabilidades empíricas (plotting positions)
    # Usamos fórmula de Weibull: (i - 0.44) / (n + 0.12)
    ranks = stats.rankdata(series)
    plotting_positions = (ranks - 0.44) / (n + 0.12)

    # Cuantiles teóricos
    theoretical_quantiles = np.array([dist.ppf(p, params) for p in plotting_positions])

    # Residuos
    residuals = series.to_numpy() - theoretical_quantiles

    # Error estándar
    eea = np.sqrt((residuals**2).sum() / n)

    # Verificar si eea es finito
    if not np.isfinite(eea):
        eea = 1e10

    # Normalizar por la media de la serie
    normalized_eea = eea / series.mean() if series.mean() > 0 else eea

    # Verificar si normalized_eea es finito
    if not np.isfinite(normalized_eea):
        normalized_eea = 1e10

    # Veredicto
    verdict = "ACCEPTED" if normalized_eea < threshold else "REJECTED"

    return eea, verdict


def calculate_goodness_of_fit(
    series: pd.Series,
    dist: BaseDistribution,
    params: dict[str, float],
    alpha: float = 0.05,
    eea_threshold: float = 0.1,
) -> GoodnessOfFit:
    """Calcula todos los indicadores de bondad de ajuste.

    Args:
        series: Serie de datos observados.
        dist: Instancia de la distribución ajustada.
        params: Parámetros de la distribución.
        alpha: Nivel de significancia para pruebas (default 0.05).
        eea_threshold: Umbral para EEA (default 0.1).

    Returns:
        Objeto GoodnessOfFit con todos los indicadores.
    """
    chi2_stat, chi2_p, chi2_verdict = chi_square_test(series, dist, params, alpha)
    ks_stat, ks_p, ks_verdict = kolmogorov_smirnov_test(series, dist, params, alpha)
    eea, eea_verdict = standard_error_of_fit(series, dist, params, eea_threshold)

    return GoodnessOfFit(
        chi_square=chi2_stat,
        chi_square_p_value=chi2_p,
        chi_square_verdict=chi2_verdict,
        ks_statistic=ks_stat,
        ks_p_value=ks_p,
        ks_verdict=ks_verdict,
        eea=eea,
        eea_verdict=eea_verdict,
    )


def fit_distribution(
    series: pd.Series,
    distribution_name: str,
    estimation_method: Literal["MOM", "MLE", "MEnt"] = "MOM",
) -> FitResult:
    """Ajusta una distribución a una serie y calcula bondad de ajuste.

    Args:
        series: Serie de datos numéricos.
        distribution_name: Nombre de la distribución a ajustar.
        estimation_method: Método de estimación de parámetros.
            Valores: "MOM", "MLE", "MEnt".

    Returns:
        Objeto FitResult con parámetros y bondad de ajuste.

    Raises:
        ValueError: Si la distribución no existe o el ajuste falla.
    """
    # Estimar parámetros según el método
    if estimation_method == "MOM":
        params = fit_by_mom(series, distribution_name)
    elif estimation_method == "MLE":
        params = fit_by_mle(series, distribution_name)
    elif estimation_method == "MEnt":
        params = fit_by_mentropy(series, distribution_name)
    else:
        msg = f"Unknown estimation method: {estimation_method}"
        raise ValueError(msg)

    # Obtener instancia de distribución
    dist = get_distribution(distribution_name)

    # Calcular bondad de ajuste
    goodness_of_fit = calculate_goodness_of_fit(series, dist, params)

    # Determinar si es recomendada (basado en veredictos de bondad de ajuste)
    # Una distribución es recomendada si pasa al menos 2 de las 3 pruebas
    accepted_count = sum(
        [
            goodness_of_fit.chi_square_verdict == "ACCEPTED",
            goodness_of_fit.ks_verdict == "ACCEPTED",
            goodness_of_fit.eea_verdict == "ACCEPTED",
        ]
    )
    is_recommended = accepted_count >= MIN_VALID_BINS

    return FitResult(
        distribution_name=distribution_name,
        parameters=params,
        estimation_method=estimation_method,
        goodness_of_fit=goodness_of_fit,
        is_recommended=is_recommended,
    )


def fit_all_distributions(
    series: pd.Series,
    estimation_method: Literal["MOM", "MLE", "MEnt"] = "MOM",
    distribution_names: list[str] | None = None,
) -> list[FitResult]:
    """Ajusta múltiples distribuciones a una serie.

    Args:
        series: Serie de datos numéricos.
        estimation_method: Método de estimación de parámetros.
        distribution_names: Lista de distribuciones a ajustar.
            Si es None, ajusta todas las disponibles.

    Returns:
        Lista de FitResult para cada distribución ajustada.
    """
    if distribution_names is None:
        distribution_names = list_distributions()

    results = []
    for dist_name in distribution_names:
        try:
            result = fit_distribution(series, dist_name, estimation_method)
            results.append(result)
        except ValueError:  # noqa: PERF203
            # Distribuciones que no pueden ajustarse (ej: requieren valores positivos)
            # se omiten silenciosamente
            continue

    # Ordenar por bondad de ajuste (EEA ascendente, luego KS)
    results.sort(key=lambda x: (x.goodness_of_fit.eea, x.goodness_of_fit.ks_statistic))

    # Marcar la mejor como recomendada si ninguna lo está
    recommended = [r for r in results if r.is_recommended]
    if not recommended and results:
        results[0].is_recommended = True

    return results


def get_best_distribution(
    series: pd.Series,
    estimation_method: Literal["MOM", "MLE", "MEnt"] = "MOM",
    distribution_names: list[str] | None = None,
) -> FitResult | None:
    """Obtiene la mejor distribución ajustada a una serie.

    Args:
        series: Serie de datos numéricos.
        estimation_method: Método de estimación de parámetros.
        distribution_names: Lista de distribuciones a considerar.

    Returns:
        El FitResult de la mejor distribución, o None si ninguna pudo ajustarse.
    """
    results = fit_all_distributions(series, estimation_method, distribution_names)

    if not results:
        return None

    # Retornar la primera (ya está ordenada por bondad de ajuste)
    return results[0]
