# METIS — Roadmap de Implementación por Etapas

Este roadmap organiza el desarrollo en etapas completas y desplegables. Cada etapa termina con un conjunto de tests que la validan antes de avanzar a la siguiente. El pipeline de CI/CD en GitHub Actions se introduce en la Etapa 1 y crece incrementalmente.

> **Convención:** Una etapa no se considera cerrada hasta que todos sus tests pasan en CI. No se arranca la siguiente etapa con tests rojos.

---

## 🗂️ Visión General

```
Etapa 0 → Etapa 1 → Etapa 2 → Etapa 3 → Etapa 4 → Etapa 5
Fixtures   Core      API       Frontend  Frecuencia  QA Final
           + CI      + CI      + CI      + CI        + CI
```

| Etapa | Nombre | Entregable concreto |
| :---: | :--- | :--- |
| **0** | Fixtures y Setup | Datasets de referencia + estructura del repositorio |
| **1** | Core Estadístico | Librería Python pura con todos los módulos de validación |
| **2** | API REST | Endpoint `/validate` consumible desde Postman o curl |
| **3** | Frontend — Validación | UI completa para la Etapa 1 del pipeline hidrológico |
| **4** | Análisis de Frecuencia | Motor de ajuste de distribuciones + eventos de diseño |
| **5** | QA Final e Integración | Sistema completo validado contra la tesis de referencia |

---

## Etapa 0 — Fixtures, Setup y Estructura del Repositorio

*Objetivo: Antes de escribir lógica, establecer la verdad matemática de referencia y la estructura del proyecto que todas las etapas siguientes van a respetar.*

### 0.1 Estructura del repositorio

```
METIS/
├── .github/
│   └── workflows/
│       └── ci.yml                  # Pipeline de CI (se construye en Etapa 1)
├── core/                           # Librería Python pura — sin dependencias de API ni UI
│   ├── __init__.py
│   ├── validation/
│   │   ├── independence.py
│   │   ├── homogeneity.py
│   │   ├── trend.py
│   │   └── outliers.py
│   ├── frequency/                  # Etapa 4
│   │   ├── distributions.py
│   │   ├── fitting.py
│   │   └── design_events.py
│   └── shared/
│       └── preprocessing.py        # Detección de ceros, negativos, NaN
├── api/                            # Capa FastAPI — consume core/
│   ├── main.py
│   ├── routers/
│   │   └── validate.py
│   └── schemas/
│       └── validation.py           # Pydantic models del schema de respuesta
├── frontend/                       # React o Streamlit
├── tests/
│   ├── fixtures/
│   │   ├── series_referencia_1.csv # Extraída de la tesis
│   │   ├── series_referencia_2.csv
│   │   └── expected_results.json   # Veredictos y estadísticos esperados
│   ├── unit/
│   │   ├── test_independence.py
│   │   ├── test_homogeneity.py
│   │   ├── test_trend.py
│   │   └── test_outliers.py
│   ├── integration/
│   │   └── test_api_validate.py
│   └── e2e/
│       └── test_full_pipeline.py
├── docs/
│   └── schema_api.md               # Contrato del schema de respuesta
├── requirements.txt
├── requirements-dev.txt            # pytest, httpx, ruff, etc.
└── README.md
```

### 0.2 Tareas

- [ ] Inicializar el repositorio con la estructura anterior.
- [ ] Extraer de la tesis del Mgter. Ganancias al menos **dos series hidrológicas completas** con sus resultados documentados (estadístico, valor crítico, veredicto por prueba).
- [ ] Crear `tests/fixtures/expected_results.json` con el contrato de correctitud: para cada serie y cada prueba, el resultado esperado. Este archivo es la fuente de verdad de todos los tests de regresión.
- [ ] Documentar en `docs/schema_api.md` el schema completo de respuesta de la API antes de implementarla.
- [ ] Configurar `requirements.txt` y `requirements-dev.txt`.
- [ ] Configurar `ruff` como linter y `black` como formateador.

### 0.3 Criterio de cierre

`expected_results.json` revisado y aprobado por el equipo técnico (incluyendo Co-director). La estructura del repositorio está creada y commiteada.

---

## Etapa 1 — Core Estadístico

*Objetivo: Implementar todos los módulos de validación como una librería Python pura, sin ninguna dependencia de HTTP ni de interfaz gráfica.*

