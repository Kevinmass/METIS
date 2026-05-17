/**
 * Componente Samhia - Análisis Estadístico Completo SAMHIA
 *
 * Este módulo implementa la UI para el análisis estadístico completo SAMHIA,
 * permitiendo:
 *   - Análisis estadístico completo con tests de independencia, homogeneidad,
 *     tendencia y detección de atípicos
 *   - Generación de reportes PDF de 10 páginas
 *   - Visualización de estadísticas descriptivas y resultados de tests
 *   - Procesamiento batch de múltiples archivos
 *
 * Integración con API:
 *   - POST /reports/analyze: Análisis estadístico completo
 *   - POST /reports/pdf: Genera reporte PDF
 *   - GET /reports/download/{filename}: Descarga PDF generado
 *   - POST /reports/upload: Subir archivo para análisis
 *
 * @module Samhia
 */

import { useState, useMemo } from "react";
import * as XLSX from "xlsx";

// =============================================================================
// CONSTANTES DE CONFIGURACIÓN
// =============================================================================

/** URL base de la API METIS */
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

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

/**
 * Parsea contenido CSV extrayendo columnas de fechas y valores.
 * @param {string} text - Contenido del archivo CSV
 * @returns {Object} Object con arrays dates y data
 */
function parseCsvWithDates(text) {
  const lines = text
    .trim()
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "");
  
  if (lines.length < 2) return { dates: [], data: [] };
  
  const headers = lines[0].split(/[;,]/).map(h => h.trim().toLowerCase());
  const dateIndex = headers.findIndex(h => h.includes('date') || h.includes('fecha'));
  const valueIndex = dateIndex === 0 ? 1 : 0;
  
  const dates = [];
  const data = [];
  
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(/[;,]/);
    if (dateIndex >= 0 && parts[dateIndex]) {
      dates.push(parts[dateIndex].trim());
    } else {
      dates.push(`2020-${String((i % 12) + 1).padStart(2, '0')}-01`);
    }
    const val = parts[valueIndex]?.trim();
    if (val && !isNaN(Number(val))) {
      data.push(Number(val));
    }
  }
  
  return { dates, data };
}

/**
 * Parsea buffer de archivo Excel extrayendo fechas y valores.
 * @param {ArrayBuffer} buffer - Buffer del archivo Excel
 * @param {string} sheetName - Nombre de la hoja (opcional)
 * @returns {Object} Object con arrays dates, data y columns
 */
function parseExcelWithDates(buffer, sheetName = null) {
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheet = sheetName || workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheet];
  const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
  
  if (jsonData.length < 2) return { dates: [], data: [], columns: [] };
  
  const headers = jsonData[0].map(h => String(h || '').toLowerCase());
  const dateIndex = headers.findIndex(h => h.includes('date') || h.includes('fecha'));
  const numericColumns = headers.map((h, i) => ({ h, i })).filter(({ h, i }) => {
    if (i === dateIndex) return false;
    const vals = jsonData.slice(1, 6).map(row => row[i]).filter(v => v !== undefined && v !== '');
    return vals.length > 0 && vals.every(v => typeof v === 'number' || !isNaN(Number(v)));
  });
  
  const dates = [];
  const data = [];
  
  for (let i = 1; i < jsonData.length; i++) {
    const row = jsonData[i];
    if (dateIndex >= 0 && row[dateIndex]) {
      const dateVal = row[dateIndex];
      if (typeof dateVal === 'number') {
        const excelEpoch = new Date(1899, 11, 30);
        const date = new Date(excelEpoch.getTime() + dateVal * 24 * 60 * 60 * 1000);
        dates.push(date.toISOString().split('T')[0]);
      } else {
        dates.push(String(dateVal));
      }
    } else {
      dates.push(`2020-${String((i % 12) + 1).padStart(2, '0')}-01`);
    }
    
    if (numericColumns.length > 0) {
      const val = row[numericColumns[0].i];
      if (val !== undefined && val !== '' && !isNaN(Number(val))) {
        data.push(Number(val));
      }
    }
  }
  
  return { dates, data, columns: numericColumns.map(c => headers[c.i]) };
}

