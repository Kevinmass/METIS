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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import validate
from api.schemas.validation import HealthResponse


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
)

# Configuración CORS - Permitir acceso desde cualquier origen
# Requerido para integración con frontend en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión de routers
app.include_router(validate.router, prefix="", tags=["validate"])


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