### 1.1 Módulo de preprocesamiento (`core/shared/preprocessing.py`)

- [ ] Función `load_series(source) -> pd.Series`: acepta CSV, Excel o lista de floats.
- [ ] Función `detect_physical_inconsistencies(series) -> list[Warning]`: detecta ceros, negativos y NaN. Devuelve advertencias estructuradas, nunca lanza excepciones que corten el flujo.
- [ ] Función `apply_log_transform(series) -> pd.Series`: aplica transformación logarítmica solo si no hay inconsistencias físicas, o con advertencia explícita si las hay.

### 1.2 Módulo de Independencia (`core/validation/independence.py`)

- [ ] `anderson_test(series) -> TestResult`: coeficiente de autocorrelación serial para $k = 1, 2, 3...$, bandas de confianza al 95%, criterio del 10%.
- [ ] `wald_wolfowitz_test(series) -> TestResult`: cálculo de corridas, contraste con distribución normal.
- [ ] `resolve_independence(anderson: TestResult, ww: TestResult) -> GroupVerdict`: encapsula la jerarquía — Anderson es determinante; Wald-Wolfowitz actúa como verificación. El veredicto grupal y si se aplicó la jerarquía quedan registrados en el objeto devuelto.

### 1.3 Módulo de Homogeneidad (`core/validation/homogeneity.py`)

- [ ] `helmert_test(series) -> TestResult`
- [ ] `t_student_test(series) -> TestResult`
- [ ] `cramer_test(series) -> TestResult`
- [ ] **Sin función de resolución agregada.** Las tres pruebas se reportan individualmente. El módulo expone `run_homogeneity(series) -> list[TestResult]`.

### 1.4 Módulo de Tendencia (`core/validation/trend.py`)

- [ ] `mann_kendall_test(series) -> TestResult`
- [ ] `kolmogorov_smirnov_trend_test(series) -> TestResult`

### 1.5 Módulo de Atípicos (`core/validation/outliers.py`)

- [ ] `chow_test(series, use_log=True) -> OutlierResult`: detecta datos atípicos, reporta índices sospechosos. Antes de la transformación logarítmica, llama a `detect_physical_inconsistencies`.

### 1.6 Orquestador del pipeline (`core/validation/__init__.py`)

- [ ] `run_validation_pipeline(series) -> ValidationReport`: ejecuta los cuatro grupos de pruebas en orden, agrega advertencias físicas, devuelve el objeto completo que la API va a serializar.

### 1.7 Tipos compartidos (`core/shared/types.py`)

Definir los dataclasses o Pydantic models del core:

```python
@dataclass
class TestResult:
    name: str
    statistic: float
    critical_value: float
    alpha: float          # siempre 0.05
    verdict: Literal["ACCEPTED", "REJECTED"]
    detail: dict          # datos adicionales específicos de cada prueba

@dataclass
class GroupVerdict:
    condition: str        # "independence" | "homogeneity" | "trend" | "outliers"
    individual_results: list[TestResult]
    resolved_verdict: Literal["ACCEPTED", "REJECTED", "INCONCLUSIVE"] | None
    hierarchy_applied: bool

@dataclass
class ValidationReport:
    n: int
    warnings: list[dict]
    independence: GroupVerdict
    homogeneity: GroupVerdict
    trend: GroupVerdict
    outliers: GroupVerdict
```

---

### ✅ Tests — Etapa 1

> Ubicación: `tests/unit/`

**`test_preprocessing.py`**
- Carga correcta desde CSV y desde lista de floats.
- Detección de ceros, negativos y NaN devuelve advertencias (no excepciones).
- La transformación logarítmica falla silenciosamente y genera warning si hay valores inválidos.

**`test_independence.py`**
- Anderson acepta una serie conocida de la tesis → veredicto y estadístico coinciden con `expected_results.json`.
- Anderson rechaza una serie con autocorrelación introducida artificialmente.
- Jerarquía: Anderson acepta + Wald-Wolfowitz rechaza → `resolve_independence` devuelve ACCEPTED con `hierarchy_applied=True`.
- Jerarquía: Anderson rechaza → resultado es REJECTED independientemente de Wald-Wolfowitz.

**`test_homogeneity.py`**
- Helmert, t-Student y Cramer reproducen los resultados de la tesis sobre las series de referencia.
- Para la serie documentada en la tesis donde Helmert rechaza y t-Student/Cramer aceptan: los tres resultados son correctos individualmente. No existe un veredicto agregado.

