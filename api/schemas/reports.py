"""Schemas Pydantic para endpoints de reportes.

Define los modelos de datos para solicitudes y respuestas de la API
de reportes SAMHIA integrados en METIS.
"""

from typing import Any

from pydantic import BaseModel, Field


class TestResultSchema(BaseModel):
    """Esquema para resultado de un test estadístico."""

    name: str
    statistic: float
    critical_value: float | list[float] | None = None
    alpha: float
    verdict: str  # "ACCEPTED" or "REJECTED"
    detail: dict[str, Any]


class IndependenceResultsSchema(BaseModel):
    """Resultados de tests de independencia."""

    anderson: TestResultSchema
    wald_wolfowitz: TestResultSchema
    durbin_watson: TestResultSchema
    ljung_box: TestResultSchema
    spearman: TestResultSchema


class HomogeneityResultsSchema(BaseModel):
    """Resultados de tests de homogeneidad."""

    helmert: TestResultSchema
    t_student: TestResultSchema
    cramer: TestResultSchema
    mann_whitney: TestResultSchema
    mood: TestResultSchema


class TrendResultsSchema(BaseModel):
    """Resultados de tests de tendencia."""

    mann_kendall: TestResultSchema
    kolmogorov_smirnov: TestResultSchema


class OutlierResultsSchema(BaseModel):
    """Resultados de detección de outliers."""

    chow: TestResultSchema
    kn: TestResultSchema


class DescriptiveStatsSchema(BaseModel):
    """Estadísticas descriptivas de la serie."""

    median: float
    mean: float
    q25: float
    q75: float
    minimum: float
    maximum: float
    skewness: float
    kurtosis: float
    std_dev: float
    variance: float
    n: int
    coefficient_of_variation: float


class SamhiaAnalysisResponse(BaseModel):
    """Respuesta completa del análisis SAMHIA."""

    series_name: str
    reservoir_name: str
    n_data: int
    descriptive_stats: DescriptiveStatsSchema
    independence: IndependenceResultsSchema
    homogeneity: HomogeneityResultsSchema
    trend: TrendResultsSchema
    outliers: OutlierResultsSchema
    warnings: list[str] = Field(default_factory=list)


class SamhiaAnalysisRequest(BaseModel):
    """Solicitud para análisis SAMHIA."""

    series_name: str = Field(..., description="Nombre de la variable a analizar")
    reservoir_name: str = Field(..., description="Nombre del embalse")
    data: list[float] = Field(..., description="Serie temporal de valores")
    dates: list[str] = Field(..., description="Fechas correspondientes (ISO format)")
    alpha: float = Field(default=0.05, description="Nivel de significancia")


class BatchFileRequest(BaseModel):
    """Solicitud para procesamiento batch de archivos."""

    files: list[str] = Field(..., description="Rutas de archivos a procesar")
    output_dir: str = Field(..., description="Directorio de salida para resultados")
    alpha: float = Field(default=0.05, description="Nivel de significancia")


class BatchFileResult(BaseModel):
    """Resultado de procesamiento de un archivo individual."""

    filename: str
    status: str  # "success" or "error"
    variables_analyzed: list[str]
    pdf_path: str | None = None
    error_message: str | None = None


class BatchProcessResponse(BaseModel):
    """Respuesta de procesamiento batch."""

    total_files: int
    successful: int
    failed: int
    results: list[BatchFileResult]
    output_directory: str


class PDFGenerationRequest(BaseModel):
    """Solicitud para generación de PDF."""

    series_name: str
    reservoir_name: str
    data: list[float]
    dates: list[str]
    output_path: str
    alpha: float = 0.05
    institution: str = "METIS - Sistema de Análisis Hidrológico"
    report_type: str = "REPORTE DE ANÁLISIS ESTADÍSTICO"
    author: str = "Proyecto Integrador ISI UCC"


class PDFGenerationResponse(BaseModel):
    """Respuesta de generación de PDF."""

    success: bool
    pdf_path: str
    message: str


class OutlierPlotRequest(BaseModel):
    """Solicitud para generar gráficos de análisis de outliers."""

    series_name: str = Field(..., description="Nombre de la variable")
    reservoir_name: str = Field(..., description="Nombre del embalse")
    data: list[float] = Field(..., description="Serie temporal de valores")
    dates: list[str] = Field(..., description="Fechas correspondientes (ISO format)")
    alpha: float = Field(default=0.05, description="Nivel de significancia")
    distribution: str = Field(
        default="lognormal",
        description="Distribución teórica (lognormal, pearson3, gumbel)",
    )


class OutlierPlotResponse(BaseModel):
    """Respuesta con información de los gráficos generados."""

    success: bool
    message: str
    plot_urls: dict[str, str] = Field(
        default_factory=dict, description="URLs de los gráficos generados"
    )
    kn_limits: dict[str, float] = Field(
        default_factory=dict, description="Límites Kn calculados"
    )
    outliers_detected: int = Field(
        default=0, description="Cantidad de outliers detectados"
    )
    outliers_indices: list[int] = Field(
        default_factory=list, description="Índices de los outliers"
    )
