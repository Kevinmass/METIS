/**
 * TeacherModeContext
 *
 * Proveedor de estado global para el Modo Docente de METIS.
 * Cuando está activo, se muestran explicaciones teóricas en todas las secciones.
 *
 * @module context/TeacherMode
 */

import { createContext, useContext, useState, useCallback } from "react";

const TeacherModeContext = createContext(null);

/**
 * Proveedor del modo docente.
 * Envuelve la aplicación y expone el estado del modo docente.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children
 */
export function TeacherModeProvider({ children }) {
  const [teacherMode, setTeacherMode] = useState(false);

  const toggleTeacherMode = useCallback(() => {
    setTeacherMode((prev) => !prev);
  }, []);

  return (
    <TeacherModeContext.Provider value={{ teacherMode, toggleTeacherMode }}>
      {children}
    </TeacherModeContext.Provider>
  );
}

/**
 * Hook para acceder al estado del modo docente.
 * @returns {{ teacherMode: boolean, toggleTeacherMode: () => void }}
 */
export function useTeacherMode() {
  const context = useContext(TeacherModeContext);
  if (!context) {
    throw new Error("useTeacherMode debe usarse dentro de un TeacherModeProvider");
  }
  return context;
}