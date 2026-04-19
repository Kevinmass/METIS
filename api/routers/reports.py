"""Router FastAPI para endpoints de reportes SAMHIA.

Expone los endpoints para análisis estadístico completo, generación
de PDFs y procesamiento batch de múltiples archivos.
"""

import base64
import tempfile
from io import BytesIO
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from scipy import stats


mpl.use("Agg")
import matplotlib.pyplot as plt

from api.schemas.reports import (
    BatchFileRequest,
    BatchFileResult,
    BatchProcessResponse,
    DescriptiveStatsSchema,
    HomogeneityResultsSchema,
    IndependenceResultsSchema,
    OutlierPlotRequest,
    OutlierPlotResponse,
    OutlierResultsSchema,
    PDFGenerationRequest,
    PDFGenerationResponse,
    SamhiaAnalysisRequest,
    SamhiaAnalysisResponse,
    TestResultSchema,
    TrendResultsSchema,
)
from core.reporting.pdf_generator import (
    ReportConfig,
    generate_samhia_report_pdf,
)
from core.reporting.plots import (
    plot_outliers,
    plot_probability_plot,
    plot_qq,
)
from core.validation.homogeneity import (
    cramer_test,
    helmert_test,
    mann_whitney_test,
    mood_test,
    t_student_test,
)
from core.validation.independence import (
    anderson_test,
    durbin_watson_test,
    ljung_box_test,
    spearman_test,
    wald_wolfowitz_test,
)
from core.validation.outliers import (
    chow_test,
    kn_outlier_detection,
)
from core.validation.trend import (
    kolmogorov_smirnov_trend_test,
    mann_kendall_test,
)


router = APIRouter()


def _test_result_to_schema(result) -> TestResultSchema:
    """Convierte TestResult a schema Pydantic."""
    return TestResultSchema(
        name=result.name,
        statistic=result.statistic,
        critical_value=result.critical_value,
        alpha=result.alpha,
        verdict=result.verdict,
        detail=result.detail,
    )


@router.post(
    "/analyze",
    response_model=SamhiaAnalysisResponse,
    summary="Análisis estadístico completo SAMHIA",
    description=(
        "Ejecuta el pipeline completo de análisis estadístico SAMHIA sobre una "
        "serie temporal."
    ),
)
async def analyze_samhia(request: SamhiaAnalysisRequest):
    """Ejecuta análisis estadístico completo y devuelve resultados JSON."""
    # Crear DataFrame
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(request.dates, errors="coerce"),
            request.series_name: request.data,
        }
    )
    df = df[df["date"].notna()].sort_values("date").reset_index(drop=True)

    series = pd.Series(df[request.series_name].dropna().to_numpy())

    if len(series) < 12:  # noqa: PLR2004
        raise HTTPException(
            status_code=400, detail="La serie debe tener al menos 12 datos válidos"
        )

    # Ejecutar tests
    independence_results = {
        "anderson": anderson_test(series, request.alpha),
        "wald_wolfowitz": wald_wolfowitz_test(series, request.alpha),
        "durbin_watson": durbin_watson_test(series, request.alpha),
        "ljung_box": ljung_box_test(series, alpha=request.alpha),
        "spearman": spearman_test(series, request.alpha),
    }

    homogeneity_results = {
        "helmert": helmert_test(series, request.alpha),
        "t_student": t_student_test(series, request.alpha),
        "cramer": cramer_test(series, request.alpha),
        "mann_whitney": mann_whitney_test(series, request.alpha),
        "mood": mood_test(series, request.alpha),
    }

    trend_results = {
        "mann_kendall": mann_kendall_test(series, request.alpha),
        "kolmogorov_smirnov": kolmogorov_smirnov_trend_test(series, request.alpha),
    }

    outlier_results = {
        "chow": chow_test(series),
        "kn": kn_outlier_detection(series, alpha=request.alpha),
    }

    # Estadísticas descriptivas
    values = series.to_numpy()
    descriptive_stats = DescriptiveStatsSchema(
        median=float(np.median(values)),
        mean=float(np.mean(values)),
        q25=float(np.percentile(values, 25)),
        q75=float(np.percentile(values, 75)),
        minimum=float(values.min()),
        maximum=float(values.max()),
        skewness=float(stats.skew(values)),
        kurtosis=float(stats.kurtosis(values, fisher=False)),
        std_dev=float(np.std(values, ddof=1)),
        variance=float(np.var(values, ddof=1)),
        n=len(values),
        coefficient_of_variation=(
            np.std(values, ddof=1) / np.mean(values) * 100
            if np.mean(values) != 0
            else np.nan
        ),
    )

    return SamhiaAnalysisResponse(
        series_name=request.series_name,
        reservoir_name=request.reservoir_name,
        n_data=len(values),
        descriptive_stats=descriptive_stats,
        independence=IndependenceResultsSchema(
            anderson=_test_result_to_schema(independence_results["anderson"]),
            wald_wolfowitz=_test_result_to_schema(
                independence_results["wald_wolfowitz"]
            ),
            durbin_watson=_test_result_to_schema(independence_results["durbin_watson"]),
            ljung_box=_test_result_to_schema(independence_results["ljung_box"]),
            spearman=_test_result_to_schema(independence_results["spearman"]),
        ),
        homogeneity=HomogeneityResultsSchema(
            helmert=_test_result_to_schema(homogeneity_results["helmert"]),
            t_student=_test_result_to_schema(homogeneity_results["t_student"]),
            cramer=_test_result_to_schema(homogeneity_results["cramer"]),
            mann_whitney=_test_result_to_schema(homogeneity_results["mann_whitney"]),
            mood=_test_result_to_schema(homogeneity_results["mood"]),
        ),
        trend=TrendResultsSchema(
            mann_kendall=_test_result_to_schema(trend_results["mann_kendall"]),
            kolmogorov_smirnov=_test_result_to_schema(
                trend_results["kolmogorov_smirnov"]
            ),
        ),
        outliers=OutlierResultsSchema(
            chow=_test_result_to_schema(outlier_results["chow"]),
            kn=_test_result_to_schema(outlier_results["kn"]),
        ),
    )