// =============================================================================
// COMPONENTE PRINCIPAL SAMHIA
// =============================================================================

/**
 * Componente de análisis estadístico completo SAMHIA.
 *
 * @param {Object} props - Props del componente
 * @param {number[]} props.series - Serie de valores numéricos
 * @param {string} props.seriesId - Identificador de la serie
 * @returns {JSX.Element} Componente de análisis SAMHIA
 */
export default function Samhia({ series, seriesId }) {
  // ---------------------------------------------------------------------------
  // ESTADO DEL COMPONENTE
  // ---------------------------------------------------------------------------

  const [reservoirName, setReservoirName] = useState(seriesId || "Embalse");
  const [seriesName, setSeriesName] = useState("Variable");
  const [dates, setDates] = useState([]);
  const [data, setData] = useState(series || []);
  const [alpha, setAlpha] = useState(0.05);
  
  const [analysisResults, setAnalysisResults] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  const [pdfPath, setPdfPath] = useState(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [pdfError, setPdfError] = useState("");
  
  const [activeTab, setActiveTab] = useState("analysis");
  const [dragOver, setDragOver] = useState(false);
  
  // Estado para gráficos de outliers
  const [outlierPlots, setOutlierPlots] = useState(null);
  const [outlierPlotsLoading, setOutlierPlotsLoading] = useState(false);
  const [outlierPlotsError, setOutlierPlotsError] = useState("");

  // ---------------------------------------------------------------------------
  // MEMOIZACIÓN DE CÁLCULOS
  // ---------------------------------------------------------------------------

  const seriesValid = data.length >= 12;
  const seriesStats = useMemo(() => {
    if (data.length === 0) return null;
    const valid = data.filter(v => Number.isFinite(v));
    return {
      n: valid.length,
      mean: valid.reduce((a, b) => a + b, 0) / valid.length,
      min: Math.min(...valid),
      max: Math.max(...valid),
    };
  }, [data]);

  // ---------------------------------------------------------------------------
  // HANDLERS DE ARCHIVOS
  // ---------------------------------------------------------------------------

  const handleFile = async (file) => {
    setAnalysisError("");
    setPdfError("");
    setAnalysisResults(null);
    setPdfPath(null);

    if (!file) return;
    
    const accepted = [".csv", ".xlsx", ".xls"];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!accepted.includes(ext)) {
      setAnalysisError("Solo se permiten archivos CSV o Excel (.xlsx, .xls)");
      return;
    }

    setReservoirName(file.name.replace(/\.[^/.]+$/, ""));

    if (ext === ".csv") {
      const text = await file.text();
      const parsed = parseCsvWithDates(text);
      if (parsed.data.length === 0) {
        setAnalysisError("El archivo no contiene valores numéricos válidos.");
        return;
      }
      setDates(parsed.dates);
      setData(parsed.data);
      return;
    }

    if (ext === ".xlsx" || ext === ".xls") {
      const buffer = await file.arrayBuffer();
      const parsed = parseExcelWithDates(buffer);
      if (parsed.data.length === 0) {
        setAnalysisError("El archivo no contiene valores numéricos válidos.");
        return;
      }
      setDates(parsed.dates);
      setData(parsed.data);
      if (parsed.columns.length > 0) {
        setSeriesName(parsed.columns[0]);
      }
      return;
    }

    setAnalysisError("Formato de archivo no compatible.");
  };

  // ---------------------------------------------------------------------------
  // HANDLERS DE API
  // ---------------------------------------------------------------------------

  /**
   * Ejecuta análisis estadístico completo SAMHIA.
   */
  const handleAnalyze = async () => {
    setAnalysisError("");
    setAnalysisResults(null);

    if (!seriesValid) {
      setAnalysisError("La serie debe tener al menos 12 datos válidos.");
      return;
    }

    setIsAnalyzing(true);
    try {
      // Generar fechas si no existen
      const analysisDates = dates.length === data.length 
        ? dates 
        : data.map((_, i) => `2020-${String((i % 12) + 1).padStart(2, '0')}-15`);

      const response = await fetch(`${API_BASE}/reports/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data: data,
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
        // Cargar gráficos de outliers automáticamente
        fetchOutlierPlots();
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
   * Obtiene los gráficos de análisis de outliers.
   */
  const fetchOutlierPlots = async () => {
    setOutlierPlotsLoading(true);
    setOutlierPlotsError("");
    
    try {
      const analysisDates = dates.length === data.length 
        ? dates 
        : data.map((_, i) => `2020-${String((i % 12) + 1).padStart(2, '0')}-15`);

      const response = await fetch(`${API_BASE}/reports/plots/outliers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data: data,
          dates: analysisDates,
          series_name: seriesName,
          reservoir_name: reservoirName,
          alpha: alpha,
          distribution: "lognormal",
        }),
      });

      const json = await response.json();
      if (!response.ok) {
        setOutlierPlotsError(json.detail || "Error al cargar gráficos");
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
   * Genera reporte PDF SAMHIA.
   */
  const handleGeneratePdf = async () => {
    setPdfError("");
    setPdfPath(null);

    if (!seriesValid) {
      setPdfError("La serie debe tener al menos 12 datos válidos.");
      return;
    }

    setIsGeneratingPdf(true);
    try {
      const analysisDates = dates.length === data.length 
        ? dates 
        : data.map((_, i) => `2020-${String((i % 12) + 1).padStart(2, '0')}-15`);

      const response = await fetch(`${API_BASE}/reports/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data: data,
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

  // ---------------------------------------------------------------------------
  // RENDERIZADO
  // ---------------------------------------------------------------------------

  return (
    <div className="app-shell">
      <header className="page-header">
        <div>
          <h1>METIS — Análisis SAMHIA</h1>
          <p>
            Sistema de Análisis Multivariable completo con tests de independencia,
            homogeneidad, tendencia y generación de reportes PDF.
          </p>
        </div>
      </header>

      <div className="section-grid">
        {/* Panel de configuración y carga */}
        <section className="panel">
          <h2>1. Datos de entrada</h2>
          
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
            <p>O selecciona un archivo para cargar la serie temporal.</p>
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              style={{ opacity: 0, position: "absolute", inset: 0, cursor: "pointer" }}
              onChange={(event) => handleFile(event.target.files?.[0])}
            />
          </div>

          {analysisError && <div className="error-banner">{analysisError}</div>}

          <div style={{ marginTop: "18px" }}>
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

          <div style={{ marginTop: "12px" }}>
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

          <div style={{ marginTop: "12px" }}>
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

          {seriesStats && (
            <div className="status-card" style={{ marginTop: "18px" }}>
              <strong>Resumen de la serie cargada</strong>
              <p>N de datos: <strong>{seriesStats.n}</strong></p>
              <p>Media: <strong>{seriesStats.mean.toFixed(2)}</strong></p>
              <p>Rango: <strong>{seriesStats.min.toFixed(2)} - {seriesStats.max.toFixed(2)}</strong></p>
            </div>
          )}

          <div className="button-group" style={{ marginTop: "18px" }}>
            <button
              type="button"
              className="button-primary"
              onClick={handleAnalyze}
              disabled={isAnalyzing || !seriesValid}
            >
              {isAnalyzing ? "Analizando..." : "Ejecutar análisis SAMHIA"}
            </button>
          </div>

          <small style={{ marginTop: "12px", display: "block" }}>
            Se requieren al menos 12 datos válidos para el análisis SAMHIA completo.
          </small>
        </section>

        {/* Panel de resultados */}
        <section className="panel">
          <h2>2. Resultados del análisis</h2>
          
          {!analysisResults ? (
            <p>Carga datos y ejecuta el análisis para ver los resultados.</p>
          ) : (
            <>
              <div className="status-card" style={{ marginBottom: "18px" }}>
                <strong>Análisis completado</strong>
                <p>Variable: <strong>{analysisResults.series_name}</strong></p>
                <p>Embalse: <strong>{analysisResults.reservoir_name}</strong></p>
                <p>N de datos: <strong>{analysisResults.n_data}</strong></p>
              </div>

              {/* Tabs de resultados */}
              <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className={`tab-button ${activeTab === "analysis" ? "active" : ""}`}
                  onClick={() => setActiveTab("analysis")}
                  style={{ padding: "8px 16px", fontSize: "0.9rem" }}
                >
                  Estadísticas
                </button>
                <button
                  type="button"
                  className={`tab-button ${activeTab === "independence" ? "active" : ""}`}
                  onClick={() => setActiveTab("independence")}
                  style={{ padding: "8px 16px", fontSize: "0.9rem" }}
                >
                  Independencia
                </button>
                <button
                  type="button"
                  className={`tab-button ${activeTab === "homogeneity" ? "active" : ""}`}
                  onClick={() => setActiveTab("homogeneity")}
                  style={{ padding: "8px 16px", fontSize: "0.9rem" }}
                >
                  Homogeneidad
                </button>
                <button
                  type="button"
                  className={`tab-button ${activeTab === "trend" ? "active" : ""}`}
                  onClick={() => setActiveTab("trend")}
                  style={{ padding: "8px 16px", fontSize: "0.9rem" }}
                >
                  Tendencia
                </button>
                <button
                  type="button"
                  className={`tab-button ${activeTab === "outliers" ? "active" : ""}`}
                  onClick={() => setActiveTab("outliers")}
                  style={{ padding: "8px 16px", fontSize: "0.9rem" }}
                >
                  Atípicos
                </button>
              </div>

              {/* Contenido de tabs */}
              {activeTab === "analysis" && (
                <DescriptiveStatsPanel stats={analysisResults.descriptive_stats} />
              )}
              {activeTab === "independence" && (
                <TestResultsPanel 
                  title="Tests de Independencia"
                  tests={analysisResults.independence}
                  description="Evalúan si los datos son independientes (no autocorrelacionados)."
                />
              )}
              {activeTab === "homogeneity" && (
                <TestResultsPanel 
                  title="Tests de Homogeneidad"
                  tests={analysisResults.homogeneity}
                  description="Evalúan si la serie es homogénea a lo largo del tiempo."
                />
              )}
              {activeTab === "trend" && (
                <TestResultsPanel 
                  title="Tests de Tendencia"
                  tests={analysisResults.trend}
                  description="Evalúan si existe tendencia significativa en la serie."
                />
              )}
              {activeTab === "outliers" && (
                <OutliersPanel 
                  tests={analysisResults.outliers}
                />
              )}
            </>
          )}
        </section>
      </div>

      {analysisResults && (
        <section className="panel visualizations-section">
          <OutlierVisualizationsPanel
            plots={outlierPlots}
            plotsLoading={outlierPlotsLoading}
            plotsError={outlierPlotsError}
            onLoadPlots={fetchOutlierPlots}
          />
        </section>
      )}

      {/* Panel de generación de PDF */}
      <section className="panel">
        <h2>3. Generación de reporte PDF</h2>
        
        {!seriesValid ? (
          <p>Carga datos válidos para generar el reporte PDF.</p>
        ) : (
          <>
            <p>
              Genera un reporte PDF completo de 10 páginas con:
            </p>
            <ul style={{ marginLeft: "20px", marginBottom: "16px", color: "#e2e8f0" }}>
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
                disabled={isGeneratingPdf}
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
          </>
        )}
      </section>
    </div>
  );
}

// =============================================================================
// SUBCOMPONENTES
// =============================================================================

/**
 * Panel de estadísticas descriptivas.
 */
function DescriptiveStatsPanel({ stats }) {
  const statsData = [
    { label: "Mediana", value: stats.median.toFixed(4) },
    { label: "Media", value: stats.mean.toFixed(4) },
    { label: "1er Cuartil (Q25)", value: stats.q25.toFixed(4) },
    { label: "3er Cuartil (Q75)", value: stats.q75.toFixed(4) },
    { label: "Mínimo", value: stats.minimum.toFixed(4) },
    { label: "Máximo", value: stats.maximum.toFixed(4) },
    { label: "Asimetría (Skewness)", value: stats.skewness.toFixed(4) },
    { label: "Kurtosis", value: stats.kurtosis.toFixed(4) },
    { label: "Desv. Estándar", value: stats.std_dev.toFixed(4) },
    { label: "Varianza (n-1)", value: stats.variance.toFixed(4) },
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

/**
 * Panel de resultados de tests estadísticos.
 */
function TestResultsPanel({ title, tests, description }) {
  const testEntries = Object.entries(tests);

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
      
      {/* Detalles adicionales */}
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
            <p key={`detail-${key}`} style={{ fontSize: "0.85rem", color: "#cbd5e1", marginBottom: "4px" }}>
              <strong>{formatTestName(key)}:</strong> {detailText}
            </p>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Panel de análisis de outliers - solo tabla de resultados.
 * Los gráficos ahora se muestran en la sección de Visualizaciones.
 */
export function OutliersPanel({ tests }) {
  const testEntries = Object.entries(tests);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h4 style={{ margin: 0 }}>Detección de Atípicos</h4>
      </div>
      <p style={{ color: "#e2e8f0", marginBottom: "12px", fontSize: "0.9rem" }}>
        Identificación de valores atípicos usando métodos Chow y Kn.
        <br />
      </p>

      {/* Tabla de resultados */}
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
                <td>
                  {Array.isArray(result.critical_value)
                    ? `[${result.critical_value.map(v => v.toFixed(2)).join(', ')}]`
                    : typeof result.critical_value === 'number'
                      ? result.critical_value.toFixed(4)
                      : "N/A"}
                </td>
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
    </div>
  );
}

/**
 * Sección de gráficos generados para el análisis de atípicos.
 */
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
      <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", alignItems: "center", flexWrap: "wrap", marginBottom: "16px" }}>
        <div>
          <h2 style={{ marginBottom: "6px" }}>Visualizaciones del análisis SAMHIA</h2>
          <p style={{ color: "#e2e8f0", margin: 0, fontSize: "0.9rem" }}>
            Gráficos generados para la detección de valores atípicos.
          </p>
        </div>
        <button
          type="button"
          className="btn-load-plots"
          onClick={onLoadPlots}
          disabled={plotsLoading}
        >
          {plotsLoading ? "Generando gráficos..." : hasPlots ? "Actualizar gráficos" : "Generar gráficos"}
        </button>
      </div>

      {plotsError && <div className="error-banner" style={{ marginBottom: "12px" }}>{plotsError}</div>}

      {plotsLoading && (
        <div className="status-card">
          Generando visualizaciones del análisis...
        </div>
      )}

      {!plotsLoading && !hasPlots && !plotsError && (
        <p style={{ color: "#e2e8f0", margin: 0 }}>
          Usa el botón para generar los gráficos asociados al análisis.
        </p>
      )}

      {hasPlots && (
        <>
          {plots.outliers_detected !== undefined && (
            <div className="status-card" style={{ marginBottom: "16px" }}>
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
                      style={{ width: "100%", height: "auto", display: "block", borderRadius: "8px" }}
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

/**
 * Formatea nombres de tests para mostrar.
 */
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
