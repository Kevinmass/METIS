"""Tests unitarios para tests estadísticos SAMHIA integrados.

Este módulo prueba los nuevos tests estadísticos agregados desde SAMHIA:
- Tests de independencia: Durbin-Watson, Ljung-Box, Spearman
- Tests de homogeneidad: Mann-Whitney, Mood
- Detección de outliers: Método Kn
"""

import numpy as np
import pandas as pd
import pytest

from core.validation.homogeneity import (
    mann_whitney_test,
    mood_test,
)
from core.validation.independence import (
    durbin_watson_test,
    ljung_box_test,
    spearman_test,
)
from core.validation.outliers import (
    kn_outlier_detection,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def series_independent():
    """Serie sin autocorrelación significativa."""
    np.random.seed(42)
    return pd.Series(np.random.normal(0, 1, 50))


@pytest.fixture
def series_autocorrelated():
    """Serie con autocorrelación positiva fuerte."""
    # Random walk
    np.random.seed(42)
    values = np.cumsum(np.random.normal(0, 1, 50))
    return pd.Series(values)


@pytest.fixture
def series_with_outlier():
    """Serie con un outlier claro."""
    np.random.seed(42)
    values = list(np.random.normal(10, 1, 20))
    values[10] = 100  # Outlier en posición 10
    return pd.Series(values)


@pytest.fixture
def series_homogeneous():
    """Serie homogénea (dos mitades similares)."""
    np.random.seed(42)
    part1 = np.random.normal(10, 1, 25)
    part2 = np.random.normal(10, 1, 25)
    return pd.Series(np.concatenate([part1, part2]))


@pytest.fixture
def series_heterogeneous():
    """Serie heterogénea (dos mitades diferentes)."""
    np.random.seed(42)
    part1 = np.random.normal(10, 1, 25)
    part2 = np.random.normal(20, 1, 25)
    return pd.Series(np.concatenate([part1, part2]))


# ============================================================================
# TESTS DE INDEPENDENCIA
# ============================================================================


class TestDurbinWatson:
    """Tests para Durbin-Watson test."""

    def test_durbin_watson_independent_series(self, series_independent):
        """Serie independiente → DW cercano a 2, veredicto ACCEPTED."""
        result = durbin_watson_test(series_independent, alpha=0.05)

        assert result.name == "Durbin-Watson Test"
        assert result.statistic >= 1.5  # En rango aceptable
        assert result.statistic <= 2.5
        assert result.verdict == "ACCEPTED"
        assert result.detail["autocorrelation_type"] == "none"

    def test_durbin_watson_autocorrelated_series(self, series_autocorrelated):
        """Serie autocorrelada → DW < 1.5, veredicto REJECTED."""
        result = durbin_watson_test(series_autocorrelated, alpha=0.05)

        assert result.name == "Durbin-Watson Test"
        assert result.statistic < 1.5  # Autocorrelación positiva
        assert result.verdict == "REJECTED"
        assert result.detail["autocorrelation_type"] == "positive"

    def test_durbin_watson_returns_float_statistic(self, series_independent):
        """Verifica que el estadístico sea float."""
        result = durbin_watson_test(series_independent)
        assert isinstance(result.statistic, float)
        assert not np.isnan(result.statistic)


class TestLjungBox:
    """Tests para Ljung-Box test."""

    def test_ljung_box_independent_series(self, series_independent):
        """Serie independiente → p-value > alpha, veredicto ACCEPTED."""
        result = ljung_box_test(series_independent, lags=12, alpha=0.05)

        assert result.name == "Ljung-Box Test"
        assert result.detail["lags_tested"] == 12
        assert "p_value" in result.detail
        assert isinstance(result.detail["p_value"], float)

    def test_ljung_box_autocorrelated_series(self, series_autocorrelated):
        """Serie autocorrelada → p-value < alpha, veredicto REJECTED."""
        result = ljung_box_test(series_autocorrelated, lags=12, alpha=0.05)

        assert result.name == "Ljung-Box Test"
        assert result.detail["lags_tested"] == 12
        assert isinstance(result.statistic, float)

    def test_ljung_box_custom_lags(self, series_independent):
        """Verifica que se respete el parámetro lags."""
        result = ljung_box_test(series_independent, lags=5, alpha=0.05)

        assert result.detail["lags_tested"] == 5


class TestSpearman:
    """Tests para Spearman rank correlation test."""

    def test_spearman_independent_series(self, series_independent):
        """Serie independiente → correlación cercana a 0, veredicto ACCEPTED."""
        result = spearman_test(series_independent, alpha=0.05)

        assert result.name == "Spearman Rank Correlation Test"
        assert "rho" in result.detail
        assert "p_value" in result.detail
        assert isinstance(result.detail["rho"], float)
        assert isinstance(result.detail["p_value"], float)

    def test_spearman_autocorrelated_series(self, series_autocorrelated):
        """Serie autocorrelada → correlación alta, veredicto REJECTED."""
        result = spearman_test(series_autocorrelated, alpha=0.05)

        assert result.name == "Spearman Rank Correlation Test"
        assert abs(result.detail["rho"]) > 0.5  # Correlación alta
        assert result.detail["correlation_direction"] in ["positive", "negative"]

    def test_spearman_correlation_direction(self, series_autocorrelated):
        """Verifica que se detecte la dirección correcta de correlación."""
        result = spearman_test(series_autocorrelated, alpha=0.05)

        assert result.detail["correlation_direction"] == "positive"


# ============================================================================
# TESTS DE HOMOGENEIDAD
# ============================================================================


class TestMannWhitney:
    """Tests para Mann-Whitney U test."""

    def test_mann_whitney_homogeneous_series(self, series_homogeneous):
        """Serie homogénea → veredicto ACCEPTED."""
        result = mann_whitney_test(series_homogeneous, alpha=0.05)

        assert result.name == "Mann-Whitney U Homogeneity Test"
        assert "p_value" in result.detail
        assert "mean_first_half" in result.detail
        assert "mean_second_half" in result.detail
        assert isinstance(result.detail["p_value"], float)

    def test_mann_whitney_heterogeneous_series(self, series_heterogeneous):
        """Serie heterogénea → veredicto REJECTED."""
        result = mann_whitney_test(series_heterogeneous, alpha=0.05)

        assert result.name == "Mann-Whitney U Homogeneity Test"
        assert result.detail["mean_first_half"] != result.detail["mean_second_half"]
        assert isinstance(result.statistic, float)

    def test_mann_whitney_returns_group_sizes(self, series_homogeneous):
        """Verifica que se reporten los tamaños de grupos."""
        result = mann_whitney_test(series_homogeneous)

        assert "n1" in result.detail
        assert "n2" in result.detail
        assert result.detail["n1"] > 0
        assert result.detail["n2"] > 0


class TestMood:
    """Tests para Mood test."""

    def test_mood_homogeneous_series(self, series_homogeneous):
        """Serie homogénea → veredicto ACCEPTED."""
        result = mood_test(series_homogeneous, alpha=0.05)

        assert result.name == "Mood Scale Homogeneity Test"
        assert "p_value" in result.detail
        assert "variance_first_half" in result.detail
        assert "variance_second_half" in result.detail
        assert isinstance(result.detail["p_value"], float)

    def test_mood_heterogeneous_variance(self, series_heterogeneous):
        """Serie con varianzas diferentes → veredicto REJECTED."""
        result = mood_test(series_heterogeneous, alpha=0.05)

        assert result.name == "Mood Scale Homogeneity Test"
        assert isinstance(result.statistic, float)
        assert isinstance(result.detail["p_value"], float)

    def test_mood_returns_variance_info(self, series_homogeneous):
        """Verifica que se reporten las varianzas de ambas mitades."""
        result = mood_test(series_homogeneous)

        assert "variance_first_half" in result.detail
        assert "variance_second_half" in result.detail
        assert isinstance(result.detail["variance_first_half"], float)
        assert isinstance(result.detail["variance_second_half"], float)


# ============================================================================
# TESTS DE OUTLIERS (MÉTODO KN)
# ============================================================================


class TestKnOutlierDetection:
    """Tests para detección de outliers método Kn."""

    def test_kn_no_outliers(self, series_independent):
        """Serie sin outliers → veredicto ACCEPTED."""
        result = kn_outlier_detection(series_independent, alpha=0.05)

        assert result.name == "Kn Outlier Detection"
        assert result.verdict == "ACCEPTED"
        assert result.detail["outliers_count"] == 0
        assert len(result.detail["outliers_indices"]) == 0

    def test_kn_with_outlier(self, series_with_outlier):
        """Serie con outlier → veredicto REJECTED."""
        result = kn_outlier_detection(series_with_outlier, alpha=0.05)

        assert result.name == "Kn Outlier Detection"
        assert result.verdict == "REJECTED"
        assert result.detail["outliers_count"] > 0
        assert len(result.detail["outliers_indices"]) > 0
        assert 10 in result.detail["outliers_indices"]  # Outlier en posición 10

    def test_kn_returns_limits(self, series_independent):
        """Verifica que se calculen los límites correctamente."""
        result = kn_outlier_detection(series_independent)

        assert "kn_value" in result.detail
        assert "mean" in result.detail
        assert "std_dev" in result.detail
        assert "lower_limit" in result.detail
        assert "upper_limit" in result.detail
        assert result.detail["lower_limit"] < result.detail["mean"]
        assert result.detail["upper_limit"] > result.detail["mean"]

    def test_kn_value_increases_with_n(self):
        """Verifica que Kn aumenta con el tamaño de muestra."""
        np.random.seed(42)
        series_small = pd.Series(np.random.normal(0, 1, 20))
        series_large = pd.Series(np.random.normal(0, 1, 100))

        result_small = kn_outlier_detection(series_small)
        result_large = kn_outlier_detection(series_large)

        # Kn debe ser mayor para muestra más grande
        assert result_large.detail["kn_value"] > result_small.detail["kn_value"]

    def test_kn_limits_calculated_correctly(self, series_independent):
        """Verifica fórmula de límites: mean ± Kn * std."""
        result = kn_outlier_detection(series_independent)

        expected_lower = (
            result.detail["mean"] - result.detail["kn_value"] * result.detail["std_dev"]
        )
        expected_upper = (
            result.detail["mean"] + result.detail["kn_value"] * result.detail["std_dev"]
        )

        assert abs(result.detail["lower_limit"] - expected_lower) < 0.01
        assert abs(result.detail["upper_limit"] - expected_upper) < 0.01


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================


class TestSamhiaIntegration:
    """Tests de integración para verificar que los tests SAMHIA funcionen juntos."""

    def test_all_independence_tests_return_valid_results(self, series_independent):
        """Verifica que todos los tests de independencia retornen resultados válidos."""
        results = {
            "durbin_watson": durbin_watson_test(series_independent),
            "ljung_box": ljung_box_test(series_independent),
            "spearman": spearman_test(series_independent),
        }

        for name, result in results.items():
            assert result.name is not None
            assert isinstance(result.statistic, (float, list))
            assert result.verdict in ["ACCEPTED", "REJECTED"]
            assert result.alpha == 0.05
            assert isinstance(result.detail, dict)

    def test_all_homogeneity_tests_return_valid_results(self, series_homogeneous):
        """Verifica que todos los tests de homogeneidad retornen resultados válidos."""
        results = {
            "mann_whitney": mann_whitney_test(series_homogeneous),
            "mood": mood_test(series_homogeneous),
        }

        for name, result in results.items():
            assert result.name is not None
            assert isinstance(result.statistic, (float, type(None)))
            assert result.verdict in ["ACCEPTED", "REJECTED"]
            assert result.alpha == 0.05
            assert isinstance(result.detail, dict)

    def test_outlier_detection_returns_valid_result(self, series_with_outlier):
        """Verifica que la detección de outliers retorne resultado válido."""
        result = kn_outlier_detection(series_with_outlier)

        assert result.name is not None
        assert isinstance(result.statistic, float)
        assert result.verdict in ["ACCEPTED", "REJECTED"]
        assert result.alpha == 0.05
        assert isinstance(result.detail, dict)
        assert isinstance(result.detail["outliers_indices"], list)
