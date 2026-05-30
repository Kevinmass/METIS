/**
 * Componente TeacherTooltip
 *
 * Tooltip flotante con explicación teórica que aparece al hacer hover.
 * Solo visible en Modo Docente.
 *
 * @param {Object} props
 * @param {string} props.content - Texto explicativo
 * @param {React.ReactNode} props.children - Elemento que activa el tooltip
 * @param {string} [props.position] - 'top' | 'bottom' (default: 'top')
 */

import { useState, useRef, useEffect } from "react";
import { useTeacherMode } from "../context/TeacherModeContext";

export default function TeacherTooltip({ content, children, position = "top" }) {
  const { teacherMode } = useTeacherMode();
  const [visible, setVisible] = useState(false);
  const [tooltipStyle, setTooltipStyle] = useState({});
  const triggerRef = useRef(null);
  const tooltipRef = useRef(null);

  useEffect(() => {
    if (visible && triggerRef.current && tooltipRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();

      let top;
      if (position === "top") {
        top = triggerRect.top - tooltipRect.height - 8;
      } else {
        top = triggerRect.bottom + 8;
      }

      let left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;

      // Keep within viewport
      if (left < 8) left = 8;
      if (left + tooltipRect.width > window.innerWidth - 8) {
        left = window.innerWidth - tooltipRect.width - 8;
      }
      if (top < 8) {
        top = triggerRect.bottom + 8;
      }

      setTooltipStyle({ top: `${top}px`, left: `${left}px` });
    }
  }, [visible, position]);

  if (!teacherMode) return <>{children}</>;

  return (
    <>
      <span
        ref={triggerRef}
        className="teacher-tooltip-trigger"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        style={{ cursor: "help", borderBottom: "1px dashed rgba(96, 165, 250, 0.5)" }}
      >
        {children}
      </span>
      {visible && (
        <div
          ref={tooltipRef}
          className="teacher-tooltip"
          style={{
            position: "fixed",
            zIndex: 9999,
            maxWidth: "320px",
            padding: "10px 14px",
            borderRadius: "10px",
            background: "rgba(15, 23, 42, 0.95)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(96, 165, 250, 0.3)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(96, 165, 250, 0.1)",
            fontSize: "12.5px",
            lineHeight: "1.5",
            color: "#e2e8f0",
            pointerEvents: "none",
            animation: "fadeIn 0.15s ease",
            ...tooltipStyle,
          }}
        >
          <span style={{ marginRight: "6px" }}>🎓</span>
          {content}
        </div>
      )}
    </>
  );
}