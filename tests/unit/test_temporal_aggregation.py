"""Tests unitarios para el módulo de agregación temporal.

Este módulo prueba la detección de frecuencias y agregaciones
de series temporales hidrológicas.
"""

import numpy as np
import pandas as pd
import pytest

from core.temporal.aggregation import (
    AggregationMethod,
    FrequencyType,
    aggregate_daily,
    aggregate_monthly,
    aggregate_subdaily,
    auto_aggregate,
    detect_frequency,
)


class TestDetectFrequency:
    """Tests para la función detect_frequency."""

    def test_detect_5min_frequency(self):
        """Detecta correctamente frecuencia de 5 minutos."""
        dates = pd.date_range("2020-01-01", periods=100, freq="5min")
        series = pd.Series(range(100), index=dates)
        result = detect_frequency(series)
        assert result == FrequencyType.MINUTES_5

    def test_detect_hourly_frequency(self):
        """Detecta correctamente frecuencia horaria."""
        dates = pd.date_range("2020-01-01", periods=24, freq="h")
        series = pd.Series(range(24), index=dates)
        result = detect_frequency(series)
        assert result == FrequencyType.HOURLY

    def test_detect_daily_frequency(self):
        """Detecta correctamente frecuencia diaria."""
        dates = pd.date_range("2020-01-01", periods=365, freq="D")
        series = pd.Series(range(365), index=dates)
        result = detect_frequency(series)
        assert result == FrequencyType.DAILY

    def test_detect_monthly_frequency(self):
        """Detecta correctamente frecuencia mensual."""
        dates = pd.date_range("2020-01", periods=12, freq="ME")
        series = pd.Series(range(12), index=dates)
        result = detect_frequency(series)
        assert result == FrequencyType.MONTHLY

    def test_detect_yearly_frequency_year_start(self):
        """Detecta correctamente frecuencia anual (YS)."""
        dates = pd.date_range("2020-01-01", periods=5, freq="YS")
        series = pd.Series([100, 200, 150, 180, 220], index=dates)
        result = detect_frequency(series)
        assert result == FrequencyType.YEARLY

    def test_detect_yearly_frequency_year_end(self):
        """Detecta correctamente frecuencia anual (YE)."""
        dates = pd.date_range("2020-12-31", periods=5, freq="YE")
        series = pd.Series([100, 200, 150, 180, 220], index=dates)
        result = detect_frequency(series)
        assert result == FrequencyType.YEARLY

    def test_detect_yearly_by_interval(self):
        """Detecta frecuencia anual por análisis de intervalos."""
        # Crear fechas aproximadamente anuales (no exactas)
        dates = pd.DatetimeIndex(
            ["2020-01-15", "2021-01-20", "2022-01-10", "2023-01-25"]
        )
        series = pd.Series([100, 200, 150, 180], index=dates)
        result = detect_frequency(series)
        assert result == FrequencyType.YEARLY

    def test_irregular_frequency(self):
        """Detecta frecuencia irregular por alta variabilidad en intervalos."""
        # Intervalos muy variables: 1 día, 10 días, 60 días (CV > 0.5)
        dates = pd.DatetimeIndex(
            ["2020-01-01", "2020-01-02", "2020-01-12", "2020-03-13"]
        )
        series = pd.Series([1, 2, 3, 4], index=dates)
        result = detect_frequency(series)
        assert result == FrequencyType.IRREGULAR

    def test_non_datetime_index(self):
        """Retorna IRREGULAR si no hay DatetimeIndex."""
        series = pd.Series([1, 2, 3, 4, 5])
        result = detect_frequency(series)
        assert result == FrequencyType.IRREGULAR


