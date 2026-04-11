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


router = APIRouter()

MIN_SERIES_LENGTH = 3


def unsupported_file_type():
    raise HTTPException(
        status_code=400,
        detail="Formato de archivo no soportado. Use .csv o .xlsx",
    )


def empty_file_error():
    raise HTTPException(
        status_code=400,
        detail="El archivo no contiene valores validos",
    )


def short_series_error():
    raise HTTPException(
        status_code=400,
        detail="La serie debe contener al menos 3 datos",
    )


def build_series_id(series_id: str | None) -> str:
    return series_id or f"series-{uuid4()}"


def normalize_warning(raw_warning: dict) -> WarningItem:
    indices = raw_warning.get("affected_indices")
    if indices is None:
        indices = raw_warning.get("indices", [])

    return WarningItem(
        code=raw_warning["code"],
        message=raw_warning["message"],
        affected_indices=list(indices),
    )


def serialize_test_result(result: TestResult) -> TestResultSchema:
    return TestResultSchema(
        statistic=result.statistic,
        critical_value=result.critical_value,
        alpha=result.alpha,
        verdict=result.verdict,
    )


def find_result(group: GroupVerdict, name_fragment: str) -> TestResult:
    return next(
        result
        for result in group.individual_results
        if name_fragment.lower() in result.name.lower()
    )


def build_response(report: ValidationReport, series_id: str) -> ValidationResponse:
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
            "description": "Analisis completado correctamente",
        },
        400: {"description": "Serie vacia o con menos de 3 datos"},
        422: {"description": "Entrada malformada o no numerica"},
    },
    summary="Ejecutar pipeline completo de validación",
    description=(
        "Recibe una serie de valores numéricos"
        "y ejecuta todas las pruebas estadísticas"
        "de validación hidrológica"
    ),
)
async def validate_series(input_data: SeriesInput):
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
        },
        400: {"description": "Archivo vacio, no soportado o con menos de 3 datos"},
        422: {"description": "Archivo invalido o con contenido no numerico"},
    },
    summary="Validar desde archivo CSV/Excel",
    description=(
        "Carga un archivo .csv o .xlsx con una"
        "única columna de valores y ejecuta"
        "el pipeline de validación"
    ),
)
async def validate_file(
    file: Annotated[
        UploadFile,
        File(description="Archivo CSV o Excel con una columna de valores numéricos"),
    ],
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No se proporcionó ningún archivo")

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file, header=None)
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file.file, header=None)
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
