"""Paquete de routers - Endpoints organizados por dominio.

Este paquete agrupa los routers de FastAPI organizados por funcionalidad.
Cada módulo define endpoints relacionados siguiendo el patrón de
arquitectura por capas.

Routers disponibles:
    - validate: Endpoints de validación estadística (/validate, /validate/file)

Estructura de URL:
    Los routers se incluyen en api/main.py con app.include_router(),
    opcionalmente con prefijos comunes.

Ejemplo de inclusión:
    >>> from api.routers import validate
    >>> app.include_router(validate.router, prefix="/api/v1")

Nota:
    Los routers usan APIRouter de FastAPI para definir rutas de forma
    modular, permitiendo organización clara y reutilización.
"""

from api.routers.validate import router as router


__all__ = ["router"]
