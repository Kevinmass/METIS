/**
 * DistributionPDFChart
 *
 * Gráfico SVG que muestra la función de densidad de probabilidad (PDF)
 * de una distribución junto con el histograma de los datos reales.
 * Reutiliza la matemática de PDF de AsymmetricDistributionsChart.
 *
 * @param {Object} props
 * @param {string} props.distributionName - Nombre de la distribución
 * @param {Object} props.parameters - Parámetros de la distribución ajustada
 * @param {number[]} props.seriesData - Datos reales de la serie
 * @param {string} [props.color] - Color de la curva (default: '#60a5fa')
 */

import { useMemo } from "react";

// Función gamma (Lanczos) - reutilizada de AsymmetricDistributionsChart
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

/**
 * Calcula la PDF para una distribución dada en el punto x.
 */
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

export default function DistributionPDFChart({ distributionName, parameters, seriesData, color = "#60a5fa" }) {
  const width = 600;
  const height = 260;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };

  const { pdfPoints, histogramBins, maxX, maxY } = useMemo(() => {
    if (!seriesData || seriesData.length === 0 || !parameters) {
      return { pdfPoints: [], histogramBins: [], maxX: 10, maxY: 1 };
    }

    const finiteData = seriesData.filter((v) => Number.isFinite(v) && v > 0);
    if (finiteData.length === 0) {
      return { pdfPoints: [], histogramBins: [], maxX: 10, maxY: 1 };
    }

    const dataMin = Math.min(...finiteData);
    const dataMax = Math.max(...finiteData);
    const range = dataMax - dataMin || 1;
    const xMin = Math.max(0, dataMin - range * 0.1);
    const xMax = dataMax + range * 0.3;

    // Calculate PDF points
    const numPoints = 200;
    const points = [];
    for (let i = 0; i <= numPoints; i++) {
      const x = xMin + ((xMax - xMin) * i) / numPoints;
      const y = calculatePDF(distributionName, parameters, x);
      points.push({ x, y });
    }

    // Calculate histogram bins
    const numBins = Math.min(20, Math.max(5, Math.floor(Math.sqrt(finiteData.length))));
    const binWidth = (xMax - xMin) / numBins;
    const bins = [];
    for (let i = 0; i < numBins; i++) {
      const binStart = xMin + i * binWidth;
      const binEnd = binStart + binWidth;
      const count = finiteData.filter((v) => v >= binStart && v < binEnd).length;
      // Normalize: density = count / (total * binWidth)
      const density = count / (finiteData.length * binWidth);
      bins.push({ x: binStart + binWidth / 2, density, width: binWidth });
    }

    const currentMaxY = Math.max(
      ...points.map((p) => p.y),
      ...bins.map((b) => b.density),
      0.01
    );

    return {
      pdfPoints: points,
      histogramBins: bins,
      maxX: xMax,
      maxY: currentMaxY * 1.15,
    };
  }, [distributionName, parameters, seriesData]);

  // Scale functions
  const xScale = (x) =>
    padding.left + (x / maxX) * (width - padding.left - padding.right);
  const yScale = (y) =>
    height - padding.bottom - (y / maxY) * (height - padding.top - padding.bottom);

  // Generate PDF path
  const pdfPath = pdfPoints
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.x).toFixed(2)} ${yScale(p.y).toFixed(2)}`)
    .join(" ");

  // Fill area under curve
  const pdfFill = pdfPath +
    ` L ${xScale(pdfPoints[pdfPoints.length - 1]?.x || 0).toFixed(2)} ${height - padding.bottom}` +
    ` L ${xScale(0).toFixed(2)} ${height - padding.bottom} Z`;

  return (
    <div className="distribution-chart-box">
      <div className="chart-label">PDF — {distributionName}</div>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="260">
        {/* Background */}
        <rect x="0" y="0" width={width} height={height} fill="#0a0f1a" rx="8" />

        {/* Grid lines */}
        {[0.25, 0.5, 0.75, 1].map((level) => (
          <line
            key={`h-${level}`}
            x1={padding.left}
            y1={yScale(maxY * level)}
            x2={width - padding.right}
            y2={yScale(maxY * level)}
            stroke="#1f2e47"
            strokeDasharray="3 3"
          />
        ))}

        {/* Axes */}
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke="#475569" strokeWidth="1.5" />
        <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} stroke="#475569" strokeWidth="1.5" />

        {/* Histogram bars */}
        {histogramBins.map((bin, i) => {
          const barX = xScale(bin.x - bin.width / 2);
          const barW = xScale(bin.x + bin.width / 2) - barX;
          const barH = (bin.density / maxY) * (height - padding.top - padding.bottom);
          return (
            <rect
              key={`bin-${i}`}
              x={barX}
              y={height - padding.bottom - barH}
              width={Math.max(0, barW - 1)}
              height={barH}
              fill="rgba(148, 163, 184, 0.2)"
              stroke="rgba(148, 163, 184, 0.3)"
              strokeWidth="0.5"
              rx="1"
            />
          );
        })}

        {/* PDF fill area */}
        <path d={pdfFill} fill={`${color}15`} />

        {/* PDF curve */}
        <path d={pdfPath} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" />

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((level) => (
          <text
            key={`yl-${level}`}
            x={padding.left - 6}
            y={yScale(maxY * level) + 3}
            fill="#64748b"
            fontSize="9"
            textAnchor="end"
          >
            {(maxY * level).toFixed(2)}
          </text>
        ))}

        {/* X-axis label */}
        <text
          x={(width - padding.left - padding.right) / 2 + padding.left}
          y={height - 8}
          fill="#94a3b8"
          fontSize="10"
          textAnchor="middle"
        >
          Valor
        </text>

        {/* Y-axis label */}
        <text
          x={12}
          y={(height - padding.top - padding.bottom) / 2 + padding.top}
          fill="#94a3b8"
          fontSize="10"
          textAnchor="middle"
          transform={`rotate(-90, 12, ${(height - padding.top - padding.bottom) / 2 + padding.top})`}
        >
          Densidad
        </text>
      </svg>
    </div>
  );
}