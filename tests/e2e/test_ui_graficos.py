from playwright.sync_api import Page, expect

"""
def test_ui_graficos_render(page: Page):
    
    page.goto("http://localhost:5173")

    # Ocultar input file
    page.evaluate(
        "document.querySelector('input[type=\"file\"]').style.display = 'none'"
    )

    # Sin datos - verificar que hay círculos por defecto (3 valores iniciales)
    expect(page.locator("circle")).to_have_count(3)

    # Agregar datos
    page.click("text=Agregar fila")
    page.click("text=Agregar fila")
    page.click("text=Agregar fila")
    page.locator("input[type='number']").nth(0).fill("1")
    page.locator("input[type='number']").nth(1).fill("2")
    page.locator("input[type='number']").nth(2).fill("3")

    # Verificar gráficos aparecen
    expect(page.locator("text=Dispersión temporal")).to_be_visible()
    expect(page.locator("circle")).to_have_count(6)  # 3 iniciales + 3 agregadas

    # Esperar a que React actualice el estado
    page.wait_for_selector("text=Dispersión temporal")

    # Verificar correlograma con pocos datos (busqueda parcial para no depender de texto exacto)
    expect(page.locator("text=4")).to_be_visible()
"""

def test_ui_graficos_completos(page: Page):
    """Test gráficos con serie completa."""
    page.goto("http://localhost:5173")

    # Ocultar input file
    page.evaluate(
        "document.querySelector('input[type=\"file\"]').style.display = 'none'"
    )

    # Cargar serie completa
    page.set_input_files("input[type='file']", "tests/fixtures/series_referencia_1.csv")

    # Verificar dispersión
    expect(page.locator("circle")).to_have_count(36)

    # Verificar correlograma
    expect(page.locator("line[stroke='#fbbf24']")).to_have_count(
        2
    )  # Bandas de confianza
