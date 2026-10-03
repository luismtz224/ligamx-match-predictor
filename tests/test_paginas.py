import re
from html import escape
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from interfaz import componentes as c
from interfaz.componentes import SLUG
from interfaz.recursos import escudo_html, modelo, nombre, ordenados
from src.formato import redondear_100
from src.prediccion import mercado, predecir
from src.equipos import cargar_equipos

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = ["paginas/predictor.py", "paginas/equipos.py", "paginas/ranking.py",
           "paginas/sobre_modelo.py"]


CON_ENLACES = {"paginas/equipos.py", "paginas/ranking.py"}  # usan st.page_link: necesitan st.navigation


def _correr(ruta, equipo=None):
    """Corre una página. Las que tienen page_link se corren dentro de app.py (switch_page);
    `equipo` es el slug de ?equipo=."""
    if ruta in CON_ENLACES:
        at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60).run()
        if equipo:
            at.query_params["equipo"] = equipo
        at = at.switch_page(ruta).run()
    else:
        at = AppTest.from_file(str(RAIZ / ruta), default_timeout=60)
        if equipo:
            at.query_params["equipo"] = equipo
        at = at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _html(at):
    return "".join(m.value for m in at.markdown)


@pytest.mark.parametrize("ruta", PAGINAS)
def test_pagina_sin_excepciones(ruta):
    assert _html(_correr(ruta))


def test_app_navegacion_css_y_pie():
    at = _correr("app.py")
    html = _html(at)
    assert "--team-chiapas" in html and ".lm-pcard" in html  # CSS inyectado
    assert c.AVISO_ESCUDOS in html  # pie con el aviso de escudos
    assert "Predice el" in html  # página por defecto: Predictor


def test_ranking_mismo_orden_y_cifras_que_el_modelo():
    est = modelo()
    esperado = sorted(est["activos"], key=lambda e: -est["elo"][e])
    html = _html(_correr("paginas/ranking.py"))
    filas = re.findall(r'class="lm-elo[^"]*".*?<span style="font-weight:600">(.*?)</span>'
                       r'<span class="lm-elo__v">(\d+)</span>', html)
    assert [n for n, _ in filas] == [escape(nombre(e)) for e in esperado]  # nombre mostrado
    assert "Club América" in html and "CD Guadalajara" in html and "Pumas UNAM" in html
    assert "Club America" not in html and "Guadalajara Chivas" not in html
    assert [int(v) for _, v in filas] == [round(est["elo"][e]) for e in esperado]


def test_sobre_el_modelo_tiene_cifras_aviso_y_enlace():
    html = _html(_correr("paginas/sobre_modelo.py"))
    for cifra in ["1.0037", "50.85%", "1.0115", "1.0281", "1.0474", "1.0670", "45.61%"]:
        assert cifra in html
    assert c.AVISO_EDUCATIVO in html and "2,651 partidos" in html


def test_equipos_lista_los_25():
    html = _html(_correr("paginas/equipos.py"))
    assert len(re.findall(r'class="lm-team( is-sel)?"', html)) == 25
    assert html.count("lm-team is-sel") == 1  # el equipo elegido


def test_equipos_ordenados_por_nombre_mostrado():
    html = _html(_correr("paginas/equipos.py"))
    nombres = re.findall(r'<div style="font-weight:600">(.*?)</div><div class="lm-team__elo">', html)
    esperado = [escape(nombre(e)) for e in ordenados(cargar_equipos().index)]
    assert nombres == esperado and len(nombres) == 25
    assert nombres.index("Querétaro") < nombres.index("Santos Laguna")
    assert "Mazatlán FC" in nombres and "Mazatlan FC" not in nombres


def test_alt_del_escudo():
    """alt="" cuando el nombre va al lado; el nombre solo cuando el escudo va solo."""
    assert 'alt=""' in escudo_html("Club America", 32)
    assert 'alt="Club América"' in escudo_html("Club America", 32, solo=True)
    assert 'alt="CD Guadalajara"' in escudo_html("Guadalajara Chivas", 48, solo=True)
    for ruta in ("paginas/ranking.py", "paginas/equipos.py", "paginas/predictor.py"):
        html = _html(_correr(ruta))
        alts = re.findall(r'<img [^>]*alt="([^"]*)"', html)
        # en Equipos, el escudo del héroe va solo (sin nombre al lado) y lleva el nombre
        permitidos = {"", "Club América"} if ruta == "paginas/equipos.py" else {""}
        assert alts and set(alts) == permitidos, ruta


