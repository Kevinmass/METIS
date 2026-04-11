# 📋 Plantilla de Formato Correcto para Carga de Series

## ✅ Formato aceptado por el sistema

El sistema acepta archivos en formato `.xlsx` o `.csv` con la siguiente estructura EXACTA:

| Columna 1  | Columna 2 |
|:--------   |:--------  |
| `fecha`    | `caudal`  |
| 1980-01-01 | 12.5      |
| 1980-02-01 | 15.3      |
| 1980-03-01 | 18.7      |
| ...        | ...       |

---

## 📌 Reglas obligatorias:

1.  **SOLAMENTE DOS COLUMNAS**: Fecha + Valor numérico
2.  **Encabezados EXACTOS**: Primera fila debe contener exactamente los nombres `fecha` y `caudal`
3.  **Orden de columnas**: Fecha SIEMPRE primera columna, valor SIEMPRE segunda
4.  **Sin filas vacías** dentro del cuerpo de datos
5.  **Sin comentarios, notas ni celdas combinadas**
6.  **Sin totales, promedios ni filas de resumen al final**
7.  Valores deben ser numéricos positivos
8.  Fechas en formato `AAAA-MM-DD` (ISO 8601)

---

## ❌ Errores comunes:
- ❌ Agregar columnas adicionales
- ❌ Usar nombres de encabezado diferentes
- ❌ Invertir orden de columnas
- ❌ Dejar filas vacías entre datos
- ❌ Agregar encabezado en la fila 2 o posterior
- ❌ Valores negativos o cero (van a generar warning)

---

## 📥 Descargar plantilla de ejemplo:
> [👉 Descargar Plantilla Excel Ejemplo](./plantilla_ejemplo_metis.xlsx)

Archivo pre-formateado listo para completar con sus datos.