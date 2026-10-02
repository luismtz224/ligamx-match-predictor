import re
from html import escape
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from interfaz import componentes as c
from interfaz.recursos import escudo_html, modelo, nombre, ordenados
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


def test_alt_del_escudo_es_el_nombre_mostrado():
    assert 'alt="Club América"' in escudo_html("Club America", 32)
    assert 'alt="CD Guadalajara"' in escudo_html("Guadalajara Chivas", 48)
