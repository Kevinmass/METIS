/**
 * Hook useToast - Sistema de notificaciones tipo Toast para METIS
 *
 * Proporciona funciones para mostrar notificaciones temporales
 * de éxito, error, advertencia e información.
 *
 * @module useToast
 */

import { useCallback, useState } from "react";

/** Tipos de notificación soportados */
export const TOAST_TYPES = {
  SUCCESS: "success",
  ERROR: "error",
  WARNING: "warning",
  INFO: "info",
};

/** Duraciones por defecto (ms) */
const DEFAULT_DURATION = 5000;
const ERROR_DURATION = 8000;

/** Iconos SVG para cada tipo */
const TOAST_ICONS = {
  [TOAST_TYPES.SUCCESS]: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  ),
  [TOAST_TYPES.ERROR]: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  ),
  [TOAST_TYPES.WARNING]: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  [TOAST_TYPES.INFO]: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  ),
};

let toastIdCounter = 0;

/**
 * Hook para gestionar notificaciones toast
 *
 * @returns {Object} Funciones y estado para manejar toasts
 *   - toasts: Array de toasts activos
 *   - showToast: Función para mostrar un toast
 *   - showSuccess: Función para mostrar toast de éxito
 *   - showError: Función para mostrar toast de error
 *   - showWarning: Función para mostrar toast de advertencia
 *   - showInfo: Función para mostrar toast informativo
 *   - removeToast: Función para eliminar un toast específico
 *   - clearAllToasts: Función para eliminar todos los toasts
 */
export function useToast() {
  const [toasts, setToasts] = useState([]);

  /**
   * Elimina un toast por su ID
   * @param {number} id - ID del toast a eliminar
   */
  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  /**
   * Elimina todos los toasts
   */
  const clearAllToasts = useCallback(() => {
    setToasts([]);
  }, []);

  /**
   * Muestra un toast genérico
   * @param {Object} options - Opciones del toast
   * @param {string} options.message - Mensaje a mostrar
   * @param {string} options.type - Tipo de toast (success, error, warning, info)
   * @param {number} options.duration - Duración en ms (default: 5000)
   * @param {string} options.title - Título opcional
   * @returns {number} ID del toast creado
   */
  const showToast = useCallback(
    ({ message, type = TOAST_TYPES.INFO, duration, title }) => {
      const id = ++toastIdCounter;
      const actualDuration =
        duration || (type === TOAST_TYPES.ERROR ? ERROR_DURATION : DEFAULT_DURATION);

      const newToast = {
        id,
        message,
        type,
        title,
        icon: TOAST_ICONS[type],
        duration: actualDuration,
      };

      setToasts((prev) => [...prev, newToast]);

      // Auto-remover después de la duración
      setTimeout(() => {
        removeToast(id);
      }, actualDuration);

      return id;
    },
    [removeToast]
  );

  /**
   * Muestra un toast de éxito
   * @param {string} message - Mensaje de éxito
   * @param {Object} options - Opciones adicionales
   */
  const showSuccess = useCallback(
    (message, options = {}) => {
      return showToast({
        ...options,
        message,
        type: TOAST_TYPES.SUCCESS,
        title: options.title || "¡Éxito!",
      });
    },
    [showToast]
  );

  /**
   * Muestra un toast de error
   * @param {string} message - Mensaje de error
   * @param {Object} options - Opciones adicionales
   */
  const showError = useCallback(
    (message, options = {}) => {
      return showToast({
        ...options,
        message,
        type: TOAST_TYPES.ERROR,
        title: options.title || "Error",
      });
    },
    [showToast]
  );

  /**
   * Muestra un toast de advertencia
   * @param {string} message - Mensaje de advertencia
   * @param {Object} options - Opciones adicionales
   */
  const showWarning = useCallback(
    (message, options = {}) => {
      return showToast({
        ...options,
        message,
        type: TOAST_TYPES.WARNING,
        title: options.title || "Advertencia",
      });
    },
    [showToast]
  );

  /**
   * Muestra un toast informativo
   * @param {string} message - Mensaje informativo
   * @param {Object} options - Opciones adicionales
   */
  const showInfo = useCallback(
    (message, options = {}) => {
      return showToast({
        ...options,
        message,
        type: TOAST_TYPES.INFO,
        title: options.title || "Información",
      });
    },
    [showToast]
  );

  return {
    toasts,
    showToast,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    removeToast,
    clearAllToasts,
  };
}

export default useToast;
