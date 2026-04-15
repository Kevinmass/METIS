"""Motor de distribuciones de probabilidad para análisis de frecuencia hidrológica.

Este módulo implementa las distribuciones de probabilidad más utilizadas en
hidrología para el análisis de frecuencia de eventos extremos. Cada distribución
expone una interfaz común: fit(series), cdf(x), ppf(p).

Distribuciones implementadas:
    - Normal
    - Log-Normal (2 parámetros)
    - Gumbel (Extreme Value Type I)
    - GEV (Generalized Extreme Value)
    - Pearson III
    - Log-Pearson III
    - Exponencial
    - Gamma (2 parámetros)
    - Weibull
    - Log-Logistic
    - Pareto
    - Beta
    - Rayleigh
"""

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from scipy import stats


# Minimum sample size for skewness calculation
MIN_SAMPLE_SIZE = 3


class BaseDistribution(ABC):
    """Clase base abstracta para todas las distribuciones.

    Define la interfaz común que todas las distribuciones deben implementar.
    """

    @abstractmethod
    def fit(self, series: pd.Series) -> dict[str, float]:
        """Ajusta la distribución a una serie de datos.

        Args:
            series: Serie de datos numéricos.

        Returns:
            Diccionario con los parámetros estimados.
        """

    @abstractmethod
    def cdf(self, x: float, params: dict[str, float]) -> float:
        """Función de distribución acumulada.

        Args:
            x: Valor para evaluar la CDF.
            params: Parámetros de la distribución.

        Returns:
            Probabilidad acumulada P(X <= x).
        """

    @abstractmethod
    def ppf(self, p: float, params: dict[str, float]) -> float:
        """Función cuantil inversa (percent point function).

        Args:
            p: Probabilidad (entre 0 y 1).
            params: Parámetros de la distribución.

        Returns:
            Valor x tal que P(X <= x) = p.
        """

    @abstractmethod
    def pdf(self, x: float, params: dict[str, float]) -> float:
        """Función de densidad de probabilidad.

        Args:
            x: Valor para evaluar la PDF.
            params: Parámetros de la distribución.

        Returns:
            Densidad de probabilidad en x.
        """


class NormalDistribution(BaseDistribution):
    """Distribución Normal (Gaussiana).

    Parámetros:
        - mu: Media
        - sigma: Desviación estándar
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        mu = series.mean()
        sigma = series.std(ddof=1)
        return {"mu": mu, "sigma": sigma}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        mu = params["mu"]
        sigma = params["sigma"]
        return stats.norm.cdf(x, loc=mu, scale=sigma)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        mu = params["mu"]
        sigma = params["sigma"]
        return stats.norm.ppf(p, loc=mu, scale=sigma)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        mu = params["mu"]
        sigma = params["sigma"]
        return stats.norm.pdf(x, loc=mu, scale=sigma)


class LogNormalDistribution(BaseDistribution):
    """Distribución Log-Normal (2 parámetros).

    Parámetros:
        - mu: Media del logaritmo natural
        - sigma: Desviación estándar del logaritmo natural
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        # Filtrar valores positivos
        positive_series = series[series > 0]
        if len(positive_series) == 0:
            msg = "Log-Normal requires positive values"
            raise ValueError(msg)
        log_series = np.log(positive_series)
        mu = log_series.mean()
        sigma = log_series.std(ddof=1)
        return {"mu": mu, "sigma": sigma}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        if x <= 0:
            return 0.0
        mu = params["mu"]
        sigma = params["sigma"]
        return stats.lognorm.cdf(x, s=sigma, scale=np.exp(mu))

    def ppf(self, p: float, params: dict[str, float]) -> float:
        mu = params["mu"]
        sigma = params["sigma"]
        return stats.lognorm.ppf(p, s=sigma, scale=np.exp(mu))

    def pdf(self, x: float, params: dict[str, float]) -> float:
        if x <= 0:
            return 0.0
        mu = params["mu"]
        sigma = params["sigma"]
        return stats.lognorm.pdf(x, s=sigma, scale=np.exp(mu))