@router.post(
    "/pdf",
    response_model=PDFGenerationResponse,
    summary="Generar reporte PDF",
    description="Genera un reporte PDF completo de 10 páginas con análisis SAMHIA.",
)
async def generate_pdf(request: PDFGenerationRequest):
    """Genera reporte PDF y devuelve la ruta del archivo."""
    # Crear DataFrame
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(request.dates, errors="coerce"),
            request.series_name: request.data,
        }
    )
    df = df[df["date"].notna()].sort_values("date").reset_index(drop=True)

    # Configuración del reporte
    config = ReportConfig(
        series_name=request.series_name,
        reservoir_name=request.reservoir_name,
        output_path=request.output_path,
        institution=request.institution,
        report_type=request.report_type,
        author=request.author,
        alpha=request.alpha,
    )

    try:
        pdf_path = generate_samhia_report_pdf(df, config)
        return PDFGenerationResponse(
            success=True,
            pdf_path=pdf_path,
            message="PDF generado exitosamente",
        )
    except Exception as e:
        msg = f"Error generando PDF: {e!s}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get(
    "/download/{filename}",
    summary="Descargar PDF generado",
    description="Descarga un PDF previamente generado.",
)
async def download_pdf(filename: str):
    """Descarga un PDF generado."""
    # Por seguridad, validar que el archivo esté en un directorio permitido
    # En producción, usar un directorio específico y validar la ruta
    pdf_path = filename  # TODO: Validar y restringir ruta

    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise HTTPException(status_code=404, detail="PDF no encontrado")

    return FileResponse(pdf_path, media_type="application/pdf", filename=path_obj.name)


def _process_single_variable(
    var: str,
    datos: pd.DataFrame,
    output_dir: str,
    filepath: str,
    alpha: float,
) -> bool:
    """Process a single variable and generate its PDF report.

    Args:
        var: Variable name to process
        datos: DataFrame containing the data
        output_dir: Base output directory
        filepath: Original file path for naming
        alpha: Significance level for tests

    Returns:
        True if processing succeeded, False otherwise
    """
    try:
        # Crear directorio de salida
        var_output_dir = Path(output_dir) / Path(filepath).stem
        var_output_dir.mkdir(parents=True, exist_ok=True)

        # Generar PDF
        df = datos[["date", var]].copy() if "date" in datos.columns else datos
        if "date" not in df.columns:
            # Si no hay columna date, crear índice temporal
            df["date"] = pd.date_range(start="2000-01-01", periods=len(df))

        config = ReportConfig(
            series_name=var,
            reservoir_name=Path(filepath).stem,
            output_path=str(
                var_output_dir / f"REPORTE_METIS_{Path(filepath).stem}_{var}.pdf"
            ),
            alpha=alpha,
        )

        generate_samhia_report_pdf(df, config)
    except Exception:  # noqa: BLE001
        # Continuar con siguiente variable si hay error
        return False
    else:
        return True


