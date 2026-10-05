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


CON_ENLACES = {"paginas/equipos.py", "paginas/equipo.py", "paginas/ranking.py"}  # usan st.page_link: necesitan st.navigation


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


def test_alt_del_escudo():
    """alt="" cuando el nombre va al lado; el nombre solo cuando el escudo va solo."""
    assert 'alt=""' in escudo_html("Club America", 32)
    assert 'alt="Club América"' in escudo_html("Club America", 32, solo=True)
    assert 'alt="CD Guadalajara"' in escudo_html("Guadalajara Chivas", 48, solo=True)
    for ruta in ("paginas/ranking.py", "paginas/equipos.py", "paginas/predictor.py"):
        html = _html(_correr(ruta))
        alts = re.findall(r'<img [^>]*alt="([^"]*)"', html)
        assert alts and set(alts) == {""}, ruta
    # en la página de un equipo, el escudo del héroe va solo (sin nombre al lado) y lleva el nombre
    alts = re.findall(r'<img [^>]*alt="([^"]*)"', _html(_correr("paginas/equipo.py", equipo="america")))
    assert set(alts) == {"", "Club América"} and alts.count("Club América") == 1


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
    # el texto de cada tarjeta está en el HTML y coincide con los valores redondeados (y con la leyenda de la barra)
    pct = [int(v) for v in re.findall(r'<span class="lm-pct">(\d+)%</span>', html)]
    assert pct == redondear_100(probs) and sum(pct) == 100
    assert pct == [int(v) for v in re.findall(r"<b>(\d+)%</b>", html)[:3]]
    assert "--v:" not in html and 'class="lm-pct" style' not in html  # ya no es un contador CSS
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


# ===== Fase 5: Equipos (rejilla) y Equipo (página oculta) =====
import pandas as pd  # noqa: E402

from interfaz.recursos import equipo_de_slug, partidos  # noqa: E402
from src import historial as hs  # noqa: E402
from src.equipos import cargar_rivalidades, rivalidades_de  # noqa: E402
from src.formato import fecha_corta, temporada_corta, texto_racha  # noqa: E402

VOLVER = "← Todos los equipos"


def _sin_css(at):
    """HTML de la página sin el <style> global de app.py (que menciona todas las clases)."""
    return "".join(m.value for m in at.markdown if not m.value.startswith("<style>/*"))


def _eq(slug):
    """Página de un equipo (/equipo?equipo=<slug>)."""
    at = _correr("paginas/equipo.py", equipo=slug)
    return at, _html(at)


def _aria(html):
    return re.search(r'aria-label="(Elo de [^"]*)"', html).group(1)


def _resumen(html, etiqueta):
    """Cifra de la dl del resumen de la gráfica (Máximo, Mínimo, Inicio, Hoy/Final)."""
    return int(re.search(rf"<dt>{etiqueta}</dt><dd>([\d,]+)<small>", html).group(1).replace(",", ""))


def _es_rejilla(at):
    html = _sin_css(at)
    return ('<h1 class="lm-h1">Equipos</h1>' in html and "lm-hero" not in html
            and not at.selectbox and not at.get("button_group"))


def test_equipos_toluca_activo():
    at, html = _eq("toluca")
    est = modelo()
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
    d = re.search(r'<path class="ln" pathLength="1" d="([^"]*)"', html).group(1)
    assert d.count("M") == 2
    assert _resumen(html, "Hoy") == round(est["elo"]["Atl. San Luis"])
    assert "antes de la fundación" not in _eq("toluca")[1]  # solo a quien corresponde


# --- Equipos: rejilla como puerta de entrada ---
def test_equipos_sin_parametro_muestra_solo_la_rejilla():
    at = _correr("paginas/equipos.py")
    assert _es_rejilla(at)
    html = _sin_css(at)
    assert len(re.findall(r'class="lm-team( is-sel)?"', html)) == 25 and "is-sel" not in html
    assert len(at.get("page_link")) == 25  # sin «← Todos los equipos»
    assert "desde 2012" in html and "<style>.stApp{--page-team" not in html  # sin colores de equipo
    assert dict(at.query_params) == {}


def test_equipos_ordenados_por_nombre_en_la_rejilla():
    html = _sin_css(_correr("paginas/equipos.py"))
    nombres = re.findall(r'<div style="font-weight:600">(.*?)</div><div class="lm-team__elo">', html)
    esperado = [escape(nombre(e)) for e in ordenados(cargar_equipos().index)]
    assert nombres == esperado and len(nombres) == 25
    assert nombres.index("Querétaro") < nombres.index("Santos Laguna")
    assert "Mazatlán FC" in nombres and "Mazatlan FC" not in nombres


