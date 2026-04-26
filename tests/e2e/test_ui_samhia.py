"""Tests E2E para el módulo SAMHIA del frontend.

Este módulo contiene pruebas end-to-end que verifican la interacción
completa del usuario con la interfaz de análisis estadístico SAMHIA.

Las pruebas cubren:
- Acceso a la sección SAMHIA en la UI unificada
- Carga de archivos CSV/Excel
- Configuración de parámetros del análisis
- Ejecución del análisis estadístico completo
- Visualización de resultados por categoría
- Generación y descarga de reportes PDF

Requisitos:
    - API corriendo en http://localhost:8000
    - Frontend corriendo en http://localhost:5173
    - pytest-playwright instalado

Nota: Después de la unificación del frontend, SAMHIA está integrado
en la página principal como la "Sección 5: Análisis SAMHIA".
"""

import pytest
from playwright.sync_api import Page, expect


# URL del frontend
FRONTEND_URL = "http://localhost:5173"
API_HEALTH_URL = "http://localhost:8000/health"


@pytest.fixture
def samhia_page(page: Page):
    """Fixture que navega a la página principal donde está integrado SAMHIA."""
    page.goto(FRONTEND_URL)
    # El módulo SAMHIA está ahora en la misma página, hacer scroll para verlo
    samhia_heading = page.locator("h2", has_text="Análisis SAMHIA")
    samhia_heading.scroll_into_view_if_needed()
    return page


class TestUISamhiaNavigation:
    """Tests de navegación al módulo SAMHIA (ahora integrado en la página principal)."""

    def test_samhia_section_visible(self, page_with_api: Page):
        """Test de que la sección SAMHIA es visible en la página principal."""
        page_with_api.goto(FRONTEND_URL)
        samhia_heading = page_with_api.locator("h2", has_text="Análisis SAMHIA")
        expect(samhia_heading).to_be_visible()

    def test_samhia_section_scrollable(self, page_with_api: Page):
        """Test de que se puede hacer scroll a la sección SAMHIA."""
        page_with_api.goto(FRONTEND_URL)
        samhia_heading = page_with_api.locator("h2", has_text="Análisis SAMHIA")
        samhia_heading.scroll_into_view_if_needed()
        expect(samhia_heading).to_be_in_viewport()

    def test_samhia_header_rendered(self, samhia_page: Page):
        """Test de que el encabezado de la sección SAMHIA se renderiza correctamente."""
        header = samhia_page.locator("h2", has_text="Análisis SAMHIA")
        expect(header).to_be_visible()

    def test_samhia_description_rendered(self, samhia_page: Page):
        """Test de que la descripción del módulo SAMHIA se muestra."""
        # La sección SAMHIA está en App.jsx con título
        # "3. Análisis SAMHIA y Reportes PDF" y descripción actual
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA y Reportes PDF"
        ).first
        description = samhia_section.locator("p").first
        expect(description).to_contain_text(
            "Análisis estadístico completo basado en SAMHIA_EST.R con tests detallados"
        )


