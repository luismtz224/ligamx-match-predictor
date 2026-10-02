import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from interfaz import componentes as c
from interfaz.recursos import modelo

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
    assert [n for n, _ in filas] == esperado
    assert [int(v) for _, v in filas] == [round(est["elo"][e]) for e in esperado]


def test_sobre_el_modelo_tiene_cifras_aviso_y_enlace():
    html = _html(_correr("paginas/sobre_modelo.py"))
    for cifra in ["1.0037", "50.85%", "1.0115", "1.0281", "1.0474", "1.0670", "45.61%"]:
        assert cifra in html
    assert c.AVISO_EDUCATIVO in html and "2,651 partidos" in html


def test_equipos_lista_los_25():
    html = _html(_correr("paginas/equipos.py"))
    assert html.count('class="lm-team"') == 25
