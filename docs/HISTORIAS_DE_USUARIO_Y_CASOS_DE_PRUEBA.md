# 10 Historias de Usuario con Casos de Prueba — METIS

> **Proyecto Integrador ISI UCC 2026**
> Sistema de Análisis Hidrológico para Validación de Series Temporales

---

## 📖 Historia de Usuario 1: Carga de datos por ingesta manual

**ID:** HU-01  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Ingresar datos manualmente en una tabla editable  
**Descripción:** Como ingeniero hidrólogo, quiero poder ingresar valores numéricos con sus fechas en una tabla interactiva para analizar series que no tengo en formato digital.

### Criterios de aceptación:
- La tabla permite agregar filas dinámicamente (al menos 50).
- Se puede editar cada celda individualmente (fecha y valor).
- Validación visual: valores negativos se resaltan en rojo, ceros en amarillo.
- Se puede eliminar una fila seleccionada.

### Caso de prueba CP-01A: Ingesta de serie válida
- **Entrada:** 15 filas con fechas entre 2000-01-01 y 2014-01-01 y valores entre 10 y 100.
- **Pasos:**
  1. Abrir la vista de ingesta manual.
  2. Completar 15 filas con fecha y caudal.
  3. Presionar "Analizar".
- **Resultado esperado:** El dashboard semáforo se muestra con resultados numéricos no nulos en cada prueba.

### Caso de prueba CP-01B: Ingesta con valores cero y negativos
- **Entrada:** Serie de 12 datos que incluye un 0 y un -5.
- **Pasos:**
  1. Completar 12 filas, incluyendo caudal=0 y caudal=-5.
  2. Verificar resaltado visual: celda con 0 en amarillo, celda con -5 en rojo.
- **Resultado esperado:** Las celdas inválidas están resaltadas antes de ejecutar análisis.

---

## 📖 Historia de Usuario 2: Carga de archivos por drag & drop

**ID:** HU-02  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Arrastrar y soltar archivos CSV/Excel  
**Descripción:** Como ingeniero hidrólogo, quiero arrastrar un archivo CSV o Excel a la interfaz para no tener que escribir los datos manualmente.

### Criterios de aceptación:
- Se aceptan archivos `.csv`, `.xlsx` y `.xls`.
- El sistema detecta automáticamente las columnas numéricas.
- El sistema detecta una columna de fecha si existe.
- Muestra vista previa de los datos antes del análisis.

### Caso de prueba CP-02A: Carga de CSV con formato correcto
- **Entrada:** Archivo CSV con columnas `date` y `caudal`, 30 filas de datos.
- **Pasos:**
  1. Arrastrar archivo al área de drag & drop.
  2. Verificar vista previa con las columnas detectadas.
  3. Seleccionar variable "caudal" y presionar "Analizar".
- **Resultado esperado:** Análisis completado con dashboard semáforo visible.

### Caso de prueba CP-02B: Carga de archivo con separador incorrecto
- **Entrada:** Archivo CSV con separador punto y coma (`;`) en lugar de coma.
- **Pasos:**
  1. Arrastrar archivo al área de drag & drop.
- **Resultado esperado:** El sistema intenta ambos separadores automáticamente y muestra los datos correctamente parseados.

---

## 📖 Historia de Usuario 3: Validación de independencia con jerarquía Anderson → Wald-Wolfowitz

**ID:** HU-03  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Verificar independencia de la serie  
**Descripción:** Como ingeniero hidrólogo, quiero que el sistema evalúe la independencia de mi serie aplicando la jerarquía Anderson → Wald-Wolfowitz documentada en la tesis de referencia, para decidir si puedo aplicar análisis de frecuencia.

### Criterios de aceptación:
- Anderson es determinante: si rechaza, el veredicto final es RECHAZADO.
- Si Anderson acepta pero Wald-Wolfowitz rechaza, el veredicto es ACEPTADO con indicador de jerarquía aplicada.
- Si ambos aceptan, veredicto ACEPTADO sin jerarquía.
- El panel expandible muestra explícitamente si se aplicó la jerarquía.

