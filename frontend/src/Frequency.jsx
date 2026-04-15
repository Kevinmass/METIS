/**
 * Componente Frequency - Análisis de Frecuencia Hidrológica
 *
 * Este módulo implementa la UI para el análisis de frecuencia, permitiendo:
 *   - Ajuste de distribuciones de probabilidad a series hidrológicas
 *   - Visualización de parámetros y bondad de ajuste
 *   - Cálculo de eventos de diseño para períodos de retorno
 *
 * Integración con API:
 *   - POST /frequency/fit: Ajusta distribuciones a una serie
 *   - POST /frequency/design-event: Calcula evento de diseño
 *
 * @module Frequency
 */

import { useState, useMemo } from "react";

// =============================================================================
// CONSTANTES DE CONFIGURACIÓN
// =============================================================================

/** URL base de la API METIS */
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/** Métodos de estimación disponibles */
const ESTIMATION_METHODS = ["MOM", "MLE", "MEnt"];

/** Distribuciones disponibles para ajuste */
const AVAILABLE_DISTRIBUTIONS = [
  "Log-Pearson III",
  "Gumbel",
  "GEV",
  "Log-Normal",
  "Normal",
  "Pearson III",
];

// =============================================================================
// FUNCIONES DE UTILIDAD
// =============================================================================

/**
 * Convierte veredicto de bondad de ajuste a clase CSS.
 * @param {string} verdict - "ACCEPTED" o "REJECTED"
 * @returns {string} Clase CSS correspondiente
 */
const verdictLabel = (verdict) => {
  return verdict === "ACCEPTED" ? "accepted" : "rejected";
};

/**
 * Traduce veredicto a texto en español.
 * @param {string} verdict - Veredicto de la API
 * @returns {string} Texto localizado
 */
const statusText = (verdict) => {
  return verdict === "ACCEPTED" ? "Aceptado" : "Rechazado";
};

// =============================================================================
// COMPONENTE PRINCIPAL FREQUENCY
// =============================================================================

/**
 * Componente de análisis de frecuencia.
 *
 * @param {Object} props - Props del componente
 * @param {number[]} props.series - Serie de valores numéricos
 * @param {string} props.seriesId - Identificador de la serie
 * @returns {JSX.Element} Componente de análisis de frecuencia
 */
