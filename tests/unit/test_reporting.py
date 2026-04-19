"""Tests unitarios para el módulo de reportes.

Este módulo prueba las funciones de visualización y generación de PDFs
del módulo core/reporting.
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from core.reporting.pdf_generator import (
    ReportConfig,
    generate_samhia_report_pdf,
)
from core.reporting.plots import (
    plot_acf,
    plot_annual_boxplots,
    plot_calendar_facets,
    plot_histogram_normal,
    plot_hydrological_facets,
    plot_monthly_boxplots,
    plot_outliers,
    plot_qq,
    plot_time_series,
)
from core.reporting.styles import (
    DEFAULT_FIGURE_CONFIG,
    DEFAULT_PDF_CONFIG,
    DEFAULT_PLOT_STYLE,
    get_y_range,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_dataframe():
    """DataFrame de ejemplo con datos temporales."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
    values = np.random.normal(50, 10, 100)
    return pd.DataFrame({"date": dates, "variable": values})


@pytest.fixture
def sample_dataframe_with_outliers(sample_dataframe):
    """DataFrame con outliers."""
    df = sample_dataframe.copy()
    df.loc[10, "variable"] = 200  # Outlier
    df.loc[50, "variable"] = -100  # Outlier
    return df


@pytest.fixture
def temp_output_dir():
    """Directorio temporal para archivos de prueba."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# TESTS DE UTILIDADES
# ============================================================================


class TestGetYRange:
    """Tests para función get_y_range."""

    def test_y_range_positive_values(self):
        """Valores positivos → rango desde 0."""
        values = np.array([10, 20, 30, 40, 50])
        y_min, y_max = get_y_range(values)

        assert y_min == 0
        assert y_max > 50  # Debe ser mayor que el máximo

    def test_y_range_negative_values(self):
        """Valores negativos → rango simétrico."""
        values = np.array([-50, -30, -20, -10, -5])
        y_min, y_max = get_y_range(values)

        assert y_min < -50  # Debe ser menor que el mínimo
        assert y_max > 0  # Debe incluir valores positivos

    def test_y_range_mixed_values(self):
        """Valores mixtos → rango simétrico alrededor de 0."""
        values = np.array([-30, -10, 0, 10, 30])
        y_min, y_max = get_y_range(values)

        assert y_min < -30
        assert y_max > 30
        assert abs(y_min) == abs(y_max)  # Rango simétrico alrededor de 0


# ============================================================================
# TESTS DE PLOTTING
# ============================================================================


class TestPlotTimeSeries:
    """Tests para plot_time_series."""

    def test_plot_time_series_creates_figure(self, sample_dataframe, temp_output_dir):
        """Verifica que se cree una figura matplotlib."""
        output_path = os.path.join(temp_output_dir, "test_ts.png")
        fig = plot_time_series(
            sample_dataframe,
            "date",
            "variable",
            title="Test",
            y_label="Value",
            output_path=output_path,
        )

        assert fig is not None
        assert os.path.exists(output_path)

    def test_plot_time_series_without_output(self, sample_dataframe):
        """Verifica que funcione sin guardar archivo."""
        fig = plot_time_series(
            sample_dataframe,
            "date",
            "variable",
            output_path=None,
        )

        assert fig is not None

    def test_plot_time_series_with_loess(self, sample_dataframe, temp_output_dir):
        """Verifica que se agregue LOESS cuando se solicita."""
        output_path = os.path.join(temp_output_dir, "test_loess.png")
        fig = plot_time_series(
            sample_dataframe,
            "date",
            "variable",
            add_loess=True,
            output_path=output_path,
        )

        assert fig is not None
        assert os.path.exists(output_path)


class TestPlotCalendarFacets:
    """Tests para plot_calendar_facets."""

    def test_plot_calendar_facets_creates_figure(
        self, sample_dataframe, temp_output_dir
    ):
        """Verifica que se cree una figura con facets."""
        output_path = os.path.join(temp_output_dir, "test_calendar.png")
        fig = plot_calendar_facets(
            sample_dataframe,
            "date",
            "variable",
            output_path=output_path,
        )

        assert fig is not None
        assert os.path.exists(output_path)


class TestPlotHydrologicalFacets:
    """Tests para plot_hydrological_facets."""

    def test_plot_hydrological_facets_creates_figure(
        self, sample_dataframe, temp_output_dir
    ):
        """Verifica que se cree una figura con facets hidrológicos."""
        output_path = os.path.join(temp_output_dir, "test_hydro.png")
        fig = plot_hydrological_facets(
            sample_dataframe,
            "date",
            "variable",
            output_path=output_path,
        )

        assert fig is not None
        assert os.path.exists(output_path)


class TestPlotOutliers:
    """Tests para plot_outliers."""

    def test_plot_outliers_creates_figure(
        self, sample_dataframe_with_outliers, temp_output_dir
    ):
        """Verifica que se cree una figura con outliers marcados."""
        output_path = os.path.join(temp_output_dir, "test_outliers.png")
        fig = plot_outliers(
            sample_dataframe_with_outliers,
            "date",
            "variable",
            lower_limit=20,
            upper_limit=80,
            output_path=output_path,
        )

        assert fig is not None
        assert os.path.exists(output_path)

    def test_plot_outliers_without_outliers(self, sample_dataframe, temp_output_dir):
        """Verifica que funcione sin outliers."""
        output_path = os.path.join(temp_output_dir, "test_no_outliers.png")
        fig = plot_outliers(
            sample_dataframe,
            "date",
            "variable",
            lower_limit=20,
            upper_limit=80,
            output_path=output_path,
        )

        assert fig is not None
        assert os.path.exists(output_path)


class TestPlotMonthlyBoxplots:
    """Tests para plot_monthly_boxplots."""

    def test_plot_monthly_boxplots_calendar(self, sample_dataframe, temp_output_dir):
        """Verifica boxplots mensuales calendario."""
        sample_dataframe["month"] = sample_dataframe["date"].dt.month
        output_path = os.path.join(temp_output_dir, "test_monthly_cal.png")
        fig = plot_monthly_boxplots(
            sample_dataframe,
            "variable",
            month_col="month",
            hydrological=False,
            output_path=output_path,
        )

        assert fig is not None
        assert os.path.exists(output_path)

    def test_plot_monthly_boxplots_hydrological(
        self, sample_dataframe, temp_output_dir
    ):
        """Verifica boxplots mensuales hidrológicos."""
        sample_dataframe["month"] = sample_dataframe["date"].dt.month
        output_path = os.path.join(temp_output_dir, "test_monthly_hydro.png")
        fig = plot_monthly_boxplots(
            sample_dataframe,
            "variable",
            month_col="month",
            hydrological=True,
            output_path=output_path,
        )

        assert fig is not None
        assert os.path.exists(output_path)


class TestPlotAnnualBoxplots:
    """Tests para plot_annual_boxplots."""

    def test_plot_annual_boxplots_creates_figure(
        self, sample_dataframe, temp_output_dir
    ):
        """Verifica que se cree figura con boxplots anuales."""
        sample_dataframe["date"] = pd.to_datetime(sample_dataframe["date"])
        output_path = os.path.join(temp_output_dir, "test_annual.png")
        fig = plot_annual_boxplots(
            sample_dataframe,
            "variable",
            output_path=output_path,
        )

        assert fig is not None
        assert os.path.exists(output_path)


class TestPlotHistogramNormal:
    """Tests para plot_histogram_normal."""

    def test_plot_histogram_normal_creates_figure(
        self, sample_dataframe, temp_output_dir
    ):
        """Verifica que se cree figura con histograma y curva normal."""
        output_path = os.path.join(temp_output_dir, "test_hist.png")
        series = pd.Series(sample_dataframe["variable"])
        fig = plot_histogram_normal(series, output_path=output_path)

        assert fig is not None
        assert os.path.exists(output_path)


class TestPlotQQ:
    """Tests para plot_qq."""

    def test_plot_qq_creates_figure(self, sample_dataframe, temp_output_dir):
        """Verifica que se cree figura con QQ plot."""
        output_path = os.path.join(temp_output_dir, "test_qq.png")
        series = pd.Series(sample_dataframe["variable"])
        fig = plot_qq(series, output_path=output_path)

        assert fig is not None
        assert os.path.exists(output_path)


class TestPlotACF:
    """Tests para plot_acf."""

    def test_plot_acf_creates_figure(self, sample_dataframe, temp_output_dir):
        """Verifica que se cree figura con ACF."""
        output_path = os.path.join(temp_output_dir, "test_acf.png")
        series = pd.Series(sample_dataframe["variable"])
        fig = plot_acf(series, output_path=output_path)

        assert fig is not None
        assert os.path.exists(output_path)

    def test_plot_acf_custom_lags(self, sample_dataframe, temp_output_dir):
        """Verifica que se respete el parámetro lags."""
        output_path = os.path.join(temp_output_dir, "test_acf_lags.png")
        series = pd.Series(sample_dataframe["variable"])
        fig = plot_acf(series, lags=20, output_path=output_path)

        assert fig is not None
        assert os.path.exists(output_path)


# ============================================================================
# TESTS DE GENERACIÓN DE PDF
# ============================================================================


class TestReportConfig:
    """Tests para ReportConfig."""

    def test_report_config_creation(self):
        """Verifica creación de ReportConfig."""
        config = ReportConfig(
            series_name="test_var",
            reservoir_name="test_reservoir",
            output_path="/tmp/test.pdf",
        )

        assert config.series_name == "test_var"
        assert config.reservoir_name == "test_reservoir"
        assert config.output_path == "/tmp/test.pdf"
        assert config.alpha == 0.05

    def test_report_config_custom_params(self):
        """Verifica parámetros personalizados de ReportConfig."""
        config = ReportConfig(
            series_name="test_var",
            reservoir_name="test_reservoir",
            output_path="/tmp/test.pdf",
            alpha=0.01,
            institution="Custom Institution",
            report_type="Custom Report",
            author="Custom Author",
        )

        assert config.alpha == 0.01
        assert config.institution == "Custom Institution"
        assert config.report_type == "Custom Report"
        assert config.author == "Custom Author"


class TestGenerateSamhiaReportPDF:
    """Tests para generate_samhia_report_pdf."""

    def test_generate_pdf_creates_file(self, sample_dataframe, temp_output_dir):
        """Verifica que se cree el archivo PDF."""
        output_path = os.path.join(temp_output_dir, "test_report.pdf")
        config = ReportConfig(
            series_name="variable",
            reservoir_name="TestReservoir",
            output_path=output_path,
        )

        pdf_path = generate_samhia_report_pdf(sample_dataframe, config)

        assert os.path.exists(pdf_path)
        assert pdf_path == output_path

    def test_generate_pdf_with_insufficient_data(self, temp_output_dir):
        """Verifica error con menos de 12 datos."""
        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=5, freq="D")
        values = np.random.normal(50, 10, 5)
        df = pd.DataFrame({"date": dates, "variable": values})

        output_path = os.path.join(temp_output_dir, "test_report_error.pdf")
        config = ReportConfig(
            series_name="variable",
            reservoir_name="TestReservoir",
            output_path=output_path,
        )

        with pytest.raises(ValueError, match="menos de 12 datos"):
            generate_samhia_report_pdf(df, config)

    def test_generate_pdf_custom_config(self, sample_dataframe, temp_output_dir):
        """Verifica que se use configuración personalizada."""
        output_path = os.path.join(temp_output_dir, "test_custom.pdf")
        config = ReportConfig(
            series_name="variable",
            reservoir_name="TestReservoir",
            output_path=output_path,
            institution="Custom Inst",
            report_type="Custom Type",
            author="Custom Author",
            alpha=0.01,
        )

        pdf_path = generate_samhia_report_pdf(sample_dataframe, config)

        assert os.path.exists(pdf_path)

    def test_generate_pdf_creates_parent_directory(
        self, sample_dataframe, temp_output_dir
    ):
        """Verifica que se cree el directorio padre si no existe."""
        nested_path = os.path.join(temp_output_dir, "nested", "dir", "test.pdf")
        config = ReportConfig(
            series_name="variable",
            reservoir_name="TestReservoir",
            output_path=nested_path,
        )

        pdf_path = generate_samhia_report_pdf(sample_dataframe, config)

        assert os.path.exists(pdf_path)
        assert os.path.exists(os.path.dirname(pdf_path))


# ============================================================================
# TESTS DE CONFIGURACIÓN
# ============================================================================


class TestDefaultConfigs:
    """Tests para configuraciones por defecto."""

    def test_default_figure_config(self):
        """Verifica configuración por defecto de figuras."""
        assert DEFAULT_FIGURE_CONFIG.figsize == (10, 6)
        assert DEFAULT_FIGURE_CONFIG.dpi == 100
        assert DEFAULT_FIGURE_CONFIG.facecolor == "white"

    def test_default_plot_style(self):
        """Verifica estilo por defecto de plots."""
        assert DEFAULT_PLOT_STYLE.linewidth == 0.8
        assert DEFAULT_PLOT_STYLE.alpha_fill == 0.5
        assert DEFAULT_PLOT_STYLE.marker_size == 10

    def test_default_pdf_config(self):
        """Verifica configuración por defecto de PDF."""
        assert DEFAULT_PDF_CONFIG.figsize_pdf == (14, 8)
        assert DEFAULT_PDF_CONFIG.title_fontsize == 24
        assert (
            DEFAULT_PDF_CONFIG.institution == "METIS - Sistema de Análisis Hidrológico"
        )