# (local, visitante, variable CSS esperada del visitante)
PARES = [("Club America", "Cruz Azul", "var(--team-cruz-azul)"),    # colores distintos
         ("Toluca", "Necaxa", "var(--team-necaxa-2)"),              # mismo rojo: usa su -2
         ("Guadalajara Chivas", "Atlas", "var(--ink)")]             # su -2 es el gris del empate


@pytest.mark.parametrize("local,visita,color_v", PARES)
def test_predictor_tres_pares(local, visita, color_v):
    at = AppTest.from_file(str(RAIZ / "paginas/predictor.py"), default_timeout=60).run()
    at.selectbox[0].set_value(local).run()
    at.selectbox[1].set_value(visita).run()
    assert not at.exception, [e.value for e in at.exception]
    assert [s.value for s in at.selectbox] == [local, visita]
    html = _html(at)
    probs = predecir(modelo(), local, visita)
    pct = [int(v) for v in re.findall(r'class="lm-pct" style="--v:(\d+)"', html)]
    assert pct == redondear_100(probs) and sum(pct) == 100
    assert html.count("lm-pcard is-top") == 1
    # la barra usa los valores sin redondear
    w = [float(v) for v in re.findall(r'<i style="--w:([\d.]+);', html)]
    assert w == [round(100 * p, 1) for p in probs]
    assert f"--c:{color_v}" in html and f"--team:var(--team-{SLUG[local]})" in html
    for texto in (escape(nombre(local)), escape(nombre(visita)), "Forma reciente", "Historial",
                  "Es la lectura del modelo, no una causa real.", "No explica el empate",
                  "Si a un equipo le falta historial", c.AVISO_EDUCATIVO, "duelos desde 2012"):
        assert texto in html, texto
    assert html.count('class="lm-factor"') == 4
    assert html.count("lm-dot") == 10
    assert len(at.get("download_button")) == 1
    assert chr(10) not in html  # HTML en una línea


def test_predictor_momios_y_mercado():
    at = AppTest.from_file(str(RAIZ / "paginas/predictor.py"), default_timeout=60).run()
    at.number_input[0].set_value(2.5).run()
    html = _html(at)
    assert not at.exception
    mer, margen = mercado(2.5, 3.30, 3.50)
    assert f"{100 * mer[0]:.1f}%" in html and f"Margen de la casa: {100 * margen:.1f}%" in html
    captions = "".join(x.value for x in at.caption)
    assert "Los valores iniciales son de ejemplo; escribe los momios del partido." in captions
    assert re.search(r'lm-odds__d (up|down)">[+−]\d+\.\d pp', html)


# ===== Fase 5: página de Equipos =====
import pandas as pd  # noqa: E402

from interfaz.recursos import equipo_de_slug, partidos  # noqa: E402
from src import historial as hs  # noqa: E402
from src.equipos import cargar_rivalidades, rivalidades_de  # noqa: E402
from src.formato import fecha_corta, temporada_corta, texto_racha  # noqa: E402


def _eq(slug):
    at = _correr("paginas/equipos.py", equipo=slug)
    return at, _html(at)


def _aria(html):
    return re.search(r'aria-label="(Elo de [^"]*)"', html).group(1)


def _resumen(html, etiqueta):
    """Cifra de la dl del resumen de la gráfica (Máximo, Mínimo, Inicio, Hoy/Final)."""
    return int(re.search(rf"<dt>{etiqueta}</dt><dd>([\d,]+)<small>", html).group(1).replace(",", ""))


def test_equipos_toluca_activo():
    at, html = _eq("toluca")
    est = modelo()
    feat, elo, _ = partidos()
    assert at.selectbox[0].value == "Toluca"
    pos = hs.posicion("Toluca", est["elo"], est["activos"])
    assert ">Elo actual<" in html and f"{est['elo']['Toluca']:,.0f}" in html
    assert f"Posición {pos} de {len(est['activos'])} activos" in html
    assert "Sin partidos en la temporada actual" not in html and "Racha actual" in html
    assert "antes de la fundación" not in html and "El trazo se corta" not in html
    # el último valor de la gráfica es el Elo del modelo
    assert _resumen(html, "Hoy") == round(est["elo"]["Toluca"])
    assert f"a {est['elo']['Toluca']:,.0f} en sep 2026" in _aria(html)
    assert 'alt="Toluca"' in html  # el escudo del héroe va solo: lleva el nombre


