/**
 * METIS - Sistema Integrado de Análisis Hidrológico
 *
 * Este módulo implementa la UI completa unificada para el sistema METIS,
 * integrando tres módulos en un flujo continuo:
 *
 *   1. VALIDACIÓN: Ingesta de datos, validación estadística básica
 *      - POST /validate: Tests de independencia, homogeneidad, tendencia, atípicos
 *
 *   2. ANÁLISIS DE FRECUENCIA: Ajuste de distribuciones y eventos de diseño
 *      - POST /frequency/fit: Ajuste de distribuciones (Gumbel, GEV, Log-Pearson III, etc.)
 *      - POST /frequency/design-event: Cálculo de eventos de diseño
 *
 *   3. ANÁLISIS SAMHIA: Análisis estadístico completo con reportes PDF
 *      - POST /reports/analyze: Análisis estadístico completo
 *      - POST /reports/pdf: Generación de reportes PDF de 10 páginas
 *
 * Arquitectura unificada:
 *   - Datos fluyen de arriba hacia abajo (serie compartida entre módulos)
 *   - Cada módulo tiene su propio panel ejecutable independientemente
 *   - Resultados se muestran en secciones colapsables
 *
 * @module App
 */

import { useMemo, useState } from "react";
import * as XLSX from "xlsx";

// =============================================================================
// CONSTANTES DE CONFIGURACIÓN
// =============================================================================

/** URL base de la API METIS */
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/** Máximo lag para cálculo de autocorrelación (correlograma) */
const MAX_LAG = 10;

/** Métodos de estimación disponibles para análisis de frecuencia */
const ESTIMATION_METHODS = ["MOM", "MLE", "MEnt"];

/** Distribuciones disponibles para ajuste de frecuencia */
const AVAILABLE_DISTRIBUTIONS = [
  "Log-Pearson III",
  "Gumbel",
  "GEV",
  "Log-Normal",
  "Normal",
  "Pearson III",
];

// =============================================================================
// FUNCIONES DE UTILIDAD - MAPEO DE VEREDICTOS
// =============================================================================

/**
 * Convierte veredicto API a clase CSS para estilizado.
 * @param {string} verdict - "ACCEPTED", "REJECTED", o "INCONCLUSIVE"
 * @returns {string} Clase CSS correspondiente
 */
const verdictLabel = (verdict) => {
  switch (verdict) {
    case "ACCEPTED":
      return "accepted";
    case "REJECTED":
      return "rejected";
    default:
      return "inconclusive";
  }
};

/**
 * Traduce veredicto API a texto en español.
 * @param {string} verdict - Veredicto de la API
 * @returns {string} Texto localizado
 */
const statusText = (verdict) => {
  if (verdict === "ACCEPTED") return "Aceptado";
  if (verdict === "REJECTED") return "Rechazado";
  return "Inconcluso";
};

/** Explicaciones de condiciones para panel informativo */
const explanations = {
  independence:
    "Para independencia se evalúa el comportamiento serial. Anderson domina y Wald-Wolfowitz valida la consistencia.",
  homogeneity:
    "La homogeneidad se presenta como tres pruebas independientes. No hay veredicto agregado para evitar falsa seguridad.",
  trend:
    "La tendencia se controla con Mann-Kendall y una prueba KS entre mitades de la serie.",
  outliers:
    "El test de Chow identifica puntos sospechosos de ruptura o atípicos en la serie.",
};

// =============================================================================
// FUNCIONES DE PARSING - INGESTA DE DATOS
// =============================================================================

/**
 * Parsea contenido CSV extrayendo la columna de valores numéricos.
 *
 * @param {string} text - Contenido del archivo CSV
 * @returns {number[]} Array de valores numéricos (segunda columna)
 */
function parseCsv(text) {
  const lines = text
    .trim()
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "")
    .slice(1); // Skip header
  return lines
    .map((line) => line.split(/[;,]/)[1]?.trim()) // Take second column (caudal)
    .filter((value) => value !== "" && value !== undefined)
    .map((value) => Number(value));
}

/**
 * Parsea buffer de archivo Excel extrayendo todos los valores numéricos.
 *
 * @param {ArrayBuffer} buffer - Buffer del archivo Excel
 * @returns {number[]} Array de valores numéricos
 */
function parseExcel(buffer) {
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
  return data
    .flat()
    .filter((value) => value !== null && value !== undefined && value !== "")
    .map((value) => Number(value));
}

// =============================================================================
// FUNCIONES DE VALIDACIÓN Y CÁLCULO
// =============================================================================

/**
 * Construye lista de advertencias para valores problemáticos.
 *
 * Detecta valores <= 0 (cero o negativos) que son físicamente
 * inválidos para caudales y generan advertencia previa.
 *
 * @param {number[]} series - Serie de valores
 * @returns {Array<{code, message, affected_indices}>} Lista de advertencias
 */
function buildWarnings(series) {
  const warnings = [];
  const indices = series
    .map((value, index) => ({ value, index }))
    .filter((item) => item.value === 0 || item.value < 0)
    .map((item) => item.index);
  if (indices.length > 0) {
    warnings.push({
      code: "NEGATIVE_OR_ZERO_VALUES",
      message: `Se encontraron ${indices.length} valores negativos o cero.`,
      affected_indices: indices,
    });
  }
  return warnings;
}

/**
 * Calcula autocorrelación de la serie para el correlograma.
 *
 * Implementa el cálculo de autocorrelación con desfasajes (lags)
 * hasta MAX_LAG para visualización del correlograma.
 *
 * @param {number[]} series - Serie de valores (filtrada de no finitos)
 * @returns {Array<{lag, value}>} Array de coeficientes de autocorrelación
 */
