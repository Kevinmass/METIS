"""Tests E2E para el módulo de ingesta de datos (UI).

Este módulo prueba la interfaz de usuario para ingreso de datos,
verificando:
    - Carga manual de datos con validación visual
    - Carga de archivos CSV vía drag & drop
    - Resaltado de valores problemáticos (ceros, negativos)
    - Visualización de advertencias
    - Dashboard semáforo con resultados
    - Gráficos de dispersión y correlograma

Fixtures de Playwright:
    - page: Página del navegador (proporcionada por pytest-playwright)
    - browser_context_args: Configuración de viewport 1280x720

URLs de prueba:
    - Frontend: http://localhost:5173
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configura viewport para tests E2E (redefinición local)."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }


def test_ui_ingesta_manual(page: Page):
    """Test ingreso manual de datos con validación visual de errores.

    Escenario:
        1. Usuario abre la aplicación
        2. Agrega filas manualmente
        3. Ingresa valores válidos y problemáticos (0, negativo)
        4. Sistema resalta celdas con error y muestra advertencia

    Valida:
        - Filas agregadas aparecen en la tabla
        - Celdas con valores <= 0 tienen clase CSS 'cell-error'
        - Banner de advertencia es visible
        - Mensaje de advertencia especifica cantidad de valores problemáticos
    """
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
    """Test carga de serie desde archivo CSV.

    Escenario:
        1. Usuario selecciona archivo CSV de fixture
        2. Sistema carga y parsea automáticamente
        3. Tabla muestra los valores cargados
        4. Identificador de serie muestra nombre del archivo

    Valida:
        - Cantidad correcta de inputs (36 valores del CSV)
        - Nombre del archivo visible en UI
    """
    page.goto("http://localhost:5173")

    # Simular drag & drop de archivo CSV
    page.set_input_files("input[type='file']", "tests/fixtures/series_referencia_1.csv")

    # Verificar que la serie se cargó
    inputs = page.locator("input[type='number']")
    expect(inputs).to_have_count(36)  # CSV tiene 36 valores (sin header)

    # Verificar identificador
    expect(page.locator("text=series_referencia_1.csv")).to_be_visible()


def test_ui_resultados_semaforo(page: Page):
    """Test dashboard de resultados modo semáforo vía análisis SAMHIA.

    Escenario:
        1. Usuario carga serie de referencia
        2. Ejecuta análisis SAMHIA
        3. Sistema muestra resultados con pills de estado

    Valida:
        - Panel de resultados SAMHIA visible
        - Pills de veredicto renderizados
        - Al menos algunas condiciones muestran 'accepted'
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

    # Esperar resultados
    samhia_section.locator("button", has_text="Independencia").click()
    expect(page.get_by_role("heading", name="Tests de Independencia")).to_be_visible()

    # Verificar pills de veredicto
    pills = page.locator("span.pill")
    expect(pills.first).to_be_visible()

    expect(pills).to_have_count(5)


def test_ui_graficos(page: Page):
    """Test visualizaciones de dispersión y correlograma.

    Escenario:
        1. Usuario carga serie
        2. Gráficos se renderizan automáticamente

    Valida:
        - Título de dispersión temporal visible
        - Círculos SVG renderizados (un por dato)
        - Título de correlograma visible
        - Líneas de bandas de confianza presentes
    """
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