### Caso de prueba CP-03A: Anderson acepta, WW rechaza → jerarquía aplicada
- **Entrada:** Serie de 20 valores con baja autocorrelación pero corridas artificiales. Ejemplo: `[10, 12, 11, 13, 10, 14, 11, 15, 12, 16, 10, 12, 11, 13, 10, 14, 11, 15, 12, 16]`
- **Resultado esperado:** `independence.resolved_verdict = "ACCEPTED"`, `hierarchy_applied = True`.

### Caso de prueba CP-03B: Anderson rechaza → veredicto RECHAZADO
- **Entrada:** Serie monótona creciente `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]`.
- **Resultado esperado:** `independence.resolved_verdict = "REJECTED"`.

---

## 📖 Historia de Usuario 4: Validación de homogeneidad sin veredicto agregado

**ID:** HU-04  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Evaluar homogeneidad de la serie  
**Descripción:** Como ingeniero hidrólogo, quiero ver los resultados individuales de las pruebas de homogeneidad (Helmert, t-Student, Cramer, Mann-Whitney, Mood) sin un veredicto único, porque necesito interpretar cada aspecto por separado.

### Criterios de aceptación:
- Las 5 pruebas se muestran individualmente en el dashboard.
- NO hay un veredicto semáforo único para homogeneidad.
- Cada prueba muestra: estadístico, valor crítico y veredicto.
- Una nota explica por qué pueden diferir los resultados.

### Caso de prueba CP-04A: Serie homogénea
- **Entrada:** Serie estable `[10.2, 10.5, 9.8, 10.1, 10.3, 10.0, 10.4, 9.9, 10.2, 10.1, 10.3, 9.7, 10.0, 10.5, 10.2]`.
- **Resultado esperado:** Las 5 pruebas aceptan homogeneidad. `resolved_verdict = None`.

### Caso de prueba CP-04B: Salto de media en la segunda mitad
- **Entrada:** `[5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 100, 100, 100, 100, 100]`.
- **Resultado esperado:** t-Student y Cramer rechazan. Helmert podría aceptar si varianza similar. `resolved_verdict = None`. El panel muestra que hay discordancia entre pruebas.

---

## 📖 Historia de Usuario 5: Validación de tendencia con Mann-Kendall modificado

**ID:** HU-05  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Detectar tendencia en la serie  
**Descripción:** Como ingeniero hidrólogo, quiero que el sistema detecte tendencias monótonas usando Mann-Kendall con corrección por autocorrelación (Modified MK) para evitar falsos positivos en datos de alta frecuencia.

### Criterios de aceptación:
- Mann-Kendall implementa corrección de Hamed & Rao (1998) cuando hay autocorrelación.
- Para datos anuales, la corrección es mínima (factor ≈ 1.0).
- Para datos mensuales/diarios con autocorrelación, la varianza se infla.
- Veredicto resolutivo: OR entre MK y KS (cualquiera que rechace → RECHAZADO).

### Caso de prueba CP-05A: Serie anual sin tendencia
- **Entrada:** 30 valores aleatorios normales `N(50, 10)`.
- **Resultado esperado:** MK y KS aceptan. `trend.resolved_verdict = "ACCEPTED"`.

### Caso de prueba CP-05B: Serie mensual con tendencia creciente
- **Entrada:** 120 valores (10 años mensuales) con pendiente positiva + ruido autorregresivo.
- **Resultado esperado:** MK rechaza (detecta tendencia). `corrected_variance_s > variance_s`. `trend.resolved_verdict = "REJECTED"`.

---

## 📖 Historia de Usuario 6: Detección de valores atípicos (outliers)

**ID:** HU-06  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Identificar outliers en la serie  
**Descripción:** Como ingeniero hidrólogo, quiero que el sistema detecte observaciones atípicas mediante el test de Chow y el método Kn, para decidir si representan eventos extremos reales o errores de medición.

### Criterios de aceptación:
- Chow detecta outliers basados en residuos studentizados de regresión lineal.
- Kn detecta outliers basados en distancia desde la media escalada por K.
- La transformación logarítmica se omite automáticamente si hay ceros/negativos.
- El sistema NUNCA elimina outliers automáticamente, solo los reporta.

### Caso de prueba CP-06A: Serie sin outliers
- **Entrada:** Serie homogénea `[10, 12, 11, 13, 10, 14, 11, 15, 12, 16, 13, 17]`.
- **Resultado esperado:** Ambos tests reportan 0 outliers. `verdict = "ACCEPTED"`.