function computeAutoCorrelation(series) {
  const n = series.length;
  if (n < 2) {
    return [];
  }
  const mean = series.reduce((sum, value) => sum + value, 0) / n;
  const deviations = series.map((value) => value - mean);
  const variance = deviations.reduce((sum, value) => sum + value * value, 0);

  return Array.from({ length: Math.min(MAX_LAG, n - 1) }, (_, lag) => {
    const autocov = deviations.reduce(
      (sum, value, index) =>
        sum + value * (series[index + lag] === undefined ? 0 : series[index + lag] - mean),
      0
    );
    return {
      lag: lag + 1,
      value: variance !== 0 ? autocov / variance : 0,
    };
  });
}

/**
 * Convierte serie a formato CSV para exportación.
 * @param {number[]} series - Serie de valores
 * @returns {string} Contenido CSV (un valor por línea)
 */
function serieToCsv(series) {
  return series.map((value) => value.toString()).join("\n");
}

// =============================================================================
// COMPONENTE PRINCIPAL APP
// =============================================================================

/**
 * Componente principal de la aplicación METIS.
 *
 * Gestiona el estado global de la serie, la comunicación con la API,
 * y el renderizado de las 4 secciones de la UI:
 *   1. Ingesta de datos (manual y archivos)
 *   2. Resumen de la serie (warnings, identificador)
 *   3. Visualizaciones (dispersión, correlograma)
 *   4. Resultados de validación (dashboard semáforo)
 *
 * @returns {JSX.Element} Aplicación React completa
 */
