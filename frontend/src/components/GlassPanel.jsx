/**
 * GlassPanel - Panel Acrílico/Crystal
 * 
 * Componente contenedor con efecto glassmorphism que proporciona
 * profundidad visual y sensación de capas en la interfaz.
 * 
 * Características:
 *   - Efecto acrílico con backdrop-filter
 *   - Borde luminoso superior (highlight)
 *   - Hover effects con elevación y glow
 *   - Múltiples variantes de tamaño y estilo
 * 
 * Props:
 *   - children: ReactNode - Contenido del panel
 *   - title: string (opcional) - Título del panel
 *   - size: 'compact' | 'default' | 'large' - Tamaño del padding
 *   - glow: boolean - Activar animación de pulso
 *   - className: string (opcional) - Clases adicionales
 *   - style: object (opcional) - Estilos inline
 *   - onClick: function (opcional) - Handler de click
 * 
 * @example
 * <GlassPanel title="Resultados del Análisis" size="large" glow>
 *   <p>Contenido aquí...</p>
 * </GlassPanel>
 */

import React from 'react';
import PropTypes from 'prop-types';

/**
 * Componente GlassPanel
 * 
 * @param {Object} props - Propiedades del componente
 * @param {React.ReactNode} props.children - Contenido del panel
 * @param {string} [props.title] - Título opcional del panel
 * @param {string} [props.size='default'] - Tamaño del padding
 * @param {boolean} [props.glow=false] - Activar animación de pulso
 * @param {string} [props.className] - Clases CSS adicionales
 * @param {Object} [props.style] - Estilos inline adicionales
 * @param {Function} [props.onClick] - Handler de click
 */
export function GlassPanel({ 
  children, 
  title, 
  size = 'default', 
  glow = false,
  className = '', 
  style = {},
  onClick
}) {
  // Mapeo de tamaños a clases CSS
  const sizeClasses = {
    compact: 'compact',
    default: '',
    large: 'large'
  };

  const sizeClass = sizeClasses[size] || '';
  const glowClass = glow ? 'glow' : '';
  
  const combinedClassName = [
    'glass-panel',
    sizeClass,
    glowClass,
    className
  ].filter(Boolean).join(' ');

  return (
    <div 
      className={combinedClassName} 
      style={style}
      onClick={onClick}
    >
      {title && (
        <h3 style={{ 
          margin: '0 0 16px 0', 
          fontSize: '1.2rem',
          fontWeight: 600,
          color: 'var(--text-primary)'
        }}>
          {title}
        </h3>
      )}
      {children}
    </div>
  );
}

GlassPanel.propTypes = {
  children: PropTypes.node.isRequired,
  title: PropTypes.string,
  size: PropTypes.oneOf(['compact', 'default', 'large']),
  glow: PropTypes.bool,
  className: PropTypes.string,
  style: PropTypes.object,
  onClick: PropTypes.func
};

GlassPanel.defaultProps = {
  size: 'default',
  glow: false,
  className: '',
  style: {}
};

export default GlassPanel;
