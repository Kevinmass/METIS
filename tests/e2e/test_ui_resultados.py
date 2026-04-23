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
    """Test renderizado completo de sección de resultados SAMHIA.

    Escenario:
        1. Usuario carga serie de referencia 1
        2. Ejecuta análisis SAMHIA
        3. Espera que termine el procesamiento
        4. Sistema muestra resultados estructurados

    Valida:
        - Pills de veredicto renderizados en resultados SAMHIA
        - Sin banners de error visibles
        - Sección "3. Análisis SAMHIA y Reportes PDF" visible
        - Botón de análisis habilitado nuevamente
    """
    page.goto("http://localhost:5173")

    # Scroll a sección SAMHIA
    samhia_heading = page.locator("h2", has_text="Análisis SAMHIA")
    samhia_heading.scroll_into_view_if_needed()

    # Cargar serie de referencia en sección de ingesta
    ingest_section = page.locator("section", has_text="Ingesta de datos").first
    file_input = ingest_section.locator("input[type='file']")
    file_input.set_input_files("tests/fixtures/series_referencia_1.csv")

    # Obtener sección SAMHIA y ejecutar análisis
    samhia_section = page.locator("section", has_text="Análisis SAMHIA").first
    analyze_button = samhia_section.locator(
        "button", has_text="Ejecutar análisis SAMHIA"
    )
    analyze_button.click()

    # Esperar que termine el loading y aparezcan los resultados
    expect(samhia_section.get_by_text("Ejecutar análisis SAMHIA")).to_be_enabled(
        timeout=30000
    )
    samhia_page = page
    samhia_page.wait_for_selector("text=Análisis completado", timeout=15000)

    # Ir a pestaña de Independencia para ver las pills
    samhia_section.locator("button", has_text="Independencia").click()
    expect(page.get_by_role("heading", name="Tests de Independencia")).to_be_visible()

    # Verificar pills de veredicto
    pills = page.locator("span.pill")
    expect(pills.first).to_be_visible()

    # Verificar que no hay errores
    expect(page.locator(".error-banner")).not_to_be_visible()

    # Verificar sección de resultados
    expect(page.locator("text=Resultados del análisis SAMHIA")).to_be_visible()


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
