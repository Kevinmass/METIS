"""Tests de integración para endpoints de reports API.

Este módulo prueba los endpoints de la API de reportes SAMHIA
usando TestClient de FastAPI.
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.schemas.reports import (
    BatchFileRequest,
    PDFGenerationRequest,
    SamhiaAnalysisRequest,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def client():
    """Cliente de prueba FastAPI."""
    return TestClient(app)


@pytest.fixture
def sample_analysis_data():
    """Datos de ejemplo para análisis."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=50, freq="D")
    values = np.random.normal(50, 10, 50).tolist()
    dates_str = [d.isoformat() for d in dates]

    return {
        "series_name": "test_variable",
        "reservoir_name": "TestReservoir",
        "data": values,
        "dates": dates_str,
        "alpha": 0.05,
    }


@pytest.fixture
def sample_csv_file(temp_output_dir):
    """Archivo CSV de ejemplo para pruebas de upload."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=50, freq="D")
    values = np.random.normal(50, 10, 50)
    df = pd.DataFrame({"date": dates, "variable1": values, "variable2": values + 5})

    filepath = os.path.join(temp_output_dir, "test_data.csv")
    df.to_csv(filepath, index=False)
    return filepath


@pytest.fixture
def temp_output_dir():
    """Directorio temporal para archivos de prueba."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# TESTS DE ENDPOINT /reports/analyze
# ============================================================================


class TestAnalyzeEndpoint:
    """Tests para POST /reports/analyze."""

    def test_analyze_valid_data(self, client, sample_analysis_data):
        """Analiza datos válidos y retorna resultados."""
        response = client.post("/reports/analyze", json=sample_analysis_data)

        assert response.status_code == 200
        data = response.json()

        assert "series_name" in data
        assert "reservoir_name" in data
        assert "n_data" in data
        assert "descriptive_stats" in data
        assert "independence" in data
        assert "homogeneity" in data
        assert "trend" in data
        assert "outliers" in data
        assert data["series_name"] == "test_variable"
        assert data["reservoir_name"] == "TestReservoir"
        assert data["n_data"] == 50

    def test_analyze_insufficient_data(self, client):
        """Rechaza análisis con menos de 12 datos."""
        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=5, freq="D")
        values = np.random.normal(50, 10, 5).tolist()
        dates_str = [d.isoformat() for d in dates]

        request_data = {
            "series_name": "test_variable",
            "reservoir_name": "TestReservoir",
            "data": values,
            "dates": dates_str,
            "alpha": 0.05,
        }

        response = client.post("/reports/analyze", json=request_data)

        assert response.status_code == 400
        assert "12" in response.json()["detail"]

    def test_analyze_custom_alpha(self, client, sample_analysis_data):
        """Verifica que se use el alpha personalizado."""
        sample_analysis_data["alpha"] = 0.01
        response = client.post("/reports/analyze", json=sample_analysis_data)

        assert response.status_code == 200
        data = response.json()
        # Verificar que el alpha se refleja en los resultados
        assert data["independence"]["anderson"]["alpha"] == 0.01

    def test_analyze_returns_all_test_results(self, client, sample_analysis_data):
        """Verifica que se retornen todos los tests esperados."""
        response = client.post("/reports/analyze", json=sample_analysis_data)

        assert response.status_code == 200
        data = response.json()

        # Independencia: 5 tests
        independence = data["independence"]
        assert "anderson" in independence
        assert "wald_wolfowitz" in independence
        assert "durbin_watson" in independence
        assert "ljung_box" in independence
        assert "spearman" in independence

        # Homogeneidad: 5 tests
        homogeneity = data["homogeneity"]
        assert "helmert" in homogeneity
        assert "t_student" in homogeneity
        assert "cramer" in homogeneity
        assert "mann_whitney" in homogeneity
        assert "mood" in homogeneity

        # Tendencia: 2 tests
        trend = data["trend"]
        assert "mann_kendall" in trend
        assert "kolmogorov_smirnov" in trend

        # Outliers: 2 métodos
        outliers = data["outliers"]
        assert "chow" in outliers
        assert "kn" in outliers


# ============================================================================
# TESTS DE ENDPOINT /reports/pdf
# ============================================================================


class TestPDFEndpoint:
    """Tests para POST /reports/pdf."""

    def test_generate_pdf_valid_data(
        self, client, sample_analysis_data, temp_output_dir
    ):
        """Genera PDF con datos válidos."""
        pdf_path = os.path.join(temp_output_dir, "test.pdf")

        request_data = {
            "series_name": "test_variable",
            "reservoir_name": "TestReservoir",
            "data": sample_analysis_data["data"],
            "dates": sample_analysis_data["dates"],
            "output_path": pdf_path,
            "alpha": 0.05,
        }

        response = client.post("/reports/pdf", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["pdf_path"] == pdf_path
        assert os.path.exists(pdf_path)

    def test_generate_pdf_custom_config(
        self, client, sample_analysis_data, temp_output_dir
    ):
        """Genera PDF con configuración personalizada."""
        pdf_path = os.path.join(temp_output_dir, "test_custom.pdf")

        request_data = {
            "series_name": "test_variable",
            "reservoir_name": "TestReservoir",
            "data": sample_analysis_data["data"],
            "dates": sample_analysis_data["dates"],
            "output_path": pdf_path,
            "alpha": 0.01,
            "institution": "Custom Institution",
            "report_type": "Custom Report",
            "author": "Custom Author",
        }

        response = client.post("/reports/pdf", json=request_data)

        assert response.status_code == 200
        assert os.path.exists(pdf_path)

    def test_generate_pdf_insufficient_data(self, client, temp_output_dir):
        """Rechaza generación con menos de 12 datos."""
        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=5, freq="D")
        values = np.random.normal(50, 10, 5).tolist()
        dates_str = [d.isoformat() for d in dates]
        pdf_path = os.path.join(temp_output_dir, "test_error.pdf")

        request_data = {
            "series_name": "test_variable",
            "reservoir_name": "TestReservoir",
            "data": values,
            "dates": dates_str,
            "output_path": pdf_path,
        }

        response = client.post("/reports/pdf", json=request_data)

        assert response.status_code == 500
        assert "12" in response.json()["detail"]


