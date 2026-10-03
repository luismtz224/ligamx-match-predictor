"""Rejilla de los 25 equipos (entrada de Equipos)."""
import streamlit as st

from interfaz import componentes as c, recursos as r


def rejilla():
    """Cada tarjeta lleva encima un `st.page_link` transparente a Equipos con ?equipo=<slug>
    (navegación del lado del cliente, sin recarga). Equipos redirige a la página del equipo:
    el cambio de página es lo que reinicia el scroll."""
    elo = r.modelo()["elo"]
    with st.container(key="rejilla"):
        for e in r.ordenados(r.equipos().index):
            with st.container(key=f"tarjeta-{c.SLUG[e]}"):
                st.markdown(c.tarjeta_equipo(e, elo[e], r.escudo_html(e, 48), nombre=r.nombre(e)),
                            unsafe_allow_html=True)
                st.page_link("paginas/equipos.py", label=r.nombre(e), query_params={"equipo": c.SLUG[e]})
