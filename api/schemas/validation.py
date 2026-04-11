from typing import Literal

from pydantic import BaseModel, Field


class TestResult(BaseModel):
    name: str = Field(description="Nombre de la prueba estadística")
    statistic: float = Field(description="Valor del estadístico calculado")
    critical_value: float = Field(
        description="Valor crítico para el nivel de significancia"
    )
    alpha: float = Field(description="Nivel de significancia, siempre 0.05")
    verdict: Literal["ACCEPTED", "REJECTED"] = Field(
        description="Veredicto final de la prueba"
    )
    detail: dict = Field(
        default_factory=dict, description="Datos adicionales específicos de cada prueba"
    )


class GroupVerdict(BaseModel):
    condition: Literal["independence", "homogeneity", "trend", "outliers"] = Field(
        description="Grupo de pruebas al que pertenece"
    )
    individual_results: list[TestResult] = Field(
        description="Resultados individuales de cada prueba del grupo"
    )
    resolved_verdict: Literal["ACCEPTED", "REJECTED", "INCONCLUSIVE"] | None = Field(
        description="Veredicto resuelto para el grupo, si aplica"
    )
    hierarchy_applied: bool = Field(
        description="Indica si se aplicó regla de jerarquía para resolver el veredicto"
    )


class SeriesInput(BaseModel):
    values: list[float] = Field(
        description="Lista de valores numéricos de la serie hidrológica",
        example=[12.3, 15.7, 9.2, 18.4, 21.1],
    )


class ValidationResponse(BaseModel):
    n: int = Field(description="Cantidad de datos en la serie")
    warnings: list[dict] = Field(
        description="Lista de advertencias de inconsistencias físicas"
    )
    independence: GroupVerdict = Field(
        description="Resultados del grupo de pruebas de independencia"
    )
    homogeneity: GroupVerdict = Field(
        description="Resultados del grupo de pruebas de homogeneidad"
    )
    trend: GroupVerdict = Field(
        description="Resultados del grupo de pruebas de tendencia"
    )
    outliers: GroupVerdict = Field(
        description="Resultados del grupo de pruebas de detección de atípicos"
    )
