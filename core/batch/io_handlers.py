"""Handlers para lectura inteligente de archivos CSV/Excel.

Proporciona funciones para leer archivos con detección automática
de formato, separador y columnas numéricas.
"""

from pathlib import Path

import pandas as pd


def read_file_intelligent(  # noqa: C901
    filepath: str,
    date_column: str | None = None,
    na_values: list[str] | None = None,
) -> pd.DataFrame:
    """Lee un archivo CSV o Excel con detección inteligente de formato.

    Detecta automáticamente:
        - Formato de archivo (CSV vs Excel)
        - Separador CSV (coma vs punto y coma)
        - Codificación (si es CSV)

    Args:
        filepath: Ruta al archivo a leer.
        date_column: Nombre de columna de fechas (si se conoce).
        na_values: Lista de valores a considerar como NA.

    Returns:
        DataFrame con los datos leídos.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si no se puede leer el archivo.
    """
    if not Path(filepath).exists():
        msg = f"Archivo no encontrado: {filepath}"
        raise FileNotFoundError(msg)

    if na_values is None:
        na_values = ["NA", "nan", "NaN", "", "N/A", "null", "NULL"]

    file_ext = Path(filepath).suffix.lower()

    if file_ext == ".csv":
        # Intentar leer con separador coma
        try:
            df = pd.read_csv(filepath, na_values=na_values, encoding="utf-8")
            # Si tiene solo una columna, intentar con punto y coma
            if len(df.columns) == 1:
                df = pd.read_csv(
                    filepath, sep=";", na_values=na_values, encoding="utf-8"
                )
        except UnicodeDecodeError:
            # Intentar con otra codificación
            try:
                df = pd.read_csv(
                    filepath, sep=",", na_values=na_values, encoding="latin-1"
                )
                if len(df.columns) == 1:
                    df = pd.read_csv(
                        filepath, sep=";", na_values=na_values, encoding="latin-1"
                    )
            except Exception:  # noqa: BLE001
                # Último intento con punto y coma y utf-8
                df = pd.read_csv(
                    filepath, sep=";", na_values=na_values, encoding="utf-8"
                )
        except Exception:  # noqa: BLE001
            # Fallback a punto y coma
            df = pd.read_csv(filepath, sep=";", na_values=na_values, encoding="utf-8")

    elif file_ext in [".xlsx", ".xls"]:
        # Leer Excel
        df = pd.read_excel(filepath, na_values=na_values)

    else:
        msg = f"Formato de archivo no soportado: {file_ext}"
        raise ValueError(msg)

    # Convertir columna de fecha si se especifica
    if date_column and date_column in df.columns:
        df[date_column] = pd.to_datetime(df[date_column], errors="coerce")

    return df


def detect_numeric_columns(
    df: pd.DataFrame,
    exclude_columns: list[str] | None = None,
) -> list[str]:
    """Detecta columnas numéricas en un DataFrame.

    Args:
        df: DataFrame a analizar.
        exclude_columns: Columnas a excluir de la detección.

    Returns:
        Lista de nombres de columnas numéricas.
    """
    if exclude_columns is None:
        exclude_columns = {
            "date",
            "year",
            "month",
            "day",
            "fecha",
            "año",
            "mes",
            "year_hydrological",
        }

    # Primer intento: usar dtype de pandas
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    # Fallback: si hay pocos numéricos detectados (por 'nan' como string)
    if len(numeric_cols) < 2:  # noqa: PLR2004
        numeric_cols = [c for c in df.columns if c.lower() not in exclude_columns]

    # Filtrar columnas excluidas
    return [c for c in numeric_cols if c.lower() not in exclude_columns]


