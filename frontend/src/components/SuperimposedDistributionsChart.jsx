/**
 * SuperimposedDistributionsChart
 *
 * Gráfico SVG que muestra TODAS las distribuciones ajustadas superpuestas
 * sobre un histograma de los datos reales. Permite mostrar/ocultar cada curva.
 *
 * @param {Object} props
 * @param {Array} props.distributions - Array de {distribution_name, parameters, is_recommended}
 * @param {number[]} props.seriesData - Datos reales de la serie
 */

import { useState, useMemo } from "react";

// Colores para cada distribución
const DIST_COLORS = {
  "Log-Pearson III": "#a78bfa",
  "Gumbel": "#f472b6",
  "GEV": "#34d399",
  "Log-Normal": "#60a5fa",
  "Normal": "#94a3b8",
  "Pearson III": "#fbbf24",
};

// Función gamma (Lanczos)
function gammaFunction(z) {
  if (z < 0.5) {
    return Math.PI / (Math.sin(Math.PI * z) * gammaFunction(1 - z));
  }
  const g = 7;
  const C = [
    0.99999999999980993, 676.5203681218851, -1259.1392167224028,
    771.32342877765313, -176.61502916214059, 12.507343278686905,
    -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7,
  ];
  z -= 1;
  let x = C[0];
  for (let i = 1; i < g + 2; i++) {
    x += C[i] / (z + i);
  }
  const t = z + g + 0.5;
  return Math.sqrt(2 * Math.PI) * Math.pow(t, z + 0.5) * Math.exp(-t) * x;
}

function calculatePDF(name, params, x) {
  switch (name) {
    case "Log-Normal": {
      if (x <= 0) return 0;
      const mu = params.mu ?? 0;
      const sigma = params.sigma ?? 1;
      const lnX = Math.log(x);
      return (1 / (x * sigma * Math.sqrt(2 * Math.PI))) *
        Math.exp(-Math.pow(lnX - mu, 2) / (2 * sigma * sigma));
    }
    case "Gumbel": {
      const xi = params.xi ?? 0;
      const alpha = params.alpha ?? 1;
      if (alpha <= 0) return 0;
      const z = (x - xi) / alpha;
      return (1 / alpha) * Math.exp(-(z + Math.exp(-z)));
    }
    case "GEV": {
      const xi = params.xi ?? 0;
      const alpha = params.alpha ?? 1;
      const k = params.k ?? 0;
      if (alpha <= 0) return 0;
      const z = (x - xi) / alpha;
      if (1 + k * z <= 0) return 0;
      const t = Math.pow(1 + k * z, -1 / k);
      return (1 / alpha) * Math.pow(t, k + 1) * Math.exp(-t);
    }
    case "Pearson III": {
      const mu = params.mu ?? params.location ?? 0;
      const sigma = params.sigma ?? params.scale ?? 1;
      const gamma = params.gamma ?? params.skew ?? 0;
      if (x <= 0 || sigma <= 0) return 0;
      const alpha = 4 / (gamma * gamma);
      const beta = (sigma * gamma) / 2;
      const x0 = mu - (2 * sigma) / gamma;
      if (x <= x0) return 0;
      const y = (x - x0) / beta;
      return (1 / (Math.abs(beta) * gammaFunction(alpha))) *
        Math.pow(y, alpha - 1) * Math.exp(-y);
    }
    case "Log-Pearson III": {
      const mu = params.mu ?? params.location ?? 0;
      const sigma = params.sigma ?? params.scale ?? 1;
      const gamma = params.gamma ?? params.skew ?? 0;
      if (x <= 0 || sigma <= 0) return 0;
      const lnX = Math.log(x);
      const alpha = 4 / (gamma * gamma);
      const beta = (sigma * gamma) / 2;
      const x0 = mu - (2 * sigma) / gamma;
      if (lnX <= x0) return 0;
      const y = (lnX - x0) / beta;
      return (1 / (x * Math.abs(beta) * gammaFunction(alpha))) *
        Math.pow(y, alpha - 1) * Math.exp(-y);
    }
    case "Normal": {
      const mu = params.mu ?? params.mean ?? 0;
      const sigma = params.sigma ?? params.std ?? 1;
      if (sigma <= 0) return 0;
      return (1 / (sigma * Math.sqrt(2 * Math.PI))) *
        Math.exp(-Math.pow(x - mu, 2) / (2 * sigma * sigma));
    }
    default:
      return 0;
  }
}

