"""Tests de integración para endpoints POST /validate y POST /validate/file.

Este módulo prueba la capa HTTP de la API, verificando:
    - Validación de series desde JSON (/validate)
    - Validación de series desde archivos CSV/Excel (/validate/file)
    - Manejo de errores (series vacías, datos no numéricos)
    - Advertencias para datos con inconsistencias físicas
    - Equivalencia de resultados entre endpoints JSON y archivo

Fixtures:
    - series_referencia_1.csv y _2.csv: Series de prueba documentadas
    - expected_results.json: Veredictos esperados para validación

Cobertura de casos:
    - Series de referencia (regresión contra tesis)
    - Series vacías (error 400)
    - Series no numéricas (error 422)
    - Series con ceros (advertencia + análisis)
    - Archivos CSV y Excel
"""

import io
import json
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from api.main import app


# Cliente de test para la aplicación FastAPI
client = TestClient(app)

# Ruta a fixtures de prueba
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures"

# Constantes HTTP
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNPROCESSABLE_ENTITY = 422
EXPECTED_WARNING_SERIES_SIZE = 5


def load_expected(series_key: str) -> dict:
    """Carga resultados esperados desde el fixture JSON.

    Args:
        series_key: Clave en expected_results.json ("series_referencia_1" o "_2")

    Returns:
        dict con estructura de resultados esperados para validación.
    """
    with (FIXTURES_PATH / "expected_results.json").open(encoding="utf-8") as fixture:
        return json.load(fixture)[series_key]


def load_reference_series(file_name: str, size: int) -> list[float]:
    """Carga serie numérica desde archivo CSV de fixtures.

    Lee la segunda columna (valores de caudal) y toma los primeros
    'size' valores no nulos.

    Args:
        file_name: Nombre del archivo CSV en fixtures/
        size: Cantidad de valores a retornar

    Returns:
        list[float]: Lista de valores numéricos de la serie.
    """
    dataframe = pd.read_csv(FIXTURES_PATH / file_name)
    return dataframe.iloc[:, 1].dropna().iloc[:size].tolist()


def assert_response_matches_expected(
    payload: dict, expected: dict, series_id: str
) -> None:
    """Helper de aserciones comparando respuesta contra valores esperados.

        Valida que la respuesta de la API coincida con los resultados
    documentados en expected_results.json.

        Args:
            payload: Respuesta JSON de la API
            expected: Diccionario de valores esperados del fixture
            series_id: Identificador esperado de la serie

        Valida:
            - series_id coincide
            - n coincide
            - Sin advertencias (warnings vacío)
            - Veredictos de todos los grupos coinciden
            - Jerarquía aplicada coincide
            - flagged_indices de outliers coincide
    """
    assert payload["series_id"] == series_id
    assert payload["n"] == expected["n"]
    assert payload["warnings"] == []

    independence = payload["validation"]["independence"]
    assert independence["verdict"] == expected["independence"]["resolved_verdict"]
    assert (
        independence["hierarchy_applied"]
        == expected["independence"]["hierarchy_applied"]
    )
    assert (
        independence["anderson"]["verdict"]
        == expected["independence"]["anderson"]["verdict"]
    )
    assert (
        independence["wald_wolfowitz"]["verdict"]
        == expected["independence"]["wald_wolfowitz"]["verdict"]
    )

    homogeneity = payload["validation"]["homogeneity"]
    assert homogeneity["individual_verdicts_only"] is True
    assert (
        homogeneity["helmert"]["verdict"]
        == expected["homogeneity"]["helmert"]["verdict"]
    )
    assert (
        homogeneity["t_student"]["verdict"]
        == expected["homogeneity"]["t_student"]["verdict"]
    )
    assert (
        homogeneity["cramer"]["verdict"] == expected["homogeneity"]["cramer"]["verdict"]
    )

    trend = payload["validation"]["trend"]
    assert (
        trend["mann_kendall"]["verdict"] == expected["trend"]["mann_kendall"]["verdict"]
    )
    assert (
        trend["kolmogorov_smirnov"]["verdict"]
        == expected["trend"]["kolmogorov_smirnov"]["verdict"]
    )

    outliers = payload["validation"]["outliers"]["chow"]
    assert outliers["verdict"] == expected["outliers"]["chow"]["verdict"]
    assert (
        outliers["flagged_indices"] == expected["outliers"]["chow"]["flagged_indices"]
    )


