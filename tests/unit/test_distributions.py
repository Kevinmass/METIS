"""Tests unitarios para el motor de distribuciones de probabilidad.

Este módulo contiene tests para verificar la correcta implementación
de las distribuciones de probabilidad utilizadas en análisis de frecuencia
hidrológica.
"""

import pandas as pd
import pytest

from core.frequency.distributions import (
    BetaDistribution,
    ExponentialDistribution,
    GammaDistribution,
    GEVDistribution,
    GumbelDistribution,
    LogLogisticDistribution,
    LogNormalDistribution,
    LogPearsonIIIDistribution,
    NormalDistribution,
    ParetoDistribution,
    PearsonIIIDistribution,
    RayleighDistribution,
    WeibullDistribution,
    get_distribution,
    list_distributions,
)


class TestNormalDistribution:
    """Tests para la distribución Normal."""

    def test_fit_normal(self):
        """Test de ajuste de distribución Normal."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = NormalDistribution()
        params = dist.fit(series)

        assert "mu" in params
        assert "sigma" in params
        assert abs(params["mu"] - 3.0) < 0.1  # Media aproximada
        assert params["sigma"] > 0

    def test_cdf_normal(self):
        """Test de CDF de distribución Normal."""
        dist = NormalDistribution()
        params = {"mu": 0.0, "sigma": 1.0}

        # CDF en la media debe ser ~0.5
        cdf_mean = dist.cdf(0.0, params)
        assert abs(cdf_mean - 0.5) < 0.01

        # CDF en -inf debe ser ~0
        cdf_neg = dist.cdf(-10.0, params)
        assert cdf_neg < 0.01

        # CDF en +inf debe ser ~1
        cdf_pos = dist.cdf(10.0, params)
        assert cdf_pos > 0.99

    def test_ppf_normal(self):
        """Test de PPF de distribución Normal."""
        dist = NormalDistribution()
        params = {"mu": 0.0, "sigma": 1.0}

        # PPF de 0.5 debe ser la media
        ppf_median = dist.ppf(0.5, params)
        assert abs(ppf_median - 0.0) < 0.01

        # Consistencia: ppf(cdf(x)) ≈ x
        x = 1.5
        cdf_x = dist.cdf(x, params)
        ppf_cdf = dist.ppf(cdf_x, params)
        assert abs(ppf_cdf - x) < 0.01

    def test_pdf_normal(self):
        """Test de PDF de distribución Normal."""
        dist = NormalDistribution()
        params = {"mu": 0.0, "sigma": 1.0}

        # PDF en la media debe ser máxima
        pdf_mean = dist.pdf(0.0, params)
        pdf_tail = dist.pdf(3.0, params)
        assert pdf_mean > pdf_tail


class TestLogNormalDistribution:
    """Tests para la distribución Log-Normal."""

    def test_fit_lognormal(self):
        """Test de ajuste de distribución Log-Normal."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = LogNormalDistribution()
        params = dist.fit(series)

        assert "mu" in params
        assert "sigma" in params
        assert params["sigma"] > 0

    def test_cdf_lognormal_positive_only(self):
        """Test de CDF de Log-Normal solo acepta valores positivos."""
        dist = LogNormalDistribution()
        params = {"mu": 0.0, "sigma": 1.0}

        # CDF de valor negativo debe ser 0
        cdf_neg = dist.cdf(-1.0, params)
        assert cdf_neg == 0.0

        # CDF de valor positivo debe ser > 0
        cdf_pos = dist.cdf(1.0, params)
        assert cdf_pos > 0

    def test_fit_lognormal_requires_positive(self):
        """Test de que Log-Normal requiere valores positivos."""
        series = pd.Series([-1.0, -2.0, -3.0])
        dist = LogNormalDistribution()

        with pytest.raises(ValueError, match="positive values"):
            dist.fit(series)


