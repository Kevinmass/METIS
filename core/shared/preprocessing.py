"""Módulo de preprocesamiento de series hidrológicas.

Proporciona funciones para carga, validación y transformación de datos
hidrológicos, garantizando que las series cumplan con los requisitos
físicos y matemáticos necesarios para el análisis estadístico.

Principio de diseño transversal (aplicado en todo METIS):
    El software detecta y advierte sobre inconsistencias, pero NUNCA
    bloquea el análisis. La interpretación final recae en el criterio
    del ingeniero hidrólogo.

Funciones principales:
    load_series: Carga series desde múltiples fuentes de datos.
    detect_physical_inconsistencies: Identifica valores problemáticos.
    apply_log_transform: Aplica transformación logarítmica con validación.
"""

import numpy as np
import pandas as pd


def load_series(
    source: str | list[float] | np.ndarray | pd.Series,
) -> pd.Series:
    """Carga una serie hidrológica desde diferentes fuentes de datos.

    Acepta múltiples formatos de entrada: rutas a archivos CSV/Excel,
    listas de números, arrays de NumPy, o Series de Pandas.

    Para archivos CSV/Excel, la función detecta automáticamente la
    columna de valores numéricos. Si hay múltiples columnas numéricas,
    selecciona la segunda (asumiendo formato estándar: año | valor).

    Args:
        source: Fuente de datos de la serie. Puede ser:
            - str: Ruta a archivo .csv, .xlsx o .xls
            - list[float]: Lista de valores numéricos
            - np.ndarray: Array de NumPy
            - pd.Series: Serie de Pandas (se copia)

    Returns:
        pd.Series: Serie de Pandas con los datos cargados y valores
            nulos eliminados. El índice se preserva para archivos o
            se genera automáticamente para listas/arrays.

    Raises:
        ValueError: Si el formato de archivo no es soportado (.csv,
            .xlsx, .xls) o si no se encuentran columnas numéricas.
        TypeError: Si el tipo de source no es soportado.

    Example:
        >>> # Desde lista
        >>> serie = load_series([12.5, 15.3, 18.7, 14.2])

        >>> # Desde archivo CSV con columnas 'fecha' y 'caudal'
        >>> serie = load_series("datos/rio_norte.csv")

        >>> # Desde archivo Excel
        >>> serie = load_series("datos/mediciones.xlsx")
    """
    if isinstance(source, pd.Series):
        return source.copy()

    if isinstance(source, (list, np.ndarray)):
        return pd.Series(source)

    if isinstance(source, str):
        if source.lower().endswith(".csv"):
            df = pd.read_csv(source)
        elif source.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(source)
        else:
            msg = "Formato de archivo no soportado. Usar CSV o Excel."
            raise ValueError(msg)

        # Tomar la primer columna numérica o la segunda columna
        # (formato estándar año/valor)
        numeric_cols = df.select_dtypes(include=np.number).columns
        min_numeric_cols = 2
        if len(numeric_cols) >= min_numeric_cols:
            return df[numeric_cols[1]].dropna()
        if len(numeric_cols) >= 1:
            return df[numeric_cols[0]].dropna()
        msg = "No se encontraron columnas numéricas en el archivo"
        raise ValueError(msg)

    msg = f"Tipo de fuente no soportado: {type(source)}"
    raise TypeError(msg)


