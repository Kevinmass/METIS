from typing import Annotated

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from api.schemas.validation import SeriesInput, ValidationResponse
from core.validation import run_validation_pipeline


router = APIRouter()


def unsupported_file_type():
    raise HTTPException(
        status_code=400,
        detail="Formato de archivo no soportado. Use .csv o .xlsx",
    )


def empty_file_error():
    raise HTTPException(
        status_code=400,
        detail="El archivo no contiene valores válidos",
    )


@router.post(
    "/validate",
    response_model=ValidationResponse,
    summary="Ejecutar pipeline completo de validación",
    description=(
        "Recibe una serie de valores numéricos"
        "y ejecuta todas las pruebas estadísticas"
        "de validación hidrológica"
    ),
)
async def validate_series(input_data: SeriesInput):
    if len(input_data.values) == 0:
        raise HTTPException(status_code=400, detail="La serie no puede estar vacía")

    try:
        series = pd.Series(input_data.values)
        return run_validation_pipeline(series)
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Error procesando la serie: {e!s}"
        ) from e


@router.post(
    "/validate/file",
    response_model=ValidationResponse,
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

        series = pd.Series(values)
        return run_validation_pipeline(series)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Error leyendo el archivo: {e!s}"
        ) from e
