import { useMemo, useState } from "react";
import * as XLSX from "xlsx";

const API_BASE = "http://127.0.0.1:8000";
const MAX_LAG = 10;

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

const statusText = (verdict) => {
  if (verdict === "ACCEPTED") return "Aceptado";
  if (verdict === "REJECTED") return "Rechazado";
  return "Inconcluso";
};

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

function serieToCsv(series) {
  return series.map((value) => value.toString()).join("\n");
}

export default function App() {
  const [series, setSeries] = useState([0, 0, 0]);
  const [seriesId, setSeriesId] = useState("serie_local");
  const [fetchError, setFetchError] = useState("");
  const [fileError, setFileError] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [isSending, setIsSending] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const warnings = useMemo(() => buildWarnings(series), [series]);
  const seriesValid = series.length >= 3 && series.every((value) => !Number.isNaN(value));

  const autoCorrelation = useMemo(
    () => computeAutoCorrelation(series.filter((value) => Number.isFinite(value))),
    [series]
  );

  const band = series.length > 0 ? 1.96 / Math.sqrt(series.length) : 0;

  const updateByIndex = (index, value) => {
    const next = [...series];
    next[index] = value;
    setSeries(next);
  };

  const addRow = () => setSeries((prev) => [...prev, 0]);
  const removeRow = (index) => setSeries((prev) => prev.filter((_, i) => i !== index));

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
        "No se pudo conectar con el backend. Asegúrate de que FastAPI esté activo en http://127.0.0.1:8000"
      );
      setAnalysis(null);
    } finally {
      setIsSending(false);
    }
  };

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

  const displayValue = (value) => {
    return Number.isFinite(value) ? value : 0;
  };

  return (
    <div className="app-shell">
      <header className="page-header">
        <div>
          <h1>METIS — Validación Hidrológica</h1>
          <p>
            Carga una serie, valida su calidad estadística y revisa los resultados de independencia,
            homogeneidad, tendencia y atípicos.
          </p>
        </div>
      </header>

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
