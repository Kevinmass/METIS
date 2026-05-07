/**
 * Componente FrequencyTheoryInfo
 *
 * Proporciona información teórica detallada sobre el análisis de frecuencia
 * hidrológica, incluyendo explicaciones de distribuciones, métricas de bondad
 * de ajuste, parámetros y eventos de diseño.
 */

import { useState } from "react";

const SECTIONS = [
  {
    id: "distributions",
    title: "📊 Distribuciones de Probabilidad",
    icon: "📈",
    content: [
      {
        name: "Log-Normal",
        description: "Distribución donde el logaritmo de la variable sigue una distribución normal.",
        usage: "Ideal para caudales medios a grandes donde existe asimetría positiva moderada.",
        characteristics: ["Asimetría positiva", "Solo valores positivos", "Cola derecha extendida"],
      },
      {
        name: "Gumbel (EVI)",
        description: "Distribución de valores extremos tipo I. Modela máximos de variables con cola exponencial.",
        usage: "Recomendada para máximos anuales de caudales cuando la muestra es limitada.",
        characteristics: ["Forma fija (no tiene parámetro de forma)", "Asimétrica hacia la derecha", "Límitada inferiormente"],
      },
      {
        name: "GEV (Valores Extremos Generalizados)",
        description: "Generalización que incluye Gumbel, Fréchet y Weibull para máximos.",
        usage: "Muy flexible para diferentes tipos de comportamiento en colas. Recomendada para estudios detallados.",
        characteristics: ["Tres parámetros (ubicación, escala, forma)", "Puede modelar colas pesadas o ligeras", "Versátil"],
      },
      {
        name: "Pearson III",
        description: "Distribución gamma con tres parámetros incluyendo ubicación.",
        usage: "Utilizada por el Servicio Geológico de EE.UU. para análisis de frecuencia de caudales.",
        characteristics: ["Tres parámetros", "Flexible para diferentes formas", "Soporta asimetría variable"],
      },
      {
        name: "Log-Pearson III",
        description: "Transformación logarítmica de Pearson III. Estándar en hidrología de EE.UU.",
        usage: "Estándar recomendado por USGS para análisis de frecuencia de caudales máximos.",
        characteristics: ["Estándar internacional", "Maneja bien series con alta variabilidad", "Asimetría positiva"],
      },
      {
        name: "Gamma",
        description: "Distribución de dos parámetros para variables continuas positivas.",
        usage: "Adecuada para precipitaciones y caudales donde todos los valores son positivos.",
        characteristics: ["Dos parámetros (forma y escala)", "Definida solo para x > 0", "Familia de formas flexible"],
      },
      {
        name: "Weibull",
        description: "Distribución versátil usada para modelar fenómenos de extremos.",
        usage: "Frecuente en análisis de viento, materiales y confiabilidad. También aplicable a caudales.",
        characteristics: ["Tres parámetros", "Puede modelar diferentes tipos de falla", "Forma variable según parámetro de forma"],
      },
      {
        name: "Log-Logistic",
        description: "Distribución con colas más pesadas que la log-normal.",
        usage: "Útil cuando se esperan eventos extremos más frecuentes que lo predicho por log-normal.",
        characteristics: ["Colas pesadas", "Similar a log-normal pero más robusta", "Buena para eventos extremos"],
      },
      {
        name: "Pareto",
        description: "Distribución power-law para modelar eventos extremos.",
        usage: "Aplicaciones en seguros, riesgos financieros y eventos hidrológicos extremos.",
        characteristics: ["Cola muy pesada", "Ley de potencias", "Enfocada en extremos"],
      },
      {
        name: "Exponencial",
        description: "Distribución de tiempos entre eventos en procesos de Poisson.",
        usage: "Modela tiempos de espera entre eventos independientes. Menos común para caudales máximos.",
        characteristics: ["Sin memoria", "Un solo parámetro", "Cola exponencial"],
      },
    ],
  },
  {
    id: "metrics",
    title: "📏 Métricas de Bondad de Ajuste",
    icon: "✅",
    content: [
      {
        name: "Chi Cuadrado (χ²)",
        description: "Prueba estadística que compara las frecuencias observadas con las esperadas teóricamente.",
        interpretation: [
          "Valor p > 0.05: No se rechaza la hipótesis de ajuste (ACEPTADO)",
          "Valor p ≤ 0.05: Se rechaza la hipótesis de ajuste (RECHAZADO)",
          "Valores menores de estadístico χ² indican mejor ajuste",
        ],
        notes: "Sensible al número de intervalos (bins) utilizados. Requiere suficientes datos por intervalo.",
      },
      {
        name: "Kolmogorov-Smirnov (KS)",
        description: "Prueba no paramétrica que compara la función de distribución empírica con la teórica.",
        interpretation: [
          "Estadístico D: Máxima diferencia entre CDFs empírica y teórica",
          "Valor p > 0.05: Ajuste aceptable (ACEPTADO)",
          "Valor p ≤ 0.05: Ajuste deficiente (RECHAZADO)",
        ],
        notes: "Más sensible a diferencias en el centro de la distribución que en las colas.",
      },
      {
        name: "Error Estándar de Ajuste (EEA)",
        description: "Medida de la desviación estándar de los residuos entre valores observados y cuantiles teóricos.",
        interpretation: [
          "EEA normalizado < 0.1: Ajuste excelente (ACEPTADO)",
          "EEA normalizado entre 0.1-0.2: Ajuste aceptable",
          "EEA normalizado > 0.2: Ajuste deficiente (RECHAZADO)",
        ],
        notes: "Métrica específica del campo hidrológico. Penaliza desviaciones en todos los cuantiles por igual.",
      },
    ],
  },
  {
    id: "parameters",
    title: "🔧 Significado de Parámetros",
    icon: "⚙️",
    content: [
      {
        name: "Parámetro de Ubicación (Location)",
        symbol: "μ, ξ, x₀",
        description: "Define el punto central o de inicio de la distribución.",
        effect: "Desplaza la distribución horizontalmente sin cambiar su forma.",
        examples: [
          "En Gumbel: Moda de la distribución",
          "En Pearson III: Límite inferior de la distribución",
        ],
      },
      {
        name: "Parámetro de Escala (Scale)",
        symbol: "σ, α, β",
        description: "Controla la dispersión o amplitud de la distribución.",
        effect: "Valores mayores = mayor dispersión. Estira o comprime la distribución.",
        examples: [
          "En Normal: Desviación estándar",
          "En Weibull: Factor de escala característico",
        ],
      },
      {
        name: "Parámetro de Forma (Shape)",
        symbol: "k, γ, c, α",
        description: "Determina la forma específica de la distribución.",
        effect: "Cambia la asimetría, curtosis y comportamiento de colas.",
        examples: [
          "En GEV: Positivo = cola pesada (Fréchet), Negativo = cola ligera (Weibull)",
          "En Gamma: Determina si la forma es exponencial decreciente o unimodal",
        ],
      },
    ],
  },
  {
    id: "design-events",
    title: "🌊 Eventos de Diseño",
    icon: "🌊",
    content: [
      {
        name: "Período de Retorno (T)",
        description: "Tiempo promedio entre ocurrencias de un evento igual o mayor que el valor de diseño.",
        interpretation: [
          "T = 2 años: Evento que ocurre cada 2 años en promedio (50% de excedencia anual)",
          "T = 10 años: Evento decenal (10% de excedencia anual)",
          "T = 100 años: Evento centenario (1% de excedencia anual)",
        ],
        notes: "NO significa que el evento ocurra exactamente cada T años, sino que la probabilidad anual de excedencia es 1/T.",
      },
      {
        name: "Probabilidad Anual de No Excedencia",
        description: "Probabilidad de que en un año dado el caudal NO supere el valor de diseño.",
        formula: "P(X ≤ x) = 1 - 1/T",
        examples: [
          "Para T=100: P = 1 - 0.01 = 0.99 (99% de no excedencia)",
          "Para T=10: P = 1 - 0.10 = 0.90 (90% de no excedencia)",
        ],
      },
      {
        name: "Valor de Diseño",
        description: "Caudal asociado al período de retorno especificado según la distribución ajustada.",
        calculation: "Se obtiene evaluando la función cuantil (inversa de CDF) en P = 1 - 1/T",
        considerations: [
          "Depende fuertemente de la distribución seleccionada",
          "Incertidumbre aumenta para períodos de retorno largos",
          "Recomendado usar distribución que pase pruebas de bondad de ajuste",
        ],
      },
      {
        name: "Períodos de Retorno Estándar",
        description: "Valores comúnmente utilizados en ingeniería hidrológica.",
        standard_values: ["2, 5, 10, 25, 50, 100, 200, 500 años"],
        applications: [
          "T=2-5: Diseño de alcantarillas y sistemas urbanos",
          "T=10-25: Diseño de puentes y estructuras menores",
          "T=50-100: Diseño de presas y protección de ciudades",
          "T>100: Estructuras de alta seguridad",
        ],
      },
    ],
  },
];