class GumbelDistribution(BaseDistribution):
    """Distribución Gumbel (Extreme Value Type I).

    Utilizada para modelar máximos anuales de caudales.

    Parámetros:
        - xi: Parámetro de ubicación (mode)
        - alpha: Parámetro de escala
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        # Método de momentos para Gumbel
        mean = series.mean()
        std = series.std(ddof=1)

        # Constantes de Gumbel
        gamma = 0.5772156649  # Constante de Euler-Mascheroni

        alpha = (std * np.sqrt(6)) / np.pi
        xi = mean - gamma * alpha

        return {"xi": xi, "alpha": alpha}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        xi = params["xi"]
        alpha = params["alpha"]
        return stats.gumbel_r.cdf(x, loc=xi, scale=alpha)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        xi = params["xi"]
        alpha = params["alpha"]
        return stats.gumbel_r.ppf(p, loc=xi, scale=alpha)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        xi = params["xi"]
        alpha = params["alpha"]
        return stats.gumbel_r.pdf(x, loc=xi, scale=alpha)


class GEVDistribution(BaseDistribution):
    """Distribución Generalized Extreme Value (GEV).

    Generaliza Gumbel, Fréchet y Weibull para máximos.

    Parámetros:
        - xi: Parámetro de ubicación
        - alpha: Parámetro de escala
        - k: Parámetro de forma (shape)
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        # Usar scipy para ajuste por máxima verosimilitud
        params = stats.genextreme.fit(series)
        # scipy devuelve (c, loc, scale) donde c = -k
        k = -params[0]
        xi = params[1]
        alpha = params[2]
        return {"xi": xi, "alpha": alpha, "k": k}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        xi = params["xi"]
        alpha = params["alpha"]
        k = params["k"]
        c = -k
        return stats.genextreme.cdf(x, c=c, loc=xi, scale=alpha)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        xi = params["xi"]
        alpha = params["alpha"]
        k = params["k"]
        c = -k
        return stats.genextreme.ppf(p, c=c, loc=xi, scale=alpha)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        xi = params["xi"]
        alpha = params["alpha"]
        k = params["k"]
        c = -k
        return stats.genextreme.pdf(x, c=c, loc=xi, scale=alpha)


