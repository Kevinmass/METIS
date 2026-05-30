/**
 * FrecuenciaTeacherNotes
 *
 * Notas teóricas para la sección de Análisis de Frecuencia.
 * Explica distribuciones, métodos de estimación y eventos de diseño.
 */

import TeacherNote from "../TeacherNote";

export default function FrecuenciaTeacherNotes() {
  return (
    <>
      <TeacherNote title="¿Qué es el análisis de frecuencia?" icon="📈" variant="concepto">
        <p>
          El <strong>análisis de frecuencia</strong> ajusta curvas matemáticas (distribuciones
          de probabilidad) a tus datos para predecir eventos extremos. Permite responder
          preguntas como: "¿Qué tan grande podría ser una inundación con un 1% de probabilidad
          de ocurrir en cualquier año?"
        </p>
        <p>
          Es una herramienta fundamental para el diseño de obras hidráulicas: puentes, presas,
          alcantarillas y sistemas de drenaje.
        </p>
      </TeacherNote>

      <TeacherNote title="Métodos de estimación" icon="🔧" variant="explicacion">
        <p>
          Los métodos determinan cómo se calculan los parámetros de cada distribución a partir
          de tus datos:
        </p>
        <p>
          <strong>MOM (Momentos)</strong>: Usa promedios y momentos estadísticos. Es el más
          simple, pero se afecta fácilmente por valores atípicos.
        </p>
        <p>
          <strong>MLE (Máxima Verosimilitud)</strong>: Busca los parámetros que hacen más
          probable observar tus datos. Eficiente con muestras grandes.
        </p>
        <p>
          <strong>MEnt (Momentos de Entropía)</strong>: Usa el principio de máxima entropía.
          Funciona bien con muestras pequeñas.
        </p>
        <p>
          <strong>LMom (L-Momentos)</strong>: <span style={{color: "#34d399"}}>Recomendado</span>.
          Usa momentos de orden inferior que son menos sensibles a valores extremos. Es el
          estándar en hidrología internacional.
        </p>
      </TeacherNote>

      <TeacherNote title="¿Por qué L-Momentos es recomendado?" icon="⭐" variant="explicacion">
        <p>
          Los L-Momentos son más <strong>robustos</strong> que otros métodos porque no se
          influyen tanto por valores atípicos. En hidrología, donde los datos de caudales
          máximos naturalmente tienen valores extremos, esto es una ventaja importante.
        </p>
        <p>
          Organismos como la USGS (Servicio Geológico de EE.UU.) y la CIA (Comisión
          Internacional de Aguas) recomiendan L-Momentos para análisis de frecuencia de caudales.
        </p>
      </TeacherNote>

      <TeacherNote title="Bondad de ajuste" icon="✅" variant="explicacion">
        <p>
          ¿Cómo saber si una distribución se ajusta bien a tus datos? Se usan tres pruebas:
        </p>
        <p>
          <strong>Chi Cuadrado (χ²)</strong>: Compara cuántos datos caen en cada intervalo
          observados vs. esperados. Un valor bajo indica buen ajuste.
        </p>
        <p>
          <strong>Kolmogorov-Smirnov (KS)</strong>: Mide la mayor diferencia entre la
          distribución de tus datos y la teórica. Un valor bajo = mejor ajuste.
        </p>
        <p>
          <strong>EEA (Error Estándar de Ajuste)</strong>: Mide qué bien la curva ajusta todos
          los puntos. Menor a 0.1 = excelente; mayor a 0.2 = deficiente.
        </p>
      </TeacherNote>

      <TeacherNote title="Evento de diseño y período de retorno" icon="🌊" variant="concepto">
        <p>
          El <strong>período de retorno (T)</strong> indica la frecuencia con que se espera que
          un evento ocurra. Pero cuidado: <strong>T = 100 años NO significa que el evento
          ocurra cada 100 años</strong>.
        </p>
        <p>
          Significa que en cada año hay una probabilidad de <strong>1/T = 1%</strong> de que el
          evento sea igualado o superado. Es una probabilidad, no una garantía de timing.
        </p>
        <p>
          <strong>Valores de diseño comunes</strong>: T=2 a 5 años (alcantarillas), T=10 a 25
          (puentes), T=50 a 100 (presas), T {'>'} 100 (estructuras de alta seguridad).
        </p>
      </TeacherNote>

      <TeacherNote title="¿Por qué mínimo 3 datos para ajuste?" icon="🔢" variant="advertencia">
        <p>
          Cada distribución tiene al menos 2 parámetros que estimar. Con menos de 3 datos,
          no hay suficiente información para determinar estos parámetros de manera confiable.
          El ajuste sería arbitrario y los resultados no tendrían valor predictivo.
        </p>
      </TeacherNote>
    </>
  );
}