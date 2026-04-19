"""Schemas Pydantic - Contratos de datos de la API METIS.

Este módulo define todos los modelos de datos utilizados para la
serialización/deserialización en la API REST. Los schemas garantizan
la validación de entrada y la consistencia de la respuesta.

Jerarquía de schemas:
    SeriesInput → Validación → ValidationResponse

    ValidationResponse contiene:
        - series_id, n, warnings
        - validation: ValidationDataSchema
            - independence: IndependenceValidationSchema
            - homogeneity: HomogeneityValidationSchema
            - trend: TrendValidationSchema
            - outliers: OutliersValidationSchema

Notas de diseño:
    - Todos los campos tienen descripciones para documentación automática
    - Se incluyen ejemplos en json_schema_extra para Swagger UI
    - Los veredictos usan Literal para validación de tipo
    - Los schemas heredan de BaseModel para validación automática

Contrato de estabilidad:
    Estos schemas forman parte del contrato público de la API.
    Cambios aquí requieren incremento de versión y consideración
    de retrocompatibilidad para consumidores (frontend, GeoAI).
"""

from typing import Literal

from pydantic import BaseModel, Field


# Tipo auxiliar para veredictos de pruebas estadísticas
Verdict = Literal["ACCEPTED", "REJECTED", "INCONCLUSIVE"]


class WarningItem(BaseModel):
    """Advertencia sobre inconsistencia física detectada en la serie.

    Representa un problema detectado en los datos de entrada que no
    impide el análisis pero debe ser reportado al usuario.

    Attributes:
        code: Identificador único del tipo de advertencia.
            Valores posibles: "MISSING_VALUES", "ZERO_VALUES", "NEGATIVE_VALUES"
        message: Descripción legible para el usuario final.
        affected_indices: Lista de posiciones (0-indexed) donde ocurre.

    Example:
        >>> warning = WarningItem(
        ...     code="ZERO_VALUES",
        ...     message="Se encontraron 2 valores iguales a cero",
        ...     affected_indices=[5, 12]
        ... )
    """

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
    """Resultado de una prueba estadística individual.

    Schema de serialización para objetos TestResult del core.
    Contiene todos los campos necesarios para interpretar el resultado.

    Attributes:
        statistic: Valor numérico del estadístico calculado.
        critical_value: Valor de referencia para comparación.
        alpha: Nivel de significancia (siempre 0.05 en METIS).
        verdict: Veredicto binario "ACCEPTED" o "REJECTED".
        detail: Diccionario con datos adicionales específicos de la prueba.

    Note:
        El veredicto se determina comparando |statistic| vs critical_value.
    """

    statistic: float = Field(description="Valor del estadistico calculado")
    critical_value: float = Field(
        description="Valor critico para el nivel de significancia"
    )
    alpha: float = Field(description="Nivel de significancia, siempre 0.05")
    verdict: Literal["ACCEPTED", "REJECTED"] = Field(
        description="Veredicto final de la prueba"
    )
    detail: dict = Field(
        default_factory=dict,
        description="Detalles adicionales específicos de la prueba",
    )


class OutlierTestResultSchema(TestResultSchema):
    """Resultado del test de Chow con índices de atípicos.

        Extiende TestResultSchema agregando información específica del
    detección de outliers: los índices de los valores marcados.

        Attributes:
            flagged_indices: Posiciones (0-indexed) de valores atípicos.
                Lista vacía si no se detectaron atípicos.
    """

    flagged_indices: list[int] = Field(
        default_factory=list,
        description="Indices marcados como potenciales atipicos",
    )


class IndependenceValidationSchema(BaseModel):
    """Resultados del grupo de pruebas de independencia.

    Contiene los resultados de Anderson (principal) y Wald-Wolfowitz
    (verificación), más el veredicto resuelto aplicando jerarquía.

    Attributes:
        verdict: Veredicto consolidado del grupo.
        hierarchy_applied: True si Anderson prevaleció sobre WW.
        anderson: Resultado del test de Anderson.
        wald_wolfowitz: Resultado del test de Wald-Wolfowitz.

    Note:
        hierarchy_applied es True cuando hay desacuerdo y Anderson decide.
        El frontend usa esto para mostrar indicación visual especial.
    """

    verdict: Verdict = Field(description="Veredicto resuelto del grupo")
    hierarchy_applied: bool = Field(
        description="Indica si se aplico la jerarquia Anderson a Wald-Wolfowitz"
    )
    anderson: TestResultSchema = Field(description="Resultado del test de Anderson")
    wald_wolfowitz: TestResultSchema = Field(
        description="Resultado del test de Wald-Wolfowitz"
    )


