/**
 * AquaButton - Botón con Estilo Frutiger Aero
 * 
 * Botón interactivo con efecto "gloss" (brillo) en la parte superior,
 * degradados vibrantes y animaciones fluidas.
 * 
 * Características:
 *   - Efecto gloss con reflejo de luz
 *   - Degradados acuáticos dinámicos
 *   - Múltiples variantes: primary, secondary, danger, success
 *   - Tamaños: small, default, large
 *   - Estados: disabled, loading
 *   - Animaciones de hover y active
 * 
 * Props:
 *   - children: ReactNode - Contenido del botón (texto o icono)
 *   - variant: 'primary' | 'secondary' | 'danger' | 'success' - Estilo visual
 *   - size: 'small' | 'default' | 'large' - Tamaño del botón
 *   - disabled: boolean - Estado deshabilitado
 *   - loading: boolean - Mostrar spinner de carga
 *   - className: string (opcional) - Clases adicionales
 *   - style: object (opcional) - Estilos inline
 *   - onClick: function - Handler de click
 *   - type: 'button' | 'submit' | 'reset' - Tipo de botón HTML
 * 
 * @example
 * <AquaButton variant="primary" size="large" onClick={handleClick}>
 *   Analizar Datos
 * </AquaButton>
 */

import React from 'react';
import PropTypes from 'prop-types';

/**
 * Componente AquaButton
 * 
 * @param {Object} props - Propiedades del componente
 * @param {React.ReactNode} props.children - Contenido del botón
 * @param {string} [props.variant='primary'] - Variante visual del botón
 * @param {string} [props.size='default'] - Tamaño del botón
 * @param {boolean} [props.disabled=false] - Estado deshabilitado
 * @param {boolean} [props.loading=false] - Estado de carga
 * @param {string} [props.className] - Clases CSS adicionales
 * @param {Object} [props.style] - Estilos inline adicionales
 * @param {Function} [props.onClick] - Handler de click
 * @param {string} [props.type='button'] - Tipo de botón HTML
 */
export function AquaButton({ 
  children, 
  variant = 'primary', 
  size = 'default',
  disabled = false,
  loading = false,
  className = '', 
  style = {},
  onClick,
  type = 'button'
}) {
  // Mapeo de variantes a clases CSS
  const variantClasses = {
    primary: '',
    secondary: 'secondary',
    danger: 'danger',
    success: 'success'
  };

  // Mapeo de tamaños a clases CSS
  const sizeClasses = {
    small: 'small',
    default: '',
    large: 'large'
  };

  const variantClass = variantClasses[variant] || '';
  const sizeClass = sizeClasses[size] || '';
  
  const combinedClassName = [
    'aqua-button',
    variantClass,
    sizeClass,
    className
  ].filter(Boolean).join(' ');

  return (
    <button 
      className={combinedClassName}
      style={style}
      onClick={onClick}
      disabled={disabled || loading}
      type={type}
    >
      {loading ? (
        <>
          <span className="aqua-loader small" style={{ 
            display: 'inline-block', 
            marginRight: '8px',
            verticalAlign: 'middle'
          }} />
          <span style={{ verticalAlign: 'middle' }}>{children}</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}

AquaButton.propTypes = {
  children: PropTypes.node.isRequired,
  variant: PropTypes.oneOf(['primary', 'secondary', 'danger', 'success']),
  size: PropTypes.oneOf(['small', 'default', 'large']),
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  className: PropTypes.string,
  style: PropTypes.object,
  onClick: PropTypes.func,
  type: PropTypes.oneOf(['button', 'submit', 'reset'])
};

AquaButton.defaultProps = {
  variant: 'primary',
  size: 'default',
  disabled: false,
  loading: false,
  className: '',
  style: {},
  type: 'button'
};

export default AquaButton;
