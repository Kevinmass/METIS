from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import validate
from api.schemas.validation import HealthResponse


app = FastAPI(
    title="METIS API",
    description="API REST para análisis estadístico de series hidrológicas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(validate.router, prefix="", tags=["validate"])


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Verifica estado del servicio",
)
async def health_check():
    return {"status": "ok", "version": app.version}
