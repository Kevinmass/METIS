"""Router de validación - Endpoints principales de la API METIS.

Este módulo define los endpoints REST para ejecutar el pipeline de
validación hidrológica. Proporciona dos vías de ingesta:

    1. POST /validate: JSON directo con la serie numérica.
    2. POST /validate/file: Archivo CSV o Excel para subida masiva.

Flujo de procesamiento:
    1. Validación de entrada (vacío, longitud mínima, formato)
    2. Conversión a pandas.Series
    3. Ejecución de core.validation.run_validation_pipeline()
    4. Serialización del ValidationReport a ValidationResponse
    5. Retorno de respuesta JSON estructurada

Manejo de errores:
    - 400: Serie vacía, archivo inválido, menos de 3 datos
    - 422: Error en procesamiento (datos no numéricos, formato incorrecto)
    - 200: Análisis completado (incluso con advertencias físicas)

Nota de diseño:
    La API NUNCA retorna 500 por errores de datos del usuario.
    Todos los errores de validación se traducen en 400/422 con
    mensajes descriptivos. El pipeline siempre completa si los
    datos son numéricos, incluso con ceros o negativos (reportados
    como advertencias).
"""

import io
from typing import Annotated
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from api.schemas.validation import (
    HomogeneityValidationSchema,
    IndependenceValidationSchema,
    OutliersValidationSchema,
    OutlierTestResultSchema,
    SeriesInput,
    TestResultSchema,
    TrendValidationSchema,
    ValidationDataSchema,
    ValidationResponse,
    WarningItem,
)
from core.shared.types import GroupVerdict, TestResult, ValidationReport
from core.validation import run_validation_pipeline


# Router de validación
router = APIRouter()

# Constantes de validación
MIN_SERIES_LENGTH = 3


def unsupported_file_type() -> None:
    """Lanza excepción HTTP 400 por formato de archivo no soportado.

    Raises:
        HTTPException: Status 400 con mensaje de error.
    """
    raise HTTPException(
        status_code=400,
        detail="Formato de archivo no soportado. Use .csv o .xlsx",
    )


def empty_file_error() -> None:
    """Lanza excepción HTTP 400 por archivo sin datos válidos.

    Raises:
        HTTPException: Status 400 con mensaje de error.
    """
    raise HTTPException(
        status_code=400,
        detail="El archivo no contiene valores validos",
    )


def short_series_error() -> None:
    """Lanza excepción HTTP 400 por serie con menos de MIN_SERIES_LENGTH datos.

    Raises:
        HTTPException: Status 400 con mensaje de error.
    """
    raise HTTPException(
        status_code=400,
        detail="La serie debe contener al menos 3 datos",
    )


def build_series_id(series_id: str | None) -> str:
    """Construye identificador de serie, generando UUID si no se provee.

    Args:
        series_id: Identificador opcional proporcionado por el cliente.

    Returns:
        str: series_id si existe, o "series-<uuid4>" generado.

    Example:
        >>> build_series_id("rio_norte")
        'rio_norte'
        >>> build_series_id(None)
        'series-550e8400-e29b-41d4-a716-446655440000'
    """
    return series_id or f"series-{uuid4()}"


def normalize_warning(raw_warning: dict) -> WarningItem:
    """Normaliza advertencia del core al schema de API.

    El core usa "indices" pero el schema API usa "affected_indices".
    Esta función adapta el formato para mantener consistencia del contrato.

    Args:
        raw_warning: Diccionario de advertencia del core con keys:
            - code: str
            - message: str
            - indices: list[int] | None

    Returns:
        WarningItem: Schema validado para serialización JSON.

    Note:
        Mantiene compatibilidad si el core cambia la key en el futuro.
    """
    indices = raw_warning.get("affected_indices")
    if indices is None:
        indices = raw_warning.get("indices", [])

    return WarningItem(
        code=raw_warning["code"],
        message=raw_warning["message"],
        affected_indices=list(indices),
    )


