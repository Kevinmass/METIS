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
      let anioCompleto;
      if (anio.length === 4) {
        anioCompleto = anio;
      } else {
        const anioNum = parseInt(anio);
        anioCompleto = anioNum >= 50 ? `19${anio}` : `20${anio}`;
      }
      return `${anioCompleto}-${String(mesNum).padStart(2, "0")}-01`;
    }
  }

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
 * Detecta y categoriza: negativos, cero, y valores virtualmente cero.
 *
 * @param {number[]} series - Serie de valores
 * @returns {Array<{code, message, affected_indices}>} Lista de advertencias
 */
function buildWarnings(series) {
  const warnings = [];

  const negativeIndices = series
    .map((value, index) => ({ value, index }))
    .filter((item) => typeof item.value === 'number' && item.value < 0)
    .map((item) => item.index);

  if (negativeIndices.length > 0) {
    warnings.push({
      code: "NEGATIVE_VALUES",
      message: `Se encontraron ${negativeIndices.length} valores negativos. Los valores negativos invalidan ciertos tests estadísticos (Chow, Kn, etc.).`,
      affected_indices: negativeIndices,
      severity: "danger",
    });
  }

  const zeroIndices = series
    .map((value, index) => ({ value, index }))
    .filter((item) => typeof item.value === 'number' && item.value === 0)
    .map((item) => item.index);

  if (zeroIndices.length > 0) {
    warnings.push({
      code: "ZERO_VALUES",
      message: `Se encontraron ${zeroIndices.length} valores iguales a cero.`,
      affected_indices: zeroIndices,
      severity: "warning",
    });
  }

  const virtualZeroIndices = series
    .map((value, index) => ({ value, index }))
    .filter((item) => typeof item.value === 'number' && item.value !== 0 && Math.abs(item.value) < 1e-10)
    .map((item) => item.index);

  if (virtualZeroIndices.length > 0) {
    warnings.push({
      code: "VIRTUALLY_ZERO_VALUES",
      message: `Se encontraron ${virtualZeroIndices.length} valores extremadamente cercanos a cero (virtualmente cero). Estos valores pueden distorsionar los cálculos estadísticos.`,
      affected_indices: virtualZeroIndices,
      severity: "warning",
    });
  }

  return warnings;
}

/**
 * Calcula autocorrelación de la serie para el correlograma.
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
// INFO DE SECCIONES PARA NAVEGACIÓN
// =============================================================================

const sectionInfo = {
  ingesta: { title: 'Ingesta de datos', desc: 'Carga tu serie hidrológica desde un archivo CSV o ingresa los valores manualmente.' },
  resumen: { title: 'Resumen de la serie', desc: 'Estadísticas descriptivas y gráficos exploratorios de la serie cargada.' },
  samhia: { title: 'Análisis SAMHIA', desc: 'Análisis estadístico completo basado en SAMHIA_EST.R con tests detallados y generación de reportes PDF.' },
  frecuencia: { title: 'Análisis de Frecuencia', desc: 'Ajusta distribuciones de probabilidad a tu serie y calcula eventos de diseño.' }
};

// =============================================================================
// COMPONENTE PRINCIPAL APP
// =============================================================================

/**
 * Componente principal de la aplicación METIS.
 *
 * @returns {JSX.Element} Aplicación React completa
 */