@router.post(
    "/batch",
    response_model=BatchProcessResponse,
    summary="Procesamiento batch de archivos",
    description=(
        "Procesa múltiples archivos CSV/Excel y genera reportes PDF para cada "
        "variable."
    ),
)
async def process_batch(request: BatchFileRequest):
    """Procesa múltiples archivos en batch."""
    results = []
    successful = 0
    failed = 0

    for filepath in request.files:
        try:
            if not Path(filepath).exists():
                results.append(
                    BatchFileResult(
                        filename=filepath,
                        status="error",
                        variables_analyzed=[],
                        error_message="Archivo no encontrado",
                    )
                )
                failed += 1
                continue

            # Leer archivo (CSV o Excel)
            if filepath.lower().endswith(".csv"):
                try:
                    datos = pd.read_csv(filepath, na_values=["NA", "nan", "NaN", ""])
                except Exception:  # noqa: BLE001
                    datos = pd.read_csv(
                        filepath, sep=";", na_values=["NA", "nan", "NaN", ""]
                    )
            else:
                datos = pd.read_excel(filepath)

            # Detección de columnas numéricas
            cols_excluir = {
                "date",
                "year",
                "month",
                "day",
                "fecha",
                "año",
                "mes",
                "year_hydrological",
            }
            cols_numericas = [
                c for c in datos.columns if pd.api.types.is_numeric_dtype(datos[c])
            ]

            if len(cols_numericas) < 2:  # noqa: PLR2004
                cols_numericas = [
                    c for c in datos.columns if c.lower() not in cols_excluir
                ]

            cols_analisis = [c for c in cols_numericas if c.lower() not in cols_excluir]

            # Procesar cada variable
            variables_analyzed = [
                var
                for var in cols_analisis
                if _process_single_variable(
                    var, datos, request.output_dir, filepath, request.alpha
                )
            ]

            results.append(
                BatchFileResult(
                    filename=filepath,
                    status="success",
                    variables_analyzed=variables_analyzed,
                    pdf_path=str(Path(request.output_dir) / Path(filepath).stem),
                )
            )
            successful += 1

        except Exception as e:  # noqa: BLE001
            results.append(
                BatchFileResult(
                    filename=filepath,
                    status="error",
                    variables_analyzed=[],
                    error_message=str(e),
                )
            )
            failed += 1

    return BatchProcessResponse(
        total_files=len(request.files),
        successful=successful,
        failed=failed,
        results=results,
        output_directory=request.output_dir,
    )


@router.post(
    "/upload",
    summary="Subir archivo para análisis",
    description="Sube un archivo CSV/Excel para análisis individual.",
)
async def upload_file(
    file: UploadFile = File(...),  # noqa: B008
    reservoir_name: str = "Desconocido",
    alpha: float = 0.05,  # noqa: ARG001
):
    """Sube un archivo y devuelve información sobre las variables detectadas."""
    # Guardar archivo temporalmente
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(file.filename).suffix
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Leer archivo
        if file.filename.lower().endswith(".csv"):
            try:
                datos = pd.read_csv(tmp_path, na_values=["NA", "nan", "NaN", ""])
            except Exception:  # noqa: BLE001
                datos = pd.read_csv(
                    tmp_path, sep=";", na_values=["NA", "nan", "NaN", ""]
                )
        else:
            datos = pd.read_excel(tmp_path)

        # Detección de columnas
        cols_excluir = {
            "date",
            "year",
            "month",
            "day",
            "fecha",
            "año",
            "mes",
            "year_hydrological",
        }
        cols_numericas = [
            c for c in datos.columns if pd.api.types.is_numeric_dtype(datos[c])
        ]

        if len(cols_numericas) < 2:  # noqa: PLR2004
            cols_numericas = [c for c in datos.columns if c.lower() not in cols_excluir]

        cols_analisis = [c for c in cols_numericas if c.lower() not in cols_excluir]

        return {
            "filename": file.filename,
            "reservoir_name": reservoir_name,
            "variables_detected": cols_analisis,
            "n_variables": len(cols_analisis),
            "n_rows": len(datos),
            "message": (
                "Archivo cargado exitosamente. "
                "Use /reports/analyze para procesar una variable específica."
            ),
        }

    finally:
        # Limpiar archivo temporal
        Path(tmp_path).unlink()