def detect_date_column(df: pd.DataFrame) -> str | None:
    """Detecta la columna de fechas en un DataFrame.

    Busca columnas con nombres comunes de fechas y verifica si
    contienen datos de tipo fecha o convertible a fecha.

    Args:
        df: DataFrame a analizar.

    Returns:
        Nombre de la columna de fechas, o None si no se detecta.
    """
    date_candidates = [
        "date",
        "fecha",
        "datetime",
        "time",
        "timestamp",
        "Date",
        "Fecha",
    ]

    # Primero buscar nombres exactos
    for candidate in date_candidates:
        if candidate in df.columns:
            # Verificar si es convertible a fecha
            try:
                pd.to_datetime(df[candidate].iloc[0], errors="coerce")
            except (IndexError, TypeError):
                continue
            else:
                return candidate

    # Segundo: buscar columnas que contengan "date" o "fecha"
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ["date", "fecha", "time"]):
            try:
                pd.to_datetime(df[col].iloc[0], errors="coerce")
            except (IndexError, TypeError):
                continue
            else:
                return col

    return None


def validate_dataframe_for_analysis(
    df: pd.DataFrame,
    date_column: str | None = None,
    value_column: str | None = None,
) -> tuple[bool, str]:
    """Valida que un DataFrame sea adecuado para análisis.

    Verifica:
        - Tiene suficientes filas
        - Tiene columna de fechas válida
        - Tiene columna de valores numéricos válida
        - Tiene suficientes datos no NA

    Args:
        df: DataFrame a validar.
        date_column: Nombre de columna de fechas (si se conoce).
        value_column: Nombre de columna de valores (si se conoce).

    Returns:
        Tupla (es_valido, mensaje_error).
    """
    if len(df) < 12:  # noqa: PLR2004
        return False, f"DataFrame tiene solo {len(df)} filas, se requieren al menos 12"

    # Detectar columna de fechas si no se proporcionó
    if date_column is None:
        date_column = detect_date_column(df)

    if date_column is None:
        return False, "No se detectó columna de fechas válida"

    # Convertir y validar fechas
    try:
        df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
    except Exception as e:  # noqa: BLE001
        return False, f"Error convirtiendo columna de fechas '{date_column}': {e!s}"

    # Detectar columna de valores si no se proporcionó
    if value_column is None:
        numeric_cols = detect_numeric_columns(df)
        if not numeric_cols:
            return False, "No se detectaron columnas numéricas válidas"
        value_column = numeric_cols[0]  # Usar la primera

    # Validar que hay suficientes datos válidos
    valid_data = df[[date_column, value_column]].dropna()
    if len(valid_data) < 12:  # noqa: PLR2004
        return (
            False,
            f"Solo {len(valid_data)} filas con datos válidos, se requieren al menos 12",
        )

    return True, ""


def prepare_dataframe_for_analysis(
    df: pd.DataFrame,
    date_column: str | None = None,
    value_column: str | None = None,
) -> pd.DataFrame:
    """Prepara un DataFrame para análisis SAMHIA.

    Realiza:
        - Detección automática de columnas
        - Limpieza de datos
        - Ordenamiento por fecha
        - Reset de índice

    Args:
        df: DataFrame original.
        date_column: Nombre de columna de fechas (si se conoce).
        value_column: Nombre de columna de valores (si se conoce).

    Returns:
        DataFrame preparado con columnas 'date' y la variable a analizar.
    """
    # Detectar columnas si no se proporcionaron
    if date_column is None:
        date_column = detect_date_column(df)
        if date_column is None:
            msg = "No se pudo detectar columna de fechas"
            raise ValueError(msg)

    if value_column is None:
        numeric_cols = detect_numeric_columns(df)
        if not numeric_cols:
            msg = "No se detectaron columnas numéricas"
            raise ValueError(msg)
        value_column = numeric_cols[0]

    # Seleccionar columnas relevantes
    df_prep = df[[date_column, value_column]].copy()
    df_prep.columns = ["date", "variable"]

    # Convertir fechas y limpiar
    df_prep["date"] = pd.to_datetime(df_prep["date"], errors="coerce")
    df_prep["variable"] = pd.to_numeric(
        df_prep["variable"].astype(str).str.strip(), errors="coerce"
    )

    # Filtrar NA y ordenar
    return df_prep[df_prep["date"].notna()].sort_values("date").reset_index(drop=True)
