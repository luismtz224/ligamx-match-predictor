import streamlit as st

from interfaz import componentes as c, recursos as r
from src import resumen_temporada as rt
from src.formato import fecha_corta, temporada_corta


def md(html):
    st.markdown(html, unsafe_allow_html=True)


md(c.titulo("Temporadas"))
st.write("Qué predijo la regresión logística en cada temporada, qué pasó y cuántos aciertos tuvo, partido por partido. "
         "Cada temporada se predijo con un modelo entrenado solo con las anteriores. La 2026/27 está en curso y no "
         "entra: todavía no hay una evaluación completa.")
df = r.predicciones()
if df is None:
    md(c.aviso("Las predicciones por temporada no están disponibles en este momento.", suave=True))
    st.stop()

fichas = r.equipos()
temporadas = rt.temporadas(df)
elegida = st.pills("Temporada", temporadas, default=temporadas[-1], required=True, key="temp_sel",
                   format_func=temporada_corta, selection_mode="single")
partidos = rt.de_temporada(df, elegida)

md(c.encabezado(f"Temporada {temporada_corta(elegida)}"))
md(c.resumen_temporada(rt.resumen(partidos), rt.NOMBRE_MODELO))
st.write("Accuracy: de cada 100 partidos, en cuántos el resultado más probable fue el que pasó. Log loss: menor es "
         "mejor. Los dos se calculan igual que en «Sobre el modelo».")
md(c.aviso(f"Una sola temporada tiene unos {len(partidos)} partidos: la diferencia entre la logística y los momios "
           "en una temporada probablemente es ruido.", suave=True))

md(c.encabezado("Partidos"))
filtro = st.pills("Mostrar", rt.FILTROS, default="Todos", required=True, key="temp_filtro", selection_mode="single")
lista = rt.filtrar(partidos, filtro)

# «Ver más» muestra de a 20; el contador vuelve a 20 al cambiar de temporada o de filtro
clave = (elegida, filtro)
if st.session_state.get("temp_clave") != clave:
    st.session_state["temp_clave"] = clave
    st.session_state["temp_n"] = rt.BLOQUE


def _ver_mas():
    st.session_state["temp_n"] += rt.BLOQUE


visibles = rt.bloque_visible(lista, st.session_state["temp_n"])
if lista.empty:
    md(c.aviso("No hay partidos con este filtro.", suave=True))
else:
    def _equipo(llave):
        return llave, r.nombre(llave), fichas.loc[llave, "siglas"]

    md(c.lista_partidos([
        c.tarjeta_partido(fecha_corta(p.fecha), _equipo(p.local), _equipo(p.visitante),
                          (p.goles_local, p.goles_visitante), rt.porcentajes(p._asdict()), p.pred_logistica, p.resultado)
        for p in visibles.itertuples()]))
    md(f'<div class="lm-muted" style="margin:16px 0 8px;font-size:14px;line-height:24px">Mostrando {len(visibles)} de '
       f'{len(lista)} partidos, en orden de fecha.</div>')
    if len(visibles) < len(lista):
        st.button(f"Ver más ({min(rt.BLOQUE, len(lista) - len(visibles))})", on_click=_ver_mas, key="temp_mas")
md(c.aviso(c.AVISO_EDUCATIVO))