def detect_physical_inconsistencies(series: pd.Series) -> list[dict]:
    """Detecta inconsistencias físicas en la serie hidrológica.

    Identifica tres tipos de valores problemáticos que afectan el
    análisis estadístico:
    1. Valores faltantes (NaN): Imposibilitan cálculos completos
    2. Valores cero: Prohiben transformaciones logarítmicas
    3. Valores negativos: Físicamente imposibles para caudales

    Siguiendo el principio de diseño de METIS, esta función NUNCA
    lanza excepciones. Siempre retorna una lista (posiblemente vacía)
    que el pipeline de validación incorpora como advertencias.

    Args:
        series: Serie de Pandas con los datos hidrológicos a validar.

    Returns:
        list[dict]: Lista de advertencias estructuradas. Cada advertencia
            es un diccionario con:
            - code: Identificador único (str)
                * "MISSING_VALUES": Valores NaN detectados
                * "ZERO_VALUES": Valores iguales a cero
                * "NEGATIVE_VALUES": Valores menores a cero
            - message: Descripción legible para el usuario (str)
            - count: Cantidad de valores afectados (int)
            - indices: Lista de índices donde ocurren (list[int])

    Example:
        >>> serie = pd.Series([10.5, 0.0, -2.3, np.nan, 15.7])
        >>> warnings = detect_physical_inconsistencies(serie)
        >>> len(warnings)
        3
        >>> warnings[0]["code"]
        'ZERO_VALUES'
    """
    warnings = []

    nan_count = int(series.isna().sum())
    if nan_count > 0:
        warnings.append(
            {
                "code": "MISSING_VALUES",
                "message": f"Se encontraron {nan_count} valores faltantes (NaN)",
                "count": int(nan_count),
                "indices": series[series.isna()].index.tolist(),
            }
        )

    zero_count = int((series == 0).sum())
    if zero_count > 0:
        warnings.append(
            {
                "code": "ZERO_VALUES",
                "message": f"Se encontraron {zero_count} valores iguales a cero",
                "count": int(zero_count),
                "indices": series[series == 0].index.tolist(),
            }
        )

    negative_count = int((series < 0).sum())
    if negative_count > 0:
        warnings.append(
            {
                "code": "NEGATIVE_VALUES",
                "message": f"Se encontraron {negative_count} valores negativos",
                "count": int(negative_count),
                "indices": series[series < 0].index.tolist(),
            }
        )

    return warnings


def apply_log_transform(
    series: pd.Series,
) -> tuple[pd.Series, list[dict]]:
    """Aplica transformación logarítmica natural con validación previa.

    Calcula ln(x) para cada elemento de la serie. Antes de aplicar
    la transformación, verifica que no existan valores que la invaliden:
    - Ceros: ln(0) es indefinido (-∞)
    - Negativos: ln(x) no está definido para x < 0 en reales
    - NaN: Se propagarían los valores faltantes

    Si se detectan inconsistencias, la función NO aplica la transformación
    y retorna la serie original junto con advertencias explicativas.
    Esto permite que el pipeline de validación continúe operando.

    Args:
        series: Serie de Pandas con valores numéricos positivos.

    Returns:
        tuple[pd.Series, list[dict]]: Tupla con:
            - Serie transformada (o copia de original si no se aplicó)
            - Lista de advertencias generadas durante el proceso

    Note:
        La función siempre ejecuta detect_physical_inconsistencies
        internamente, por lo que las advertencias de valores problemáticos
        se incluyen en el retorno junto con el estado de la transformación.

    Example:
        >>> # Serie válida - transformación aplicada
        >>> serie = pd.Series([1.0, 2.718, 7.389])
        >>> log_serie, warnings = apply_log_transform(serie)
        >>> # log_serie ≈ [0.0, 1.0, 2.0]
        >>> any(w["code"] == "LOG_TRANSFORM_APPLIED" for w in warnings)
        True

        >>> # Serie con cero - transformación omitida
        >>> serie_invalida = pd.Series([0.0, 5.0, 10.0])
        >>> original, warnings = apply_log_transform(serie_invalida)
        >>> any(w["code"] == "LOG_TRANSFORM_SKIPPED" for w in warnings)
        True
    """
    warnings = detect_physical_inconsistencies(series)

    has_inconsistencies = any(
        w["code"] in ["ZERO_VALUES", "NEGATIVE_VALUES", "MISSING_VALUES"]
        for w in warnings
    )

    if has_inconsistencies:
        warnings.append(
            {
                "code": "LOG_TRANSFORM_SKIPPED",
                "message": "No se aplicó transformación logarítmica "
                "por presencia de valores inválidos",
                "applied": False,
            }
        )
        return series.copy(), warnings

    log_series = np.log(series)

    warnings.append(
        {
            "code": "LOG_TRANSFORM_APPLIED",
            "message": "Transformación logarítmica aplicada correctamente",
            "applied": True,
        }
    )

    return log_series, warnings
