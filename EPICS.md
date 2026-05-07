# METIS — Mapeo de Epics a Archivos del Proyecto

**Documento de referencia:** `ROADMAP.md` describe las etapas de desarrollo.
**Alcance:** Epics 1-4 implementadas. Epics 5 y 6 pendientes.
**Última actualización:** Mayo 2026

---

## 🗂️ Visión General de Epics

| Epic | Nombre | Estado | Descripción |
| :---: | :--- | :---: | :--- |
| **1** | Core Estadístico | ✅ Implementada | Librería Python pura con módulos de validación estadística |
| **2** | API REST | ✅ Implementada | FastAPI con endpoints de validación, frecuencia y reportes |
| **3** | Frontend — Validación | ✅ Implementada | UI React con diseño Frutiger Aero para análisis completo |
| **4** | Análisis de Frecuencia + UI/UX | ✅ Implementada | Motor de distribuciones, eventos de diseño, middleware de errores y sistema de notificaciones toast |
| **5** | QA Final e Integración | ⏳ Pendiente | Validación contra tesis de referencia, integración GeoAI |
| **6** | Reportes Avanzados | ⏳ Pendiente | Exportación Excel, informes consolidados, dashboards |

---

## 📌 Epic 1 — Core Estadístico

**Objetivo:** Implementar la librería Python pura con todos los módulos de validación estadística (independencia, homogeneidad, tendencia, outliers) y el motor de análisis de frecuencia.

### Archivos Implementados

#### 1.1 Preprocesamiento y Utilidades
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `core/shared/preprocessing.py` | ~200 | Carga de series desde CSV/Excel/lista, detección de inconsistencias físicas (ceros, negativos, NaN), transformación logarítmica con warnings |
| `core/shared/types.py` | ~80 | Dataclasses base: `TestResult`, `GroupVerdict`, `ValidationReport` |
| `core/shared/__init__.py` | - | Exportación de tipos compartidos |

#### 1.2 Módulo de Independencia
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `core/validation/independence.py` | ~483 | `anderson_test()` — autocorrelación serial con bandas 95%; `wald_wolfowitz_test()` — corridas; `resolve_independence()` — jerarquía Anderson determinante |

#### 1.3 Módulo de Homogeneidad
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `core/validation/homogeneity.py` | ~300 | `helmert_test()`, `t_student_test()`, `cramer_test()` — sin resolución agregada, resultados individuales |

#### 1.4 Módulo de Tendencia
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `core/validation/trend.py` | ~219 | `mann_kendall_test()`, `kolmogorov_smirnov_trend_test()` |

#### 1.5 Módulo de Atípicos (Outliers)
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `core/validation/outliers.py` | ~400 | `chow_test()` — detección con transformación logarítmica, `kn_test()` |

#### 1.6 Orquestador del Pipeline
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `core/validation/__init__.py` | ~150 | `run_validation_pipeline()` — ejecuta los 4 grupos de pruebas en orden, agrega warnings físicos |
| `core/__init__.py` | - | Inicialización del paquete core |

#### 1.7 Motor de Frecuencia (Extendido en Epic 4)
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `core/frequency/distributions.py` | ~711 | 13 distribuciones: Normal, Log-Normal, Gumbel, GEV, Pearson III, Log-Pearson III, Exponencial, Gamma, Weibull, Log-Logistic, Pareto, Beta, Rayleigh |
| `core/frequency/fitting.py` | ~800 | Métodos MOM, MLE, MEnt, **LMom** (L-Moments); bondad de ajuste: Chi-Square, Kolmogorov-Smirnov, Standard Error |
| `core/frequency/design_events.py` | ~200 | `calculate_design_event()` — cálculo de eventos extremos para período de retorno T |
| `core/frequency/__init__.py` | - | Exportación del motor de frecuencia |

#### 1.8 Procesamiento Temporal
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `core/temporal/processing.py` | ~300 | Agregación ascendente flexible: yearly, monthly, daily, hourly, minutely; año hidrológico configurable |

---

## 📌 Epic 2 — API REST

**Objetivo:** Exponer el core estadístico como servicio HTTP consumible externamente mediante FastAPI.

### Archivos Implementados

#### 2.1 Setup de FastAPI
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `api/main.py` | ~141 | App FastAPI, CORS, endpoints `/health`, `/docs`, `/redoc`; integración de routers; encoding JSON para `inf`/`nan` |