class TestAggregateMonthly:
    """Tests para la función aggregate_monthly."""

    def test_monthly_to_annual_sum(self):
        """Agrega serie mensual a anual por suma."""
        dates = pd.date_range("2020-01", periods=24, freq="ME")
        # 24 meses = 2 años completos
        series = pd.Series([100] * 12 + [200] * 12, index=dates)
        result = aggregate_monthly(series, method="sum")

        assert len(result) == 2
        assert result.loc[2020] == 1200  # 100 * 12
        assert result.loc[2021] == 2400  # 200 * 12
        assert result.index.name == "year"

    def test_monthly_to_annual_mean(self):
        """Agrega serie mensual a anual por promedio."""
        dates = pd.date_range("2020-01", periods=12, freq="ME")
        series = pd.Series(
            [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120], index=dates
        )
        result = aggregate_monthly(series, method="mean")

        assert len(result) == 1
        assert result.loc[2020] == pytest.approx(65.0)

    def test_monthly_to_annual_max(self):
        """Agrega serie mensual a anual por máximo."""
        dates = pd.date_range("2020-01", periods=12, freq="ME")
        series = pd.Series([10, 20, 5, 30, 15, 8, 25, 12, 18, 35, 22, 9], index=dates)
        result = aggregate_monthly(series, method="max")

        assert len(result) == 1
        assert result.loc[2020] == 35

    def test_monthly_hydrological_year(self):
        """Agrega usando año hidrológico (oct-sep)."""
        # Datos de oct 2020 a sep 2021 (año hidrológico 2021)
        dates = pd.date_range("2020-10", periods=12, freq="ME")
        series = pd.Series([100] * 12, index=dates)
        result = aggregate_monthly(
            series, method="sum", hydrological_year=True, hydrological_start_month=10
        )

        # Oct 2020 - Sep 2021 -> año hidrológico 2021 (termina en 2021)
        assert len(result) == 1
        assert result.loc[2021] == 1200

    def test_monthly_hydrological_custom_start(self):
        """Agrega usando año hidrológico con inicio en abril."""
        dates = pd.date_range("2020-04", periods=12, freq="ME")
        series = pd.Series([50] * 12, index=dates)
        result = aggregate_monthly(
            series, method="sum", hydrological_year=True, hydrological_start_month=4
        )

        # Abr 2020 - Dic 2020 (meses >= 4) -> año hidrológico 2021 (termina en 2021)
        # Los meses Ene-Mar 2020 no están en los datos
        assert len(result) == 1
        assert result.loc[2021] == 600


class TestAggregateDaily:
    """Tests para la función aggregate_daily."""

    def test_daily_to_annual_max(self):
        """Obtiene máximo anual diario."""
        dates = pd.date_range("2020-01-01", periods=366, freq="D")  # Año bisiesto
        values = [1] * 365 + [100]  # Máximo en último día
        series = pd.Series(values, index=dates)
        result = aggregate_daily(series, target="annual_max")

        assert len(result) == 1
        assert result.loc[2020] == 100

    def test_daily_to_annual_sum(self):
        """Obtiene suma anual diaria."""
        dates = pd.date_range("2020-01-01", periods=365, freq="D")
        series = pd.Series([1] * 365, index=dates)
        result = aggregate_daily(series, target="annual_sum")

        assert len(result) == 1
        assert result.loc[2020] == 365

    def test_daily_to_monthly_mean(self):
        """Obtiene media mensual."""
        dates = pd.date_range("2020-01-01", periods=60, freq="D")  # ~2 meses
        series = pd.Series(range(60), index=dates)
        result = aggregate_daily(series, target="monthly_mean")

        # Enero y febrero (con medias diferentes)
        assert len(result) == 2

    def test_daily_multiple_years(self):
        """Procesa múltiples años."""
        dates = pd.date_range("2020-01-01", periods=730, freq="D")  # 2 años
        # 2020 es bisiesto (366 días), valores 0-365 para 2020 y 366-729 para 2021
        values = list(range(730))
        series = pd.Series(values, index=dates)
        result = aggregate_daily(series, target="annual_max")

        assert len(result) == 2
        # 2020: máximo de 0-365 = 365 (último día del año bisiesto)
        # 2021: máximo de 366-729 = 729
        assert result.loc[2020] == 365
        assert result.loc[2021] == 729


