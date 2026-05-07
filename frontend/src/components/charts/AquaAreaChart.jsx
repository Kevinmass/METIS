/**
 * AquaAreaChart - Gráfico de Área Estilizado
 * 
 * Componente de gráfico de área basado en Recharts con
 * estilos Frutiger Aero integrados y degradado de relleno.
 * 
 * Props:
 *   - data: array - Datos para el gráfico
 *   - dataKeyX: string - Clave para el eje X
 *   - dataKeyY: string - Clave para el eje Y
 *   - color: string (opcional) - Color de la línea (default: #00d4ff)
 *   - height: number (opcional) - Altura del gráfico (default: 300)
 *   - showGrid: boolean (opcional) - Mostrar grid (default: true)
 */

import React from 'react';
import PropTypes from 'prop-types';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

export function AquaAreaChart({
  data,
  dataKeyX,
  dataKeyY,
  color = '#00d4ff',
  height = 300,
  showGrid = true
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
      <AreaChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
        <defs>
          <linearGradient id={`gradient-${dataKeyY}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.4}/>
            <stop offset="95%" stopColor={color} stopOpacity={0.05}/>
          </linearGradient>
        </defs>
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
        <Area
          type="monotone"
          dataKey={dataKeyY}
          stroke={color}
          strokeWidth={2}
          fill={`url(#gradient-${dataKeyY})`}
          activeDot={{ r: 6, fill: color, stroke: '#fff', strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

AquaAreaChart.propTypes = {
  data: PropTypes.array.isRequired,
  dataKeyX: PropTypes.string.isRequired,
  dataKeyY: PropTypes.string.isRequired,
  color: PropTypes.string,
  height: PropTypes.number,
  showGrid: PropTypes.bool
};

AquaAreaChart.defaultProps = {
  color: '#00d4ff',
  height: 300,
  showGrid: true
};

export default AquaAreaChart;
