from typing import Literal

from pydantic import BaseModel, Field


Verdict = Literal["ACCEPTED", "REJECTED", "INCONCLUSIVE"]


class WarningItem(BaseModel):
    code: str = Field(
        description="Codigo unico de la advertencia",
        json_schema_extra={"example": "ZERO_VALUES"},
    )
    message: str = Field(
        description="Descripcion legible de la advertencia",
        json_schema_extra={"example": "Se encontraron 1 valores iguales a cero"},
    )
    affected_indices: list[int] = Field(
        default_factory=list,
        description="Indices afectados por la inconsistencia detectada",
        json_schema_extra={"example": [10]},
    )


class TestResultSchema(BaseModel):
    statistic: float = Field(description="Valor del estadistico calculado")
    critical_value: float = Field(
        description="Valor critico para el nivel de significancia"
    )
    alpha: float = Field(description="Nivel de significancia, siempre 0.05")
    verdict: Literal["ACCEPTED", "REJECTED"] = Field(
        description="Veredicto final de la prueba"
    )


class OutlierTestResultSchema(TestResultSchema):
    flagged_indices: list[int] = Field(
        default_factory=list,
        description="Indices marcados como potenciales atipicos",
    )


class IndependenceValidationSchema(BaseModel):
    verdict: Verdict = Field(description="Veredicto resuelto del grupo")
    hierarchy_applied: bool = Field(
        description="Indica si se aplico la jerarquia Anderson a Wald-Wolfowitz"
    )
    anderson: TestResultSchema = Field(description="Resultado del test de Anderson")
    wald_wolfowitz: TestResultSchema = Field(
        description="Resultado del test de Wald-Wolfowitz"
    )


class HomogeneityValidationSchema(BaseModel):
    individual_verdicts_only: bool = Field(
        default=True,
        description="Siempre true, ya que no existe un veredicto agregado",
    )
    helmert: TestResultSchema = Field(description="Resultado del test de Helmert")
    t_student: TestResultSchema = Field(description="Resultado del test t-Student")
    cramer: TestResultSchema = Field(description="Resultado del test de Cramer")


class TrendValidationSchema(BaseModel):
    mann_kendall: TestResultSchema = Field(
        description="Resultado del test de Mann-Kendall"
    )
    kolmogorov_smirnov: TestResultSchema = Field(
        description="Resultado del test de Kolmogorov-Smirnov para tendencia"
    )


class OutliersValidationSchema(BaseModel):
    chow: OutlierTestResultSchema = Field(description="Resultado del test de Chow")


class ValidationDataSchema(BaseModel):
    independence: IndependenceValidationSchema = Field(
        description="Resultados del grupo de independencia"
    )
    homogeneity: HomogeneityValidationSchema = Field(
        description="Resultados del grupo de homogeneidad"
    )
    trend: TrendValidationSchema = Field(
        description="Resultados del grupo de tendencia"
    )
    outliers: OutliersValidationSchema = Field(
        description="Resultados del grupo de deteccion de atipicos"
    )


class SeriesInput(BaseModel):
    series: list[float] = Field(
        description="Lista de valores numericos de la serie hidrologica",
        json_schema_extra={"example": [12.3, 15.7, 9.2, 18.4, 21.1]},
    )
    series_id: str | None = Field(
        default=None,
        description="Identificador opcional de la serie para trazabilidad",
        json_schema_extra={"example": "serie_referencia_1"},
    )


class ValidationResponse(BaseModel):
    series_id: str = Field(
        description="Identificador de la serie analizada",
        json_schema_extra={"example": "serie_referencia_1"},
    )
    n: int = Field(
        description="Cantidad de datos en la serie",
        json_schema_extra={"example": 35},
    )
    warnings: list[WarningItem] = Field(
        default_factory=list,
        description="Lista de advertencias de inconsistencias fisicas",
    )
    validation: ValidationDataSchema = Field(
        description="Bloque agrupado con todos los resultados de validacion"
    )


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(description="Estado del servicio")
    version: str = Field(description="Version actual de la API")