**`test_trend.py`**
- Mann-Kendall acepta una serie sin tendencia conocida.
- KS de tendencia rechaza una serie con tendencia lineal creciente introducida artificialmente.

**`test_outliers.py`**
- Chow detecta el índice correcto en una serie con un outlier conocido.
- Chow no detecta outliers en una serie limpia de referencia.
- Chow genera warning (no excepción) si la serie contiene ceros antes de la transformación logarítmica.

**`test_pipeline.py`**
- `run_validation_pipeline` sobre la serie de referencia 1 produce un `ValidationReport` que coincide campo a campo con `expected_results.json`.
- `run_validation_pipeline` sobre la serie de referencia 2 ídem.

---

### 🔧 CI — Etapa 1 (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install ruff black
      - run: ruff check .
      - run: black --check .

  test-core:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/unit/ -v --tb=short
```

### Criterio de cierre — Etapa 1

Todos los tests unitarios pasan en CI. Los estadísticos calculados coinciden con error cero frente a `expected_results.json`.

---

## Etapa 2 — API REST

*Objetivo: Exponer el core estadístico como servicio HTTP consumible externamente. Esta etapa no modifica la lógica del core — solo la envuelve.*

### 2.1 Setup de FastAPI (`api/main.py`)

- [ ] Configuración base de FastAPI con CORS habilitado.
- [ ] Endpoint `GET /health`: devuelve `{ "status": "ok", "version": "x.x" }`.
- [ ] Configuración de Swagger UI en `/docs` y ReDoc en `/redoc`.

### 2.2 Schemas Pydantic (`api/schemas/validation.py`)

- [ ] Traducir los dataclasses del core a modelos Pydantic para serialización JSON.
- [ ] Modelo de entrada: `SeriesInput` — acepta lista de floats o referencia a archivo subido.
- [ ] Modelo de salida: `ValidationResponse` — refleja exactamente el schema documentado en `docs/schema_api.md`.

### 2.3 Endpoint principal (`api/routers/validate.py`)

- [ ] `POST /validate`: recibe `SeriesInput`, invoca `run_validation_pipeline`, serializa y devuelve `ValidationResponse`.
- [ ] `POST /validate/file`: acepta un archivo `.csv` o `.xlsx` mediante `multipart/form-data`.
- [ ] Manejo de errores HTTP: 422 para entrada malformada, 400 para series vacías, 200 con `warnings` para inconsistencias físicas (la API nunca devuelve 500 por datos del usuario).

### 2.4 Documentación de la API

- [ ] Todos los endpoints tienen descripciones, ejemplos de request/response y códigos de error documentados en el schema Pydantic (campo `description` y `example`).
- [ ] `docs/schema_api.md` actualizado con los ejemplos reales generados por Swagger.

---

### ✅ Tests — Etapa 2

> Ubicación: `tests/integration/`

**`test_api_health.py`**
- `GET /health` devuelve 200 con el campo `status`.

**`test_api_validate.py`**
- `POST /validate` con la serie de referencia 1 devuelve 200 y el body coincide con `expected_results.json`.
- `POST /validate` con la serie de referencia 2 ídem.
- `POST /validate` con una serie vacía devuelve 400.
- `POST /validate` con datos no numéricos devuelve 422.
- `POST /validate` con una serie que contiene ceros devuelve 200 con al menos un warning `NEGATIVE_OR_ZERO_VALUES` y el análisis completo.
- `POST /validate/file` con un `.csv` válido devuelve los mismos resultados que el endpoint JSON.

**`test_api_schema.py`**
- La respuesta de `/validate` contiene todos los campos requeridos del schema: `n`, `warnings`, `validation.independence`, `validation.homogeneity`, `validation.trend`, `validation.outliers`.
- Cada `TestResult` en la respuesta contiene `statistic`, `critical_value`, `alpha` y `verdict`.

---

### 🔧 CI — Etapa 2 (agregado a `ci.yml`)

```yaml
  test-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Start API
        run: uvicorn api.main:app --host 0.0.0.0 --port 8000 &
      - run: sleep 3
      - run: pytest tests/integration/ -v --tb=short
