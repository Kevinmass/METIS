# Changelog - METIS

Todos los cambios notables en el proyecto METIS serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [Unreleased]

### Added
- **Modo Docente**: Nuevo sistema de explicaciones teóricas activable desde el sidebar.
  - Context global `TeacherModeContext` con toggle en sidebar footer.
  - Componente `TeacherNote`: bloques de explicación con 3 variantes visuales.
  - Componente `TeacherTooltip`: tooltips flotantes al hacer hover.
  - Contenido teórico para las 4 secciones: Ingesta, Resumen, SAMHIA, Frecuencia.
  - Tooltips explicativos para 14 tests estadísticos en SAMHIA.
- **Gráficos de Distribuciones (SVG nativo)**:
  - `DistributionPDFChart`: curva PDF + histograma real para cada distribución ajustada.
  - `SuperimposedDistributionsChart`: todas las distribuciones superpuestas con toggle.
  - Cálculo de PDF 100% en frontend (sin matplotlib ni backend).
- **Scripts de tests**: `run_tests.sh` y `run_tests.bat` para ejecutar la suite completa.
- **ARCHITECTURE.md**: Documento completo de arquitectura del sistema.

### Changed
- **App.jsx**: Integración completa del Modo Docente en las 4 secciones.
- **components/index.js**: Exportación de nuevos componentes TeacherNote, TeacherTooltip.
- **styles/components.css**: Estilos para modo docente, tooltips y gráficos de distribución.
- **README**: Convertido a `README.md` y reescrito con documentación actualizada.
- **ROADMAP.md**: Actualizado con nuevas funcionalidades implementadas.

### Fixed
- (Sin fixes en esta release)

## [1.0.0] - 2026-04-30

### Added
- **Frutiger Aero Design System**: Nuevo sistema de diseño completo con estética acuática, glassmorphism y colores vívidos.
- **Archivos CSS**:
  - `src/styles/frutiger-aero.css`: Variables CSS, base, layout, formularios, tablas
  - `src/styles/animations.css`: Keyframes (ripple, glow, fadeIn), utilidades de animación
  - `src/styles/components.css`: Estilos de GlassPanel, AquaButton, WaterChartBox
- **Componentes React**:
  - `WaterChartBox.jsx`: Contenedor de gráficos con efecto ripple CSS puro
  - `GlassPanel.jsx`: Panel con glassmorphism, backdrop-filter, borde luminoso
  - `AquaButton.jsx`: Botón con efecto gloss, degradados, múltiples variantes
- **Componentes de Gráficos (Recharts)**:
  - `AquaLineChart.jsx`, `AquaBarChart.jsx`, `AquaAreaChart.jsx`, `AquaScatterChart.jsx`
- **Fondo personalizado**: `Background.png` como fondo del programa con overlay para legibilidad

### Changed
- Transición de dark mode tradicional a degradados dinámicos azul-cian
- Tipografía: Inter con pesos optimizados para legibilidad sobre fondos glassmorphism
- Integración completa de componentes Frutiger Aero en App.jsx

---

*Historial de cambios del proyecto METIS — PI ISI UCC 2026*