export default function SuperimposedDistributionsChart({ distributions, seriesData }) {
  const width = 800;
  const height = 380;
  const padding = { top: 30, right: 160, bottom: 50, left: 60 };

  const [hiddenDists, setHiddenDists] = useState(new Set());

  const toggleDist = (name) => {
    setHiddenDists((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const { chartData, histogramBins, globalMaxX, globalMaxY } = useMemo(() => {
    if (!distributions || distributions.length === 0 || !seriesData || seriesData.length === 0) {
      return { chartData: [], histogramBins: [], globalMaxX: 10, globalMaxY: 1 };
    }

    const finiteData = seriesData.filter((v) => Number.isFinite(v) && v > 0);
    if (finiteData.length === 0) {
      return { chartData: [], histogramBins: [], globalMaxX: 10, globalMaxY: 1 };
    }

    const dataMin = Math.min(...finiteData);
    const dataMax = Math.max(...finiteData);
    const range = dataMax - dataMin || 1;
    const xMin = Math.max(0, dataMin - range * 0.1);
    const xMax = dataMax + range * 0.4;

    // Calculate PDF for each distribution
    const numPoints = 200;
    const data = distributions.map((dist) => {
      const color = DIST_COLORS[dist.distribution_name] || "#60a5fa";
      const points = [];
      for (let i = 0; i <= numPoints; i++) {
        const x = xMin + ((xMax - xMin) * i) / numPoints;
        const y = calculatePDF(dist.distribution_name, dist.parameters, x);
        points.push({ x, y });
      }
      return {
        name: dist.distribution_name,
        color,
        isRecommended: dist.is_recommended,
        points,
      };
    });

    // Histogram
    const numBins = Math.min(20, Math.max(5, Math.floor(Math.sqrt(finiteData.length))));
    const binWidth = (xMax - xMin) / numBins;
    const bins = [];
    for (let i = 0; i < numBins; i++) {
      const binStart = xMin + i * binWidth;
      const binEnd = binStart + binWidth;
      const count = finiteData.filter((v) => v >= binStart && v < binEnd).length;
      const density = count / (finiteData.length * binWidth);
      bins.push({ x: binStart + binWidth / 2, density, width: binWidth });
    }

    const allY = [
      ...data.flatMap((d) => d.points.map((p) => p.y)),
      ...bins.map((b) => b.density),
    ];
    const maxY = Math.max(...allY, 0.01) * 1.15;

    return {
      chartData: data,
      histogramBins: bins,
      globalMaxX: xMax,
      globalMaxY: maxY,
    };
  }, [distributions, seriesData]);

  const xScale = (x) =>
    padding.left + (x / globalMaxX) * (width - padding.left - padding.right);
  const yScale = (y) =>
    height - padding.bottom - (y / globalMaxY) * (height - padding.top - padding.bottom);

  const generatePath = (points) => {
    if (points.length === 0) return "";
    return points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.x).toFixed(2)} ${yScale(p.y).toFixed(2)}`)
      .join(" ");
  };

  return (
    <div className="distribution-chart-box">
      <div className="chart-label" style={{ marginBottom: "12px", fontSize: "13px", fontWeight: 600 }}>
        Comparación de Distribuciones Ajustadas
      </div>

      {/* Toggle buttons */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "12px", justifyContent: "center" }}>
        {chartData.map((dist) => (
          <button
            key={dist.name}
            onClick={() => toggleDist(dist.name)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              borderRadius: "6px",
              border: `1px solid ${hiddenDists.has(dist.name) ? "var(--border)" : dist.color}`,
              background: hiddenDists.has(dist.name) ? "transparent" : `${dist.color}15`,
              color: hiddenDists.has(dist.name) ? "var(--fg-muted)" : dist.color,
              fontSize: "11px",
              cursor: "pointer",
              transition: "all 0.2s ease",
              opacity: hiddenDists.has(dist.name) ? 0.5 : 1,
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: dist.color, opacity: hiddenDists.has(dist.name) ? 0.3 : 1 }} />
            {dist.name}
            {dist.isRecommended && <span style={{ fontSize: "9px" }}>★</span>}
          </button>
        ))}
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="380">
        {/* Background */}
        <rect x="0" y="0" width={width} height={height} fill="#0a0f1a" rx="8" />

        {/* Grid */}
        {[0.25, 0.5, 0.75, 1].map((level) => (
          <line
            key={`h-${level}`}
            x1={padding.left}
            y1={yScale(globalMaxY * level)}
            x2={width - padding.right}
            y2={yScale(globalMaxY * level)}
            stroke="#1f2e47"
            strokeDasharray="3 3"
          />
        ))}

        {/* Axes */}
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke="#475569" strokeWidth="1.5" />
        <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} stroke="#475569" strokeWidth="1.5" />

        {/* Histogram */}
        {histogramBins.map((bin, i) => {
          const barX = xScale(bin.x - bin.width / 2);
          const barW = xScale(bin.x + bin.width / 2) - barX;
          const barH = (bin.density / globalMaxY) * (height - padding.top - padding.bottom);
          return (
            <rect
              key={`bin-${i}`}
              x={barX}
              y={height - padding.bottom - barH}
              width={Math.max(0, barW - 1)}
              height={barH}
              fill="rgba(148, 163, 184, 0.15)"
              stroke="rgba(148, 163, 184, 0.25)"
              strokeWidth="0.5"
              rx="1"
            />
          );
        })}

        {/* Distribution curves */}
        {chartData.map((dist) => {
          if (hiddenDists.has(dist.name)) return null;
          const path = generatePath(dist.points);
          return (
            <g key={dist.name}>
              <path
                d={path}
                fill="none"
                stroke={dist.color}
                strokeWidth={dist.isRecommended ? 3 : 2}
                strokeLinecap="round"
                opacity={dist.isRecommended ? 1 : 0.8}
              />
            </g>
          );
        })}

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((level) => (
          <text
            key={`yl-${level}`}
            x={padding.left - 8}
            y={yScale(globalMaxY * level) + 3}
            fill="#64748b"
            fontSize="10"
            textAnchor="end"
          >
            {(globalMaxY * level).toFixed(3)}
          </text>
        ))}

        {/* X-axis labels */}
        {Array.from({ length: 6 }).map((_, i) => {
          const x = (globalMaxX * i) / 5;
          return (
            <text
              key={`xl-${i}`}
              x={xScale(x)}
              y={height - padding.bottom + 18}
              fill="#64748b"
              fontSize="10"
              textAnchor="middle"
            >
              {x.toFixed(0)}
            </text>
          );
        })}

        {/* Axis labels */}
        <text
          x={(width - padding.left - padding.right) / 2 + padding.left}
          y={height - 8}
          fill="#94a3b8"
          fontSize="11"
          textAnchor="middle"
        >
          Valor de la variable
        </text>
        <text
          x={14}
          y={(height - padding.top - padding.bottom) / 2 + padding.top}
          fill="#94a3b8"
          fontSize="11"
          textAnchor="middle"
          transform={`rotate(-90, 14, ${(height - padding.top - padding.bottom) / 2 + padding.top})`}
        >
          Densidad de probabilidad f(x)
        </text>

        {/* Legend */}
        <g transform={`translate(${width - padding.right + 16}, ${padding.top})`}>
          <rect x="-8" y="-8" width="140" height={chartData.length * 22 + 16} fill="#0f172a" stroke="#1f2e47" rx="6" />
          {chartData.map((dist, i) => {
            const isHidden = hiddenDists.has(dist.name);
            return (
              <g key={`legend-${dist.name}`} transform={`translate(0, ${i * 22})`} opacity={isHidden ? 0.3 : 1}>
                <line x1="0" y1="8" x2="18" y2="8" stroke={dist.color} strokeWidth={dist.isRecommended ? 3 : 2} />
                <text x="24" y="12" fill="#e2e8f0" fontSize="10" fontWeight={dist.isRecommended ? "bold" : "normal"}>
                  {dist.name}{dist.isRecommended ? " ★" : ""}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}