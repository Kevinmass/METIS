/**
 * Componente AsymmetricDistributionsChart
 *
 * Visualiza las funciones de densidad de probabilidad (PDF) de las distribuciones
 * asimétricas utilizadas en el análisis de frecuencia hidrológica.
 *
 * Cada curva muestra la forma característica de la distribución con parámetros
 * de ejemplo representativos para contextos hidrológicos.
 */

import { useState } from "react";

// Configuración de distribuciones asimétricas con parámetros de ejemplo
const DISTRIBUTIONS_CONFIG = [
  {
    name: "Log-Normal",
    color: "#60a5fa",
    params: { mu: 0, sigma: 0.5 },
    description: "Asimetría positiva moderada",
    range: [0.1, 8],
  },
  {
    name: "Gumbel",
    color: "#f472b6",
    params: { xi: 2, alpha: 1 },
    description: "Para máximos anuales",
    range: [-1, 8],
  },
  {
    name: "GEV",
    color: "#34d399",
    params: { xi: 2, alpha: 1, k: 0.2 },
    description: "Generalización flexible",
    range: [-1, 8],
  },
  {
    name: "Pearson III",
    color: "#fbbf24",
    params: { mu: 3, sigma: 1.5, gamma: 1.2 },
    description: "Gamma con locación",
    range: [0, 8],
  },
  {
    name: "Log-Pearson III",
    color: "#a78bfa",
    params: { mu: 1, sigma: 0.8, gamma: 0.5 },
    description: "Estándar USGS",
    range: [0.1, 10],
  },
  {
    name: "Gamma",
    color: "#f87171",
    params: { shape: 2, scale: 1.5 },
    description: "Eventos positivos",
    range: [0.1, 10],
  },
  {
    name: "Weibull",
    color: "#22d3ee",
    params: { c: 1.5, loc: 0, scale: 2 },
    description: "Versátil para extremos",
    range: [0, 8],
  },
  {
    name: "Log-Logistic",
    color: "#fb923c",
    params: { mu: 1, sigma: 0.5 },
    description: "Colas pesadas",
    range: [0.1, 10],
  },
  {
    name: "Pareto",
    color: "#c084fc",
    params: { xm: 1, alpha: 2 },
    description: "Eventos extremos",
    range: [1, 8],
  },
  {
    name: "Exponencial",
    color: "#4ade80",
    params: { scale: 2 },
    description: "Procesos de Poisson",
    range: [0, 8],
  },
];

// Funciones PDF para cada distribución
function calculatePDF(distribution, x) {
  switch (distribution.name) {
    case "Log-Normal": {
      const { mu, sigma } = distribution.params;
      if (x <= 0) return 0;
      const lnX = Math.log(x);
      return (
        (1 / (x * sigma * Math.sqrt(2 * Math.PI))) *
        Math.exp(-Math.pow(lnX - mu, 2) / (2 * sigma * sigma))
      );
    }
    case "Gumbel": {
      const { xi, alpha } = distribution.params;
      const z = (x - xi) / alpha;
      return (1 / alpha) * Math.exp(-(z + Math.exp(-z)));
    }
    case "GEV": {
      const { xi, alpha, k } = distribution.params;
      const z = (x - xi) / alpha;
      if (1 + k * z <= 0) return 0;
      const t = Math.pow(1 + k * z, -1 / k);
      return (1 / alpha) * Math.pow(t, k + 1) * Math.exp(-t);
    }
    case "Pearson III": {
      const { mu, sigma, gamma } = distribution.params;
      if (x <= 0) return 0;
      const alpha = 4 / (gamma * gamma);
      const beta = sigma * gamma / 2;
      const x0 = mu - 2 * sigma / gamma;
      if (x <= x0) return 0;
      const y = (x - x0) / beta;
      return (
        (1 / (Math.abs(beta) * gammaFunction(alpha))) *
        Math.pow(y, alpha - 1) *
        Math.exp(-y)
      );
    }
    case "Log-Pearson III": {
      const { mu, sigma, gamma } = distribution.params;
      if (x <= 0) return 0;
      const lnX = Math.log(x);
      const alpha = 4 / (gamma * gamma);
      const beta = sigma * gamma / 2;
      const x0 = mu - 2 * sigma / gamma;
      if (lnX <= x0) return 0;
      const y = (lnX - x0) / beta;
      return (
        (1 / (x * Math.abs(beta) * gammaFunction(alpha))) *
        Math.pow(y, alpha - 1) *
        Math.exp(-y)
      );
    }
    case "Gamma": {
      const { shape, scale } = distribution.params;
      if (x <= 0) return 0;
      return (
        (1 / (Math.pow(scale, shape) * gammaFunction(shape))) *
        Math.pow(x, shape - 1) *
        Math.exp(-x / scale)
      );
    }
    case "Weibull": {
      const { c, loc, scale } = distribution.params;
      if (x <= loc) return 0;
      const z = (x - loc) / scale;
      return (c / scale) * Math.pow(z, c - 1) * Math.exp(-Math.pow(z, c));
    }
    case "Log-Logistic": {
      const { mu, sigma } = distribution.params;
      if (x <= 0) return 0;
      const lnX = Math.log(x);
      const z = (lnX - mu) / sigma;
      const expZ = Math.exp(-z);
      return (1 / (x * sigma)) * (expZ / Math.pow(1 + expZ, 2));
    }
    case "Pareto": {
      const { xm, alpha } = distribution.params;
      if (x < xm) return 0;
      return (alpha * Math.pow(xm, alpha)) / Math.pow(x, alpha + 1);
    }
    case "Exponencial": {
      const { scale } = distribution.params;
      if (x < 0) return 0;
      return (1 / scale) * Math.exp(-x / scale);
    }
    default:
      return 0;
  }
}

