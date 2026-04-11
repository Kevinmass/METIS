# Schema de Respuesta de la API - Contrato para Etapa 2

Este documento define el contrato vigente de la API REST de METIS para la etapa 2. La implementacion de `FastAPI`, los tests de integracion y este documento quedaron alineados.

## Endpoints disponibles

### `GET /health`

Respuesta esperada:

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### `POST /validate`

Request body:

```json
{
  "series_id": "serie_referencia_1",
  "series": [1.2, 3.4, 5.6]
}
```

Response body:

```json
{
  "series_id": "serie_referencia_1",
  "n": 35,
  "warnings": [
    {
      "code": "ZERO_VALUES",
      "message": "Se encontraron 1 valores iguales a cero",
      "affected_indices": [10]
    }
  ],
  "validation": {
    "independence": {
      "verdict": "REJECTED",
      "hierarchy_applied": true,
      "anderson": {
        "statistic": 0.82,
        "critical_value": 0.33,
        "alpha": 0.05,
        "verdict": "REJECTED"
      },
      "wald_wolfowitz": {
        "statistic": -3.94,
        "critical_value": 1.96,
        "alpha": 0.05,
        "verdict": "REJECTED"
      }
    },
    "homogeneity": {
      "individual_verdicts_only": true,
      "helmert": {
        "statistic": 1.1,
        "critical_value": 2.7,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      },
      "t_student": {
        "statistic": 1.01,
        "critical_value": 2.03,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      },
      "cramer": {
        "statistic": 0.12,
        "critical_value": 0.46,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      }
    },
    "trend": {
      "mann_kendall": {
        "statistic": 0.67,
        "critical_value": 1.96,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      },
      "kolmogorov_smirnov": {
        "statistic": 0.21,
        "critical_value": 0.47,
        "alpha": 0.05,
        "verdict": "ACCEPTED"
      }
    },
    "outliers": {
      "chow": {
        "statistic": 1.94,
        "critical_value": 3.48,
        "alpha": 0.05,
        "verdict": "ACCEPTED",
        "flagged_indices": []
      }
    }
  }
}
```

### `POST /validate/file`

Acepta `multipart/form-data` con un archivo `file` en formato `.csv`, `.xls` o `.xlsx`.

## Campos obligatorios

- `series` es obligatorio en `POST /validate`.
- `series_id` es opcional en `POST /validate`; si no se envia, la API genera uno automaticamente.
- `warnings` puede ser una lista vacia.
- `validation.independence.hierarchy_applied` siempre refleja si se aplico la jerarquia Anderson -> Wald-Wolfowitz.
- `validation.homogeneity.individual_verdicts_only` siempre es `true`.
- `validation.outliers.chow.flagged_indices` puede ser una lista vacia.

## Codigos de error

- `400 Bad Request`: serie vacia, archivo vacio o serie con menos de 3 datos.
- `422 Unprocessable Entity`: datos no numericos o archivo malformado.
- `200 OK`: la API devuelve el analisis completo aun cuando existan warnings fisicos.

## Notas de diseno

- Los estadisticos y valores criticos deben coincidir con el `core`.
- La estructura JSON esta preparada para ser consumida por frontend y por futuras integraciones.
- Swagger UI queda disponible en `/docs` y ReDoc en `/redoc`.
