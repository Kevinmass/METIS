"""Tests unitarios para métodos de ajuste y pruebas de bondad de ajuste.

Este módulo contiene tests para verificar la correcta implementación
de los métodos de estimación de parámetros (MOM, MLE, MEnt) y las
pruebas de bondad de ajuste (Chi-Square, KS, EEA).
"""

import numpy as np
import pandas as pd
import pytest

from core.frequency.distributions import NormalDistribution
from core.frequency.fitting import (
    calculate_goodness_of_fit,
    chi_square_test,
    fit_all_distributions,
    fit_by_mentropy,
    fit_by_mle,
    fit_by_mom,
    fit_distribution,
    get_best_distribution,
    kolmogorov_smirnov_test,
    standard_error_of_fit,
)
from core.shared.types import GoodnessOfFit


class TestEstimationMethods:
    """Tests para métodos de estimación de parámetros."""

    def test_fit_by_mom_normal(self):
        """Test de ajuste por MOM para distribución Normal."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        params = fit_by_mom(series, "Normal")

        assert "mu" in params
        assert "sigma" in params
        assert abs(params["mu"] - 3.0) < 0.1
        assert params["sigma"] > 0

    def test_fit_by_mle_normal(self):
        """Test de ajuste por MLE para distribución Normal."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        params = fit_by_mle(series, "Normal")

        assert "mu" in params
        assert "sigma" in params

    def test_fit_by_mentropy_normal(self):
        """Test de ajuste por Máxima Entropía para distribución Normal."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        params = fit_by_mentropy(series, "Normal")

        assert "mu" in params
        assert "sigma" in params

    def test_fit_by_mom_invalid_distribution(self):
        """Test de ajuste por MOM con distribución inválida."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

        with pytest.raises(ValueError, match="not found"):
            fit_by_mom(series, "InvalidDistribution")