def serialize_test_result(result: TestResult) -> TestResultSchema:
    """Serializa TestResult del core a schema de API.

    Args:
        result: Objeto TestResult del core estadístico.

    Returns:
        TestResultSchema: Schema Pydantic listo para serialización JSON.
    """
    return TestResultSchema(
        statistic=result.statistic,
        critical_value=result.critical_value,
        alpha=result.alpha,
        verdict=result.verdict,
    )


def find_result(group: GroupVerdict, name_fragment: str) -> TestResult:
    """Busca un resultado específico dentro de un grupo por fragmento de nombre.

    Args:
        group: Grupo de veredicto con múltiples resultados individuales.
        name_fragment: Fragmento del nombre a buscar (case-insensitive).

    Returns:
        TestResult: El primer resultado cuyo nombre contiene el fragmento.

    Raises:
        StopIteration: Si ningún resultado coincide (error de programación).

    Example:
        >>> result = find_result(independence_group, "anderson")
        >>> result.name
        'Anderson Autocorrelation Test'
    """
    return next(
        result
        for result in group.individual_results
        if name_fragment.lower() in result.name.lower()
    )


def build_response(report: ValidationReport, series_id: str) -> ValidationResponse:
    """Construye la respuesta API completa desde un ValidationReport del core.

    Transforma el resultado del pipeline de validación en el schema
    ValidationResponse que consume el frontend. Extrae y serializa
    todos los resultados individuales de los cuatro grupos.

    Args:
        report: Reporte completo del core estadístico.
        series_id: Identificador de la serie para la respuesta.

    Returns:
        ValidationResponse: Schema raíz de la respuesta HTTP 200.

    Estructura de respuesta:
        - series_id, n, warnings
        - validation:
            - independence: Anderson + Wald-Wolfowitz + veredicto resuelto
            - homogeneity: Helmert + t-Student + Cramer
            - trend: Mann-Kendall + Kolmogorov-Smirnov
            - outliers: Chow con flagged_indices
    """
    independence = report.independence
    homogeneity = report.homogeneity
    trend = report.trend
    outliers = report.outliers
    chow_result = find_result(outliers, "chow")

    return ValidationResponse(
        series_id=series_id,
        n=report.n,
        warnings=[normalize_warning(warning) for warning in report.warnings],
        validation=ValidationDataSchema(
            independence=IndependenceValidationSchema(
                verdict=independence.resolved_verdict or "INCONCLUSIVE",
                hierarchy_applied=independence.hierarchy_applied,
                anderson=serialize_test_result(find_result(independence, "anderson")),
                wald_wolfowitz=serialize_test_result(find_result(independence, "wald")),
            ),
            homogeneity=HomogeneityValidationSchema(
                individual_verdicts_only=True,
                helmert=serialize_test_result(find_result(homogeneity, "helmert")),
                t_student=serialize_test_result(find_result(homogeneity, "student")),
                cramer=serialize_test_result(find_result(homogeneity, "cramer")),
            ),
            trend=TrendValidationSchema(
                mann_kendall=serialize_test_result(find_result(trend, "mann")),
                kolmogorov_smirnov=serialize_test_result(
                    find_result(trend, "kolmogorov")
                ),
            ),
            outliers=OutliersValidationSchema(
                chow=OutlierTestResultSchema(
                    statistic=chow_result.statistic,
                    critical_value=chow_result.critical_value,
                    alpha=chow_result.alpha,
                    verdict=chow_result.verdict,
                    flagged_indices=list(
                        chow_result.detail.get("outliers_indices", [])
                    ),
                )
            ),
        ),
    )


