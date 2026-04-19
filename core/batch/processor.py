"""Procesador batch para análisis SAMHIA de múltiples archivos.

Orquesta el procesamiento de múltiples archivos CSV/Excel,
ejecutando el análisis completo SAMHIA para cada variable detectada.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from core.batch.io_handlers import (
    detect_date_column,
    detect_numeric_columns,
    prepare_dataframe_for_analysis,
    read_file_intelligent,
    validate_dataframe_for_analysis,
)
from core.reporting.pdf_generator import ReportConfig, generate_samhia_report_pdf


@dataclass
class BatchConfig:
    """Configuración para procesamiento batch."""

    output_dir: str
    alpha: float = 0.05
    institution: str = "METIS - Sistema de Análisis Hidrológico"
    report_type: str = "REPORTE DE ANÁLISIS ESTADÍSTICO"
    author: str = "Proyecto Integrador ISI UCC"
    max_workers: int = 4  # Número de workers para procesamiento paralelo


@dataclass
class FileResult:
    """Resultado de procesamiento de un archivo."""

    filename: str
    status: str  # "success", "error", "skipped"
    variables_analyzed: list[str]
    output_paths: dict[str, str]  # variable -> pdf_path
    error_message: str | None = None
    n_rows: int = 0


class BatchProcessor:
    """Procesador batch para análisis SAMHIA."""

    def __init__(self, config: BatchConfig):
        """Inicializa el procesador batch.

        Args:
            config: Configuración del procesamiento batch.
        """
        self.config = config
        self.results: list[FileResult] = []

    def process_file(self, filepath: str) -> FileResult:
        """Procesa un solo archivo individual.

        Args:
            filepath: Ruta del archivo a procesar.

        Returns:
            FileResult con el resultado del procesamiento.
        """
        path_obj = Path(filepath)
        filename = path_obj.name
        reservoir_name = path_obj.stem

        try:
            # Leer archivo
            df = read_file_intelligent(filepath)

            # Validar DataFrame
            is_valid, error_msg = validate_dataframe_for_analysis(df)
            if not is_valid:
                result = FileResult(
                    filename=filename,
                    status="skipped",
                    variables_analyzed=[],
                    output_paths={},
                    error_message=error_msg,
                    n_rows=len(df),
                )
                self.results.append(result)
                return result

            # Detectar columnas numéricas
            numeric_cols = detect_numeric_columns(df)
            date_col = detect_date_column(df)

            if not numeric_cols:
                result = FileResult(
                    filename=filename,
                    status="skipped",
                    variables_analyzed=[],
                    output_paths={},
                    error_message="No se detectaron columnas numéricas",
                    n_rows=len(df),
                )
                self.results.append(result)
                return result

            # Crear directorio de salida
            output_dir = Path(self.config.output_dir) / reservoir_name
            output_dir.mkdir(parents=True, exist_ok=True)

            # Procesar cada variable
            variables_analyzed = []
            output_paths = {}

            for var in numeric_cols:
                try:
                    # Preparar DataFrame para esta variable
                    df_prep = prepare_dataframe_for_analysis(
                        df, date_column=date_col, value_column=var
                    )

                    # Verificar suficientes datos
                    if len(df_prep) < 12:  # noqa: PLR2004
                        continue

                    # Configurar reporte
                    pdf_path = str(
                        output_dir / f"REPORTE_METIS_{reservoir_name}_{var}.pdf"
                    )

                    config_report = ReportConfig(
                        series_name=var,
                        reservoir_name=reservoir_name,
                        output_path=pdf_path,
                        institution=self.config.institution,
                        report_type=self.config.report_type,
                        author=self.config.author,
                        alpha=self.config.alpha,
                    )

                    # Generar PDF
                    generate_samhia_report_pdf(df_prep, config_report)

                    variables_analyzed.append(var)
                    output_paths[var] = pdf_path

                except Exception:  # noqa: S112, BLE001
                    # Continuar con siguiente variable si hay error
                    continue

            if not variables_analyzed:
                result = FileResult(
                    filename=filename,
                    status="skipped",
                    variables_analyzed=[],
                    output_paths={},
                    error_message="No se pudo analizar ninguna variable",
                    n_rows=len(df),
                )
                self.results.append(result)
                return result

            result = FileResult(
                filename=filename,
                status="success",
                variables_analyzed=variables_analyzed,
                output_paths=output_paths,
                n_rows=len(df),
            )
            self.results.append(result)
        except Exception as e:  # noqa: BLE001
            result = FileResult(
                filename=filename,
                status="error",
                variables_analyzed=[],
                output_paths={},
                error_message=f"Error: {e!s}",
                n_rows=0,
            )
            self.results.append(result)
        return result

    def process_files(
        self,
        filepaths: list[str],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[FileResult]:
        """Procesa múltiples archivos en paralelo.

        Args:
            filepaths: Lista de rutas de archivos a procesar.
            progress_callback: Función callback para reportar progreso
                (callback(current, total)).

        Returns:
            Lista de FileResult con resultados de cada archivo.
        """
        self.results = []
        total = len(filepaths)

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Enviar todas las tareas
            future_to_file = {
                executor.submit(self.process_file, filepath): filepath
                for filepath in filepaths
            }

            # Recopilar resultados a medida que completan
            for i, future in enumerate(as_completed(future_to_file)):
                filepath = future_to_file[future]
                try:
                    future.result()
                    # No agregar a self.results - process_file ya lo hizo

                    # Reportar progreso si hay callback
                    if progress_callback:
                        progress_callback(i + 1, total)

                except Exception as e:  # noqa: BLE001
                    self.results.append(
                        FileResult(
                            filename=Path(filepath).name,
                            status="error",
                            variables_analyzed=[],
                            output_paths={},
                            error_message=f"Error en procesamiento: {e!s}",
                            n_rows=0,
                        )
                    )

        return self.results

    def get_summary(self) -> dict:
        """Genera resumen de resultados del procesamiento batch.

        Returns:
            Diccionario con estadísticas del procesamiento.
        """
        total = len(self.results)
        successful = sum(1 for r in self.results if r.status == "success")
        failed = sum(1 for r in self.results if r.status == "error")
        skipped = sum(1 for r in self.results if r.status == "skipped")

        total_variables = sum(len(r.variables_analyzed) for r in self.results)

        return {
            "total_files": total,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "total_variables_analyzed": total_variables,
            "output_directory": self.config.output_dir,
        }


def process_files_batch(
    filepaths: list[str],
    output_dir: str,
    alpha: float = 0.05,
    max_workers: int = 4,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[FileResult]:
    """Función conveniente para procesamiento batch.

    Args:
        filepaths: Lista de rutas de archivos a procesar.
        output_dir: Directorio de salida para los reportes.
        alpha: Nivel de significancia para tests estadísticos.
        max_workers: Número de workers para procesamiento paralelo.
        progress_callback: Función callback para reportar progreso.

    Returns:
        Lista de FileResult con resultados de cada archivo.
    """
    config = BatchConfig(
        output_dir=output_dir,
        alpha=alpha,
        max_workers=max_workers,
    )

    processor = BatchProcessor(config)
    return processor.process_files(filepaths, progress_callback)