export default function App() {
  // ---------------------------------------------------------------------------
  // NAVEGACIÓN
  // ---------------------------------------------------------------------------

  const [activeSection, setActiveSection] = useState("ingesta");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navigate = (sectionId) => {
    setActiveSection(sectionId);
    setSidebarOpen(false);
    if (sectionId === 'resumen') updateResumen();
    if (sectionId === 'samhia') updateSamhiaState();
    if (sectionId === 'frecuencia') updateFrecuenciaState();
  };

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
  const [temporalDailyStartHour, setTemporalDailyStartHour] = useState(0);
  const [temporalProcessingLoading, setTemporalProcessingLoading] = useState(false);
  const [temporalProcessingError, setTemporalProcessingError] = useState("");
  const [temporalProcessingResult, setTemporalProcessingResult] = useState(null);
  const [originalSeries, setOriginalSeries] = useState(null);
  const [availableTargetFrequencies, setAvailableTargetFrequencies] = useState([]);

  // ---------------------------------------------------------------------------
  // ESTADO - CONFIGURACIÓN DE FRECUENCIA TEMPORAL (parámetro 't')
  // ---------------------------------------------------------------------------

  const [timeFrequency, setTimeFrequency] = useState("auto");
  const [customTimeInterval, setCustomTimeInterval] = useState(1);
  const [customTimeUnit, setCustomTimeUnit] = useState("minutes");

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

  /** Actualiza valor en índice específico (ingesta manual) */
  const updateByIndex = (index, rawValue) => {
    // Permitir cadena vacía mientras el usuario escribe
    if (rawValue === "") {
      setSeries((prev) => {
        const next = [...prev];
        next[index] = "";
        return next;
      });
      return;
    }

    const numValue = Number(rawValue);
    if (Number.isNaN(numValue)) return;

    // Bloquear valores negativos en ingesta manual
    if (numValue < 0) {
      showWarning("No se permiten valores negativos en la ingesta manual.", {
        title: "Valor inválido",
      });
      return;
    }

    // Bloquear valores "virtualmente cero" (extremadamente pequeños)
    if (numValue !== 0 && Math.abs(numValue) < 1e-10) {
      showWarning(
        "El valor es extremadamente cercano a cero y no se considera válido para el análisis.",
        { title: "Valor inválido" }
      );
      return;
    }

    setSeries((prev) => {
      const next = [...prev];
      next[index] = numValue;
      return next;
    });
  };

  /** Confirma el valor cuando el input pierde foco (convierte "" a 0) */
  const commitValue = (index) => {
    setSeries((prev) => {
      const next = [...prev];
      if (next[index] === "" || next[index] === null || next[index] === undefined) {
        next[index] = 0;
      }
      return next;
    });
  };

  /** Agrega fila con valor 0 al final */
  const addRow = () => setSeries((prev) => [...prev, 0]);

  /** Elimina fila en índice específico */
  const removeRow = (index) => {
    setSeries((prev) => {
      const next = prev.filter((_, i) => i !== index);
      // Si se elimina la última fila, restaurar estado inicial [0, 0, 0]
      if (next.length === 0) {
        return [0, 0, 0];
      }
      return next;
    });
  };

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
    const loadingStartedAt = Date.now();
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
      const elapsed = Date.now() - loadingStartedAt;
      if (elapsed < 500) {
        await new Promise((resolve) => setTimeout(resolve, 500 - elapsed));
      }
      setIsAnalyzing(false);
    }
  };

  /**
   * Genera reporte PDF SAMHIA.
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
    const loadingStartedAt = Date.now();
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
      const elapsed = Date.now() - loadingStartedAt;
      if (elapsed < 350) {
        await new Promise((resolve) => setTimeout(resolve, 350 - elapsed));
      }
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

        setRawFileContent({ type: "csv", content: text });
        setFilePreview(preview);
        showSuccess(`Archivo CSV cargado: ${preview.headers.length} columnas detectadas`, {
          title: "Vista previa lista",
        });

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

        setRawFileContent({ type: "excel", content: buffer });
        setFilePreview(preview);
        setSelectedSheet(0);

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

      setOriginalSeries({ values: result.values, dates: result.dates });
      setSeries(result.values);
      setDates(result.dates);

      setTemporalProcessingEnabled(false);
      setTemporalProcessingResult(null);
      setTemporalProcessingError("");

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
        setSeries(json.values);
        if (temporalTargetFrequency === "yearly") {
          setDates(json.index.map(y => `${y}-06-15`));
        } else if (temporalTargetFrequency === "monthly") {
          setDates(json.index.map(m => `${m}-15`));
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
  // FUNCIONES DE ACTUALIZACIÓN DE SECCIONES
  // ---------------------------------------------------------------------------

  function getValidData() { return series.filter(v => !isNaN(v) && isFinite(v)); }

  function updateResumen() {
    // This is called on navigation; stats are computed inline in the render
  }

  function updateSamhiaState() {
    const valid = getValidData().filter(v => v > 0);
    // Stats computed inline
  }

  function updateFrecuenciaState() {
    const valid = getValidData();
    // Stats computed inline
  }

  // ---------------------------------------------------------------------------
  // RENDERIZADO
  // ---------------------------------------------------------------------------

  const displayValue = (value) => {
    return Number.isFinite(value) ? value : 0;
  };

  return (
    <>
      {/* Background Effects */}
      <div className="bg-effects" aria-hidden="true">
        <div className="blob blob-1"></div>
        <div className="blob blob-2"></div>
        <div className="blob blob-3"></div>
        <div className="grid-overlay"></div>
      </div>

      {/* Sidebar Overlay (mobile) */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'open' : ''}`}
        id="sidebarOverlay"
        onClick={() => setSidebarOpen(false)}
      ></div>

      <div className="app-shell">
        {/* Sidebar */}
        <aside className="sidebar" role="navigation" aria-label="Navegación principal">
          <div className="sidebar-brand">
            <div style={{display:'flex', alignItems:'center', gap:'10px'}}>
              <div style={{width:'34px', height:'34px', borderRadius:'9px', background:'var(--accent)', display:'flex', alignItems:'center', justifyContent:'center'}}>
                <i className="fas fa-water" style={{color:'#fff', fontSize:'15px'}}></i>
              </div>
              <div>
                <div className="font-display" style={{fontWeight:'700', fontSize:'17px', letterSpacing:'-0.02em', color:'var(--fg)'}}>METIS</div>
                <div style={{fontSize:'10px', color:'var(--fg-muted)', letterSpacing:'0.04em', textTransform:'uppercase'}}>Análisis Hidrológico</div>
              </div>
            </div>
          </div>

          <nav className="sidebar-nav">
            <button
              className={`nav-item ${activeSection === 'ingesta' ? 'active' : ''}`}
              onClick={() => navigate('ingesta')}
            >
              <i className="fas fa-cloud-arrow-up"></i><span>Ingesta de datos</span>
            </button>
            <button
              className={`nav-item ${activeSection === 'resumen' ? 'active' : ''}`}
              onClick={() => navigate('resumen')}
            >
              <i className="fas fa-chart-line"></i><span>Resumen de la serie</span>
            </button>
            <button
              className={`nav-item ${activeSection === 'samhia' ? 'active' : ''}`}
              onClick={() => navigate('samhia')}
            >
              <i className="fas fa-file-pdf"></i><span>Análisis SAMHIA</span>
            </button>
            <button
              className={`nav-item ${activeSection === 'frecuencia' ? 'active' : ''}`}
              onClick={() => navigate('frecuencia')}
            >
              <i className="fas fa-wave-square"></i><span>Análisis de Frecuencia</span>
            </button>
          </nav>

          <div className="sidebar-footer">
            <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
              <div className="status-dot"></div>
              <span style={{fontSize:'12px', color:'var(--fg-muted)'}}>Sistema activo</span>
            </div>
            <div style={{fontSize:'10px', color:'var(--border)', marginTop:'6px'}}>v2.0 — SAMHIA_EST.R</div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          {/* Top Bar */}
          <header className="top-bar">
            <div style={{display:'flex', alignItems:'center', gap:'14px'}}>
              <button
                className="mobile-toggle"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                style={{background:'var(--bg-raised)', border:'1px solid var(--border)', color:'var(--fg-muted)', cursor:'pointer', padding:'7px 10px', borderRadius:'8px', fontSize:'16px'}}
                aria-label="Abrir menú"
              >
                <i className="fas fa-bars"></i>
              </button>
              <div>
                <h1 className="font-display" style={{fontSize:'18px', fontWeight:'700', letterSpacing:'-0.01em', margin:'0'}}>
                  {sectionInfo[activeSection]?.title || 'METIS'}
                </h1>
                <p style={{fontSize:'12.5px', color:'var(--fg-muted)', margin:'2px 0 0'}}>
                  {sectionInfo[activeSection]?.desc || ''}
                </p>
              </div>
            </div>
            <div style={{display:'flex', alignItems:'center', gap:'16px'}}>
              <span
                className={`data-badge ${series.length > 0 ? 'visible' : ''}`}
              >
                <i className="fas fa-database" style={{marginRight:'5px'}}></i>
                <span>{series.length}</span> -datos
              </span>
            </div>
          </header>

          <div className="content-area">
            {/* ==================== SECCIÓN 1: INGESTA ==================== */}
            <section className={`section ${activeSection === 'ingesta' ? 'active' : ''}`} id="sec-ingesta" aria-label="Ingesta de datos">
              <div style={{marginBottom:'28px'}}>
                <h2 className="font-display" style={{fontSize:'26px', fontWeight:'700', margin:'0 0 8px', letterSpacing:'-0.02em'}}>Ingesta de datos</h2>
                <p style={{color:'var(--fg-muted)', fontSize:'14.5px', maxWidth:'600px', lineHeight:'1.6'}}>Carga tu serie hidrológica desde un archivo CSV o ingresa los valores manualmente. Los datos se almacenarán para todos los módulos de análisis.</p>
              </div>

              {/* Dropzone */}
              {(importStep === "upload" || importStep === "done") && (
                <div className="card" style={{marginBottom:'20px'}}>
                  <div
                    className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => document.getElementById('fileInput')?.click()}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        document.getElementById('fileInput')?.click();
                      }
                    }}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={(e) => { e.preventDefault(); setDragOver(false); const file = e.dataTransfer.files[0]; if (file) handleFile(file); }}
                  >
                    <div className="drop-icon"><i className="fas fa-cloud-arrow-up"></i></div>
                    <p style={{fontSize:'15px', fontWeight:'600', margin:'0 0 6px', position:'relative'}}>Arrastra un CSV o Excel aquí</p>
                    <p style={{fontSize:'13px', color:'var(--fg-muted)', margin:'0 0 16px', position:'relative'}}>O selecciona un archivo para cargar la serie de valores</p>
                    <input
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      style={{display:'none'}}
                      id="fileInput"
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => { handleFile(e.target.files?.[0]); e.target.value = ''; }}
                    />
                    <button
                      className="btn-secondary"
                      onClick={(e) => { e.stopPropagation(); document.getElementById('fileInput')?.click(); }}
                      type="button"
                    >
                      <i className="fas fa-folder-open" style={{marginRight:'6px'}}></i>Seleccionar archivo
                    </button>
                  </div>
                  <div style={{display:'flex', alignItems:'center', gap:'12px', marginTop:'14px', paddingTop:'14px', borderTop:'1px solid var(--border)'}}>
                    <span style={{fontSize:'11px', color:'var(--border)', marginLeft:'auto'}}>Formatos: CSV, XLSX, XLS</span>
                  </div>
                </div>
              )}

              {/* Preview & Column Selection */}
              {importStep === "preview" && filePreview && (
                <div className="card" style={{marginBottom:'20px'}}>
                  <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0 0 12px'}}>📄 Preview: {seriesId}</h3>

                  {filePreview.sheetNames.length > 0 && (
                    <div style={{marginBottom:'12px'}}>
                      <label className="form-label">Hoja:</label>
                      <select className="form-input" value={selectedSheet} onChange={(e) => setSelectedSheet(Number(e.target.value))}>
                        {filePreview.sheetNames.map((name, i) => (
                          <option key={i} value={i}>{name}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="table-wrapper" style={{maxHeight:'200px', overflow:'auto'}}>
                    <table className="data-table" style={{fontSize:'0.85em'}}>
                      <thead>
                        <tr>
                          {filePreview.headers.map((header, i) => (
                            <th key={i} style={{textAlign:'center'}}>
                              {header}
                              <span style={{marginLeft:'4px', fontSize:'0.9em'}}>
                                {filePreview.columnTypes[i] === 'date' && ' 📅'}
                                {filePreview.columnTypes[i] === 'numeric' && ' 🔢'}
                                {filePreview.columnTypes[i] === 'text' && ' 📝'}
                              </span>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {filePreview.rows.map((row, rowIdx) => (
                          <tr key={rowIdx}>
                            {row.map((cell, cellIdx) => (
                              <td key={cellIdx} style={{padding:'4px 8px'}}>{cell}</td>
                            ))}
                          </tr>
                        ))}
                        <tr>
                          <td colSpan={filePreview.headers.length} style={{textAlign:'center', color:'var(--fg-muted)', fontStyle:'italic'}}>
                            ... (más filas)
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div style={{fontSize:'0.8em', color:'var(--fg-muted)', marginTop:'8px'}}>📅 Fecha | 🔢 Numérica | 📝 Texto</div>

                  <div style={{marginTop:'16px', display:'grid', gap:'12px'}}>
                    <div>
                      <label className="form-label">Columna de fechas:</label>
                      <select className="form-input" value={selectedDateColumn} onChange={(e) => setSelectedDateColumn(e.target.value)}>
                        {filePreview.headers.map((header, i) => (
                          <option key={i} value={header}>
                            {filePreview.columnTypes[i] === 'date' && '📅 '}
                            {filePreview.columnTypes[i] === 'numeric' && '🔢 '}
                            {filePreview.columnTypes[i] === 'text' && '📝 '}
                            {header}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="form-label">Columna de valores:</label>
                      <select className="form-input" value={selectedValueColumn} onChange={(e) => setSelectedValueColumn(e.target.value)}>
                        {filePreview.headers.map((header, i) => (
                          <option key={i} value={header}>
                            {filePreview.columnTypes[i] === 'date' && '📅 '}
                            {filePreview.columnTypes[i] === 'numeric' && '🔢 '}
                            {filePreview.columnTypes[i] === 'text' && '📝 '}
                            {header}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {selectedDateColumn && selectedValueColumn && (
                    <div style={{marginTop:'16px', padding:'12px', background:'var(--bg)', borderRadius:'8px'}}>
                      <strong style={{fontSize:'0.9em'}}>Preview de importación:</strong>
                      <div style={{fontSize:'0.8em', color:'var(--fg-muted)', marginTop:'4px'}}>
                        Fecha: <strong style={{color:'var(--accent)'}}>{selectedDateColumn}</strong> | Valor: <strong style={{color:'var(--accent)'}}>{selectedValueColumn}</strong>
                      </div>
                    </div>
                  )}

                  <div className="button-group" style={{marginTop:'16px'}}>
                    <button className="btn-secondary" onClick={handleCancelImport}>← Volver</button>
                    <button className="btn-primary" onClick={handleImport} disabled={!selectedDateColumn || !selectedValueColumn}>Importar datos</button>
                  </div>
                </div>
              )}

              {/* Temporal Processing */}
              {importStep === "process" && (
                <div className="card" style={{marginBottom:'20px'}}>
                  <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0 0 12px'}}>⚙️ Procesamiento Temporal</h3>

                  <div className="temporal-controls" style={{marginBottom:'16px'}}>
                    <strong>📊 Datos cargados</strong>
                    <div style={{fontSize:'0.9em', color:'var(--fg-muted)', marginTop:'4px'}}>
                      {dates.length} observaciones desde {dates[0]} hasta {dates[dates.length - 1]}
                    </div>
                    {availableTargetFrequencies.length > 0 && (
                      <div style={{fontSize:'0.8em', color:'var(--accent)', marginTop:'8px'}}>
                        Frecuencias disponibles para agregación: {availableTargetFrequencies.join(", ")}
                      </div>
                    )}
                  </div>

                  <div className="temporal-controls" style={{marginBottom:'16px'}}>
                    <h4 style={{marginBottom:'12px', color:'var(--fg)'}}>⏱️ Configuración de Frecuencia Temporal</h4>
                    <p style={{fontSize:'0.85em', color:'var(--fg-muted)', marginBottom:'12px'}}>
                      Define el intervalo temporal de tu serie para los análisis estadísticos.
                    </p>

                    <div className="temporal-controls-row">
                      <div className="temporal-control-group">
                        <label>Frecuencia de la serie:</label>
                        <select value={timeFrequency} onChange={(e) => setTimeFrequency(e.target.value)}>
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
                          <div className="temporal-control-group" style={{flex:'0 0 100px'}}>
                            <label>Intervalo:</label>
                            <input type="number" min="1" value={customTimeInterval} onChange={(e) => setCustomTimeInterval(Number(e.target.value))} />
                          </div>
                          <div className="temporal-control-group" style={{flex:'0 0 150px'}}>
                            <label>Unidad:</label>
                            <select value={customTimeUnit} onChange={(e) => setCustomTimeUnit(e.target.value)}>
                              <option value="minutes">Minutos</option>
                              <option value="hours">Horas</option>
                              <option value="days">Días</option>
                            </select>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="temporal-toggle" style={{marginBottom:'16px'}}>
                    <input type="checkbox" checked={temporalProcessingEnabled} onChange={(e) => setTemporalProcessingEnabled(e.target.checked)} />
                    <span>Agregar datos a mayor resolución temporal</span>
                  </div>
                  <p style={{fontSize:'0.8em', color:'var(--fg-muted)', marginTop:'-10px', marginBottom:'16px', marginLeft:'54px'}}>
                    Permite agregar desde una frecuencia menor a una mayor (ej: minutos → horas → días).
                  </p>

                  {temporalProcessingEnabled && (
                    <div className="temporal-controls">
                      <h4 style={{marginBottom:'12px'}}>Opciones de Agregación Ascendente</h4>

                      <div className="temporal-controls-row">
                        <div className="temporal-control-group">
                          <label>Frecuencia objetivo:</label>
                          <select value={temporalTargetFrequency} onChange={(e) => setTemporalTargetFrequency(e.target.value)}>
                            {availableTargetFrequencies.includes("yearly") && <option value="yearly">📅 Anual</option>}
                            {availableTargetFrequencies.includes("monthly") && <option value="monthly">📆 Mensual</option>}
                            {availableTargetFrequencies.includes("daily") && <option value="daily">📋 Diaria</option>}
                            {availableTargetFrequencies.includes("hourly") && <option value="hourly">🕐 Horaria</option>}
                            {!availableTargetFrequencies.length && <option value="yearly">📅 Anual (default)</option>}
                          </select>
                        </div>

                        <div className="temporal-control-group">
                          <label>Método de agregación:</label>
                          <select value={temporalAggregationMethod} onChange={(e) => setTemporalAggregationMethod(e.target.value)}>
                            <option value="sum">∑ Suma (precipitación/volumen)</option>
                            <option value="mean">Ø Promedio (temperatura/nivel)</option>
                            <option value="max">↑ Máximo (caudal pico)</option>
                            <option value="min">↓ Mínimo</option>
                          </select>
                        </div>
                      </div>

                      <div className="temporal-controls-row" style={{marginTop:'12px'}}>
                        <div className="temporal-control-group">
                          <label className="temporal-toggle" style={{padding:0}}>
                            <input type="checkbox" checked={temporalHydrologicalYear} onChange={(e) => setTemporalHydrologicalYear(e.target.checked)} />
                            <span>Usar año hidrológico</span>
                          </label>
                        </div>

                        {temporalHydrologicalYear && (
                          <div className="temporal-control-group">
                            <label>Mes de inicio:</label>
                            <select value={temporalHydrologicalStartMonth} onChange={(e) => setTemporalHydrologicalStartMonth(Number(e.target.value))}>
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

                      <button className="btn-primary" onClick={handleTemporalProcessing} disabled={temporalProcessingLoading} style={{width:'100%', marginTop:'16px'}}>
                        {temporalProcessingLoading ? "⏳ Procesando..." : temporalProcessingResult ? "🔄 Reprocesar" : "▶️ Procesar datos"}
                      </button>
                    </div>
                  )}

                  {temporalProcessingError && (
                    <div className="status-banner error" style={{marginBottom:'16px', marginTop:'16px'}}>{temporalProcessingError}</div>
                  )}

                  {temporalProcessingResult && (
                    <div style={{marginBottom:'16px', padding:'12px', background:'var(--accent-light)', borderRadius:'8px', border:'1px solid rgba(10,143,116,0.2)'}}>
                      <h4 style={{marginBottom:'8px', color:'var(--accent)'}}>✓ Procesamiento completado</h4>
                      <div style={{fontSize:'0.85em'}}>
                        <div><strong>Frecuencia original:</strong> {temporalProcessingResult.original_frequency}</div>
                        <div><strong>Frecuencia objetivo:</strong> {temporalProcessingResult.target_frequency}</div>
                        <div><strong>Resultado:</strong> {temporalProcessingResult.n_original} → {temporalProcessingResult.n_result} observaciones</div>
                        <div><strong>Método:</strong> {temporalProcessingResult.aggregation_method}</div>
                        {temporalProcessingResult.daily_start_hour > 0 && (
                          <div><strong>Período diario:</strong> {temporalProcessingResult.daily_start_hour}:00 a {temporalProcessingResult.daily_start_hour}:00</div>
                        )}
                        {temporalProcessingResult.aggregation_bypass && (
                          <div style={{color:'var(--warning)'}}>⚠ Serie ya estaba en la frecuencia solicitada (sin cambios)</div>
                        )}
                      </div>
                      <button className="btn-secondary" onClick={handleRestoreOriginal} style={{marginTop:'12px'}}>↺ Restaurar serie original</button>
                    </div>
                  )}

                  <div className="button-group" style={{marginTop:'16px'}}>
                    <button className="btn-secondary" onClick={() => setImportStep("preview")}>← Volver</button>
                    <button className="btn-primary" onClick={handleFinishImport}>Continuar al análisis →</button>
                  </div>
                </div>
              )}

              {fileError && <div className="status-banner error" style={{marginTop:'12px'}}>{fileError}</div>}

              {/* Data Table */}
              <div className="card" id="tableCard" style={{display: series.length > 0 ? 'block' : 'none'}}>
                <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'16px'}}>
                  <div style={{display:'flex', alignItems:'center', gap:'10px'}}>
                    <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0'}}>Datos cargados</h3>
                    <span style={{fontSize:'11px', padding:'2px 8px', borderRadius:'5px', background:'var(--bg-hover)', color:'var(--fg-muted)', fontWeight:'600'}}>{series.length}</span>
                    <span style={{fontSize:'12px', color:'var(--fg-muted)'}}>{seriesId}</span>
                  </div>
                  <div style={{display:'flex', gap:'8px'}}>
                    <button className="btn-secondary" onClick={addRow} style={{fontSize:'12px', padding:'6px 12px'}}>
                      <i className="fas fa-plus" style={{marginRight:'4px'}}></i>Agregar fila
                    </button>
                    <button className="btn-secondary" onClick={() => { setSeries([0, 0, 0]); showWarning('Los datos fueron reiniciados al estado inicial', 'warning'); }} style={{fontSize:'12px', padding:'6px 12px', color:'var(--danger)', borderColor:'var(--danger-border)'}}>
                      <i className="fas fa-trash-can" style={{marginRight:'4px'}}></i>Limpiar
                    </button>
                  </div>
                </div>
                <div style={{maxHeight:'360px', overflowY:'auto', borderRadius:'10px', border:'1px solid var(--border)'}}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th style={{width:'60px'}}>#</th>
                        {dates.length > 0 && <th>Fecha</th>}
                        <th>Valor</th>
                        <th style={{width:'60px'}}>Acción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {series.map((value, index) => {
                        const isNumeric = typeof value === 'number';
                        const isNegative = isNumeric && value < 0;
                        const isZero = isNumeric && value === 0;
                        const isVirtualZero = isNumeric && value !== 0 && Math.abs(value) < 1e-10;

                        let rowClass = '';
                        if (isNegative) rowClass = 'cell-danger cell-error';
                        else if (isVirtualZero) rowClass = 'cell-virtual-zero cell-error';
                        else if (isZero) rowClass = 'cell-zero cell-error';

                        let cellClass = '';
                        let inputClass = '';
                        if (isNegative) { cellClass = 'danger-cell'; inputClass = 'danger'; }
                        else if (isVirtualZero) { cellClass = 'virtual-zero-cell'; inputClass = 'virtual-zero'; }
                        else if (isZero) { cellClass = 'warn-cell'; inputClass = 'warn'; }

                        return (
                          <tr
                            key={`row-${index}`}
                            className={rowClass}
                            style={{animation: `fadeUp 0.3s ease ${index * 0.02}s both`}}
                          >
                            <td style={{color:'var(--fg-muted)', fontSize:'12px'}}>{index + 1}</td>
                            {dates.length > 0 && <td style={{fontSize:'0.85em', color:'var(--fg-muted)'}}>{dates[index] || '-'}</td>}
                            <td className={cellClass}>
                              <input
                                type="number"
                                step="any"
                                value={value === "" ? "" : (typeof value === 'number' ? value : 0)}
                                className={inputClass}
                                data-index={index}
                                onChange={(e) => updateByIndex(index, e.target.value)}
                                onBlur={() => commitValue(index)}
                              />
                            </td>
                            <td>
                              <button className="btn-ghost" onClick={() => removeRow(index)} aria-label="Eliminar fila">
                                <i className="fas fa-xmark"></i>
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <p style={{fontSize:'11.5px', color:'var(--fg-muted)', margin:'12px 0 0', display:'flex', alignItems:'center', gap:'6px'}}>
                  <i className="fas fa-circle-info" style={{fontSize:'10px'}}></i>
                  <span style={{color:'var(--danger)'}}>🔴 Negativos</span> — 
                  <span style={{color:'var(--warning)'}}>🟡 Cero</span> — 
                  <span style={{color:'#ff8c42'}}>🟠 Virtualmente cero</span>.
                  Estos valores se consideran advertencias en el análisis.
                </p>
              </div>
            </section>

            {/* ==================== SECCIÓN 2: RESUMEN ==================== */}
            <section className={`section ${activeSection === 'resumen' ? 'active' : ''}`} id="sec-resumen" aria-label="Resumen de la serie">
              <div style={{marginBottom:'28px'}}>
                <h2 className="font-display" style={{fontSize:'26px', fontWeight:'700', margin:'0 0 8px', letterSpacing:'-0.02em'}}>Resumen de la serie</h2>
                <p style={{color:'var(--fg-muted)', fontSize:'14.5px', maxWidth:'600px', lineHeight:'1.6'}}>Estadísticas descriptivas y gráficos exploratorios de la serie cargada.</p>
              </div>

              {/* No Data State */}
              {getValidData().length === 0 && (
                <div className="card" style={{textAlign:'center', padding:'60px 24px'}}>
                  <i className="fas fa-chart-bar" style={{fontSize:'40px', color:'var(--border)', marginBottom:'16px'}}></i>
                  <p style={{fontSize:'15px', fontWeight:'600', color:'var(--fg-muted)', margin:'0 0 6px'}}>Sin datos cargados</p>
                  <p style={{fontSize:'13px', color:'var(--border)', margin:'0'}}>Ve a la sección de Ingesta para cargar tu serie hidrológica.</p>
                </div>
              )}

              {/* Data */}
              {getValidData().length > 0 && (
                <>
                  {/* Stat Cards */}
                  <div className="grid-stats">
                    {(() => {
                      const valid = getValidData();
                      const n = valid.length;
                      const mean = valid.reduce((a, b) => a + b, 0) / n;
                      const std = Math.sqrt(valid.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1));
                      const min = Math.min(...valid);
                      const max = Math.max(...valid);
                      const cv = mean !== 0 ? (std / Math.abs(mean)) : 0;
                      return (
                        <>
                          <div className="stat-card">
                            <div style={{display:'flex', alignItems:'flex-start', justifyContent:'space-between'}}>
                              <div>
                                <div className="stat-value">{n}</div>
                                <div className="stat-label">N de datos</div>
                              </div>
                              <div className="stat-icon" style={{background:'var(--accent-light)', color:'var(--accent)'}}><i className="fas fa-hashtag"></i></div>
                            </div>
                          </div>
                          <div className="stat-card">
                            <div style={{display:'flex', alignItems:'flex-start', justifyContent:'space-between'}}>
                              <div>
                                <div className="stat-value">{mean.toFixed(2)}</div>
                                <div className="stat-label">Media</div>
                              </div>
                              <div className="stat-icon" style={{background:'#eef0ff', color:'#6366f1'}}><i className="fas fa-equals"></i></div>
                            </div>
                          </div>
                          <div className="stat-card">
                            <div style={{display:'flex', alignItems:'flex-start', justifyContent:'space-between'}}>
                              <div>
                                <div className="stat-value">{std.toFixed(2)}</div>
                                <div className="stat-label">Desv. estándar</div>
                              </div>
                              <div className="stat-icon" style={{background:'var(--warning-bg)', color:'var(--warning)'}}><i className="fas fa-chart-area"></i></div>
                            </div>
                          </div>
                          <div className="stat-card">
                            <div style={{display:'flex', alignItems:'flex-start', justifyContent:'space-between'}}>
                              <div>
                                <div className="stat-value">{min.toFixed(2)}</div>
                                <div className="stat-label">Mínimo</div>
                              </div>
                              <div className="stat-icon" style={{background:'#eef6ff', color:'#3b82f6'}}><i className="fas fa-arrow-down"></i></div>
                            </div>
                          </div>
                          <div className="stat-card">
                            <div style={{display:'flex', alignItems:'flex-start', justifyContent:'space-between'}}>
                              <div>
                                <div className="stat-value">{max.toFixed(2)}</div>
                                <div className="stat-label">Máximo</div>
                              </div>
                              <div className="stat-icon" style={{background:'var(--danger-bg)', color:'var(--danger)'}}><i className="fas fa-arrow-up"></i></div>
                            </div>
                          </div>
                          <div className="stat-card">
                            <div style={{display:'flex', alignItems:'flex-start', justifyContent:'space-between'}}>
                              <div>
                                <div className="stat-value">{(cv * 100).toFixed(2)}%</div>
                                <div className="stat-label">Coef. variación</div>
                              </div>
                              <div className="stat-icon" style={{background:'#f5eeff', color:'#a855f7'}}><i className="fas fa-percent"></i></div>
                            </div>
                          </div>
                        </>
                      );
                    })()}
                  </div>

                  {/* Warnings */}
                  {warnings.length > 0 && (
                    <div className="card status-banner warning" style={{marginBottom:'24px', borderColor:'var(--warning-border)'}}>
                      <div style={{display:'flex', alignItems:'center', gap:'10px', marginBottom:'12px'}}>
                        <div className="warning-badge"><div className="pulse-dot"></div>Advertencias detectadas</div>
                      </div>
                      {warnings.map((w) => (
                        <p key={w.code} style={{fontSize:'13px', color:'var(--fg-muted)', margin:'0', lineHeight:'1.6'}}>
                          {w.message} [{w.affected_indices.join(', ')}]
                        </p>
                      ))}
                    </div>
                  )}

                  {/* Charts */}
                  <div className="grid-charts">
                    <div className="card">
                      <h3 className="font-display" style={{fontSize:'14px', fontWeight:'600', margin:'0 0 16px', display:'flex', alignItems:'center', gap:'8px'}}>
                        <i className="fas fa-braille" style={{color:'var(--accent)', fontSize:'12px'}}></i>Dispersión temporal
                      </h3>
                      <div className="chart-container">
                        {(() => {
                          const valid = getValidData();
                          if (valid.length >= 2) {
                            return <ScatterPlot values={valid} />;
                          }
                          return <p style={{color:'var(--fg-muted)'}}>Agrega más datos para ver el gráfico.</p>;
                        })()}
                      </div>
                    </div>
                    <div className="card">
                      <h3 className="font-display" style={{fontSize:'14px', fontWeight:'600', margin:'0 0 16px', display:'flex', alignItems:'center', gap:'8px'}}>
                        <i className="fas fa-bars-staggered" style={{color:'var(--accent)', fontSize:'12px'}}></i>Correlograma preliminar
                      </h3>
                      {getValidData().length >= 4 ? (
                        <div className="chart-container">
                          <Correlogram data={autoCorrelation} band={band} />
                        </div>
                      ) : (
                        <div style={{textAlign:'center', padding:'60px 0'}}>
                          <i className="fas fa-chart-bar" style={{fontSize:'32px', color:'var(--border)', marginBottom:'12px'}}></i>
                          <p style={{fontSize:'13px', color:'var(--fg-muted)', margin:'0'}}>Necesitas al menos 4 datos para ver autocorrelación.</p>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </section>

            {/* ==================== SECCIÓN 3: SAMHIA ==================== */}
            <section className={`section ${activeSection === 'samhia' ? 'active' : ''}`} id="sec-samhia" aria-label="Análisis SAMHIA">
              <div style={{marginBottom:'28px'}}>
                <h2 className="font-display" style={{fontSize:'26px', fontWeight:'700', margin:'0 0 8px', letterSpacing:'-0.02em'}}>Análisis SAMHIA y Reportes PDF</h2>
                <p style={{color:'var(--fg-muted)', fontSize:'14.5px', maxWidth:'660px', lineHeight:'1.6'}}>Análisis estadístico completo basado en SAMHIA_EST.R con tests detallados y generación de reportes PDF de 10 páginas.</p>
              </div>

              <div className="grid-2col">
                <div className="card">
                  <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0 0 20px'}}>Configuración del reporte</h3>
                  <div style={{display:'flex', flexDirection:'column', gap:'16px'}}>
                    <div>
                      <label className="form-label" htmlFor="samEmbalse">Nombre del embalse</label>
                      <input type="text" id="samEmbalse" className="form-input" value={reservoirName} onChange={(e) => setReservoirName(e.target.value)} placeholder="Ej: Embalse La Angostura" />
                    </div>
                    <div>
                      <label className="form-label" htmlFor="samVariable">Nombre de la variable</label>
                      <input type="text" id="samVariable" className="form-input" value={seriesName} onChange={(e) => setSeriesName(e.target.value)} placeholder="Ej: Caudal máximo mensual (m³/s)" />
                    </div>
                    <div>
                      <label className="form-label" htmlFor="samAlpha">Nivel de significancia (α)</label>
                      <select id="samAlpha" className="form-input" value={alpha} onChange={(e) => setAlpha(Number(e.target.value))}>
                        <option value="0.01">0.01 (99%)</option>
                        <option value="0.05">0.05 (95%)</option>
                        <option value="0.10">0.10 (90%)</option>
                      </select>
                    </div>
                    <div id="samDataReq" style={{
                      padding:'10px 14px', borderRadius:'8px',
                      background: 'var(--warning-bg)', border: '1px solid var(--warning-border)',
                      fontSize:'12.5px', color:'var(--warning)', display:'flex', alignItems:'center', gap:'8px',
                      ...(getValidData().filter(v => v > 0).length >= 12 ? {display:'none'} : {})
                    }}>
                      <i className="fas fa-triangle-exclamation"></i>
                      Se requieren al menos 12 datos válidos para el análisis SAMHIA completo.
                    </div>
                    <button className="btn-primary" id="samGenerateBtn" onClick={handleGeneratePdf} disabled={isGeneratingPdf || getValidData().filter(v => v > 0).length < 12} style={{width:'100%', marginTop:'4px'}}>
                      <i className="fas fa-file-pdf" style={{marginRight:'8px'}}></i>{isGeneratingPdf ? "Generando PDF..." : "Generar reporte PDF"}
                    </button>
                  </div>
                </div>

                <div className="card">
                  <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0 0 16px'}}>Contenido del reporte</h3>
                  <p style={{fontSize:'13px', color:'var(--fg-muted)', margin:'0 0 14px'}}>El reporte PDF generado incluye las siguientes secciones:</p>
                  <div className="feature-item"><i className="fas fa-check"></i><span>Gráficos de serie temporal, años calendario e hidrológico</span></div>
                  <div className="feature-item"><i className="fas fa-check"></i><span>Análisis de datos atípicos y boxplots mensuales/anuales</span></div>
                  <div className="feature-item"><i className="fas fa-check"></i><span>Histograma, Q-Q plot y función de autocorrelación</span></div>
                  <div className="feature-item"><i className="fas fa-check"></i><span>Tablas resumen de estadísticas y año hidrológico</span></div>
                  <div className="feature-item"><i className="fas fa-check"></i><span>Resultados de tests de independencia, homogeneidad y tendencia</span></div>
                  <div style={{marginTop:'18px', padding:'14px', borderRadius:'10px', background:'var(--bg)', border:'1px solid var(--border)'}}>
                    <div style={{display:'flex', alignItems:'center', gap:'8px', marginBottom:'6px'}}>
                      <i className="fas fa-file-pdf" style={{color:'var(--danger)', fontSize:'18px'}}></i>
                      <span style={{fontSize:'13px', fontWeight:'600'}}>10 páginas</span>
                    </div>
                    <p style={{fontSize:'11.5px', color:'var(--fg-muted)', margin:'0', lineHeight:'1.5'}}>Formato profesional listo para presentación o entrega técnica.</p>
                  </div>
                </div>
              </div>

              {/* PDF Generation Progress */}
              <div style={{marginTop:'20px'}}>
                <div className="card" style={{marginBottom:'20px'}}>
                  <div className="button-group">
                    <button className="btn-primary" onClick={handleAnalyzeSamhia} disabled={isAnalyzing || series.length < 12}>
                      {isAnalyzing ? "Analizando..." : "Ejecutar análisis SAMHIA"}
                    </button>
                    {pdfPath && (
                      <button className="btn-secondary" onClick={handleDownloadPdf}>
                        Descargar PDF
                      </button>
                    )}
                  </div>

                  {analysisError && <div className="status-banner error" style={{marginTop:'12px'}}>{analysisError}</div>}
                  {pdfError && <div className="status-banner error" style={{marginTop:'12px'}}>{pdfError}</div>}

                  {pdfPath && (
                    <div className="status-pill accepted" style={{marginTop:'12px', display:'inline-flex'}}>
                      PDF generado exitosamente
                    </div>
                  )}
                </div>

                {/* Analysis Results */}
                {analysisResults && (
                  <div className="card">
                    <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0 0 16px'}}>Resultados del análisis SAMHIA</h3>

                    <div className="status-card" style={{marginBottom:'18px'}}>
                      <strong>Análisis completado</strong>
                      <p>Variable: <strong>{analysisResults.series_name}</strong></p>
                      <p>Embalse: <strong>{analysisResults.reservoir_name}</strong></p>
                      <p>N de datos: <strong>{analysisResults.n_data}</strong></p>
                    </div>

                    {/* Tabs */}
                    <div style={{display:'flex', gap:'8px', marginBottom:'16px', flexWrap:'wrap'}}>
                      {["analysis", "independence", "homogeneity", "trend", "outliers"].map((tab) => (
                        <button
                          key={tab}
                          className={`btn-secondary ${activeSamhiaTab === tab ? 'selected-tab' : ''}`}
                          onClick={() => setActiveSamhiaTab(tab)}
                          style={{
                            padding:'8px 16px', fontSize:'0.9rem',
                            ...(activeSamhiaTab === tab ? {background:'var(--accent-light)', color:'var(--accent)', borderColor:'var(--accent)'} : {})
                          }}
                        >
                          {tab === "analysis" && "Estadísticas"}
                          {tab === "independence" && "Independencia"}
                          {tab === "homogeneity" && "Homogeneidad"}
                          {tab === "trend" && "Tendencia"}
                          {tab === "outliers" && "Atípicos"}
                        </button>
                      ))}
                    </div>

                    {/* Tab Content */}
                    {activeSamhiaTab === "analysis" && (
                      <DescriptiveStatsPanel stats={analysisResults.descriptive_stats} />
                    )}
                    {activeSamhiaTab === "independence" && (
                      <TestResultsPanel title="Tests de Independencia" tests={analysisResults.independence} description="Evalúan si los datos son independientes (no autocorrelacionados)." />
                    )}
                    {activeSamhiaTab === "homogeneity" && (
                      <TestResultsPanel title="Tests de Homogeneidad" tests={analysisResults.homogeneity} description="Evalúan si la serie es homogénea a lo largo del tiempo." />
                    )}
                    {activeSamhiaTab === "trend" && (
                      <TestResultsPanel title="Tests de Tendencia" tests={analysisResults.trend} description="Evalúan si existe tendencia significativa en la serie." />
                    )}
                    {activeSamhiaTab === "outliers" && (
                      <OutliersPanel tests={analysisResults.outliers} />
                    )}
                  </div>
                )}

                {analysisResults && (
                  <div className="card visualizations-section">
                    <OutlierVisualizationsPanel
                      plots={outlierPlots}
                      plotsLoading={outlierPlotsLoading}
                      plotsError={outlierPlotsError}
                      onLoadPlots={handleLoadOutlierPlots}
                    />
                  </div>
                )}

              </div>
            </section>

            {/* ==================== SECCIÓN 4: FRECUENCIA ==================== */}
            <section className={`section ${activeSection === 'frecuencia' ? 'active' : ''}`} id="sec-frecuencia" aria-label="Análisis de Frecuencia">
              <div style={{marginBottom:'28px'}}>
                <h2 className="font-display" style={{fontSize:'26px', fontWeight:'700', margin:'0 0 8px', letterSpacing:'-0.02em'}}>Análisis de Frecuencia</h2>
                <p style={{color:'var(--fg-muted)', fontSize:'14.5px', maxWidth:'640px', lineHeight:'1.6'}}>Ajusta distribuciones de probabilidad a tu serie y calcula eventos de diseño.</p>
              </div>

              {getValidData().length === 0 && (
                <div className="card" style={{textAlign:'center', padding:'60px 24px'}}>
                  <i className="fas fa-wave-square" style={{fontSize:'40px', color:'var(--border)', marginBottom:'16px'}}></i>
                  <p style={{fontSize:'15px', fontWeight:'600', color:'var(--fg-muted)', margin:'0 0 6px'}}>Sin datos cargados</p>
                  <p style={{fontSize:'13px', color:'var(--border)', margin:'0'}}>Carga una serie hidrológica en la sección de Ingesta para ejecutar el análisis.</p>
                </div>
              )}

              {getValidData().length > 0 && (
                <>
                  <div className="grid-2col" style={{marginBottom:'20px'}}>
                    <div className="card">
                      <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0 0 16px'}}>Parámetros del análisis</h3>
                      <div style={{marginBottom:'16px'}}>
                        <label className="form-label" htmlFor="frecMethod">Método de estimación</label>
                        <select id="frecMethod" className="form-input" value={estimationMethod} onChange={(e) => setEstimationMethod(e.target.value)}>
                          {ESTIMATION_METHODS.map((method) => (
                            <option key={method} value={method}>{method}</option>
                          ))}
                        </select>
                      </div>
                      <p style={{fontSize:'12px', color:'var(--fg-muted)', margin:'0', lineHeight:'1.5'}}>
                        <i className="fas fa-circle-info" style={{fontSize:'10px', marginRight:'4px'}}></i>
                        El método L-Momentos es recomendado por SAMHIA para series hidrológicas con presencia de valores atípicos.
                      </p>
                    </div>
                    <div className="card">
                      <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0 0 16px'}}>Distribuciones a ajustar</h3>
                      <div className="grid-dists">
                        {AVAILABLE_DISTRIBUTIONS.map((dist) => (
                          <label key={dist} className="custom-check">
                            <input type="checkbox" checked={selectedDistributions.includes(dist)} onChange={() => toggleDistribution(dist)} />
                            <span className="check-box"><i className="fas fa-check"></i></span>
                            <span>{dist}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  <button className="btn-primary" onClick={handleFit} disabled={isFitting || selectedDistributions.length === 0} style={{marginBottom:'24px'}}>
                    <i className="fas fa-play" style={{marginRight:'8px'}}></i>
                    {isFitting ? "Ajustando..." : "Ejecutar análisis de frecuencia"}
                  </button>

                  {fitError && <div className="status-banner error" style={{marginBottom:'24px'}}>{fitError}</div>}

                  {/* Fit Results */}
                  {fitResults && (
                    <>
                      <div className="card" style={{marginBottom:'20px'}}>
                        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'18px'}}>
                          <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0'}}>Resultados del ajuste</h3>
                          <span className="status-pill accepted">
                            <i className="fas fa-check-circle" style={{marginRight:'4px'}}></i>Completado
                          </span>
                        </div>

                        {fitResults.recommended_distribution && (
                          <div className="status-card" style={{marginBottom:'18px'}}>
                            <strong>Distribución recomendada</strong>
                            <span className="status-pill accepted" style={{marginTop:'8px', display:'inline-flex'}}>
                              {fitResults.recommended_distribution.distribution_name}
                            </span>
                            <p style={{marginTop:'8px', fontSize:'0.9rem', color:'var(--fg-muted)'}}>
                              Método: {fitResults.estimation_method} | N: {fitResults.n}
                            </p>
                          </div>
                        )}

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
                      </div>

                      {/* Design Event */}
                      {selectedDistribution && (
                        <div className="card" style={{marginBottom:'20px'}}>
                          <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0 0 16px'}}>Cálculo de evento de diseño</h3>
                          <div style={{display:'flex', gap:'18px', flexWrap:'wrap', alignItems:'flex-end'}}>
                            <div style={{flex:1, minWidth:'200px'}}>
                              <label className="form-label" htmlFor="returnPeriod">Período de retorno (años):</label>
                              <input id="returnPeriod" type="number" className="form-input" value={returnPeriod} onChange={(e) => setReturnPeriod(Number(e.target.value))} min="1" step="1" />
                            </div>
                            <button className="btn-primary" onClick={handleDesignEvent} disabled={isCalculatingDesign}>
                              {isCalculatingDesign ? "Calculando..." : "Calcular evento de diseño"}
                            </button>
                          </div>

                          {designError && <div className="status-banner error" style={{marginTop:'12px'}}>{designError}</div>}

                          {designEvent && (
                            <div className="status-card" style={{marginTop:'18px'}}>
                              <strong>Resultado del evento de diseño</strong>
                              <div className="table-wrapper">
                                <table>
                                  <tbody>
                                    <tr><th>Período de retorno</th><td>{designEvent.return_period.toFixed(1)} años</td></tr>
                                    <tr><th>Probabilidad anual</th><td>{(designEvent.annual_probability * 100).toFixed(2)}%</td></tr>
                                    <tr><th>Valor de diseño</th><td style={{fontSize:'1.1rem', fontWeight:'bold', color:'var(--accent)'}}>{designEvent.design_value.toFixed(2)}</td></tr>
                                    <tr><th>Distribución utilizada</th><td>{designEvent.distribution_name}</td></tr>
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </>
              )}
            </section>
          </div>
        </main>
      </div>

      {/* Toast Container */}
      <div className="toast-container" id="toastContainer" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.type} ${toast.removing ? 'removing' : ''}`}
            onClick={() => removeToast(toast.id)}
          >
            <i className={`fas ${toast.type === 'success' ? 'fa-check-circle' : toast.type === 'warning' ? 'fa-triangle-exclamation' : toast.type === 'error' ? 'fa-circle-xmark' : 'fa-circle-info'}`}></i>
            <span>{toast.message}</span>
          </div>
        ))}
      </div>
    </>
  );
}