class TestAggregateSubdaily:
    """Tests para la función aggregate_subdaily."""

    def test_hourly_to_annual_max(self):
        """Agrega serie horaria a máximo anual."""
        dates = pd.date_range("2020-01-01", periods=24 * 365, freq="h")
        values = np.random.default_rng(42).random(24 * 365)
        values[1000] = 100.0  # Máximo
        series = pd.Series(values, index=dates)
        result = aggregate_subdaily(series, target="annual_max")

        assert len(result) == 1
        assert result.loc[2020] == 100.0

    def test_hourly_to_daily_max(self):
        """Agrega serie horaria a máximo diario."""
        dates = pd.date_range("2020-01-01", periods=48, freq="h")  # 2 días
        values = [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23,
            24,  # día 1
            5,
            10,
            15,
            20,
            25,
            30,
            35,
            40,
            45,
            50,
            55,
            60,
            65,
            70,
            75,
            80,
            85,
            90,
            95,
            100,
            105,
            110,
            115,
            120,
        ]  # día 2
        series = pd.Series(values, index=dates)
        result = aggregate_subdaily(series, target="daily_max")

        assert len(result) == 2
        assert result.iloc[0] == 24
        assert result.iloc[1] == 120

    def test_minutes_to_daily_sum(self):
        """Agrega serie por minutos a suma diaria."""
        dates = pd.date_range("2020-01-01", periods=1440, freq="min")  # 1 día
        series = pd.Series([1] * 1440, index=dates)
        result = aggregate_subdaily(series, target="daily_sum")

        assert len(result) == 1
        assert result.iloc[0] == 1440

    def test_5min_to_annual_sum(self):
        """Agrega serie de 5 minutos a suma anual."""
        dates = pd.date_range("2020-01-01", periods=100, freq="5min")
        series = pd.Series([1] * 100, index=dates)
        result = aggregate_subdaily(series, target="annual_sum")

        assert len(result) == 1
        assert result.loc[2020] == 100


class TestAutoAggregate:
    """Tests para la función auto_aggregate."""

    def test_bypass_yearly_series(self):
        """Series ya anuales se retornan sin modificar (bypass)."""
        dates = pd.date_range("2020-01-01", periods=3, freq="YS")
        series = pd.Series([100, 200, 150], index=dates)
        result = auto_aggregate(series, target_frequency="yearly")

        # Debería ser copia con metadatos
        assert result._aggregation_bypass is True  # noqa: SLF001
        assert result._original_frequency == "yearly"  # noqa: SLF001
        assert len(result) == 3
        assert list(result.values) == [100, 200, 150]

    def test_bypass_yearly_by_interval(self):
        """Series aproximadamente anuales también hacen bypass."""
        dates = pd.DatetimeIndex(["2020-01-15", "2021-01-20", "2022-01-10"])
        series = pd.Series([100, 200, 150], index=dates)
        result = auto_aggregate(series, target_frequency="yearly")

        assert result._aggregation_bypass is True  # noqa: SLF001

    def test_aggregate_monthly_series(self):
        """Agrega serie mensual correctamente."""
        dates = pd.date_range("2020-01", periods=24, freq="ME")
        series = pd.Series([100] * 24, index=dates)
        result = auto_aggregate(
            series, target_frequency="yearly", aggregation_method="sum"
        )

        assert len(result) == 2
        assert result._aggregation_performed is True  # noqa: SLF001
        assert result._original_frequency == "monthly"  # noqa: SLF001
        assert result._aggregation_method == "sum"  # noqa: SLF001

    def test_aggregate_daily_series(self):
        """Agrega serie diaria correctamente."""
        dates = pd.date_range("2020-01-01", periods=365, freq="D")
        series = pd.Series([1] * 365, index=dates)
        result = auto_aggregate(
            series, target_frequency="yearly", aggregation_method="max"
        )

        assert len(result) == 1
        assert result.loc[2020] == 1
        assert result._aggregation_performed is True  # noqa: SLF001

    def test_aggregate_hourly_series(self):
        """Agrega serie horaria correctamente."""
        dates = pd.date_range("2020-01-01", periods=8760, freq="h")
        series = pd.Series(np.random.default_rng(42).random(8760), index=dates)
        result = auto_aggregate(series, target_frequency="yearly")

        assert len(result) == 1
        assert result._aggregation_performed is True  # noqa: SLF001

    def test_aggregate_with_hydrological_year(self):
        """Agrega usando año hidrológico para series mensuales."""
        dates = pd.date_range("2020-04", periods=12, freq="ME")
        series = pd.Series([50] * 12, index=dates)
        result = auto_aggregate(
            series,
            target_frequency="yearly",
            aggregation_method="sum",
            hydrological_year=True,
            hydrological_start_month=4,
        )

        # Abr-Dic 2020 (meses >= 4) -> año hidrológico 2021
        assert len(result) == 1
        assert result.loc[2021] == 600

    def test_invalid_target_frequency(self):
        """Lanza error si target_frequency no es 'yearly'."""
        dates = pd.date_range("2020-01", periods=12, freq="ME")
        series = pd.Series(range(12), index=dates)

        with pytest.raises(ValueError, match="Solo target_frequency='yearly'"):
            auto_aggregate(series, target_frequency="monthly")

    def test_invalid_index_type(self):
        """Lanza error si la serie no tiene DatetimeIndex."""
        series = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(TypeError, match="DatetimeIndex válido"):
            auto_aggregate(series, target_frequency="yearly")


