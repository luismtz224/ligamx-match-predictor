import streamlit as st

from interfaz import componentes as c, recursos as r
from src import grafica, historial as h
from src.equipos import fundacion_posterior, rivalidades_de
from src.formato import fecha_corta, temporada_corta, texto_racha, texto_ultimo_duelo


VOLVER = "← Todos los equipos"


def md(html):
    st.markdown(html, unsafe_allow_html=True)


def aviso(texto):
    """Aviso suave con aire arriba y abajo (va suelto entre bloques)."""
    md(f'<div style="margin:16px 0">{c.aviso(texto, suave=True)}</div>')


LEYENDA_GEP = ('<p class="lm-muted" style="margin:8px 0 0;font-size:12px;line-height:16px">G-E-P: '
               'ganados, empatados y perdidos del equipo.</p>')

est = r.modelo()
feat, elo_proc, _ = r.partidos()
elo, activos = est["elo"], est["activos"]
fichas = r.equipos()
todos = r.ordenados(fichas.index)
actual = feat["Season"].max()  # temporada en curso


def pagina_equipo(equipo):
    slug = c.SLUG[equipo]
    nombre = r.nombre(equipo)
    ficha = fichas.loc[equipo]
    pe = h.partidos_equipo(feat, equipo, elo)
    activo = equipo in activos

    md(c.heroe(equipo, nombre, r.escudo_html(equipo, 256, solo=True)))
    md(c.ficha(ficha))
    if len(pe) and fundacion_posterior(ficha["fundacion"], pe["temporada"].iloc[0]):
        ini = pe["temporada"].iloc[0]
        aviso(f"Sus partidos empiezan en {temporada_corta(ini)}, antes de la fundación del club: "
              "probablemente el CSV incluye al equipo anterior.")

    # --- Elo actual (no depende del filtro de temporada) ---
    md(c.encabezado("Elo"))
    md(c.elo_actual(equipo, elo[equipo], activo, h.posicion(equipo, elo, activos), len(activos)))
    if not activo:
        aviso("Sin partidos en la temporada actual.")

    # --- filtro de temporada ---
    temps = h.temporadas(pe)

    def _etiqueta(t):
        if t is None:
            return "Todas"
        return temporada_corta(t) + (" · en curso" if t == actual else "")

    elegida = st.pills("Temporada", [None] + temps, key=f"temp-{slug}", format_func=_etiqueta,
                       selection_mode="single", default=None)
    pf = h.filtrar_temporada(pe, elegida)  # None (sin selección) = todas
    md('<p class="lm-muted" style="font-size:14px;margin:8px 0 0">El filtro de temporada afecta la '
       'gráfica, el récord, los últimos 10 y los rivales. El Elo actual, la racha y los clásicos son '
       'siempre históricos (desde 2012).</p>')

    serie = h.serie_elo(pf)
    md(c.grafica_elo(equipo, nombre, grafica.geometria(serie), h.extremos(serie),
                     etiqueta_final="Hoy" if (elegida is None and activo) else "Final"))

    # --- récord ---
    md(c.encabezado("Récord"))
    md(c.record_equipo(h.record(pf)))

    # --- racha (siempre de hoy) y últimos 10 (filtrados) ---
    md(c.encabezado("Racha y últimos 10"))
    res, n = h.racha(pe)
    if res:
        rotulo = ("Racha actual" if activo else
                  f"Racha en su último partido ({fecha_corta(pe['fecha'].iloc[-1])})")
        md(c.racha_actual(rotulo, texto_racha(res, n)))
    ult = [dict(resultado=p.resultado, fecha=fecha_corta(p.fecha), rival=r.nombre(p.rival),
                marcador=f"{p.gf}–{p.gc}", condicion="Local" if p.local else "Visita")
           for p in h.ultimos(pf, 10).itertuples()]
    md(c.forma(ult, nombre, r.escudo_html(equipo, 24), sm=True))

    # --- rivales (filtrados) ---
    md(c.encabezado("Rivales"))

    def _fila(rival, f):
        return dict(escudo_html=r.escudo_html(rival, 24), nombre=r.nombre(rival), ppp=f.ppp,
                    n=f.n, g=f.g, e=f.e, p=f.p)

    mejores, peores = h.mejores_peores(h.rivales(pf))
    md(c.rivales([_fila(i, f) for i, f in zip(mejores.index, mejores.itertuples())],
                 [_fila(i, f) for i, f in zip(peores.index, peores.itertuples())]))
    md(LEYENDA_GEP)

    # --- clásicos (siempre históricos) ---
    md(c.encabezado("Clásicos"))
    lista = []
    for rival, nombre_clasico in rivalidades_de(equipo, r.rivalidades()):
        k = h.clasico(feat, equipo, rival)
        ultimo = texto_ultimo_duelo(k["ultimo"], nombre, r.nombre(rival)) if k["ultimo"] else None
        lista.append(dict(nombre=nombre_clasico, escudo_html=r.escudo_html(rival, 24),
                          rival=r.nombre(rival), n=k["n"], g=k["g"], e=k["e"], p=k["p"], ultimo=ultimo))
    md(c.clasicos(lista))
    if lista:
        md(LEYENDA_GEP)

    # --- volver: el mismo enlace de arriba, para no tener que subir al terminar de leer. Sin rejilla
    # aquí: al tocar otra tarjeta desde el final de la página no se abría desde arriba. ---
    with st.container(key="volver-abajo"):
        st.page_link("paginas/equipos.py", label=VOLVER)
    md(c.estilo_equipo(equipo))  # colores del equipo sobre la página (al final: no deja hueco arriba)


# --- el equipo viene de ?equipo=<slug>; sin equipo o con un slug inválido se vuelve a la rejilla ---
# Esta página es oculta (st.Page visibility="hidden"): se llega con un cambio de página, y eso
# reinicia el scroll. Las tarjetas y el Ranking enlazan a Equipos (/equipos?equipo=<slug>), que
# redirige aquí. El selector cambia de equipo sin salir de la página (el usuario ya está arriba).
slug_url = st.query_params.get("equipo")
equipo_url = r.equipo_de_slug(slug_url)
if equipo_url is None:
    st.switch_page("paginas/equipos.py")  # también limpia la URL

if "sel_equipo" not in st.session_state or st.session_state.get("slug_visto") != slug_url:
    st.session_state["sel_equipo"] = equipo_url
with st.container(key="volver"):
    st.page_link("paginas/equipos.py", label=VOLVER)
equipo = st.selectbox("Equipo", todos, key="sel_equipo", format_func=r.nombre)
slug = c.SLUG[equipo]
if slug != slug_url:
    st.query_params["equipo"] = slug
st.session_state["slug_visto"] = slug

with st.container(key=f"equipo-{slug}"):
    pagina_equipo(equipo)
