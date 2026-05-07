/**
 * WaterChartBox - Componente Envoltorio para Gráficos
 * 
 * Este componente proporciona un contenedor estilizado con el efecto
 * "salpicadura" (ripple) inspirado en Frutiger Aero. Al hacer hover,
 * se activan ondas concéntricas que simulan una piedra cayendo en el agua.
 * 
 * Características:
 *   - Efecto ripple CSS puro con ::before y ::after
 *   - Animaciones con keyframes para alto rendimiento
 *   - pointer-events: none en ondas para no interferir con gráficos
 *   - Compatible con cualquier librería de gráficos (Recharts, Chart.js, SVG)
 *   - Diseño responsive que se adapta a diferentes proporciones
 * 
 * Props:
 *   - title: string (opcional) - Título del gráfico
 *   - children: ReactNode - Gráfico o contenido a mostrar
 *   - className: string (opcional) - Clases CSS adicionales
 *   - style: object (opcional) - Estilos inline adicionales
 * 
 * @example
 * <WaterChartBox title="Caudal Mensual">
 *   <LineChart data={data}>
 *     <Line type="monotone" dataKey="value" stroke="#00d4ff" />
 *   </LineChart>
 * </WaterChartBox>
 */

import React from 'react';
import PropTypes from 'prop-types';

/**
 * Componente WaterChartBox
 * 
 * @param {Object} props - Propiedades del componente
 * @param {string} [props.title] - Título opcional del gráfico
 * @param {React.ReactNode} props.children - Contenido del gráfico
 * @param {string} [props.className] - Clases CSS adicionales
 * @param {Object} [props.style] - Estilos inline adicionales
 * @param {string} [props.size='medium'] - Tamaño del contenedor: 'small', 'medium', 'large', 'full'
 */
export function WaterChartBox({ 
  title, 
  children, 
  className = '', 
  style = {},
  size = 'medium'
}) {
  // Mapeo de tamaños a clases CSS
  const sizeClasses = {
    small: 'water-chart-box--small',
    medium: '',
    large: 'water-chart-box--large',
    full: 'water-chart-box--full'
  };

  const sizeClass = sizeClasses[size] || '';
  const combinedClassName = `water-chart-box ${sizeClass} ${className}`.trim();

  return (
    <div className={combinedClassName} style={style}>
      {title && (
        <div className="chart-title">
          {title}
        </div>
      )}
      <div className="chart-content">
        {children}
      </div>
    </div>
  );
}

export default WaterChartBox;
