"""Tests E2E para visualización de resultados de validación.

Este módulo prueba la sección de resultados de la UI, verificando:
    - Renderizado del dashboard de resultados (modo semáforo)
    - Ausencia de errores en la UI
    - Visualización de gráficos detallados
    - Controles de la interfaz de resultados

Requiere:
    - API y frontend corriendo
    - Serie de referencia 1 disponible en fixtures
"""

from playwright.sync_api import Page, expect


def test_ui_resultados(page: Page):
    """Test renderizado completo de sección de resultados.

    Escenario:
        1. Usuario carga serie de referencia 1
        2. Ejecuta análisis
        3. Espera que termine el procesamiento
        4. Sistema muestra resultados estructurados

    Valida:
        - 4 indicadores de estado renderizados (condiciones de validación)
        - Sin banners de error visibles
        - Sección "3. Resultados de validación" visible
        - Botón "Ejecutar análisis" habilitado nuevamente
    """
    page.goto("http://localhost:5173")

    # Ocultar input file
    page.evaluate(
        "document.querySelector('input[type=\"file\"]').style.display = 'none'"
    )

    # Cargar serie de referencia 1
    page.set_input_files("input[type='file']", "tests/fixtures/series_referencia_1.csv")
    page.click("text=Ejecutar análisis")

    # Esperar que termine el loading y aparezcan los resultados
    expect(page.get_by_text("Ejecutar análisis")).to_be_enabled()
    page.wait_for_selector(".pill", state="attached")

    # Verificar semáforo
    expect(page.locator(".pill")).to_have_count(4)

    # Verificar que no hay errores
    expect(page.locator(".error-banner")).not_to_be_visible()

    # Verificar sección de resultados
    expect(page.locator("text=3. Resultados de validación")).to_be_visible()


def test_ui_graficos_detalle(page: Page):
    """Test visualización detallada de gráficos de resultados.

    Escenario:
        1. Usuario carga serie de referencia
        2. Gráficos se renderizan con datos reales

    Valida:
        - Elemento SVG de gráfico visible
        - Círculos renderizados para cada punto de dato (36)
        - Texto "Banda 95%" visible en correlograma
    """
    page.goto("http://localhost:5173")

    # Ocultar input file
    page.evaluate(
        "document.querySelector('input[type=\"file\"]').style.display = 'none'"
    )

    # Cargar serie
    page.set_input_files("input[type='file']", "tests/fixtures/series_referencia_1.csv")

    # Verificar SVG de dispersión
    svg = page.locator("svg").first
    expect(svg).to_be_visible()

    # Verificar elementos del gráfico
    expect(page.locator("circle")).to_have_count(36)  # 36 puntos

    # Verificar correlograma
    expect(page.locator("text=Banda 95%")).to_be_visible()
