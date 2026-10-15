"""Fase C: comparar el Elo de dos equipos en la misma gráfica."""
import hashlib
import itertools
import re
from pathlib import Path

import pandas as pd
import pytest

from interfaz import componentes as c
from interfaz.recursos import color_comparado, colores_css, escudo_html, nombre
from src import historial as hs
from src.entrenar import RUTA_CSV
from src.features import cargar_partidos, procesar
from src.formato import delta_e
from src.grafica import ABAJO, ALTO, ANCHO, ARRIBA, DER, IZQ, escala_y, geometria, geometria_comparada
from tests.test_paginas import _eq, _html

RAIZ = Path(__file__).resolve().parent.parent
CSS = (RAIZ / "estilos" / "custom.css").read_text(encoding="utf-8")
PELIGRO = '<b>&"x'


def _serie(fechas, elos, nuevos=None):
    nuevos = nuevos or [i == 0 for i in range(len(elos))]
    return pd.DataFrame({"fecha": pd.to_datetime(fechas), "elo": elos, "tramo_nuevo": nuevos})


@pytest.fixture(scope="module")
def datos():
    feat, elo, _ = procesar(cargar_partidos(RUTA_CSV), K=20, ventaja=60, regresion=0.0)
    return feat, elo


def _serie_de(datos, equipo, temporada=None):
    feat, elo = datos
    return hs.serie_elo(hs.filtrar_temporada(hs.partidos_equipo(feat, equipo, elo), temporada))


# ---------- geometría compartida ----------

def test_misma_escala_de_elo_y_mismo_eje_de_tiempo():
    a = _serie(["2020-01-01", "2020-07-01"], [1500.0, 1600.0])
    b = _serie(["2020-04-01", "2021-01-01"], [1400.0, 1450.0])
    ga, gb = geometria_comparada(a, b)
    assert ga["rango"] == gb["rango"] == escala_y([1500.0, 1600.0, 1400.0, 1450.0])
    xa_fin = max(p["x"] for p in ga["puntos"])  # el último punto de cada serie (a veces es también max/min)
    xb_fin = max(p["x"] for p in gb["puntos"])
    assert xb_fin == ANCHO - DER and xa_fin < xb_fin  # b termina al final del eje común, a antes
    assert ga["rejilla"] == gb["rejilla"]
    mismo = _serie(["2020-01-01", "2021-01-01"], [1500.0, 1500.0])
    g1, g2 = geometria_comparada(mismo, mismo.copy())
    assert g1["linea"] == g2["linea"]  # mismo dato = mismo pixel


def test_el_mismo_dato_en_las_dos_series_cae_en_el_mismo_pixel():
    a = _serie(["2020-01-01", "2020-06-01", "2021-01-01"], [1500.0, 1560.0, 1540.0])
    b = _serie(["2019-01-01", "2020-06-01", "2022-01-01"], [1480.0, 1560.0, 1450.0])
    ga, gb = geometria_comparada(a, b)
    pa = re.findall(r"(\d+\.\d) (\d+\.\d)", ga["linea"])[1]
    pb = re.findall(r"(\d+\.\d) (\d+\.\d)", gb["linea"])[1]
    assert pa == pb  # 1 jun 2020 con Elo 1560 en las dos


def test_todo_cabe_en_el_lienzo(datos):
    for ea, eb in (("Toluca", "Club America"), ("Chiapas", "Toluca"), ("Atl. San Luis", "Atlante")):
        ga, gb = geometria_comparada(_serie_de(datos, ea), _serie_de(datos, eb))
        for g in (ga, gb):
            for p in g["puntos"]:
                assert IZQ <= p["x"] <= ANCHO - DER and ARRIBA <= p["y"] <= ALTO - ABAJO, (ea, eb)
            xs = [float(n) for n in re.findall(r"[ML]?(-?\d+\.\d) -?\d+\.\d", g["linea"])]
            ys = [float(n) for n in re.findall(r"[ML]?-?\d+\.\d (-?\d+\.\d)", g["linea"])]
            assert all(IZQ <= x <= ANCHO - DER for x in xs) and all(ARRIBA <= y <= ALTO - ABAJO for y in ys)


