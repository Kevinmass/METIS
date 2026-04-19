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

from api.routers import frequency, reports, validate
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

# Inclusión de routers
app.include_router(validate.router, prefix="", tags=["validate"])
app.include_router(frequency.router, prefix="/frequency", tags=["frequency"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Verifica que el servicio esté operativo y retorna info de versión.",
    response_description="Servicio operativo con estado 'ok'",
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
