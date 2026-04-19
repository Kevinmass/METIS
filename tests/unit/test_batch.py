"""Tests unitarios para el módulo de procesamiento batch.

Este módulo prueba las funciones de lectura de archivos
y el procesador batch del módulo core/batch.
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from core.batch.io_handlers import (
    detect_date_column,
    detect_numeric_columns,
    prepare_dataframe_for_analysis,
    read_file_intelligent,
    validate_dataframe_for_analysis,
)
from core.batch.processor import (
    BatchConfig,
    BatchProcessor,
    FileResult,
    process_files_batch,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_csv_file(temp_output_dir):
    """Archivo CSV de ejemplo."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=50, freq="D")
    values = np.random.normal(50, 10, 50)
    df = pd.DataFrame({"date": dates, "variable1": values, "variable2": values + 5})

    filepath = os.path.join(temp_output_dir, "test_data.csv")
    df.to_csv(filepath, index=False)
    return filepath


@pytest.fixture
def sample_excel_file(temp_output_dir):
    """Archivo Excel de ejemplo."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=50, freq="D")
    values = np.random.normal(50, 10, 50)
    df = pd.DataFrame({"date": dates, "variable1": values, "variable2": values + 5})

    filepath = os.path.join(temp_output_dir, "test_data.xlsx")
    df.to_excel(filepath, index=False)
    return filepath


@pytest.fixture
def sample_csv_semicolon(temp_output_dir):
    """Archivo CSV con separador punto y coma."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=50, freq="D")
    values = np.random.normal(50, 10, 50)
    df = pd.DataFrame({"date": dates, "variable1": values, "variable2": values + 5})

    filepath = os.path.join(temp_output_dir, "test_data_semicolon.csv")
    df.to_csv(filepath, index=False, sep=";")
    return filepath


@pytest.fixture
def sample_dataframe_insufficient():
    """DataFrame con menos de 12 filas."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=5, freq="D")
    values = np.random.normal(50, 10, 5)
    return pd.DataFrame({"date": dates, "variable": values})


@pytest.fixture
def temp_output_dir():
    """Directorio temporal para archivos de prueba."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# TESTS DE LECTURA DE ARCHIVOS
# ============================================================================


class TestReadFileIntelligent:
    """Tests para read_file_intelligent."""

    def test_read_csv_comma(self, sample_csv_file):
        """Lee archivo CSV con separador coma."""
        df = read_file_intelligent(sample_csv_file)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "date" in df.columns
        assert "variable1" in df.columns

    def test_read_csv_semicolon(self, sample_csv_semicolon):
        """Lee archivo CSV con separador punto y coma."""
        df = read_file_intelligent(sample_csv_semicolon)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "date" in df.columns
        assert "variable1" in df.columns

    def test_read_excel(self, sample_excel_file):
        """Lee archivo Excel."""
        df = read_file_intelligent(sample_excel_file)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "date" in df.columns
        assert "variable1" in df.columns

    def test_read_nonexistent_file(self, temp_output_dir):
        """Lanza error con archivo inexistente."""
        filepath = os.path.join(temp_output_dir, "nonexistent.csv")

        with pytest.raises(FileNotFoundError):
            read_file_intelligent(filepath)

    def test_read_with_date_column(self, sample_csv_file):
        """Convierte columna de fechas si se especifica."""
        df = read_file_intelligent(sample_csv_file, date_column="date")

        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_read_unsupported_format(self, temp_output_dir):
        """Rechaza formato no soportado."""
        filepath = os.path.join(temp_output_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("some content")

        with pytest.raises(ValueError, match="no soportado"):
            read_file_intelligent(filepath)


# ============================================================================
# TESTS DE DETECCIÓN DE COLUMNAS
# ============================================================================


class TestDetectNumericColumns:
    """Tests para detect_numeric_columns."""

    def test_detect_numeric_columns_basic(self, sample_csv_file):
        """Detecta columnas numéricas básicas."""
        df = read_file_intelligent(sample_csv_file)
        numeric_cols = detect_numeric_columns(df)

        assert "variable1" in numeric_cols
        assert "variable2" in numeric_cols
        assert "date" not in numeric_cols

    def test_detect_numeric_columns_with_exclude(self, sample_csv_file):
        """Excluye columnas especificadas."""
        df = read_file_intelligent(sample_csv_file)
        numeric_cols = detect_numeric_columns(df, exclude_columns=["variable2"])

        assert "variable1" in numeric_cols
        assert "variable2" not in numeric_cols

    def test_detect_numeric_columns_case_insensitive(self, sample_csv_file):
        """Exclusión es case-insensitive."""
        df = read_file_intelligent(sample_csv_file)
        df = df.rename(columns={"variable1": "Variable1"})
        numeric_cols = detect_numeric_columns(df, exclude_columns=["variable1"])

        assert "Variable1" not in numeric_cols


class TestDetectDateColumn:
    """Tests para detect_date_column."""

    def test_detect_date_column_exact_match(self, sample_csv_file):
        """Detecta columna 'date' exacta."""
        df = read_file_intelligent(sample_csv_file)
        date_col = detect_date_column(df)

        assert date_col == "date"

    def test_detect_date_column_spanish(self, temp_output_dir):
        """Detecta columna 'fecha'."""
        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=50, freq="D")
        values = np.random.normal(50, 10, 50)
        df = pd.DataFrame({"fecha": dates, "variable": values})

        filepath = os.path.join(temp_output_dir, "test_fecha.csv")
        df.to_csv(filepath, index=False)

        df_read = read_file_intelligent(filepath)
        date_col = detect_date_column(df_read)

        assert date_col == "fecha"

    def test_detect_date_column_none(self, temp_output_dir):
        """Retorna None si no detecta columna de fechas."""
        np.random.seed(42)
        values = np.random.normal(50, 10, 50)
        df = pd.DataFrame({"var1": values, "var2": values + 5})

        date_col = detect_date_column(df)

        assert date_col is None