class TestUISamhiaDataIngest:
    """Tests de carga de datos en el módulo SAMHIA."""

    def test_file_dropzone_visible(self, samhia_page: Page):
        """Test de que la zona de drop de archivos es visible."""
        dropzone = samhia_page.get_by_text("Arrastra un CSV o Excel aquí")
        expect(dropzone).to_be_visible()

    def test_file_input_accepts_csv(self, samhia_page: Page):
        """Test de que el input de archivo acepta CSV."""
        file_input = samhia_page.locator("input[type='file']")
        expect(file_input).to_have_attribute("accept", ".csv,.xlsx,.xls")

    def test_reservoir_name_input(self, samhia_page: Page):
        """Test del input de nombre de embalse."""
        # Buscar dentro de la sección SAMHIA (despues de hacer scroll)
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        label = samhia_section.locator("label", has_text="Nombre del embalse")
        expect(label).to_be_visible()

    def test_series_name_input(self, samhia_page: Page):
        """Test del input de nombre de variable."""
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        label = samhia_section.locator("label", has_text="Nombre de la variable")
        expect(label).to_be_visible()

    def test_alpha_selector(self, samhia_page: Page):
        """Test del selector de nivel de significancia."""
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        label = samhia_section.locator("label", has_text="Nivel de significancia")
        expect(label).to_be_visible()

        select = samhia_section.locator("select").first
        expect(select).to_be_visible()
        expect(select).to_have_value("0.05")

    def test_upload_csv_file(self, samhia_page: Page, tmp_path):
        """Test de carga de archivo CSV via sección SAMHIA."""
        # Primero subir archivo en la sección de ingesta (antes de SAMHIA)
        csv_file = tmp_path / "test_data.csv"
        csv_content = "date,value\n2020-01-01,10.5\n2020-02-01,12.3\n2020-03-01,8.7\n"
        for i in range(4, 16):  # Añadir más filas para cumplir mínimo de 12 datos
            csv_content += f"2020-{i:02d}-01,{10 + i}\n"
        csv_file.write_text(csv_content)

        # Subir archivo en la sección 1 (ingesta de datos)
        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación (preview -> importar -> procesar -> continuar)
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Los datos se comparten con la sección SAMHIA
        # Verificar que el botón de análisis SAMHIA está habilitado
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        analyze_button = samhia_section.locator(
            "button", has_text="Ejecutar análisis SAMHIA"
        )
        expect(analyze_button).to_be_enabled()

    def test_series_summary_displayed_after_upload(self, samhia_page: Page, tmp_path):
        """Test de que el resumen de la serie se muestra después de cargar datos."""
        # Crear archivo CSV de prueba con suficientes datos
        csv_file = tmp_path / "test_summary.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i * 2}\n"
        csv_file.write_text(csv_content)

        # Subir archivo en la sección de ingesta
        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Verificar resumen en sección SAMHIA (ahora muestra 15 datos)
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        # El resumen se muestra en la sección 2 (Resumen de la serie)
        summary = samhia_page.locator("section", has_text="Resumen de la serie").first
        expect(summary).to_contain_text("15")


class TestUISamhiaAnalysisExecution:
    """Tests de ejecución del análisis SAMHIA."""

    def test_analyze_button_disabled_without_sufficient_data(self, samhia_page: Page):
        """Test de que el botón de análisis está deshabilitado sin suficientes datos."""
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        analyze_button = samhia_section.locator(
            "button", has_text="Ejecutar análisis SAMHIA"
        )
        # El botón está deshabilitado si hay menos de 12 datos válidos
        expect(analyze_button).to_be_disabled()

    def test_analyze_button_enabled_with_data(self, samhia_page: Page, tmp_path):
        """Test de que el botón de análisis se habilita con datos válidos."""
        # Crear archivo CSV con suficientes datos
        csv_file = tmp_path / "test_analyze.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        # Subir archivo en la sección de ingesta
        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Verificar botón habilitado en sección SAMHIA
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        analyze_button = samhia_section.locator(
            "button", has_text="Ejecutar análisis SAMHIA"
        )
        expect(analyze_button).to_be_enabled()

    def test_analyze_button_shows_loading(self, samhia_page: Page, tmp_path):
        """Test de que el botón muestra estado de carga durante análisis."""
        # Crear archivo CSV con suficientes datos
        csv_file = tmp_path / "test_loading.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        # Subir archivo en la sección de ingesta
        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Clic en analizar en sección SAMHIA
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        analyze_button = samhia_section.locator(
            "button", has_text="Ejecutar análisis SAMHIA"
        )
        analyze_button.click()

        # Verificar estado de carga
        expect(
            samhia_section.locator("button", has_text="Analizando...")
        ).to_be_visible()

    def test_error_message_for_insufficient_data(self, samhia_page: Page, tmp_path):
        """Test de mensaje de error con datos insuficientes."""
        # Crear archivo CSV con pocos datos
        csv_file = tmp_path / "test_small.csv"
        csv_content = "date,value\n2020-01-01,10\n2020-02-01,12\n"
        csv_file.write_text(csv_content)

        # Subir archivo en la sección de ingesta
        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Verificar mensaje de error en sección SAMHIA
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        error_message = samhia_section.get_by_text("al menos 12 datos")
        expect(error_message).to_be_visible()


