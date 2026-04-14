"""Configuración compartida para tests E2E con Playwright.

Este módulo proporciona fixtures y configuración para tests de
extremo a extremo (E2E) que verifican la UI completa del frontend
interactuando con la API.

Requisitos:
    - API corriendo en http://localhost:8000
    - Frontend corriendo en http://localhost:5173

Preparación para CI:
    El pipeline de CI debe iniciar API y frontend antes de ejecutar
    estos tests. Ver .github/workflows/ci.yml para la configuración.
"""

import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configura el viewport del navegador para tests E2E.

    Establece resolución de 1280x720 para simular escritorio
    estándar y asegurar consistencia en capturas y posicionamiento.

    Args:
        browser_context_args: Argumentos base de Playwright

    Returns:
        dict: Argumentos mergeados con viewport configurado
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }


@pytest.fixture
def page_with_api(page):
    """Fixture de página con verificación de API disponible.

    Retorna una página de Playwright lista para usar. En futuras
    versiones podría incluir ping a /health para confirmar que
    la API está operativa antes de ejecutar tests.

    Args:
        page: Fixture base de Playwright (proporcionado por pytest-playwright)

    Returns:
        Page: Instancia de página configurada
    """
    # Aquí podríamos agregar lógica para verificar que la API esté up
    # Pero por simplicidad, asumimos que el CI lo maneja
    return page