class PearsonIIIDistribution(BaseDistribution):
    """Distribución Pearson III.

    Distribución gamma con parámetro de ubicación.

    Parámetros:
        - mu: Media
        - sigma: Desviación estándar
        - gamma: Coeficiente de asimetría
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        mu = series.mean()
        sigma = series.std(ddof=1)

        # Coeficiente de asimetría
        n = len(series)
        if n < MIN_SAMPLE_SIZE or sigma == 0:
            gamma = 0.0
        else:
            gamma = ((series - mu) ** 3).sum() / ((n - 1) * sigma**3)

        return {"mu": mu, "sigma": sigma, "gamma": gamma}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        mu = params["mu"]
        sigma = params["sigma"]
        gamma = params["gamma"]

        if gamma == 0:
            # Caso especial: distribución normal
            return stats.norm.cdf(x, loc=mu, scale=sigma)

        # Transformación a distribución gamma
        alpha = 4 / (gamma**2)
        beta = sigma * abs(gamma) / 2
        xi = mu - 2 * sigma / gamma

        if gamma > 0:
            return stats.gamma.cdf(x - xi, a=alpha, scale=beta)
        return 1 - stats.gamma.cdf(xi - x, a=alpha, scale=beta)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        mu = params["mu"]
        sigma = params["sigma"]
        gamma = params["gamma"]

        if gamma == 0:
            return stats.norm.ppf(p, loc=mu, scale=sigma)

        alpha = 4 / (gamma**2)
        beta = sigma * abs(gamma) / 2
        xi = mu - 2 * sigma / gamma

        if gamma > 0:
            return xi + stats.gamma.ppf(p, a=alpha, scale=beta)
        return xi - stats.gamma.ppf(1 - p, a=alpha, scale=beta)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        # Aproximación numérica usando diferencias de CDF
        h = 1e-6
        return (self.cdf(x + h, params) - self.cdf(x - h, params)) / (2 * h)


class LogPearsonIIIDistribution(BaseDistribution):
    """Distribución Log-Pearson III.

    Pearson III aplicada a logaritmos de los datos.
    Muy utilizada en hidrología de EE.UU.

    Parámetros:
        - mu: Media del logaritmo
        - sigma: Desviación estándar del logaritmo
        - gamma: Coeficiente de asimetría del logaritmo
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        positive_series = series[series > 0]
        if len(positive_series) == 0:
            msg = "Log-Pearson III requires positive values"
            raise ValueError(msg)

        log_series = np.log(positive_series)
        mu = log_series.mean()
        sigma = log_series.std(ddof=1)

        n = len(log_series)
        if n < MIN_SAMPLE_SIZE or sigma == 0:
            gamma = 0.0
        else:
            gamma = ((log_series - mu) ** 3).sum() / ((n - 1) * sigma**3)

        return {"mu": mu, "sigma": sigma, "gamma": gamma}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        if x <= 0:
            return 0.0

        log_x = np.log(x)
        params_pearson = {
            "mu": params["mu"],
            "sigma": params["sigma"],
            "gamma": params["gamma"],
        }
        pearson = PearsonIIIDistribution()
        return pearson.cdf(log_x, params_pearson)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        params_pearson = {
            "mu": params["mu"],
            "sigma": params["sigma"],
            "gamma": params["gamma"],
        }
        pearson = PearsonIIIDistribution()
        log_x = pearson.ppf(p, params_pearson)
        return np.exp(log_x)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        if x <= 0:
            return 0.0
        h = 1e-6
        return (self.cdf(x + h, params) - self.cdf(x - h, params)) / (2 * h)


class ExponentialDistribution(BaseDistribution):
    """Distribución Exponencial.

    Modelo simple para tiempos entre eventos.

    Parámetros:
        - lambda_: Tasa (inverso de la media)
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        # Mínimo para shift
        x_min = series.min()
        shifted_series = series - x_min
        lambda_ = 1 / shifted_series.mean() if shifted_series.mean() > 0 else 1.0
        return {"lambda_": lambda_, "loc": x_min}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        lambda_ = params["lambda_"]
        loc = params.get("loc", 0.0)
        if x < loc:
            return 0.0
        return stats.expon.cdf(x, loc=loc, scale=1 / lambda_)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        lambda_ = params["lambda_"]
        loc = params.get("loc", 0.0)
        return stats.expon.ppf(p, loc=loc, scale=1 / lambda_)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        lambda_ = params["lambda_"]
        loc = params.get("loc", 0.0)
        if x < loc:
            return 0.0
        return stats.expon.pdf(x, loc=loc, scale=1 / lambda_)


class GammaDistribution(BaseDistribution):
    """Distribución Gamma (2 parámetros).

    Parámetros:
        - alpha: Parámetro de forma (shape)
        - beta: Parámetro de escala
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        # Ajuste usando scipy
        alpha, _loc, beta = stats.gamma.fit(series, floc=0)
        return {"alpha": alpha, "beta": beta}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        alpha = params["alpha"]
        beta = params["beta"]
        return stats.gamma.cdf(x, a=alpha, scale=beta)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        alpha = params["alpha"]
        beta = params["beta"]
        return stats.gamma.ppf(p, a=alpha, scale=beta)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        alpha = params["alpha"]
        beta = params["beta"]
        return stats.gamma.pdf(x, a=alpha, scale=beta)