// =============================================================================
// SUBCOMPONENTES - SVG GRÁFICOS
// =============================================================================

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
      <rect x="0" y="0" width="100%" height="100%" fill="var(--bg)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--border)" />
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--border)" />
      {points.map((point, index) => (
        <circle key={index} cx={point.x} cy={point.y} r="4" fill="var(--accent)" />
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
      <rect x="0" y="0" width="100%" height="100%" fill="var(--bg)" />
      <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="var(--border)" />
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
            <line x1={x} y1={height / 2} x2={x} y2={y} stroke="#7dd3fc" strokeWidth="10" />
            <text x={x} y={height - 12} fill="var(--fg-muted)" fontSize="12" textAnchor="middle">
              {item.lag}
            </text>
          </g>
        );
      })}
      <text x={padding} y={padding - 6} fill="var(--fg-muted)" fontSize="12">
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
        className={`accordion-button ${isSelected ? 'selected' : ''}`}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
      >
        <span>
          {distribution.distribution_name}
          {distribution.is_recommended && (
            <span className="pill accepted" style={{marginLeft:'8px', fontSize:'0.8rem'}}>Recomendada</span>
          )}
        </span>
        <span>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="accordion-panel">
          <div style={{marginBottom:'12px'}}>
            <button type="button" className="btn-secondary" onClick={onSelect} style={{fontSize:'0.9rem', padding:'8px 14px'}}>
              {isSelected ? "Seleccionada" : "Seleccionar para evento de diseño"}
            </button>
          </div>

          <div style={{marginBottom:'16px'}}>
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
      <h4 style={{marginBottom:'12px'}}>Estadísticas Descriptivas</h4>
      <div className="table-wrapper">
        <table>
          <tbody>
            {statsData.map((stat) => (
              <tr key={stat.label}>
                <th style={{textAlign:'left', width:'50%'}}>{stat.label}</th>
                <td style={{textAlign:'right'}}>{stat.value}</td>
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
        <h4 style={{marginBottom:'12px'}}>{title}</h4>
        <p style={{color:'var(--fg-muted)'}}>No hay resultados disponibles.</p>
      </div>
    );
  }

  return (
    <div>
      <h4 style={{marginBottom:'12px'}}>{title}</h4>
      <p style={{color:'var(--fg-muted)', marginBottom:'12px', fontSize:'0.9rem'}}>{description}</p>
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

      <div style={{marginTop:'16px'}}>
        {testEntries.map(([key, result]) => {
          if (!result.detail) return null;
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
            <p key={`detail-${key}`} style={{fontSize:'0.85rem', color:'var(--fg-muted)', marginBottom:'4px'}}>
              <strong>{formatTestName(key)}:</strong> {detailText}
            </p>
          );
        })}
      </div>
    </div>
  );
}

