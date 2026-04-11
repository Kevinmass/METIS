import io
import json
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures"
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNPROCESSABLE_ENTITY = 422
EXPECTED_WARNING_SERIES_SIZE = 5


def load_expected(series_key: str) -> dict:
    with (FIXTURES_PATH / "expected_results.json").open(encoding="utf-8") as fixture:
        return json.load(fixture)[series_key]


def load_reference_series(file_name: str, size: int) -> list[float]:
    dataframe = pd.read_csv(FIXTURES_PATH / file_name)
    return dataframe.iloc[:, 1].dropna().iloc[:size].tolist()


def assert_response_matches_expected(
    payload: dict, expected: dict, series_id: str
) -> None:
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
    response = client.post("/validate", json={"series": []})

    assert response.status_code == HTTP_BAD_REQUEST


def test_validate_non_numeric_series_returns_422():
    response = client.post("/validate", json={"series": ["a", "b", "c"]})

    assert response.status_code == HTTP_UNPROCESSABLE_ENTITY


def test_validate_series_with_zero_returns_warning_and_analysis():
    response = client.post("/validate", json={"series": [4.0, 2.0, 0.0, 3.0, 5.0]})

    assert response.status_code == HTTP_OK
    assert response.json()["n"] == EXPECTED_WARNING_SERIES_SIZE
    warning_codes = {warning["code"] for warning in response.json()["warnings"]}
    assert "ZERO_VALUES" in warning_codes
    assert "validation" in response.json()


def test_validate_file_csv_returns_same_result_as_json_endpoint():
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
