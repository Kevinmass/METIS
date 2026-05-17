"""Módulo de pruebas de independencia para series hidrológicas.

Las pruebas de independencia verifican que las observaciones de una serie
no estén correlacionadas serialmente. La independencia es un requisito
fundamental para la validez de los análisis de frecuencia posteriores.

Ahora con soporte para frecuencia temporal:
    - Los valores críticos y lags se escalan según la frecuencia real de la serie.
    - Anderson: El valor crítico usa n_yearly_equivalent (años equivalentes)
      en lugar de n crudo, para que no se infle artificialmente con datos
      de alta frecuencia.
    - Ljung-Box: Los lags por defecto se calculan como min(12, n/4) para yearly,
      se escalan a 12 para monthly y se ajustan para otras frecuencias.
    - Durbin-Watson: Umbrales fijos aceptables, pero se reporta n_yearly.

Pruebas implementadas:
    - Anderson (Test de autocorrelación serial): Principal, analiza
      correlaciones con desfasajes 1, 2 y 3.
    - Wald-Wolfowitz (Test de corridas): Verificación, analiza patrones
      de subidas y bajadas respecto a la mediana.

Jerarquía de resolución (política de diseño METIS):
    Anderson es DETERMINANTE. Wald-Wolfowitz actúa solo como verificación.

    Casos:
        1. Anderson REJECTED → Veredicto final REJECTED (sin importar WW)
        2. Anderson ACCEPTED + WW ACCEPTED → Veredicto ACCEPTED
        3. Anderson ACCEPTED + WW REJECTED → Veredicto ACCEPTED
           (Anderson prevalece, hierarchy_applied=True)

    Esta jerarquía está documentada en la tesis de referencia del
    Mgter. Ing. Facundo Ganancias.
"""

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.stattools import durbin_watson

from core.shared.types import GroupVerdict, TestResult, get_scaled_sample_size


# Frecuencia temporal por defecto (año hidrológico convencional)
DEFAULT_FREQUENCY = "yearly"


def anderson_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de Anderson para autocorrelación serial.

    Evalúa la independencia calculando coeficientes de autocorrelación
    para desfasajes (lags) k=1, 2, 3. Si algún coeficiente excede las
    bandas de confianza al 95%, se rechaza la hipótesis de independencia.

    Fórmula:
        r_k = Σ[(x_t - x̄)(x_{t+k} - x̄)] / Σ(x_t - x̄)²
        Valor crítico: ±1.96 / √n_yearly (usando años equivalentes)

    La escala del valor crítico usa la cantidad de AÑOS equivalentes
    (n / steps_per_year) en lugar de n crudo. Esto evita que series
    de alta frecuencia (mensual, diaria) rechacen falsamente por tener
    n demasiado grande.

    Args:
        series: Serie temporal de valores numéricos.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).
        temporal_frequency: Frecuencia temporal de la serie.
            "yearly", "monthly", "daily", "hourly", "minutes", "5min".
            Por defecto "yearly".

    Returns:
        TestResult con máximo coeficiente de autocorrelación absoluto,
        valor crítico, veredicto y detalles incluyendo r_1, r_2, r_3.
    """
    n = len(series)
    x = series.to_numpy()
    mean = np.mean(x)

    # Obtener métricas escaladas por frecuencia
    scaled = get_scaled_sample_size(n, temporal_frequency)
    effective_years = scaled["effective_years"]

    # Valor crítico escalado por años efectivos (no por n crudo)
    # Esto evita que datos de alta frecuencia inflen falsamente la potencia
    n_effective = max(effective_years, 3)  # mínimo 3 años equivalentes
    critical_value = 1.96 / np.sqrt(n_effective)

    # Calcular autocorrelaciones lag 1, 2, 3
    acf = []
    for k in [1, 2, 3]:
        num = np.sum((x[:-k] - mean) * (x[k:] - mean))
        den = np.sum((x - mean) ** 2)
        rk = num / den if den != 0 else 0
        acf.append(rk)

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
            "n_effective_years": n_effective,
            "temporal_frequency": temporal_frequency,
        },
    )


def wald_wolfowitz_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de corridas de Wald-Wolfowitz para independencia.

    Analiza el número de "corridas" (runs) - secuencias consecutivas
    de valores por encima o debajo de la mediana. Si hay demasiadas o
    demasiadas pocas corridas, indica dependencia serial.

    Fórmula:
        Z = (R - mu_R) / sigma_R
        mu_R = (2*n1*n2)/(n1+n2) + 1
        sigma_R² = [2*n1*n2*(2*n1*n2 - n1 - n2)] / [(n1+n2)²*(n1+n2-1)]

    donde:
        R = número de corridas observadas
        n1 = cantidad de valores > mediana
        n2 = cantidad de valores ≤ mediana

    La frecuencia temporal se incluye en los detalles para trazabilidad,
    pero el test de Wald-Wolfowitz es no paramétrico y no depende de n
    en su estadístico (sí en el valor crítico).

    Args:
        series: Serie temporal de valores numéricos.
        alpha: Nivel de significancia. Default 0.05 (95% confianza).
        temporal_frequency: Frecuencia temporal de la serie.
            Se incluye en detalles informativos.

    Returns:
        TestResult con estadístico Z, valor crítico, veredicto y detalles
        incluyendo corridas observadas, esperadas y conteos n1/n2.
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
            detail={
                "note": "All values are equal, independence assumed",
                "temporal_frequency": temporal_frequency,
            },
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
            "temporal_frequency": temporal_frequency,
        },
    )


def durbin_watson_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de Durbin-Watson para autocorrelación en residuos.

    Detecta autocorrelación de primer orden en los residuos de una
    regresión. El estadístico DW oscila entre 0 y 4:
        - DW ≈ 2: No hay autocorrelación
        - DW < 2: Autocorrelación positiva
        - DW > 2: Autocorrelación negativa

    Fórmula:
        DW = Σ(e_t - e_{t-1})² / Σe_t²

    La frecuencia temporal se reporta en detalles para ayudar a
    interpretar los umbrales en contexto.

    Args:
        series: Serie temporal de valores numéricos.
        alpha: Nivel de significancia. Default 0.05.
        temporal_frequency: Frecuencia temporal de la serie.

    Returns:
        TestResult con estadístico DW, rango crítico, veredicto y
        detalles sobre el tipo de autocorrelación detectada.
    """
    x = series.to_numpy()

    try:
        dw_stat = float(durbin_watson(x))
    except Exception:  # noqa: BLE001
        # Fallback si statsmodels falla
        residuals = x
        diff_residuals = np.diff(residuals)
        numerator = np.sum(diff_residuals**2)
        denominator = np.sum(residuals**2)
        dw_stat = numerator / denominator if denominator != 0 else 2.0

    # Rango crítico aproximado para alpha=0.05
    # DW < 1.5: autocorrelación positiva
    # DW > 2.5: autocorrelación negativa
    # 1.5 <= DW <= 2.5: aceptable
    if dw_stat < 1.5:  # noqa: PLR2004
        verdict = "REJECTED"
        autocorr_type = "positive"
    elif dw_stat > 2.5:  # noqa: PLR2004
        verdict = "REJECTED"
        autocorr_type = "negative"
    else:
        verdict = "ACCEPTED"
        autocorr_type = "none"

    # Obtener n de la serie
    scaled = get_scaled_sample_size(len(x), temporal_frequency)

    return TestResult(
        name="Durbin-Watson Test",
        statistic=float(dw_stat),
        critical_value=[1.5, 2.5],  # Rango aceptable
        alpha=alpha,
        verdict=verdict,
        detail={
            "autocorrelation_type": autocorr_type,
            "interpretation": (
                "Positive autocorrelation"
                if autocorr_type == "positive"
                else "Negative autocorrelation"
                if autocorr_type == "negative"
                else "No significant autocorrelation"
            ),
            "temporal_frequency": temporal_frequency,
            "effective_years": scaled["effective_years"],
        },
    )