class TestUISamhiaResultsDisplay:
    """Tests de visualización de resultados del análisis."""

    def test_results_tabs_visible_after_analysis(self, samhia_page: Page, tmp_path):
        """Test de que las pestañas de resultados son visibles después del análisis."""
        # Crear y subir archivo en la sección de ingesta
        csv_file = tmp_path / "test_results.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Ejecutar análisis en sección SAMHIA
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        analyze_button = samhia_section.locator(
            "button", has_text="Ejecutar análisis SAMHIA"
        )
        analyze_button.click()

        # Esperar resultados
        samhia_page.wait_for_selector("text=Análisis completado", timeout=10000)

        # Verificar pestañas
        expect(
            samhia_section.locator("button", has_text="Estadísticas")
        ).to_be_visible()
        expect(
            samhia_section.locator("button", has_text="Independencia")
        ).to_be_visible()
        expect(
            samhia_section.locator("button", has_text="Homogeneidad")
        ).to_be_visible()
        expect(samhia_section.locator("button", has_text="Tendencia")).to_be_visible()
        expect(samhia_section.locator("button", has_text="Atípicos")).to_be_visible()

    def test_descriptive_stats_panel(self, samhia_page: Page, tmp_path):
        """Test del panel de estadísticas descriptivas."""
        # Crear y subir archivo
        csv_file = tmp_path / "test_stats.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Ejecutar análisis en sección SAMHIA
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        samhia_section.locator("button", has_text="Ejecutar análisis SAMHIA").click()
        samhia_page.wait_for_selector("text=Análisis completado", timeout=10000)

        # Verificar panel de estadísticas (debería estar activo por defecto)
        stats_panel = samhia_section.locator("text=Estadísticas Descriptivas")
        expect(stats_panel).to_be_visible()

    def test_independence_tab_content(self, samhia_page: Page, tmp_path):
        """Test del contenido de la pestaña de independencia."""
        # Crear y subir archivo
        csv_file = tmp_path / "test_indep.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Ejecutar análisis en sección SAMHIA
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        samhia_section.locator("button", has_text="Ejecutar análisis SAMHIA").click()
        samhia_page.wait_for_selector("text=Análisis completado", timeout=10000)

        # Clic en pestaña de independencia
        samhia_section.locator("button", has_text="Independencia").click()

        # Verificar contenido - el título se renderiza como h4
        expect(
            samhia_section.locator("h4", has_text="Tests de Independencia")
        ).to_be_visible()
        # Los tests de independencia incluyen Anderson y Wald-Wolfowitz (con sufijo)
        expect(
            samhia_section.get_by_text("Anderson (Pearson)", exact=True)
        ).to_be_visible()
        expect(
            samhia_section.get_by_text("Wald-Wolfowitz (Runs)", exact=True)
        ).to_be_visible()

    def test_verdict_pills_displayed(self, samhia_page: Page, tmp_path):
        """Test de que los veredictos se muestran con pills."""
        # Crear y subir archivo
        csv_file = tmp_path / "test_verdict.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Ejecutar análisis en sección SAMHIA
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        samhia_section.locator("button", has_text="Ejecutar análisis SAMHIA").click()
        samhia_page.wait_for_selector("text=Análisis completado", timeout=10000)

        # Ir a pestaña de Independencia para ver las pills de veredicto
        samhia_section.locator("button", has_text="Independencia").click()
        # Las pills están en las tablas de tests
        pills = samhia_page.locator("span.pill")
        expect(pills.first).to_be_visible()


