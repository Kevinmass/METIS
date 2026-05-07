# Changelog - Metis Frontend

Todos los cambios notables en el frontend de Metis serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [Unreleased]

### Added
- **Fondo personalizado**: `Background.png` como fondo del programa con overlay para legibilidad
- **Carpeta public**: Estructura para archivos estáticos (Background.png)

### Changed
- **frutiger-aero.css**: Reemplazado degradado de fondo por imagen Background.png con capa overlay

### Fixed

## [1.0.0] - 2026-04-30

### Added
- **Frutiger Aero Design System**: Nuevo sistema de diseño completo con estética acuática, glassmorphism y colores vívidos.
- **Archivos CSS**:
  - `src/styles/frutiger-aero.css`: Variables CSS, base, layout, formularios, tablas
  - `src/styles/animations.css`: Keyframes (ripple, glow, fadeIn), utilidades de animación
  - `src/styles/components.css`: Estilos de GlassPanel, AquaButton, WaterChartBox
- **Componentes React**:
  - `WaterChartBox.jsx`: Contenedor de gráficos con efecto ripple CSS puro (::before, ::after)
  - `GlassPanel.jsx`: Panel con glassmorphism, backdrop-filter, borde luminoso
  - `AquaButton.jsx`: Botón con efecto gloss, degradados, múltiples variantes
  - `index.js`: Exportación centralizada de componentes
- **Componentes de Gráficos (Recharts)**:
  - `AquaLineChart.jsx`: Gráfico de líneas estilizado
  - `AquaBarChart.jsx`: Gráfico de barras con bordes redondeados
  - `AquaAreaChart.jsx`: Gráfico de área con degradado
  - `AquaScatterChart.jsx`: Gráfico de dispersión
  - `index.js`: Exportación centralizada de gráficos
- **Dependencia**: `recharts@^2.x` para visualizaciones estadísticas
- **Estructura de carpetas**: `src/components/`, `src/components/charts/`, `src/styles/`

### Changed
- **Paleta de colores**: Transición de dark mode tradicional (#08101f) a degradados dinámicos azul-cian.
  - Primary: #00d4ff (aqua)
  - Secondary: #0080ff (blue)
  - Fondo: gradiente 135deg #0a1628 → #0d2847 → #0a3d62
- **Tipografía**: Inter con pesos optimizados para legibilidad sobre fondos glassmorphism.
- **main.jsx**: Actualizado para importar nuevos archivos CSS del sistema Frutiger Aero.
- **App.jsx**: Integración completa de componentes Frutiger Aero:
  - Importados `WaterChartBox`, `GlassPanel`, `AquaButton` y gráficos Recharts
  - Reemplazadas clases legacy: `panel` → `glass-panel`, `chart-box` → `water-chart-box`
  - Reemplazados botones: `button-primary` → `aqua-button`, `button-secondary` → `aqua-button secondary`
  - Actualizados banners: `error-banner` → `status-banner error`, `warning-banner` → `status-banner warning`
  - Actualizados pills: `pill accepted` → `status-pill accepted`
  - Gráficos de dispersión y correlograma ahora usan `WaterChartBox` con efecto ripple

### Notas de Implementación
- Efecto ripple implementado con CSS puro (sin Framer Motion) para alto rendimiento
- Las ondas (::before, ::after) tienen `pointer-events: none` para no interferir con tooltips de gráficos
- Colores legacy mantenidos en `style.css` para compatibilidad gradual
- WaterChartBox acepta children de cualquier librería de gráficos