class WeibullDistribution(BaseDistribution):
    """Distribución Weibull.

    Utilizada para análisis de supervivencia y confiabilidad.

    Parámetros:
        - c: Parámetro de forma (shape)
        - scale: Parámetro de escala
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        c, _loc, scale = stats.weibull_min.fit(series, floc=0)
        return {"c": c, "scale": scale}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        c = params["c"]
        scale = params["scale"]
        return stats.weibull_min.cdf(x, c=c, scale=scale)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        c = params["c"]
        scale = params["scale"]
        return stats.weibull_min.ppf(p, c=c, scale=scale)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        c = params["c"]
        scale = params["scale"]
        return stats.weibull_min.pdf(x, c=c, scale=scale)


class LogLogisticDistribution(BaseDistribution):
    """Distribución Log-Logistic.

    Similar a Log-Normal pero con colas más pesadas.

    Parámetros:
        - alpha: Parámetro de escala
        - beta: Parámetro de forma
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        positive_series = series[series > 0]
        if len(positive_series) == 0:
            msg = "Log-Logistic requires positive values"
            raise ValueError(msg)

        # Ajuste por máxima verosimilitud
        log_series = np.log(positive_series)
        alpha = np.exp(log_series.mean())
        beta = (
            1 / (log_series.std(ddof=1) * np.sqrt(3) / np.pi)
            if log_series.std(ddof=1) > 0
            else 1.0
        )

        return {"alpha": alpha, "beta": beta}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        if x <= 0:
            return 0.0
        alpha = params["alpha"]
        beta = params["beta"]
        return (x / alpha) ** beta / (1 + (x / alpha) ** beta)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        alpha = params["alpha"]
        beta = params["beta"]
        return alpha * (p / (1 - p)) ** (1 / beta)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        if x <= 0:
            return 0.0
        alpha = params["alpha"]
        beta = params["beta"]
        z = (x / alpha) ** beta
        return (beta / alpha) * z / (1 + z) ** 2


class ParetoDistribution(BaseDistribution):
    """Distribución Pareto (Tipo I).

    Para modelar colas pesadas.

    Parámetros:
        - xm: Parámetro de escala (mínimo)
        - alpha: Parámetro de forma (shape)
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        xm = series.min()
        if xm <= 0:
            msg = "Pareto requires positive minimum value"
            raise ValueError(msg)

        log_sum = np.sum(np.log(series / xm))
        if log_sum == 0:
            msg = "Cannot fit Pareto distribution: log sum is zero"
            raise ValueError(msg)

        alpha = len(series) / log_sum
        return {"xm": xm, "alpha": alpha}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        xm = params["xm"]
        alpha = params["alpha"]
        if x < xm:
            return 0.0
        return 1 - (xm / x) ** alpha

    def ppf(self, p: float, params: dict[str, float]) -> float:
        xm = params["xm"]
        alpha = params["alpha"]
        return xm / (1 - p) ** (1 / alpha)

    def pdf(self, x: float, params: dict[str, float]) -> float:
        xm = params["xm"]
        alpha = params["alpha"]
        if x < xm:
            return 0.0
        return alpha * xm**alpha / x ** (alpha + 1)


class BetaDistribution(BaseDistribution):
    """Distribución Beta.

    Para variables acotadas en [0, 1].

    Parámetros:
        - alpha: Parámetro de forma 1
        - beta: Parámetro de forma 2
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        # Normalizar a [0, 1]
        x_min = series.min()
        x_max = series.max()
        if x_max == x_min:
            msg = "Cannot fit Beta distribution with constant values"
            raise ValueError(msg)

        # Normalizar y agregar pequeño epsilon para evitar exactamente 0 y 1
        # scipy beta.fit requiere datos estrictamente entre 0 y 1
        epsilon = 1e-10
        normalized = (series - x_min) / (x_max - x_min)
        normalized = np.clip(normalized, epsilon, 1 - epsilon)

        alpha, beta_param, _loc, _scale = stats.beta.fit(normalized, floc=0, fscale=1)

        # Validar que los parámetros sean positivos
        if alpha <= 0 or beta_param <= 0:
            # Intentar método de momentos como fallback
            mean = normalized.mean()
            var = normalized.var()
            if var <= 0:
                msg = "Cannot fit Beta distribution: insufficient variance"
                raise ValueError(msg)

            # Método de momentos para Beta
            common = mean * (1 - mean) / var - 1
            if common <= 0:
                msg = "Cannot fit Beta distribution: invalid moment estimates"
                raise ValueError(msg)

            alpha = mean * common
            beta_param = (1 - mean) * common

        return {
            "alpha": alpha,
            "beta": beta_param,
            "loc": x_min,
            "scale": x_max - x_min,
        }

    def cdf(self, x: float, params: dict[str, float]) -> float:
        alpha = params["alpha"]
        beta_param = params["beta"]
        loc = params["loc"]
        scale = params["scale"]

        if scale == 0:
            return 1.0 if x >= loc else 0.0

        normalized = (x - loc) / scale
        normalized = np.clip(normalized, 0, 1)
        return stats.beta.cdf(normalized, a=alpha, b=beta_param)

    def ppf(self, p: float, params: dict[str, float]) -> float:
        alpha = params["alpha"]
        beta_param = params["beta"]
        loc = params["loc"]
        scale = params["scale"]

        normalized = stats.beta.ppf(p, a=alpha, b=beta_param)
        return loc + scale * normalized

    def pdf(self, x: float, params: dict[str, float]) -> float:
        alpha = params["alpha"]
        beta_param = params["beta"]
        loc = params["loc"]
        scale = params["scale"]

        if scale == 0:
            return 0.0

        normalized = (x - loc) / scale
        if normalized < 0 or normalized > 1:
            return 0.0

        return stats.beta.pdf(normalized, a=alpha, b=beta_param) / scale