export default function App() {
  // ---------------------------------------------------------------------------
  // ESTADO GLOBAL - DATOS COMPARTIDOS
  // ---------------------------------------------------------------------------

  const [series, setSeries] = useState([0, 0, 0]);
  const [seriesId, setSeriesId] = useState("serie_local");
  const [fileError, setFileError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  // ---------------------------------------------------------------------------
  // ESTADO - MÓDULO DE VALIDACIÓN
  // ---------------------------------------------------------------------------

  const [fetchError, setFetchError] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [isSending, setIsSending] = useState(false);

  // ---------------------------------------------------------------------------
  // ESTADO - MÓDULO DE FRECUENCIA
  // ---------------------------------------------------------------------------

  const [estimationMethod, setEstimationMethod] = useState("MOM");
  const [selectedDistributions, setSelectedDistributions] = useState(AVAILABLE_DISTRIBUTIONS);
  const [fitResults, setFitResults] = useState(null);
  const [fitError, setFitError] = useState("");
  const [isFitting, setIsFitting] = useState(false);
  const [selectedDistribution, setSelectedDistribution] = useState(null);
  const [returnPeriod, setReturnPeriod] = useState(100);
  const [designEvent, setDesignEvent] = useState(null);
  const [designError, setDesignError] = useState("");
  const [isCalculatingDesign, setIsCalculatingDesign] = useState(false);

  // ---------------------------------------------------------------------------
  // ESTADO - MÓDULO SAMHIA
  // ---------------------------------------------------------------------------

  const [reservoirName, setReservoirName] = useState("Embalse");
  const [seriesName, setSeriesName] = useState("Variable");
  const [dates, setDates] = useState([]);
  const [samhiaData, setSamhiaData] = useState([]);
  const [alpha, setAlpha] = useState(0.05);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [pdfPath, setPdfPath] = useState(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [pdfError, setPdfError] = useState("");
  const [activeSamhiaTab, setActiveSamhiaTab] = useState("analysis");

  // ---------------------------------------------------------------------------
  // MEMOIZACIÓN DE CÁLCULOS
  // ---------------------------------------------------------------------------

  /** Advertencias calculadas de la serie actual */
  const warnings = useMemo(() => buildWarnings(series), [series]);

  /** Validación de serie: mínimo 3 valores numéricos */
  const seriesValid = series.length >= 3 && series.every((value) => !Number.isNaN(value));

  /** Coeficientes de autocorrelación para correlograma */
  const autoCorrelation = useMemo(
    () => computeAutoCorrelation(series.filter((value) => Number.isFinite(value))),
    [series]
  );

  /** Banda de confianza 95% para correlograma */
  const band = series.length > 0 ? 1.96 / Math.sqrt(series.length) : 0;

  // ---------------------------------------------------------------------------
  // HANDLERS DE MODIFICACIÓN DE SERIE
  // ---------------------------------------------------------------------------

  /** Actualiza valor en índice específico */
  const updateByIndex = (index, value) => {
    const next = [...series];
    next[index] = value;
    setSeries(next);
  };

  /** Agrega fila con valor 0 al final */
  const addRow = () => setSeries((prev) => [...prev, 0]);

  /** Elimina fila en índice específico */
  const removeRow = (index) => setSeries((prev) => prev.filter((_, i) => i !== index));

  /** Toggle selección de distribución para ajuste de frecuencia */
  const toggleDistribution = (dist) => {
    setSelectedDistributions((prev) =>
      prev.includes(dist) ? prev.filter((d) => d !== dist) : [...prev, dist]
    );
  };

  // ---------------------------------------------------------------------------
  // HANDLERS DE API - VALIDACIÓN
  // ---------------------------------------------------------------------------

  /**
   * Ejecuta análisis enviando serie a la API.
   *
   * POST /validate con body { series, series_id }
   * Almacena respuesta en estado 'analysis' o error en 'fetchError'
   */
  const handleSubmit = async () => {
    setFetchError("");
    if (!seriesValid) {
      setFetchError("La serie debe tener al menos 3 valores numéricos.");
      return;
    }

    setIsSending(true);
    try {
      const response = await fetch(`${API_BASE}/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ series, series_id: seriesId }),
      });

      const json = await response.json();
      if (!response.ok) {
        setFetchError(json.detail || "Error al procesar la serie");
        setAnalysis(null);
      } else {
        setAnalysis(json);
      }
    } catch (error) {
      setFetchError(
        `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`
      );
      setAnalysis(null);
    } finally {
      setIsSending(false);
    }
  };

  // ---------------------------------------------------------------------------
  // HANDLERS DE API - FRECUENCIA
  // ---------------------------------------------------------------------------

  /**
   * Ejecuta ajuste de distribuciones enviando serie a la API.
   *
   * POST /frequency/fit con body { series, estimation_method, distribution_names }
   */
  const handleFit = async () => {
    setFitError("");
    setFitResults(null);
    setDesignEvent(null);

    if (series.length < 3) {
      setFitError("La serie debe tener al menos 3 valores numéricos.");
      return;
    }

    setIsFitting(true);
    try {
      const response = await fetch(`${API_BASE}/frequency/fit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          series,
          estimation_method: estimationMethod,
          distribution_names: selectedDistributions,
        }),
      });

      const json = await response.json();
      if (!response.ok) {
        setFitError(json.detail || "Error al ajustar distribuciones");
      } else {
        setFitResults(json);
        if (json.recommended_distribution) {
          setSelectedDistribution(json.recommended_distribution);
        }
      }
    } catch (error) {
      setFitError(
        `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`
      );
    } finally {
      setIsFitting(false);
    }
  };

  /**
   * Calcula evento de diseño para el período de retorno seleccionado.
   *
   * POST /frequency/design-event con body { distribution_name, parameters, return_period }
   */
  const handleDesignEvent = async () => {
    setDesignError("");
    setDesignEvent(null);

    if (!selectedDistribution) {
      setDesignError("Selecciona una distribución primero.");
      return;
    }

    if (returnPeriod <= 0) {
      setDesignError("El período de retorno debe ser positivo.");
      return;
    }

    setIsCalculatingDesign(true);
    try {
      const response = await fetch(`${API_BASE}/frequency/design-event`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          distribution_name: selectedDistribution.distribution_name,
          parameters: selectedDistribution.parameters,
          return_period: returnPeriod,
        }),
      });

      const json = await response.json();
      if (!response.ok) {
        setDesignError(json.detail || "Error al calcular evento de diseño");
      } else {
        setDesignEvent(json);
      }
    } catch (error) {
      setDesignError(
        `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`
      );
    } finally {
      setIsCalculatingDesign(false);
    }
  };

  // ---------------------------------------------------------------------------
  // HANDLERS DE API - SAMHIA
  // ---------------------------------------------------------------------------

  /**
   * Ejecuta análisis estadístico completo SAMHIA.
   *
   * POST /reports/analyze con datos de la serie
   */
  const handleAnalyzeSamhia = async () => {
    setAnalysisError("");
    setAnalysisResults(null);

    const validData = series.filter((v) => Number.isFinite(v));
    if (validData.length < 12) {
      setAnalysisError("La serie debe tener al menos 12 datos válidos para el análisis SAMHIA.");
      return;
    }

    setIsAnalyzing(true);
    try {
      const analysisDates = dates.length === validData.length
        ? dates
        : validData.map((_, i) => `2020-${String((i % 12) + 1).padStart(2, '0')}-15`);

      const response = await fetch(`${API_BASE}/reports/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data: validData,
          dates: analysisDates,
          series_name: seriesName,
          reservoir_name: reservoirName,
          alpha: alpha,
        }),
      });

      const json = await response.json();
      if (!response.ok) {
        setAnalysisError(json.detail || "Error al ejecutar análisis SAMHIA");
      } else {
        setAnalysisResults(json);
        setSamhiaData(validData);
      }
    } catch (error) {
      setAnalysisError(
        `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  /**
   * Genera reporte PDF SAMHIA.
   *
   * POST /reports/pdf
   */
  const handleGeneratePdf = async () => {
    setPdfError("");
    setPdfPath(null);

    const validData = series.filter((v) => Number.isFinite(v));
    if (validData.length < 12) {
      setPdfError("La serie debe tener al menos 12 datos válidos.");
      return;
    }

    setIsGeneratingPdf(true);
    try {
      const analysisDates = dates.length === validData.length
        ? dates
        : validData.map((_, i) => `2020-${String((i % 12) + 1).padStart(2, '0')}-15`);

      const response = await fetch(`${API_BASE}/reports/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data: validData,
          dates: analysisDates,
          series_name: seriesName,
          reservoir_name: reservoirName,
          alpha: alpha,
          output_path: `./samhia_report_${reservoirName}_${seriesName}.pdf`,
          institution: "Universidad Católica de Córdoba - EHCPA",
          author: "Sistema METIS",
        }),
      });

      const json = await response.json();
      if (!response.ok) {
        setPdfError(json.detail || "Error al generar PDF");
      } else {
        setPdfPath(json.pdf_path);
      }
    } catch (error) {
      setPdfError(
        `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`
      );
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  /**
   * Descarga el PDF generado.
   */
  const handleDownloadPdf = async () => {
    if (!pdfPath) return;

    try {
      const filename = pdfPath.split(/[\\/]/).pop();
      const response = await fetch(`${API_BASE}/reports/download/${encodeURIComponent(filename)}`);

      if (!response.ok) {
        setPdfError("Error al descargar el PDF");
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `SAMHIA_${reservoirName}_${seriesName}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      setPdfError("Error al descargar el PDF");
    }
  };

  /**
   * Procesa archivo CSV o Excel cargado.
   *
   * Detecta formato por extensión, parsea contenido y actualiza
   * estados 'series' y 'seriesId'.
   *
   * @param {File} file - Archivo seleccionado vía input o drag-drop
   */
  const handleFile = async (file) => {
    setFileError("");
    setFetchError("");
    setAnalysis(null);

    if (!file) return;
    const accepted = ["text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"];
    if (!file.name.endsWith(".csv") && !file.name.endsWith(".xlsx") && !file.name.endsWith(".xls") && !accepted.includes(file.type)) {
      setFileError("Solo se permiten archivos CSV o XLSX.");
      return;
    }

    if (file.name.endsWith(".csv")) {
      const text = await file.text();
      const parsed = parseCsv(text);
      if (parsed.length === 0) {
        setFileError("El archivo no contiene valores numéricos válidos.");
        return;
      }
      setSeries(parsed);
      setSeriesId(file.name);
      return;
    }

    if (file.name.endsWith(".xlsx") || file.name.endsWith(".xls")) {
      const buffer = await file.arrayBuffer();
      const parsed = parseExcel(buffer);
      if (parsed.length === 0) {
        setFileError("El archivo no contiene valores numéricos válidos.");
        return;
      }
      setSeries(parsed);
      setSeriesId(file.name);
      return;
    }

    setFileError("Formato de archivo no compatible.");
  };

  // ---------------------------------------------------------------------------
  // RENDERIZADO
  // ---------------------------------------------------------------------------

  const displayValue = (value) => {
    return Number.isFinite(value) ? value : 0;
  };

  return (
    <div className="app-shell">
      <header className="page-header">
        <div>
          <h1>METIS — Sistema Integrado de Análisis Hidrológico</h1>
          <p>
            Plataforma unificada para validación estadística, análisis de frecuencia y reportes SAMHIA.
            Carga tus datos una vez y ejecuta los análisis que necesites.
          </p>
        </div>
      </header>

      {/* ================================================================
          SECCIÓN 1: INGESTA Y RESUMEN DE DATOS
          ================================================================ */}
      <div className="section-grid">
        <section className="panel">
          <h2>1. Ingesta de datos</h2>
          <div
            className={`file-dropzone ${dragOver ? "dragover" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragOver(false);
              const file = event.dataTransfer.files[0];
              handleFile(file);
            }}
          >
            <strong>Arrastra un CSV o Excel aquí</strong>
            <p>O selecciona un archivo para cargar la serie de valores.</p>
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              style={{ opacity: 0, position: "absolute", inset: 0, cursor: "pointer" }}
              onChange={(event) => handleFile(event.target.files?.[0])}
            />
          </div>
          {fileError ? <div className="error-banner">{fileError}</div> : null}
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Valor</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                {series.map((value, index) => {
                  const invalid = !Number.isFinite(value);
                  const warningValue = value <= 0;
                  return (
                    <tr key={`row-${index}`} className={warningValue ? "cell-error" : ""}>
                      <td>{index + 1}</td>
                      <td>
                        <input
                          type="number"
                          value={displayValue(value)}
                          onChange={(event) => updateByIndex(index, Number(event.target.value))}
                          className={invalid ? "cell-error" : ""}
                        />
                      </td>
                      <td>
                        <button type="button" className="button-secondary" onClick={() => removeRow(index)}>
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="button-group">
            <button type="button" className="button-secondary" onClick={addRow}>
              Agregar fila
            </button>
            <button type="button" className="button-primary" onClick={handleSubmit} disabled={isSending}>
              {isSending ? "Analizando..." : "Ejecutar análisis"}
            </button>
          </div>
          <small>
            Las celdas con valores cero o negativos se resaltan y se consideran advertencias en el análisis.
          </small>
        </section>

        <section className="panel">
          <h2>2. Resumen de la serie</h2>
          <p>
            Identificador: <strong>{seriesId || "serie_local"}</strong>
          </p>
          <p>
            N de datos: <strong>{series.length}</strong>
          </p>
          {warnings.length > 0 ? (
            <div className="warning-banner">
              <strong>Advertencias detectadas</strong>
              <ul>
                {warnings.map((warning) => (
                  <li key={warning.code}>
                    {warning.message} [{warning.affected_indices.join(", ")}]
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="status-card">
              <strong>Estado físico</strong>
              <p>No se detectaron valores cero o negativos.</p>
            </div>
          )}

          <div className="panel" style={{ marginTop: "18px" }}>
            <h3>Gráficos rápidos</h3>
            <div className="chart-box">
              <div className="chart-title">Dispersión temporal</div>
              {series.length >= 2 ? (
                <ScatterPlot values={series} />
              ) : (
                <p>Agrega más datos para ver el gráfico.</p>
              )}
            </div>
            <div className="chart-box" style={{ marginTop: "18px" }}>
              <div className="chart-title">Correlograma preliminar</div>
              {series.length >= 4 ? (
                <Correlogram data={autoCorrelation} band={band} />
              ) : (
                <p>Necesitas al menos 4 datos para ver autocorrelación.</p>
              )}
            </div>
          </div>
        </section>
      </div>

      <section className="panel">
        <h2>3. Resultados de validación</h2>
        {fetchError ? <div className="error-banner">{fetchError}</div> : null}

        {analysis ? (
          <>
            <div className="status-grid" style={{ marginBottom: "18px" }}>
              {[
                { name: "Independencia", verdict: analysis.validation.independence.verdict },
                { name: "Homogeneidad", verdict: analysis.validation.homogeneity.verdict },
                { name: "Tendencia", verdict: analysis.validation.trend.mann_kendall.verdict },
                { name: "Atípicos", verdict: analysis.validation.outliers.chow.verdict },
              ].map((item) => (
                <div key={item.name} className="status-card">
                  <strong>{item.name}</strong>
                  <span className={`pill ${verdictLabel(item.verdict)}`}>
                    {statusText(item.verdict)}
                  </span>
                </div>
              ))}
            </div>

            <div className="accordion">
              <AccordionItem title="Independencia" description={explanations.independence}>
                <div className="panel">
                  <p>
                    Veredicto general: <strong>{statusText(analysis.validation.independence.verdict)}</strong>
                  </p>
                  <p>
                    Jerarquía aplicada: <strong>{analysis.validation.independence.hierarchy_applied ? "Sí" : "No"}</strong>
                  </p>
                  <ResultTable name="Anderson" result={analysis.validation.independence.anderson} />
                  <ResultTable name="Wald-Wolfowitz" result={analysis.validation.independence.wald_wolfowitz} />
                </div>
              </AccordionItem>
              <AccordionItem title="Homogeneidad" description={explanations.homogeneity}>
                <div className="panel">
                  <p>
                    No hay veredicto único. Cada prueba se reporta por separado.
                  </p>
                  <ResultTable name="Helmert" result={analysis.validation.homogeneity.helmert} />
                  <ResultTable name="t-Student" result={analysis.validation.homogeneity.t_student} />
                  <ResultTable name="Cramer" result={analysis.validation.homogeneity.cramer} />
                </div>
              </AccordionItem>
              <AccordionItem title="Tendencia" description={explanations.trend}>
                <div className="panel">
                  <ResultTable name="Mann-Kendall" result={analysis.validation.trend.mann_kendall} />
                  <ResultTable name="Kolmogorov-Smirnov" result={analysis.validation.trend.kolmogorov_smirnov} />
                </div>
              </AccordionItem>
              <AccordionItem title="Atípicos" description={explanations.outliers}>
                <div className="panel">
                  <ResultTable name="Chow" result={analysis.validation.outliers.chow} />
                  <p>
                    Índices marcados: {analysis.validation.outliers.chow.flagged_indices.length > 0 ? analysis.validation.outliers.chow.flagged_indices.join(", ") : "Ninguno"}
                  </p>
                </div>
              </AccordionItem>
            </div>
          </>
        ) : (
          <p>Ejecuta el análisis para ver los resultados de cada prueba.</p>
        )}
      </section>

      {/* ================================================================
          SECCIÓN 4: ANÁLISIS DE FRECUENCIA
          ================================================================ */}
      <section className="panel">
        <h2>4. Análisis de Frecuencia</h2>
        <p style={{ color: "#94a3b8", marginBottom: "18px" }}>
          Ajusta distribuciones de probabilidad a tu serie y calcula eventos de diseño.
        </p>

        <div className="section-grid">
          {/* Panel de configuración de frecuencia */}
          <div>
            <div style={{ marginBottom: "18px" }}>
              <label htmlFor="estimation-method">
                <strong>Método de estimación:</strong>
              </label>
              <select
                id="estimation-method"
                value={estimationMethod}
                onChange={(e) => setEstimationMethod(e.target.value)}
                style={{ marginTop: "8px", width: "100%" }}
              >
                {ESTIMATION_METHODS.map((method) => (
                  <option key={method} value={method}>
                    {method}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: "18px" }}>
              <strong>Distribuciones a ajustar:</strong>
              <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {AVAILABLE_DISTRIBUTIONS.map((dist) => (
                  <label
                    key={dist}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "6px 10px",
                      background: selectedDistributions.includes(dist) ? "#1e3a5f" : "#0f1a2f",
                      border: selectedDistributions.includes(dist) ? "1px solid #3b82f6" : "1px solid #1f2e47",
                      borderRadius: "8px",
                      cursor: "pointer",
                      fontSize: "0.9rem",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedDistributions.includes(dist)}
                      onChange={() => toggleDistribution(dist)}
                    />
                    <span>{dist}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="button-group">
              <button
                type="button"
                className="button-primary"
                onClick={handleFit}
                disabled={isFitting || selectedDistributions.length === 0}
              >
                {isFitting ? "Ajustando..." : "Ajustar distribuciones"}
              </button>
            </div>

            {fitError && <div className="error-banner" style={{ marginTop: "12px" }}>{fitError}</div>}
          </div>

          {/* Panel de resultados de ajuste */}
          <div>
            {fitResults ? (
              <>
                <div className="status-card" style={{ marginBottom: "18px" }}>
                  <strong>Distribución recomendada</strong>
                  {fitResults.recommended_distribution ? (
                    <>
                      <p className="pill accepted" style={{ marginTop: "8px" }}>
                        {fitResults.recommended_distribution.distribution_name}
                      </p>
                      <p style={{ marginTop: "8px", fontSize: "0.9rem", color: "#94a3b8" }}>
                        Método: {fitResults.estimation_method} | N: {fitResults.n}
                      </p>
                    </>
                  ) : (
                    <p>No se pudo determinar una distribución recomendada.</p>
                  )}
                </div>

                <div className="accordion">
                  {fitResults.distributions.map((dist) => (
                    <DistributionResult
                      key={dist.distribution_name}
                      distribution={dist}
                      isSelected={selectedDistribution?.distribution_name === dist.distribution_name}
                      onSelect={() => setSelectedDistribution(dist)}
                    />
                  ))}
                </div>
              </>
            ) : (
              <p>Configura y ejecuta el análisis para ver los resultados.</p>
            )}
          </div>
        </div>

        {/* Cálculo de evento de diseño */}
        {fitResults && selectedDistribution && (
          <div style={{ marginTop: "24px", paddingTop: "24px", borderTop: "1px solid #1f2e47" }}>
            <h3>Cálculo de evento de diseño</h3>
            <div style={{ display: "flex", gap: "18px", flexWrap: "wrap", alignItems: "flex-end", marginTop: "12px" }}>
              <div style={{ flex: 1, minWidth: "200px" }}>
                <label htmlFor="return-period">
                  <strong>Período de retorno (años):</strong>
                </label>
                <input
                  id="return-period"
                  type="number"
                  value={returnPeriod}
                  onChange={(e) => setReturnPeriod(Number(e.target.value))}
                  min="1"
                  step="1"
                  style={{ marginTop: "8px" }}
                />
              </div>
              <button
                type="button"
                className="button-primary"
                onClick={handleDesignEvent}
                disabled={isCalculatingDesign}
              >
                {isCalculatingDesign ? "Calculando..." : "Calcular evento de diseño"}
              </button>
            </div>

            {designError && <div className="error-banner" style={{ marginTop: "12px" }}>{designError}</div>}

            {designEvent && (
              <div className="status-card" style={{ marginTop: "18px" }}>
                <strong>Resultado del evento de diseño</strong>
                <div className="table-wrapper" style={{ marginTop: "12px" }}>
                  <table>
                    <tbody>
                      <tr>
                        <th>Período de retorno</th>
                        <td>{designEvent.return_period.toFixed(1)} años</td>
                      </tr>
                      <tr>
                        <th>Probabilidad anual</th>
                        <td>{(designEvent.annual_probability * 100).toFixed(2)}%</td>
                      </tr>
                      <tr>
                        <th>Valor de diseño</th>
                        <td style={{ fontSize: "1.1rem", fontWeight: "bold", color: "#7dd3fc" }}>
                          {designEvent.design_value.toFixed(2)}
                        </td>
                      </tr>
                      <tr>
                        <th>Distribución utilizada</th>
                        <td>{designEvent.distribution_name}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ================================================================
          SECCIÓN 5: ANÁLISIS SAMHIA Y GENERACIÓN DE REPORTES
          ================================================================ */}
      <section className="panel">
        <h2>5. Análisis SAMHIA y Reportes PDF</h2>
        <p style={{ color: "#94a3b8", marginBottom: "18px" }}>
          Análisis estadístico completo con tests detallados y generación de reportes PDF de 10 páginas.
        </p>

        <div className="section-grid">
          {/* Panel de configuración SAMHIA */}
          <div>
            <div style={{ marginBottom: "12px" }}>
              <label>
                <strong>Nombre del embalse:</strong>
                <input
                  type="text"
                  value={reservoirName}
                  onChange={(e) => setReservoirName(e.target.value)}
                  style={{ marginTop: "6px", width: "100%" }}
                  placeholder="Ej: UCC-DAT-ESR-AH-001"
                />
              </label>
            </div>

            <div style={{ marginBottom: "12px" }}>
              <label>
                <strong>Nombre de la variable:</strong>
                <input
                  type="text"
                  value={seriesName}
                  onChange={(e) => setSeriesName(e.target.value)}
                  style={{ marginTop: "6px", width: "100%" }}
                  placeholder="Ej: Caudal, Nivel, Precipitación"
                />
              </label>
            </div>

            <div style={{ marginBottom: "18px" }}>
              <label>
                <strong>Nivel de significancia (α):</strong>
                <select
                  value={alpha}
                  onChange={(e) => setAlpha(Number(e.target.value))}
                  style={{ marginTop: "6px", width: "100%" }}
                >
                  <option value={0.01}>0.01 (99% confianza)</option>
                  <option value={0.05}>0.05 (95% confianza)</option>
                  <option value={0.10}>0.10 (90% confianza)</option>
                </select>
              </label>
            </div>

            <div className="button-group">
              <button
                type="button"
                className="button-primary"
                onClick={handleAnalyzeSamhia}
                disabled={isAnalyzing || series.length < 12}
              >
                {isAnalyzing ? "Analizando..." : "Ejecutar análisis SAMHIA"}
              </button>
            </div>

            {analysisError && <div className="error-banner" style={{ marginTop: "12px" }}>{analysisError}</div>}

            <small style={{ marginTop: "12px", display: "block", color: "#94a3b8" }}>
              Se requieren al menos 12 datos válidos para el análisis SAMHIA completo.
            </small>
          </div>

          {/* Panel de generación de PDF */}
          <div>
            <p style={{ marginBottom: "12px" }}>
              Genera un reporte PDF completo de 10 páginas con:
            </p>
            <ul style={{ marginLeft: "20px", marginBottom: "16px", color: "#94a3b8", fontSize: "0.9rem" }}>
              <li>Gráficos de serie temporal, años calendario e hidrológico</li>
              <li>Análisis de datos atípicos y boxplots mensuales/anuales</li>
              <li>Histograma, Q-Q plot y función de autocorrelación</li>
              <li>Tablas resumen de estadísticas y año hidrológico</li>
              <li>Resultados de tests de independencia, homogeneidad y tendencia</li>
            </ul>

            <div className="button-group">
              <button
                type="button"
                className="button-primary"
                onClick={handleGeneratePdf}
                disabled={isGeneratingPdf || series.length < 12}
              >
                {isGeneratingPdf ? "Generando PDF..." : "Generar reporte PDF"}
              </button>

              {pdfPath && (
                <button
                  type="button"
                  className="button-secondary"
                  onClick={handleDownloadPdf}
                >
                  Descargar PDF
                </button>
              )}
            </div>

            {pdfError && <div className="error-banner" style={{ marginTop: "12px" }}>{pdfError}</div>}

            {pdfPath && (
              <div className="status-card accepted" style={{ marginTop: "12px" }}>
                <span className="pill accepted">PDF generado exitosamente</span>
                <p style={{ marginTop: "8px", fontSize: "0.9rem" }}>
                  Ruta: {pdfPath}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Resultados del análisis SAMHIA */}
        {analysisResults && (
          <div style={{ marginTop: "24px", paddingTop: "24px", borderTop: "1px solid #1f2e47" }}>
            <h3>Resultados del análisis SAMHIA</h3>

            <div className="status-card" style={{ marginBottom: "18px" }}>
              <strong>Análisis completado</strong>
              <p>Variable: <strong>{analysisResults.series_name}</strong></p>
              <p>Embalse: <strong>{analysisResults.reservoir_name}</strong></p>
              <p>N de datos: <strong>{analysisResults.n_data}</strong></p>
            </div>

            {/* Tabs de resultados SAMHIA */}
            <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
              {["analysis", "independence", "homogeneity", "trend", "outliers"].map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className={`tab-button ${activeSamhiaTab === tab ? "active" : ""}`}
                  onClick={() => setActiveSamhiaTab(tab)}
                  style={{ padding: "8px 16px", fontSize: "0.9rem" }}
                >
                  {tab === "analysis" && "Estadísticas"}
                  {tab === "independence" && "Independencia"}
                  {tab === "homogeneity" && "Homogeneidad"}
                  {tab === "trend" && "Tendencia"}
                  {tab === "outliers" && "Atípicos"}
                </button>
              ))}
            </div>

            {/* Contenido de tabs SAMHIA */}
            {activeSamhiaTab === "analysis" && (
              <DescriptiveStatsPanel stats={analysisResults.descriptive_stats} />
            )}
            {activeSamhiaTab === "independence" && (
              <TestResultsPanel
                title="Tests de Independencia"
                tests={analysisResults.independence}
                description="Evalúan si los datos son independientes (no autocorrelacionados)."
              />
            )}
            {activeSamhiaTab === "homogeneity" && (
              <TestResultsPanel
                title="Tests de Homogeneidad"
                tests={analysisResults.homogeneity}
                description="Evalúan si la serie es homogénea a lo largo del tiempo."
              />
            )}
            {activeSamhiaTab === "trend" && (
              <TestResultsPanel
                title="Tests de Tendencia"
                tests={analysisResults.trend}
                description="Evalúan si existe tendencia significativa en la serie."
              />
            )}
            {activeSamhiaTab === "outliers" && (
              <TestResultsPanel
                title="Detección de Atípicos"
                tests={analysisResults.outliers}
                description="Identificación de valores atípicos y puntos de ruptura."
              />
            )}
          </div>
        )}
      </section>
    </div>
  );
}

function ResultTable({ name, result }) {
  return (
    <div style={{ marginBottom: "16px" }}>
      <h4>{name}</h4>
      <div className="table-wrapper">
        <table>
          <tbody>
            <tr>
              <th>Estadístico</th>
              <td>{result.statistic?.toFixed(4)}</td>
            </tr>
            <tr>
              <th>Valor crítico</th>
              <td>{result.critical_value?.toFixed(4)}</td>
            </tr>
            <tr>
              <th>α</th>
              <td>{result.alpha?.toFixed(2)}</td>
            </tr>
            <tr>
              <th>Veredicto</th>
              <td>{statusText(result.verdict)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AccordionItem({ title, description, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="accordion-item">
      <button className="accordion-button" type="button" onClick={() => setOpen((prev) => !prev)}>
        <span>
          {title} <small>{description}</small>
        </span>
        <span>{open ? "▲" : "▼"}</span>
      </button>
      {open ? <div className="accordion-panel">{children}</div> : null}
    </div>
  );
}

function ScatterPlot({ values }) {
  const width = 560;
  const height = 240;
  const padding = 36;
  const finiteValues = values.filter((val) => Number.isFinite(val));
  const max = Math.max(...finiteValues, 1);
  const min = Math.min(...finiteValues, 0);
  const range = Math.max(max - min, 1);

  const points = finiteValues.map((value, index) => {
    const x = padding + (index / Math.max(values.length - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((value - min) / range) * (height - padding * 2);
    return { x, y };
  });

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="260">
      <rect x="0" y="0" width="100%" height="100%" fill="#08101f" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#334155" />
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#334155" />
      {points.map((point, index) => (
        <circle key={index} cx={point.x} cy={point.y} r="4" fill="#60a5fa" />
      ))}
    </svg>
  );
}

function Correlogram({ data, band }) {
  const width = 560;
  const height = 240;
  const padding = 36;
  const maxValue = Math.max(1, ...data.map((item) => Math.abs(item.value)), band);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="260">
      <rect x="0" y="0" width="100%" height="100%" fill="#08101f" />
      <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="#334155" />
      <line
        x1={padding}
        y1={padding + ((1 - band / maxValue) * (height - padding * 2)) / 2}
        x2={width - padding}
        y2={padding + ((1 - band / maxValue) * (height - padding * 2)) / 2}
        stroke="#fbbf24"
        strokeDasharray="4 3"
      />
      <line
        x1={padding}
        y1={height - padding - ((1 - band / maxValue) * (height - padding * 2)) / 2}
        x2={width - padding}
        y2={height - padding - ((1 - band / maxValue) * (height - padding * 2)) / 2}
        stroke="#fbbf24"
        strokeDasharray="4 3"
      />
      {data.map((item, index) => {
        const x = padding + (index / Math.max(data.length - 1, 1)) * (width - padding * 2);
        const y = height / 2 - (item.value / maxValue) * ((height - padding * 2) / 2);
        return (
          <g key={item.lag}>
            <line
              x1={x}
              y1={height / 2}
              x2={x}
              y2={y}
              stroke="#7dd3fc"
              strokeWidth="10"
            />
            <text x={x} y={height - 12} fill="#94a3b8" fontSize="12" textAnchor="middle">
              {item.lag}
            </text>
          </g>
        );
      })}
      <text x={padding} y={padding - 6} fill="#cbd5e1" fontSize="12">
        Banda 95% ±{band.toFixed(3)}
      </text>
    </svg>
  );
}

// =============================================================================
// SUBCOMPONENTES - ANÁLISIS DE FRECUENCIA
// =============================================================================

function DistributionResult({ distribution, isSelected, onSelect }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="accordion-item">
      <button
        className={`accordion-button ${isSelected ? "selected" : ""}`}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        style={{
          background: isSelected ? "rgba(59, 130, 246, 0.1)" : "transparent",
        }}
      >
        <span>
          {distribution.distribution_name}
          {distribution.is_recommended && (
            <span className="pill accepted" style={{ marginLeft: "8px", fontSize: "0.8rem" }}>
              Recomendada
            </span>
          )}
        </span>
        <span>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="accordion-panel">
          <div style={{ marginBottom: "12px" }}>
            <button
              type="button"
              className="button-secondary"
              onClick={onSelect}
              style={{ fontSize: "0.9rem", padding: "8px 14px" }}
            >
              {isSelected ? "Seleccionada" : "Seleccionar para evento de diseño"}
            </button>
          </div>

          <div style={{ marginBottom: "16px" }}>
            <h4>Parámetros</h4>
            <div className="table-wrapper">
              <table>
                <tbody>
                  {Object.entries(distribution.parameters).map(([key, value]) => (
                    <tr key={key}>
                      <th>{key}</th>
                      <td>{typeof value === "number" ? value.toFixed(4) : value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h4>Bondad de ajuste</h4>
            <div className="table-wrapper">
              <table>
                <tbody>
                  <tr>
                    <th>Chi Cuadrado</th>
                    <td>{distribution.goodness_of_fit.chi_square.toFixed(4)}</td>
                    <td>
                      <span className={`pill ${distribution.goodness_of_fit.chi_square_verdict === "ACCEPTED" ? "accepted" : "rejected"}`}>
                        {distribution.goodness_of_fit.chi_square_verdict === "ACCEPTED" ? "Aceptado" : "Rechazado"}
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <th>Kolmogorov-Smirnov</th>
                    <td>{distribution.goodness_of_fit.ks_statistic.toFixed(4)}</td>
                    <td>
                      <span className={`pill ${distribution.goodness_of_fit.ks_verdict === "ACCEPTED" ? "accepted" : "rejected"}`}>
                        {distribution.goodness_of_fit.ks_verdict === "ACCEPTED" ? "Aceptado" : "Rechazado"}
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <th>EEA</th>
                    <td>{distribution.goodness_of_fit.eea.toFixed(4)}</td>
                    <td>
                      <span className={`pill ${distribution.goodness_of_fit.eea_verdict === "ACCEPTED" ? "accepted" : "rejected"}`}>
                        {distribution.goodness_of_fit.eea_verdict === "ACCEPTED" ? "Aceptado" : "Rechazado"}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// SUBCOMPONENTES - ANÁLISIS SAMHIA
// =============================================================================

function DescriptiveStatsPanel({ stats }) {
  const statsData = [
    { label: "Mediana", value: stats.median?.toFixed(4) },
    { label: "Media", value: stats.mean?.toFixed(4) },
    { label: "1er Cuartil (Q25)", value: stats.q25?.toFixed(4) },
    { label: "3er Cuartil (Q75)", value: stats.q75?.toFixed(4) },
    { label: "Mínimo", value: stats.minimum?.toFixed(4) },
    { label: "Máximo", value: stats.maximum?.toFixed(4) },
    { label: "Asimetría (Skewness)", value: stats.skewness?.toFixed(4) },
    { label: "Kurtosis", value: stats.kurtosis?.toFixed(4) },
    { label: "Desv. Estándar", value: stats.std_dev?.toFixed(4) },
    { label: "Varianza (n-1)", value: stats.variance?.toFixed(4) },
    { label: "N Datos", value: stats.n },
    { label: "Coef. Variación (%)", value: stats.coefficient_of_variation?.toFixed(2) || "N/A" },
  ];

  return (
    <div>
      <h4 style={{ marginBottom: "12px" }}>Estadísticas Descriptivas</h4>
      <div className="table-wrapper">
        <table>
          <tbody>
            {statsData.map((stat) => (
              <tr key={stat.label}>
                <th style={{ textAlign: "left", width: "50%" }}>{stat.label}</th>
                <td style={{ textAlign: "right" }}>{stat.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TestResultsPanel({ title, tests, description }) {
  const testEntries = Object.entries(tests || {});

  if (testEntries.length === 0) {
    return (
      <div>
        <h4 style={{ marginBottom: "12px" }}>{title}</h4>
        <p style={{ color: "#94a3b8" }}>No hay resultados disponibles.</p>
      </div>
    );
  }

  return (
    <div>
      <h4 style={{ marginBottom: "12px" }}>{title}</h4>
      <p style={{ color: "#94a3b8", marginBottom: "12px", fontSize: "0.9rem" }}>
        {description}
      </p>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Test</th>
              <th>Estadístico</th>
              <th>Valor crítico</th>
              <th>p-value/α</th>
              <th>Veredicto</th>
            </tr>
          </thead>
          <tbody>
            {testEntries.map(([key, result]) => (
              <tr key={key}>
                <td><strong>{formatTestName(key)}</strong></td>
                <td>{typeof result.statistic === 'number' ? result.statistic.toFixed(4) : "N/A"}</td>
                <td>{typeof result.critical_value === 'number' ? result.critical_value.toFixed(4) : "N/A"}</td>
                <td>{typeof result.alpha === 'number' ? result.alpha.toFixed(2) : "N/A"}</td>
                <td>
                  <span className={`pill ${verdictLabel(result.verdict)}`}>
                    {statusText(result.verdict)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: "16px" }}>
        {testEntries.map(([key, result]) => {
          if (!result.detail) return null;
          // Convert detail to readable string if it's an object
          let detailText;
          if (typeof result.detail === 'string') {
            detailText = result.detail;
          } else if (typeof result.detail === 'object' && Object.keys(result.detail).length > 0) {
            detailText = Object.entries(result.detail)
              .map(([k, v]) => `${k}: ${v}`)
              .join(', ');
          } else {
            return null;
          }
          return (
            <p key={`detail-${key}`} style={{ fontSize: "0.85rem", color: "#64748b", marginBottom: "4px" }}>
              <strong>{formatTestName(key)}:</strong> {detailText}
            </p>
          );
        })}
      </div>
    </div>
  );
}

function formatTestName(key) {
  const names = {
    anderson: "Anderson (Pearson)",
    wald_wolfowitz: "Wald-Wolfowitz (Runs)",
    durbin_watson: "Durbin-Watson",
    ljung_box: "Ljung-Box",
    spearman: "Spearman",
    helmert: "Helmert",
    t_student: "t-Student",
    cramer: "Cramér-von Mises",
    mann_whitney: "Mann-Whitney",
    mood: "Mood",
    mann_kendall: "Mann-Kendall",
    kolmogorov_smirnov: "Kolmogorov-Smirnov",
    chow: "Chow (Outliers)",
    kn: "Kn (Outliers)",
  };
  return names[key] || key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}