#### 2.2 Schemas Pydantic
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `api/schemas/validation.py` | ~200 | `SeriesInput`, `ValidationResponse`, `TestResultSchema`, `GroupVerdictSchema` |
| `api/schemas/frequency.py` | ~294 | `FrequencyFitRequest`, `FrequencyFitResponse`, `DesignEventRequest`, `DesignEventResponse`, `GoodnessOfFitSchema` |
| `api/schemas/reports.py` | ~150 | Schemas para análisis SAMHIA, PDF generation |

#### 2.3 Routers (Endpoints)
| Archivo | Líneas | Endpoints | Descripción |
|---------|--------|-----------|-------------|
| `api/routers/validate.py` | ~405 | `POST /validate`, `POST /validate/file` | Validación completa SAMHIA con upload CSV/XLSX |
| `api/routers/frequency.py` | ~331 | `POST /frequency/fit`, `POST /frequency/design-event` | Ajuste de distribuciones y cálculo de eventos de diseño |
| `api/routers/reports.py` | ~499 | `POST /reports/analyze`, `POST /reports/pdf`, `GET /reports/download/{filename}` | Análisis SAMHIA, generación y descarga de PDFs |

#### 2.4 Middleware
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `api/middleware/error_handler.py` | ~227 | Epic 4: Captura de errores matemáticos (división por cero, log negativo, overflow, convergencia, matriz singular); respuestas 422 estructuradas |
| `api/middleware/__init__.py` | ~6 | Exportación del middleware |

#### 2.5 Configuración del Paquete
| Archivo | Descripción |
|---------|-------------|
| `api/__init__.py` | Inicialización del paquete API |

---

## 📌 Epic 3 — Frontend: Módulo de Validación

**Objetivo:** Construir la interfaz React completa para el pipeline hidrológico con diseño Frutiger Aero.

### Archivos Implementados

#### 3.1 Setup del Proyecto Frontend
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `frontend/vite.config.js` | ~30 | Configuración Vite para React |
| `frontend/index.html` | ~15 | HTML base con fuentes y metatags |
| `frontend/src/main.jsx` | ~15 | Entry point React, montaje de App |

#### 3.2 Aplicación Principal
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `frontend/src/App.jsx` | ~2,600 | Componente principal con: ingesta de datos (CSV/Excel drag-drop, tabla manual), resumen de serie, visualizaciones (dispersión, correlograma), dashboard SAMHIA (semáforo), paneles expandibles, resultados de validación, análisis de frecuencia, generación de PDF |

#### 3.3 Componentes Frutiger Aero
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `frontend/src/components/WaterChartBox.jsx` | ~80 | Contenedor de gráficos con efecto acuoso |
| `frontend/src/components/GlassPanel.jsx` | ~60 | Panel con glassmorphism (blur + transparencia) |
| `frontend/src/components/AquaButton.jsx` | ~50 | Botón con efectos de agua, ripple, glow |
| `frontend/src/components/index.js` | ~20 | Exportación centralizada de todos los componentes |

#### 3.4 Componentes de Chart (Aqua Charts)
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `frontend/src/components/charts/AquaLineChart.jsx` | ~200 | Gráfico de líneas con SVG puro, estilo Frutiger Aero |
| `frontend/src/components/charts/AquaBarChart.jsx` | ~150 | Gráfico de barras con SVG |
| `frontend/src/components/charts/AquaAreaChart.jsx` | ~180 | Gráfico de área con SVG |
| `frontend/src/components/charts/AquaScatterChart.jsx` | ~150 | Dispersión temporal con SVG |
| `frontend/src/components/charts/index.js` | ~10 | Exportación de charts |

#### 3.5 Componentes de Frecuencia
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `frontend/src/components/AsymmetricDistributionsChart.jsx` | ~250 | Visualización de distribuciones asimétricas |
| `frontend/src/components/FrequencyTheoryInfo.jsx` | ~300 | Panel informativo teórico del análisis de frecuencia |

#### 3.6 Módulo SAMHIA
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `frontend/src/Samhia.jsx` | ~800 | Componente OutliersPanel: visualización de outliers, gráficos de análisis de atípicos |

#### 3.7 Estilos CSS (Diseño Frutiger Aero)
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `frontend/src/style.css` | ~800 | Estilos base, layout, tipografía, utilidades |
| `frontend/src/styles/frutiger-aero.css` | ~600 | Variables CSS de color (paletas acuáticas), glassmorphism, efectos de agua, sombras, bordes |
| `frontend/src/styles/components.css` | ~400 | Estilos de componentes: botones, paneles, tablas, acordeones, inputs |
| `frontend/src/styles/animations.css` | ~270 | Keyframes: ripple, glow, fade, slide, **toast animations** (Epic 4) |