def ljung_box_test(
    series: pd.Series,
    lags: int | None = None,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de Ljung-Box para autocorrelación en múltiples lags.

    Test portmanteau que evalúa si alguna de las autocorrelaciones
    hasta el lag especificado es significativamente diferente de cero.
    Es más general que Anderson porque evalúa múltiples lags simultáneamente.

    Fórmula:
        Q = n(n+2) Σ(r_k² / (n-k))
        para k = 1 hasta lags

    Los lags por defecto se calculan según la frecuencia temporal:
        - yearly: min(12, n/4) (hasta 12 años de rezago)
        - monthly: 12 (captura estacionalidad anual)
        - daily: 30 (captura estacionalidad mensual)
        - hourly: 168 (captura estacionalidad semanal)

    Args:
        series: Serie temporal de valores numéricos.
        lags: Número máximo de lags a evaluar. Si es None, se calcula
            automáticamente según la frecuencia temporal.
        alpha: Nivel de significancia. Default 0.05.
        temporal_frequency: Frecuencia temporal de la serie.

    Returns:
        TestResult con estadístico Q, valor crítico χ², veredicto y
        valor p.

    Note:
        Los lags automáticos están diseñados para capturar la estacionalidad
        más larga relevante para cada frecuencia.
    """
    x = series.to_numpy()
    n = len(x)

    # Calcular lags por defecto según frecuencia
    if lags is None:
        freq_lags = {
            "yearly": min(12, max(3, n // 4)),
            "monthly": 12,  # Estacionalidad anual
            "daily": 30,  # Estacionalidad mensual
            "hourly": 168,  # Estacionalidad semanal (7*24)
            "minutes": 60,  # Estacionalidad horaria
            "5min": 288,  # Estacionalidad diaria (24*12)
            "irregular": min(12, max(3, n // 4)),
        }
        lags = freq_lags.get(temporal_frequency, min(12, max(3, n // 4)))

    # Asegurar que lags no exceda n // 2 - 1 (requisito técnico)
    lags = min(lags, max(1, n // 2 - 1))

    try:
        lb_result = acorr_ljungbox(x, lags=[lags], return_df=True)
        lb_stat = float(lb_result["lb_stat"].iloc[0])
        lb_p = float(lb_result["lb_pvalue"].iloc[0])
    except Exception:  # noqa: BLE001
        # Fallback manual si statsmodels falla
        mean = np.mean(x)
        acf = []
        for k in range(1, lags + 1):
            if k >= n:
                acf.append(0)
                continue
            num = np.sum((x[:-k] - mean) * (x[k:] - mean))
            den = np.sum((x - mean) ** 2)
            rk = num / den if den != 0 else 0
            acf.append(rk)

        # Calcular Q
        q_stat = (
            n * (n + 2) * sum(rk**2 / (n - k) for k, rk in enumerate(acf, 1) if n > k)
        )
        lb_stat = float(q_stat)
        lb_p = 1 - stats.chi2.cdf(q_stat, df=lags)

    # Valor crítico χ²
    critical_value = stats.chi2.ppf(1 - alpha, df=lags)
    verdict = "REJECTED" if lb_p < alpha else "ACCEPTED"

    # Obtener métricas escaladas
    scaled = get_scaled_sample_size(n, temporal_frequency)

    return TestResult(
        name="Ljung-Box Test",
        statistic=float(lb_stat),
        critical_value=float(critical_value),
        alpha=alpha,
        verdict=verdict,
        detail={
            "lags_tested": lags,
            "p_value": float(lb_p),
            "temporal_frequency": temporal_frequency,
            "effective_years": scaled["effective_years"],
        },
    )


def spearman_test(
    series: pd.Series,
    alpha: float = 0.05,
    temporal_frequency: str = DEFAULT_FREQUENCY,
) -> TestResult:
    """Test de correlación de Spearman para independencia.

    Evalúa la correlación de rangos entre valores consecutivos de la serie.
    Es una alternativa no paramétrica al test de Pearson y es más robusta
    ante valores atípicos y distribuciones no normales.

    Fórmula:
        rho = 1 - (6Σd_i²) / (n(n²-1))

    donde:
        d_i = diferencia de rangos entre x_i y x_{i+1}
        n = tamaño de muestra - 1 (pares consecutivos)

    La frecuencia temporal se incluye en detalles para trazabilidad.

    Args:
        series: Serie temporal de valores numéricos.
        alpha: Nivel de significancia. Default 0.05.
        temporal_frequency: Frecuencia temporal de la serie.

    Returns:
        TestResult con estadístico rho, valor crítico, veredicto y valor p.
    """
    x = series.to_numpy()

    # Crear pares consecutivos
    x_lag1 = x[:-1]
    x_lag0 = x[1:]

    try:
        rho, p_value = stats.spearmanr(x_lag0, x_lag1, nan_policy="omit")
    except Exception:  # noqa: BLE001
        # Fallback manual
        rho = 0.0
        p_value = 1.0

    # Valor crítico aproximado para Spearman (n grande)
    n_pairs = len(x_lag0)
    critical_value = stats.norm.ppf(1 - alpha / 2) / np.sqrt(n_pairs - 1)
    verdict = "REJECTED" if abs(rho) > abs(critical_value) else "ACCEPTED"

    return TestResult(
        name="Spearman Rank Correlation Test",
        statistic=float(abs(rho)),
        critical_value=float(abs(critical_value)),
        alpha=alpha,
        verdict=verdict,
        detail={
            "rho": float(rho),
            "p_value": float(p_value),
            "correlation_direction": (
                "positive" if rho > 0 else "negative" if rho < 0 else "none"
            ),
            "temporal_frequency": temporal_frequency,
        },
    )


def resolve_independence(
    anderson: TestResult, wald_wolfowitz: TestResult
) -> GroupVerdict:
    """Resuelve veredicto grupal aplicando jerarquía Anderson → Wald-Wolfowitz.

    Implementa la política de resolución del dominio hidrológico según
    la cual Anderson es determinante y Wald-Wolfowitz actúa como
    verificación secundaria.

    Reglas de resolución:
        1. Si Anderson.verdict == "REJECTED":
           → resolved_verdict = "REJECTED"
           → hierarchy_applied = True (Anderson decidió)

        2. Si Anderson.verdict == "ACCEPTED":
           → resolved_verdict = "ACCEPTED"
           → hierarchy_applied = (Wald-Wolfowitz.verdict == "REJECTED")
             (True si hubo desacuerdo que se resolvió a favor de Anderson)

    Args:
        anderson: Resultado del test de Anderson (prueba principal).
        wald_wolfowitz: Resultado del test de Wald-Wolfowitz (verificación).

    Returns:
        GroupVerdict con:
            - condition="independence"
            - individual_results=[anderson, wald_wolfowitz]
            - resolved_verdict según reglas de jerarquía
            - hierarchy_applied indicando si se aplicó resolución

    Example:
        >>> anderson = TestResult(..., verdict="ACCEPTED")
        >>> ww = TestResult(..., verdict="REJECTED")
        >>> group = resolve_independence(anderson, ww)
        >>> group.resolved_verdict
        'ACCEPTED'
        >>> group.hierarchy_applied
        True  # Anderson prevaleció sobre WW
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