def test_equipos_chiapas_inactivo():
    at, html = _eq("chiapas")
    feat, elo, _ = partidos()
    est = modelo()
    pe = hs.partidos_equipo(feat, "Chiapas", elo)
    assert ">Elo final<" in html and ">Elo actual<" not in html and "Posición" not in html
    assert "Sin partidos en la temporada actual." in html
    assert f"Racha en su último partido ({fecha_corta(pe['fecha'].iloc[-1])})" in html
    assert "Racha actual" not in html and "<dt>Final</dt>" in html and "<dt>Hoy</dt>" not in html
    assert _resumen(html, "Final") == round(est["elo"]["Chiapas"])
    pills = at.get("button_group")[0]
    assert pills.options[-1] == "2016/17"  # no juega 2026/27 (etiquetas ya formateadas)
    assert "en curso" not in " ".join(pills.options)
    assert pills.options[0] == "Todas"


def test_equipos_atl_san_luis_hueco_y_fundacion():
    at, html = _eq("san-luis")
    est = modelo()
    assert at.selectbox[0].value == "Atl. San Luis"
    assert "Sus partidos empiezan en 2012/13, antes de la fundación del club: probablemente" in html
    assert "El trazo se corta donde el equipo no jugó (más de un año)." in html
    assert html.count('class="ln"') == 1 and html.count(" M") + html.count('d="M') >= 1
    d = re.search(r'<path class="ln" pathLength="1" d="([^"]*)"', html).group(1)
    assert d.count("M") == 2
    assert _resumen(html, "Hoy") == round(est["elo"]["Atl. San Luis"])
    # el aviso de fundación no sale en equipos fundados antes de 2012
    assert "antes de la fundación" not in _eq("toluca")[1]


def test_equipos_query_param_selecciona_y_slug_invalido_cae_al_defecto():
    assert _eq("cruz-azul")[0].selectbox[0].value == "Cruz Azul"
    for malo in ("xyz", "", "Toluca"):
        at, html = _eq(malo)
        assert at.selectbox[0].value == "Club America" and "Club América" in html
    at = _correr("paginas/equipos.py")  # sin parámetro
    assert at.selectbox[0].value == "Club America"
    assert at.query_params["equipo"] == ["america"]  # la URL queda con el equipo mostrado


def test_equipos_cambiar_el_selector_actualiza_la_url_y_el_equipo():
    at = _correr("paginas/equipos.py", equipo="toluca")
    at.selectbox[0].set_value("Atlas").run()
    assert not at.exception and at.selectbox[0].value == "Atlas"
    assert at.query_params["equipo"] == ["atlas"] and "Atlas" in _html(at)


def test_equipos_la_rejilla_tiene_25_enlaces_con_su_slug():
    at, _ = _eq("toluca")
    enlaces = at.get("page_link")
    assert len(enlaces) == 25
    slugs = [e.proto.query_string.split("=", 1)[1] for e in enlaces]
    assert sorted(slugs) == sorted(c.SLUG.values())
    for e in enlaces:
        assert equipo_de_slug(e.proto.query_string.split("=", 1)[1]) is not None
        assert e.proto.page == "equipos"


def test_ranking_18_enlaces_con_su_slug_y_query_params():
    at = _correr("paginas/ranking.py")
    est = modelo()
    enlaces = at.get("page_link")
    assert len(enlaces) == 18
    esperado = [c.SLUG[e] for e in sorted(est["activos"], key=lambda e: -est["elo"][e])]
    assert [e.proto.query_string for e in enlaces] == [f"equipo={s}" for s in esperado]
    assert {equipo_de_slug(s) for s in esperado} == set(est["activos"])
    assert all(e.proto.page == "equipos" for e in enlaces)
    assert [nombre(equipo_de_slug(s)) for s in esperado] == [e.proto.label for e in enlaces]