class TestAggregationMetadata:
    """Tests para verificar metadatos de agregación."""

    def test_yearly_series_has_bypass_flag(self):
        """Series anuales tienen flag de bypass."""
        dates = pd.date_range("2020-01-01", periods=5, freq="YS")
        series = pd.Series([1, 2, 3, 4, 5], index=dates)
        result = auto_aggregate(series)

        assert hasattr(result, "_aggregation_bypass")
        assert result._aggregation_bypass is True  # noqa: SLF001
        assert hasattr(result, "_original_frequency")
        assert result._original_frequency == "yearly"  # noqa: SLF001

    def test_aggregated_series_has_performed_flag(self):
        """Series agregadas tienen flag de performed."""
        dates = pd.date_range("2020-01-01", periods=365, freq="D")
        series = pd.Series(range(365), index=dates)
        result = auto_aggregate(series)

        assert hasattr(result, "_aggregation_performed")
        assert result._aggregation_performed is True  # noqa: SLF001
        assert hasattr(result, "_original_frequency")
        assert result._original_frequency == "daily"  # noqa: SLF001
        assert hasattr(result, "_aggregation_method")


class TestEdgeCases:
    """Tests para casos edge y excepciones."""

    def test_single_value_series(self):
        """Maneja serie con un solo valor - retorna IRREGULAR."""
        dates = pd.DatetimeIndex(["2020-01-01"])
        series = pd.Series([100], index=dates)
        result = auto_aggregate(series)

        # Una sola observación no puede determinar frecuencia
        # Debe manejarse como IRREGULAR y hacer fallback a resample
        assert len(result) == 1
        assert result.iloc[0] == 100

    def test_series_with_gaps(self):
        """Maneja serie con gaps temporales."""
        dates = pd.DatetimeIndex(
            [
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
                "2020-02-01",
                "2020-02-02",  # Gap de ~1 mes
            ]
        )
        series = pd.Series([1, 2, 3, 4, 5], index=dates)
        result = auto_aggregate(series)

        # Debería detectar como irregular y hacer fallback
        assert len(result) >= 1

    def test_empty_series(self):
        """Maneja serie vacía."""
        dates = pd.DatetimeIndex([])
        series = pd.Series([], index=dates, dtype=float)
        result = auto_aggregate(series)

        # Serie vacía retorna serie vacía
        assert len(result) == 0
        assert isinstance(result, pd.Series)

    def test_monthly_aggregation_handles_feb_leap_year(self):
        """Maneja febrero en año bisiesto."""
        dates = pd.date_range("2020-01", periods=24, freq="ME")  # 2020 es bisiesto
        series = pd.Series([100] * 24, index=dates)
        result = aggregate_monthly(series, method="sum")

        assert len(result) == 2
        # 2020 tiene un día extra (366 días)
        assert result.loc[2020] == 1200  # 100 * 12 meses

    def test_aggregate_daily_invalid_target(self):
        """Lanza error para target inválido en aggregate_daily."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        series = pd.Series(range(10), index=dates)

        with pytest.raises(ValueError, match="no soportado"):
            aggregate_daily(series, target="invalid_target")

    def test_aggregate_subdaily_invalid_target(self):
        """Lanza error para target inválido en aggregate_subdaily."""
        dates = pd.date_range("2020-01-01", periods=24, freq="h")
        series = pd.Series(range(24), index=dates)

        with pytest.raises(ValueError, match="no soportado"):
            aggregate_subdaily(series, target="invalid_target")


class TestEnumClasses:
    """Tests para las clases Enum."""

    def test_frequency_type_values(self):
        """Verifica valores de FrequencyType."""
        assert FrequencyType.MINUTES_5.value == "5min"
        assert FrequencyType.MINUTES.value == "minutes"
        assert FrequencyType.HOURLY.value == "hourly"
        assert FrequencyType.DAILY.value == "daily"
        assert FrequencyType.MONTHLY.value == "monthly"
        assert FrequencyType.YEARLY.value == "yearly"
        assert FrequencyType.IRREGULAR.value == "irregular"

    def test_aggregation_method_values(self):
        """Verifica valores de AggregationMethod."""
        assert AggregationMethod.SUM.value == "sum"
        assert AggregationMethod.MEAN.value == "mean"
        assert AggregationMethod.MAX.value == "max"
        assert AggregationMethod.MIN.value == "min"


class TestHydrologicalYearVariations:
    """Tests para variaciones de año hidrológico."""

    def test_hydrological_year_january_start(self):
        """Año hidrológico con inicio en enero (año calendario)."""
        dates = pd.date_range("2020-01", periods=24, freq="ME")
        series = pd.Series([100] * 24, index=dates)
        result = aggregate_monthly(
            series,
            method="sum",
            hydrological_year=True,
            hydrological_start_month=1,
        )

        # Todos los meses >= 1, así que:
        # Ene-Dic 2020 -> año hidrológico 2021
        # Ene-Dic 2021 -> año hidrológico 2022
        assert len(result) == 2
        assert result.loc[2021] == 1200
        assert result.loc[2022] == 1200

    def test_hydrological_year_june_start(self):
        """Año hidrológico con inicio en junio."""
        dates = pd.date_range("2020-01", periods=12, freq="ME")
        series = pd.Series(range(1, 13), index=dates)
        result = aggregate_monthly(
            series,
            method="sum",
            hydrological_year=True,
            hydrological_start_month=6,
        )

        # Ene-Mayo 2020 (meses 1-5 < 6) -> año hidrológico 2020
        # Jun-Dic 2020 (meses 6-12 >= 6) -> año hidrológico 2021
        # Resultado: año 2020 = 1+2+3+4+5 = 15, año 2021 = 6+7+8+9+10+11+12 = 63
        assert len(result) == 2
        assert result.loc[2020] == 15  # 1+2+3+4+5
        assert result.loc[2021] == 63  # 6+7+8+9+10+11+12 (Junio=6 también va a 2021)

    def test_hydrological_year_spanning_multiple_years(self):
        """Año hidrológico que abarca múltiples años calendario."""
        dates = pd.date_range("2019-10", periods=24, freq="ME")
        series = pd.Series([100] * 24, index=dates)
        result = aggregate_monthly(
            series,
            method="sum",
            hydrological_year=True,
            hydrological_start_month=10,
        )

        # Oct 2019 - Sep 2020 (termina en 2020) -> año hidrológico 2020
        # Oct 2020 - Sep 2021 (termina en 2021) -> año hidrológico 2021
        assert len(result) == 2
        assert result.loc[2020] == 1200
        assert result.loc[2021] == 1200