def test_equipos_slug_invalido_cae_a_la_rejilla_y_limpia_la_url():
    for malo in ("xyz", "", "Toluca", "toluca "):
        at = _correr("paginas/equipos.py", equipo=malo)
        assert _es_rejilla(at), malo
        assert dict(at.query_params) == {}, malo  # la URL queda limpia


def test_equipos_con_slug_redirige_a_la_pagina_del_equipo():
    """/equipos?equipo=<slug> (enlaces del Ranking, tarjetas y URLs compartidas) abre el equipo."""
    at = _correr("paginas/equipos.py", equipo="cruz-azul")
    assert at.selectbox[0].value == "Cruz Azul" and "lm-hero" in _sin_css(at)
    assert at.query_params["equipo"] == ["cruz-azul"]


def test_equipos_entrada_no_tiene_selector_la_rejilla_es_el_selector():
    for slug in (None, "xyz"):
        at = _correr("paginas/equipos.py", equipo=slug)
        assert not at.selectbox and not at.get("selectbox"), slug  # sin «Elige un equipo»
        assert "sel_rejilla" not in at.session_state and "abrir_equipo" not in at.session_state
        assert len(at.get("page_link")) == 25  # las 25 tarjetas son los enlaces


# --- Equipo: página de un equipo ---
def _planos(nodo):
    """Elementos de un árbol de AppTest en orden de aparición (recorre los bloques)."""
    for hijo in nodo.children.values():
        if hasattr(hijo, "children"):
            yield from _planos(hijo)
        else:
            yield hijo


def test_equipo_con_slug_tiene_volver_arriba_y_abajo_y_ninguna_rejilla():
    at, html = _eq("toluca")
    enlaces = at.get("page_link")
    assert len(enlaces) == 2  # arriba y abajo; las tarjetas ya no están en la página de un equipo
    for e in enlaces:
        assert e.proto.label == VOLVER and e.proto.query_string == "" and e.proto.page == "equipos"
    sin_css = _sin_css(at)
    assert 'class="lm-team' not in sin_css and "Todos los equipos</h2>" not in sin_css
    assert not any(e.proto.query_string for e in enlaces)  # ningún enlace a otro equipo
    # orden: primero el enlace, después el héroe, y al final (tras los clásicos) el otro enlace
    planos = list(_planos(at.main))
    pos = lambda f: next(i for i, e in enumerate(planos) if f(e))
    es_link = lambda e: getattr(e, "type", "") == "page_link"
    md_con = lambda txt: (lambda e: getattr(e, "type", "") == "markdown" and txt in e.value)
    primero = pos(es_link)
    ultimo = max(i for i, e in enumerate(planos) if es_link(e))
    assert primero < pos(md_con('class="lm-hero"')) and pos(md_con("Clásicos</h2>")) < ultimo


def test_equipo_slug_invalido_o_ausente_cae_a_la_rejilla_sin_error():
    for slug in ("xyz", "", None):
        at = _correr("paginas/equipo.py", equipo=slug)
        assert _es_rejilla(at), slug
        assert dict(at.query_params) == {}, slug


def test_equipo_cambiar_el_selector_actualiza_la_url_y_el_equipo():
    at, _ = _eq("toluca")
    at.selectbox[0].set_value("Atlas").run()
    assert not at.exception and at.selectbox[0].value == "Atlas"
    assert at.query_params["equipo"] == ["atlas"] and 'alt="Atlas"' in _html(at)


def test_equipo_abierto_por_enlace_conserva_el_equipo_al_usar_el_filtro():
    """Regresión de la URL: tras llegar desde un enlace, una interacción (pastilla) no debe
    volver al equipo anterior."""
    at = _correr("paginas/equipos.py", equipo="toluca")
    at.query_params["equipo"] = "chiapas"  # lo que hace el clic en la tarjeta de Chiapas
    at.run()
    assert at.selectbox[0].value == "Chiapas" and at.query_params["equipo"] == ["chiapas"]
    at.get("button_group")[0].set_value("2013/2014").run()
    assert not at.exception and at.selectbox[0].value == "Chiapas"
    assert at.query_params["equipo"] == ["chiapas"] and 'alt="Chiapas"' in _html(at)


