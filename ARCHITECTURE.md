# METIS — Arquitectura del Sistema

## Visión General

METIS es un sistema de análisis hidrológico compuesto por tres capas independientes que se comunican a través de HTTP:

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND                          │
│              React + Vite + SVG                      │
│  ┌─────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │ Ingesta │ │  SAMHIA  │ │   Frecuencia          │  │
│  │ +Tabla  │ │ +Tests   │ │ +Distribuciones       │  │
│  └────┬────┘ └────┬─────┘ └──────────┬───────────┘  │
│       └───────────┼──────────────────┘               │
│                   │ HTTP (fetch)                      │
└───────────────────┼─────────────────────────────────┘
                    │
┌───────────────────┼─────────────────────────────────┐
│                   ▼                                  │
│               API REST                               │
│            FastAPI + Pydantic                        │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐   │
│  │ /validate│ │/frequency│ │ /reports  /temporal │   │
│  └────┬─────┘ └────┬─────┘ └────────┬───────────┘   │
│       └───────────┼──────────────────┘               │
│                   │ Llamadas directas                 │
└───────────────────┼─────────────────────────────────┘
                    │
┌───────────────────┼─────────────────────────────────┐
│                   ▼                                  │
│             CORE ESTADÍSTICO                         │
│         Python puro (NumPy, SciPy)                   │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐   │
│  │Validation│ │Frequency │ │ Temporal + Shared   │   │
│  │Indep/Hom │ │6+ dists  │ │ Agregación temporal │   │
│  │Tend/Out  │ │MOM/MLE/  │ │ Año hidrológico     │   │
│  │          │ │MEnt/LMom │ │                     │   │
│  └──────────┘ └──────────┘ └────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Estructura de Directorios

```
METIS/
├── core/                           # ← Capa 1: Core estadístico
│   ├── validation/                 #   Tests de validación hidrológica
│   │   ├── independence.py         #   Anderson, Wald-Wolfowitz
│   │   ├── homogeneity.py          #   Helmert, t-Student, Cramér
│   │   ├── trend.py               #   Mann-Kendall, KS
│   │   └── outliers.py            #   Chow, Kn
│   ├── frequency/                  #   Análisis de frecuencia
│   │   ├── distributions.py        #   Definiciones matemáticas
│   │   ├── fitting.py             #   MOM, MLE, MEnt, LMom
│   │   └── design_events.py       #   Cálculo de eventos de diseño
│   ├── temporal/                   #   Procesamiento temporal
│   │   └── aggregation.py         #   Agregación ascendente flexible
│   └── shared/                     #   Utilidades compartidas
│       └── preprocessing.py       #   Detección de ceros, negativos, NaN
│
├── api/                            # ← Capa 2: API REST
│   ├── main.py                    #   Configuración FastAPI + CORS
│   ├── routers/
│   │   ├── validate.py            #   POST /validate
│   │   ├── frequency.py           #   POST /frequency/fit y /design-event
│   │   ├── reports.py             #   POST /reports/analyze y /pdf
│   │   └── temporal.py            #   POST /temporal/aggregate
│   ├── schemas/                    #   Modelos Pydantic
│   └── middleware/                 #   Error handling
│
├── frontend/                       # ← Capa 3: Interfaz de usuario
│   ├── src/
│   │   ├── App.jsx                #   Componente principal (orquestador)
│   │   ├── Frequency.jsx          #   Página de frecuencia (independiente)
│   │   ├── Samhia.jsx             #   Componentes SAMHIA
│   │   ├── context/
│   │   │   └── TeacherModeContext.jsx  # Context global del Modo Docente
│   │   ├── components/
│   │   │   ├── TeacherNote.jsx    #   Bloque de explicación teórica
│   │   │   ├── TeacherTooltip.jsx #   Tooltip flotante para hover
│   │   │   ├── DistributionPDFChart.jsx  #   PDF individual SVG
│   │   │   ├── SuperimposedDistributionsChart.jsx # Todas las curvas
│   │   │   ├── AsymmetricDistributionsChart.jsx # Chart interactivo
│   │   │   ├── FrequencyTheoryInfo.jsx # Info teórica de frecuencia
│   │   │   ├── teacher/           #   Contenido teórico por sección
│   │   │   │   ├── IngestaTeacherNotes.jsx
│   │   │   │   ├── ResumenTeacherNotes.jsx
│   │   │   │   ├── SamhiaTeacherNotes.jsx
│   │   │   │   └── FrecuenciaTeacherNotes.jsx
│   │   │   ├── charts/            #   Gráficos Recharts
│   │   │   ├── WaterChartBox.jsx  #   Contenedor con efecto ripple
│   │   │   └── ...                 #   GlassPanel, AquaButton, Toast
│   │   ├── hooks/                  #   Custom hooks
│   │   └── styles/                 #   CSS Frutiger Aero
│   ├── index.html
│   └── vite.config.js
│
├── tests/                          # Tests automatizados
│   ├── unit/                       #   Tests unitarios del core
│   ├── integration/                #   Tests de integración de API
│   ├── e2e/                        #   Tests end-to-end (Playwright)
│   └── fixtures/                   #   Datos de referencia
│
├── docs/                           # Documentación
│   ├── ARCHITECTURE.md             #   Este archivo
│   ├── ROADMAP.md                  #   Roadmap de implementación
│   ├── schema_api.md              #   Contrato de la API
│   ├── PLANTILLA_FORMATO_CORRECTO.md  # Formato de datos esperado
│   ├── HISTORIAS_DE_USUARIO_Y_CASOS_DE_PRUEBA.md # Casos de uso
│   ├── REPORTE_AUDITORIA_QA_TECNICA.md  # Auditoría de calidad
│   └── *.csv                       #   Datos de referencia y ejemplos
│
├── CHANGELOG.md                    # Historial de cambios del proyecto
├── run_tests.sh / run_tests.bat    # Scripts de ejecución de tests
├── dev.sh                          # Script de desarrollo local
├── pyproject.toml                  # Configuración Ruff + Black
├── requirements.txt                # Dependencias producción
└── requirements-dev.txt            # Dependencias desarrollo
```

