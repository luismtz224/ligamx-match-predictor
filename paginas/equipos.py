import streamlit as st

from interfaz import componentes as c, recursos as r

st.markdown(c.titulo("Equipos"), unsafe_allow_html=True)
st.markdown(c.aviso("En rediseño: aquí van las páginas de cada equipo (partidos desde 2012). "
                    "Mientras tanto, la lista de los 25.", suave=True), unsafe_allow_html=True)

elo = r.modelo()["elo"]
tarjetas = "".join(c.tarjeta_equipo(e, elo[e], r.escudo_html(e, 48)) for e in sorted(r.equipos().index))
st.markdown('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));'
            f'gap:16px;margin-top:24px">{tarjetas}</div>', unsafe_allow_html=True)
