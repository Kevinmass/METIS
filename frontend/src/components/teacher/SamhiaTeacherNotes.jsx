/**
 * SamhiaTeacherNotes
 *
 * Notas teóricas para la sección de Análisis SAMHIA.
 * Incluye notas generales y tooltips para cada test estadístico.
 */

import TeacherNote from "../TeacherNote";
import TeacherTooltip from "../TeacherTooltip";

/** Tooltips para categorías de tests */
export const CATEGORY_TOOLTIPS = {
  independence: "Evalúa si cada dato es independiente del anterior. Si hay autocorrelación, los tests estándar pierden validez y los resultados pueden ser engañosos.",
  homogeneity: "Verifica si la serie se comporta de la misma manera a lo largo del tiempo. Un cambio en las condiciones (por ejemplo, construcción de una presa) puede dividir la serie en partes con comportamientos distintos.",
  trend: "Detecta si los valores muestran una dirección creciente o decreciente. La tendencia puede indicar cambios climáticos, urbanización o modificaciones en la cuenca hidrográfica.",
  outliers: "Identifica valores anormalmente altos o bajos que pueden distorsionar el ajuste de distribuciones y los cálculos de eventos de diseño.",
};

/** Tooltips para tests individuales */
export const TEST_TOOLTIPS = {
  anderson: "Compara la distribución de los datos con una distribución normal. Si rechaza, los datos no siguen una forma normal.",
  wald_wolfowitz: "Cuenta 'rachas' de valores por encima o por debajo de la media. Rachas demasiado largas o cortas indican que los datos no son aleatorios.",
  durbin_watson: "Detecta autocorrelación entre un dato y el siguiente. Un valor cercano a 2 indica ausencia de autocorrelación.",
  ljung_box: "Evalúa si hay autocorrelación en múltiples rezagos al mismo tiempo, no solo entre datos consecutivos.",
  spearman: "Mide si hay tendencia usando los rangos de los datos. Es robusta porque no se afecta por valores extremos.",
  helmert: "Compara las medias de diferentes partes de la serie para ver si cambiaron con el tiempo.",
  t_student: "Compara las medias de las dos mitades de la serie. Si difieren mucho, puede haber un cambio en el comportamiento.",
  cramer: "Similar a Kolmogorov-Smirnov pero más sensible a diferencias en las colas de la distribución.",
  mann_whitney: "Compara las distribuciones de las dos mitades de la serie sin asumir que los datos sean normales.",
  mood: "Compara la dispersión (varianza) de las dos mitades de la serie. Detecta si los datos se volvieron más o menos variables.",
  mann_kendall: "Test estándar en hidrología para detectar tendencia. No asume normalidad y es robusto ante valores atípicos.",
  kolmogorov_smirnov: "Compara las distribuciones acumuladas de las dos mitades de la serie. Detecta cambios en la forma de la distribución.",
  chow: "Busca un punto en la serie donde el comportamiento cambia bruscamente (ruptura).",
  kn: "Identifica valores atípicos usando un estadístico que compara cada valor con sus vecinos.",
};

export default function SamhiaTeacherNotes() {
  return (
    <>
      <TeacherNote title="¿Qué es SAMHIA?" icon="📋" variant="concepto">
        <p>
          <strong>SAMHIA</strong> (Sistema de Análisis de Mediciones Hidrológicas e
          Hidroquímicas Ambientales) es un conjunto de pruebas estadísticas que verifican
          si tus datos cumplen las condiciones necesarias para un análisis confiable.
        </p>
        <p>
          Antes de ajustar distribuciones de probabilidad, es fundamental confirmar que los
          datos son <strong>independientes</strong>, <strong>homogéneos</strong>, sin
          <strong>tendencia</strong>, y libres de <strong>valores atípicos</strong> problemáticos.
        </p>
      </TeacherNote>

      <TeacherNote title="¿Por qué mínimo 12 datos?" icon="🔢" variant="advertencia">
        <p>
          Los tests de tendencia y homogeneidad necesitan suficientes observaciones para tener
          <strong> potencia estadística</strong>. Con menos de 12 datos, los tests pierden
          capacidad de detectar patrones reales y pueden dar conclusiones incorrectas.
        </p>
        <p>
          Más datos = más confiabilidad en los resultados.
        </p>
      </TeacherNote>

      <TeacherNote title="Nivel de significancia (α)" icon="🎚️" variant="explicacion">
        <p>
          El nivel de significancia <strong>α = 0.05</strong> significa que aceptamos un 5% de
          riesgo de rechazar incorrectamente una hipótesis que es verdadera (Error Tipo I).
        </p>
        <p>
          Es el estándar en ingeniería e hidrología. Un α más bajo (0.01) es más conservador,
          pero puede pasar por alto cambios reales.
        </p>
      </TeacherNote>

      <TeacherNote title="Categorías de análisis" icon="📂" variant="concepto">
        <p>
          Los tests se organizan en cuatro categorías. En Modo Docente, pasar el mouse sobre
          el nombre de cada categoría o test mostrará una explicación rápida.
        </p>
      </TeacherNote>
    </>
  );
}