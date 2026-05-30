/**
 * Componente TeacherNote
 *
 * Bloque de explicación teórica que se muestra solo en Modo Docente.
 * Estilo glassmorphism con borde lateral según variante.
 *
 * @param {Object} props
 * @param {string} props.title - Título de la nota
 * @param {string} [props.icon] - Emoji icono (default: 🎓)
 * @param {string} [props.variant] - 'concepto' | 'explicacion' | 'advertencia'
 * @param {React.ReactNode} props.children - Contenido de la nota
 */

import { useTeacherMode } from "../context/TeacherModeContext";

const VARIANT_STYLES = {
  concepto: {
    borderLeft: "3px solid #60a5fa",
    background: "rgba(96, 165, 250, 0.06)",
  },
  explicacion: {
    borderLeft: "3px solid #34d399",
    background: "rgba(52, 211, 153, 0.06)",
  },
  advertencia: {
    borderLeft: "3px solid #fbbf24",
    background: "rgba(251, 191, 36, 0.06)",
  },
};

export default function TeacherNote({ title, icon = "\uD83C\uDF93", variant = "concepto", children }) {
  const { teacherMode } = useTeacherMode();

  if (!teacherMode) return null;

  const style = VARIANT_STYLES[variant] || VARIANT_STYLES.concepto;

  return (
    <div className="teacher-note" style={style}>
      <div className="teacher-note-header">
        <span className="teacher-note-icon">{icon}</span>
        <span className="teacher-note-title">{title}</span>
      </div>
      <div className="teacher-note-content">
        {children}
      </div>
    </div>
  );
}