@router.post(
    "/plots/outliers",
    response_model=OutlierPlotResponse,
    summary="Generar gráficos de análisis de outliers",
    description=(
        "Genera los 3 gráficos para análisis de outliers: Control Chart, "
        "Probability Plot y Q-Q Plot."
    ),
)
async def generate_outlier_plots(request: OutlierPlotRequest):
    """Genera gráficos para análisis de outliers con método Kn y Chow."""

    # Crear DataFrame
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(request.dates, errors="coerce"),
            request.series_name: request.data,
        }
    )
    df = df[df["date"].notna()].sort_values("date").reset_index(drop=True)

    series = pd.Series(df[request.series_name].dropna().to_numpy())

    if len(series) < 12:  # noqa: PLR2004
        raise HTTPException(
            status_code=400, detail="La serie debe tener al menos 12 datos válidos"
        )

    # Ejecutar test Kn para obtener límites
    kn_result = kn_outlier_detection(series, alpha=request.alpha)
    chow_test(series)

    # Extraer límites Kn
    kn_detail = kn_result.detail
    lower_limit = kn_detail.get("lower_limit")
    upper_limit = kn_detail.get("upper_limit")
    outliers_indices = kn_detail.get("outliers_indices", [])

    # Crear DataFrame de outliers para plot_outliers
    outliers_df = df.iloc[outliers_indices] if outliers_indices else pd.DataFrame()

    try:
        # Generar los 3 gráficos
        plot_urls = {}

        with tempfile.TemporaryDirectory():
            # 1. Control Chart (Serie Temporal con Umbrales)
            fig1 = plot_outliers(
                df=df,
                date_col="date",
                value_col=request.series_name,
                lower_limit=lower_limit,
                upper_limit=upper_limit,
                outliers_df=outliers_df if not outliers_df.empty else None,
                y_label=request.series_name,
            )
            buf1 = BytesIO()
            fig1.savefig(buf1, format="png", dpi=150, bbox_inches="tight")
            buf1.seek(0)
            plot_urls[
                "control_chart"
            ] = f"data:image/png;base64,{base64.b64encode(buf1.read()).decode()}"
            plt.close(fig1)

            # 2. Probability Plot en escala logarítmica
            fig2 = plot_probability_plot(
                series=series,
                lower_limit=lower_limit,
                upper_limit=upper_limit,
                distribution=request.distribution,
                y_label=request.series_name,
            )
            buf2 = BytesIO()
            fig2.savefig(buf2, format="png", dpi=150, bbox_inches="tight")
            buf2.seek(0)
            plot_urls[
                "probability_plot"
            ] = f"data:image/png;base64,{base64.b64encode(buf2.read()).decode()}"
            plt.close(fig2)

            # 3. Q-Q Plot
            fig3 = plot_qq(
                series=series,
            )
            buf3 = BytesIO()
            fig3.savefig(buf3, format="png", dpi=150, bbox_inches="tight")
            buf3.seek(0)
            plot_urls[
                "qq_plot"
            ] = f"data:image/png;base64,{base64.b64encode(buf3.read()).decode()}"
            plt.close(fig3)

        return OutlierPlotResponse(
            success=True,
            message="Gráficos generados exitosamente",
            plot_urls=plot_urls,
            kn_limits={
                "lower": lower_limit,
                "upper": upper_limit,
                "mean": kn_detail.get("mean"),
                "std_dev": kn_detail.get("std_dev"),
                "kn_value": kn_detail.get("kn_value"),
            },
            outliers_detected=len(outliers_indices),
            outliers_indices=outliers_indices,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generando gráficos: {e!s}"
        ) from e
