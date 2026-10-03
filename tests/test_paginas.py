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


def _correr(ruta):
    at = AppTest.from_file(str(RAIZ / ruta), default_timeout=60).run()
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
    assert html.count('class="lm-team"') == 25


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
        assert alts and set(alts) == {""}, ruta


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
