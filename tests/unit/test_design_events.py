"""Tests unitarios para cálculo de eventos de diseño.

Este módulo contiene tests para verificar la correcta implementación
del cálculo de eventos de diseño a partir de distribuciones ajustadas.
"""

import pytest

from core.frequency.design_events import (
    calculate_design_event,
    calculate_exceedance_probability,
    calculate_multiple_design_events,
    calculate_return_period_from_value,
    get_standard_return_periods,
)
from core.shared.types import FitResult, GoodnessOfFit


class TestCalculateDesignEvent:
    """Tests para función calculate_design_event."""

    def test_calculate_design_event_t100(self):
        """Test de cálculo de evento de diseño para T=100."""
        # Crear FitResult con distribución Normal
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        event = calculate_design_event(fit_result, return_period=100.0)

        assert event.return_period == 100.0
        assert event.annual_probability == 0.99
        assert event.design_value > 100.0  # Debe ser mayor que la media
        assert event.distribution_name == "Normal"

    def test_calculate_design_event_t50(self):
        """Test de cálculo de evento de diseño para T=50."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        event = calculate_design_event(fit_result, return_period=50.0)

        assert event.return_period == 50.0
        assert event.annual_probability == 0.98
        # Para T=50, el valor debe ser menor que para T=100
        event_100 = calculate_design_event(fit_result, return_period=100.0)
        assert event.design_value < event_100.design_value

    def test_calculate_design_event_invalid_return_period(self):
        """Test de cálculo con período de retorno inválido."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        with pytest.raises(ValueError, match="must be positive"):
            calculate_design_event(fit_result, return_period=-10.0)

        with pytest.raises(ValueError, match="must be positive"):
            calculate_design_event(fit_result, return_period=0.0)

    def test_calculate_design_event_t2(self):
        """Test de cálculo de evento de diseño para T=2 (mediana)."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        event = calculate_design_event(fit_result, return_period=2.0)

        assert event.return_period == 2.0
        assert event.annual_probability == 0.5
        # Para distribución normal, T=2 debe dar la mediana ≈ media
        assert abs(event.design_value - 100.0) < 1.0


class TestCalculateMultipleDesignEvents:
    """Tests para función calculate_multiple_design_events."""

    def test_calculate_multiple_design_events(self):
        """Test de cálculo de múltiples eventos de diseño."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        return_periods = [2, 5, 10, 25, 50, 100]
        events = calculate_multiple_design_events(fit_result, return_periods)

        assert len(events) == len(return_periods)
        # Verificar que están ordenados por período de retorno
        assert events == sorted(events, key=lambda e: e.return_period)

        # Verificar que los valores de diseño crecen con el período
        design_values = [e.design_value for e in events]
        assert design_values == sorted(design_values)

    def test_calculate_multiple_design_events_with_invalid(self):
        """Test de cálculo con períodos inválidos mezclados."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        # Incluir un valor inválido
        return_periods = [2, -10, 5, 0, 10]
        events = calculate_multiple_design_events(fit_result, return_periods)

        # Debe ignorar los valores inválidos
        assert len(events) == 3
        assert all(e.return_period > 0 for e in events)


class TestGetStandardReturnPeriods:
    """Tests para función get_standard_return_periods."""

    def test_get_standard_return_periods(self):
        """Test de obtención de períodos de retorno estándar."""
        periods = get_standard_return_periods()

        assert isinstance(periods, list)
        assert len(periods) > 0
        assert 2 in periods
        assert 5 in periods
        assert 10 in periods
        assert 50 in periods
        assert 100 in periods

    def test_standard_return_periods_sorted(self):
        """Test de que períodos estándar están ordenados."""
        periods = get_standard_return_periods()

        assert periods == sorted(periods)


class TestCalculateExceedanceProbability:
    """Tests para función calculate_exceedance_probability."""

    def test_calculate_exceedance_probability(self):
        """Test de cálculo de probabilidad de excedencia."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        # Valor muy alto debe tener baja probabilidad de excedencia
        prob_high = calculate_exceedance_probability(fit_result, 200.0)
        assert 0 <= prob_high < 0.1

        # Valor cerca de la media debe tener ~50% de probabilidad de excedencia
        prob_median = calculate_exceedance_probability(fit_result, 100.0)
        assert 0.4 <= prob_median <= 0.6

        # Valor muy bajo debe tener alta probabilidad de excedencia
        prob_low = calculate_exceedance_probability(fit_result, 50.0)
        assert prob_low > 0.8

    def test_calculate_exceedance_probability_bounds(self):
        """Test de que probabilidad de excedencia está entre 0 y 1."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        for value in [0.0, 50.0, 100.0, 150.0, 200.0, 1000.0]:
            prob = calculate_exceedance_probability(fit_result, value)
            assert 0 <= prob <= 1


class TestCalculateReturnPeriodFromValue:
    """Tests para función calculate_return_period_from_value."""

    def test_calculate_return_period_from_value(self):
        """Test de cálculo de período de retorno desde un valor."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        # Valor alto debe dar período de retorno grande
        rp_high = calculate_return_period_from_value(fit_result, 200.0)
        assert rp_high > 10

        # Valor cerca de la media debe dar T ≈ 2
        rp_median = calculate_return_period_from_value(fit_result, 100.0)
        assert 1.5 <= rp_median <= 2.5

    def test_calculate_return_period_from_value_extreme(self):
        """Test de cálculo con valor extremo
        (probabilidad de excedencia cercana a 0)."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        # Valor extremadamente alto que puede causar probabilidad de excedencia ~0
        # Esto debe lanzar ValueError
        with pytest.raises(ValueError, match="exceedance probability"):
            calculate_return_period_from_value(fit_result, 1000.0)

    def test_calculate_return_period_from_value_zero_exceedance(self):
        """Test de cálculo cuando probabilidad de excedencia es 0."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        # Valor extremadamente alto que da probabilidad de excedencia ~0
        # En práctica, esto puede depender de la implementación
        # Este test verifica el manejo del error
        with pytest.raises(ValueError, match="exceedance probability"):
            calculate_return_period_from_value(fit_result, 10000.0)


