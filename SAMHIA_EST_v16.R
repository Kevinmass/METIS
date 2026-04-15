# ==============================================================================
# PROYECTO: SAMHIA - SISTEMA DE ANÁLISIS MULTIVARIABLE (VERSIÓN FINAL EXTENDIDA)
# AUTOR: Dr. Ing. Carlos G. Catalini
# DESCRIPCIÓN: Análisis estadístico completo, explícito y detallado.
# ==============================================================================

# --- 1. INSTALACIÓN Y CARGA DE PAQUETES ---
install_packages_if_missing <- function(packages) {
  for (package in packages) {
    if (!require(package, character.only = TRUE)) {
      tryCatch({
        install.packages(package, dependencies = TRUE)
        library(package, character.only = TRUE)
      }, error = function(e) {
        cat(paste("Advertencia: No se pudo instalar", package, "\n"))
      })
    }
  }
}

pkgs <- c("ggplot2", "dplyr", "lubridate", "readxl", "moments", 
          "gridExtra", "grid", "png", "car", "randtests", 
          "coin", "trend", "zyp", "scales", "exactRankTests")

install_packages_if_missing(pkgs)

# Carga explícita de librerías para asegurar el entorno
library(ggplot2)
library(dplyr)
library(lubridate)
library(gridExtra)
library(grid)
library(moments)
library(png)
library(car)
library(randtests)
library(trend)