function OutlierVisualizationsPanel({ plots, plotsLoading, plotsError, onLoadPlots }) {
  const plotItems = [
    { key: "control_chart", title: "Serie temporal con umbrales Kn" },
    { key: "probability_plot", title: "Probability plot" },
    { key: "qq_plot", title: "Q-Q plot" },
    { key: "fdp_plot", title: "Función de densidad de probabilidad" },
  ];
  const plotUrls = plots?.plot_urls || {};
  const hasPlots = Object.keys(plotUrls).length > 0;

  return (
    <div>
      <div style={{display:'flex', justifyContent:'space-between', gap:'16px', alignItems:'center', flexWrap:'wrap', marginBottom:'16px'}}>
        <div>
          <h3 className="font-display" style={{fontSize:'15px', fontWeight:'600', margin:'0 0 6px'}}>Visualizaciones del análisis SAMHIA</h3>
          <p style={{fontSize:'13px', color:'var(--fg-muted)', margin:0, lineHeight:'1.5'}}>
            Gráficos generados para la detección de valores atípicos.
          </p>
        </div>
        <button
          type="button"
          className="btn-load-plots"
          onClick={onLoadPlots}
          disabled={plotsLoading}
        >
          <i className="fas fa-chart-line"></i>
          {plotsLoading ? "Generando gráficos..." : hasPlots ? "Actualizar gráficos" : "Generar gráficos"}
        </button>
      </div>

      {plotsError && <div className="status-banner error" style={{marginBottom:'12px'}}>{plotsError}</div>}

      {plotsLoading && (
        <div className="status-card">
          Generando visualizaciones del análisis...
        </div>
      )}

      {!plotsLoading && !hasPlots && !plotsError && (
        <p style={{fontSize:'13px', color:'var(--fg-muted)', margin:0}}>
          Usa el botón para generar los gráficos asociados al análisis.
        </p>
      )}

      {hasPlots && (
        <>
          {plots.outliers_detected !== undefined && (
            <div className="status-card" style={{marginBottom:'16px'}}>
              Atípicos detectados: <strong>{plots.outliers_detected}</strong>
            </div>
          )}
          <div className="visualizations-grid">
            {plotItems.map((plot) => (
              plotUrls[plot.key] ? (
                <div key={plot.key} className="water-chart-box">
                  <div className="chart-title">{plot.title}</div>
                  <div className="chart-content">
                    <img
                      src={plotUrls[plot.key]}
                      alt={plot.title}
                      style={{width:'100%', height:'auto', display:'block', borderRadius:'8px'}}
                    />
                  </div>
                </div>
              ) : null
            ))}
          </div>
        </>
      )}
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

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function hashStr(str) { let h = 0; for (let i = 0; i < str.length; i++) h = ((h << 5) - h) + str.charCodeAt(i); return Math.abs(h); }
function r(seed) { const x = Math.sin(seed * 9301 + 49297) * 49297; return x - Math.floor(x); }
