import re
from html import escape
from pathlib import Path

import pytest

from interfaz import componentes as c
from src.equipos import cargar_equipos
from src.formato import contraste

RAIZ = Path(__file__).resolve().parent.parent
CSS = (RAIZ / "estilos" / "custom.css").read_text(encoding="utf-8")
README = (RAIZ / "README.md").read_text(encoding="utf-8")
PELIGRO = '<b>&"\'x'


def _sin_sangria(h):
    """Una línea, sin saltos ni espacios al inicio: Markdown no lo vuelve bloque de código."""
    assert "\n" not in h and "\r" not in h
    assert h == h.strip() and not h.startswith(" ")


def _var(nombre):
    return re.search(rf"--{nombre}:\s*(#[0-9a-fA-F]{{6}})", CSS).group(1).lower()


def test_slug_cubre_25_equipos_y_el_css_los_define():
    eq = cargar_equipos()
    assert set(c.SLUG) == set(eq.index) and len(set(c.SLUG.values())) == 25
    for equipo, slug in c.SLUG.items():
        assert re.search(rf"--team-{re.escape(slug)}:\s*#[0-9a-fA-F]{{6}}", CSS), equipo
    assert c.HALO <= set(eq.index)


def test_colores_nuevos_son_el_primer_color_con_contraste():
    """Los 7 equipos que no venían en el diseño: primer color del CSV con contraste >= 3:1."""
    eq = cargar_equipos()
    superficie = _var("surface")
    faltan = ["Chiapas", "Dorados de Sinaloa", "Leones Negros", "Lobos BUAP", "Mazatlan FC",
              "Monarcas", "Veracruz"]
    for e in faltan:
        cols = [x for x in eq.loc[e, ["color1", "color2", "color3"]] if x]
        esperado = next(x for x in cols if contraste(x, superficie) >= 3).lower()
        assert _var(f"team-{c.SLUG[e]}") == esperado, e


def test_todos_los_componentes_son_una_linea():
    img = c.escudo("AAAA", 32, halo=True)
    for h in (img, c.escudo(None, 32), c.titulo("Predice el partido", grad="partido"),
              c.encabezado("Qué tan bueno es"), c.aviso("a"), c.aviso("a", suave=True),
              c.pie_escudos(), c.tarjeta_equipo("Toluca", 1643.6, img),
              c.fila_ranking(1, "Toluca", 1643.6, 83.7, img),
              c.fila_ranking(1, "Toluca", 1643.6, 83.7, img, href="?equipo=toluca"),
              c.lista_modelos()):
        _sin_sangria(h)


def test_nombre_mostrado_en_tarjeta_fila_y_alt():
    t = c.tarjeta_equipo("Club America", 1643.4, "", nombre="Club América")
    assert ">Club América<" in t and ">Club America<" not in t and "--team-america" in t
    f = c.fila_ranking(3, "Guadalajara Chivas", 1613.2, 50, "", nombre="CD Guadalajara")
    assert ">CD Guadalajara<" in f and "Chivas" not in f and "--team-chivas" in f
    assert '>Juarez<' in c.fila_ranking(1, "Juarez", 1500, 0, "")  # sin nombre: usa la llave
    assert 'alt="Pumas UNAM"' in c.escudo("QUJD", 32, alt="Pumas UNAM")
    assert 'alt=""' in c.escudo("QUJD", 32)
    assert 'alt="&lt;x&gt;&quot;"' in c.escudo("QUJD", 32, alt='<x>"')


def test_escudo_fallback_y_halo():
    vacio = c.escudo(None, 40)
    assert "lm-crest" in vacio and "<img" not in vacio and "has-img" not in vacio
    con = c.escudo("QUJD", 40, halo=True)
    assert 'src="data:image/png;base64,QUJD"' in con and "halo" in con and "has-img" in con
    assert "halo" not in c.escudo("QUJD", 40)


def test_escapa_texto_de_datos():
    for h in (c.titulo(PELIGRO, grad=PELIGRO), c.encabezado(PELIGRO), c.aviso(PELIGRO),
              c.tarjeta_equipo(PELIGRO, 1500, ""), c.fila_ranking(1, PELIGRO, 1500, 50, ""),
              c.fila_ranking(1, "x", 1500, 50, "", href=PELIGRO),
              c.lista_modelos([(PELIGRO, "1.0", PELIGRO)])):
        assert PELIGRO not in h  # el texto crudo no llega al HTML
        assert escape(PELIGRO) in h and "&lt;b&gt;&amp;&quot;&#x27;x" in h


def test_fila_ranking_div_o_enlace():
    assert c.fila_ranking(3, "Club America", 1643.4, 83.7, "").startswith('<div class="lm-elo is-static"')
    a = c.fila_ranking(3, "Club America", 1643.4, 83.7, "", href="?equipo=club-america")
    assert a.startswith('<a href="?equipo=club-america" class="lm-elo"') and a.endswith("</a>")
    assert "--team:var(--team-america);--p:83.7%" in a and ">1643<" in a
    assert "--team:var(--accent)" in c.fila_ranking(1, "Desconocido", 1500, 0, "")


def test_lista_modelos_marca_el_mejor():
    h = c.lista_modelos()
    assert h.count("best") == 3 and 'class="best">Mercado' in h
    assert 'class="r best">1.0037' in h


def test_cifras_de_sobre_el_modelo_coinciden_con_el_readme():
    """Compara números, no frases: cada fila (log loss, accuracy) de la tabla del README
    debe estar entre las que muestra la página."""
    pagina = {(float(ll), float(acc.rstrip("%"))) for _, ll, acc in c.RESULTADOS_MODELOS}
    leidas = []
    for linea in README.splitlines():
        if not linea.startswith("|"):
            continue
        nums = re.findall(r"\d+\.\d+", linea)
        if len(nums) == 2:
            leidas.append((float(nums[0]), float(nums[1])))
    assert len(leidas) >= 4, "no se encontró la tabla de resultados en el README"
    assert set(leidas) <= pagina
    assert len(pagina) == len(c.RESULTADOS_MODELOS) == 5