class RayleighDistribution(BaseDistribution):
    """Distribución Rayleigh.

    Caso especial de Weibull con c=2.

    Parámetros:
        - sigma: Parámetro de escala
    """

    def fit(self, series: pd.Series) -> dict[str, float]:
        sigma = np.sqrt((series**2).mean() / 2)
        return {"sigma": sigma}

    def cdf(self, x: float, params: dict[str, float]) -> float:
        sigma = params["sigma"]
        if x < 0:
            return 0.0
        return 1 - np.exp(-(x**2) / (2 * sigma**2))

    def ppf(self, p: float, params: dict[str, float]) -> float:
        sigma = params["sigma"]
        return sigma * np.sqrt(-2 * np.log(1 - p))

    def pdf(self, x: float, params: dict[str, float]) -> float:
        sigma = params["sigma"]
        if x < 0:
            return 0.0
        return (x / sigma**2) * np.exp(-(x**2) / (2 * sigma**2))


# Diccionario de distribuciones disponibles
DISTRIBUTIONS: dict[str, BaseDistribution] = {
    "Normal": NormalDistribution(),
    "Log-Normal": LogNormalDistribution(),
    "Gumbel": GumbelDistribution(),
    "GEV": GEVDistribution(),
    "Pearson III": PearsonIIIDistribution(),
    "Log-Pearson III": LogPearsonIIIDistribution(),
    "Exponential": ExponentialDistribution(),
    "Gamma": GammaDistribution(),
    "Weibull": WeibullDistribution(),
    "Log-Logistic": LogLogisticDistribution(),
    "Pareto": ParetoDistribution(),
    "Beta": BetaDistribution(),
    "Rayleigh": RayleighDistribution(),
}


def get_distribution(name: str) -> BaseDistribution:
    """Obtiene una distribución por su nombre.

    Args:
        name: Nombre de la distribución.

    Returns:
        Instancia de la distribución.

    Raises:
        ValueError: Si la distribución no existe.
    """
    if name not in DISTRIBUTIONS:
        available = ", ".join(DISTRIBUTIONS.keys())
        msg = f"Distribution '{name}' not found. Available: {available}"
        raise ValueError(msg)
    return DISTRIBUTIONS[name]


def list_distributions() -> list[str]:
    """Lista todas las distribuciones disponibles.

    Returns:
        Lista de nombres de distribuciones.
    """
    return list(DISTRIBUTIONS.keys())