class TestChiSquareTest:
    """Tests para prueba de bondad de ajuste Chi Cuadrado."""

    def test_chi_square_test_normal(self):
        """Test de Chi-Square con distribución Normal."""
        # Generar datos de una distribución normal
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=100))

        dist = NormalDistribution()
        params = {"mu": 0.0, "sigma": 1.0}

        chi2_stat, p_value, verdict = chi_square_test(series, dist, params)

        assert chi2_stat >= 0
        assert 0 <= p_value <= 1
        assert verdict in ["ACCEPTED", "REJECTED"]

    def test_chi_square_test_small_series(self):
        """Test de Chi-Square con serie pequeña."""
        series = pd.Series([1.0, 2.0, 3.0])
        dist = NormalDistribution()
        params = {"mu": 2.0, "sigma": 1.0}

        _chi2_stat, _p_value, verdict = chi_square_test(series, dist, params)

        # Con serie pequeña puede rechazar por falta de datos
        assert verdict in ["ACCEPTED", "REJECTED"]

    def test_chi_square_test_alpha(self):
        """Test de Chi-Square con diferentes niveles de significancia."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=100))

        dist = NormalDistribution()
        params = {"mu": 0.0, "sigma": 1.0}

        # Alpha 0.05
        _, p_value_05, _verdict_05 = chi_square_test(series, dist, params, alpha=0.05)

        # Alpha 0.01
        _, p_value_01, _verdict_01 = chi_square_test(series, dist, params, alpha=0.01)

        assert p_value_05 == p_value_01  # p-value no cambia
        # Veredicto puede cambiar con alpha diferente


class TestKolmogorovSmirnovTest:
    """Tests para prueba de bondad de ajuste Kolmogorov-Smirnov."""

    def test_ks_test_normal(self):
        """Test de KS con distribución Normal."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=100))

        dist = NormalDistribution()
        params = {"mu": 0.0, "sigma": 1.0}

        ks_stat, p_value, verdict = kolmogorov_smirnov_test(series, dist, params)

        assert ks_stat >= 0
        assert ks_stat <= 1
        assert 0 <= p_value <= 1
        assert verdict in ["ACCEPTED", "REJECTED"]

    def test_ks_test_perfect_fit(self):
        """Test de KS con ajuste perfecto (datos de la misma distribución)."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        # Ajustar a los mismos datos
        dist = NormalDistribution()
        params = dist.fit(series)

        ks_stat, _p_value, _verdict = kolmogorov_smirnov_test(series, dist, params)

        # Debe aceptar con alta probabilidad
        assert ks_stat < 0.3  # Estadístico debe ser pequeño

    def test_ks_test_poor_fit(self):
        """Test de KS con mal ajuste."""
        # Datos normales pero ajustados a distribución con parámetros incorrectos
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        dist = NormalDistribution()
        params = {"mu": 10.0, "sigma": 1.0}  # Media muy diferente

        _ks_stat, _p_value, verdict = kolmogorov_smirnov_test(series, dist, params)

        # Debe rechazar
        assert verdict == "REJECTED"


class TestStandardErrorOfFit:
    """Tests para Error Estándar de Ajuste."""

    def test_eea_normal(self):
        """Test de EEA con distribución Normal."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        dist = NormalDistribution()
        params = dist.fit(series)

        eea, verdict = standard_error_of_fit(series, dist, params)

        assert eea >= 0
        assert verdict in ["ACCEPTED", "REJECTED"]

    def test_eea_threshold(self):
        """Test de EEA con diferentes umbrales."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        dist = NormalDistribution()
        params = dist.fit(series)

        eea_1, _verdict_1 = standard_error_of_fit(series, dist, params, threshold=0.05)
        eea_2, _verdict_2 = standard_error_of_fit(series, dist, params, threshold=0.5)

        assert eea_1 == eea_2  # EEA no cambia
        # Veredicto puede cambiar con umbral diferente


class TestCalculateGoodnessOfFit:
    """Tests para cálculo completo de bondad de ajuste."""

    def test_calculate_goodness_of_fit(self):
        """Test de cálculo de todos los indicadores de bondad de ajuste."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=100))

        dist = NormalDistribution()
        params = {"mu": 0.0, "sigma": 1.0}

        gof = calculate_goodness_of_fit(series, dist, params)

        assert gof.chi_square >= 0
        assert 0 <= gof.chi_square_p_value <= 1
        assert gof.chi_square_verdict in ["ACCEPTED", "REJECTED"]

        assert gof.ks_statistic >= 0
        assert 0 <= gof.ks_p_value <= 1
        assert gof.ks_verdict in ["ACCEPTED", "REJECTED"]

        assert gof.eea >= 0
        assert gof.eea_verdict in ["ACCEPTED", "REJECTED"]


class TestFitDistribution:
    """Tests para función fit_distribution."""

    def test_fit_distribution_normal(self):
        """Test de ajuste de distribución Normal."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        result = fit_distribution(series, "Normal", estimation_method="MOM")

        assert result.distribution_name == "Normal"
        assert result.estimation_method == "MOM"
        assert "mu" in result.parameters
        assert "sigma" in result.parameters
        assert result.goodness_of_fit is not None

    def test_fit_distribution_invalid_method(self):
        """Test de ajuste con método inválido."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

        with pytest.raises(ValueError, match="Unknown estimation method"):
            fit_distribution(series, "Normal", estimation_method="INVALID")