### Caso de prueba CP-06B: Serie con outlier evidente
- **Entrada:** Serie con un valor extremo `[10, 12, 11, 13, 10, 14, 500, 15, 12, 16, 13, 17]`.
- **Resultado esperado:** Al menos uno de los tests detecta el índice 6 como outlier. `verdict = "REJECTED"`.

---

## 📖 Historia de Usuario 7: Visualización del dashboard semáforo

**ID:** HU-07  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Ver estado general de la serie en dashboard  
**Descripción:** Como ingeniero hidrólogo, quiero ver un dashboard tipo semáforo que me muestre de un vistazo el estado de las 4 condiciones (independencia, homogeneidad, tendencia, atípicos) para tomar decisiones rápidas.

### Criterios de aceptación:
- Cada condición muestra un indicador verde (ACEPTADO) o rojo (RECHAZADO).
- Homogeneidad NO tiene semáforo único; muestra los 5 resultados individuales.
- Independencia muestra el veredicto resuelto y si se aplicó jerarquía.
- Al hacer clic en cada condición, se expande un panel con detalles.

### Caso de prueba CP-07A: Serie completamente válida
- **Entrada:** Serie estacionaria sin tendencia, homogénea, independiente, sin outliers.
- **Resultado esperado:** Independencia → verde, Tendencia → verde, Atípicos → verde. Homogeneidad muestra 5 tests individuales (todos verdes o con nota aclaratoria).

### Caso de prueba CP-07B: Serie con tendencia y outlier
- **Entrada:** Serie creciente con un valor extremo.
- **Resultado esperado:** Independencia → rojo o verde según el caso, Tendencia → rojo, Atípicos → rojo. Homogeneidad según resultados individuales.

---

## 📖 Historia de Usuario 8: Análisis con frecuencia temporal (escalado)

**ID:** HU-08  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Especificar frecuencia temporal de la serie  
**Descripción:** Como ingeniero hidrólogo, quiero poder indicar si mi serie es anual, mensual, diaria u otra frecuencia para que los valores críticos se escalen correctamente y no se inflen falsamente con datos de alta frecuencia.

### Criterios de aceptación:
- El usuario puede seleccionar la frecuencia en un dropdown (yearly, monthly, daily, hourly, minutes, 5min).
- El valor crítico de Anderson usa años equivalentes, no n crudo.
- Los lags de Ljung-Box se ajustan según frecuencia.
- La corrección de Modified MK se activa para frecuencias no anuales.

### Caso de prueba CP-08A: Misma serie, frecuencias distintas → resultados distintos
- **Entrada:** 365 valores con autocorrelación lag-1 de 0.15.
- **Frecuencia yearly:** `n_yearly = 365` → valor crítico Anderson = `1.96 / sqrt(365) ≈ 0.10` → RECHAZADO (falso positivo).
- **Frecuencia daily:** `n_effective = 1` (1 año) → valor crítico Anderson = `1.96 / sqrt(1) ≈ 1.96` → ACEPTADO (correcto).
- **Resultado esperado:** Con frecuencia daily el veredicto es ACEPTADO; con yearly es RECHAZADO. Esto demuestra que el escalado funciona.

---

## 📖 Historia de Usuario 9: Generación y descarga de reporte PDF

**ID:** HU-09  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Exportar reporte PDF del análisis  
**Descripción:** Como ingeniero hidrólogo, quiero generar un reporte PDF completo con todos los resultados del análisis para adjuntarlo a informes técnicos o entregables docentes.

### Criterios de aceptación:
- El PDF incluye: portada, estadísticas descriptivas, resultados de las 4 condiciones, gráficos (serie temporal, correlograma).
- El PDF tiene al menos 8 páginas con formato profesional.
- Se puede descargar desde un botón en la interfaz.
- El nombre del archivo incluye el nombre del embalse y la fecha.

### Caso de prueba CP-09A: Generación de PDF para serie válida
- **Entrada:** Serie de 30 caudales anuales con metadatos (nombre embalse, autor, institución).
- **Pasos:**
  1. Completar análisis exitosamente.
  2. Presionar botón "Generar PDF".
  3. Descargar archivo.