class TestGumbelDistribution:
    """Tests para la distribución Gumbel."""

    def test_fit_gumbel(self):
        """Test de ajuste de distribución Gumbel."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = GumbelDistribution()
        params = dist.fit(series)

        assert "xi" in params
        assert "alpha" in params
        assert params["alpha"] > 0

    def test_cdf_gumbel(self):
        """Test de CDF de distribución Gumbel."""
        dist = GumbelDistribution()
        params = {"xi": 0.0, "alpha": 1.0}

        # CDF debe estar entre 0 y 1
        cdf = dist.cdf(0.0, params)
        assert 0 <= cdf <= 1


class TestGEVDistribution:
    """Tests para la distribución GEV."""

    def test_fit_gev(self):
        """Test de ajuste de distribución GEV."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = GEVDistribution()
        params = dist.fit(series)

        assert "xi" in params
        assert "alpha" in params
        assert "k" in params

    def test_cdf_gev(self):
        """Test de CDF de distribución GEV."""
        dist = GEVDistribution()
        params = {"xi": 0.0, "alpha": 1.0, "k": 0.0}

        # CDF debe estar entre 0 y 1
        cdf = dist.cdf(0.0, params)
        assert 0 <= cdf <= 1


class TestPearsonIIIDistribution:
    """Tests para la distribución Pearson III."""

    def test_fit_pearson3(self):
        """Test de ajuste de distribución Pearson III."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = PearsonIIIDistribution()
        params = dist.fit(series)

        assert "mu" in params
        assert "sigma" in params
        assert "gamma" in params

    def test_cdf_pearson3_symmetric(self):
        """Test de CDF de Pearson III con asimetría cero (caso normal)."""
        dist = PearsonIIIDistribution()
        params = {"mu": 0.0, "sigma": 1.0, "gamma": 0.0}

        # Con gamma=0, debe comportarse como normal
        cdf = dist.cdf(0.0, params)
        assert abs(cdf - 0.5) < 0.01


class TestLogPearsonIIIDistribution:
    """Tests para la distribución Log-Pearson III."""

    def test_fit_logpearson3(self):
        """Test de ajuste de distribución Log-Pearson III."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = LogPearsonIIIDistribution()
        params = dist.fit(series)

        assert "mu" in params
        assert "sigma" in params
        assert "gamma" in params

    def test_cdf_logpearson3_positive_only(self):
        """Test de CDF de Log-Pearson III solo acepta valores positivos."""
        dist = LogPearsonIIIDistribution()
        params = {"mu": 0.0, "sigma": 1.0, "gamma": 0.0}

        # CDF de valor negativo debe ser 0
        cdf_neg = dist.cdf(-1.0, params)
        assert cdf_neg == 0.0


class TestExponentialDistribution:
    """Tests para la distribución Exponencial."""

    def test_fit_exponential(self):
        """Test de ajuste de distribución Exponencial."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = ExponentialDistribution()
        params = dist.fit(series)

        assert "lambda_" in params
        assert params["lambda_"] > 0

    def test_cdf_exponential(self):
        """Test de CDF de distribución Exponencial."""
        dist = ExponentialDistribution()
        params = {"lambda_": 1.0, "loc": 0.0}

        # CDF debe estar entre 0 y 1
        cdf = dist.cdf(1.0, params)
        assert 0 <= cdf <= 1


class TestGammaDistribution:
    """Tests para la distribución Gamma."""

    def test_fit_gamma(self):
        """Test de ajuste de distribución Gamma."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = GammaDistribution()
        params = dist.fit(series)

        assert "alpha" in params
        assert "beta" in params
        assert params["alpha"] > 0
        assert params["beta"] > 0


class TestWeibullDistribution:
    """Tests para la distribución Weibull."""

    def test_fit_weibull(self):
        """Test de ajuste de distribución Weibull."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = WeibullDistribution()
        params = dist.fit(series)

        assert "c" in params
        assert "scale" in params
        assert params["c"] > 0
        assert params["scale"] > 0


class TestLogLogisticDistribution:
    """Tests para la distribución Log-Logistic."""

    def test_fit_loglogistic(self):
        """Test de ajuste de distribución Log-Logistic."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = LogLogisticDistribution()
        params = dist.fit(series)

        assert "alpha" in params
        assert "beta" in params
        assert params["alpha"] > 0
        assert params["beta"] > 0