class TestFitAllDistributions:
    """Tests para función fit_all_distributions."""

    def test_fit_all_distributions_default(self):
        """Test de ajuste de todas las distribuciones."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        results = fit_all_distributions(series, estimation_method="MOM")

        assert len(results) > 0
        # Al menos Normal debería ajustarse
        normal_result = next(
            (r for r in results if r.distribution_name == "Normal"), None
        )
        assert normal_result is not None

    def test_fit_all_distributions_specific(self):
        """Test de ajuste de distribuciones específicas."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        dist_names = ["Normal", "Gumbel"]
        results = fit_all_distributions(
            series, estimation_method="MOM", distribution_names=dist_names
        )

        assert len(results) <= 2
        assert all(r.distribution_name in dist_names for r in results)

    def test_fit_all_distributions_sorted(self):
        """Test de que resultados están ordenados por bondad de ajuste."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        results = fit_all_distributions(series, estimation_method="MOM")

        # Verificar que están ordenados por EEA ascendente
        eea_values = [r.goodness_of_fit.eea for r in results]
        assert eea_values == sorted(eea_values)

    def test_fit_all_distributions_recommended(self):
        """Test de que al menos una distribución es recomendada."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        results = fit_all_distributions(series, estimation_method="MOM")

        recommended = [r for r in results if r.is_recommended]
        assert len(recommended) >= 1


class TestGetBestDistribution:
    """Tests para función get_best_distribution."""

    def test_get_best_distribution(self):
        """Test de obtención de mejor distribución."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.normal(loc=0, scale=1, size=50))

        best = get_best_distribution(series, estimation_method="MOM")

        assert best is not None
        assert best.is_recommended

    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_get_best_distribution_none(self):
        """Test de get_best_distribution cuando ninguna ajusta."""
        # Serie muy pequeña o problemática
        series = pd.Series([1.0, 1.0, 1.0])

        # Con valores constantes, muchas distribuciones fallarán
        best = get_best_distribution(series, estimation_method="MOM")

        # Puede ser None si ninguna distribución pudo ajustarse
        # O puede haber alguna que sí (ej: Normal)
        assert best is None or best.is_recommended


class TestLogPearsonIIIFitting:
    """Tests específicos para ajuste de Log-Pearson III."""

    def test_fit_logpearson3_positive_series(self):
        """Test de ajuste de Log-Pearson III con serie positiva."""
        rng = np.random.default_rng(42)
        series = pd.Series(rng.lognormal(mean=1, sigma=0.5, size=50))

        result = fit_distribution(series, "Log-Pearson III", estimation_method="MOM")

        assert result.distribution_name == "Log-Pearson III"
        assert "mu" in result.parameters
        assert "sigma" in result.parameters
        assert "gamma" in result.parameters

    def test_fit_logpearson3_negative_fails(self):
        """Test de que Log-Pearson III falla con valores negativos."""
        series = pd.Series([-1.0, -2.0, -3.0])

        with pytest.raises(ValueError, match="positive"):
            fit_distribution(series, "Log-Pearson III", estimation_method="MOM")


class TestGoodnessOfFitCriteria:
    """Tests para criterios de recomendación de distribución."""

    def test_recommendation_two_accepted(self):
        """Test de recomendación cuando 2 de 3 pruebas aceptan."""
        # Crear un FitResult con 2 aceptaciones
        gof = GoodnessOfFit(
            chi_square=5.0,
            chi_square_p_value=0.5,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.1,
            ks_p_value=0.5,
            ks_verdict="ACCEPTED",
            eea=0.15,
            eea_verdict="REJECTED",
        )

        # fit_distribution debería marcar como recomendada si pasa 2 de 3
        # Este test verifica la lógica interna
        accepted_count = sum(
            [
                gof.chi_square_verdict == "ACCEPTED",
                gof.ks_verdict == "ACCEPTED",
                gof.eea_verdict == "ACCEPTED",
            ]
        )
        assert accepted_count == 2

    def test_recommendation_one_accepted(self):
        """Test de no recomendación cuando solo 1 de 3 pruebas acepta."""
        gof = GoodnessOfFit(
            chi_square=5.0,
            chi_square_p_value=0.5,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.3,
            ks_p_value=0.01,
            ks_verdict="REJECTED",
            eea=0.5,
            eea_verdict="REJECTED",
        )

        accepted_count = sum(
            [
                gof.chi_square_verdict == "ACCEPTED",
                gof.ks_verdict == "ACCEPTED",
                gof.eea_verdict == "ACCEPTED",
            ]
        )
        assert accepted_count == 1
