import numpy as np
import pandas as pd


def load_series(source: str | list[float] | np.ndarray | pd.Series) -> pd.Series:
    """
    Carga una serie hidrológica desde diferentes fuentes.
    Acepta ruta a CSV/Excel, lista de floats, numpy array o pandas Series.
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
    """
    Detecta inconsistencias físicas en la serie: ceros, negativos y NaN.
    Devuelve lista de advertencias estructuradas, NUNCA lanza excepciones.
    """
    warnings = []

    nan_count = series.isna().sum()
    if nan_count > 0:
        warnings.append(
            {
                "code": "MISSING_VALUES",
                "message": f"Se encontraron {nan_count} valores faltantes (NaN)",
                "count": int(nan_count),
                "indices": series[series.isna()].index.tolist(),
            }
        )

    zero_count = (series == 0).sum()
    if zero_count > 0:
        warnings.append(
            {
                "code": "ZERO_VALUES",
                "message": f"Se encontraron {zero_count} valores iguales a cero",
                "count": int(zero_count),
                "indices": series[series == 0].index.tolist(),
            }
        )

    negative_count = (series < 0).sum()
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


def apply_log_transform(series: pd.Series) -> tuple[pd.Series, list[dict]]:
    """
    Aplica transformación logarítmica natural a la serie.
    Si existen inconsistencias físicas devuelve advertencia y NO aplica transformación.
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
