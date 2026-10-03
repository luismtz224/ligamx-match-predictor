import streamlit as st

from interfaz import componentes as c, recursos as r
from src import grafica, historial as h
from src.equipos import fundacion_posterior, rivalidades_de
from src.formato import fecha_corta, temporada_corta, texto_racha, texto_ultimo_duelo

POR_DEFECTO = "Club America"


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

# --- selector sincronizado con ?equipo=<slug> (enlaces sin recargar) ---
# Un clic en una tarjeta cambia los query params en el servidor pero no la URL del navegador:
# sin reescribirla, la siguiente interacción (p. ej. una pastilla) volvería al equipo anterior.
slug_url = st.query_params.get("equipo")
por_enlace = "sel_equipo" not in st.session_state or st.session_state.get("slug_visto") != slug_url
if por_enlace:
    st.session_state["sel_equipo"] = r.equipo_de_slug(slug_url) or POR_DEFECTO
equipo = st.selectbox("Equipo", todos, key="sel_equipo", format_func=r.nombre)
slug = c.SLUG[equipo]
if por_enlace or slug_url != slug:
    st.query_params["equipo"] = slug  # siempre envía el cambio al navegador
st.session_state["slug_visto"] = slug

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


opciones = [None] + temps
elegida = st.pills("Temporada", opciones, key=f"temp-{slug}", format_func=_etiqueta,
                   selection_mode="single", default=None)
pf = h.filtrar_temporada(pe, elegida)  # None (sin selección) = todas
md('<p class="lm-muted" style="font-size:14px;margin:8px 0 0">El filtro de temporada afecta la gráfica, '
   'el récord, los últimos 10 y los rivales. El Elo actual, la racha y los clásicos son siempre '
   'históricos (desde 2012).</p>')

serie = h.serie_elo(pf)
geo = grafica.geometria(serie)
ext = h.extremos(serie)
md(c.grafica_elo(equipo, nombre, geo, ext,
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
    ultimo = (texto_ultimo_duelo(k["ultimo"], nombre, r.nombre(rival)) if k["ultimo"] else None)
    lista.append(dict(nombre=nombre_clasico, escudo_html=r.escudo_html(rival, 24),
                      rival=r.nombre(rival), n=k["n"], g=k["g"], e=k["e"], p=k["p"], ultimo=ultimo))
md(c.clasicos(lista))
if lista:
    md(LEYENDA_GEP)

# --- rejilla de todos los equipos ---
md(c.encabezado("Todos los equipos"))
with st.container(key="rejilla"):
    for e in todos:
        with st.container(key=f"tarjeta-{c.SLUG[e]}"):
            md(c.tarjeta_equipo(e, elo[e], r.escudo_html(e, 48), seleccionada=e == equipo,
                                nombre=r.nombre(e)))
            st.page_link("paginas/equipos.py", label=r.nombre(e),
                         query_params={"equipo": c.SLUG[e]})
