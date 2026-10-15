import streamlit as st

from interfaz import componentes as c, recursos as r
from src.grafica import geometria_calibracion
from src.resumen_calibracion import (CLASE, FUENTES, NOMBRE_FUENTE, NOMBRE_RESULTADO, RESULTADOS, conclusiones,
                                     filas_detalle, frase_n, resumen, resumen_serie, serie, texto_aria)

AYUDA_EJES = ("Horizontal: la probabilidad que dio el modelo. Vertical: con qué frecuencia sí pasó. "
              "Un punto sobre la diagonal es una predicción bien calibrada.")

st.markdown(c.titulo("Sobre el modelo"), unsafe_allow_html=True)
st.markdown(c.encabezado("Qué tan bueno es"), unsafe_allow_html=True)
st.write("Validación walk-forward: 8 temporadas de prueba (2018/19 a 2025/26, 2,651 partidos), "
         "cada una con un modelo entrenado solo con las temporadas anteriores. "
         "Menor log loss es mejor.")
st.markdown(c.lista_modelos(), unsafe_allow_html=True)
st.write("La regresión logística (el modelo de este dashboard) supera a \"no saber nada\" "
         "(las frecuencias históricas): gana en los 8 folds. **Ningún modelo supera al mercado**: "
         "los momios probablemente incluyen lesiones y alineaciones, que este modelo no ve. Esto se midió "
         "con intervalos de confianza al 95% por bootstrap, y ninguna diferencia contra el "
         "mercado cruza 0.")

# --- calibración: datos de datos/procesados/calibracion.csv (los genera src/exportar_calibracion.py) ---
st.markdown(c.encabezado("Calibración"), unsafe_allow_html=True)
st.write("¿Las probabilidades se parecen a la realidad? Si un modelo dice «60%» en muchos partidos, ¿pasa más o menos "
         "en 60 de cada 100? Eso es la calibración. "
         "Se mide con los mismos partidos fuera de muestra de arriba: se ordenan por la probabilidad que dio el "
         "modelo, se juntan en grupos del mismo tamaño y se compara lo que dijo con lo que pasó.")
tabla = r.calibracion()
if tabla is None:
    st.markdown(c.aviso("La gráfica de calibración no está disponible en este momento.", suave=True),
                unsafe_allow_html=True)
else:
    st.markdown(c.aviso(frase_n(tabla), suave=True), unsafe_allow_html=True)
    st.markdown(c.leyenda_calibracion(), unsafe_allow_html=True)
    figuras = ""
    for resultado in RESULTADOS:
        geo = geometria_calibracion({f: serie(tabla, f, resultado) for f in FUENTES})
        resumenes = [(NOMBRE_FUENTE[f], CLASE[f], resumen_serie(resumen(tabla, f, resultado))) for f in FUENTES]
        detalle = c.detalle_calibracion("Cada punto, con su n", [
            (NOMBRE_FUENTE[f], CLASE[f], filas_detalle(tabla, f, resultado)) for f in FUENTES])
        figuras += c.grafica_calibracion(NOMBRE_RESULTADO[resultado], geo, texto_aria(tabla, resultado), resumenes,
                                         AYUDA_EJES, detalle)
    st.markdown(f'<div class="lm-twocol" style="margin-bottom:24px">{figuras}</div>', unsafe_allow_html=True)
    for frase in conclusiones(tabla):
        st.write(frase)

st.markdown(c.aviso(c.AVISO_EDUCATIVO), unsafe_allow_html=True)
st.markdown("[Código y metodología en GitHub](https://github.com/luismtz224/ligamx-match-predictor)")