class TestParetoDistribution:
    """Tests para la distribución Pareto."""

    def test_fit_pareto(self):
        """Test de ajuste de distribución Pareto."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = ParetoDistribution()
        params = dist.fit(series)

        assert "xm" in params
        assert "alpha" in params
        assert params["xm"] > 0
        assert params["alpha"] > 0


class TestBetaDistribution:
    """Tests para la distribución Beta."""

    def test_fit_beta(self):
        """Test de ajuste de distribución Beta."""
        series = pd.Series([0.1, 0.3, 0.5, 0.7, 0.9])
        dist = BetaDistribution()
        params = dist.fit(series)

        assert "alpha" in params
        assert "beta" in params
        assert params["alpha"] > 0
        assert params["beta"] > 0

    def test_fit_beta_constant_fails(self):
        """Test de que Beta falla con valores constantes."""
        series = pd.Series([1.0, 1.0, 1.0])
        dist = BetaDistribution()

        with pytest.raises(ValueError, match="constant values"):
            dist.fit(series)


class TestRayleighDistribution:
    """Tests para la distribución Rayleigh."""

    def test_fit_rayleigh(self):
        """Test de ajuste de distribución Rayleigh."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = RayleighDistribution()
        params = dist.fit(series)

        assert "sigma" in params
        assert params["sigma"] > 0


class TestDistributionRegistry:
    """Tests para el registro de distribuciones."""

    def test_list_distributions(self):
        """Test de listado de distribuciones disponibles."""
        dist_list = list_distributions()

        assert isinstance(dist_list, list)
        assert len(dist_list) > 0
        assert "Normal" in dist_list
        assert "Log-Normal" in dist_list
        assert "Gumbel" in dist_list

    def test_get_distribution_valid(self):
        """Test de obtención de distribución válida."""
        dist = get_distribution("Normal")
        assert isinstance(dist, NormalDistribution)

        dist = get_distribution("Gumbel")
        assert isinstance(dist, GumbelDistribution)

    def test_get_distribution_invalid(self):
        """Test de obtención de distribución inválida."""
        with pytest.raises(ValueError, match="not found"):
            get_distribution("InvalidDistribution")


class TestDistributionConsistency:
    """Tests de consistencia interna de distribuciones."""

    @pytest.mark.parametrize(
        ("dist_class", "params"),
        [
            (NormalDistribution, {"mu": 0.0, "sigma": 1.0}),
            (GumbelDistribution, {"xi": 0.0, "alpha": 1.0}),
            (ExponentialDistribution, {"lambda_": 1.0, "loc": 0.0}),
        ],
    )
    def test_ppf_cdf_consistency(self, dist_class, params):
        """Test de consistencia: ppf(cdf(x)) ≈ x."""
        dist = dist_class()
        test_values = [0.5, 1.0, 2.0]

        for x in test_values:
            cdf_x = dist.cdf(x, params)
            ppf_cdf = dist.ppf(cdf_x, params)
            assert abs(ppf_cdf - x) < 0.01, f"Failed for {x} in {dist_class.__name__}"

    @pytest.mark.parametrize(
        ("dist_class", "params"),
        [
            (NormalDistribution, {"mu": 0.0, "sigma": 1.0}),
            (GumbelDistribution, {"xi": 0.0, "alpha": 1.0}),
        ],
    )
    def test_cdf_monotonic(self, dist_class, params):
        """Test de que CDF es monótona creciente."""
        dist = dist_class()
        x1, x2 = 0.0, 1.0

        cdf1 = dist.cdf(x1, params)
        cdf2 = dist.cdf(x2, params)

        assert cdf2 >= cdf1

    @pytest.mark.parametrize(
        ("dist_class", "params"),
        [
            (NormalDistribution, {"mu": 0.0, "sigma": 1.0}),
            (GumbelDistribution, {"xi": 0.0, "alpha": 1.0}),
        ],
    )
    def test_ppf_monotonic(self, dist_class, params):
        """Test de que PPF es monótona creciente."""
        dist = dist_class()
        p1, p2 = 0.3, 0.7

        ppf1 = dist.ppf(p1, params)
        ppf2 = dist.ppf(p2, params)

        assert ppf2 >= ppf1
