import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }


def test_ui_ingesta_manual(page: Page):
    """Test carga manual de datos y validación visual."""
    page.goto("http://localhost:5173")

    # Ocultar el input file para evitar interferencias
    page.evaluate(
        "document.querySelector('input[type=\"file\"]').style.display = 'none'"
    )

    # Agregar filas y editar valores
    page.click("text=Agregar fila")
    page.click("text=Agregar fila")
    page.click("text=Agregar fila")

    # Editar valores
    inputs = page.locator("input[type='number']")
    inputs.nth(0).fill("12.3")
    inputs.nth(1).fill("0")  # Valor cero
    inputs.nth(2).fill("-5.2")  # Valor negativo
    inputs.nth(3).fill("18.4")
    inputs.nth(4).fill("21.1")

    # Verificar resaltado de celdas con error
    expect(page.locator("tr.cell-error")).to_have_count(
        3
    )  # 2 valores negativos/cero + 1 valor por defecto 0

    # Verificar advertencias
    expect(page.locator(".warning-banner")).to_be_visible()
    expect(
        page.locator("text=Se encontraron 3 valores negativos o cero.")
    ).to_be_visible()


def test_ui_ingesta_csv(page: Page):
    """Test carga desde archivo CSV."""
    page.goto("http://localhost:5173")

    # Simular drag & drop de archivo CSV
    page.set_input_files("input[type='file']", "tests/fixtures/series_referencia_1.csv")

    # Verificar que la serie se cargó
    inputs = page.locator("input[type='number']")
    expect(inputs).to_have_count(36)  # CSV tiene 36 valores (sin header)

    # Verificar identificador
    expect(page.locator("text=series_referencia_1.csv")).to_be_visible()


def test_ui_resultados_semaforo(page: Page):
    """Test dashboard semáforo con resultados."""
    page.goto("http://localhost:5173")

    # Ocultar input file
    page.evaluate(
        "document.querySelector('input[type=\"file\"]').style.display = 'none'"
    )

    # Cargar serie de referencia
    page.set_input_files("input[type='file']", "tests/fixtures/series_referencia_1.csv")

    # Ejecutar análisis
    page.click("text=Ejecutar análisis")

    # Esperar resultados
    expect(page.locator(".status-grid")).to_be_visible()

    # Verificar semáforo
    status_cards = page.locator(".status-card")
    expect(status_cards).to_have_count(5)

    # Verificar que al menos uno esté aceptado
    expect(page.locator(".pill.accepted")).to_have_count(2)

"""
def test_ui_paneles_expandibles(page: Page):
    
    page.goto("http://localhost:5173")

    # Ocultar input file
    page.evaluate(
        "document.querySelector('input[type=\"file\"]').style.display = 'none'"
    )

    # Cargar y analizar
    page.set_input_files("input[type='file']", "tests/fixtures/series_referencia_1.csv")
    page.click("text=Ejecutar análisis")

    # Esperar que termine el analisis completamente
    expect(page.locator(".status-grid")).to_be_visible()
    
    # Expandir panel de independencia
    page.click("text=Independencia")
    # Validacion robusta sin depender de texto exacto
    expect(page.locator(".accordion-panel")).to_be_visible()
    expect(page.locator(".veredicto")).to_be_visible()

    # Verificar tablas de resultados
    expect(page.locator("th:has-text('Estadístico')")).to_be_visible()

    # Colapsar y expandir homogeneidad
    page.click("text=Independencia")  # Colapsar
    page.click("text=Homogeneidad")
    expect(page.locator("text=No hay veredicto único.")).to_be_visible()
    expect(page.locator("text=Helmert")).to_be_visible()
    expect(page.locator("text=t-Student")).to_be_visible()
    expect(page.locator("text=Cramer")).to_be_visible()
"""

def test_ui_graficos(page: Page):
    """Test visualizaciones."""
    page.goto("http://localhost:5173")

    # Ocultar input file
    page.evaluate(
        "document.querySelector('input[type=\"file\"]').style.display = 'none'"
    )

    # Cargar serie
    page.set_input_files("input[type='file']", "tests/fixtures/series_referencia_1.csv")

    # Verificar gráfico de dispersión
    expect(page.locator("text=Dispersión temporal")).to_be_visible()
    expect(page.locator("circle")).to_have_count(36)  # 36 puntos

    # Verificar correlograma
    expect(page.locator("text=Correlograma preliminar")).to_be_visible()
    expect(page.locator("line[stroke='#7dd3fc']")).to_have_count(10)
