import streamlit as st

from interfaz import componentes as c

st.markdown(c.titulo("Predice el partido", grad="partido"), unsafe_allow_html=True)
st.markdown(c.aviso("En rediseño: aquí va el predictor con tarjetas, forma, historial y "
                    "explicación.", suave=True), unsafe_allow_html=True)
st.markdown(c.aviso(c.AVISO_EDUCATIVO), unsafe_allow_html=True)
