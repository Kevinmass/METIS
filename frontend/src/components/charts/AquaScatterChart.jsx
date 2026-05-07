/**
 * AquaScatterChart - Gráfico de Dispersión Estilizado
 * 
 * Componente de gráfico de dispersión basado en Recharts con
 * estilos Frutiger Aero integrados.
 * 
 * Props:
 *   - data: array - Datos para el gráfico
 *   - dataKeyX: string - Clave para el eje X
 *   - dataKeyY: string - Clave para el eje Y
 *   - color: string (opcional) - Color de los puntos (default: #00d4ff)
 *   - height: number (opcional) - Altura del gráfico (default: 300)
 *   - showGrid: boolean (opcional) - Mostrar grid (default: true)
 */

import React from 'react';
import PropTypes from 'prop-types';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis
} from 'recharts';

export function AquaScatterChart({
  data,
  dataKeyX,
  dataKeyY,
  color = '#00d4ff',
  height = 300,
  showGrid = true
}) {
  // Estilos del tooltip personalizado
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
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
            {dataKeyX}: {data[dataKeyX]}
          </p>
          <p style={{ margin: 0, color: color, fontWeight: 600, fontSize: '1rem' }}>
            {dataKeyY}: {data[dataKeyY]}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
        {showGrid && (
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="rgba(255, 255, 255, 0.1)"
          />
        )}
        <XAxis 
          type="number"
          dataKey={dataKeyX}
          tick={{ fill: 'rgba(255, 255, 255, 0.6)', fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: 'rgba(255, 255, 255, 0.15)' }}
        />
        <YAxis 
          type="number"
          dataKey={dataKeyY}
          tick={{ fill: 'rgba(255, 255, 255, 0.6)', fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: 'rgba(255, 255, 255, 0.15)' }}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: color, strokeWidth: 1, strokeDasharray: '4 4' }} />
        <Scatter
          data={data}
          fill={color}
          fillOpacity={0.6}
          stroke={color}
          strokeWidth={1}
        />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

AquaScatterChart.propTypes = {
  data: PropTypes.array.isRequired,
  dataKeyX: PropTypes.string.isRequired,
  dataKeyY: PropTypes.string.isRequired,
  color: PropTypes.string,
  height: PropTypes.number,
  showGrid: PropTypes.bool
};

AquaScatterChart.defaultProps = {
  color: '#00d4ff',
  height: 300,
  showGrid: true
};

export default AquaScatterChart;
