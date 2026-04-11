import json
from pathlib import Path

import pandas as pd

from core.validation import run_validation_pipeline


STATISTIC_COMPARISON_TOLERANCE = 1e-2


def test_series_referencia_1():
    """Prueba completa contra serie referencia 1"""
    """todos los resultados deben coincidir exactamente"""
    fixtures_path = Path(__file__).parent.parent / "fixtures"

    with (fixtures_path / "expected_results.json").open() as f:
        expected = json.load(f)["series_referencia_1"]

    # Cargar serie de referencia (tomar solo la columna numérica de caudal)
    df = pd.read_csv(fixtures_path / "series_referencia_1.csv")
    serie = df.iloc[:, 1].squeeze().dropna().iloc[:35]

    report = run_validation_pipeline(serie)

    # Validar campos básicos
    assert report.n == expected["n"]

    # Validar Independencia
    assert (
        report.independence.resolved_verdict
        == expected["independence"]["resolved_verdict"]
    )
    assert (
        report.independence.hierarchy_applied
        == expected["independence"]["hierarchy_applied"]
    )

    anderson = next(
        r for r in report.independence.individual_results if "Anderson" in r.name
    )
    ww = next(r for r in report.independence.individual_results if "Wald" in r.name)

    assert (
        abs(anderson.statistic - expected["independence"]["anderson"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert anderson.verdict == expected["independence"]["anderson"]["verdict"]

    assert (
        abs(ww.statistic - expected["independence"]["wald_wolfowitz"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert ww.verdict == expected["independence"]["wald_wolfowitz"]["verdict"]

    # Validar Homogeneidad
    helmert = next(
        r for r in report.homogeneity.individual_results if "Helmert" in r.name
    )
    t_student = next(
        r for r in report.homogeneity.individual_results if "Student" in r.name
    )
    cramer = next(
        r for r in report.homogeneity.individual_results if "Cramer" in r.name
    )

    assert helmert.verdict == expected["homogeneity"]["helmert"]["verdict"]
    assert t_student.verdict == expected["homogeneity"]["t_student"]["verdict"]
    assert cramer.verdict == expected["homogeneity"]["cramer"]["verdict"]

    # Validar Tendencia
    mk = next(r for r in report.trend.individual_results if "Mann" in r.name)
    ks = next(r for r in report.trend.individual_results if "Kolmogorov" in r.name)

    assert (
        abs(mk.statistic - expected["trend"]["mann_kendall"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert mk.verdict == expected["trend"]["mann_kendall"]["verdict"]

    assert (
        abs(ks.statistic - expected["trend"]["kolmogorov_smirnov"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert ks.verdict == expected["trend"]["kolmogorov_smirnov"]["verdict"]

    # Validar Outliers
    chow = next(r for r in report.outliers.individual_results if "Chow" in r.name)
    assert (
        abs(chow.statistic - expected["outliers"]["chow"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert chow.verdict == expected["outliers"]["chow"]["verdict"]


def test_series_referencia_2():
    """Prueba completa contra serie referencia 2"""
    """todos los resultados deben coincidir exactamente"""
    fixtures_path = Path(__file__).parent.parent / "fixtures"

    with (fixtures_path / "expected_results.json").open() as f:
        expected = json.load(f)["series_referencia_2"]

    # Cargar serie de referencia (tomar solo la columna numérica de caudal)
    df = pd.read_csv(fixtures_path / "series_referencia_2.csv")
    serie = df.iloc[:, 1].squeeze().dropna().iloc[:50]

    report = run_validation_pipeline(serie)

    # Validar campos básicos
    assert report.n == expected["n"]

    # Validar Independencia
    assert (
        report.independence.resolved_verdict
        == expected["independence"]["resolved_verdict"]
    )
    assert (
        report.independence.hierarchy_applied
        == expected["independence"]["hierarchy_applied"]
    )

    anderson = next(
        r for r in report.independence.individual_results if "Anderson" in r.name
    )
    ww = next(r for r in report.independence.individual_results if "Wald" in r.name)

    assert (
        abs(anderson.statistic - expected["independence"]["anderson"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert anderson.verdict == expected["independence"]["anderson"]["verdict"]

    assert (
        abs(ww.statistic - expected["independence"]["wald_wolfowitz"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert ww.verdict == expected["independence"]["wald_wolfowitz"]["verdict"]

    # Validar Homogeneidad
    helmert = next(
        r for r in report.homogeneity.individual_results if "Helmert" in r.name
    )
    t_student = next(
        r for r in report.homogeneity.individual_results if "Student" in r.name
    )
    cramer = next(
        r for r in report.homogeneity.individual_results if "Cramer" in r.name
    )

    assert helmert.verdict == expected["homogeneity"]["helmert"]["verdict"]
    assert t_student.verdict == expected["homogeneity"]["t_student"]["verdict"]
    assert cramer.verdict == expected["homogeneity"]["cramer"]["verdict"]

    # Validar Tendencia
    mk = next(r for r in report.trend.individual_results if "Mann" in r.name)
    ks = next(r for r in report.trend.individual_results if "Kolmogorov" in r.name)

    assert (
        abs(mk.statistic - expected["trend"]["mann_kendall"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert mk.verdict == expected["trend"]["mann_kendall"]["verdict"]

    assert (
        abs(ks.statistic - expected["trend"]["kolmogorov_smirnov"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert ks.verdict == expected["trend"]["kolmogorov_smirnov"]["verdict"]

    # Validar Outliers
    chow = next(r for r in report.outliers.individual_results if "Chow" in r.name)
    assert (
        abs(chow.statistic - expected["outliers"]["chow"]["statistic"])
        < STATISTIC_COMPARISON_TOLERANCE
    )
    assert chow.verdict == expected["outliers"]["chow"]["verdict"]