# ============================================================================
# TESTS DE ENDPOINT /reports/download
# ============================================================================


class TestDownloadEndpoint:
    """Tests para GET /reports/download/{filename}."""

    def test_download_existing_pdf(self, client, temp_output_dir):
        """Descarga un PDF existente."""
        # Crear un PDF de prueba
        pdf_path = os.path.join(temp_output_dir, "test.pdf")
        with open(pdf_path, "w") as f:
            f.write("fake pdf content")

        response = client.get(f"/reports/download/{pdf_path}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_download_nonexistent_pdf(self, client, temp_output_dir):
        """Intenta descargar un PDF inexistente."""
        pdf_path = os.path.join(temp_output_dir, "nonexistent.pdf")

        response = client.get(f"/reports/download/{pdf_path}")

        assert response.status_code == 404


# ============================================================================
# TESTS DE ENDPOINT /reports/batch
# ============================================================================


class TestBatchEndpoint:
    """Tests para POST /reports/batch."""

    def test_process_batch_valid_files(self, client, sample_csv_file, temp_output_dir):
        """Procesa múltiples archivos en batch."""
        request_data = {
            "files": [sample_csv_file],
            "output_dir": temp_output_dir,
            "alpha": 0.05,
        }

        response = client.post("/reports/batch", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "total_files" in data
        assert "successful" in data
        assert "failed" in data
        assert "results" in data
        assert data["total_files"] == 1

    def test_process_batch_nonexistent_file(self, client, temp_output_dir):
        """Procesa archivo inexistente."""
        request_data = {
            "files": ["/nonexistent/file.csv"],
            "output_dir": temp_output_dir,
            "alpha": 0.05,
        }

        response = client.post("/reports/batch", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["total_files"] == 1
        assert data["failed"] == 1
        assert data["results"][0]["status"] == "error"


# ============================================================================
# TESTS DE ENDPOINT /reports/upload
# ============================================================================


class TestUploadEndpoint:
    """Tests para POST /reports/upload."""

    def test_upload_csv_file(self, client, sample_csv_file):
        """Sube un archivo CSV y detecta variables."""
        with open(sample_csv_file, "rb") as f:
            files = {"file": ("test.csv", f, "text/csv")}
            params = {"reservoir_name": "TestReservoir", "alpha": "0.05"}

            response = client.post("/reports/upload", files=files, params=params)

        assert response.status_code == 200
        data = response.json()

        assert "filename" in data
        assert "variables_detected" in data
        assert "n_variables" in data
        assert "n_rows" in data
        assert data["n_variables"] >= 1

    def test_upload_excel_file(self, client, temp_output_dir):
        """Sube un archivo Excel y detecta variables."""
        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=50, freq="D")
        values = np.random.normal(50, 10, 50)
        df = pd.DataFrame({"date": dates, "variable1": values, "variable2": values + 5})

        filepath = os.path.join(temp_output_dir, "test_data.xlsx")
        df.to_excel(filepath, index=False)

        with open(filepath, "rb") as f:
            files = {
                "file": (
                    "test.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            }
            params = {"reservoir_name": "TestReservoir"}

            response = client.post("/reports/upload", files=files, params=params)

        assert response.status_code == 200
        data = response.json()

        assert data["filename"] == "test.xlsx"
        assert data["n_variables"] >= 1


# ============================================================================
# TESTS DE SCHEMAS
# ============================================================================


class TestSchemas:
    """Tests para schemas Pydantic."""

    def test_samhia_analysis_request_validation(self):
        """Valida schema de solicitud de análisis."""
        request = SamhiaAnalysisRequest(
            series_name="test_var",
            reservoir_name="TestRes",
            data=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            dates=[
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
                "2020-01-04",
                "2020-01-05",
                "2020-01-06",
                "2020-01-07",
                "2020-01-08",
                "2020-01-09",
                "2020-01-10",
                "2020-01-11",
                "2020-01-12",
            ],
            alpha=0.05,
        )

        assert request.series_name == "test_var"
        assert request.alpha == 0.05
        assert len(request.data) == 12

    def test_pdf_generation_request_validation(self):
        """Valida schema de solicitud de PDF."""
        request = PDFGenerationRequest(
            series_name="test_var",
            reservoir_name="TestRes",
            data=[1, 2, 3, 4, 5],
            dates=[
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
                "2020-01-04",
                "2020-01-05",
            ],
            output_path="/tmp/test.pdf",
        )

        assert request.series_name == "test_var"
        assert request.output_path == "/tmp/test.pdf"
        assert request.alpha == 0.05  # Default

    def test_batch_file_request_validation(self):
        """Valida schema de solicitud batch."""
        request = BatchFileRequest(
            files=["/path/to/file1.csv", "/path/to/file2.xlsx"],
            output_dir="/tmp/output",
            alpha=0.01,
        )

        assert len(request.files) == 2
        assert request.output_dir == "/tmp/output"
        assert request.alpha == 0.01