export default function Frequency({ series, seriesId }) {
  // ---------------------------------------------------------------------------
  // ESTADO DEL COMPONENTE
  // ---------------------------------------------------------------------------

  const [estimationMethod, setEstimationMethod] = useState("MOM");
  const [selectedDistributions, setSelectedDistributions] = useState(AVAILABLE_DISTRIBUTIONS);
  const [fitResults, setFitResults] = useState(null);
  const [fitError, setFitError] = useState("");
  const [isFitting, setIsFitting] = useState(false);

  // Estado para cálculo de evento de diseño
  const [selectedDistribution, setSelectedDistribution] = useState(null);
  const [returnPeriod, setReturnPeriod] = useState(100);
  const [designEvent, setDesignEvent] = useState(null);
  const [designError, setDesignError] = useState("");
  const [isCalculatingDesign, setIsCalculatingDesign] = useState(false);

  // ---------------------------------------------------------------------------
  // HANDLERS DE API
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
        // Seleccionar la distribución recomendada por defecto
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

  /**
   * Toggle selección de distribución para ajuste.
   */
  const toggleDistribution = (dist) => {
    setSelectedDistributions((prev) =>
      prev.includes(dist) ? prev.filter((d) => d !== dist) : [...prev, dist]
    );
  };

  // ---------------------------------------------------------------------------
  // RENDERIZADO
  // ---------------------------------------------------------------------------

  return (
    <div className="app-shell">
      <header className="page-header">
        <div>
          <h1>METIS — Análisis de Frecuencia</h1>
          <p>
            Ajusta distribuciones de probabilidad a tu serie hidrológica y calcula eventos de diseño
            para diferentes períodos de retorno.
          </p>
        </div>
      </header>

      <div className="section-grid">
        {/* Panel de configuración */}
        <section className="panel">
          <h2>1. Configuración del análisis</h2>
          <p>
            Serie: <strong>{seriesId || "serie_local"}</strong>
          </p>
          <p>
            N de datos: <strong>{series.length}</strong>
          </p>

          <div style={{ marginTop: "18px" }}>
            <label htmlFor="estimation-method">
              <strong>Método de estimación:</strong>
            </label>
            <select
              id="estimation-method"
              value={estimationMethod}
              onChange={(e) => setEstimationMethod(e.target.value)}
              style={{ marginTop: "8px" }}
            >
              {ESTIMATION_METHODS.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginTop: "18px" }}>
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

          <div className="button-group" style={{ marginTop: "18px" }}>
            <button
              type="button"
              className="button-primary"
              onClick={handleFit}
              disabled={isFitting || selectedDistributions.length === 0}
            >
              {isFitting ? "Ajustando..." : "Ajustar distribuciones"}
            </button>
          </div>
        </section>

        {/* Panel de resultados de ajuste */}
        <section className="panel">
          <h2>2. Resultados del ajuste</h2>
          {fitError ? <div className="error-banner">{fitError}</div> : null}

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

              <div className="chart-box" style={{ marginBottom: "18px" }}>
                <div className="chart-title">Comparación de Bondad de Ajuste</div>
                <GoodnessOfFitComparisonChart distributions={fitResults.distributions} />
              </div>

              <div className="chart-box" style={{ marginBottom: "18px" }}>
                <div className="chart-title">Ranking de Distribuciones</div>
                <DistributionRankingChart distributions={fitResults.distributions} />
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
        </section>
      </div>

      {/* Panel de evento de diseño */}
      <section className="panel">
        <h2>3. Cálculo de evento de diseño</h2>
        {!selectedDistribution ? (
          <p>Primero ajusta las distribuciones y selecciona una para calcular eventos de diseño.</p>
        ) : (
          <>
            <div style={{ display: "flex", gap: "18px", flexWrap: "wrap", alignItems: "flex-end" }}>
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

            {designError ? <div className="error-banner" style={{ marginTop: "18px" }}>{designError}</div> : null}

            {designEvent ? (
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
            ) : null}
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
 * Componente para mostrar resultado de ajuste de una distribución.
 */
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

          <div className="chart-box" style={{ marginBottom: "16px" }}>
            <div className="chart-title">Indicadores de Bondad de Ajuste</div>
            <GoodnessOfFitRadarChart goodnessOfFit={distribution.goodness_of_fit} />
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
                      <span className={`pill ${verdictLabel(distribution.goodness_of_fit.chi_square_verdict)}`}>
                        {statusText(distribution.goodness_of_fit.chi_square_verdict)}
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <th>Kolmogorov-Smirnov</th>
                    <td>{distribution.goodness_of_fit.ks_statistic.toFixed(4)}</td>
                    <td>
                      <span className={`pill ${verdictLabel(distribution.goodness_of_fit.ks_verdict)}`}>
                        {statusText(distribution.goodness_of_fit.ks_verdict)}
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <th>EEA</th>
                    <td>{distribution.goodness_of_fit.eea.toFixed(4)}</td>
                    <td>
                      <span className={`pill ${verdictLabel(distribution.goodness_of_fit.eea_verdict)}`}>
                        {statusText(distribution.goodness_of_fit.eea_verdict)}
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
// COMPONENTES DE GRÁFICOS
// =============================================================================

/**
 * Gráfico de comparación de bondad de ajuste para todas las distribuciones.
 * Muestra los tres indicadores (Chi Cuadrado, KS, EEA) como barras agrupadas.
 */
function GoodnessOfFitComparisonChart({ distributions }) {
  const width = 560;
  const height = 320;
  const padding = { top: 40, right: 20, bottom: 80, left: 60 };

  const metrics = [
    { key: "chi_square", label: "Chi²", color: "#60a5fa" },
    { key: "ks_statistic", label: "KS", color: "#f472b6" },
    { key: "eea", label: "EEA", color: "#34d399" },
  ];

  const allValues = distributions.flatMap((dist) =>
    metrics.map((m) => dist.goodness_of_fit[m.key])
  );
  const maxValue = Math.max(...allValues) * 1.1;
  const minValue = 0;

  const barWidth = (width - padding.left - padding.right) / distributions.length / metrics.length - 8;
  const groupWidth = (width - padding.left - padding.right) / distributions.length;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="100%">
      <rect x="0" y="0" width="100%" height="100%" fill="#08101f" />

      {/* Eje Y */}
      <line
        x1={padding.left}
        y1={padding.top}
        x2={padding.left}
        y2={height - padding.bottom}
        stroke="#334155"
        strokeWidth="2"
      />

      {/* Eje X */}
      <line
        x1={padding.left}
        y1={height - padding.bottom}
        x2={width - padding.right}
        y2={height - padding.bottom}
        stroke="#334155"
        strokeWidth="2"
      />

      {/* Líneas de grid y etiquetas Y */}
      {Array.from({ length: 5 }).map((_, i) => {
        const value = minValue + (maxValue - minValue) * (i / 4);
        const y = height - padding.bottom - (i / 4) * (height - padding.top - padding.bottom);
        return (
          <g key={i}>
            <line
              x1={padding.left}
              y1={y}
              x2={width - padding.right}
              y2={y}
              stroke="#1f2e47"
              strokeDasharray="4 4"
            />
            <text x={padding.left - 10} y={y + 4} fill="#94a3b8" fontSize="11" textAnchor="end">
              {value.toFixed(2)}
            </text>
          </g>
        );
      })}

      {/* Barras agrupadas por distribución */}
      {distributions.map((dist, distIndex) => {
    const groupX = padding.left + distIndex * groupWidth + groupWidth / 2;
    return (
      <g key={dist.distribution_name}>
        {metrics.map((metric, metricIndex) => {
          const value = dist.goodness_of_fit[metric.key];
          const barHeight = (value / maxValue) * (height - padding.top - padding.bottom);
          const x = groupX - (metrics.length * barWidth) / 2 + metricIndex * (barWidth + 8);
          const y = height - padding.bottom - barHeight;
          return (
            <g key={metric.key}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                fill={metric.color}
                opacity={dist.is_recommended ? 1 : 0.6}
                rx="4"
              />
              {dist.is_recommended && (
                <rect
                  x={x - 2}
                  y={y - 2}
                  width={barWidth + 4}
                  height={barHeight + 2}
                  fill="none"
                  stroke="#fbbf24"
                  strokeWidth="2"
                  rx="4"
                />
              )}
            </g>
          );
        })}
        {/* Etiqueta de distribución */}
        <text
          x={groupX}
          y={height - padding.bottom + 20}
          fill="#e2e8f0"
          fontSize="10"
          textAnchor="middle"
          fontWeight={dist.is_recommended ? "bold" : "normal"}
        >
          {dist.distribution_name.length > 12
            ? dist.distribution_name.substring(0, 10) + "..."
            : dist.distribution_name}
        </text>
      </g>
    );
  })}

      {/* Leyenda */}
      <g transform={`translate(${padding.left}, ${padding.top - 25})`}>
        {metrics.map((metric, i) => (
          <g key={metric.key} transform={`translate(${i * 80}, 0)`}>
            <rect width="16" height="16" fill={metric.color} rx="4" />
            <text x="22" y="13" fill="#cbd5e1" fontSize="12">
              {metric.label}
            </text>
          </g>
        ))}
      </g>
    </svg>
  );
}

/**
 * Gráfico de radar para mostrar los tres indicadores de bondad de ajuste.
 * Normaliza los valores para mostrar el rendimiento relativo.
 */
function GoodnessOfFitRadarChart({ goodnessOfFit }) {
  const size = 200;
  const center = size / 2;
  const radius = size / 2 - 30;

  const metrics = [
    { key: "chi_square", label: "Chi²" },
    { key: "ks_statistic", label: "KS" },
    { key: "eea", label: "EEA" },
  ];

  const values = metrics.map((m) => goodnessOfFit[m.key]);
  const maxValue = Math.max(...values) || 1;

  const points = metrics.map((m, i) => {
    const value = goodnessOfFit[m.key];
    const normalized = value / maxValue;
    const angle = (i * 2 * Math.PI) / metrics.length - Math.PI / 2;
    const x = center + normalized * radius * Math.cos(angle);
    const y = center + normalized * radius * Math.sin(angle);
    return { x, y, label: m.label, value };
  });

  const polygonPoints = points.map((p) => `${p.x},${p.y}`).join(" ");

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width="100%" height="100%">
      <rect x="0" y="0" width="100%" height="100%" fill="#08101f" />

      {/* Círculos de fondo */}
      {[0.25, 0.5, 0.75, 1].map((level) => (
        <circle
          key={level}
          cx={center}
          cy={center}
          r={radius * level}
          fill="none"
          stroke="#1f2e47"
          strokeWidth="1"
        />
      ))}

      {/* Líneas de los ejes */}
      {metrics.map((_, i) => {
        const angle = (i * 2 * Math.PI) / metrics.length - Math.PI / 2;
        const x = center + radius * Math.cos(angle);
        const y = center + radius * Math.sin(angle);
        return (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={x}
            y2={y}
            stroke="#1f2e47"
            strokeWidth="1"
          />
        );
      })}

      {/* Polígono de datos */}
      <polygon
        points={polygonPoints}
        fill="rgba(96, 165, 250, 0.3)"
        stroke="#60a5fa"
        strokeWidth="2"
      />

      {/* Puntos y etiquetas */}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="4" fill="#60a5fa" />
          <text
            x={p.x + (p.x - center) * 0.2}
            y={p.y + (p.y - center) * 0.2}
            fill="#cbd5e1"
            fontSize="10"
            textAnchor="middle"
          >
            {p.value.toFixed(3)}
          </text>
          <text
            x={center + (radius + 15) * Math.cos((i * 2 * Math.PI) / metrics.length - Math.PI / 2)}
            y={center + (radius + 15) * Math.sin((i * 2 * Math.PI) / metrics.length - Math.PI / 2)}
            fill="#94a3b8"
            fontSize="11"
            textAnchor="middle"
            dominantBaseline="middle"
          >
            {p.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

/**
 * Gráfico de ranking de distribuciones basado en el puntaje de bondad de ajuste.
 * Calcula un puntaje compuesto y muestra las distribuciones ordenadas.
 */
function DistributionRankingChart({ distributions }) {
  const width = 560;
  const height = 280;
  const padding = { top: 40, right: 120, bottom: 60, left: 140 };

  // Calcular puntaje compuesto (menor es mejor para estas métricas)
  const rankedDistributions = useMemo(
    () =>
      distributions
        .map((dist) => {
          const score =
            dist.goodness_of_fit.chi_square +
            dist.goodness_of_fit.ks_statistic +
            dist.goodness_of_fit.eea;
          return { ...dist, score };
        })
        .sort((a, b) => a.score - b.score),
    [distributions]
  );

  const maxScore = rankedDistributions[rankedDistributions.length - 1]?.score || 1;
  const minScore = rankedDistributions[0]?.score || 0;
  const scoreRange = maxScore - minScore || 1;

  const barHeight = (height - padding.top - padding.bottom) / rankedDistributions.length - 12;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="100%">
      <rect x="0" y="0" width="100%" height="100%" fill="#08101f" />

      {/* Eje Y */}
      <line
        x1={padding.left}
        y1={padding.top}
        x2={padding.left}
        y2={height - padding.bottom}
        stroke="#334155"
        strokeWidth="2"
      />

      {/* Eje X */}
      <line
        x1={padding.left}
        y1={height - padding.bottom}
        x2={width - padding.right}
        y2={height - padding.bottom}
        stroke="#334155"
        strokeWidth="2"
      />

      {/* Líneas de grid y etiquetas X */}
      {Array.from({ length: 5 }).map((_, i) => {
        const value = minScore + scoreRange * (i / 4);
        const x = padding.left + (i / 4) * (width - padding.left - padding.right);
        return (
          <g key={i}>
            <line
              x1={x}
              y1={padding.top}
              x2={x}
              y2={height - padding.bottom}
              stroke="#1f2e47"
              strokeDasharray="4 4"
            />
            <text x={x} y={height - padding.bottom + 20} fill="#94a3b8" fontSize="11" textAnchor="middle">
              {value.toFixed(2)}
            </text>
          </g>
        );
      })}

      {/* Barras horizontales */}
      {rankedDistributions.map((dist, i) => {
        const barWidth = ((dist.score - minScore) / scoreRange) * (width - padding.left - padding.right);
        const y = padding.top + i * (barHeight + 12);
        const isTop3 = i < 3;
        return (
          <g key={dist.distribution_name}>
            <rect
              x={padding.left}
              y={y}
              width={barWidth}
              height={barHeight}
              fill={isTop3 ? "#34d399" : dist.is_recommended ? "#60a5fa" : "#64748b"}
              opacity={dist.is_recommended ? 1 : 0.7}
              rx="6"
            />
            {dist.is_recommended && (
              <rect
                x={padding.left - 2}
                y={y - 2}
                width={barWidth + 2}
                height={barHeight + 4}
                fill="none"
                stroke="#fbbf24"
                strokeWidth="2"
                rx="6"
              />
            )}
            {/* Etiqueta de distribución */}
            <text
              x={padding.left - 10}
              y={y + barHeight / 2 + 4}
              fill="#e2e8f0"
              fontSize="11"
              textAnchor="end"
              fontWeight={dist.is_recommended ? "bold" : "normal"}
            >
              {dist.distribution_name}
            </text>
            {/* Valor del puntaje */}
            <text
              x={padding.left + barWidth + 10}
              y={y + barHeight / 2 + 4}
              fill="#cbd5e1"
              fontSize="11"
            >
              {dist.score.toFixed(3)}
            </text>
            {/* Ranking */}
            <text
              x={width - padding.right + 20}
              y={y + barHeight / 2 + 4}
              fill={isTop3 ? "#34d399" : "#94a3b8"}
              fontSize="12"
              fontWeight="bold"
            >
              #{i + 1}
            </text>
          </g>
        );
      })}

      {/* Etiqueta del eje X */}
      <text
        x={(width - padding.left - padding.right) / 2 + padding.left}
        y={height - 15}
        fill="#94a3b8"
        fontSize="12"
        textAnchor="middle"
      >
        Puntaje compuesto (menor es mejor)
      </text>
    </svg>
  );
}