def test_los_cortes_aplican_a_cada_linea(datos):
    sa, sb = _serie_de(datos, "Atl. San Luis"), _serie_de(datos, "Atlante")
    ga, gb = geometria_comparada(sa, sb)
    assert ga["linea"].count("M") == sa["tramo_nuevo"].sum() >= 2
    assert gb["linea"].count("M") == sb["tramo_nuevo"].sum() >= 2
    assert ga["cortes"] and gb["cortes"]


def test_serie_vacia_no_arrastra_a_la_otra():
    a = _serie(["2020-01-01", "2020-02-01"], [1500.0, 1510.0])
    vacia = _serie([], [])
    ga, gb = geometria_comparada(a, vacia)
    assert gb is None and ga == geometria(a)
    assert geometria_comparada(vacia, a)[0] is None


def test_geometria_con_su_propio_rango_y_dominio_no_cambia():
    s = _serie(["2020-01-01", "2020-02-01", "2020-03-01"], [1500.0, 1600.0, 1550.0])
    assert geometria(s) == geometria(s, escala_y(s["elo"]), (s["fecha"].iloc[0], s["fecha"].iloc[-1]))


# ---------- color de la segunda línea: los 600 pares ----------

def test_color_comparado_se_distingue_en_los_600_pares():
    v = colores_css()
    pares = list(itertools.permutations(c.SLUG, 2))
    assert len(pares) == 600
    usados = {"team": 0, "team-2": 0, "ink": 0, "accent": 0}
    for a, b in pares:
        css = color_comparado(a, b)
        var = re.fullmatch(r"var\(--([a-z0-9-]+)\)", css).group(1)
        assert delta_e(v[var], v[f"team-{c.SLUG[a]}"]) >= 30, (a, b, var)
        sl = c.SLUG[b]
        usados["team" if var == f"team-{sl}" else "team-2" if var == f"team-{sl}-2"
               else "ink" if var == "ink" else "accent"] += 1
    assert sum(usados.values()) == 600 and usados["team"] > 400  # casi siempre, su propio color


def test_color_comparado_prefiere_su_color_luego_el_dos_luego_ink():
    assert color_comparado("Toluca", "Club America") == "var(--team-america)"
    # dos amarillos: el de América no se distingue del de Monarcas
    assert color_comparado("Club America", "Monarcas") != "var(--team-monarcas)"
    assert color_comparado("Club America", "Monarcas") in ("var(--team-monarcas-2)", "var(--ink)",
                                                           "var(--accent)")


# ---------- componente ----------

def _comp(datos, a, b, temporada=None, etiqueta="Hoy"):
    sa, sb = _serie_de(datos, a, temporada), _serie_de(datos, b, temporada)
    ga, gb = geometria_comparada(sa, sb)
    comp = dict(equipo=b, nombre=nombre(b), geo=gb, ext=hs.extremos(sb), etiqueta_final=etiqueta,
                color=color_comparado(a, b), escudo=escudo_html(b, 24))
    return c.grafica_elo(a, nombre(a), ga, hs.extremos(sa), etiqueta_final=etiqueta, comp=comp,
                         escudo=escudo_html(a, 24)), sa, sb


def test_sin_comparacion_el_html_es_identico_al_de_antes(datos):
    """Hashes del HTML de grafica_elo calculados con el código anterior a la Fase C."""
    esperado = {
        ("Toluca", "Hoy"): "b8902feba737f8c0", ("Toluca", "Final"): "400651e05eb1eea4",
        ("Chiapas", "Hoy"): "022a4680ab09e377", ("Chiapas", "Final"): "25c554e4158c5c8d",
        ("Atl. San Luis", "Hoy"): "81d424b45d2af0b5", ("Atl. San Luis", "Final"): "bc8001ba69292b6e"}
    for (eq, et), h in esperado.items():
        s = _serie_de(datos, eq)
        html = c.grafica_elo(eq, eq, geometria(s), hs.extremos(s), etiqueta_final=et)
        assert hashlib.sha256(html.encode()).hexdigest()[:16] == h, (eq, et)
        assert html == c.grafica_elo(eq, eq, geometria(s), hs.extremos(s), et, comp=None, escudo="x")