## Decisiones Técnicas

### 1. Core Python puro (sin framework)

**Decisión:** El core estadístico (`core/`) es una librería Python sin dependencias de HTTP ni UI.

**Motivación:** La lógica estadística debe ser verificable en aislamiento, sin necesidad de un servidor HTTP ni un navegador. Esto permite:
- Tests unitarios que no requieren infraestructura
- Reproducibilidad desde scripts Python independientes
- Posibilidad de integrar el core en otros proyectos (CLI, Jupyter, GeoAI)

### 2. FastAPI como capa de transporte

**Decisión:** FastAPI con documentación OpenAPI automática.

**Motivación:**
- Documentación Swagger/ReDoc gratuita para integración con GeoAI
- Validación de schemas con Pydantic en runtime
- Async nativo para endpoints futuros de archivos grandes
- Rendimiento competitivo con Go/Node.js en benchmarks

### 3. React + Vite para el frontend

**Decisión:** React 18 con Vite como bundler.

**Motivación:**
- Ecosistema maduro de componentes reutilizables
- Vite ofrece HMR instantáneo y builds rápidos
- Posibilidad de escalar a TypeScript sin refactorizar la arquitectura
- Mayor disponibilidad de talento en el mercado comparado con Streamlit

### 4. Sistema de diseño Frutiger Aero

**Decisión:** Estética glassmorphism acuática con colores azul-cian.

**Motivación:**
- Identidad visual diferenciadora (no es un "dashboard genérico")
- Esquema de colores alineado con el dominio hidrológico (agua, profundidad oceánica)
- Efectos visuales (ripple, gloss, brillos) que mejoran la percepción de calidad profesional
- Sin dependencias externas de UI (todo es CSS personalizado)

### 5. Gráficos de distribuciones en SVG nativo (frontend)

**Decisión:** Las PDFs de distribuciones se calculan y dibujan en JavaScript usando SVG, no matplotlib en backend ni Recharts.

**Motivación:**
- Sin llamada HTTP → respuesta instantánea
- Sin dependencia de backend para visualización
- Las funciones matemáticas de PDF ya existían en `AsymmetricDistributionsChart.jsx`
- SVG permite interactividad nativa (hover, toggle, zoom)
- Matplotlib genera imágenes raster que no escalan bien en UI responsive

### 6. Modo Docente como toggle frontend

**Decisión:** El Modo Docente es un estado React global (Context) que controla visibilidad de componentes, no un flag de backend.

**Motivación:**
- El contenido teórico ya existe en el frontend (texto, tooltips)
- No requiere recargar datos de la API al activar/desactivar
- Experiencia de usuario fluida: toggle instantáneo sin latencia
- Separa la lógica de presentación (docente) de la lógica de negocio (cálculos)