```

### Criterio de cierre — Etapa 2

Todos los tests de integración pasan en CI. La API es consumible desde Postman o curl con las series de referencia y produce resultados idénticos al core.

---

## Etapa 3 — Frontend: Módulo de Validación

*Objetivo: Construir la interfaz completa para la Etapa 1 del pipeline hidrológico. El frontend consume la API de la Etapa 2 y no contiene lógica estadística propia.*

### 3.1 Setup del proyecto frontend

- [ ] Inicializar proyecto React (Vite) o Streamlit según decisión de arquitectura.
- [ ] Configurar proxy hacia la API local para desarrollo.
- [ ] Configurar variables de entorno para la URL base de la API.

### 3.2 Módulo de ingesta de datos

- [ ] Componente de drag & drop para archivos `.csv` y `.xlsx`.
- [ ] Tabla interactiva para ingreso y edición manual de datos.
- [ ] Validación visual previa al envío: resaltar celdas con valores cero o negativos con advertencia inline.
- [ ] Botón "Ejecutar análisis" que invoca `POST /validate`.

### 3.3 Dashboard de resultados — Vista Semáforo

- [ ] Panel de resumen con el estado de las cuatro condiciones (independencia, homogeneidad, tendencia, atípicos).
- [ ] Indicación visual cuando pruebas de una misma condición no coinciden (ej. Helmert rechaza, t-Student acepta).
- [ ] Sección de advertencias físicas destacada antes de los resultados estadísticos.

### 3.4 Paneles expandibles por prueba — Modo Docente

- [ ] Cada prueba expone: nombre, estadístico calculado, valor crítico, $\alpha$, veredicto y explicación teórica del mecanismo.
- [ ] Para independencia: nota visible si se aplicó la jerarquía Anderson → Wald-Wolfowitz.
- [ ] Para homogeneidad: los tres resultados en paralelo con nota explicando por qué pueden diferir.
- [ ] Los paneles están colapsados por defecto y se expanden bajo demanda.

### 3.5 Visualizaciones

- [ ] Gráfico de dispersión temporal de la serie ingresada.
- [ ] Correlograma de Anderson con bandas de confianza al 95%.

---

### ✅ Tests — Etapa 3

> Ubicación: `tests/e2e/` — usar Playwright o Cypress

**`test_ui_ingesta.py`**
- El componente de carga acepta un CSV válido y muestra los datos en la tabla.
- Al ingresar un valor negativo manualmente, aparece el indicador visual de advertencia antes de enviar.

**`test_ui_resultados.py`**
- Al ejecutar el análisis con la serie de referencia 1, el semáforo muestra los estados correctos para las cuatro condiciones.
- Los paneles expandibles muestran el estadístico y valor crítico correctos al abrirse.
- La nota de jerarquía de Anderson aparece cuando corresponde.
- Cuando Helmert y t-Student tienen veredictos distintos, ambos se muestran por separado sin un veredicto agregado.

**`test_ui_graficos.py`**
- El gráfico de dispersión se renderiza con el número correcto de puntos.
- El correlograma se renderiza al expandir el panel de Anderson.

---

### 🔧 CI — Etapa 3 (agregado a `ci.yml`)

```yaml
  test-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Install Playwright
        run: playwright install --with-deps chromium
      - name: Start API
        run: uvicorn api.main:app --host 0.0.0.0 --port 8000 &
      - name: Start Frontend
        run: npm --prefix frontend run dev &
      - run: sleep 5
      - run: pytest tests/e2e/ -v --tb=short