- **Resultado esperado:** PDF generado con código 200. Archivo descargable con extensión `.pdf`. Al abrirlo, contiene todas las secciones esperadas.

### Caso de prueba CP-09B: Generación de PDF sin datos suficientes
- **Entrada:** Serie de 5 datos.
- **Resultado esperado:** El sistema rechaza la generación con código 400 y mensaje "La serie debe tener al menos 12 datos".

---

## 📖 Historia de Usuario 10: Análisis de frecuencia y cálculo de eventos de diseño

**ID:** HU-10  
**Rol:** Ingeniero hidrólogo  
**Funcionalidad:** Ajustar distribuciones de probabilidad y calcular eventos de diseño  
**Descripción:** Como ingeniero hidrólogo, quiero que el sistema ajuste las 13 distribuciones de probabilidad del dominio hidrológico a mi serie ya validada, evalúe la bondad de ajuste y calcule eventos de diseño para períodos de retorno dados, para dimensionar obras hidráulicas como vertederos, aliviaderos o defensas ribereñas.

### Criterios de aceptación:
- Se ajustan automáticamente las 13 distribuciones soportadas (Gumbel, Log-Normal, Log-Pearson III, GEV, etc.).
- Se estiman parámetros por 3 métodos: Momentos (MOM), Máxima Verosimilitud (MLE) y Máxima Entropía (MEnt).
- Bondad de ajuste evaluada con Chi-Cuadrado, Kolmogorov-Smirnov y Error Estándar de Ajuste (EEA).
- El sistema recomienda la mejor distribución según los criterios combinados.
- Para un período de retorno T dado, calcula el valor del evento de diseño y su probabilidad anual (1/T).

### Caso de prueba CP-10A: Ajuste y recomendación de distribución
- **Entrada:** Serie de 30 caudales máximos anuales `[120.5, 98.3, 145.2, 110.8, 132.1, 89.6, 155.0, 105.4, 128.7, 95.2, 140.3, 115.6, 138.9, 92.1, 150.8, 108.3, 125.4, 100.7, 135.2, 118.9, 142.5, 102.3, 148.1, 112.5, 130.2, 97.8, 152.6, 107.1, 122.8, 99.4]`.
- **Resultado esperado:**
  - `fit_all_distributions(series)` retorna 13 resultados (uno por distribución).
  - Al menos una distribución tiene `is_recommended = True`.
  - `get_best_distribution(results)` retorna la distribución con mejores indicadores de bondad de ajuste.
  - `goodness_of_fit.ks_verdict = "ACCEPTED"` para la distribución recomendada.

### Caso de prueba CP-10B: Cálculo de evento de diseño centenario
- **Entrada:** Misma serie del CP-10A. Usar la distribución recomendada.
- **Pasos:**
  1. Ajustar distribución recomendada.
  2. Calcular evento de diseño para T = 100 años.
  3. Calcular evento de diseño para T = 50 años.
- **Resultado esperado:**
  - `calculate_design_event(best_fit, return_period=100.0)` → `annual_probability = 0.01`.
  - `design_value_100 > max(series)` (el evento centenario debe superar el máximo observado).
  - `design_value_100 > design_value_50` (consistencia: mayor T → mayor caudal).

---

## 📊 Resumen de Cobertura

| # | Historia de Usuario | Tipo de Prueba | Módulo |
|---|---------------------|----------------|--------|
| 1 | Carga manual | E2E / UNIT | Frontend / Core |
| 2 | Drag & drop archivos | E2E | Frontend |
| 3 | Jerarquía independencia | UNIT | `core/validation/independence.py` |
| 4 | Homogeneidad sin veredicto | UNIT / INTEGRATION | `core/validation/homogeneity.py` |
| 5 | Mann-Kendall modificado | UNIT | `core/validation/trend.py` |
| 6 | Detección de outliers | UNIT | `core/validation/outliers.py` |
| 7 | Dashboard semáforo | E2E | Frontend / API |
| 8 | Frecuencia temporal | UNIT / INTEGRATION | Core + API |
| 9 | Reporte PDF | INTEGRATION | `api/routers/reports.py` |
| 10 | Análisis de frecuencia y eventos de diseño | UNIT | `core/frequency/` |

---

*Documento de casos de prueba — PI ISI UCC 2026*
*Octavio Carpineti | Kevin Massholder*