def test_ranking_18_enlaces_con_su_slug_y_query_params():
    at = _correr("paginas/ranking.py")
    est = modelo()
    enlaces = at.get("page_link")
    assert len(enlaces) == 18
    esperado = [c.SLUG[e] for e in sorted(est["activos"], key=lambda e: -est["elo"][e])]
    assert [e.proto.query_string for e in enlaces] == [f"equipo={s}" for s in esperado]
    assert {equipo_de_slug(s) for s in esperado} == set(est["activos"])
    assert all(e.proto.page == "equipos" for e in enlaces)  # siguen yendo a /equipos?equipo=<slug>
    assert [nombre(equipo_de_slug(s)) for s in esperado] == [e.proto.label for e in enlaces]


def test_equipo_filtro_de_temporada_afecta_lo_que_debe_y_no_lo_demas():
    feat, elo, _ = partidos()
    est = modelo()
    at, base = _eq("toluca")
    at.get("button_group")[0].set_value("2025/2026").run()
    assert not at.exception, [e.value for e in at.exception]
    html = _html(at)
    pe = hs.partidos_equipo(feat, "Toluca", elo)
    pf = hs.filtrar_temporada(pe, "2025/2026")
    # afectan: gráfica, récord, últimos 10 y rivales
    assert f"de {pf['elo_antes'].iloc[0]:,.0f} en {fecha_corta(pf['fecha'].iloc[0])[3:]}" in _aria(html)
    assert _aria(html) != _aria(base)
    rec = hs.record(pf)
    for lado in ("Local", "Visitante"):
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
    clasicos_base = re.search(r"Clásicos</h2>.*", base, re.S).group(0)
    clasicos_filtrado = re.search(r"Clásicos</h2>.*", html, re.S).group(0)
    assert clasicos_base == clasicos_filtrado
    assert "<dt>Final</dt>" in html  # con filtro, la última cifra ya no es «Hoy»


def test_equipo_filtro_a_una_temporada_sin_rivales_con_6_duelos():
    at, _ = _eq("toluca")
    at.get("button_group")[0].set_value("2025/2026").run()
    assert "Sin suficientes duelos" in _html(at)  # casi ningún equipo tiene 6 duelos en una temporada


def test_equipo_cambiar_de_equipo_reinicia_el_filtro():
    at, _ = _eq("toluca")
    at.get("button_group")[0].set_value("2025/2026").run()
    at.selectbox[0].set_value("Atlas").run()
    assert not at.exception
    assert at.get("button_group")[0].value is None  # vuelve a «Todas»
    assert "<dt>Hoy</dt>" in _html(at)


def test_equipo_clasicos_con_su_n_real():
    feat, _, _ = partidos()
    riv = cargar_rivalidades()
    esperados = {"Necaxa": 1, "Leones Negros": 2, "Lobos BUAP": 4, "Juarez": 14, "Atl. San Luis": 16}
    for equipo, n in esperados.items():
        html = _eq(c.SLUG[equipo])[1]
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


def test_equipos_html_una_linea_en_las_dos_vistas():
    for ruta, slug in (("paginas/equipos.py", None), ("paginas/equipo.py", "toluca"),
                       ("paginas/equipo.py", "chiapas"), ("paginas/equipo.py", "san-luis")):
        at = _correr(ruta, equipo=slug)
        for m in at.markdown:
            if m.value.startswith("<style>/*"):
                continue
            assert "\n" not in m.value and m.value == m.value.strip(), m.value[:80]


# --- colores del equipo como diseño ---
def test_equipo_inyecta_sus_colores_y_la_rejilla_no():
    for slug in ("america", "chiapas", "pachuca"):
        html = _eq(slug)[1]
        assert f"<style>.stApp{{--page-team:var(--team-{slug});" in html
        assert html.count("<style>.stApp{--page-team") == 1
    assert "<style>.stApp{--page-team" not in _sin_css(_correr("paginas/equipos.py"))
    # sin ficha de colores: ya no hay muestras ni hex
    html = _eq("toluca")[1]
    assert "lm-swatch" not in html and "<dt>Colores</dt>" not in html


def test_equipo_chiapas_usa_su_cifra_clara_y_los_demas_no():
    chiapas = _eq("chiapas")[1]
    assert chiapas.count('class="lm-eloact__n" style="color:var(--team-chiapas-claro)"') == 1
    assert 'class="lm-hero" style="--team:var(--team-chiapas)"' in chiapas  # el borde sigue siendo el acento
    for slug in ("toluca", "america", "pachuca"):
        assert "team-chiapas-claro" not in _sin_css(_correr("paginas/equipo.py", equipo=slug)), slug


def test_ficha_de_la_pagina_marca_el_palmares_largo():
    html = _eq("toluca")[1]
    assert '<div class="largo"><dt>Palmarés</dt>' in html
    assert '<div><dt>Siglas</dt><dd>TOL</dd></div>' in html  # lo corto sigue en una fila