---

## 📌 Epic 4 — Análisis de Frecuencia + UI/UX (Middleware de Errores y Toast)

**Objetivo:** Extender el sistema con análisis de frecuencia completo (distribuciones, bondad de ajuste, eventos de diseño) e implementar manejo de errores matemáticos + sistema de notificaciones toast.

### Parte A: Análisis de Frecuencia (Backend)

#### 4.1.1 Motor de Distribuciones
| Archivo | Funciones Clave | Descripción |
|---------|----------------|-------------|
| `core/frequency/distributions.py` | `fit()`, `cdf()`, `ppf()`, `pdf()` | 13 distribuciones con interfaz común |

#### 4.1.2 Métodos de Estimación
| Archivo | Funciones Clave | Descripción |
|---------|----------------|-------------|
| `core/frequency/fitting.py` | `fit_by_mom()`, `fit_by_mle()`, `fit_by_ment()`, `fit_by_lmoments()` | Estimación de parámetros + bondad de ajuste |

#### 4.1.3 Eventos de Diseño
| Archivo | Funciones Clave | Descripción |
|---------|----------------|-------------|
| `core/frequency/design_events.py` | `calculate_design_event()` | Cálculo de eventos extremos |

#### 4.1.4 Endpoints de Frecuencia
| Archivo | Endpoints | Descripción |
|---------|-----------|-------------|
| `api/routers/frequency.py` | `/frequency/fit`, `/frequency/design-event` | Ajuste y diseño |

### Parte B: Middleware de Errores Matemáticos (Epic 4 Backend)

| Archivo | Líneas | Componente | Descripción |
|---------|--------|------------|-------------|
| `api/middleware/error_handler.py` | ~227 | `ErrorHandlerMiddleware` | Captura errores matemáticos: `MathError`, `DomainError`, `NumericOverflowError`, `ConvergenceError` |
| | | `is_math_error()` | Detecta si una excepción es matemática |
| | | `categorize_math_error()` | Categoriza: `DIVISION_BY_ZERO`, `LOGARITHM_DOMAIN_ERROR`, `NUMERIC_OVERFLOW`, `CONVERGENCE_ERROR`, `SINGULAR_MATRIX`, `INVALID_NUMERIC_VALUE` |
| | | Respuesta JSON | `{error_type, message, detail, suggestion}` con HTTP 422 |
| `api/main.py` | Línea 110 | `app.add_middleware(error_handler_middleware)` | Integrado después de CORS |

### Parte C: Sistema de Notificaciones Toast (Epic 4 Frontend)

| Archivo | Líneas | Componente | Descripción |
|---------|--------|------------|-------------|
| `frontend/src/hooks/useToast.js` | ~205 | `useToast` | Hook con: `showToast()`, `showSuccess()`, `showError()`, `showWarning()`, `showInfo()` |
| | | `TOAST_TYPES` | SUCCESS, ERROR, WARNING, INFO |
| | | Auto-cierre | 5000ms (normal), 8000ms (errores) |
| `frontend/src/components/Toast.jsx` | ~205 | `ToastContainer` | Renderiza lista de toasts, posición fixed top-right |
| | | `ToastItem` | Glassmorphism + icono SVG + barra de progreso + botón cerrar |
| `frontend/src/styles/animations.css` | Líneas 196-270 | Keyframes | `toastSlideIn`, `toastSlideOut`, `toastProgress` |
| `frontend/src/components/index.js` | Línea 13 | Export | `export { ToastContainer }` |

### Parte D: Integración Toast en Handlers de API

| Archivo | Handler | Notificaciones Implementadas |
|---------|---------|------------------------------|
| `frontend/src/App.jsx` | `handleFit()` | Warning (datos insuficientes), Success (ajuste completado), Error (errores matemáticos / conexión) |
| `frontend/src/App.jsx` | `handleDesignEvent()` | Warning (sin distribución / período inválido), Success (cálculo completado), Error (errores / conexión) |
| `frontend/src/App.jsx` | `handleAnalyzeSamhia()` | Warning (datos insuficientes), Success (análisis completado), Error (errores / conexión) |
| `frontend/src/App.jsx` | `handleGeneratePdf()` | Info (generando...), Success (PDF listo), Error (fallo generación / conexión) |
| `frontend/src/App.jsx` | `handleDownloadPdf()` | Success (descarga completada), Error (fallo descarga) |
| `frontend/src/App.jsx` | `handleFile()` | Info (cargando...), Success (vista previa lista), Error (archivo inválido / vacío), Warning (formato inválido) |
| `frontend/src/Frequency.jsx` | `handleFit()` | Warning, Success, Error (mismo esquema que App.jsx) |
| `frontend/src/Frequency.jsx` | `handleDesignEvent()` | Warning, Success, Error (mismo esquema que App.jsx) |

