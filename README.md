# METIS — Sistema Integrado de Análisis Hidrológico

> **M**ódulo **E**stadístico para la **T**oma de **I**nformación en **S**eries hidrológicas

METIS es un sistema de análisis hidrológico de tres capas (Core Python → API FastAPI → Frontend React) diseñado para la validación estadística de series hidrológicas, el ajuste de distribuciones de probabilidad y el cálculo de eventos de diseño para obras de ingeniería civil.

---

## 🧭 Tabla de Contenidos

- [Funcionalidades](#-funcionalidades)
- [Arquitectura](#-arquitectura)
- [Stack Tecnológico](#-stack-tecnológico)
- [Setup Local](#-setup-local)
- [Uso](#-uso)
- [Tests](#-tests)
- [Documentación](#-documentación)
- [Despliegue](#-despliegue)
- [Licencia](#-licencia)

---

## 🎯 Funcionalidades

### ✅ Módulo de Validación (SAMHIA)
- **Independencia**: Test de Anderson (autocorrelación serial) + Wald-Wolfowitz (rachas)
- **Homogeneidad**: Helmert, t-Student, Cramér (sin veredicto agregado)
- **Tendencia**: Mann-Kendall + Kolmogorov-Smirnov
- **Atípicos**: Chow con transformación logarítmica

### 📊 Análisis de Frecuencia
- 6 distribuciones: Normal, Log-Normal, Gumbel, GEV, Pearson III, Log-Pearson III
- 4 métodos de estimación: MOM, MLE, MEnt, LMom
- Bondad de ajuste: Chi², Kolmogorov-Smirnov, Error Estándar de Ajuste
- Cálculo de eventos de diseño para períodos de retorno T

### 🎓 Modo Docente
- Explicaciones teóricas activables en todas las secciones
- Tooltips interactivos para tests estadísticos
- Gráficos de distribuciones (PDF + histograma) en SVG nativo
- Sin dependencia de backend para visualizaciones

### 🎨 Sistema de Diseño Frutiger Aero
- Glassmorphism acuático con colores azul-cian
- Efectos ripple, gloss y brillos dinámicos
- Experiencia visual profesional y diferenciadora

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────┐
│  Frontend (React + Vite + SVG)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │ Ingesta  │ │  SAMHIA  │ │   Frecuencia         │  │
│  └────┬─────┘ └────┬─────┘ └──────────┬───────────┘  │
│       └────────────┼──────────────────┘               │
│                    │ HTTP                              │
├────────────────────┼─────────────────────────────────┤
│                    ▼                                   │
│  API (FastAPI + Pydantic)                             │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐    │
│  │/validate │ │/frequency│ │ /reports /temporal  │    │
│  └────┬─────┘ └────┬─────┘ └────────┬───────────┘    │
│       └────────────┼──────────────────┘               │
│                    │ Llamadas directas                 │
├────────────────────┼─────────────────────────────────┤
│                    ▼                                   │
│  Core (Python puro - NumPy/SciPy)                     │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐    │
│  │Validation│ │Frequency │ │ Temporal + Shared   │    │
│  └──────────┘ └──────────┘ └────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

Para detalles completos de arquitectura, ver [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 📦 Stack Tecnológico

| Capa | Tecnología | Propósito |
|:-----|:-----------|:----------|
| Core estadístico | Python 3.10+, NumPy, Pandas, SciPy, statsmodels | Motor de cálculo independiente |
| API | FastAPI | Capa de transporte HTTP con OpenAPI |
| Frontend | React 18 + Vite | Interfaz de usuario |
| Gráficos | SVG nativo + Recharts | Visualizaciones sin dependencias externas |
| Testing | pytest, Playwright | Validación por capas |
| Linting | Ruff + Black | Calidad de código Python |

---

## 🚀 Setup Local

### Requisitos
- Python 3.10+
- Node.js 18+
- npm

### Opción rápida (recomendada)

```bash
# En la raíz del proyecto
./dev.sh
```

Arranca API en `http://127.0.0.1:8000` y frontend en `http://127.0.0.1:5173` automáticamente.

### Manual

**1. Backend (API):**

```bash
# Instalar dependencias Python
pip install -r requirements.txt -r requirements-dev.txt

# Iniciar servidor
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

**2. Frontend:**

```bash
cd frontend
npm install
npm run dev
```

**3. Acceder:**

- Frontend: [`http://localhost:5173`](http://localhost:5173)
- API Docs: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)

---

## 🎮 Uso

### 1. Ingesta de datos
Carga un archivo CSV o Excel con tu serie hidrológica, o ingresa los valores manualmente en la tabla editable.

### 2. Resumen de la serie
Visualiza estadísticas descriptivas (media, desviación estándar, CV), gráfico de dispersión y correlograma.

### 3. Análisis SAMHIA
Ejecuta la batería completa de tests estadísticos. Los resultados se agrupan en 4 categorías con indicadores visuales de aceptación/rechazo.

### 4. Análisis de Frecuencia
Selecciona distribuciones y método de estimación. El sistema ajusta cada distribución, calcula bondad de ajuste y recomienda la mejor. Luego calcula eventos de diseño para el período de retorno deseado.

### 5. Modo Docente 🎓
Activa el toggle en el sidebar para ver explicaciones teóricas en todas las secciones. Pasa el mouse sobre los tests en SAMHIA para ver tooltips explicativos.

---

## 🧪 Tests

### Ejecutar suite completa

```bash
# Windows:
run_tests.bat

# Linux / Git Bash:
bash run_tests.sh
```

### Ejecutar por separado

```bash
# Unitarios
pytest tests/unit/ -v

# Integración (requiere API corriendo)
python -m pytest tests/integration -q

# E2E (requiere API + frontend corriendo)
pytest tests/e2e/ -v

# Linting
ruff check --fix
black .
```

---

## 📚 Documentación

| Documento | Contenido |
|:----------|:----------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Arquitectura, decisiones técnicas, flujo de datos |
| [`ROADMAP.md`](ROADMAP.md) | Roadmap de implementación por etapas |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial de cambios del proyecto |
| [`docs/schema_api.md`](docs/schema_api.md) | Contrato de la API REST |
| [`docs/PLANTILLA_FORMATO_CORRECTO.md`](docs/PLANTILLA_FORMATO_CORRECTO.md) | Formato de datos esperado |
| [`docs/HISTORIAS_DE_USUARIO_Y_CASOS_DE_PRUEBA.md`](docs/HISTORIAS_DE_USUARIO_Y_CASOS_DE_PRUEBA.md) | Casos de uso y pruebas |
| [`docs/REPORTE_AUDITORIA_QA_TECNICA.md`](docs/REPORTE_AUDITORIA_QA_TECNICA.md) | Auditoría de calidad |

---

## 🌐 Despliegue

El proyecto está configurado para desplegarse en [Render](https://render.com) usando `render.yaml`:

- **Backend**: Web Service (Python/FastAPI) en puerto dinámico
- **Frontend**: Static Site (React/Vite) construido con `npm run build`

Variables de entorno:
- `VITE_API_URL`: URL del backend en producción (ej: `https://metis-backend.onrender.com`)
- `FRONTEND_URL`: Para restringir CORS (opcional, por defecto permite todos los orígenes)

---

## 📄 Licencia

Proyecto integrador de la carrera Ingeniería en Sistemas de Información — Universidad Católica de Córdoba.

*Octavio Carpineti | Kevin Massholder*
*Director: Dr. Ing. Carlos Catalini | Co-director: Mgter. Ing. Facundo Ganancias*

---

*PI ISI UCC 2026*