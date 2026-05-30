/**
 * IngestaTeacherNotes
 *
 * Notas teóricas para la sección de Ingesta de Datos.
 * Explica conceptos básicos para usuarios no expertos.
 */

import TeacherNote from "../TeacherNote";

export default function IngestaTeacherNotes() {
  return (
    <>
      <TeacherNote title="¿Qué es una serie hidrológica?" icon="🌊" variant="concepto">
        <p>
          Una <strong>serie hidrológica</strong> es un registro ordenado en el tiempo de mediciones
          de una variable del agua: caudales, precipitaciones, niveles, etc. Cada dato representa
          una medición tomada en un momento o período específico.
        </p>
        <p>
          Esta serie es la base para todos los análisis estadísticos que METIS puede realizar,
          como detectar tendencias, identificar eventos extremos y predecir futuros valores.
        </p>
      </TeacherNote>

      <TeacherNote title="¿Por qué mínimo 3 datos?" icon="🔢" variant="explicacion">
        <p>
          Los cálculos estadísticos básicos necesitan al menos <strong>3 valores</strong> para
          funcionar. Con solo 1 o 2 datos no existe variabilidad que medir: la desviación
          estándar (que mide cuánto se dispersan los datos) requiere al menos 3 puntos para
          calcularse correctamente.
        </p>
        <p>
          Para análisis más robustos como SAMHIA se recomiendan al menos 12 datos, ya que
          los tests estadísticos necesitan suficiente información para detectar patrones reales.
        </p>
      </TeacherNote>

      <TeacherNote title="Formatos de archivo" icon="📁" variant="concepto">
        <p>
          <strong>CSV</strong> (valores separados por coma o punto y coma): es el formato más
          común. Puede abrirse con cualquier editor de texto o Excel.
        </p>
        <p>
          <strong>XLSX / XLS</strong>: archivos de hoja de cálculo de Excel directamente.
          METIS detecta automáticamente las columnas disponibles.
        </p>
        <p>
          Lo importante es que el archivo tenga al menos una <strong>columna de fechas</strong> y
          una <strong>columna de valores numéricos</strong>.
        </p>
      </TeacherNote>

      <TeacherNote title="Procesamiento temporal" icon="⏱️" variant="explicacion">
        <p>
          Si tus datos tienen alta frecuencia (ej. cada 5 minutos), puedes <strong>agregarlos</strong>
          a una frecuencia menor (ej. diaria o anual). Esto es útil cuando necesitas
          analizar tendencias a largo plazo.
        </p>
        <p>
          El <strong>año hidrológico</strong> comienza en un mes distinto al calendario (por ejemplo,
          en octubre en el hemisferio sur), porque agrupa una temporada de lluvias completa.
        </p>
      </TeacherNote>
    </>
  );
}