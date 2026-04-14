"""Tests unitarios para el módulo de independencia.

Este módulo prueba la lógica de resolución de independencia, específicamente
la jerarquía entre los tests de Anderson y Wald-Wolfowitz.

Política de resolución probada:
    - Anderson es determinante (prueba principal)
    - Wald-Wolfowitz es verificación (prueba secundaria)
    - Si Anderson acepta pero WW rechaza: veredicto ACCEPTED con hierarchy_applied=True

Fixtures:
    make_result: Helper factory para crear objetos TestResult de prueba.
"""

from core.shared.types import TestResult as ValidationTestResult
from core.validation.independence import resolve_independence


def make_result(name: str, verdict: str) -> ValidationTestResult:
    """Factory helper para crear objetos TestResult de prueba.

    Crea un TestResult mínimo con valores dummy para statistic y critical_value,
    útil para tests que solo necesitan controlar el veredicto.

    Args:
        name: Nombre descriptivo de la prueba (ej: "Anderson Autocorrelation Test")
        verdict: Veredicto a asignar ("ACCEPTED" o "REJECTED")

    Returns:
        ValidationTestResult: Objeto configurado para el test.
    """
    return ValidationTestResult(
        name=name,
        statistic=0.0,
        critical_value=1.0,
        alpha=0.05,
        verdict=verdict,
        detail={},
    )


def test_resolve_independence_accepts_when_anderson_accepts_and_ww_rejects():
    """Test jerarquía: Anderson acepta, WW rechaza → veredicto ACCEPTED.

    Verifica que cuando la prueba principal (Anderson) acepta independencia,
    el veredicto final es ACCEPTED independientemente de lo que diga
    Wald-Wolfowitz. Además verifica que hierarchy_applied=True indica
    que se aplicó la resolución por jerarquía.

    Este es el caso típico donde la jerarquía Anderson → WW se activa.
    """
    anderson = make_result("Anderson Autocorrelation Test", "ACCEPTED")
    ww = make_result("Wald-Wolfowitz Runs Test", "REJECTED")

    report = resolve_independence(anderson, ww)

    assert report.resolved_verdict == "ACCEPTED"
    assert report.hierarchy_applied is True