class TestDesignEventConsistency:
    """Tests de consistencia entre funciones de eventos de diseño."""

    def test_design_event_exceedance_probability_consistency(self):
        """Test de consistencia entre evento de diseño y probabilidad de excedencia."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        # Calcular evento de diseño para T=100
        event = calculate_design_event(fit_result, return_period=100.0)

        # Calcular probabilidad de excedencia para ese valor
        exceedance_prob = calculate_exceedance_probability(
            fit_result, event.design_value
        )

        # La probabilidad de excedencia debe ser 1/T = 0.01
        assert abs(exceedance_prob - 0.01) < 0.001

    def test_design_event_return_period_consistency(self):
        """Test de consistencia entre evento de diseño y período de retorno inverso."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        # Calcular evento de diseño para T=50
        event = calculate_design_event(fit_result, return_period=50.0)

        # Calcular período de retorno desde ese valor
        calculated_rp = calculate_return_period_from_value(
            fit_result, event.design_value
        )

        # Debe dar aproximadamente el mismo período de retorno
        assert abs(calculated_rp - 50.0) < 1.0

    def test_monotonic_design_values(self):
        """Test de que valores de diseño son monótonos con período de retorno."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        return_periods = [2, 5, 10, 25, 50, 100, 200, 500]
        events = calculate_multiple_design_events(fit_result, return_periods)

        # Verificar que los valores de diseño crecen monótonamente
        design_values = [e.design_value for e in events]
        for i in range(1, len(design_values)):
            assert design_values[i] > design_values[i - 1]

    def test_annual_probability_formula(self):
        """Test de que la probabilidad anual sigue la fórmula 1 - 1/T."""
        gof = GoodnessOfFit(
            chi_square=0.0,
            chi_square_p_value=1.0,
            chi_square_verdict="ACCEPTED",
            ks_statistic=0.0,
            ks_p_value=1.0,
            ks_verdict="ACCEPTED",
            eea=0.0,
            eea_verdict="ACCEPTED",
        )

        fit_result = FitResult(
            distribution_name="Normal",
            parameters={"mu": 100.0, "sigma": 20.0},
            estimation_method="MOM",
            goodness_of_fit=gof,
            is_recommended=True,
        )

        for return_period in [2, 5, 10, 25, 50, 100]:
            event = calculate_design_event(fit_result, return_period=return_period)
            expected_prob = 1.0 - 1.0 / return_period
            assert abs(event.annual_probability - expected_prob) < 1e-10