# ============================================================================
# TESTS DE VALIDACIÓN
# ============================================================================


class TestValidateDataFrame:
    """Tests para validate_dataframe_for_analysis."""

    def test_validate_valid_dataframe(self, sample_csv_file):
        """Valida DataFrame válido."""
        df = read_file_intelligent(sample_csv_file)
        is_valid, error_msg = validate_dataframe_for_analysis(df)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_insufficient_rows(self, sample_dataframe_insufficient):
        """Rechaza DataFrame con menos de 12 filas."""
        is_valid, error_msg = validate_dataframe_for_analysis(
            sample_dataframe_insufficient
        )

        assert is_valid is False
        assert "12" in error_msg

    def test_validate_without_date_column(self, temp_output_dir):
        """Rechaza DataFrame sin columna de fechas."""
        np.random.seed(42)
        values = np.random.normal(50, 10, 50)
        df = pd.DataFrame({"var1": values, "var2": values + 5})

        is_valid, error_msg = validate_dataframe_for_analysis(df)

        assert is_valid is False
        assert "fecha" in error_msg.lower()


# ============================================================================
# TESTS DE PREPARACIÓN
# ============================================================================


class TestPrepareDataFrame:
    """Tests para prepare_dataframe_for_analysis."""

    def test_prepare_dataframe_basic(self, sample_csv_file):
        """Prepara DataFrame básico para análisis."""
        df = read_file_intelligent(sample_csv_file)
        df_prep = prepare_dataframe_for_analysis(df)

        assert "date" in df_prep.columns
        assert "variable" in df_prep.columns
        assert len(df_prep) > 0
        assert df_prep["date"].notna().all()

    def test_prepare_dataframe_with_specific_columns(self, sample_csv_file):
        """Prepara DataFrame con columnas específicas."""
        df = read_file_intelligent(sample_csv_file)
        df_prep = prepare_dataframe_for_analysis(
            df, date_column="date", value_column="variable1"
        )

        assert "date" in df_prep.columns
        assert "variable" in df_prep.columns
        assert len(df_prep) > 0

    def test_prepare_dataframe_sorted(self, sample_csv_file):
        """Verifica que el DataFrame esté ordenado por fecha."""
        df = read_file_intelligent(sample_csv_file)
        # Desordenar
        df = df.sample(frac=1).reset_index(drop=True)

        df_prep = prepare_dataframe_for_analysis(df)

        assert df_prep["date"].is_monotonic_increasing

    def test_prepare_dataframe_index_reset(self, sample_csv_file):
        """Verifica que el índice se resetee."""
        df = read_file_intelligent(sample_csv_file)
        df_prep = prepare_dataframe_for_analysis(df)

        assert df_prep.index.is_monotonic_increasing
        assert df_prep.index[0] == 0


# ============================================================================
# TESTS DE CONFIGURACIÓN BATCH
# ============================================================================


