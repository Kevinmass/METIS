from playwright.sync_api import Page, expect


def test_ui_resultados(page: Page):
    """Test resultados completos del análisis."""
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
    """Test gráficos con datos reales."""
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
