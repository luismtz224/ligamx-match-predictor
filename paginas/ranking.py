import streamlit as st

from interfaz import componentes as c, recursos as r
from src.historial import ranking

est = r.modelo()
elo, activos = est["elo"], est["activos"]
orden = ranking(elo, activos)
# misma escala que la barra anterior: mínimo y máximo redondeados a 50
lo, hi = int(orden.min() // 50 * 50), int(orden.max() // 50 * 50 + 50)

st.markdown(c.titulo("Ranking Elo"), unsafe_allow_html=True)
st.markdown(f'<p class="lm-muted">Equipos activos ({len(activos)})</p>', unsafe_allow_html=True)
with st.container(key="ranking"):
    for i, (e, v) in enumerate(orden.items(), start=1):
        with st.container(key=f"fila-{c.SLUG[e]}"):
            st.markdown(c.fila_ranking(i, e, v, (v - lo) / (hi - lo) * 100, r.escudo_html(e, 32),
                                       nombre=r.nombre(e), enlazada=True), unsafe_allow_html=True)
            st.page_link("paginas/equipos.py", label=r.nombre(e),
                         query_params={"equipo": c.SLUG[e]})
st.markdown('<p class="lm-muted" style="margin-top:24px;font-size:14px">Todos los equipos empiezan '
            'en 1500. Gana puntos quien vence a rivales fuertes. Calculado con los partidos '
            'desde 2012.</p>', unsafe_allow_html=True)
