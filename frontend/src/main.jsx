/**
 * Punto de entrada principal de la aplicación React METIS.
 *
 * Este módulo inicializa la aplicación React renderizando el componente
 * App en el elemento DOM con id "root". Configura StrictMode para
 * detectar problemas potenciales durante el desarrollo.
 *
 * Estructura de la aplicación:
 *   - App.jsx: Componente raíz con lógica de validación hidrológica
 *   - style.css: Estilos globales con tema oscuro
 *
 * Dependencias:
 *   - react: Biblioteca de UI
 *   - react-dom: Renderizador DOM para React
 *   - xlsx: Parser de archivos Excel (usado en App.jsx)
 *
 * @module main
 */

import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./style.css";

// Obtener contenedor root del DOM
const container = document.getElementById("root");

// Crear root de React 18
const root = createRoot(container);

// Renderizar aplicación con StrictMode
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