class TestUISamhiaPdfGeneration:
    """Tests de generación y descarga de PDF."""

    def test_pdf_section_visible(self, samhia_page: Page):
        """Test de que la sección de PDF es visible dentro del módulo SAMHIA."""
        # La sección PDF está integrada en "5. Análisis SAMHIA y Reportes PDF"
        # Buscar el botón "Generar reporte PDF" que es el elemento principal
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA y Reportes PDF"
        ).first
        pdf_button = samhia_section.locator("button", has_text="Generar reporte PDF")
        expect(pdf_button).to_be_visible()

    def test_pdf_button_disabled_without_data(self, samhia_page: Page):
        """Test de que el botón de PDF está deshabilitado sin datos suficientes."""
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        pdf_button = samhia_section.locator("button", has_text="Generar reporte PDF")
        expect(pdf_button).to_be_disabled()

    def test_pdf_button_enabled_with_data(self, samhia_page: Page, tmp_path):
        """Test de que el botón de PDF se habilita con datos."""
        # Crear archivo CSV
        csv_file = tmp_path / "test_pdf.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        # Subir archivo en la sección de ingesta
        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Verificar botón habilitado en sección SAMHIA
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        pdf_button = samhia_section.locator("button", has_text="Generar reporte PDF")
        expect(pdf_button).to_be_enabled()

    def test_pdf_generation_loading_state(self, samhia_page: Page, tmp_path):
        """Test de estado de carga durante generación de PDF."""
        # Crear y subir archivo
        csv_file = tmp_path / "test_pdf_gen.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Clic en generar PDF
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        pdf_button = samhia_section.locator("button", has_text="Generar reporte PDF")
        pdf_button.click()

        # Verificar estado de carga
        expect(
            samhia_section.locator("button", has_text="Generando PDF...")
        ).to_be_visible()

    def test_download_button_appears_after_generation(
        self, samhia_page: Page, tmp_path
    ):
        """Test de que aparece botón de descarga después de generar PDF."""
        # Crear y subir archivo
        csv_file = tmp_path / "test_download.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Esperar a que el archivo se procese y el resumen se actualice
        summary_section = samhia_page.locator(
            "section", has_text="Resumen de la serie"
        ).first
        expect(summary_section).to_contain_text("15")

        # Scroll a la sección SAMHIA para asegurar que está visible
        samhia_heading = samhia_page.locator("h2", has_text="Análisis SAMHIA")
        samhia_heading.scroll_into_view_if_needed()

        # Generar PDF
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        pdf_button = samhia_section.locator("button", has_text="Generar reporte PDF")
        expect(pdf_button).to_be_enabled(timeout=5000)
        pdf_button.click()

        # Esperar a que termine la generación (el botón vuelve a su estado normal)
        expect(pdf_button).to_have_text("Generar reporte PDF", timeout=20000)

        # Verificar si hay mensaje de error
        error_banner = samhia_section.locator("div.error-banner")
        if error_banner.is_visible():
            error_text = error_banner.text_content()
            pytest.fail(f"Error generando PDF: {error_text}")

        # Verificar botón de descarga (puede tardar en aparecer)
        download_button = samhia_section.locator("button", has_text="Descargar PDF")
        expect(download_button).to_be_visible(timeout=5000)
        expect(download_button).to_be_enabled()


class TestUISamhiaCompleteWorkflow:
    """Tests de flujo completo de trabajo SAMHIA."""

    def test_complete_analysis_workflow(self, samhia_page: Page, tmp_path):
        """Test del flujo completo: carga -> análisis -> resultados -> PDF."""
        # 1. Crear archivo CSV de prueba
        csv_file = tmp_path / "test_workflow.csv"
        csv_content = "date,value\n"
        for i in range(20):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i * 1.5}\n"
        csv_file.write_text(csv_content)

        # 2. Cargar archivo en sección de ingesta
        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # 3. Completar flujo de importación (preview -> importar -> procesar)
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Verificar carga exitosa
        summary_section = samhia_page.locator(
            "section", has_text="Resumen de la serie"
        ).first
        expect(summary_section).to_contain_text("20")

        # 4. Obtener sección SAMHIA
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first

        # 5. Configurar parámetros
        samhia_section.locator("input[type='text']").first.fill("Embalse de Prueba")
        samhia_section.locator("input[type='text']").nth(1).fill("Caudal Mensual")

        # 5. Ejecutar análisis
        analyze_button = samhia_section.locator(
            "button", has_text="Ejecutar análisis SAMHIA"
        )
        analyze_button.click()

        # Esperar resultados
        samhia_page.wait_for_selector("text=Análisis completado", timeout=10000)

        # 6. Verificar todas las pestañas de resultados
        expect(
            samhia_section.locator("button", has_text="Estadísticas")
        ).to_be_visible()
        expect(
            samhia_section.locator("button", has_text="Independencia")
        ).to_be_visible()
        expect(
            samhia_section.locator("button", has_text="Homogeneidad")
        ).to_be_visible()
        expect(samhia_section.locator("button", has_text="Tendencia")).to_be_visible()
        expect(samhia_section.locator("button", has_text="Atípicos")).to_be_visible()

        # 7. Navegar por las pestañas
        samhia_section.locator("button", has_text="Independencia").click()
        expect(
            samhia_section.locator("h4", has_text="Tests de Independencia")
        ).to_be_visible()

        samhia_section.locator("button", has_text="Homogeneidad").click()
        expect(
            samhia_section.locator("h4", has_text="Tests de Homogeneidad")
        ).to_be_visible()

        samhia_section.locator("button", has_text="Tendencia").click()
        expect(
            samhia_section.locator("h4", has_text="Tests de Tendencia")
        ).to_be_visible()

        # 8. Generar PDF
        pdf_button = samhia_section.locator("button", has_text="Generar reporte PDF")
        expect(pdf_button).to_be_enabled(timeout=5000)
        pdf_button.click()

        # Esperar a que termine la generación (el botón vuelve a su estado normal)
        expect(pdf_button).to_have_text("Generar reporte PDF", timeout=20000)

        # Verificar si hay mensaje de error
        error_banner = samhia_section.locator("div.error-banner")
        if error_banner.is_visible():
            error_text = error_banner.text_content()
            pytest.fail(f"Error generando PDF: {error_text}")

        # 9. Verificar éxito - botón de descarga visible y mensaje de éxito
        download_button = samhia_section.locator("button", has_text="Descargar PDF")
        expect(download_button).to_be_visible(timeout=5000)
        expect(download_button).to_be_enabled()
        expect(samhia_section.locator("text=PDF generado exitosamente")).to_be_visible()

    def test_data_preserved_when_scrolling(self, samhia_page: Page, tmp_path):
        """Test de que los datos se preservan al hacer scroll."""
        # Crear y cargar archivo
        csv_file = tmp_path / "test_preserve.csv"
        csv_content = "date,value\n"
        for i in range(15):
            csv_content += f"2020-{((i % 12) + 1):02d}-15,{10 + i}\n"
        csv_file.write_text(csv_content)

        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Hacer scroll a otra sección y volver
        samhia_heading = samhia_page.locator("h2", has_text="Análisis SAMHIA")
        samhia_heading.scroll_into_view_if_needed()

        # Verificar que los datos siguen cargados en resumen
        summary_section = samhia_page.locator(
            "section", has_text="Resumen de la serie"
        ).first
        expect(summary_section).to_contain_text("15")


