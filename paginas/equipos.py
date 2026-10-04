import streamlit as st

from interfaz import componentes as c, recursos as r
from interfaz.rejilla import rejilla


def md(html):
    st.markdown(html, unsafe_allow_html=True)


# --- /equipos?equipo=<slug> redirige a la página del equipo (oculta): el cambio de página reinicia
# el scroll. Sin parámetro, o con un slug inválido, se muestra la rejilla (y se limpia la URL).
# La rejilla es el selector: no hay selectbox en esta entrada. ---
slug_url = st.query_params.get("equipo")
if r.equipo_de_slug(slug_url):
    st.switch_page("paginas/equipo.py", query_params={"equipo": slug_url})
if slug_url is not None:
    st.query_params.clear()

md(c.titulo("Equipos"))
md('<p class="lm-muted" style="margin:0 0 16px">Los 25 equipos con partidos desde 2012. '
   'Toca uno para ver su Elo, su historial y sus rivales.</p>')
rejilla()
