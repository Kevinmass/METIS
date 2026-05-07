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
import { OutliersPanel } from "./Samhia.jsx";

// Componentes Frutiger Aero
import { WaterChartBox, GlassPanel, AquaButton, ToastContainer } from "./components";
import { AquaLineChart, AquaBarChart, AquaAreaChart, AquaScatterChart } from "./components/charts";

// Hook de notificaciones toast (Epic 4)
import { useToast } from "./hooks/useToast.jsx";

// =============================================================================
// CONSTANTES DE CONFIGURACIÓN
// =============================================================================

/** URL base de la API METIS */
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/** Máximo lag para cálculo de autocorrelación (correlograma) */
const MAX_LAG = 10;

/** Métodos de estimación disponibles para análisis de frecuencia */
const ESTIMATION_METHODS = ["MOM", "MLE", "MEnt", "LMom"];

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
// FUNCIONES DE PARSING AVANZADO - PREVIEW Y SELECCIÓN DE COLUMNAS
// =============================================================================

/**
 * Detecta el tipo de una columna basándose en sus valores.
 *
 * @param {Array} values - Valores de la columna
 * @returns {string} Tipo detectado: 'date', 'numeric', 'text'
 */
function detectColumnType(values) {
  const nonNullValues = values.filter((v) => v !== null && v !== undefined && v !== "");
  if (nonNullValues.length === 0) return "text";

  // Verificar si es fecha
  const datePattern = /^(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2})$/;
  const dateCandidates = nonNullValues.filter((v) => {
    const str = String(v).trim();
    return datePattern.test(str) || !Number.isNaN(Date.parse(str));
  });
  if (dateCandidates.length >= nonNullValues.length * 0.5) return "date";

  // Verificar si es numérica
  const numericCandidates = nonNullValues.filter((v) => !Number.isNaN(Number(v)));
  if (numericCandidates.length >= nonNullValues.length * 0.5) return "numeric";

  return "text";
}

/**
 * Parsea CSV y retorna preview con headers y tipos de columnas.
 *
 * @param {string} text - Contenido del archivo CSV
 * @param {number} maxRows - Máximo de filas para preview
 * @returns {Object} Preview con headers, filas, tipos y sheetNames
 */
function parseCsvPreview(text, maxRows = 5) {
  const lines = text
    .trim()
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "");

  if (lines.length === 0) {
    return { headers: [], rows: [], columnTypes: [], sheetNames: [] };
  }

  // Detectar separador
  const firstLine = lines[0];
  const separator = firstLine.includes(";") ? ";" : ",";

  // Detectar si tiene headers (primera fila contiene texto no numérico)
  const firstRow = firstLine.split(separator).map((c) => c.trim());
  const hasHeaders = firstRow.some((cell) => {
    const num = Number(cell);
    return Number.isNaN(num) || String(cell).match(/^[a-zA-ZáéíóúÁÉÍÓÚñÑ_]/);
  });

  const headers = hasHeaders ? firstRow : firstRow.map((_, i) => `Col ${i + 1}`);
  const dataStartIndex = hasHeaders ? 1 : 0;

  // Parsear filas de datos
  const rows = lines
    .slice(dataStartIndex, dataStartIndex + maxRows)
    .map((line) => line.split(separator).map((c) => c.trim()));

  // Detectar tipos de columnas
  const allDataRows = lines.slice(dataStartIndex).map((line) => line.split(separator).map((c) => c.trim()));
  const columnTypes = headers.map((_, colIndex) => {
    const columnValues = allDataRows.map((row) => row[colIndex]).filter((v) => v !== undefined);
    return detectColumnType(columnValues);
  });

  return { headers, rows, columnTypes, sheetNames: [], hasHeaders };
}

/**
 * Parsea Excel y retorna preview con headers, tipos y nombres de hojas.
 *
 * @param {ArrayBuffer} buffer - Buffer del archivo Excel
 * @param {number} maxRows - Máximo de filas para preview
 * @returns {Object} Preview con headers, filas, tipos y sheetNames
 */
function parseExcelPreview(buffer, maxRows = 5) {
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheetNames = workbook.SheetNames;

  if (sheetNames.length === 0) {
    return { headers: [], rows: [], columnTypes: [], sheetNames: [] };
  }

  const worksheet = workbook.Sheets[sheetNames[0]];
  const rawData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: "" });

  if (rawData.length === 0) {
    return { headers: [], rows: [], columnTypes: [], sheetNames: [] };
  }

  // Detectar headers
  const firstRow = rawData[0];
  const hasHeaders = firstRow.some((cell) => {
    if (cell === "" || cell === null || cell === undefined) return false;
    const str = String(cell).trim();
    const num = Number(str);
    return Number.isNaN(num) || str.match(/^[a-zA-ZáéíóúÁÉÍÓÚñÑ_]/);
  });

  const headers = hasHeaders ? firstRow.map(String) : firstRow.map((_, i) => `Col ${i + 1}`);
  const dataStartIndex = hasHeaders ? 1 : 0;

  // Obtener preview de filas
  const rows = rawData.slice(dataStartIndex, dataStartIndex + maxRows).map((row) =>
    headers.map((_, i) => (row[i] !== undefined ? String(row[i]) : ""))
  );

  // Detectar tipos de columnas usando todas las filas
  const allDataRows = rawData.slice(dataStartIndex);
  const columnTypes = headers.map((_, colIndex) => {
    const columnValues = allDataRows.map((row) => row[colIndex]).filter((v) => v !== "" && v !== undefined && v !== null);
    return detectColumnType(columnValues);
  });

  return { headers, rows, columnTypes, sheetNames, hasHeaders };
}

/**
 * Normaliza una fecha a formato ISO 8601 (YYYY-MM-DD).
 * Soporta múltiples formatos de entrada comunes en CSV argentinos.
 *
 * @param {string} dateStr - Fecha en cualquier formato soportado
 * @returns {string} Fecha en formato YYYY-MM-DD
 */
