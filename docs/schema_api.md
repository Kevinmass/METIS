# Schema de Respuesta de la API — Contrato para Etapa 2

Este documento define el contrato completo de la API antes de su implementación. La API debe devolver exactamente este schema para garantizar compatibilidad futura con el módulo de GeoAI.

## Endpoint: `POST /validate`

### Request Body
```json
{
  "series": [1.2, 3.4, 5.6, ...],  // Lista de floats
  "series_id": "optional_string"    // Opcional, para trazabilidad
}
```

### Response Body
```json
{
  "series_id": "string",  // Echo del request o generado
  "n": 35,                // Número de datos en la serie
  "warnings": [           // Advertencias físicas, nunca bloquean el análisis
    {
      "code": "NEGATIVE_VALUES",
      "affected_indices": [4, 17],
      "message": "Se detectaron valores negativos en los índices 4 y 17. Se aplicará transformación logarítmica con advertencia."
    },
    {
      "code": "ZERO_VALUES",
      "affected_indices": [10],
      "message": "Se detectaron valores cero en el índice 10. La transformación logarítmica fallará silenciosamente."
    }
  ],
  "validation": {
    "independence": {
      "verdict": "ACCEPTED",  // "ACCEPTED" | "REJECTED" | "INCONCLUSIVE"
      "hierarchy_applied": false,  // true si Anderson rechaza pero WW acepta
      "anderson": {
        "statistic": 0.18,
        "critical_value": 0.27,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      },
      "wald_wolfowitz": {
        "statistic": 1.94,
        "critical_value": 1.96,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      }
    },
    "homogeneity": {
      "individual_verdicts_only": true,  // Siempre true, no hay veredicto agregado
      "helmert": {
        "statistic": -3,
        "critical_range": [-5, 5],
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      },
      "t_student": {
        "statistic": 1.12,
        "critical_value": 2.03,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      },
      "cramer": {
        "statistic": 0.87,
        "critical_value": 1.41,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      }
    },
    "trend": {
      "mann_kendall": {
        "statistic": 0.31,
        "critical_value": 1.96,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      },
      "kolmogorov_smirnov": {
        "statistic": 0.14,
        "critical_value": 0.23,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      }
    },
    "outliers": {
      "chow": {
        "statistic": 2.1,
        "critical_value": 2.87,
        "alpha": 0.05,
        "verdict": "ACCEPTED",
        "flagged_indices": []  // Lista vacía si no hay atípicos
      }
    }
  }
}
```

### Campos Obligatorios
- Todos los campos mostrados son obligatorios.
- `warnings` puede ser una lista vacía.
- `flagged_indices` en outliers puede ser lista vacía.
- `hierarchy_applied` en independence debe reflejar si se aplicó la regla Anderson → Wald-Wolfowitz.

### Códigos de Error
- `400 Bad Request`: Serie vacía o con menos de 3 datos.
- `422 Unprocessable Entity`: Datos no numéricos.
- `200 OK`: Siempre devuelve análisis completo, incluso con warnings.

### Notas de Diseño
- El schema es extensible para futuras etapas (frecuencia, etc.).
- Los `statistic` y `critical_value` deben coincidir exactamente con los calculados en el core.
- El módulo de GeoAI consumirá este endpoint, por lo que cualquier cambio requiere coordinación.