def test_componente_leyenda_resumen_y_aria_de_los_dos(datos):
    html, sa, sb = _comp(datos, "Toluca", "Club America")
    assert "\n" not in html
    assert html.count('<ul class="lm-claves">') == 1
    assert html.count("lm-crest has-img") == 2 and html.count("--s:24px") == 2
    for n in ("Toluca", nombre("Club America")):
        assert f"<span>{n}</span>" in html
    assert html.count('<dl class="lm-chartsum">') == 2
    for t in ("Máximo", "Mínimo", "Inicio", "Hoy"):
        assert html.count(f"<dt>{t}</dt>") == 2
    aria = re.search(r'aria-label="([^"]*)"', html).group(1)
    assert aria.startswith("Elo de Toluca:") and f"Elo de {nombre('Club America')}:" in aria
    for s in (sa, sb):
        e = hs.extremos(s)
        for clave in ("inicio", "maximo", "minimo", "final"):
            assert f"{e[clave][1]:,.0f}<small>" in html
    assert 'class="ln2"' in html and 'class="pt b"' in html and "--team2:var(--team-america)" in html
    assert "stroke-dasharray" not in html  # el punteado y la animación viven en el CSS


def test_componente_escapa_nombres_y_etiqueta_final_por_equipo(datos):
    s = _serie_de(datos, "Toluca")
    ga, gb = geometria_comparada(s, s)
    comp = dict(equipo="Chiapas", nombre=PELIGRO, geo=gb, ext=hs.extremos(s), etiqueta_final="Final",
                color="var(--ink)", escudo="")
    html = c.grafica_elo("Toluca", "Toluca", ga, hs.extremos(s), comp=comp)
    assert PELIGRO not in html and "&lt;b&gt;&amp;&quot;x" in html
    assert html.count("<dt>Hoy</dt>") == 1 and html.count("<dt>Final</dt>") == 1


def test_nota_de_cortes_con_hueco_en_cualquiera_de_las_dos(datos):
    html, *_ = _comp(datos, "Atl. San Luis", "Atlante")
    assert "El trazo de un equipo se corta donde no jugó" in html
    html, *_ = _comp(datos, "Toluca", "Club America")
    assert "El trazo" not in html


def test_css_de_la_segunda_linea_punteada_y_sin_animacion():
    regla = re.search(r"\.lm-spark \.ln2 \{([^}]*)\}", CSS).group(1)
    assert "stroke-dasharray: 7 5" in regla and "animation" not in regla


# ---------- página ----------

def _comparar(at, rival):
    clave = f"comp-{c.SLUG[at.selectbox[0].value]}"
    at.selectbox(key=clave).set_value(rival).run()
    assert not at.exception, [e.value for e in at.exception]
    return _html(at)


def test_selector_vacio_por_defecto_sin_el_propio_equipo_y_con_los_24():
    at, html = _eq("toluca")
    sel = at.selectbox(key="comp-toluca")
    assert sel.label == "Comparar con…" and sel.value is None
    assert len(sel.options) == 24 and "Toluca" not in sel.options
    assert '<ul class="lm-claves">' not in html and html.count('class="ln2"') == 0


def test_pagina_sin_comparacion_tiene_el_mismo_html_que_antes(datos):
    _, html = _eq("toluca")
    s = _serie_de(datos, "Toluca")
    assert c.grafica_elo("Toluca", "Toluca", geometria(s), hs.extremos(s), etiqueta_final="Hoy") in html


def test_toluca_contra_america():
    at, _ = _eq("toluca")
    html = _comparar(at, "Club America")
    assert html.count('class="ln2"') == 1
    assert nombre("Club America") in re.search(r'<ul class="lm-claves">.*?</ul>', html).group(0)
    assert html.count("<dt>Hoy</dt>") >= 2  # los dos están activos