function normalizeDate(dateStr) {
  if (!dateStr || typeof dateStr !== "string") return "";

  const str = dateStr.trim();

  // Formato ISO: 2020-01-01 o 2020-01
  if (str.match(/^\d{4}-\d{2}(-\d{2})?$/)) {
    return str.length === 7 ? `${str}-01` : str;
  }

  // Formato año-mes corto: 2020-1
  if (str.match(/^\d{4}-\d{1}$/)) {
    return `${str}-01`;
  }

  // Formato mes/año: 01/2020 o 1/2020
  const mesAnioMatch = str.match(/^(\d{1,2})[/-](\d{4})$/);
  if (mesAnioMatch) {
    const [, mes, anio] = mesAnioMatch;
    return `${anio}-${mes.padStart(2, "0")}-01`;
  }

  // Formato mes/año corto: 01/20 o 1/20
  const mesAnioCortoMatch = str.match(/^(\d{1,2})[/-](\d{2})$/);
  if (mesAnioCortoMatch) {
    const [, mes, anio] = mesAnioCortoMatch;
    const anioCompleto = parseInt(anio) >= 50 ? `19${anio}` : `20${anio}`;
    return `${anioCompleto}-${mes.padStart(2, "0")}-01`;
  }

  // Formato dia/mes/año: 15/01/2020 o 15/1/2020
  const fechaCompletaMatch = str.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);
  if (fechaCompletaMatch) {
    const [, dia, mes, anio] = fechaCompletaMatch;
    return `${anio}-${mes.padStart(2, "0")}-${dia.padStart(2, "0")}`;
  }

  // Formato dia/mes/año corto: 15/01/20
  const fechaCortaMatch = str.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$/);
  if (fechaCortaMatch) {
    const [, dia, mes, anio] = fechaCortaMatch;
    const anioCompleto = parseInt(anio) >= 50 ? `19${anio}` : `20${anio}`;
    return `${anioCompleto}-${mes.padStart(2, "0")}-${dia.padStart(2, "0")}`;
  }

  // Formato mes abreviado en inglés + año: Jan-00, Feb-01, Jun-2000
  // Común en datos climáticos e hidrológicos (IMERG, TRMM, etc.)
  const mesAbbrMatch = str.match(/^([A-Za-z]{3})-(\d{2,4})$/);
  if (mesAbbrMatch) {
    const mesesAbbr = {
      jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6,
      jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12
    };
    const [, mesAbbr, anio] = mesAbbrMatch;
    const mesNum = mesesAbbr[mesAbbr.toLowerCase()];
    if (mesNum) {
      // Determinar año completo
      let anioCompleto;
      if (anio.length === 4) {
        anioCompleto = anio;
      } else {
        const anioNum = parseInt(anio);
        // Asumir 2000+ para años 00-49, 1900+ para 50-99
        anioCompleto = anioNum >= 50 ? `19${anio}` : `20${anio}`;
      }
      return `${anioCompleto}-${String(mesNum).padStart(2, "0")}-01`;
    }
  }

  // Si no coincide con ningún formato conocido, devolver como está
  // y dejar que el backend intente parsear
  return str;
}

/**
 * Extrae datos completos de CSV con fechas normalizadas.
 *
 * @param {string} text - Contenido CSV
 * @param {string} dateColumn - Nombre de columna de fechas
 * @param {string} valueColumn - Nombre de columna de valores
 * @param {Object} previewInfo - Info del preview (headers, hasHeaders)
 * @returns {Object} Objeto con fechas normalizadas y valores
 */
function extractCsvData(text, dateColumn, valueColumn, previewInfo) {
  const lines = text
    .trim()
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "");

  const separator = lines[0].includes(";") ? ";" : ",";
  const dataStartIndex = previewInfo.hasHeaders ? 1 : 0;

  const dateColIndex = previewInfo.headers.indexOf(dateColumn);
  const valueColIndex = previewInfo.headers.indexOf(valueColumn);

  const dataRows = lines.slice(dataStartIndex);
  const dates = [];
  const values = [];

  for (const line of dataRows) {
    const cells = line.split(separator).map((c) => c.trim());
    const dateVal = cells[dateColIndex];
    const valueVal = cells[valueColIndex];

    if (dateVal && valueVal !== undefined && valueVal !== "") {
      const numValue = Number(valueVal);
      if (!Number.isNaN(numValue)) {
        // Normalizar la fecha antes de guardar
        const normalizedDate = normalizeDate(dateVal);
        if (normalizedDate) {
          dates.push(normalizedDate);
          values.push(numValue);
        }
      }
    }
  }

  return { dates, values };
}

/**
 * Extrae datos completos de Excel con fechas normalizadas.
 *
 * @param {ArrayBuffer} buffer - Buffer Excel
 * @param {string} dateColumn - Nombre de columna de fechas
 * @param {string} valueColumn - Nombre de columna de valores
 * @param {Object} previewInfo - Info del preview
 * @param {number} sheetIndex - Índice de la hoja a usar
 * @returns {Object} Objeto con fechas normalizadas y valores
 */
