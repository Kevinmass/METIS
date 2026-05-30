/**
 * ResumenTeacherNotes
 *
 * Notas teóricas para la sección de Resumen de la Serie.
 * Explica estadísticas descriptivas y autocorrelación.
 */

import TeacherNote from "../TeacherNote";

export default function ResumenTeacherNotes() {
  return (
    <>
      <TeacherNote title="Estadísticas descriptivas" icon="📊" variant="concepto">
        <p>
          Las estadísticas descriptivas resumen las características principales de tu serie
          en un solo vistazo. Cada indicador cuenta algo diferente:
        </p>
        <p>
          <strong>Media</strong>: el valor promedio de todos los datos. Es el "centro" de la serie.
        </p>
        <p>
          <strong>Desviación estándar</strong>: mide cuánto se alejan los datos de la media.
          Un valor alto indica que los datos son muy variables.
        </p>
        <p>
          <strong>Coeficiente de Variación (CV)</strong>: es la desviación estándar dividida por la
          media. Si CV {'>'} 30%, la serie tiene <strong>alta variabilidad</strong>, lo que puede
          afectar qué distribución estadística se ajusta mejor.
        </p>
      </TeacherNote>

      <TeacherNote title="Dispersión temporal" icon="📈" variant="concepto">
        <p>
          Este gráfico muestra cada dato de tu serie en orden cronológico. Permite identificar
          visualmente:
        </p>
        <p>
          <strong>Tendencias</strong>: si los valores tienden a subir o bajar con el tiempo.
        </p>
        <p>
          <strong>Valores atípicos</strong>: puntos que se alejan mucho del resto.
        </p>
        <p>
          <strong>Estacionalidad</strong>: patrones que se repiten en ciclos regulares.
        </p>
      </TeacherNote>

      <TeacherNote title="Correlograma y autocorrelación" icon="🔗" variant="explicacion">
        <p>
          La <strong>autocorrelación</strong> mide si un valor de la serie depende de los valores
          anteriores. Por ejemplo, si los años de mucha lluvia tienden a seguir a otros años
          de mucha lluvia, hay autocorrelación positiva.
        </p>
        <p>
          El <strong>correlograma</strong> muestra esta relación para diferentes "rezagos" (cuántos
          pasos atrás se compara). La <strong>banda de confianza 95%</strong> (líneas punteadas
          amarillas) indica el rango normal: si una barra sale de la banda, hay autocorrelación
          significativa en ese rezago.
        </p>
        <p>
          ¿Por qué importa? Porque muchos tests estadísticos asumen que los datos son
          <strong> independientes</strong>. Si hay autocorrelación, esos tests pueden dar
          resultados incorrectos.
        </p>
      </TeacherNote>
    </>
  );
}