---

## 📌 Epic 5 — QA Final e Integración (⏳ Pendiente)

**Objetivo:** Validar el sistema completo contra la tesis de referencia, preparar integración con GeoAI.

### Tareas Pendientes

| Tarea | Descripción | Archivo Objetivo |
|-------|-------------|-----------------|
| 5.1.1 | Validación cruzada contra tesis del Mgter. Ganancias | `tests/test_regression_tesis.py` |
| 5.1.2 | Serie Alpa Corral (caso especial con advertencias) | `tests/fixtures/` |
| 5.2.1 | Revisión de textos explicativos (Modo Docente) | `frontend/src/App.jsx` (paneles expandibles) |
| 5.3.1 | Documentar contrato de integración GeoAI | `docs/geoai_integration.md` |
| 5.3.2 | Versionar API (`/v1/`) | `api/main.py` |
| 5.4.1 | `README.md` con instrucciones completas | `README.md` |
| 5.4.2 | `CHANGELOG.md` con historial | `CHANGELOG.md` |

---

## 📌 Epic 6 — Reportes Avanzados (⏳ Pendiente)

**Objetivo:** Exportación avanzada: Excel, informes consolidados, dashboards.

### Tareas Pendientes

| Tarea | Descripción | Archivo Objetivo |
|-------|-------------|-----------------|
| 6.1 | Exportación de resultados a Excel | `api/routers/reports.py` (nuevo endpoint) |
| 6.2 | Informe consolidado (validación + frecuencia) | `core/reporting/` |
| 6.3 | Dashboard resumen ejecutivo | `frontend/src/components/` |
| 6.4 | Comparativa multi-series | `frontend/src/App.jsx` |

---

## 📊 Resumen de Archivos por Epic

| Epic | Backend (Python) | Frontend (JSX/CSS) | Tests | Docs |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `core/validation/*.py`, `core/frequency/*.py`, `core/shared/*.py` | — | `tests/unit/*.py` | `docs/schema_api.md` |
| **2** | `api/*.py`, `api/routers/*.py`, `api/schemas/*.py` | — | `tests/integration/*.py` | `docs/schema_api.md` |
| **3** | — | `frontend/src/App.jsx`, `frontend/src/components/*.jsx`, `frontend/src/styles/*.css` | `tests/e2e/*.py` | `docs/schema_api.md` |
| **4** | `core/frequency/*.py` (extendido), `api/middleware/*.py` | `frontend/src/hooks/useToast.js`, `frontend/src/components/Toast.jsx` | — | — |
| **5** | — | — | `tests/test_regression_tesis.py` | `README.md`, `CHANGELOG.md`, `docs/geoai_integration.md` |
| **6** | `core/reporting/` (nuevo) | `frontend/src/components/` (nuevo) | — | — |

---

## 🔍 Notas de Implementación

### Epic 4 — Detalles Técnicos del Middleware
El middleware de errores (`api/middleware/error_handler.py`) intercepta excepciones en el pipeline de FastAPI y devuelve respuestas HTTP 422 con el siguiente schema:

```json
{
  "error_type": "MATH_ERROR | DIVISION_BY_ZERO | LOGARITHM_DOMAIN_ERROR | NUMERIC_OVERFLOW | CONVERGENCE_ERROR | SINGULAR_MATRIX | INVALID_NUMERIC_VALUE",
  "message": "Descripción del error",
  "detail": { ... },
  "suggestion": "Acción recomendada para el usuario"
}
```

### Epic 4 — Detalles Técnicos del Toast
El sistema de toast se integra en los handlers mediante el hook `useToast()`:

```javascript
const { showSuccess, showError, showWarning, showInfo } = useToast();

// Ejemplo de uso
showSuccess("Ajuste completado", { title: "Análisis de frecuencia" });
showError("División por cero detectada", { title: "Error matemático", duration: 8000 });
```

---

*Documento generado automáticamente para trazabilidad de requerimientos.*
*Para modificaciones, actualizar este archivo y el `ROADMAP.md`.*