// Aproximación de la función gamma usando Lanczos
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

export default function AsymmetricDistributionsChart() {
  const [selectedDistributions, setSelectedDistributions] = useState(
    DISTRIBUTIONS_CONFIG.map((d) => d.name)
  );
  const [hoveredDist, setHoveredDist] = useState(null);

  const toggleDistribution = (name) => {
    setSelectedDistributions((prev) =>
      prev.includes(name)
        ? prev.filter((n) => n !== name)
        : [...prev, name]
    );
  };

  const width = 800;
  const height = 400;
  const padding = { top: 40, right: 200, bottom: 60, left: 60 };

  // Calcular puntos para todas las distribuciones seleccionadas
  const chartData = selectedDistributions.map((name) => {
    const dist = DISTRIBUTIONS_CONFIG.find((d) => d.name === name);
    if (!dist) return null;

    const [minX, maxX] = dist.range;
    const points = [];
    const numPoints = 200;

    for (let i = 0; i <= numPoints; i++) {
      const x = minX + (maxX - minX) * (i / numPoints);
      const y = calculatePDF(dist, x);
      points.push({ x, y });
    }

    return { ...dist, points };
  }).filter(Boolean);

  // Encontrar máximo Y para escalar
  const maxY = Math.max(
    ...chartData.flatMap((d) => d.points.map((p) => p.y)),
    0.5
  );

  // Escalar puntos a coordenadas SVG
  const xScale = (x) =>
    padding.left +
    ((x - 0) / (10 - 0)) * (width - padding.left - padding.right);
  const yScale = (y) =>
    height - padding.bottom - (y / maxY) * (height - padding.top - padding.bottom);

  // Generar path SVG
  const generatePath = (points) => {
    if (points.length === 0) return "";
    return points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.x)} ${yScale(p.y)}`)
      .join(" ");
  };

  return (
    <div className="asymmetric-chart-container">
      {/* Panel de control de distribuciones */}
      <div className="distribution-toggles">
        {DISTRIBUTIONS_CONFIG.map((dist) => (
          <button
            key={dist.name}
            className={`dist-toggle ${
              selectedDistributions.includes(dist.name) ? "active" : ""
            }`}
            onClick={() => toggleDistribution(dist.name)}
            onMouseEnter={() => setHoveredDist(dist.name)}
            onMouseLeave={() => setHoveredDist(null)}
            style={{
              borderColor: dist.color,
              backgroundColor: selectedDistributions.includes(dist.name)
                ? `${dist.color}20`
                : "transparent",
            }}
          >
            <span
              className="color-indicator"
              style={{ backgroundColor: dist.color }}
            />
            <span className="dist-name">{dist.name}</span>
          </button>
        ))}
      </div>

      {/* Gráfico SVG */}
      <div className="chart-wrapper">
        <svg viewBox={`0 0 ${width} ${height}`} className="pdf-chart">
          {/* Fondo */}
          <rect
            x="0"
            y="0"
            width={width}
            height={height}
            fill="#0a0f1a"
            rx="8"
          />

          {/* Grid */}
          {Array.from({ length: 6 }).map((_, i) => {
            const y = padding.top + (i / 5) * (height - padding.top - padding.bottom);
            return (
              <g key={`h-${i}`}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke="#1f2e47"
                  strokeDasharray="4 4"
                />
              </g>
            );
          })}
          {Array.from({ length: 11 }).map((_, i) => {
            const x = padding.left + (i / 10) * (width - padding.left - padding.right);
            return (
              <g key={`v-${i}`}>
                <line
                  x1={x}
                  y1={padding.top}
                  x2={x}
                  y2={height - padding.bottom}
                  stroke="#1f2e47"
                  strokeDasharray="4 4"
                />
              </g>
            );
          })}

          {/* Ejes */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={height - padding.bottom}
            stroke="#475569"
            strokeWidth="2"
          />
          <line
            x1={padding.left}
            y1={height - padding.bottom}
            x2={width - padding.right}
            y2={height - padding.bottom}
            stroke="#475569"
            strokeWidth="2"
          />

          {/* Etiquetas de ejes */}
          <text
            x={padding.left - 10}
            y={padding.top - 10}
            fill="#94a3b8"
            fontSize="11"
            textAnchor="end"
          >
            Densidad f(x)
          </text>
          <text
            x={(width - padding.left - padding.right) / 2 + padding.left}
            y={height - 20}
            fill="#94a3b8"
            fontSize="11"
            textAnchor="middle"
          >
            Valor x
          </text>

          {/* Marcas de eje Y */}
          {Array.from({ length: 6 }).map((_, i) => {
            const value = maxY * (1 - i / 5);
            const y = padding.top + (i / 5) * (height - padding.top - padding.bottom);
            return (
              <text
                key={`yl-${i}`}
                x={padding.left - 10}
                y={y + 4}
                fill="#64748b"
                fontSize="10"
                textAnchor="end"
              >
                {value.toFixed(2)}
              </text>
            );
          })}

          {/* Marcas de eje X */}
          {Array.from({ length: 11 }).map((_, i) => {
            const value = i;
            const x = padding.left + (i / 10) * (width - padding.left - padding.right);
            return (
              <text
                key={`xl-${i}`}
                x={x}
                y={height - padding.bottom + 20}
                fill="#64748b"
                fontSize="10"
                textAnchor="middle"
              >
                {value}
              </text>
            );
          })}

          {/* Curvas de distribución */}
          {chartData.map((dist) => (
            <g key={dist.name}>
              <path
                d={generatePath(dist.points)}
                fill="none"
                stroke={dist.color}
                strokeWidth={hoveredDist === dist.name ? 4 : 2}
                opacity={hoveredDist && hoveredDist !== dist.name ? 0.3 : 1}
              />
              {/* Punto máximo */}
              {(() => {
                const maxPoint = dist.points.reduce((max, p) =>
                  p.y > max.y ? p : max
                );
                return (
                  <circle
                    cx={xScale(maxPoint.x)}
                    cy={yScale(maxPoint.y)}
                    r="4"
                    fill={dist.color}
                    opacity={hoveredDist && hoveredDist !== dist.name ? 0.3 : 1}
                  />
                );
              })()}
            </g>
          ))}

          {/* Leyenda */}
          <g transform={`translate(${width - padding.right + 20}, ${padding.top})`}>
            <rect
              x="-10"
              y="-10"
              width="170"
              height={chartData.length * 25 + 20}
              fill="#0f172a"
              stroke="#1f2e47"
              rx="6"
            />
            {chartData.map((dist, i) => (
              <g
                key={`legend-${dist.name}`}
                transform={`translate(0, ${i * 25})`}
                opacity={hoveredDist && hoveredDist !== dist.name ? 0.3 : 1}
              >
                <line
                  x1="0"
                  y1="8"
                  x2="20"
                  y2="8"
                  stroke={dist.color}
                  strokeWidth="2"
                />
                <text
                  x="28"
                  y="12"
                  fill="#e2e8f0"
                  fontSize="11"
                  fontWeight={hoveredDist === dist.name ? "bold" : "normal"}
                >
                  {dist.name}
                </text>
              </g>
            ))}
          </g>
        </svg>
      </div>

      {/* Información de distribución hovered */}
      {hoveredDist && (
        <div className="dist-info-panel">
          {(() => {
            const dist = DISTRIBUTIONS_CONFIG.find((d) => d.name === hoveredDist);
            return dist ? (
              <>
                <h4 style={{ color: dist.color }}>{dist.name}</h4>
                <p className="dist-description">{dist.description}</p>
                <div className="dist-params">
                  <strong>Parámetros:</strong>
                  <code>{JSON.stringify(dist.params).replace(/[{}"]/g, "")}</code>
                </div>
              </>
            ) : null;
          })()}
        </div>
      )}
    </div>
  );
}