# --- 2. FUNCIÓN DE ANÁLISIS DETALLADO (LÓGICA PASO A PASO) ---
analizar_variable_samhia <- function(datos_origen, nombre_variable, nombre_embalse, carpeta_raiz) {
  
  cat(paste("   -> Procesando variable:", nombre_variable, "...\n"))
  
  # ==========================================================================
  # A. PREPARACIÓN, LIMPIEZA Y TRANSFORMACIÓN DE DATOS
  # ==========================================================================
  
  # Crear carpeta de salida específica
  dir_salida <- file.path(carpeta_raiz, nombre_variable)
  if (!dir.exists(dir_salida)) dir.create(dir_salida, recursive = TRUE)
  
  # Selección y Limpieza (Blindaje contra 'nan' de texto y vacíos)
  Archivo <- datos_origen %>%
    select(date, variable_raw = all_of(nombre_variable)) %>%
    mutate(
      date = as.Date(date),
      # Conversión explícita a caracter y luego a numérico para gestionar 'nan'
      variable = suppressWarnings(as.numeric(as.character(variable_raw)))
    ) %>%
    filter(!is.na(date)) %>% 
    arrange(date)
  
  # Vector de cálculo limpio (sin NAs) para tests estadísticos
  variable_calc <- na.omit(Archivo$variable)
  
  # Validación de datos mínimos
  if (length(variable_calc) < 12) {
    cat("      [AVISO] Variable saltada: Menos de 12 datos válidos.\n")
    return(NULL)
  }
  
  # Generación de Variables Temporales
  Archivo$month <- month(Archivo$date)
  Archivo$year <- year(Archivo$date)
  
  # Año Hidrológico (Junio = Inicio)
  Archivo$year_hydrological <- ifelse(month(Archivo$date) >= 6, year(Archivo$date), year(Archivo$date) - 1)
  
  # Reordenar dataframe para gráficos hidrológicos
  Archivo <- arrange(Archivo, year_hydrological)
  
  # Definición de Límites para Gráficos (Eje Y dinámico)
  max_serie <- max(variable_calc)
  min_serie <- min(variable_calc)
  
  if (min_serie >= 0) {
    rango_y <- c(0, max_serie * 1.25)
  } else {
    abs_max <- max(abs(max_serie), abs(min_serie))
    rango_y <- c(-abs_max * 1.25, abs_max * 1.25)
  }
  
  # Cálculo de Intervalos de Confianza (Outliers)
  N <- length(variable_calc)
  Kn <- 0.4083 * log(N) + 1.1584
  media_val <- mean(variable_calc)
  sd_val <- sd(variable_calc)
  limite_superior <- media_val + Kn * sd_val
  limite_inferior <- media_val - Kn * sd_val
  
  # ==========================================================================
  # B. GENERACIÓN DE GRÁFICOS (G1 - G4 y Boxplots)
  # ==========================================================================
  tema_base <- theme_minimal()
  
  # G1: Serie Temporal Completa
  g1 <- ggplot(Archivo, aes(x = date, y = variable)) +
    geom_line(na.rm = TRUE) +
    geom_area(fill = "grey", alpha = 0.5, na.rm = TRUE) +
    geom_smooth(method = "loess", se = FALSE, na.rm = TRUE, color = "blue") +
    labs(title = "Serie Temporal", x = "Fecha", y = nombre_variable) +
    scale_y_continuous(limits = rango_y) +
    tema_base
  
  # G2: Facet por Año Calendario
  g2 <- ggplot(Archivo, aes(x = date, y = variable)) +
    geom_line(na.rm = TRUE) +
    geom_area(fill = "grey", alpha = 0.5, na.rm = TRUE) +
    facet_wrap(~year, scales = "free", labeller = label_both) +
    labs(title = "Gráfico dividido por Año Calendario", x = "Fecha", y = "Variable") +
    scale_x_date(date_labels = "%b") +
    scale_y_continuous(limits = rango_y) +
    tema_base
  
  # G3: Facet por Año Hidrológico
  Archivo$hydro_factor <- factor(Archivo$year_hydrological)
  g3 <- ggplot(Archivo, aes(x = date, y = variable)) +
    geom_line(na.rm = TRUE) +
    geom_area(fill = "grey", alpha = 0.5, na.rm = TRUE) +
    facet_wrap(~hydro_factor, scales = "free") +
    labs(title = "Gráfico dividido por Año Hidrológico", x = "Fecha", y = "Variable") +
    scale_x_date(date_labels = "%b") +
    scale_y_continuous(limits = rango_y) +
    tema_base
  
  # G4: Análisis de Datos Atípicos
  datos_atipicos_df <- Archivo %>% filter(variable > limite_superior | variable < limite_inferior)
  
  g4 <- ggplot(data = Archivo, aes(x = date, y = variable)) +
    geom_line(na.rm = TRUE) +
    geom_hline(yintercept = limite_superior, linetype = "dashed", color = "red") +
    geom_hline(yintercept = limite_inferior, linetype = "dashed", color = "red") +
    geom_point(data = datos_atipicos_df, aes(x=date, y=variable), color = "red", na.rm = TRUE) +
    labs(title = "Análisis de Datos Atípicos", x = "Fecha", y = "Valor") +
    scale_y_continuous(limits = rango_y) +
    tema_base
  
  # Boxplot 1: Mensual Calendario (Ene-Dic)
  month_names <- month.abb
  grafico_boxplot <- ggplot(Archivo, aes(x = factor(month, levels = 1:12, labels = month_names), y = variable)) +
    geom_boxplot(fill = "lightblue", color = "blue", outlier.shape = NA, na.rm = TRUE) +
    labs(title = "Valores Mensuales (Año Calendario)", x = "Mes", y = nombre_variable) +
    tema_base
  
  # Boxplot 2: Mensual Hidrológico (Jun-May)
  orden_jun_jul <- c(6:12, 1:5)
  grafico_boxplot_jun_jul <- ggplot(Archivo, aes(x = factor(month, levels = orden_jun_jul, labels = month_names[orden_jun_jul]), y = variable)) +
    geom_boxplot(fill = "lightgreen", color = "darkgreen", outlier.shape = NA, na.rm = TRUE) +
    labs(title = "Valores Mensuales (Año Hidrológico)", x = "Mes (jun-jul)", y = nombre_variable) +
    tema_base
  
  # Boxplot 3: Anual Hidrológico
  grafico_boxplot_hydrological_year <- ggplot(Archivo, aes(x = factor(year_hydrological), y = variable)) +
    geom_boxplot(fill = "lightblue", color = "blue", outlier.shape = NA, na.rm = TRUE) +
    labs(title = "Box-plot año hidrológico (Anual)", x = "Año Hidrológico", y = nombre_variable) +
    tema_base +
    theme(axis.text.x = element_text(angle = 90, vjust = 0.5))
  
  # ==========================================================================
  # C. GUARDADO DE GRÁFICOS INDIVIDUALES (PNG)
  # ==========================================================================
  ggsave(file.path(dir_salida, paste0("01_SerieTemporal_", nombre_variable, ".png")), g1, width = 10, height = 6)
  ggsave(file.path(dir_salida, paste0("02_AnoCalendario_", nombre_variable, ".png")), g2, width = 10, height = 6)
  ggsave(file.path(dir_salida, paste0("03_AnoHidrologico_", nombre_variable, ".png")), g3, width = 10, height = 6)
  ggsave(file.path(dir_salida, paste0("04_DatosAtipicos_", nombre_variable, ".png")), g4, width = 10, height = 6)
  ggsave(file.path(dir_salida, paste0("05_Boxplot_Mensual_", nombre_variable, ".png")), grafico_boxplot, width = 10, height = 6)
  ggsave(file.path(dir_salida, paste0("06_Boxplot_Hidro_", nombre_variable, ".png")), grafico_boxplot_jun_jul, width = 10, height = 6)
  
  # Gráficos Base (Histograma, QQ, ACF) con dispositivo PNG
  png_file_hist <- file.path(dir_salida, paste0("07_Histograma_", nombre_variable, ".png"))
  png(png_file_hist, width = 600, height = 600)
  try({
    hist(variable_calc, prob=TRUE, main="Histograma y Normal", xlab="Variable", col="gray90")
    curve(dnorm(x, mean=mean(variable_calc), sd=sd(variable_calc)), add=TRUE, col="blue", lwd=2)
  })
  dev.off()
  
  png_file_qq <- file.path(dir_salida, paste0("08_QQPlot_", nombre_variable, ".png"))
  png(png_file_qq, width = 600, height = 600)
  try({
    qqnorm(variable_calc, main = "Q-Q Plot - Normal")
    qqline(variable_calc, col = "blue", lwd=2)
  })
  dev.off()
  
  acf_result <- acf(variable_calc, plot = FALSE)
  png_file_acf <- file.path(dir_salida, paste0("09_Autocorrelacion_", nombre_variable, ".png"))
  png(png_file_acf, width = 800, height = 600)
  try({
    plot(acf_result, main = "Función de Autocorrelación")
  })
  dev.off()
  
  # ==========================================================================
  # D. CÁLCULOS ESTADÍSTICOS Y TESTS (VERBOSIDAD COMPLETA)
  # ==========================================================================
  
  # 1. Estadísticos Descriptivos
  asymmetry <- skewness(variable_calc)
  kurt <- kurtosis(variable_calc)
  var_n_1 <- var(variable_calc)
  coefficient_of_variation <- (sd_val / media_val) * 100
  
  stat_values <- data.frame(
    Estadistica = c("Asimetría", "Kurtosis", "Desv. Estándar", "Varianza (n-1)", "N Datos", "Coef. Variación"),
    Valor = round(c(asymmetry, kurt, sd_val, var_n_1, N, coefficient_of_variation), 4)
  )
  
  summary_stats_table <- data.frame(
    Estadistica = c("Mediana", "Media", "1er Cuartil", "3er Cuartil", "Mínimo", "Máximo"),
    Valor = round(c(median(variable_calc), mean(variable_calc), quantile(variable_calc, 0.25), quantile(variable_calc, 0.75), min(variable_calc), max(variable_calc)), 4)
  )
  combined_stat_table <- rbind(summary_stats_table, stat_values)
  stat_table_grob <- tableGrob(combined_stat_table, rows = NULL, theme = ttheme_default(base_size = 10))
  
  # Tabla Resumen Año Hidrológico
  tabla_informacion <- Archivo %>%
    group_by(year_hydrological) %>%
    summarize(
      Medio = mean(variable, na.rm=TRUE),
      Maximo = max(variable, na.rm=TRUE),
      Minimo = min(variable, na.rm=TRUE)
    )
  
  # 2. Tests de Autocorrelación
  # Durbin-Watson (Manejo explícito de error)
  dw_test <- tryCatch(durbinWatsonTest(lm(variable_calc ~ 1)), error=function(e) NULL)
  
  # Extracción segura de valores (Durbin-Watson a veces usa nombres distintos)
  dw_stat_val <- NA
  dw_p_val <- NA
  if (!is.null(dw_test)) {
    dw_stat_val <- if(!is.null(dw_test$dw)) dw_test$dw else dw_test$statistic
    dw_p_val <- if(!is.null(dw_test$p)) dw_test$p else dw_test$p.value
  }
  
  # Ljung-Box
  lb_test <- tryCatch(Box.test(variable_calc, lag = 12, type = "Ljung-Box"), error=function(e) NULL)
  lb_stat_val <- if(!is.null(lb_test)) lb_test$statistic else NA
  lb_p_val <- if(!is.null(lb_test)) lb_test$p.value else NA
  
  
  # 3. Test de Independencia ANDERSON
  result_anderson <- tryCatch(cor.test(variable_calc[-N], variable_calc[-1], method = "pearson"), error=function(e) NULL)
  conclusion_anderson <- "Error o datos insuficientes"
  if (!is.null(result_anderson) && !is.na(result_anderson$p.value)) {
    if (result_anderson$p.value < 0.05) {
      conclusion_anderson <- "Hay evidencia para rechazar la hipótesis nula de independencia."
    } else {
      conclusion_anderson <- "No hay suficiente evidencia para rechazar la hipótesis nula de independencia."
    }
  }
  
  # 4. Test de Independencia WALD-WOLFOWITZ
  test_ww <- tryCatch(runs.test(variable_calc), error=function(e) NULL)
  conclusion_ww <- "Error o datos insuficientes"
  if (!is.null(test_ww) && !is.na(test_ww$p.value)) {
    if (test_ww$p.value < 0.05) {
      conclusion_ww <- "Hay evidencia para rechazar la hipótesis nula de independencia."
    } else {
      conclusion_ww <- "No hay suficiente evidencia para rechazar la hipótesis nula de independencia."
    }
  }
  
  # 5. Test de Independencia SPEARMAN
  test_spearman <- tryCatch(cor.test(variable_calc[-N], variable_calc[-1], method = "spearman"), error=function(e) NULL)
  conclusion_spearman <- "Error o datos insuficientes"
  if (!is.null(test_spearman) && !is.na(test_spearman$p.value)) {
    if (test_spearman$p.value < 0.05) {
      conclusion_spearman <- "Hay evidencia para rechazar la hipótesis nula de independencia."
    } else {
      conclusion_spearman <- "No hay suficiente evidencia para rechazar la hipótesis nula de independencia."
    }
  }
  
  # 6. Test de Homogeneidad MANN-WHITNEY
  n_obs <- length(variable_calc)
  half_point <- n_obs %/% 2
  group <- factor(rep(c("Primera Mitad", "Segunda Mitad"), times = c(half_point, n_obs - half_point)))
  
  test_mann_whitney <- tryCatch(wilcox.test(variable_calc ~ group), error=function(e) NULL)
  conclusion_mw <- "Error o datos insuficientes"
  if (!is.null(test_mann_whitney) && !is.na(test_mann_whitney$p.value)) {
    if (test_mann_whitney$p.value < 0.05) {
      conclusion_mw <- "Hay evidencia para rechazar la hipótesis nula de homogeneidad."
    } else {
      conclusion_mw <- "No hay evidencia suficiente para rechazar homogeneidad."
    }
  }
  
  # 7. Test de Homogeneidad MOOD
  test_mood <- tryCatch(mood.test(variable_calc ~ group), error=function(e) NULL)
  conclusion_mood <- "Error o datos insuficientes"
  if (!is.null(test_mood) && !is.na(test_mood$p.value)) {
    if (test_mood$p.value < 0.05) {
      conclusion_mood <- "Hay evidencia para rechazar la hipótesis nula de homogeneidad."
    } else {
      conclusion_mood <- "No hay evidencia suficiente para rechazar homogeneidad."
    }
  }
  
  # 8. Tests de Tendencia MANN-KENDALL
  mk_trend <- tryCatch(mk.test(variable_calc), error=function(e) NULL)
  conclusion_mk <- "Error o datos insuficientes"
  mk_tau_val <- NA
  if (!is.null(mk_trend) && !is.na(mk_trend$p.value)) {
    mk_tau_val <- mk_trend$estimates[3]
    if (mk_trend$p.value < 0.05) {
      conclusion_mk <- "Hay evidencia significativa de tendencia."
    } else {
      conclusion_mk <- "No hay evidencia suficiente de tendencia."
    }
  }
  
  # Wald-Wolfowitz Trend (Runs)
  conclusion_ww_trend <- "Error o datos insuficientes"
  if (!is.null(test_ww) && !is.na(test_ww$p.value)) {
    if (test_ww$p.value < 0.05) {
      conclusion_ww_trend <- "Hay evidencia de tendencia (no aleatoriedad)."
    } else {
      conclusion_ww_trend <- "No hay evidencia suficiente de tendencia."
    }
  }
  
  # ==========================================================================
  # E. GENERACIÓN DEL PDF (ESTRUCTURA DE 10 PÁGINAS)
  # ==========================================================================
  
  pdf_filename <- file.path(dir_salida, paste0("REPORTE_FINAL_", nombre_embalse, "_", nombre_variable, ".pdf"))
  pdf(pdf_filename, width = 14, height = 8)
  
  # --- PÁGINA 1: CARÁTULA INSTITUCIONAL ---
  grid.newpage()
  # Marco doble decorativo
  grid.rect(gp = gpar(lwd = 4, col = "darkblue", fill = NA))
  grid.rect(x = 0.5, y = 0.5, width = 0.96, height = 0.96, gp = gpar(lwd = 1, col = "black", fill = NA))
  
  # Títulos Institucionales
  grid.text("UNIVERSIDAD CATÓLICA DE CÓRDOBA", y = 0.85, gp = gpar(fontsize = 24, fontface = "bold", col = "darkred"))
  grid.text("GRUPO DE ESTUDIOS HIDROLÓGICOS EN\nCUENCAS POBREMENTE AFORADAS (EHCPA)", y = 0.75, gp = gpar(fontsize = 18, fontface = "bold", col = "black"))
  
  # Título del Proyecto
  grid.text("SISTEMA SAMHIA", y = 0.60, gp = gpar(fontsize = 32, fontface = "bold", col = "darkblue"))
  grid.text("REPORTE DE ANÁLISIS ESTADÍSTICO", y = 0.53, gp = gpar(fontsize = 20))
  
  # Detalles del Reporte
  grid.text(paste("Embalse:", nombre_embalse), y = 0.40, gp = gpar(fontsize = 16))
  grid.text(paste("Variable Analizada:", nombre_variable), y = 0.35, gp = gpar(fontsize = 16, fontface="bold"))
  
  # Autoría y Fecha
  grid.text("Autor: Dr. Ing. Carlos G. Catalini", y = 0.20, gp = gpar(fontsize = 14, fontface="italic"))
  grid.text(paste("Fecha de Generación:", Sys.Date()), y = 0.10, gp = gpar(fontsize = 10, col = "gray40"))
  
  # --- PÁGINA 2: GRÁFICOS COMBINADOS ---
  # No duplicamos página de gráficos sueltos, vamos directo a la combinada
  grid.newpage()
  grid.draw(arrangeGrob(
    arrangeGrob(g1, g2, ncol = 2),
    arrangeGrob(g3, g4, ncol = 2),
    ncol = 1
  ))
  
  # --- PÁGINA 3: RESUMEN ESTADÍSTICO Y OUTLIERS ---
  grid.newpage()
  grid.text("\nResumen Estadístico Descriptivo:\n", x = 0.1, y = 0.95, just = "left")
  grid.draw(stat_table_grob)
  
  if (nrow(datos_atipicos_df) > 0) {
    grid.text("\nIdentificación de Datos Atípicos (Muestra primeros 20):\n", x = 0.5, y = 0.95, just = "left")
    tabla_outliers <- tableGrob(head(datos_atipicos_df, 20), rows = NULL, theme = ttheme_default(base_size = 8))
    grid.draw(arrangeGrob(nullGrob(), tabla_outliers, ncol = 2))
  } else {
    grid.text("\nSin Datos Atípicos detectados bajo criterio normal.\n", x = 0.5, y = 0.9, just = "left")
  }
  
  # --- PÁGINA 4: BOXPLOTS ---
  grid.newpage()
  grid.draw(arrangeGrob(
    arrangeGrob(grafico_boxplot, grafico_boxplot_jun_jul, ncol = 1),
    grafico_boxplot_hydrological_year,
    ncol = 2
  ))
  
  # --- PÁGINA 5: TABLAS RESUMEN AÑO HIDROLÓGICO ---
  grid.newpage()
  grid.text("\nTablas Resumen Año Hidrológico:\n", x = 0.1, y = 0.9, just = "left")
  if (nrow(tabla_informacion) > 25) {
    grid.table(head(tabla_informacion, 25))
    grid.text("(Tabla truncada a 25 filas por espacio)", x = 0.1, y = 0.1, just = "left")
  } else {
    grid.table(tabla_informacion)
  }
  
  # --- PÁGINA 6: NORMALIDAD VISUAL (PNG) ---
  # IMPORTANTE: No llamar a grid.newpage() al final de esta sección para evitar hojas en blanco
  grid.newpage()
  
  img_hist_raster <- if(file.exists(png_file_hist)) rasterGrob(readPNG(png_file_hist), interpolate = TRUE) else nullGrob()
  img_qq_raster <- if(file.exists(png_file_qq)) rasterGrob(readPNG(png_file_qq), interpolate = TRUE) else nullGrob()
  
  grid.text("Análisis de Normalidad Visual", x=0.5, y=0.95, gp=gpar(fontsize=14))
  grid.arrange(img_hist_raster, img_qq_raster, ncol=2)
  
  # --- PÁGINA 7: AUTOCORRELACIÓN ---
  grid.newpage()
  img_acf_raster <- if(file.exists(png_file_acf)) rasterGrob(readPNG(png_file_acf), interpolate = TRUE) else nullGrob()
  grid.arrange(img_acf_raster, top = textGrob("Autocorrelación", gp=gpar(fontsize=14)))
  
  # Tabla estadística de autocorrelación
  txt_dw <- paste("Durbin-Watson:", round(dw_stat_val, 4), " (p:", round(dw_p_val, 4), ")")
  txt_lb <- paste("Ljung-Box:", round(lb_stat_val, 4), " (p:", round(lb_p_val, 4), ")")
  grid.text(paste(txt_dw, "\n", txt_lb), x=0.5, y=0.1)
  
  # --- PÁGINA 8: TEST DE INDEPENDENCIA ---
  grid.newpage()
  grid.text("TEST DE INDEPENDENCIA", x = 0.5, y = 0.95, just = "center", gp = gpar(fontsize = 14, fontface = "bold"))
  
  # Anderson
  t_val <- if(!is.null(result_anderson)) round(result_anderson$statistic, 4) else "NA"
  p_val <- if(!is.null(result_anderson)) round(result_anderson$p.value, 4) else "NA"
  txt_anderson <- paste0("\nTest de Independencia de Anderson (Pearson):\n",
                         "Estadístico (t): ", t_val, "\np-value: ", p_val, "\nConclusión: ", conclusion_anderson)
  grid.text(txt_anderson, x = 0.1, y = 0.8, just = "left")
  
  # Wald-Wolfowitz
  t_val <- if(!is.null(test_ww)) round(test_ww$statistic, 4) else "NA"
  p_val <- if(!is.null(test_ww)) round(test_ww$p.value, 4) else "NA"
  txt_ww <- paste0("\nTest de Independencia de Wald-Wolfowitz (Runs):\n",
                   "Estadístico (Z): ", t_val, "\np-value: ", p_val, "\nConclusión: ", conclusion_ww)
  grid.text(txt_ww, x = 0.1, y = 0.6, just = "left")
  
  # Spearman
  t_val <- if(!is.null(test_spearman)) round(test_spearman$estimate, 4) else "NA"
  p_val <- if(!is.null(test_spearman)) round(test_spearman$p.value, 4) else "NA"
  txt_spearman <- paste0("\nTest de Coeficiente de Spearman:\n",
                         "Estadístico (rho): ", t_val, "\np-value: ", p_val, "\nConclusión: ", conclusion_spearman)
  grid.text(txt_spearman, x = 0.1, y = 0.4, just = "left")
  
  # --- PÁGINA 9: TEST DE HOMOGENEIDAD ---
  grid.newpage()
  grid.text("TEST DE HOMOGENEIDAD (Mitad vs Mitad)", x = 0.5, y = 0.95, just = "center", gp = gpar(fontsize = 14, fontface = "bold"))
  
  # Mann-Whitney
  t_val <- if(!is.null(test_mann_whitney)) round(test_mann_whitney$statistic, 4) else "NA"
  p_val <- if(!is.null(test_mann_whitney)) round(test_mann_whitney$p.value, 4) else "NA"
  txt_mw <- paste0("\nTest de Mann-Whitney:\n",
                   "Estadístico (W): ", t_val, "\np-value: ", p_val, "\nConclusión: ", conclusion_mw)
  grid.text(txt_mw, x = 0.1, y = 0.8, just = "left")
  
  # Mood
  t_val <- if(!is.null(test_mood)) round(test_mood$statistic, 4) else "NA"
  p_val <- if(!is.null(test_mood)) round(test_mood$p.value, 4) else "NA"
  txt_mood <- paste0("\nTest de Mood:\n",
                     "Estadístico (Z): ", t_val, "\np-value: ", p_val, "\nConclusión: ", conclusion_mood)
  grid.text(txt_mood, x = 0.1, y = 0.5, just = "left")
  
  # --- PÁGINA 10: TEST DE ESTACIONALIDAD / TENDENCIA ---
  grid.newpage()
  grid.text("TEST DE ESTACIONALIDAD / TENDENCIA", x = 0.5, y = 0.95, just = "center", gp = gpar(fontsize = 14, fontface = "bold"))
  
  # Mann-Kendall
  mk_tau_disp <- if(!is.na(mk_tau_val)) round(mk_tau_val, 4) else "NA"
  p_val <- if(!is.null(mk_trend)) round(mk_trend$p.value, 4) else "NA"
  txt_mk <- paste0("\nPrueba de Tendencia Mann-Kendall:\n",
                   "Estadístico (tau): ", mk_tau_disp, "\np-value: ", p_val, "\nConclusión: ", conclusion_mk)
  grid.text(txt_mk, x = 0.1, y = 0.8, just = "left")
  
  # Wald-Wolfowitz Trend
  t_val <- if(!is.null(test_ww)) round(test_ww$statistic, 4) else "NA"
  p_val <- if(!is.null(test_ww)) round(test_ww$p.value, 4) else "NA"
  txt_ww_trend <- paste0("\nPrueba de Tendencia Wald-Wolfowitz:\n",
                         "Estadístico: ", t_val, "\np-value: ", p_val, "\nConclusión: ", conclusion_ww_trend)
  grid.text(txt_ww_trend, x = 0.1, y = 0.5, just = "left")
  
  dev.off() # Cerrar PDF
  cat(paste("      -> Reporte guardado con éxito:", pdf_filename, "\n"))
}