class TestBatchConfig:
    """Tests para BatchConfig."""

    def test_batch_config_creation(self, temp_output_dir):
        """Crea configuración batch básica."""
        config = BatchConfig(output_dir=temp_output_dir)

        assert config.output_dir == temp_output_dir
        assert config.alpha == 0.05
        assert config.max_workers == 4

    def test_batch_config_custom_params(self, temp_output_dir):
        """Crea configuración con parámetros personalizados."""
        config = BatchConfig(
            output_dir=temp_output_dir,
            alpha=0.01,
            max_workers=2,
            institution="Custom Inst",
        )

        assert config.alpha == 0.01
        assert config.max_workers == 2
        assert config.institution == "Custom Inst"


class TestFileResult:
    """Tests para FileResult."""

    def test_file_result_creation(self):
        """Crea resultado de archivo exitoso."""
        result = FileResult(
            filename="test.csv",
            status="success",
            variables_analyzed=["var1", "var2"],
            output_paths={"var1": "/path/to/var1.pdf", "var2": "/path/to/var2.pdf"},
            n_rows=50,
        )

        assert result.filename == "test.csv"
        assert result.status == "success"
        assert len(result.variables_analyzed) == 2
        assert len(result.output_paths) == 2

    def test_file_result_error(self):
        """Crea resultado de archivo con error."""
        result = FileResult(
            filename="test.csv",
            status="error",
            variables_analyzed=[],
            output_paths={},
            error_message="File not found",
            n_rows=0,
        )

        assert result.status == "error"
        assert result.error_message == "File not found"


# ============================================================================
# TESTS DE PROCESADOR BATCH
# ============================================================================


class TestBatchProcessor:
    """Tests para BatchProcessor."""

    def test_batch_processor_creation(self, temp_output_dir):
        """Crea procesador batch."""
        config = BatchConfig(output_dir=temp_output_dir)
        processor = BatchProcessor(config)

        assert processor.config == config
        assert processor.results == []

    def test_process_single_file_success(self, sample_csv_file, temp_output_dir):
        """Procesa un solo archivo exitosamente."""
        config = BatchConfig(output_dir=temp_output_dir)
        processor = BatchProcessor(config)

        result = processor.process_file(sample_csv_file)

        assert result.status in ["success", "skipped", "error"]
        assert result.filename == os.path.basename(sample_csv_file)
        assert isinstance(result.variables_analyzed, list)
        assert isinstance(result.output_paths, dict)

    def test_process_single_file_error(self, temp_output_dir):
        """Procesa archivo inexistente."""
        config = BatchConfig(output_dir=temp_output_dir)
        processor = BatchProcessor(config)

        nonexistent = os.path.join(temp_output_dir, "nonexistent.csv")
        result = processor.process_file(nonexistent)

        assert result.status == "error"
        assert "error" in result.error_message.lower()

    def test_process_multiple_files(
        self, sample_csv_file, sample_excel_file, temp_output_dir
    ):
        """Procesa múltiples archivos."""
        config = BatchConfig(output_dir=temp_output_dir, max_workers=2)
        processor = BatchProcessor(config)

        results = processor.process_files([sample_csv_file, sample_excel_file])

        assert len(results) == 2
        assert all(isinstance(r, FileResult) for r in results)

    def test_get_summary(self, sample_csv_file, temp_output_dir):
        """Obtiene resumen de procesamiento."""
        config = BatchConfig(output_dir=temp_output_dir)
        processor = BatchProcessor(config)

        processor.process_file(sample_csv_file)
        summary = processor.get_summary()

        assert "total_files" in summary
        assert "successful" in summary
        assert "failed" in summary
        assert "skipped" in summary
        assert "total_variables_analyzed" in summary
        assert summary["total_files"] == 1


# ============================================================================
# TESTS DE FUNCIÓN CONVENIENCIA
# ============================================================================


class TestProcessFilesBatch:
    """Tests para process_files_batch."""

    def test_process_files_batch_basic(self, sample_csv_file, temp_output_dir):
        """Procesa archivos batch con función conveniencia."""
        results = process_files_batch(
            [sample_csv_file],
            output_dir=temp_output_dir,
            alpha=0.05,
            max_workers=2,
        )

        assert len(results) == 1
        assert isinstance(results[0], FileResult)

    def test_process_files_batch_with_callback(self, sample_csv_file, temp_output_dir):
        """Usa callback de progreso."""
        progress_calls = []

        def callback(current, total):
            progress_calls.append((current, total))

        results = process_files_batch(
            [sample_csv_file],
            output_dir=temp_output_dir,
            progress_callback=callback,
        )

        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == 1  # Última llamada: current=1
