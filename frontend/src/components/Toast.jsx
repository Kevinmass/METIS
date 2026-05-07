/**
 * Componente ToastContainer - Contenedor de notificaciones tipo Toast
 *
 * Muestra notificaciones flotantes en la esquina superior derecha
 * con animaciones de entrada y salida.
 *
 * Estilos Frutiger Aero: glassmorphism, sombras suaves, colores temáticos
 *
 * @module Toast
 */

import { TOAST_TYPES } from "../hooks/useToast";

/**
 * Componente individual de Toast
 * @param {Object} props
 * @param {Object} props.toast - Datos del toast
 * @param {Function} props.onClose - Función para cerrar el toast
 */
function ToastItem({ toast, onClose }) {
  const getTypeStyles = (type) => {
    switch (type) {
      case TOAST_TYPES.SUCCESS:
        return {
          borderLeft: "4px solid #10b981",
          background: "linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(6, 182, 212, 0.1) 100%)",
          iconColor: "#10b981",
        };
      case TOAST_TYPES.ERROR:
        return {
          borderLeft: "4px solid #ef4444",
          background: "linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(249, 115, 22, 0.1) 100%)",
          iconColor: "#ef4444",
        };
      case TOAST_TYPES.WARNING:
        return {
          borderLeft: "4px solid #f59e0b",
          background: "linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(234, 179, 8, 0.1) 100%)",
          iconColor: "#f59e0b",
        };
      case TOAST_TYPES.INFO:
      default:
        return {
          borderLeft: "4px solid #06b6d4",
          background: "linear-gradient(135deg, rgba(6, 182, 212, 0.15) 0%, rgba(59, 130, 246, 0.1) 100%)",
          iconColor: "#06b6d4",
        };
    }
  };

  const styles = getTypeStyles(toast.type);

  return (
    <div
      className="toast-item"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "12px",
        padding: "16px 20px",
        marginBottom: "12px",
        borderRadius: "12px",
        background: styles.background,
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderLeft: styles.borderLeft,
        boxShadow: "0 8px 32px rgba(0, 105, 148, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.2)",
        minWidth: "320px",
        maxWidth: "480px",
        animation: "toastSlideIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)",
      }}
    >
      {/* Icono */}
      <div
        style={{
          flexShrink: 0,
          width: "24px",
          height: "24px",
          color: styles.iconColor,
        }}
      >
        {toast.icon}
      </div>

      {/* Contenido */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {toast.title && (
          <div
            style={{
              fontWeight: 600,
              fontSize: "14px",
              color: "#1e3a5f",
              marginBottom: "4px",
            }}
          >
            {toast.title}
          </div>
        )}
        <div
          style={{
            fontSize: "13px",
            color: "#475569",
            lineHeight: 1.5,
          }}
        >
          {toast.message}
        </div>
      </div>

      {/* Botón cerrar */}
      <button
        onClick={() => onClose(toast.id)}
        style={{
          flexShrink: 0,
          width: "20px",
          height: "20px",
          border: "none",
          background: "transparent",
          cursor: "pointer",
          color: "#94a3b8",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "4px",
          transition: "all 0.2s ease",
        }}
        onMouseEnter={(e) => {
          e.target.style.color = "#64748b";
          e.target.style.background = "rgba(0, 0, 0, 0.05)";
        }}
        onMouseLeave={(e) => {
          e.target.style.color = "#94a3b8";
          e.target.style.background = "transparent";
        }}
        aria-label="Cerrar notificación"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}

/**
 * Contenedor de Toasts
 * @param {Object} props
 * @param {Array} props.toasts - Lista de toasts a mostrar
 * @param {Function} props.removeToast - Función para eliminar un toast
 */
export function ToastContainer({ toasts, removeToast }) {
  if (toasts.length === 0) return null;

  return (
    <div
      className="toast-container"
      style={{
        position: "fixed",
        top: "20px",
        right: "20px",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        pointerEvents: "none", // Permite clicks a través del contenedor
      }}
    >
      {toasts.map((toast) => (
        <div key={toast.id} style={{ pointerEvents: "auto" }}>
          <ToastItem toast={toast} onClose={removeToast} />
        </div>
      ))}
    </div>
  );
}

export default ToastContainer;
