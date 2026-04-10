import numpy as np
import pandas as pd
from scipy import stats

from core.shared.types import GroupVerdict, TestResult


def anderson_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """
    Test de Anderson para autocorrelación serial.
    Calcula coeficientes de autocorrelación para k=1,2,3 y aplica criterio del 10%.
    """
    n = len(series)
    x = series.to_numpy()
    mean = np.mean(x)

    # Calcular autocorrelaciones lag 1, 2, 3
    acf = []
    for k in [1, 2, 3]:
        num = np.sum((x[:-k] - mean) * (x[k:] - mean))
        den = np.sum((x - mean) ** 2)
        rk = num / den if den != 0 else 0
        acf.append(rk)

    # Valor crítico al 95%: ± 1.96 / sqrt(n)
    critical_value = 1.96 / np.sqrt(n)

    # Criterio del 10%: si el 10% de los coeficientes exceden bandas -> rechazar
    max_acf = np.max(np.abs(acf))
    verdict = "REJECTED" if max_acf > critical_value else "ACCEPTED"

    return TestResult(
        name="Anderson Autocorrelation Test",
        statistic=float(max_acf),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "acf_lag1": float(acf[0]),
            "acf_lag2": float(acf[1]),
            "acf_lag3": float(acf[2]),
            "n": n,
        },
    )


def wald_wolfowitz_test(series: pd.Series, alpha: float = 0.05) -> TestResult:
    """
    Test de corridas de Wald-Wolfowitz para independencia.
    Contrasta número de corridas observadas contra distribución normal.
    """
    n = len(series)
    median = np.median(series)

    # Secuencia de signos respecto a la mediana
    signs = np.where(series > median, 1, 0)

    # Contar número de corridas
    runs = np.sum(signs[1:] != signs[:-1]) + 1

    # Número de observaciones arriba y abajo de la mediana
    n1 = np.sum(signs)
    n2 = n - n1

    if n1 == 0 or n2 == 0:
        # Todos los valores son iguales
        return TestResult(
            name="Wald-Wolfowitz Runs Test",
            statistic=0.0,
            critical_value=1.96,
            alpha=alpha,
            verdict="ACCEPTED",
            detail={"note": "All values are equal, independence assumed"},
        )

    # Media y varianza esperada del número de corridas
    mu = (2 * n1 * n2) / (n1 + n2) + 1
    sigma2 = (2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)) / ((n1 + n2) ** 2 * (n1 + n2 - 1))
    sigma = np.sqrt(sigma2)

    # Estadístico Z
    z = (runs - mu) / sigma if sigma != 0 else 0

    critical_value = stats.norm.ppf(1 - alpha / 2)
    verdict = "REJECTED" if abs(z) > critical_value else "ACCEPTED"

    return TestResult(
        name="Wald-Wolfowitz Runs Test",
        statistic=float(z),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "observed_runs": int(runs),
            "expected_runs": float(mu),
            "n1": int(n1),
            "n2": int(n2),
        },
    )


def resolve_independence(
    anderson: TestResult, wald_wolfowitz: TestResult
) -> GroupVerdict:
    """
    Resuelve veredicto grupal de independencia aplicando jerarquía:
    - Anderson es determinante
    - Wald-Wolfowitz solo actúa como verificación
    - Si Anderson acepta, veredicto final es ACEPTED sin importar Wald-Wolfowitz
    """
    hierarchy_applied = False
    resolved_verdict = None

    if anderson.verdict == "REJECTED":
        resolved_verdict = "REJECTED"
        hierarchy_applied = True
    elif anderson.verdict == "ACCEPTED":
        resolved_verdict = "ACCEPTED"
        if wald_wolfowitz.verdict == "REJECTED":
            hierarchy_applied = True

    return GroupVerdict(
        condition="independence",
        individual_results=[anderson, wald_wolfowitz],
        resolved_verdict=resolved_verdict,
        hierarchy_applied=hierarchy_applied,
    )