def test_validate_reference_series_1_returns_expected_report():
    """Test de regresión: serie de referencia 1 vía endpoint JSON.

    Carga la serie de referencia 1 desde fixture y la envía al endpoint
    /validate. Verifica que todos los veredictos coincidan con los
    valores documentados en expected_results.json.
    """
    expected = load_expected("series_referencia_1")
    series = load_reference_series("series_referencia_1.csv", size=35)

    response = client.post(
        "/validate",
        json={"series_id": "series_referencia_1", "series": series},
    )

    assert response.status_code == HTTP_OK
    assert_response_matches_expected(
        response.json(), expected, series_id="series_referencia_1"
    )


def test_validate_reference_series_2_returns_expected_report():
    """Test de regresión: serie de referencia 2 vía endpoint JSON.

    Similar al test de referencia 1 pero con la segunda serie documentada.
    """
    expected = load_expected("series_referencia_2")
    series = load_reference_series("series_referencia_2.csv", size=50)

    response = client.post(
        "/validate",
        json={"series_id": "series_referencia_2", "series": series},
    )

    assert response.status_code == HTTP_OK
    assert_response_matches_expected(
        response.json(), expected, series_id="series_referencia_2"
    )


def test_validate_empty_series_returns_400():
    """Test manejo de error: serie vacía debe retornar HTTP 400.

    Verifica que el endpoint rechace series sin datos con error 400
    (Bad Request) en lugar de fallar internamente.
    """
    response = client.post("/validate", json={"series": []})

    assert response.status_code == HTTP_BAD_REQUEST


def test_validate_non_numeric_series_returns_422():
    """Test manejo de error: datos no numéricos deben retornar HTTP 422.

    Verifica que Pydantic/FastAPI validen el tipo de datos y rechacen
    series con strings u otros tipos no numéricos.
    """
    response = client.post("/validate", json={"series": ["a", "b", "c"]})

    assert response.status_code == HTTP_UNPROCESSABLE_ENTITY


def test_validate_series_with_zero_returns_warning_and_analysis():
    """Test de principio de diseño: detectar y advertir, no bloquear.

    Verifica que una serie con valores cero:
        1. Retorna HTTP 200 (no bloquea)
        2. Incluye advertencia ZERO_VALUES
        3. Incluye el análisis completo en "validation"

    Esto demuestra el principio "detectar y advertir, nunca bloquear".
    """
    response = client.post("/validate", json={"series": [4.0, 2.0, 0.0, 3.0, 5.0]})

    assert response.status_code == HTTP_OK
    assert response.json()["n"] == EXPECTED_WARNING_SERIES_SIZE
    warning_codes = {warning["code"] for warning in response.json()["warnings"]}
    assert "ZERO_VALUES" in warning_codes
    assert "validation" in response.json()


def test_validate_file_csv_returns_same_result_as_json_endpoint():
    """Test equivalencia: /validate/file CSV vs /validate JSON.

    Verifica que el endpoint de archivo CSV produzca exactamente los
    mismos resultados que el endpoint JSON para la misma serie.
    """
    expected = load_expected("series_referencia_1")
    series = load_reference_series("series_referencia_1.csv", size=35)
    csv_content = "\n".join(str(value) for value in series).encode("utf-8")

    response = client.post(
        "/validate/file",
        files={
            "file": (
                "series_referencia_1.csv",
                io.BytesIO(csv_content),
                "text/csv",
            )
        },
    )

    assert response.status_code == HTTP_OK
    assert_response_matches_expected(
        response.json(), expected, series_id="series_referencia_1.csv"
    )


def test_validate_file_xlsx_returns_same_result_as_json_endpoint():
    """Test equivalencia: /validate/file Excel vs /validate JSON.

    Verifica que el endpoint de archivo Excel (.xlsx) produzca los
    mismos resultados que el endpoint JSON para la misma serie.
    """
    expected = load_expected("series_referencia_2")
    series = load_reference_series("series_referencia_2.csv", size=50)
    excel_buffer = io.BytesIO()
    pd.DataFrame(series).to_excel(excel_buffer, header=False, index=False)
    excel_buffer.seek(0)

    response = client.post(
        "/validate/file",
        files={
            "file": (
                "series_referencia_2.xlsx",
                excel_buffer,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == HTTP_OK
    assert_response_matches_expected(
        response.json(), expected, series_id="series_referencia_2.xlsx"
    )
