"""Middleware de manejo de errores matemáticos para METIS API.

Este módulo implementa un middleware que captura errores matemáticos
comunes en análisis hidrológico y los convierte en respuestas HTTP
estructuradas con mensajes descriptivos para el frontend.

Errores capturados:
    - Divisiones por cero
    - Logaritmos de números negativos o cero
    - Overflow/underflow numérico
    - Valores infinitos o NaN
    - Errores de dominio matemático

Estructura de respuesta de error:
    {
        "error_type": "MATH_ERROR|DOMAIN_ERROR|NUMERIC_ERROR",
        "message": "Descripción legible del error",
        "detail": "Información técnica adicional",
        "suggestion": "Recomendación para el usuario"
    }
"""

from typing import Any

import numpy as np
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class MathError(Exception):
    """Excepción personalizada para errores matemáticos en hidrología."""

    def __init__(
        self,
        message: str,
        error_type: str = "MATH_ERROR",
        detail: str | None = None,
        suggestion: str | None = None,
    ):
        self.message = message
        self.error_type = error_type
        self.detail = detail
        self.suggestion = suggestion
        super().__init__(self.message)


class DomainError(MathError):
    """Error de dominio matemático (e.g., logaritmo de negativo)."""

    def __init__(
        self, message: str, detail: str | None = None, suggestion: str | None = None
    ):
        super().__init__(
            message=message,
            error_type="DOMAIN_ERROR",
            detail=detail,
            suggestion=suggestion or "Verifique que los datos sean positivos y válidos",
        )


class NumericOverflowError(MathError):
    """Error de overflow/underflow numérico."""

    def __init__(
        self, message: str, detail: str | None = None, suggestion: str | None = None
    ):
        super().__init__(
            message=message,
            error_type="NUMERIC_OVERFLOW",
            detail=detail,
            suggestion=suggestion
            or "Los valores numéricos son demasiado grandes o pequeños",
        )


class ConvergenceError(MathError):
    """Error de convergencia en algoritmos iterativos (MLE, etc.)."""

    def __init__(
        self, message: str, detail: str | None = None, suggestion: str | None = None
    ):
        super().__init__(
            message=message,
            error_type="CONVERGENCE_ERROR",
            detail=detail,
            suggestion=suggestion
            or "Intente con otro método de estimación o verifique los datos",
        )


def is_math_error(exception: Exception) -> bool:
    """Determina si una excepción es un error matemático.

    Args:
        exception: La excepción a evaluar.

    Returns:
        True si es un error matemático reconocible.
    """
    math_error_types = (
        # Python built-in
        ZeroDivisionError,
        OverflowError,
        ValueError,  # Para math domain errors
        # NumPy
        np.linalg.LinAlgError,
        FloatingPointError,
        # Errores específicos de SciPy si están disponibles
    )

    if isinstance(exception, math_error_types):
        return True

    # Verificar mensaje de error para domain errors
    error_msg = str(exception).lower()
    math_keywords = [
        "domain error",
        "math domain error",
        "logarithm",
        "negative",
        "zero",
        "divide by zero",
        "overflow",
        "underflow",
        "inf",
        "nan",
        "singular matrix",
        "convergence",
    ]

    return any(keyword in error_msg for keyword in math_keywords)


def categorize_math_error(exception: Exception) -> dict[str, Any]:
    """Categoriza un error matemático y genera respuesta estructurada.

    Args:
        exception: La excepción matemática.

    Returns:
        Diccionario con tipo de error, mensaje y sugerencia.
    """
    error_msg = str(exception).lower()
    error_type = type(exception).__name__

    # Categorización por tipo de error
    if isinstance(exception, ZeroDivisionError) or "divide by zero" in error_msg:
        return {
            "error_type": "DIVISION_BY_ZERO",
            "message": "División por cero detectada en el cálculo",
            "detail": str(exception),
            "suggestion": "Verifique que la serie no contenga valores constantes o iguales",
        }

    if "log" in error_msg or "logarithm" in error_msg or "domain error" in error_msg:
        return {
            "error_type": "LOGARITHM_DOMAIN_ERROR",
            "message": "Error en función logarítmica",
            "detail": str(exception),
            "suggestion": "Para Log-Normal o Log-Pearson III, todos los valores deben ser positivos",
        }

    if "overflow" in error_msg or isinstance(exception, OverflowError):
        return {
            "error_type": "NUMERIC_OVERFLOW",
            "message": "Desbordamiento numérico",
            "detail": str(exception),
            "suggestion": "Los valores son demasiado grandes. Considere normalizar los datos",
        }

    if "convergence" in error_msg or "failed to converge" in error_msg:
        return {
            "error_type": "CONVERGENCE_ERROR",
            "message": "El algoritmo no convergió",
            "detail": str(exception),
            "suggestion": "Intente con el método MOM (Momentos) en lugar de MLE o MEnt",
        }

    if "singular matrix" in error_msg or "linalg" in error_type.lower():
        return {
            "error_type": "SINGULAR_MATRIX",
            "message": "Matriz singular en cálculo matricial",
            "detail": str(exception),
            "suggestion": "La serie puede tener multicolinealidad o datos insuficientes",
        }

    if "inf" in error_msg or "nan" in error_msg:
        return {
            "error_type": "INVALID_NUMERIC_VALUE",
            "message": "Valores infinitos o no numéricos detectados",
            "detail": str(exception),
            "suggestion": "Verifique que los datos no contengan valores faltantes o extremos",
        }

    # Error matemático genérico
    return {
        "error_type": "MATH_ERROR",
        "message": "Error en cálculo matemático",
        "detail": str(exception),
        "suggestion": "Revise los datos de entrada y los parámetros seleccionados",
    }


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware para capturar y formatear errores matemáticos.

    Este middleware intercepta todas las excepciones matemáticas
    y las convierte en respuestas JSON estructuradas con código 422.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Procesa el request y captura errores matemáticos.

        Args:
            request: El request HTTP.
            call_next: Función para continuar con el siguiente middleware.

        Returns:
            Response normal o respuesta de error estructurada.
        """
        try:
            return await call_next(request)

        except MathError as math_exc:
            # Errores matemáticos personalizados ya están estructurados
            return JSONResponse(
                status_code=422,
                content={
                    "error_type": math_exc.error_type,
                    "message": math_exc.message,
                    "detail": math_exc.detail,
                    "suggestion": math_exc.suggestion,
                },
            )

        except Exception as exc:
            # Verificar si es un error matemático conocido
            if is_math_error(exc):
                error_info = categorize_math_error(exc)
                return JSONResponse(
                    status_code=422,
                    content=error_info,
                )

            # Re-lanzar otros errores para que se manejen normalmente
            raise


# Instancia del middleware para importación fácil
error_handler_middleware = ErrorHandlerMiddleware