### 7. Sin base de datos (stateless)

**Decisión:** El backend es completamente stateless. No persiste análisis previos.

**Motivación:**
- Simplifica el despliegue (sin necesidad de administrar una DB)
- Ideal para prototipado y MVP
- La exportación a PDF/Excel reemplaza la necesidad de persistencia
- Futura integración con GeoAI podría agregar persistencia si es necesario

## Flujo de Datos

### Pipeline de Validación
```
1. Ingesta (CSV/Excel/Manual)
   → 2. Preprocesamiento (detección de ceros, negativos)
   → 3. Tests de Independencia (Anderson + Wald-Wolfowitz)
   → 4. Tests de Homogeneidad (Helmert, t-Student, Cramér)
   → 5. Tests de Tendencia (Mann-Kendall, KS)
   → 6. Tests de Atípicos (Chow, Kn)
   → 7. Reporte con veredictos + advertencias
```

### Pipeline de Frecuencia
```
1. Serie validada
   → 2. Selección de distribuciones y método de estimación
   → 3. Ajuste de cada distribución a los datos
   → 4. Cálculo de bondad de ajuste (Chi², KS, EEA)
   → 5. Ranking y recomendación de mejor distribución
   → 6. Cálculo de evento de diseño para T dado
```

## Componentes del Frontend

### Árbol de Componentes (App.jsx)

```
<TeacherModeProvider>          ← Context global
  <App>
    ├── Sidebar                ← Navegación
    │   ├── NavItem: Ingesta
    │   ├── NavItem: Resumen
    │   ├── NavItem: SAMHIA
    │   ├── NavItem: Frecuencia
    │   └── TeacherModeToggle  ← Footer
    │
    ├── TopBar                 ← Encabezado dinámico
    │
    └── ContentArea            ← Sección activa
        ├── Section: Ingesta
        │   ├── IngestaTeacherNotes     ← Modo Docente
        │   ├── DropZone (CSV/XLSX)
        │   ├── FilePreview + ColumnSelector
        │   ├── TemporalProcessing
        │   └── DataTable (editable)
        │
        ├── Section: Resumen
        │   ├── ResumenTeacherNotes     ← Modo Docente
        │   ├── StatCards (media, std, cv...)
        │   ├── Warnings
        │   ├── ScatterPlot (SVG)
        │   └── Correlogram (SVG)
        │
        ├── Section: SAMHIA
        │   ├── SamhiaTeacherNotes      ← Modo Docente
        │   ├── ConfigForm (nombre, alpha)
        │   ├── PDF Generator
        │   ├── TabButtons + TeacherTooltip
        │   ├── DescriptiveStatsPanel
        │   ├── TestResultsPanel
        │   └── OutlierVisualizations
        │
        └── Section: Frecuencia
            ├── FrecuenciaTeacherNotes  ← Modo Docente
            ├── ParamsForm (método, distribuciones)
            ├── FitResults
            │   ├── DistributionResult (accordion)
            │   │   ├── DistributionPDFChart  ← Modo Docente
            │   │   ├── Params Table
            │   │   └── GoodnessOfFit Table
            │   └── SuperimposedDistributionsChart  ← Modo Docente
            └── DesignEvent (cálculo T)
```

### Roles de Componentes Clave

| Componente | Rol |
|-----------|-----|
| `TeacherNote` | Bloque de explicación teórica con 3 variantes visuales |
| `TeacherTooltip` | Tooltip flotante que aparece al hover sobre elementos |
| `DistributionPDFChart` | Curva PDF de una distribución + histograma real |
| `SuperimposedDistributionsChart` | Múltiples curvas superpuestas con toggle |
| `AsymmetricDistributionsChart` | Chart interactivo de distribuciones asimétricas (página independiente) |
| `FrequencyTheoryInfo` | Información teórica detallada sobre análisis de frecuencia |
| `WaterChartBox` | Contenedor con efecto ripple para gráficos |

## Integración con GeoAI (Futuro)

El endpoint `/validate` está diseñado para ser consumido por un módulo de GeoAI. El contrato incluye:
- Schema de respuesta documentado en Swagger (`/docs`)
- Versionado planificado (`/v1/validate`)
- CORS configurado dinámicamente via `FRONTEND_URL`

Para detalles específicos de integración, ver `docs/schema_api.md`.

---

*Documento de arquitectura — PI ISI UCC 2026*
*Octavio Carpineti | Kevin Massholder*