function DistributionCard({ item }) {
  return (
    <div className="theory-card distribution-card">
      <h4 className="card-title">{item.name}</h4>
      <p className="card-description">{item.description}</p>
      {item.usage && (
        <div className="card-section">
          <strong>🎯 Uso:</strong> {item.usage}
        </div>
      )}
      {item.characteristics && (
        <div className="card-section">
          <strong>✨ Características:</strong>
          <ul className="feature-list">
            {item.characteristics.map((char, i) => (
              <li key={i}>{char}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function MetricCard({ item }) {
  return (
    <div className="theory-card metric-card">
      <h4 className="card-title">{item.name}</h4>
      <p className="card-description">{item.description}</p>
      {item.interpretation && (
        <div className="card-section">
          <strong>📋 Criterios:</strong>
          <ul className="criteria-list">
            {item.interpretation.map((crit, i) => (
              <li key={i}>{crit}</li>
            ))}
          </ul>
        </div>
      )}
      {item.notes && (
        <div className="card-note">
          <strong>💡 Nota:</strong> {item.notes}
        </div>
      )}
    </div>
  );
}

function ParameterCard({ item }) {
  return (
    <div className="theory-card parameter-card">
      <h4 className="card-title">
        {item.name} <code className="param-symbol">{item.symbol}</code>
      </h4>
      <p className="card-description">{item.description}</p>
      <div className="card-section">
        <strong>🔄 Efecto:</strong> {item.effect}
      </div>
      {item.examples && (
        <div className="card-section">
          <strong>💭 Ejemplos:</strong>
          <ul className="example-list">
            {item.examples.map((ex, i) => (
              <li key={i}>{ex}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function DesignEventCard({ item }) {
  return (
    <div className="theory-card design-event-card">
      <h4 className="card-title">{item.name}</h4>
      <p className="card-description">{item.description}</p>
      {item.formula && (
        <div className="formula-box">
          <code>{item.formula}</code>
        </div>
      )}
      {item.interpretation && (
        <div className="card-section">
          <ul className="interpretation-list">
            {item.interpretation.map((interp, i) => (
              <li key={i}>{interp}</li>
            ))}
          </ul>
        </div>
      )}
      {item.examples && (
        <div className="card-section">
          <ul className="example-list">
            {item.examples.map((ex, i) => (
              <li key={i}>{ex}</li>
            ))}
          </ul>
        </div>
      )}
      {item.calculation && (
        <div className="card-section">
          <strong>🧮 Cálculo:</strong> {item.calculation}
        </div>
      )}
      {item.considerations && (
        <div className="card-section">
          <strong>⚠️ Consideraciones:</strong>
          <ul className="consideration-list">
            {item.considerations.map((cons, i) => (
              <li key={i}>{cons}</li>
            ))}
          </ul>
        </div>
      )}
      {item.standard_values && (
        <div className="card-section">
          <strong>📊 Valores:</strong> <code>{item.standard_values[0]}</code>
        </div>
      )}
      {item.applications && (
        <div className="card-section">
          <strong>🏗️ Aplicaciones:</strong>
          <ul className="application-list">
            {item.applications.map((app, i) => (
              <li key={i}>{app}</li>
            ))}
          </ul>
        </div>
      )}
      {item.notes && (
        <div className="card-note">
          <strong>💡 Nota:</strong> {item.notes}
        </div>
      )}
    </div>
  );
}

export default function FrequencyTheoryInfo() {
  const [openSection, setOpenSection] = useState(null);

  const toggleSection = (id) => {
    setOpenSection(openSection === id ? null : id);
  };

  const renderContent = (section) => {
    switch (section.id) {
      case "distributions":
        return (
          <div className="cards-grid distributions-grid">
            {section.content.map((item, i) => (
              <DistributionCard key={i} item={item} />
            ))}
          </div>
        );
      case "metrics":
        return (
          <div className="cards-grid metrics-grid">
            {section.content.map((item, i) => (
              <MetricCard key={i} item={item} />
            ))}
          </div>
        );
      case "parameters":
        return (
          <div className="cards-grid parameters-grid">
            {section.content.map((item, i) => (
              <ParameterCard key={i} item={item} />
            ))}
          </div>
        );
      case "design-events":
        return (
          <div className="cards-grid design-events-grid">
            {section.content.map((item, i) => (
              <DesignEventCard key={i} item={item} />
            ))}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="theory-info-container">
      <div className="theory-header">
        <h3>📚 Información Teórica</h3>
        <p className="theory-subtitle">
          Guía completa para comprender el análisis de frecuencia hidrológica
        </p>
      </div>

      <div className="accordion-container">
        {SECTIONS.map((section) => (
          <div
            key={section.id}
            className={`theory-accordion ${openSection === section.id ? "open" : ""}`}
          >
            <button
              className="accordion-header"
              onClick={() => toggleSection(section.id)}
            >
              <span className="accordion-icon">{section.icon}</span>
              <span className="accordion-title">{section.title}</span>
              <span className="accordion-toggle">
                {openSection === section.id ? "−" : "+"}
              </span>
            </button>
            {openSection === section.id && (
              <div className="accordion-content">{renderContent(section)}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