def test_chiapas_inactivo_contra_toluca():
    at, _ = _eq("chiapas")
    html = _comparar(at, "Toluca")
    graf = re.search(r'<div class="lm-chart" style="[^"]*"><ul class="lm-claves">.*?</dl></div></div>', html).group(0)
    assert graf.count("<dt>Final</dt>") == 1 and graf.count("<dt>Hoy</dt>") == 1
    assert "--team:var(--team-chiapas)" in graf.split("<ul")[0]  # en el contenedor: lo ve la leyenda


def test_san_luis_con_hueco_contra_atlante():
    at, _ = _eq("san-luis")
    html = _comparar(at, "Atlante")
    assert "El trazo de un equipo se corta" in html and html.count('class="ln2"') == 1


def test_el_filtro_de_temporada_aplica_a_las_dos_lineas(datos):
    at, _ = _eq("toluca")
    at.get("button_group")[0].set_value("2025/2026").run()
    html = _comparar(at, "Club America")
    for eq in ("Toluca", "Club America"):
        e = hs.extremos(_serie_de(datos, eq, "2025/2026"))
        assert f"{e['inicio'][1]:,.0f}<small>" in html and f"{e['maximo'][1]:,.0f}<small>" in html


def test_rival_sin_partidos_en_la_temporada_avisa_y_dibuja_solo_al_primero(datos):
    feat, elo = datos
    temp = "2013/2014"
    ausentes = [e for e in c.SLUG if e != "Toluca"
                and hs.filtrar_temporada(hs.partidos_equipo(feat, e, elo), temp).empty]
    assert ausentes, "debe haber un equipo sin partidos en 2013/14"
    at, _ = _eq("toluca")
    at.get("button_group")[0].set_value(temp).run()
    html = _comparar(at, ausentes[0])
    assert f"{nombre(ausentes[0])} no jugó en esta temporada" in html
    assert html.count('class="ln2"') == 0 and '<ul class="lm-claves">' not in html and html.count('class="ln"') == 1


def test_cambiar_de_equipo_reinicia_la_comparacion():
    at, _ = _eq("toluca")
    _comparar(at, "Club America")
    at.selectbox[0].set_value("Atlas").run()
    assert not at.exception
    assert at.selectbox(key="comp-atlas").value is None
    assert 'class="ln2"' not in _html(at)


def test_html_de_la_grafica_comparada_en_una_linea():
    at, _ = _eq("toluca")
    _comparar(at, "Club America")
    graficas = [m.value for m in at.markdown if "lm-claves" in m.value and m.value.startswith("<div")]
    assert len(graficas) == 1 and "\n" not in graficas[0]


def test_la_segunda_linea_dibuja_los_datos_del_segundo_y_su_escudo(datos):
    html, sa, sb = _comp(datos, "Toluca", "Club America")
    ga, gb = geometria_comparada(sa, sb)
    assert f'class="ln" pathLength="1" d="{ga["linea"]}"' in html
    assert f'class="ln2" d="{gb["linea"]}"' in html and ga["linea"] != gb["linea"]
    leyenda = re.search(r'<ul class="lm-claves">.*?</ul>', html).group(0)
    assert escudo_html("Club America", 24) in leyenda and escudo_html("Toluca", 24) in leyenda
    assert escudo_html("Toluca", 24) != escudo_html("Club America", 24)


def test_nota_de_cortes_si_solo_el_segundo_tiene_hueco(datos):
    assert not geometria(_serie_de(datos, "Toluca"))["cortes"]
    assert geometria(_serie_de(datos, "Atlante"))["cortes"]
    html, *_ = _comp(datos, "Toluca", "Atlante")
    assert "El trazo de un equipo se corta" in html


def test_los_colores_viven_en_el_contenedor_y_no_en_el_svg(datos):
    html, *_ = _comp(datos, "Toluca", "Club America")
    cont = re.search(r'<div class="lm-chart" style="([^"]*)"', html).group(1)
    assert "--team:var(--team-toluca)" in cont and "--team2:var(--team-america)" in cont
    assert "--team" not in re.search(r'<svg[^>]*>', html).group(0)
