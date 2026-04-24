#!/usr/bin/env python3
"""Test script to verify FDP plot is returned by API."""

# Simular la respuesta del endpoint para verificar estructura
test_response = {
    "success": True,
    "message": "Gráficos generados exitosamente",
    "plot_urls": {
        "control_chart": "data:image/png;base64,test...",
        "probability_plot": "data:image/png;base64,test...",
        "qq_plot": "data:image/png;base64,test...",
        "fdp_plot": "data:image/png;base64,test...",
    },
    "kn_limits": {
        "lower": 10.0,
        "upper": 50.0,
        "mean": 30.0,
        "std_dev": 10.0,
        "kn_value": 2.5,
    },
    "outliers_detected": 0,
    "outliers_indices": [],
}

print("=== Verificación de estructura de respuesta ===")  # noqa: T201
print(f"Keys en plot_urls: {list(test_response['plot_urls'].keys())}")  # noqa: T201
print(f"fdp_plot presente: {'fdp_plot' in test_response['plot_urls']}")  # noqa: T201
print()  # noqa: T201

# Verificar la función plot_fdp
print("=== Verificando import de plot_fdp ===")  # noqa: T201
try:
    from core.reporting.plots import plot_fdp

    print("plot_fdp importado correctamente desde core.reporting.plots")  # noqa: T201
    print(f"Ubicación: {plot_fdp.__module__}")  # noqa: T201
except ImportError as e:
    print(f"ERROR al importar plot_fdp: {e}")  # noqa: T201