```

### Criterio de cierre — Etapa 3

Un usuario sin conocimiento previo puede cargar una serie, leer el veredicto de cada prueba y entender la razón del rechazo. Todos los tests E2E pasan en CI.

---

## Etapa 4 — Análisis de Frecuencia

*Objetivo: Extender el sistema con el módulo de ajuste de distribuciones y estimación de eventos de diseño sobre series que pasaron la validación.*

### 4.1 Motor de distribuciones (`core/frequency/distributions.py`)

- [ ] Implementar las 13 distribuciones del dominio: Normal, Log-Normal, Gumbel, GEV, Pearson III, Log-Pearson III, Exponencial, Gamma, Weibull, entre otras.
- [ ] Cada distribución expone una interfaz común: `fit(series)`, `cdf(x)`, `ppf(p)` (inversa).

### 4.2 Métodos de estimación de parámetros (`core/frequency/fitting.py`)

- [ ] Método de Momentos (MOM).
- [ ] Máxima Verosimilitud (MLE).
- [ ] Máxima Entropía (MEnt).
- [ ] Cada método devuelve los parámetros estimados y un objeto `FitResult` con la distribución calibrada.

### 4.3 Bondad de ajuste (`core/frequency/fitting.py`)

- [ ] Prueba Chi Cuadrado.
- [ ] Prueba de Kolmogorov-Smirnov de bondad de ajuste.
- [ ] Error Estándar de Ajuste (EEA).
- [ ] Tabla comparativa: para cada distribución ajustada, los tres indicadores de bondad de ajuste.

### 4.4 Eventos de diseño (`core/frequency/design_events.py`)

- [ ] `calculate_design_event(fit: FitResult, T: float) -> DesignEvent`: dado un período de retorno $T$, calcula la probabilidad anual $1/T$ y el valor del evento extremo correspondiente.

### 4.5 API — nuevo endpoint (`api/routers/frequency.py`)

- [ ] `POST /frequency/fit`: recibe una serie validada y devuelve todas las distribuciones ajustadas con sus indicadores de bondad de ajuste.
- [ ] `POST /frequency/design-event`: recibe una distribución ajustada y un $T$, devuelve el evento de diseño.

### 4.6 Frontend — módulo de frecuencia

- [ ] Selector de distribuciones y método de estimación.
- [ ] Tabla comparativa de bondad de ajuste con resaltado de la distribución recomendada.
- [ ] Gráfico de ajuste: curva teórica superpuesta sobre los puntos de la muestra en escala de probabilidad.
- [ ] Input de período de retorno $T$ con output de probabilidad anual y valor de diseño.
- [ ] Exportación de informe: PDF o Excel con serie validada, distribuciones ajustadas y evento de diseño.

---

### ✅ Tests — Etapa 4

> Unitarios en `tests/unit/`, integración en `tests/integration/`, E2E en `tests/e2e/`

**`test_distributions.py`**
- Cada distribución implementada reproduce parámetros conocidos sobre una muestra de referencia (comparar contra valores de la tesis o de SciPy como ground truth).
- `ppf(cdf(x)) ≈ x` para todos los valores de la serie (consistencia interna).

**`test_fitting.py`**
- MOM, MLE y MEnt producen parámetros dentro de tolerancia aceptable para la distribución Log-Pearson III sobre la serie de referencia.
- Los tres indicadores de bondad de ajuste se calculan correctamente.

**`test_design_events.py`**
- Para $T = 100$, la probabilidad anual devuelta es exactamente $0.01$.
- El valor de diseño coincide con el documentado en la tesis para la serie y distribución de referencia.

**`test_api_frequency.py`**
- `POST /frequency/fit` devuelve resultados para todas las distribuciones implementadas.
- `POST /frequency/design-event` con $T = 50$ devuelve el valor correcto.

**`test_ui_frequency.py`** (E2E)
- La tabla de bondad de ajuste se renderiza con todas las distribuciones.
- Al ingresar $T = 100$, el valor de diseño se muestra correctamente.

---

### 🔧 CI — Etapa 4 (sin cambios en el workflow)

Los jobs existentes `test-core`, `test-api` y `test-e2e` cubren automáticamente los nuevos tests al estar en las mismas carpetas.

### Criterio de cierre — Etapa 4

El sistema produce un informe exportable con evento de diseño para un $T$ dado. El valor calculado coincide con el documentado en la tesis de referencia.

---

## Etapa 5 — QA Final e Integración

*Objetivo: Validar el sistema completo contra la fuente de verdad, preparar la integración con GeoAI y cerrar la documentación.*

### 5.1 Validación cruzada completa

- [ ] Ejecutar el pipeline completo (validación + frecuencia + evento de diseño) sobre **todas** las series documentadas en la tesis del Mgter. Ganancias.
- [ ] Comparar campo a campo contra los resultados del Excel de referencia. Documentar cualquier diferencia encontrada y su resolución.
- [ ] Incluir la serie Alpa Corral del Río Barrancas (caso documentado donde la serie no pasa independencia ni homogeneidad pero el análisis continúa con advertencias).

### 5.2 Revisión del Modo Docente

- [ ] Revisión con el equipo técnico de todos los textos explicativos de cada prueba.
- [ ] Verificar que la jerarquía Anderson/Wald-Wolfowitz está correctamente comunicada en la UI.
- [ ] Verificar que el tratamiento de desacuerdos en homogeneidad está correctamente comunicado.

### 5.3 Preparación para integración con GeoAI

- [ ] Verificar que el endpoint `/validate` devuelve toda la información que el módulo de GeoAI necesita consumir.
- [ ] Documentar el contrato de integración en `docs/geoai_integration.md`: qué consume, qué devuelve, qué errores maneja.
- [ ] Versionar la API (`/v1/validate`) para garantizar compatibilidad futura.

### 5.4 Documentación final

- [ ] `README.md` del repositorio con instrucciones de setup, ejecución local y ejecución de tests.
- [ ] `docs/schema_api.md` con el schema final y ejemplos reales.
- [ ] `docs/geoai_integration.md` con el contrato de integración.
- [ ] `CHANGELOG.md` con el historial de etapas completadas.

---

### ✅ Tests — Etapa 5

**`test_regression_tesis.py`** (en `tests/`)
- Para cada serie de la tesis con resultado documentado: el pipeline completo reproduce estadístico, valor crítico y veredicto con error cero.
- La serie Alpa Corral: el pipeline devuelve los warnings correctos y produce el análisis de frecuencia sin lanzar errores.
- Todos los eventos de diseño documentados en la tesis se reproducen dentro de la tolerancia numérica aceptable.

**`test_api_contract.py`**
- El schema de respuesta no tiene campos faltantes ni tipos incorrectos.
- El versionado `/v1/validate` funciona y es equivalente a `/validate`.

---

### 🔧 CI — Etapa 5 (estado final de `ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install ruff black
      - run: ruff check .
      - run: black --check .

  test-core:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/unit/ -v --tb=short --cov=core --cov-report=xml
      - uses: codecov/codecov-action@v4

  test-api:
    runs-on: ubuntu-latest
    needs: test-core
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: uvicorn api.main:app --host 0.0.0.0 --port 8000 &
      - run: sleep 3
      - run: pytest tests/integration/ -v --tb=short

  test-e2e:
    runs-on: ubuntu-latest
    needs: test-api
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: playwright install --with-deps chromium
      - run: uvicorn api.main:app --host 0.0.0.0 --port 8000 &
      - run: npm --prefix frontend run dev &
      - run: sleep 5
      - run: pytest tests/e2e/ -v --tb=short

  test-regression:
    runs-on: ubuntu-latest
    needs: test-e2e
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/test_regression_tesis.py -v --tb=short
```

### Criterio de cierre — Etapa 5

Todos los jobs del pipeline CI pasan en verde. La validación cruzada contra la tesis no reporta ninguna diferencia no justificada. El sistema está listo para integrarse con el módulo de GeoAI.

---

## 📊 Resumen de cobertura de tests por etapa

| Etapa | Tipo de tests | Qué valida |
| :---: | :--- | :--- |
| **1** | Unitarios | Correctitud matemática de cada prueba estadística |
| **2** | Integración | Contrato HTTP de la API, serialización, manejo de errores |
| **3** | E2E | Experiencia de usuario, renderizado correcto de resultados |
| **4** | Unitarios + Integración + E2E | Ajuste de distribuciones, bondad de ajuste, eventos de diseño |
| **5** | Regresión | Reproducibilidad completa contra la tesis de referencia |

---

## 🚀 Hitos de entrega

| Hito | Etapa de cierre | Criterio verificable |
| :--- | :---: | :--- |
| **M0 — Verdad establecida** | 0 | `expected_results.json` aprobado por el equipo técnico |
| **M1 — Motor funcionando** | 1 | Tests unitarios en verde en CI, error cero vs fixtures |
| **M2 — API consumible** | 2 | `POST /validate` reproducible desde Postman con series reales |
| **M3 — UI de validación** | 3 | Tests E2E en verde, revisión de Modo Docente aprobada |
| **M4 — Frecuencia completa** | 4 | Evento de diseño exportable, validado contra la tesis |
| **M5 — Sistema listo** | 5 | Pipeline CI completo en verde, contrato GeoAI documentado |

---

*Documento de trabajo interno — PI ISI UCC 2026*
*Octavio Carpineti | Kevin Massholder*
*Director: Dr. Ing. Carlos Catalini | Co-director: Mgter. Ing. Facundo Ganancias*