def test_equipos_filtro_de_temporada_afecta_lo_que_debe_y_no_lo_demas():
    feat, elo, _ = partidos()
    est = modelo()
    base_at, base = _eq("toluca")
    at = base_at
    pills = at.get("button_group")[0]
    pills.set_value("2025/2026").run()
    assert not at.exception, [e.value for e in at.exception]
    html = _html(at)
    pe = hs.partidos_equipo(feat, "Toluca", elo)
    pf = hs.filtrar_temporada(pe, "2025/2026")
    # afectan: gráfica, récord, últimos 10 y rivales
    assert f"de {pf['elo_antes'].iloc[0]:,.0f} en {fecha_corta(pf['fecha'].iloc[0])[3:]}" in _aria(html)
    assert _aria(html) != _aria(base)
    rec = hs.record(pf)
    for lado, i in (("Local", 0), ("Visitante", 1)):
        assert f"<dt>Partidos</dt><dd>{int(rec.loc[lado, 'PJ'])}</dd>" in html
    assert "<dt>Partidos</dt><dd>274</dd>" in base and "<dt>Partidos</dt><dd>274</dd>" not in html
    forma = re.search(r'class="lm-forma".*?Rivales', html, re.S).group(0)
    for f in hs.ultimos(pf, 10)["fecha"]:
        assert fecha_corta(f) in forma  # los últimos 10 son de la temporada elegida
    assert fecha_corta(pe["fecha"].iloc[-1]) not in forma  # y no los de 2026/27
    assert html.count('class="lm-duel"') != base.count('class="lm-duel"')  # rivales/últimos cambian
    # no afectan: Elo actual, posición, racha y clásicos
    for texto in (f"{est['elo']['Toluca']:,.0f}</div>", "Posición", "Racha actual",
                  texto_racha(*hs.racha(pe))):
        assert texto in html, texto
    clasicos_base = re.search(r"Clásicos.*?Todos los equipos", base, re.S).group(0)
    clasicos_filtrado = re.search(r"Clásicos.*?Todos los equipos", html, re.S).group(0)
    assert clasicos_base == clasicos_filtrado
    assert "<dt>Final</dt>" in html  # con filtro, la última cifra ya no es «Hoy»


def test_equipos_filtro_a_una_temporada_sin_rivales_con_6_duelos():
    at, _ = _eq("toluca")
    at.get("button_group")[0].set_value("2025/2026").run()
    assert "Sin suficientes duelos" in _html(at)  # casi ningún equipo tiene 6 duelos en una temporada


def test_equipos_cambiar_de_equipo_reinicia_el_filtro():
    at, _ = _eq("toluca")
    at.get("button_group")[0].set_value("2025/2026").run()
    at.selectbox[0].set_value("Atlas").run()
    assert not at.exception
    assert at.get("button_group")[0].value is None  # vuelve a «Todas»
    assert "<dt>Hoy</dt>" in _html(at)


def test_equipos_clasicos_con_su_n_real(datos_pagina=None):
    feat, _, _ = partidos()
    riv = cargar_rivalidades()
    esperados = {"Necaxa": 1, "Leones Negros": 2, "Lobos BUAP": 4, "Juarez": 14, "Atl. San Luis": 16}
    for equipo, n in esperados.items():
        slug = c.SLUG[equipo]
        html = _eq(slug)[1]
        pares = rivalidades_de(equipo, riv)
        assert pares, equipo
        for rival, nombre_clasico in pares:
            k = hs.clasico(feat, equipo, rival)
            texto = "1 duelo desde 2012" if k["n"] == 1 else f"{k['n']} duelos desde 2012"
            assert escape(nombre_clasico) in html and texto in html, (equipo, rival)
            assert f"G-E-P {k['g']}-{k['e']}-{k['p']}" in html
            assert ("Pocos duelos" in html) == any(
                hs.clasico(feat, equipo, r_)["n"] < 6 for r_, _ in pares)
    assert "Sin clásicos registrados." in _eq("toluca")[1]


def test_equipos_html_una_linea_y_escudos_con_alt_correcto():
    for slug in ("toluca", "chiapas", "san-luis"):
        at, _ = _eq(slug)
        for m in at.markdown:
            if m.value.startswith("<style>"):
                continue
            assert "\n" not in m.value and m.value == m.value.strip(), m.value[:80]


def test_equipos_un_enlace_reescribe_la_url_del_navegador(monkeypatch):
    """Regresión: al hacer clic en una tarjeta de la misma página, Streamlit cambia los query
    params en el servidor pero no la URL del navegador. Si la página no la reescribe, la
    siguiente interacción (p. ej. una pastilla) vuelve al equipo anterior. AppTest no tiene
    URL de navegador: se vigila que la página envíe el cambio."""
    from streamlit.runtime.state.query_params import QueryParams
    enviados = []
    original = QueryParams._send_query_param_msg

    def espia(self):
        enviados.append(str(self._query_params.get("equipo")))
        return original(self)

    monkeypatch.setattr(QueryParams, "_send_query_param_msg", espia)
    at = _correr("paginas/equipos.py", equipo="toluca")
    enviados.clear()
    at.query_params["equipo"] = "chiapas"  # lo que hace el clic en la tarjeta de Chiapas
    at.run()
    assert not at.exception and at.selectbox[0].value == "Chiapas"
    assert enviados and "chiapas" in enviados[-1]  # la URL del navegador se corrige

