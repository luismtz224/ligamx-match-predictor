import streamlit as st

from interfaz import componentes as c, recursos as r
from interfaz.rejilla import rejilla


def _abrir():
    """Callback del selector: pide abrir el equipo elegido (lo atiende el script)."""
    e = st.session_state.get("sel_rejilla")
    if e:
        st.session_state["abrir_equipo"] = c.SLUG[e]


def md(html):
    st.markdown(html, unsafe_allow_html=True)


# --- /equipos?equipo=<slug> redirige a la página del equipo (oculta): el cambio de página reinicia
# el scroll. Sin parámetro, o con un slug inválido, se muestra la rejilla (y se limpia la URL). ---
slug_url = st.query_params.get("equipo")
abrir = st.session_state.pop("abrir_equipo", None) or (slug_url if r.equipo_de_slug(slug_url) else None)
if abrir:
    st.switch_page("paginas/equipo.py", query_params={"equipo": abrir})
if slug_url is not None:
    st.query_params.clear()

md(c.titulo("Equipos"))
md('<p class="lm-muted" style="margin:0 0 16px">Los 25 equipos con partidos desde 2012. '
   'Toca uno para ver su Elo, su historial y sus rivales.</p>')
st.session_state.pop("sel_rejilla", None)  # el selector siempre llega vacío
st.selectbox("Equipo", r.ordenados(r.equipos().index), index=None, key="sel_rejilla",
             placeholder="Elige un equipo", format_func=r.nombre, on_change=_abrir)
rejilla()