class HomogeneityValidationSchema(BaseModel):
    """Resultados del grupo de pruebas de homogeneidad.

    Contiene los tres resultados individuales sin veredicto agregado,
    conforme al diseño de METIS (no colapsamos resultados discordantes).

    Attributes:
        individual_verdicts_only: Siempre True (flag de diseño).
        helmert: Resultado del test de Helmert (varianza).
        t_student: Resultado del test t-Student (media).
        cramer: Resultado del test de Cramer-von Mises (distribución).

    Note:
        El frontend debe mostrar los tres resultados por separado.
        No hay veredicto único para evitar falsa seguridad.
    """

    individual_verdicts_only: bool = Field(
        default=True,
        description="Siempre true, ya que no existe un veredicto agregado",
    )
    helmert: TestResultSchema = Field(description="Resultado del test de Helmert")
    t_student: TestResultSchema = Field(description="Resultado del test t-Student")
    cramer: TestResultSchema = Field(description="Resultado del test de Cramer")


class TrendValidationSchema(BaseModel):
    """Resultados del grupo de pruebas de tendencia.

    Contiene Mann-Kendall (no paramétrico, principal) y
    Kolmogorov-Smirnov (comparación de distribuciones).

    Attributes:
        mann_kendall: Resultado del test de Mann-Kendall.
        kolmogorov_smirnov: Resultado del test KS para tendencia.

    Note:
        Aunque no está en este schema, el veredicto grupal usa regla OR:
        si cualquiera de las dos rechaza, el grupo rechaza.
    """

    mann_kendall: TestResultSchema = Field(
        description="Resultado del test de Mann-Kendall"
    )
    kolmogorov_smirnov: TestResultSchema = Field(
        description="Resultado del test de Kolmogorov-Smirnov para tendencia"
    )


class OutliersValidationSchema(BaseModel):
    """Resultados del grupo de detección de atípicos.

    Contiene únicamente el resultado del test de Chow con los
    índices de valores marcados como atípicos.

    Attributes:
        chow: Resultado completo del test de Chow.
    """

    chow: OutlierTestResultSchema = Field(description="Resultado del test de Chow")


class ValidationDataSchema(BaseModel):
    """Contenedor de todos los grupos de validación.

    Agrupa los cuatro grupos de pruebas en una estructura anidada
    que facilita el consumo por parte del frontend.

    Attributes:
        independence: Grupo de pruebas de independencia.
        homogeneity: Grupo de pruebas de homogeneidad.
        trend: Grupo de pruebas de tendencia.
        outliers: Grupo de detección de atípicos.
    """

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
    """Datos de entrada para validación desde JSON.

    Schema del body para POST /validate. Recibe la serie como
    lista de números y un identificador opcional.

    Attributes:
        series: Lista de valores numéricos de la serie temporal.
            Mínimo 3 valores requeridos.
        series_id: Identificador opcional para trazabilidad.
            Si no se provee, la API genera uno automáticamente.

    Validation:
        - series: Requerido, mínimo 3 elementos
        - Valores deben ser numéricos (float)

    Example:
        >>> input_data = SeriesInput(
        ...     series=[12.5, 15.3, 14.8, 16.2, 13.9],
        ...     series_id="rio_norte_2024"
        ... )
    """

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
    """Respuesta completa del pipeline de validación.

    Schema de respuesta para POST /validate y POST /validate/file.
    Contiene todos los resultados estructurados para consumo del frontend.

    Attributes:
        series_id: Identificador de la serie (proporcionado o generado).
        n: Cantidad de observaciones válidas analizadas.
        warnings: Lista de advertencias de inconsistencias físicas.
        validation: Bloque con los cuatro grupos de resultados.

    Note:
        Este schema es el contrato principal de la API. El frontend
        y futuros consumidores (GeoAI) dependen de esta estructura.
        Cualquier cambio requiere consideración de retrocompatibilidad.

    Example:
        >>> response = ValidationResponse(
        ...     series_id="serie_123",
        ...     n=35,
        ...     warnings=[],
        ...     validation=ValidationDataSchema(...)
        ... )
    """

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
    """Respuesta del endpoint de verificación de salud.

    Schema simple para GET /health. Indica operatividad del servicio.

    Attributes:
        status: Siempre "ok" cuando el servicio está operativo.
        version: Versión semántica actual de la API (ej: "1.0.0").
    """

    status: Literal["ok"] = Field(description="Estado del servicio")
    version: str = Field(description="Version actual de la API")
