import streamlit as st

from interfaz import componentes as c

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
st.markdown(c.aviso(c.AVISO_EDUCATIVO), unsafe_allow_html=True)
st.markdown("[Código y metodología en GitHub](https://github.com/luismtz224/ligamx-match-predictor)")
