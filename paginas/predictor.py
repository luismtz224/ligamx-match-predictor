import streamlit as st

from interfaz import componentes as c, recursos as r
from src.explicacion import contribuciones
from src.formato import fecha_corta, redondear_100
from src.historial import h2h, partidos_equipo, ultimos
from src.imagen import generar_png
from src.prediccion import features_partido, mercado, predecir


def md(html):
    st.markdown(html, unsafe_allow_html=True)


def _forma(feat, equipo):
    """Últimos 5 del equipo (del más viejo al más reciente) para el componente de forma."""
    return [dict(resultado=p.resultado, fecha=fecha_corta(p.fecha), rival=r.nombre(p.rival),
                 marcador=f"{p.gf}–{p.gc}", condicion="Local" if p.local else "Visita")
            for p in ultimos(partidos_equipo(feat, equipo), 5).itertuples()]


@st.cache_data
def _png(local, visita, recursos):  # `recursos` = r.huella_png(...): sin él, un push dejaba la imagen vieja
    est = r.modelo()
    feat, _, _ = r.partidos()
    pct = redondear_100(predecir(est, local, visita))
    _, _, hex_l, hex_v = r.colores_partido(local, visita)
    (g, e, p), duelos = h2h(feat, local, visita, n=1)
    ultimo = None
    if len(duelos):
        u = duelos.iloc[-1]
        loc, vis = (local, visita) if u["local"] else (visita, local)
        ultimo = (f"{fecha_corta(u['fecha'])}, {r.nombre(loc)} {u['goles_local']}–"
                  f"{u['goles_visita']} {r.nombre(vis)}")
    forma = tuple([x["resultado"] for x in _forma(feat, t)] for t in (local, visita))
    return generar_png(r.nombre(local), r.nombre(visita), pct, (hex_l, hex_v),
                       r.ruta_escudo(local), r.ruta_escudo(visita), forma=forma,
                       h2h=dict(g=g, e=e, p=p, ultimo=ultimo),
                       halos=(local in c.HALO, visita in c.HALO))


est = r.modelo()
feat, _, _ = r.partidos()
activos = r.ordenados(est["activos"])

md(c.titulo("Predice el partido", grad="partido"))

c1, c2 = st.columns(2)
idx = activos.index("Club America") if "Club America" in activos else 0
local = c1.selectbox("Local", activos, index=idx, format_func=r.nombre)
with c1:
    md(c.elegido(r.escudo_html(local, 48), r.nombre(local)))
opciones = [e for e in activos if e != local]
idv = opciones.index("Cruz Azul") if "Cruz Azul" in opciones else 0
visita = c2.selectbox("Visitante", opciones, index=idv, format_func=r.nombre)
with c2:
    md(c.elegido(r.escudo_html(visita, 48), r.nombre(visita)))

nl, nv = r.nombre(local), r.nombre(visita)
probs = predecir(est, local, visita)  # (local, empate, visitante)
pct = redondear_100(probs)
css_l, css_v, _, _ = r.colores_partido(local, visita)

md(c.tarjetas_probabilidad(pct, (nl, nv), (css_l, css_v),
                           (r.escudo_html(local, 40), r.escudo_html(visita, 40))))
md(f'<div style="margin-top:24px">{c.barra_apilada(probs, pct, (css_l, css_v))}</div>')

# forma
md(c.encabezado("Forma reciente"))
md(c.forma(_forma(feat, local), nl, r.escudo_html(local, 24))
   + c.forma(_forma(feat, visita), nv, r.escudo_html(visita, 24)))
md('<p class="lm-muted" style="margin-top:8px;font-size:14px">Últimos 5 partidos de cada uno, '
   'el más reciente a la derecha. V gana, E empata, D pierde.</p>')

# historial
md(c.encabezado("Historial"))
gep_l, duelos = h2h(feat, local, visita, n=5)
filas = [(fecha_corta(d.fecha), nl if d.local else nv, d.goles_local, d.goles_visita)
         for d in duelos.iloc[::-1].itertuples()]
md(c.h2h((nl, nv), (css_l, css_v), gep_l, filas))

# por qué
md(c.encabezado("Por qué da este resultado"))
x = features_partido(est, local, visita)
ex = contribuciones(est["modelo"], x)
md('<p class="lm-muted" style="font-size:14px;margin-bottom:16px">Cuánto empuja cada factor hacia '
   'el local o hacia el visitante, comparado con un partido promedio. No explica el empate.</p>')
md(c.factores(list(ex["por_factor"].items()), (css_l, css_v)))
v = x.iloc[0]
num = lambda col, dec=2: "—" if v[col] != v[col] else f"{v[col]:.{dec}f}"  # NaN -> —
datos = [("Elo", num("elo_h", 0), num("elo_a", 0)),
         ("Puntos por partido (últ. 5)", num("pts_h"), num("pts_a")),
         ("Goles a favor (últ. 5)", num("gf_h"), num("gf_a")),
         ("Goles en contra (últ. 5)", num("gc_h"), num("gc_a"))]
lado = "local" if ex["intercepto"] > 0 else "visitante"
imputadas = ""
if ex["imputadas"]:
    imputadas = (f'<p class="lm-muted" style="font-size:14px;margin-top:8px">En este partido se '
                 f'usó la mediana en: {", ".join(ex["imputadas"])}.</p>')
md('<details class="lm-detail" style="margin-top:16px"><summary><span style="font-weight:600">'
   'Ver el detalle</span><span class="lm-detail__hint">Datos del modelo</span></summary>'
   f'<p class="lm-muted" style="font-size:14px;margin-top:8px">Punto de partida (partido promedio): '
   f'{abs(ex["intercepto"]):.2f} hacia el {lado}, por jugar en casa. Las cifras están en la escala '
   f'interna del modelo (log-odds).</p>{c.datos_modelo((nl, nv), datos)}'
   '<p class="lm-muted" style="font-size:14px;margin-top:16px">Si a un equipo le falta historial, '
   f'el modelo usa la mediana de los datos de entrenamiento.</p>{imputadas}</details>')
md(f'<div style="margin-top:16px">{c.aviso("Es la lectura del modelo, no una causa real.", suave=True)}</div>')

# modelo contra mercado
md(c.encabezado("Modelo contra mercado"))
with st.expander("Comparar con los momios (opcional)"):
    st.caption("Los valores iniciales son de ejemplo; escribe los momios del partido.")
    m1, m2, m3 = st.columns(3)
    mh = m1.number_input("Local", min_value=1.01, value=2.00)
    mdd = m2.number_input("Empate", min_value=1.01, value=3.30)
    ma = m3.number_input("Visitante", min_value=1.01, value=3.50)
    mer, margen = mercado(mh, mdd, ma)
    md(c.modelo_vs_mercado([(f"Gana {nl}", probs[0], mer[0]), ("Empate", probs[1], mer[1]),
                            (f"Gana {nv}", probs[2], mer[2])]))
    md(f'<p class="lm-muted" style="font-size:14px;margin-top:8px">Margen de la casa: '
       f'{100 * margen:.1f}%. El mercado se calcula quitando ese margen (1/momio, normalizado).</p>')

st.download_button("Descargar imagen", data=_png(local, visita, r.huella_png(local, visita)),
                   file_name=f"prediccion-{c.SLUG[local]}-vs-{c.SLUG[visita]}.png",
                   mime="image/png")
md(f'<div style="margin-top:24px">{c.aviso(c.AVISO_EDUCATIVO)}</div>')