# ==============================================================================
# 3. BUCLE PRINCIPAL DE EJECUCIÓN
# ==============================================================================

# LISTA DE ARCHIVOS (Agrega aquí tus archivos XLSX o CSV)
lista_archivos <- c(
  "UCC-DAT-ESR-AH-001-26-00.xlsx",              # Archivo 1
  "UCC-DAT-ELM-AH-001-26-00.xlsx",              # Archivo 2
  "UCC-DAT-EMB-AH-001-26-00.xlsx"               # Archivo 3
)

# Carpeta Maestra de Salida
ruta_resultados <- file.path(getwd(), "SAMHIA_Resultados_Est")
if (!dir.exists(ruta_resultados)) dir.create(ruta_resultados)

cat("========================================================\n")
cat(" SISTEMA SAMHIA: INICIANDO PROCESAMIENTO MASIVO \n")
cat("========================================================\n")

for (archivo in lista_archivos) {
  
  if (!file.exists(archivo)) {
    cat(paste("\n[ERROR] El archivo no se encuentra:", archivo, "\n"))
    next
  }
  
  nombre_embalse <- tools::file_path_sans_ext(basename(archivo))
  cat(paste("\n>> ANALIZANDO ARCHIVO:", archivo, "\n"))
  
  # Lectura Inteligente (CSV o Excel)
  if (grepl("\\.csv$", archivo)) {
    datos <- tryCatch(
      read.csv(archivo, na.strings = c("NA", "nan", "NaN", ""), stringsAsFactors = FALSE),
      error = function(e) read.csv2(archivo, na.strings = c("NA", "nan", "NaN", ""), stringsAsFactors = FALSE)
    )
  } else {
    datos <- read_excel(archivo)
  }
  
  # Detección de columnas numéricas
  cols_numericas <- names(datos)[sapply(datos, is.numeric)]
  
  # Si falla detección por 'nan', asumimos todas menos fechas
  if(length(cols_numericas) < 2) {
    cols_numericas <- setdiff(names(datos), c("date", "fecha", "Date", "Fecha"))
  }
  
  cols_excluir <- c("date", "year", "month", "day", "fecha", "año", "mes", "year_hydrological")
  cols_analisis <- cols_numericas[!cols_numericas %in% cols_excluir]
  
  cat(paste("   Variables detectadas para análisis:", length(cols_analisis), "\n"))
  
  # Loop por cada variable
  for (var in cols_analisis) {
    tryCatch({
      analizar_variable_samhia(datos, var, nombre_embalse, file.path(ruta_resultados, nombre_embalse))
    }, error = function(e) {
      cat(paste("   [ERROR CRÍTICO] en variable", var, ":", e$message, "\n"))
      if(!is.null(dev.list())) dev.off()
    })
  }
}

cat("\n========================================================\n")
cat(" PROCESO SAMHIA FINALIZADO \n")
cat(paste(" Resultados en:", ruta_resultados, "\n"))
cat("========================================================\n")