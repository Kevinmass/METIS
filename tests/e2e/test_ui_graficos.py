"""Tests E2E específicos para visualizaciones gráficas.

Este módulo contiene tests enfocados en verificar el correcto
renderizado de los gráficos SVG de la aplicación, incluyendo:
    - Gráfico de dispersión temporal
    - Correlograma con bandas de confianza

Nota:
    Estos tests usan selectores CSS específicos de SVG que pueden
    necesitar actualización si cambia la implementación visual.
"""

from playwright.sync_api import Page, expect


def test_ui_graficos_completos(page: Page):
    """Test renderizado completo de gráficos SVG.

    Escenario:
        1. Usuario carga serie completa (36 valores)
        2. Sistema renderiza gráficos de dispersión y correlograma

    Valida:
        - 36 círculos SVG en gráfico de dispersión (uno por dato)
        - 2 líneas de bandas de confianza en correlograma
    """
    page.goto("http://localhost:5173")

    # Ocultar input file
    page.evaluate(
        "document.querySelector('input[type=\"file\"]').style.display = 'none'"
    )

    # Cargar serie completa
    page.set_input_files("input[type='file']", "tests/fixtures/series_referencia_1.csv")

    # Verificar dispersión
    expect(page.locator("circle")).to_have_count(36)

    # Verificar correlograma - bandas de confianza (líneas amarillas)
    expect(page.locator("line[stroke='#fbbf24']")).to_have_count(2)
