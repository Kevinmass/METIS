"""API REST de METIS - Punto de entrada principal.

Esta aplicación FastAPI expone el core estadístico de validación hidrológica
como servicio HTTP consumible. Proporciona endpoints para ejecutar el
pipeline completo de validación sobre series de caudales u otras variables
hidrológicas.

Endpoints principales:
    POST /validate: Ejecuta validación desde JSON.
    POST /validate/file: Ejecuta validación desde archivo CSV/Excel.
    GET /health: Verificación de estado del servicio.

Documentación interactiva:
    Swagger UI: http://localhost:8000/docs
    ReDoc: http://localhost:8000/redoc

Integración con GeoAI:
    Esta API está diseñada para ser consumida por el módulo de GeoAI.
    El schema de respuesta es estable y versionado para garantizar
    compatibilidad futura.

Ejecución local:
    uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
"""

import json
import math
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from api.middleware.error_handler import error_handler_middleware
from api.routers import frequency, reports, temporal, validate
from api.schemas.validation import HealthResponse


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles infinity and NaN values.

    Replaces:
        - inf with 1e10
        - -inf with -1e10
        - nan with None
    """

    def default(self, obj):
        """Encode object, handling special float values."""
        if isinstance(obj, float):
            if math.isinf(obj):
                return 1e10 if obj > 0 else -1e10
            if math.isnan(obj):
                return None
        return super().default(obj)


# Custom JSON response class
class CustomJSONResponse(JSONResponse):
    """JSON response that uses CustomJSONEncoder."""

    def render(self, content) -> bytes:
        """Render content using CustomJSONEncoder."""
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            cls=CustomJSONEncoder,
        ).encode("utf-8")


# Metadata descriptiva para los tags de la documentación OpenAPI.
# Cada grupo define un bloque navegable en Swagger UI / ReDoc.
openapi_tags = [
    {
        "name": "health",
        "description": (
            "Verificación de estado del servicio. "
            "Utilizado por sistemas de monitoreo y orquestación "
            "para confirmar que la API está operativa."
        ),
    },
    {
        "name": "validate",
        "description": (
            "**Validación hidrológica** — Ejecuta el pipeline completo de pruebas "
            "estadísticas sobre series de caudales u otras variables hidrológicas.\n\n"
            "Incluye:\n"
            "- **Independencia**: Anderson (principal) + "
            "Wald-Wolfowitz (verificación)\n"
            "- **Homogeneidad**: Helmert, t-Student, "
            "Cramer (sin veredicto agregado)\n"
            "- **Tendencia**: Mann-Kendall (con corrección Modified MK) + "
            "Kolmogorov-Smirnov\n"
            "- **Atípicos**: Chow (residuos studentizados) + "
            "Kn (distancia escalada)\n\n"
            "Dos vías de ingesta:\n"
            "- `POST /validate`: JSON directo con la serie numérica\n"
            "- `POST /validate/file`: Archivo CSV o Excel para subida masiva"
        ),
        "externalDocs": {
            "description": "Ver contrato de API (schema_api.md)",
            "url": "https://github.com/Kevinmass/-/blob/main/docs/schema_api.md",
        },
    },
    {
        "name": "frequency",
        "description": (
            "**Análisis de frecuencia** — Ajuste de distribuciones de "
            "probabilidad y cálculo de eventos de diseño para "
            "dimensionamiento de obras hidráulicas.\n\n"
            "Endpoints:\n"
            "- `POST /frequency/fit`: Ajusta distribuciones a una serie hidrológica\n"
            "- `POST /frequency/design-event`: Calcula evento de diseño "
            "para un período de retorno\n\n"
            "Distribuciones soportadas: Gumbel, Log-Normal, Log-Pearson III, GEV, "
            "y otras 9 del dominio hidrológico.\n"
            "Métodos de estimación: MOM, MLE, MEnt, LMom."
        ),
    },
    {
        "name": "reports",
        "description": (
            "**Reportes SAMHIA** — Análisis estadístico completo, gráficos, "
            "generación de PDFs profesionales y procesamiento batch.\n\n"
            "Endpoints:\n"
            "- `POST /reports/analyze`: Análisis SAMHIA completo "
            "con estadísticas descriptivas\n"
            "- `POST /reports/pdf`: Genera reporte PDF de 10+ páginas\n"
            "- `GET /reports/download/{filename}`: Descarga PDF generado\n"
            "- `POST /reports/batch`: Procesamiento batch de múltiples archivos\n"
            "- `POST /reports/upload`: Subida y detección de variables\n"
            "- `POST /reports/plots/outliers`: Genera gráficos de análisis de outliers"
        ),
    },
    {
        "name": "temporal",
        "description": (
            "**Agregación temporal** — Detección de frecuencia y agregación "
            "de series temporales a resoluciones superiores.\n\n"
            "Soporta agregación ascendente:\n"
            "- Minutos (5min) → Horaria → Diaria → Mensual → Anual\n"
            "- Año hidrológico configurable (default: octubre)\n"
            "- Período diario personalizado (ej: 09:00 a 09:00)\n\n"
            "Endpoints:\n"
            "- `POST /temporal/aggregate`: Agrega serie a la frecuencia objetivo\n"
            "- `POST /temporal/detect-frequency`: Detecta la frecuencia temporal\n"
            "- `POST /temporal/available-targets`: "
            "Lista frecuencias objetivo disponibles"
        ),
    },
]

# Configuración de la aplicación FastAPI
app = FastAPI(
    title="METIS API",
    description=(
        "API REST para análisis estadístico de series hidrológicas. "
        "Proporciona validación de independencia, homogeneidad, "
        "tendencia y detección de atípicos conforme a estándares "
        "de ingeniería hidrológica."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Proyecto Integrador ISI UCC",
        "url": "https://github.com/Kevinmass/METIS",
    },
    license_info={
        "name": "Proyecto Académico - UCC",
    },
    openapi_tags=openapi_tags,
    swagger_ui_parameters={
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "syntaxHighlight": {"theme": "monokai"},
        "persistAuthorization": True,
        "docExpansion": "list",
    },
    default_response_class=CustomJSONResponse,
)

# Configuración CORS - Permitir acceso desde orígenes configurados
# Usar variable de entorno FRONTEND_URL o permitir todos para prototipo
allowed_origins = os.getenv("FRONTEND_URL", "*")
if allowed_origins != "*":
    allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if isinstance(allowed_origins, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de manejo de errores matemáticos (Epic 4)
# Debe ir después de CORS para capturar errores de los routers
app.add_middleware(error_handler_middleware)

# Inclusión de routers
app.include_router(validate.router, prefix="", tags=["validate"])
app.include_router(frequency.router, prefix="/frequency", tags=["frequency"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(temporal.router)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Verifica que el servicio esté operativo y retorna info de versión.",
    response_description="Servicio operativo con estado 'ok'",
    tags=["health"],
)
async def health_check() -> dict:
    """Endpoint de verificación de salud del servicio.

    Utilizado por:
        - Monitoreo de salud (health checks)
        - Verificación de despliegue exitoso
        - Determinación de versión en uso

    Returns:
        dict con:
            - status: "ok" si el servicio está operativo
            - version: Versión actual de la API (ej: "1.0.0")

    Example:
        >>> import httpx
        >>> response = httpx.get("http://localhost:8000/health")
        >>> response.json()
        {'status': 'ok', 'version': '1.0.0'}
    """
    return {"status": "ok", "version": app.version}
