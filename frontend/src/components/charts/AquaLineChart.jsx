/**
 * AquaLineChart - Gráfico de Líneas Estilizado
 * 
 * Componente de gráfico de líneas basado en Recharts con
 * estilos Frutiger Aero integrados.
 * 
 * Props:
 *   - data: array - Datos para el gráfico
 *   - dataKeyX: string - Clave para el eje X
 *   - dataKeyY: string - Clave para el eje Y
 *   - color: string (opcional) - Color de la línea (default: #00d4ff)
 *   - height: number (opcional) - Altura del gráfico (default: 300)
 *   - showGrid: boolean (opcional) - Mostrar grid (default: true)
 *   - showDots: boolean (opcional) - Mostrar puntos (default: false)
 *   - strokeWidth: number (opcional) - Grosor de línea (default: 2)
 */

import React from 'react';
import PropTypes from 'prop-types';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

export function AquaLineChart({
  data,
  dataKeyX,
  dataKeyY,
  color = '#00d4ff',
  height = 300,
  showGrid = true,
  showDots = false,
  strokeWidth = 2
}) {
  // Estilos del tooltip personalizado
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'rgba(10, 30, 50, 0.95)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: '12px',
          padding: '12px 16px',
          boxShadow: '0 8px 32px rgba(0, 100, 200, 0.3)'
        }}>
          <p style={{ margin: '0 0 4px 0', color: 'rgba(255, 255, 255, 0.6)', fontSize: '0.85rem' }}>
            {label}
          </p>
          <p style={{ margin: 0, color: color, fontWeight: 600, fontSize: '1rem' }}>
            {payload[0].value}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
        {showGrid && (
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="rgba(255, 255, 255, 0.1)"
            vertical={false}
          />
        )}
        <XAxis 
          dataKey={dataKeyX}
          tick={{ fill: 'rgba(255, 255, 255, 0.6)', fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: 'rgba(255, 255, 255, 0.15)' }}
        />
        <YAxis 
          tick={{ fill: 'rgba(255, 255, 255, 0.6)', fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: 'rgba(255, 255, 255, 0.15)' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey={dataKeyY}
          stroke={color}
          strokeWidth={strokeWidth}
          dot={showDots ? { fill: color, strokeWidth: 0, r: 4 } : false}
          activeDot={{ r: 6, fill: color, stroke: '#fff', strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

AquaLineChart.propTypes = {
  data: PropTypes.array.isRequired,
  dataKeyX: PropTypes.string.isRequired,
  dataKeyY: PropTypes.string.isRequired,
  color: PropTypes.string,
  height: PropTypes.number,
  showGrid: PropTypes.bool,
  showDots: PropTypes.bool,
  strokeWidth: PropTypes.number
};

AquaLineChart.defaultProps = {
  color: '#00d4ff',
  height: 300,
  showGrid: true,
  showDots: false,
  strokeWidth: 2
};

export default AquaLineChart;