# ===== Fase A: gráfica de calibración en «Sobre el modelo» =====
def _sobre_el_modelo(csv=None, monkeypatch=None):
    if csv is not None:
        from interfaz import recursos as _r
        monkeypatch.setattr(_r, "RUTA_CALIBRACION", csv)
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=120).run()
    at = at.switch_page("paginas/sobre_modelo.py").run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_sobre_el_modelo_tiene_las_dos_graficas_con_su_n_y_su_resumen():
    at = _sobre_el_modelo()
    html = _sin_css(at)
    tabla = pd.read_csv(RAIZ / "datos" / "procesados" / "calibracion.csv")
    assert html.count('<svg class="lm-calsvg"') == 2 and html.count('role="img"') >= 2
    assert 'aria-label="Gana local. Diagrama de calibración' in html and 'aria-label="Gana visitante. Diagrama' in html
    assert ">Gana local<" in html and ">Gana visitante<" in html
    # cada punto lleva su n: las 24 n del CSV, en el mismo orden (resultados local y visitante; logística y mercado)
    en_html = re.findall(r'<text class="cal-n [lm]" x="[\d.]+" y="[\d.]+">(\d+)</text>', html)
    esperado = []
    for resultado in ("local", "visitante"):
        for fuente in ("logistica", "mercado"):
            esperado += [str(n) for n in tabla.query("fuente == @fuente and resultado == @resultado").sort_values("grupo")["n"]]
    assert sorted(en_html) == sorted(esperado) and len(en_html) == 24
    # el resumen en texto trae el ECE de cada serie (con los números del CSV)
    for (fuente, resultado), g in tabla.groupby(["fuente", "resultado"]):
        assert f"error promedio (ECE) de {g['ece'].iloc[0] * 100:.1f} puntos" in html, (fuente, resultado)
    assert html.count("<details") >= 2 and html.count('class="lm-duel"') == 24
    assert "n = 442 partidos · dio 25.7% · pasó 26.0%" in html


def test_sobre_el_modelo_explica_n_y_conserva_la_conclusion_honesta():
    html = _sin_css(_sobre_el_modelo())
    assert "n es cuántos partidos son" in html and "pura suerte" in html and "unos 441 a 442 partidos" in html
    assert "no muestra descalibración ni en «gana local» ni en «gana visitante»" in html
    assert "el mercado queda descalibrado en «gana local»" in html
    assert "esta conversión de momios" in html and "Probablemente la conversión influya" in html
    assert "es una hipótesis, no un hecho" in html  # no se afirma como hecho
    # lo que ya estaba sigue ahí
    for texto in ("Qué tan bueno es", "1.0037", "Ningún modelo supera al mercado", c.AVISO_EDUCATIVO):
        assert texto in html, texto


def test_sobre_el_modelo_html_en_una_linea_y_peso_razonable():
    at = _sobre_el_modelo()
    for m in at.markdown:
        if m.value.startswith("<style>/*"):
            continue
        assert "\n" not in m.value and m.value == m.value.strip(), m.value[:80]
    peso = sum(len(m.value) for m in at.markdown) / 1024
    assert peso < 500, f"{peso:.0f} KB"  # regla de Extras: avisar si una página pasa de ~500 KB


def test_sobre_el_modelo_sin_el_csv_avisa_y_no_falla(tmp_path, monkeypatch):
    at = _sobre_el_modelo(tmp_path / "no_esta.csv", monkeypatch)
    html = _sin_css(at)
    assert "La gráfica de calibración no está disponible" in html and "lm-calsvg" not in html
    assert "Qué tan bueno es" in html and "1.0037" in html  # el resto de la página sigue


def test_sobre_el_modelo_sigue_al_csv_si_cambia(tmp_path, monkeypatch):
    """Cambiar una bandera del CSV cambia la conclusión que se muestra (no está escrita a mano)."""
    ruta = tmp_path / "calibracion.csv"
    t = pd.read_csv(RAIZ / "datos" / "procesados" / "calibracion.csv")
    t.to_csv(ruta, index=False)
    at = _sobre_el_modelo(ruta, monkeypatch)
    assert "el mercado queda descalibrado en «gana local»" in _sin_css(at)
    t.loc[(t["fuente"] == "mercado") & (t["resultado"] == "local"), "sobre_ruido"] = False
    t.to_csv(ruta, index=False)
    at.run()
    html = _sin_css(at)
    assert not at.exception and "el mercado queda descalibrado en «gana local»" not in html
    assert "el mercado no muestra descalibración ni en «gana local» ni en «gana visitante»" in html
