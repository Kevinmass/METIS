"""Módulo de procesamiento batch para METIS.

Proporciona funcionalidades para leer múltiples archivos CSV/Excel
y procesarlos en lote con el sistema de análisis SAMHIA.
"""

from core.batch.io_handlers import (
    detect_date_column,
    detect_numeric_columns,
    read_file_intelligent,
)
from core.batch.processor import (
    BatchConfig,
    BatchProcessor,
    process_files_batch,
)


__all__ = [
    # Processor
    "BatchConfig",
    "BatchProcessor",
    # IO handlers
    "detect_date_column",
    "detect_numeric_columns",
    "process_files_batch",
    "read_file_intelligent",
]
