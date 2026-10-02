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
filas = "".join(
    c.fila_ranking(i, e, v, (v - lo) / (hi - lo) * 100, r.escudo_html(e, 32), nombre=r.nombre(e))
    for i, (e, v) in enumerate(orden.items(), start=1))
st.markdown(f'<div class="lm-stack">{filas}</div>', unsafe_allow_html=True)
st.markdown('<p class="lm-muted" style="margin-top:24px;font-size:14px">Todos los equipos empiezan '
            'en 1500. Gana puntos quien vence a rivales fuertes. Calculado con los partidos '
            'desde 2012.</p>', unsafe_allow_html=True)