class TestUISamhiaEdgeCases:
    """Tests de casos edge y manejo de errores."""

    def test_invalid_file_format(self, samhia_page: Page, tmp_path):
        """Test de manejo de formato de archivo inválido."""
        # Crear archivo de texto no CSV
        txt_file = tmp_path / "invalid.txt"
        txt_file.write_text("esto no es un csv valido")

        # Intentar subir en sección de ingesta
        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        # Nota: Playwright puede no rechazar esto automáticamente,
        # pero el frontend debería manejarlo

    def test_empty_csv_file(self, samhia_page: Page, tmp_path):
        """Test de manejo de archivo CSV vacío."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("date,value\n")

        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Esperar preview y click en importar
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()

        # Debería mostrar error después de intentar importar
        expect(
            ingest_section.locator("text=No se encontraron valores numéricos")
        ).to_be_visible()

    def test_csv_with_missing_values(self, samhia_page: Page, tmp_path):
        """Test de manejo de CSV con valores faltantes."""
        csv_file = tmp_path / "missing.csv"
        csv_content = "date,value\n2020-01-01,10\n2020-02-01,\n2020-03-01,15\n"
        # Añadir más filas válidas
        for i in range(3, 15):
            csv_content += f"2020-{((i % 12) + 1):02d}-01,{10 + i}\n"
        csv_file.write_text(csv_content)

        ingest_section = samhia_page.locator(
            "section", has_text="Ingesta de datos"
        ).first
        file_input = ingest_section.locator("input[type='file']")
        file_input.set_input_files(str(csv_file))

        # Completar flujo de importación
        expect(samhia_page.locator("text=Preview:")).to_be_visible()
        samhia_page.get_by_role("button", name="Importar datos").click()
        expect(samhia_page.locator("text=Procesamiento Temporal")).to_be_visible()
        samhia_page.get_by_role("button", name="Continuar al análisis").click()

        # Debería cargar los datos válidos y mostrar resumen
        summary_section = samhia_page.locator(
            "section", has_text="Resumen de la serie"
        ).first
        expect(summary_section).to_be_visible()

    def test_very_long_series_name(self, samhia_page: Page):
        """Test de manejo de nombre de serie muy largo."""
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        series_input = samhia_section.locator("input[type='text']").nth(1)
        long_name = "A" * 100
        series_input.fill(long_name)
        expect(series_input).to_have_value(long_name)

    def test_special_characters_in_names(self, samhia_page: Page):
        """Test de manejo de caracteres especiales en nombres."""
        samhia_section = samhia_page.locator(
            "section", has_text="Análisis SAMHIA"
        ).first
        reservoir_input = samhia_section.locator("input[type='text']").first
        special_name = "Embalse_Niño-Mañana"
        reservoir_input.fill(special_name)
        expect(reservoir_input).to_have_value(special_name)
