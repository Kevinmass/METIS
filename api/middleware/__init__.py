"""Middlewares personalizados para la API METIS.

Este módulo contiene middlewares para manejo de errores,
logging, y procesamiento de requests/responses.
"""

from api.middleware.error_handler import MathError, error_handler_middleware


__all__ = ["MathError", "error_handler_middleware"]