@router.post(
    "/validate",
    response_model=ValidationResponse,
    responses={
        200: {
            "description": "Análisis completado exitosamente",
            "content": {
                "application/json": {"schema": ValidationResponse.model_json_schema()}
            },
        },
        400: {"description": "Serie vacía o con menos de 3 datos"},
        422: {"description": "Entrada malformada o datos no numéricos"},
    },
    summary="Ejecutar pipeline completo de validación",
    description=(
        "Recibe una serie de valores numéricos y ejecuta todas las pruebas "
        "estadísticas de validación hidrológica (independencia, homogeneidad, "
        "tendencia, atípicos). Retorna un reporte completo con veredictos "
        "individuales y resueltos."
    ),
)
async def validate_series(input_data: SeriesInput) -> ValidationResponse:
    """Endpoint POST /validate - Validación desde JSON.

    Recibe la serie como lista de números en el body JSON. Ejecuta el
    pipeline completo de validación y retorna resultados estructurados.

    Args:
        input_data: Body JSON validado contra SeriesInput schema.
            - series: list[float] - mínimo 3 valores
            - series_id: str | None - opcional, para trazabilidad

    Returns:
        ValidationResponse: Reporte completo de validación.

    Raises:
        HTTPException 400: Si la serie está vacía o tiene menos de 3 datos.
        HTTPException 422: Si hay error en el procesamiento estadístico.

    Example:
        >>> import httpx
        >>> response = httpx.post(
        ...     "http://localhost:8000/validate",
        ...     json={"series": [12.5, 15.3, 14.8, 16.2], "series_id": "test"}
        ... )
        >>> response.status_code
        200
        >>> response.json()["n"]
        4
    """
    if len(input_data.series) == 0:
        raise HTTPException(status_code=400, detail="La serie no puede estar vacía")
    if len(input_data.series) < MIN_SERIES_LENGTH:
        short_series_error()

    try:
        series = pd.Series(input_data.series)
        report = run_validation_pipeline(series)
        return build_response(report, build_series_id(input_data.series_id))
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Error procesando la serie: {e!s}"
        ) from e


@router.post(
    "/validate/file",
    response_model=ValidationResponse,
    responses={
        200: {
            "description": "Archivo procesado correctamente",
            "content": {
                "application/json": {"schema": ValidationResponse.model_json_schema()}
            },
        },
        400: {"description": "Archivo vacío, no soportado o menos de 3 datos"},
        422: {"description": "Archivo inválido o contenido no numérico"},
    },
    summary="Validar desde archivo CSV/Excel",
    description=(
        "Carga un archivo .csv o .xlsx con una única columna de valores "
        "numéricos y ejecuta el pipeline completo de validación. "
        "La primera columna del archivo se interpreta como la serie."
    ),
)
async def validate_file(
    file: Annotated[
        UploadFile,
        File(description="Archivo CSV o Excel con una columna de valores numéricos"),
    ],
) -> ValidationResponse:
    """Endpoint POST /validate/file - Validación desde archivo.

    Acepta subida de archivos CSV (.csv) o Excel (.xlsx, .xls).
    Lee la primera columna como serie de valores numéricos.

    Args:
        file: Archivo subido vía multipart/form-data.
            Formatos soportados: .csv, .xlsx, .xls

    Returns:
        ValidationResponse: Reporte completo de validación.

    Raises:
        HTTPException 400: Si el archivo está vacío, tiene formato no
            soportado, o contiene menos de 3 valores válidos.
        HTTPException 422: Si hay error al leer el archivo o procesar
            los datos (formato incorrecto, valores no numéricos).

    Note:
        El nombre del archivo se usa como series_id en la respuesta.
        Valores no numéricos en el archivo generan error 422.

    Example:
        >>> import httpx
        >>> with open("serie.csv", "rb") as f:
        ...     response = httpx.post(
        ...         "http://localhost:8000/validate/file",
        ...         files={"file": ("serie.csv", f, "text/csv")}
        ...     )
        >>> response.status_code
        200
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No se proporcionó ningún archivo")

    try:
        file_bytes = await file.read()
        buffer = io.BytesIO(file_bytes)

        if file.filename.endswith(".csv"):
            df = pd.read_csv(buffer, header=None)
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(buffer, header=None, engine="openpyxl")
        else:
            unsupported_file_type()

        values = df.iloc[:, 0].dropna().tolist()

        if len(values) == 0:
            empty_file_error()
        if len(values) < MIN_SERIES_LENGTH:
            short_series_error()

        series = pd.Series(values)
        report = run_validation_pipeline(series)
        return build_response(report, build_series_id(file.filename))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Error leyendo el archivo: {e!s}"
        ) from e
