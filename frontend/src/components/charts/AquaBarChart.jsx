/**
 * AquaBarChart - Gráfico de Barras Estilizado
 * 
 * Componente de gráfico de barras basado en Recharts con
 * estilos Frutiger Aero integrados.
 * 
 * Props:
 *   - data: array - Datos para el gráfico
 *   - dataKeyX: string - Clave para el eje X
 *   - dataKeyY: string - Clave para el eje Y
 *   - color: string (opcional) - Color de las barras (default: #00d4ff)
 *   - height: number (opcional) - Altura del gráfico (default: 300)
 *   - showGrid: boolean (opcional) - Mostrar grid (default: true)
 */

import React from 'react';
import PropTypes from 'prop-types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';

export function AquaBarChart({
  data,
  dataKeyX,
  dataKeyY,
  color = '#00d4ff',
  height = 300,
  showGrid = true,
  colors = null
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
      <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
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
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0, 212, 255, 0.1)' }} />
        <Bar 
          dataKey={dataKeyY} 
          fill={color}
          radius={[6, 6, 0, 0]}
        >
          {colors && data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

AquaBarChart.propTypes = {
  data: PropTypes.array.isRequired,
  dataKeyX: PropTypes.string.isRequired,
  dataKeyY: PropTypes.string.isRequired,
  color: PropTypes.string,
  height: PropTypes.number,
  showGrid: PropTypes.bool,
  colors: PropTypes.array
};

AquaBarChart.defaultProps = {
  color: '#00d4ff',
  height: 300,
  showGrid: true,
  colors: null
};

export default AquaBarChart;
