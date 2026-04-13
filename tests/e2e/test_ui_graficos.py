from playwright.sync_api import Page, expect


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