function extractExcelData(buffer, dateColumn, valueColumn, previewInfo, sheetIndex = 0) {
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheetName = previewInfo.sheetNames[sheetIndex] || workbook.SheetNames[sheetIndex];
  const worksheet = workbook.Sheets[sheetName];
  const rawData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: "" });

  const dataStartIndex = previewInfo.hasHeaders ? 1 : 0;
  const dateColIndex = previewInfo.headers.indexOf(dateColumn);
  const valueColIndex = previewInfo.headers.indexOf(valueColumn);

  const dates = [];
  const values = [];

  for (let i = dataStartIndex; i < rawData.length; i++) {
    const row = rawData[i];
    const dateVal = row[dateColIndex];
    const valueVal = row[valueColIndex];

    if (dateVal !== "" && valueVal !== "" && valueVal !== undefined) {
      const numValue = Number(valueVal);
      if (!Number.isNaN(numValue)) {
        // Para Excel, si ya es un objeto Date, convertir a ISO
        // Si es string, normalizar
        let normalizedDate;
        if (dateVal instanceof Date) {
          normalizedDate = dateVal.toISOString().split("T")[0];
        } else {
          normalizedDate = normalizeDate(String(dateVal));
        }
        if (normalizedDate) {
          dates.push(normalizedDate);
          values.push(numValue);
        }
      }
    }
  }

  return { dates, values };
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
  // NOTIFICACIONES TOAST (Epic 4)
  // ---------------------------------------------------------------------------

  const { toasts, removeToast, showSuccess, showError, showWarning, showInfo } = useToast();

  // ---------------------------------------------------------------------------
  // ESTADO GLOBAL - DATOS COMPARTIDOS
  // ---------------------------------------------------------------------------

  const [series, setSeries] = useState([0, 0, 0]);
  const [seriesId, setSeriesId] = useState("serie_local");
  const [fileError, setFileError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  // ---------------------------------------------------------------------------
  // ESTADO - MÓDULO DE VALIDACIÓN (SAMHIA integrado en sección 3)
  // ---------------------------------------------------------------------------

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
  const [outlierPlots, setOutlierPlots] = useState(null);
  const [outlierPlotsLoading, setOutlierPlotsLoading] = useState(false);
  const [outlierPlotsError, setOutlierPlotsError] = useState("");

  // ---------------------------------------------------------------------------
  // ESTADO - IMPORTACIÓN CSV/EXCEL CON SELECCIÓN DE COLUMNAS
  // ---------------------------------------------------------------------------

  const [importStep, setImportStep] = useState("upload"); // 'upload' | 'preview' | 'select' | 'process' | 'done'
  const [filePreview, setFilePreview] = useState(null); // { headers, rows, columnTypes, sheetNames, hasHeaders }
  const [selectedDateColumn, setSelectedDateColumn] = useState("");
  const [selectedValueColumn, setSelectedValueColumn] = useState("");
  const [selectedSheet, setSelectedSheet] = useState(0);
  const [rawFileContent, setRawFileContent] = useState(null); // { type: 'csv'|'excel', content: text|buffer }

  // ---------------------------------------------------------------------------
  // ESTADO - PROCESAMIENTO TEMPORAL EXPANDIDO
  // ---------------------------------------------------------------------------

  const [temporalProcessingEnabled, setTemporalProcessingEnabled] = useState(false);
  const [temporalTargetFrequency, setTemporalTargetFrequency] = useState("yearly");
  const [temporalAggregationMethod, setTemporalAggregationMethod] = useState("sum");
  const [temporalHydrologicalYear, setTemporalHydrologicalYear] = useState(false);
  const [temporalHydrologicalStartMonth, setTemporalHydrologicalStartMonth] = useState(10);
  const [temporalDailyStartHour, setTemporalDailyStartHour] = useState(0);  // Período diario personalizado
  const [temporalProcessingLoading, setTemporalProcessingLoading] = useState(false);
  const [temporalProcessingError, setTemporalProcessingError] = useState("");
  const [temporalProcessingResult, setTemporalProcessingResult] = useState(null);
  const [originalSeries, setOriginalSeries] = useState(null); // Guardar serie original antes de procesar
  const [availableTargetFrequencies, setAvailableTargetFrequencies] = useState([]);

  // ---------------------------------------------------------------------------
  // ESTADO - CONFIGURACIÓN DE FRECUENCIA TEMPORAL (parámetro 't')
  // ---------------------------------------------------------------------------

  const [timeFrequency, setTimeFrequency] = useState("auto"); // 'auto', 'yearly', 'monthly', 'daily', 'hourly', 'custom'
  const [customTimeInterval, setCustomTimeInterval] = useState(1); // Para frecuencia personalizada
  const [customTimeUnit, setCustomTimeUnit] = useState("minutes"); // 'minutes', 'hours', 'days'

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
      const msg = "La serie debe tener al menos 3 valores numéricos.";
      setFitError(msg);
      showWarning(msg, { title: "Datos insuficientes" });
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
        // Error del middleware de errores matemáticos (Epic 4)
        const errorMsg = json.message || json.detail || "Error al ajustar distribuciones";
        const suggestion = json.suggestion || "";
        setFitError(errorMsg);
        showError(`${errorMsg}${suggestion ? `. ${suggestion}` : ""}`, {
          title: json.error_type === "MATH_ERROR" ? "Error matemático" : "Error",
        });
      } else {
        setFitResults(json);
        if (json.recommended_distribution) {
          setSelectedDistribution(json.recommended_distribution);
        }
        showSuccess(
          `Ajuste completado. Mejor distribución: ${json.recommended_distribution?.distribution_name || "N/A"}`,
          { title: "Análisis de frecuencia" }
        );
      }
    } catch (error) {
      const msg = `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`;
      setFitError(msg);
      showError(msg, { title: "Error de conexión" });
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
      const msg = "Selecciona una distribución primero.";
      setDesignError(msg);
      showWarning(msg, { title: "Distribución requerida" });
      return;
    }

    if (returnPeriod <= 0) {
      const msg = "El período de retorno debe ser positivo.";
      setDesignError(msg);
      showWarning(msg, { title: "Período inválido" });
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
        const errorMsg = json.message || json.detail || "Error al calcular evento de diseño";
        const suggestion = json.suggestion || "";
        setDesignError(errorMsg);
        showError(`${errorMsg}${suggestion ? `. ${suggestion}` : ""}`, {
          title: "Error en cálculo",
        });
      } else {
        setDesignEvent(json);
        showSuccess(
          `Evento de diseño T=${json.return_period}: ${json.design_value?.toFixed(2) || "N/A"}`,
          { title: "Cálculo completado" }
        );
      }
    } catch (error) {
      const msg = `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`;
      setDesignError(msg);
      showError(msg, { title: "Error de conexión" });
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
      const msg = "La serie debe tener al menos 12 datos válidos para el análisis SAMHIA.";
      setAnalysisError(msg);
      showWarning(msg, { title: "Datos insuficientes" });
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
        const errorMsg = json.message || json.detail || "Error al ejecutar análisis SAMHIA";
        const suggestion = json.suggestion || "";
        setAnalysisError(errorMsg);
        showError(`${errorMsg}${suggestion ? `. ${suggestion}` : ""}`, {
          title: "Error en análisis",
        });
      } else {
        setAnalysisResults(json);
        setSamhiaData(validData);
        showSuccess("Análisis SAMHIA completado exitosamente", {
          title: "Análisis completado",
        });
      }
    } catch (error) {
      const msg = `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`;
      setAnalysisError(msg);
      showError(msg, { title: "Error de conexión" });
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
      const msg = "La serie debe tener al menos 12 datos válidos.";
      setPdfError(msg);
      showWarning(msg, { title: "Datos insuficientes" });
      return;
    }

    setIsGeneratingPdf(true);
    showInfo("Generando reporte PDF...", { title: "Procesando", duration: 3000 });

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
        const errorMsg = json.message || json.detail || "Error al generar PDF";
        setPdfError(errorMsg);
        showError(errorMsg, { title: "Error al generar PDF" });
      } else {
        setPdfPath(json.pdf_path);
        showSuccess("Reporte PDF generado exitosamente", {
          title: "PDF listo",
          duration: 8000,
        });
      }
    } catch (error) {
      const msg = `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`;
      setPdfError(msg);
      showError(msg, { title: "Error de conexión" });
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  /**
   * Carga los gráficos de análisis de outliers.
   */
  const handleLoadOutlierPlots = async () => {
    setOutlierPlotsLoading(true);
    setOutlierPlotsError("");

    try {
      const validData = series.filter((v) => Number.isFinite(v));
      const analysisDates = dates.length === validData.length
        ? dates
        : validData.map((_, i) => `2020-${String((i % 12) + 1).padStart(2, '0')}-15`);

      const response = await fetch(`${API_BASE}/reports/plots/outliers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data: validData,
          dates: analysisDates,
          series_name: seriesName,
          reservoir_name: reservoirName,
          alpha: alpha,
          distribution: "lognormal",
        }),
      });

      const json = await response.json();
      if (!response.ok) {
        setOutlierPlotsError(json.detail || "Error al cargar gráficos de outliers");
      } else {
        setOutlierPlots(json);
      }
    } catch (error) {
      setOutlierPlotsError("No se pudieron cargar los gráficos de outliers");
    } finally {
      setOutlierPlotsLoading(false);
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
        showError("Error al descargar el PDF", { title: "Descarga fallida" });
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
      showSuccess("PDF descargado correctamente", { title: "Descarga completada" });
    } catch (error) {
      setPdfError("Error al descargar el PDF");
      showError("Error al descargar el PDF", { title: "Descarga fallida" });
    }
  };

  /**
   * Procesa archivo CSV o Excel cargado - Paso 1: Preview.
   *
   * Detecta formato por extensión, carga preview y muestra
   * la interfaz de selección de columnas.
   *
   * @param {File} file - Archivo seleccionado vía input o drag-drop
   */
  const handleFile = async (file) => {
    setFileError("");
    setAnalysisError("");
    setAnalysisResults(null);

    if (!file) return;
    const accepted = ["text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"];
    if (!file.name.endsWith(".csv") && !file.name.endsWith(".xlsx") && !file.name.endsWith(".xls") && !accepted.includes(file.type)) {
      const msg = "Solo se permiten archivos CSV o XLSX.";
      setFileError(msg);
      showWarning(msg, { title: "Formato inválido" });
      return;
    }

    showInfo(`Cargando archivo: ${file.name}...`, { title: "Procesando", duration: 2000 });

    try {
      if (file.name.endsWith(".csv")) {
        const text = await file.text();
        const preview = parseCsvPreview(text, 5);

        if (preview.headers.length === 0) {
          const msg = "El archivo está vacío o no tiene formato válido.";
          setFileError(msg);
          showError(msg, { title: "Archivo inválido" });
          return;
        }

        // Guardar contenido raw y preview
        setRawFileContent({ type: "csv", content: text });
        setFilePreview(preview);
        showSuccess(`Archivo CSV cargado: ${preview.headers.length} columnas detectadas`, {
          title: "Vista previa lista",
        });

        // Sugerir columnas por defecto
        const dateCol = preview.headers.find((h, i) => preview.columnTypes[i] === "date") || preview.headers[0];
        const valueCol = preview.headers.find((h, i) => preview.columnTypes[i] === "numeric") || preview.headers[1] || preview.headers[0];
        setSelectedDateColumn(dateCol);
        setSelectedValueColumn(valueCol);

        setSeriesId(file.name);
        setImportStep("preview");
        return;
      }

      if (file.name.endsWith(".xlsx") || file.name.endsWith(".xls")) {
        const buffer = await file.arrayBuffer();
        const preview = parseExcelPreview(buffer, 5);

        if (preview.headers.length === 0) {
          setFileError("El archivo está vacío o no tiene formato válido.");
          return;
        }

        // Guardar contenido raw y preview
        setRawFileContent({ type: "excel", content: buffer });
        setFilePreview(preview);
        setSelectedSheet(0);

        // Sugerir columnas por defecto
        const dateCol = preview.headers.find((h, i) => preview.columnTypes[i] === "date") || preview.headers[0];
        const valueCol = preview.headers.find((h, i) => preview.columnTypes[i] === "numeric") || preview.headers[1] || preview.headers[0];
        setSelectedDateColumn(dateCol);
        setSelectedValueColumn(valueCol);

        setSeriesId(file.name);
        setImportStep("preview");
        return;
      }

      setFileError("Formato de archivo no compatible.");
    } catch (error) {
      setFileError(`Error al procesar el archivo: ${error.message}`);
    }
  };

  /**
   * Cancela la importación y vuelve al estado inicial.
   */
  const handleCancelImport = () => {
    setImportStep("upload");
    setFilePreview(null);
    setRawFileContent(null);
    setSelectedDateColumn("");
    setSelectedValueColumn("");
    setSelectedSheet(0);
  };

  /**
   * Importa los datos con las columnas seleccionadas.
   * Va al paso de procesamiento temporal antes de "done".
   */
  const handleImport = () => {
    if (!rawFileContent || !filePreview) return;

    try {
      let result;

      if (rawFileContent.type === "csv") {
        result = extractCsvData(rawFileContent.content, selectedDateColumn, selectedValueColumn, filePreview);
      } else {
        result = extractExcelData(rawFileContent.content, selectedDateColumn, selectedValueColumn, filePreview, selectedSheet);
      }

      if (result.values.length === 0) {
        setFileError("No se encontraron valores numéricos válidos en las columnas seleccionadas.");
        return;
      }

      // Guardar datos originales
      setOriginalSeries({ values: result.values, dates: result.dates });
      setSeries(result.values);
      setDates(result.dates);

      // Resetear estado de procesamiento temporal
      setTemporalProcessingEnabled(false);
      setTemporalProcessingResult(null);
      setTemporalProcessingError("");

      // Ir al paso de procesamiento temporal
      setImportStep("process");
    } catch (error) {
      setFileError(`Error al importar datos: ${error.message}`);
    }
  };

  /**
   * Detecta frecuencia original y obtiene targets disponibles para agregación.
   */
  const detectAvailableTargets = async () => {
    if (!dates.length || !series.length) return;

    try {
      const response = await fetch(`${API_BASE}/temporal/detect-frequency`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dates: dates,
          values: series,
        }),
      });

      if (response.ok) {
        const json = await response.json();
        // Obtener targets disponibles
        const targetsResponse = await fetch(`${API_BASE}/temporal/available-targets`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            dates: dates,
            values: series,
          }),
        });
        if (targetsResponse.ok) {
          const targetsJson = await targetsResponse.json();
          setAvailableTargetFrequencies(targetsJson.available_targets || []);
        }
      }
    } catch (error) {
      console.error("Error detectando frecuencia:", error);
    }
  };

  // Detectar frecuencia cuando cambian los datos
  useMemo(() => {
    if (dates.length > 0 && series.length > 0) {
      detectAvailableTargets();
    }
  }, [dates, series]);

  /**
   * Ejecuta procesamiento temporal (agregación ascendente flexible).
   */
  const handleTemporalProcessing = async () => {
    setTemporalProcessingError("");
    setTemporalProcessingResult(null);

    if (!dates.length || !series.length) {
      setTemporalProcessingError("No hay datos para procesar.");
      return;
    }

    setTemporalProcessingLoading(true);
    try {
      const response = await fetch(`${API_BASE}/temporal/aggregate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dates: dates,
          values: series,
          target_frequency: temporalTargetFrequency,
          aggregation_method: temporalAggregationMethod,
          hydrological_year: temporalHydrologicalYear,
          hydrological_start_month: temporalHydrologicalStartMonth,
          daily_start_hour: temporalDailyStartHour,
        }),
      });

      const json = await response.json();
      if (!response.ok) {
        setTemporalProcessingError(json.detail || "Error en procesamiento temporal");
      } else {
        setTemporalProcessingResult(json);
        // Actualizar serie con datos procesados
        setSeries(json.values);
        // Actualizar fechas según el tipo de índice resultante
        if (temporalTargetFrequency === "yearly") {
          setDates(json.index.map(y => `${y}-06-15`)); // Fecha representativa del año
        } else if (temporalTargetFrequency === "monthly") {
          setDates(json.index.map(m => `${m}-15`)); // Fecha representativa del mes
        } else {
          setDates(json.index);
        }
      }
    } catch (error) {
      setTemporalProcessingError(
        `No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en ${API_BASE}`
      );
    } finally {
      setTemporalProcessingLoading(false);
    }
  };

  /**
   * Restaura la serie original antes del procesamiento.
   */
  const handleRestoreOriginal = () => {
    if (originalSeries) {
      setSeries(originalSeries.values);
      setDates(originalSeries.dates);
      setTemporalProcessingResult(null);
      setTemporalProcessingEnabled(false);
    }
  };

  /**
   * Finaliza el flujo de importación y va a "done".
   */
  const handleFinishImport = () => {
    setImportStep("done");
    setFilePreview(null);
    setRawFileContent(null);
    setOriginalSeries(null);
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
        <section className="glass-panel">
          <h2>1. Ingesta de datos</h2>

          {/* PASO 1: DROPZONE (upload) */}
          {(importStep === "upload" || importStep === "done") && (
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
          )}

          {/* PASO 2: PREVIEW Y SELECCIÓN DE COLUMNAS */}
          {importStep === "preview" && filePreview && (
            <div className="glass-panel compact">
              <h3>📄 Preview: {seriesId}</h3>

              {/* Selector de hoja para Excel */}
              {filePreview.sheetNames.length > 0 && (
                <div style={{ marginBottom: "12px" }}>
                  <label>Hoja: </label>
                  <select
                    value={selectedSheet}
                    onChange={(e) => setSelectedSheet(Number(e.target.value))}
                  >
                    {filePreview.sheetNames.map((name, i) => (
                      <option key={i} value={i}>{name}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Tabla de preview con iconos de tipo */}
              <div className="table-wrapper" style={{ maxHeight: "200px", overflow: "auto" }}>
                <table style={{ fontSize: "0.85em" }}>
                  <thead>
                    <tr>
                      {filePreview.headers.map((header, i) => (
                        <th key={i} style={{ textAlign: "center" }}>
                          {header}
                          <span style={{ marginLeft: "4px", fontSize: "0.9em" }}>
                            {filePreview.columnTypes[i] === "date" && "📅"}
                            {filePreview.columnTypes[i] === "numeric" && "🔢"}
                            {filePreview.columnTypes[i] === "text" && "📝"}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filePreview.rows.map((row, rowIdx) => (
                      <tr key={rowIdx}>
                        {row.map((cell, cellIdx) => (
                          <td key={cellIdx} style={{ padding: "4px 8px" }}>{cell}</td>
                        ))}
                      </tr>
                    ))}
                    <tr>
                      <td
                        colSpan={filePreview.headers.length}
                        style={{ textAlign: "center", color: "#cbd5e1", fontStyle: "italic" }}
                      >
                        ... (más filas)
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Leyenda de tipos */}
              <div style={{ fontSize: "0.8em", color: "#cbd5e1", marginTop: "8px" }}>
                📅 Fecha | 🔢 Numérica | 📝 Texto
              </div>

              {/* Selectores de columnas */}
              <div style={{ marginTop: "16px", display: "grid", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", marginBottom: "4px", fontWeight: 500 }}>
                    Columna de fechas:
                  </label>
                  <select
                    value={selectedDateColumn}
                    onChange={(e) => setSelectedDateColumn(e.target.value)}
                    style={{ width: "100%", padding: "6px" }}
                  >
                    {filePreview.headers.map((header, i) => (
                      <option key={i} value={header}>
                        {filePreview.columnTypes[i] === "date" && "📅 "}
                        {filePreview.columnTypes[i] === "numeric" && "🔢 "}
                        {filePreview.columnTypes[i] === "text" && "📝 "}
                        {header}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", marginBottom: "4px", fontWeight: 500 }}>
                    Columna de valores:
                  </label>
                  <select
                    value={selectedValueColumn}
                    onChange={(e) => setSelectedValueColumn(e.target.value)}
                    style={{ width: "100%", padding: "6px" }}
                  >
                    {filePreview.headers.map((header, i) => (
                      <option key={i} value={header}>
                        {filePreview.columnTypes[i] === "date" && "📅 "}
                        {filePreview.columnTypes[i] === "numeric" && "🔢 "}
                        {filePreview.columnTypes[i] === "text" && "📝 "}
                        {header}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Preview de importación */}
              {selectedDateColumn && selectedValueColumn && (
                <div style={{ marginTop: "16px", padding: "12px", background: "#0f172a", borderRadius: "6px" }}>
                  <strong style={{ fontSize: "0.9em" }}>Preview de importación:</strong>
                  <div style={{ fontSize: "0.8em", color: "#cbd5e1", marginTop: "4px" }}>
                    Fecha: <strong style={{ color: "#60a5fa" }}>{selectedDateColumn}</strong> | Valor: <strong style={{ color: "#60a5fa" }}>{selectedValueColumn}</strong>
                  </div>
                </div>
              )}

              {/* Botones de acción */}
              <div className="button-group" style={{ marginTop: "16px" }}>
                <button type="button" className="aqua-button secondary" onClick={handleCancelImport}>
                  ← Volver
                </button>
                <button
                  type="button"
                  className="aqua-button"
                  onClick={handleImport}
                  disabled={!selectedDateColumn || !selectedValueColumn}
                >
                  Importar datos
                </button>
              </div>
            </div>
          )}

          {/* PASO 3: PROCESAMIENTO TEMPORAL EXPANDIDO */}
          {importStep === "process" && (
            <div className="glass-panel compact">
              <h3>⚙️ Procesamiento Temporal</h3>

              {/* Info de datos cargados */}
              <div className="temporal-controls" style={{ marginBottom: "16px" }}>
                <strong>📊 Datos cargados</strong>
                <div style={{ fontSize: "0.9em", color: "#e2e8f0", marginTop: "4px" }}>
                  {dates.length} observaciones desde {dates[0]} hasta {dates[dates.length - 1]}
                </div>
                {availableTargetFrequencies.length > 0 && (
                  <div style={{ fontSize: "0.8em", color: "#60a5fa", marginTop: "8px" }}>
                    Frecuencias disponibles para agregación: {availableTargetFrequencies.join(", ")}
                  </div>
                )}
              </div>

              {/* CONFIGURACIÓN DE FRECUENCIA TEMPORAL (parámetro 't') */}
              <div className="temporal-controls" style={{ marginBottom: "16px" }}>
                <h4 style={{ marginBottom: "12px", color: "#7dd3fc" }}>⏱️ Configuración de Frecuencia Temporal</h4>
                <p style={{ fontSize: "0.85em", color: "#e2e8f0", marginBottom: "12px" }}>
                  Define el intervalo temporal de tu serie para los análisis estadísticos.
                </p>

                <div className="temporal-controls-row">
                  <div className="temporal-control-group">
                    <label>Frecuencia de la serie:</label>
                    <select
                      value={timeFrequency}
                      onChange={(e) => setTimeFrequency(e.target.value)}
                    >
                      <option value="auto">🔍 Auto-detectar</option>
                      <option value="yearly">📅 Anual (1 año)</option>
                      <option value="monthly">📆 Mensual (1 mes)</option>
                      <option value="daily">📋 Diaria (24 horas)</option>
                      <option value="hourly">🕐 Horaria (1 hora)</option>
                      <option value="custom">⚙️ Personalizada...</option>
                    </select>
                  </div>

                  {timeFrequency === "custom" && (
                    <>
                      <div className="temporal-control-group" style={{ flex: "0 0 100px" }}>
                        <label>Intervalo:</label>
                        <input
                          type="number"
                          min="1"
                          value={customTimeInterval}
                          onChange={(e) => setCustomTimeInterval(Number(e.target.value))}
                        />
                      </div>
                      <div className="temporal-control-group" style={{ flex: "0 0 150px" }}>
                        <label>Unidad:</label>
                        <select
                          value={customTimeUnit}
                          onChange={(e) => setCustomTimeUnit(e.target.value)}
                        >
                          <option value="minutes">Minutos</option>
                          <option value="hours">Horas</option>
                          <option value="days">Días</option>
                        </select>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Toggle para activar agregación */}
              <div className="temporal-toggle" style={{ marginBottom: "16px" }}>
                <input
                  type="checkbox"
                  checked={temporalProcessingEnabled}
                  onChange={(e) => setTemporalProcessingEnabled(e.target.checked)}
                />
                <span>Agregar datos a mayor resolución temporal</span>
              </div>
              <p style={{ fontSize: "0.8em", color: "#cbd5e1", marginTop: "-10px", marginBottom: "16px", marginLeft: "54px" }}>
                Permite agregar desde una frecuencia menor a una mayor (ej: minutos → horas → días).
              </p>

              {/* Opciones de agregación ascendente */}
              {temporalProcessingEnabled && (
                <div className="temporal-controls">
                  <h4 style={{ marginBottom: "12px" }}>Opciones de Agregación Ascendente</h4>

                  {/* Frecuencia objetivo */}
                  <div className="temporal-controls-row">
                    <div className="temporal-control-group">
                      <label>Frecuencia objetivo:</label>
                      <select
                        value={temporalTargetFrequency}
                        onChange={(e) => setTemporalTargetFrequency(e.target.value)}
                      >
                        {availableTargetFrequencies.includes("yearly") && (
                          <option value="yearly">📅 Anual</option>
                        )}
                        {availableTargetFrequencies.includes("monthly") && (
                          <option value="monthly">📆 Mensual</option>
                        )}
                        {availableTargetFrequencies.includes("daily") && (
                          <option value="daily">📋 Diaria</option>
                        )}
                        {availableTargetFrequencies.includes("hourly") && (
                          <option value="hourly">🕐 Horaria</option>
                        )}
                        {!availableTargetFrequencies.length && (
                          <option value="yearly">📅 Anual (default)</option>
                        )}
                      </select>
                    </div>

                    <div className="temporal-control-group">
                      <label>Método de agregación:</label>
                      <select
                        value={temporalAggregationMethod}
                        onChange={(e) => setTemporalAggregationMethod(e.target.value)}
                      >
                        <option value="sum">∑ Suma (precipitación/volumen)</option>
                        <option value="mean">Ø Promedio (temperatura/nivel)</option>
                        <option value="max">↑ Máximo (caudal pico)</option>
                        <option value="min">↓ Mínimo</option>
                      </select>
                    </div>
                  </div>

                  {/* Año hidrológico - siempre visible, aplicable a series agregadas y no agregadas */}
                  <div className="temporal-controls-row" style={{ marginTop: "12px" }}>
                    <div className="temporal-control-group">
                      <label className="temporal-toggle" style={{ padding: 0 }}>
                        <input
                          type="checkbox"
                          checked={temporalHydrologicalYear}
                          onChange={(e) => setTemporalHydrologicalYear(e.target.checked)}
                        />
                        <span>Usar año hidrológico</span>
                      </label>
                    </div>

                    {temporalHydrologicalYear && (
                      <div className="temporal-control-group">
                        <label>Mes de inicio:</label>
                        <select
                          value={temporalHydrologicalStartMonth}
                          onChange={(e) => setTemporalHydrologicalStartMonth(Number(e.target.value))}
                        >
                          <option value={1}>Enero</option>
                          <option value={2}>Febrero</option>
                          <option value={3}>Marzo</option>
                          <option value={4}>Abril</option>
                          <option value={5}>Mayo</option>
                          <option value={6}>Junio</option>
                          <option value={7}>Julio</option>
                          <option value={8}>Agosto</option>
                          <option value={9}>Septiembre</option>
                          <option value={10}>Octubre (default)</option>
                          <option value={11}>Noviembre</option>
                          <option value={12}>Diciembre</option>
                        </select>
                      </div>
                    )}
                  </div>

                  {/* Período diario personalizado (solo para agregación diaria desde subdiaria) */}
                  {(temporalTargetFrequency === "daily" || temporalTargetFrequency === "yearly") &&
                   availableTargetFrequencies.some(f => ["hourly", "minutes", "5min"].includes(f)) && (
                    <div className="temporal-controls-row" style={{ marginTop: "12px" }}>
                      <div className="temporal-control-group">
                        <label>Período diario personalizado:</label>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <input
                            type="checkbox"
                            checked={temporalDailyStartHour !== 0}
                            onChange={(e) => setTemporalDailyStartHour(e.target.checked ? 9 : 0)}
                            style={{ width: "auto" }}
                          />
                          <span style={{ fontSize: "0.85em", color: "#e2e8f0" }}>
                            Usar período 24hs personalizado (ej: 09:00 a 09:00)
                          </span>
                        </div>
                      </div>

                      {temporalDailyStartHour !== 0 && (
                        <div className="temporal-control-group" style={{ flex: "0 0 120px" }}>
                          <label>Hora de inicio:</label>
                          <input
                            type="number"
                            min="0"
                            max="23"
                            value={temporalDailyStartHour}
                            onChange={(e) => setTemporalDailyStartHour(Number(e.target.value))}
                          />
                        </div>
                      )}
                    </div>
                  )}

                  {/* Botón procesar */}
                  <button
                    type="button"
                    className="btn-load-plots"
                    onClick={handleTemporalProcessing}
                    disabled={temporalProcessingLoading}
                    style={{ width: "100%", marginTop: "16px" }}
                  >
                    {temporalProcessingLoading ? "⏳ Procesando..." : temporalProcessingResult ? "🔄 Reprocesar" : "▶️ Procesar datos"}
                  </button>
                </div>
              )}

              {/* Error de procesamiento */}
              {temporalProcessingError && (
                <div className="status-banner error" style={{ marginBottom: "16px", marginTop: "16px" }}>
                  {temporalProcessingError}
                </div>
              )}

              {/* Resultado del procesamiento */}
              {temporalProcessingResult && (
                <div style={{ marginBottom: "16px", padding: "12px", background: "#064e3b", borderRadius: "6px", border: "1px solid #10b981" }}>
                  <h4 style={{ marginBottom: "8px", color: "#34d399" }}>✓ Procesamiento completado</h4>
                  <div style={{ fontSize: "0.85em" }}>
                    <div><strong>Frecuencia original:</strong> {temporalProcessingResult.original_frequency}</div>
                    <div><strong>Frecuencia objetivo:</strong> {temporalProcessingResult.target_frequency}</div>
                    <div><strong>Resultado:</strong> {temporalProcessingResult.n_original} → {temporalProcessingResult.n_result} observaciones</div>
                    <div><strong>Método:</strong> {temporalProcessingResult.aggregation_method}</div>
                    {temporalProcessingResult.daily_start_hour > 0 && (
                      <div><strong>Período diario:</strong> {temporalProcessingResult.daily_start_hour}:00 a {temporalProcessingResult.daily_start_hour}:00</div>
                    )}
                    {temporalProcessingResult.aggregation_bypass && (
                      <div style={{ color: "#fbbf24" }}>⚠ Serie ya estaba en la frecuencia solicitada (sin cambios)</div>
                    )}
                  </div>

                  {/* Botón restaurar */}
                  <button
                    type="button"
                    className="aqua-button secondary"
                    onClick={handleRestoreOriginal}
                    style={{ marginTop: "12px", fontSize: "0.85em" }}
                  >
                    ↺ Restaurar serie original
                  </button>
                </div>
              )}

              {/* Botones de acción final */}
              <div className="button-group" style={{ marginTop: "16px" }}>
                <button
                  type="button"
                  className="aqua-button secondary"
                  onClick={() => setImportStep("preview")}
                >
                  ← Volver
                </button>
                <button
                  type="button"
                  className="aqua-button"
                  onClick={handleFinishImport}
                >
                  Continuar al análisis →
                </button>
              </div>
            </div>
          )}

          {fileError ? <div className="status-banner error" style={{ marginTop: "12px" }}>{fileError}</div> : null}

          {/* Tabla de datos (siempre visible cuando hay datos) */}
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  {dates.length > 0 && <th>Fecha</th>}
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
                      {dates.length > 0 && <td style={{ fontSize: "0.85em", color: "#94a3b8" }}>{dates[index] || "-"}</td>}
                      <td>
                        <input
                          type="number"
                          value={displayValue(value)}
                          onChange={(event) => updateByIndex(index, Number(event.target.value))}
                          className={invalid ? "cell-error" : ""}
                        />
                      </td>
                      <td>
                        <button type="button" className="aqua-button secondary" onClick={() => removeRow(index)}>
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
            <button type="button" className="aqua-button secondary" onClick={addRow}>
              Agregar fila
            </button>
          </div>
          <small>
            Las celdas con valores cero o negativos se resaltan y se consideran advertencias en el análisis.
          </small>
        </section>

        <section className="glass-panel">
          <h2>2. Resumen de la serie</h2>
          <p>
            Identificador: <strong>{seriesId || "serie_local"}</strong>
          </p>
          <p>
            N de datos: <strong>{series.length}</strong>
          </p>
          {warnings.length > 0 ? (
            <div className="status-banner warning">
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

          <div className="glass-panel compact" style={{ marginTop: "18px" }}>
            <h3>Gráficos rápidos</h3>
            <WaterChartBox title="Dispersión temporal">
              {series.length >= 2 ? (
                <ScatterPlot values={series} />
              ) : (
                <p>Agrega más datos para ver el gráfico.</p>
              )}
            </WaterChartBox>
            <WaterChartBox title="Correlograma preliminar" style={{ marginTop: "18px" }}>
              {series.length >= 4 ? (
                <Correlogram data={autoCorrelation} band={band} />
              ) : (
                <p>Necesitas al menos 4 datos para ver autocorrelación.</p>
              )}
            </WaterChartBox>
          </div>
        </section>
      </div>

      {/* ================================================================
          SECCIÓN 3: ANÁLISIS SAMHIA Y GENERACIÓN DE REPORTES
          ================================================================ */}
      <section className="glass-panel">
        <h2>3. Análisis SAMHIA y Reportes PDF</h2>
        <p style={{ color: "#e2e8f0", marginBottom: "18px" }}>
          Análisis estadístico completo basado en SAMHIA_EST.R con tests detallados y generación de reportes PDF de 10 páginas.
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
                className="aqua-button"
                onClick={handleAnalyzeSamhia}
                disabled={isAnalyzing || series.length < 12}
              >
                {isAnalyzing ? "Analizando..." : "Ejecutar análisis SAMHIA"}
              </button>
            </div>

            {analysisError && <div className="status-banner error" style={{ marginTop: "12px" }}>{analysisError}</div>}

            <small style={{ marginTop: "12px", display: "block", color: "#cbd5e1" }}>
              Se requieren al menos 12 datos válidos para el análisis SAMHIA completo.
            </small>
          </div>

          {/* Panel de generación de PDF */}
          <div>
            <p style={{ marginBottom: "12px" }}>
              Genera un reporte PDF completo de 10 páginas con:
            </p>
            <ul style={{ marginLeft: "20px", marginBottom: "16px", color: "#e2e8f0", fontSize: "0.9rem" }}>
              <li>Gráficos de serie temporal, años calendario e hidrológico</li>
              <li>Análisis de datos atípicos y boxplots mensuales/anuales</li>
              <li>Histograma, Q-Q plot y función de autocorrelación</li>
              <li>Tablas resumen de estadísticas y año hidrológico</li>
              <li>Resultados de tests de independencia, homogeneidad y tendencia</li>
            </ul>

            <div className="button-group">
              <button
                type="button"
                className="aqua-button"
                onClick={handleGeneratePdf}
                disabled={isGeneratingPdf || series.length < 12}
              >
                {isGeneratingPdf ? "Generando PDF..." : "Generar reporte PDF"}
              </button>

              {pdfPath && (
                <button
                  type="button"
                  className="aqua-button secondary"
                  onClick={handleDownloadPdf}
                >
                  Descargar PDF
                </button>
              )}
            </div>

            {pdfError && <div className="status-banner error" style={{ marginTop: "12px" }}>{pdfError}</div>}

            {pdfPath && (
              <div className="status-card" style={{ marginTop: "12px" }}>
                <span className="status-pill accepted">PDF generado exitosamente</span>
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
              <OutliersPanel
                tests={analysisResults.outliers}
              />
            )}
          </div>
        )}
      </section>

      {/* ================================================================
          SECCIÓN 4: ANÁLISIS DE FRECUENCIA
          ================================================================ */}
      <section className="glass-panel">
        <h2>4. Análisis de Frecuencia</h2>
        <p style={{ color: "#e2e8f0", marginBottom: "18px" }}>
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
                className="aqua-button"
                onClick={handleFit}
                disabled={isFitting || selectedDistributions.length === 0}
              >
                {isFitting ? "Ajustando..." : "Ajustar distribuciones"}
              </button>
            </div>

            {fitError && <div className="status-banner error" style={{ marginTop: "12px" }}>{fitError}</div>}
          </div>

          {/* Panel de resultados de ajuste */}
          <div>
            {fitResults ? (
              <>
                <div className="status-card" style={{ marginBottom: "18px" }}>
                  <strong>Distribución recomendada</strong>
                  {fitResults.recommended_distribution ? (
                    <>
                      <span className="status-pill accepted" style={{ marginTop: "8px", display: "inline-flex" }}>
                        {fitResults.recommended_distribution.distribution_name}
                      </span>
                      <p style={{ marginTop: "8px", fontSize: "0.9rem", color: "#e2e8f0" }}>
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
                className="aqua-button"
                onClick={handleDesignEvent}
                disabled={isCalculatingDesign}
              >
                {isCalculatingDesign ? "Calculando..." : "Calcular evento de diseño"}
              </button>
            </div>

            {designError && <div className="status-banner error" style={{ marginTop: "12px" }}>{designError}</div>}

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
          SECCIÓN 5: VISUALIZACIONES Y GRÁFICOS (separada de Outliers)
          ================================================================ */}
      {analysisResults && (
        <section className="glass-panel visualizations-section">
          <h2>5. Visualizaciones y Gráficos</h2>
          <p style={{ color: "#e2e8f0", marginBottom: "18px" }}>
            Gráficos estadísticos generados desde el análisis SAMHIA.
          </p>

          <div className="visualizations-grid">
            {/* Gráficos de Outliers con botón de carga */}
            <div className="water-chart-box" style={{ gridColumn: "1 / -1" }}>
              <div className="chart-title">
                Análisis de Atípicos (Outliers)
                {!outlierPlots && !outlierPlotsLoading && (
                  <button
                    type="button"
                    className="btn-load-plots"
                    onClick={handleLoadOutlierPlots}
                    style={{ marginLeft: "16px", padding: "6px 14px", fontSize: "0.85rem" }}
                  >
                    Generar Gráficos
                  </button>
                )}
              </div>
              <div className="chart-content">
                {outlierPlotsLoading && (
                  <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                    Generando gráficos de outliers...
                  </div>
                )}
                {outlierPlotsError && (
                  <div className="error-banner" style={{ marginBottom: "16px" }}>
                    {outlierPlotsError}
                    <button
                      type="button"
                      onClick={handleLoadOutlierPlots}
                      style={{ marginLeft: "12px", padding: "4px 8px", fontSize: "0.8rem" }}
                    >
                      Reintentar
                    </button>
                  </div>
                )}
                {outlierPlots?.plot_urls && (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(500px, 1fr))", gap: "20px" }}>
                    {/* Control Chart */}
                    {outlierPlots.plot_urls.control_chart && (
                      <div>
                        <h6 style={{ marginBottom: "8px", fontSize: "0.9rem", color: "#334155" }}>
                          Gráfico de Control (Umbrales Kn)
                        </h6>
                        <img
                          src={outlierPlots.plot_urls.control_chart}
                          alt="Control Chart"
                          style={{ width: "100%", borderRadius: "6px", border: "1px solid #e2e8f0" }}
                        />
                      </div>
                    )}
                    {/* Probability Plot */}
                    {outlierPlots.plot_urls.probability_plot && (
                      <div>
                        <h6 style={{ marginBottom: "8px", fontSize: "0.9rem", color: "#334155" }}>
                          Gráfico de Probabilidad
                        </h6>
                        <img
                          src={outlierPlots.plot_urls.probability_plot}
                          alt="Probability Plot"
                          style={{ width: "100%", borderRadius: "6px", border: "1px solid #e2e8f0" }}
                        />
                      </div>
                    )}
                    {/* Q-Q Plot */}
                    {outlierPlots.plot_urls.qq_plot && (
                      <div>
                        <h6 style={{ marginBottom: "8px", fontSize: "0.9rem", color: "#334155" }}>
                          Q-Q Plot
                        </h6>
                        <img
                          src={outlierPlots.plot_urls.qq_plot}
                          alt="Q-Q Plot"
                          style={{ width: "100%", borderRadius: "6px", border: "1px solid #e2e8f0" }}
                        />
                      </div>
                    )}
                    {/* FDP Plot */}
                    {outlierPlots.plot_urls.fdp_plot && (
                      <div>
                        <h6 style={{ marginBottom: "8px", fontSize: "0.9rem", color: "#334155" }}>
                          Función de Densidad de Probabilidad
                        </h6>
                        <img
                          src={outlierPlots.plot_urls.fdp_plot}
                          alt="FDP"
                          style={{ width: "100%", borderRadius: "6px", border: "1px solid #e2e8f0" }}
                        />
                      </div>
                    )}
                  </div>
                )}
                {!outlierPlots && !outlierPlotsLoading && !outlierPlotsError && (
                  <div style={{ textAlign: "center", padding: "30px" }}>
                    <p style={{ color: "#64748b", marginBottom: "12px" }}>
                      Los gráficos de análisis de outliers no se han cargado.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Gráficos rápidos de la serie */}
            <div className="water-chart-box">
              <div className="chart-title">Dispersión Temporal</div>
              <div className="chart-content">
                {series.length >= 2 ? (
                  <ScatterPlot values={series} />
                ) : (
                  <p style={{ color: "#64748b" }}>Agrega más datos para ver el gráfico.</p>
                )}
              </div>
            </div>

            <div className="water-chart-box">
              <div className="chart-title">Correlograma Preliminar</div>
              <div className="chart-content">
                {series.length >= 4 ? (
                  <Correlogram data={autoCorrelation} band={band} />
                ) : (
                  <p style={{ color: "#64748b" }}>Necesitas al menos 4 datos para ver autocorrelación.</p>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Contenedor de notificaciones Toast (Epic 4) */}
      <ToastContainer toasts={toasts} removeToast={removeToast} />

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
            <text x={x} y={height - 12} fill="#cbd5e1" fontSize="12" textAnchor="middle">
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
              className="aqua-button secondary"
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
        <p style={{ color: "#e2e8f0" }}>No hay resultados disponibles.</p>
      </div>
    );
  }

  return (
    <div>
      <h4 style={{ marginBottom: "12px" }}>{title}</h4>
      <p style={{ color: "#e2e8f0", marginBottom: "12px", fontSize: "0.9rem" }}>
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
