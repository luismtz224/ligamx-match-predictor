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


# ===== Predictor =====
FORMA = [dict(resultado=r, fecha="13 sep 2026", rival=PELIGRO, marcador="2–1", condicion="Local")
         for r in "VEDVV"]


def _predictor_html():
    """Todos los componentes del Predictor con texto peligroso en cada campo de datos."""
    return [
        c.elegido("", PELIGRO),
        c.tarjetas_probabilidad([44, 29, 27], (PELIGRO, PELIGRO), ("var(--a)", "var(--b)"), ("", "")),
        c.barra_apilada((0.4374, 0.2941, 0.2685), [44, 29, 27], ("var(--a)", "var(--b)")),
        c.forma(FORMA, PELIGRO, ""),
        c.forma([], PELIGRO, ""),
        c.h2h((PELIGRO, PELIGRO), ("var(--a)", "var(--b)"), (17, 15, 11), [("13 sep 2026", PELIGRO, 4, 3)]),
        c.h2h((PELIGRO, PELIGRO), ("var(--a)", "var(--b)"), (0, 0, 0), []),
        c.factores([(PELIGRO, -0.08), ("Goles", 0.14), ("Nada", 0.0)], ("var(--a)", "var(--b)")),
        c.datos_modelo((PELIGRO, PELIGRO), [(PELIGRO, PELIGRO, PELIGRO)]),
        c.modelo_vs_mercado([(PELIGRO, 0.437, 0.459)]),
    ]


def test_componentes_predictor_una_linea_y_escapados():
    for h in _predictor_html():
        _sin_sangria(h)
        assert PELIGRO not in h


def test_componentes_predictor_escapan_cada_campo():
    for h in _predictor_html():
        if "Sin duelos" in h:
            continue
        assert escape(PELIGRO) in h or "lm-stackbar" in h, h[:80]


def test_tarjetas_un_solo_top_y_porcentajes():
    h = c.tarjetas_probabilidad([44, 29, 27], ("A", "B"), ("var(--a)", "var(--b)"), ("", ""))
    assert h.count("is-top") == 1 and h.index("is-top") < h.index("Empate")
    # el porcentaje es texto real en el HTML (lo lee un lector de pantalla), no un contador CSS
    assert re.findall(r'<span class="lm-pct">(\d+)%</span>', h) == ["44", "29", "27"]
    assert "--v:" not in h and 'class="lm-pct" style' not in h and "aria-label" not in h
    cambiado = c.tarjetas_probabilidad([61, 23, 16], ("A", "B"), ("var(--a)", "var(--b)"), ("", ""))
    assert re.findall(r'<span class="lm-pct">(\d+)%</span>', cambiado) == ["61", "23", "16"]
    empate = c.tarjetas_probabilidad([30, 40, 30], ("A", "B"), ("var(--a)", "var(--b)"), ("", ""))
    assert empate.count("is-top") == 1
    i = empate.index("is-top")
    assert empate[i:].index("Empate") < empate[i:].index("Visitante")  # el top es la de empate
    # empate en el máximo: solo la primera
    assert c.tarjetas_probabilidad([40, 20, 40], ("A", "B"), ("x", "y"), ("", "")).count("is-top") == 1


def test_barra_usa_valores_sin_redondear():
    h = c.barra_apilada((0.43742, 0.29407, 0.26851), [44, 29, 27], ("var(--a)", "var(--b)"))
    assert re.findall(r"--w:([\d.]+)", h) == ["43.7", "29.4", "26.9"]
    assert "--c:var(--draw)" in h and "Local <b>44%</b>" in h
    assert 'aria-label="Local 44%, empate 29%, visitante 27%"' in h


def test_forma_mas_reciente_a_la_derecha():
    f = [dict(resultado=r, fecha=str(i), rival="X", marcador="1–0", condicion="Visita")
         for i, r in enumerate("DEEVV")]
    h = c.forma(f, "Toluca", "")
    puntos = re.findall(r'class="lm-dot (\w)( is-latest)?"', h)
    assert [p[0] for p in puntos] == list("deevv")
    assert [bool(p[1]) for p in puntos] == [False] * 4 + [True]
    assert "<details" in h and "<summary>" in h
    # en el detalle, el más reciente arriba
    assert h.index("<div>4<small>") < h.index("<div>0<small>")


def test_factores_direccion_y_normalizacion():
    h = c.factores([("Elo", -0.0763), ("Goles a favor", 0.1435), ("Nada", 0.0)],
                   ("var(--a)", "var(--b)"))
    assert '<b>0.08 · Visitante</b>' in h and '<b>0.14 · Local</b>' in h and '<b>0.00 · Neutro</b>' in h
    assert 'lm-factor__fill visita" style="--p:0.53;--c:var(--b)"' in h
    assert 'lm-factor__fill local" style="--p:1.00;--c:var(--a)"' in h
    assert h.count("lm-factor__fill") == 2


def test_h2h_y_odds():
    h = c.h2h(("Club América", "Cruz Azul"), ("var(--a)", "var(--b)"), (17, 15, 11),
              [("13 sep 2026", "Cruz Azul", 4, 3)])
    assert "43 duelos desde 2012" in h and "<b>4 – 3</b>" in h and "Local: Cruz Azul" in h
    assert "1 duelo desde 2012" in c.h2h(("A", "B"), ("x", "y"), (1, 0, 0), [("f", "A", 1, 0)])
    assert "Sin duelos" in c.h2h(("A", "B"), ("x", "y"), (0, 0, 0), [])
    o = c.modelo_vs_mercado([("Gana A", 0.437, 0.459), ("Empate", 0.294, 0.294), ("Gana B", 0.27, 0.247)])
    assert "<span>43.7%</span><span>45.9%</span>" in o
    assert "lm-odds__d down\">−2.2 pp" in o and "lm-odds__d up\">+2.3 pp" in o
    assert "lm-odds__d\">0.0 pp" in o


def test_colores_partido_nunca_chocan():
    """En los 306 pares de activos, los tres segmentos de la barra se distinguen (delta E >= 30)."""
    import itertools

    from interfaz.recursos import colores_css, colores_partido, modelo
    from src.formato import UMBRAL_PARECIDOS, delta_e

    v = colores_css()
    for local, visita in itertools.permutations(modelo()["activos"], 2):
        css_l, css_v, hl, hv = colores_partido(local, visita)
        assert css_l == f"var(--team-{c.SLUG[local]})" and v[css_v[6:-1]] == hv
        assert delta_e(hl, hv) >= UMBRAL_PARECIDOS, (local, visita)
        assert delta_e(hv, v["draw"]) >= UMBRAL_PARECIDOS, (local, visita)
        assert delta_e(hl, v["draw"]) >= UMBRAL_PARECIDOS, (local, visita)


# ===== Fase 5: componentes de Equipos =====
import pandas as pd  # noqa: E402

from src.equipos import cargar_equipos as _cargar_equipos  # noqa: E402


def _ficha_peligrosa():
    f = {k: PELIGRO for k in ("siglas", "apodo", "ciudad_estado", "estadio", "fundacion", "palmares")}
    f.update(color1="#112233", color2="#445566", color3="")
    return f


def _geo_ext():
    from src.grafica import geometria
    from src.historial import extremos
    s = pd.DataFrame({"fecha": pd.to_datetime(["2020-01-01", "2020-02-01", "2023-01-01", "2023-02-01"]),
                      "elo": [1500.0, 1520.0, 1520.0, 1480.0], "tramo_nuevo": [True, False, True, False]})
    return geometria(s), extremos(s)


def _rec(pj=10):
    nan = float("nan")
    fila = dict(PJ=pj, G=4, E=3, P=3, GF_pp=1.5 if pj else nan, GC_pp=1.0 if pj else nan)
    return pd.DataFrame({"Local": fila, "Visitante": fila}).T


def _fila_rival(nombre):
    return dict(escudo_html='<span class="lm-crest"></span>', nombre=nombre, ppp=2.1, n=20, g=9, e=3, p=8)


def _clasico(n=30, nombre=PELIGRO, ultimo=PELIGRO):
    return dict(nombre=nombre, escudo_html='<span class="lm-crest"></span>', rival=PELIGRO, n=n,
                g=1, e=2, p=3, ultimo=ultimo)


def _componentes_equipos():
    geo, ext = _geo_ext()
    return [
        c.heroe("Toluca", PELIGRO, ""),
        c.ficha(_ficha_peligrosa()),
        c.elo_actual("Toluca", 1643.6, True, 2, 18), c.elo_actual("Chiapas", 1417.0, False),
        c.grafica_elo("Toluca", PELIGRO, geo, ext), c.grafica_elo("Toluca", PELIGRO, None, None),
        c.record_equipo(_rec()), c.record_equipo(_rec(0)),
        c.racha_actual(PELIGRO, PELIGRO),
        c.rivales([_fila_rival(PELIGRO)], [_fila_rival(PELIGRO)]), c.rivales([], []),
        c.rivales([_fila_rival("A")], []),
        c.clasicos([_clasico(), _clasico(1), _clasico(5)]), c.clasicos([]),
        c.clasicos([_clasico(ultimo=None)]),
    ]


def test_componentes_equipos_una_linea():
    for h in _componentes_equipos():
        _sin_sangria(h)


def test_componentes_equipos_escapan_texto_de_datos():
    for h in _componentes_equipos():
        assert PELIGRO not in h  # el texto crudo nunca llega al HTML
    assert escape(PELIGRO) in c.heroe("Toluca", PELIGRO, "")
    ficha = c.ficha(_ficha_peligrosa())
    assert ficha.count(escape(PELIGRO)) == 6  # los 6 campos de texto, cada uno escapado
    geo, ext = _geo_ext()
    assert escape(PELIGRO) in c.grafica_elo("Toluca", PELIGRO, geo, ext)  # aria-label
    assert escape(PELIGRO) in c.racha_actual(PELIGRO, PELIGRO)
    assert c.rivales([_fila_rival(PELIGRO)], []).count(escape(PELIGRO)) == 1
    k = c.clasicos([_clasico()])
    assert k.count(escape(PELIGRO)) == 3  # nombre del clásico, rival y último duelo


def test_ficha_estadio_con_comillas_de_veracruz_y_campos_vacios():
    fichas = _cargar_equipos()
    f = fichas.loc["Veracruz"]
    h = c.ficha(f)
    assert escape(f["estadio"]) in h
    if '"' in f["estadio"]:
        assert f["estadio"] not in h  # las comillas van escapadas
    assert "<dt>Apodo</dt>" in c.ficha(dict(f, apodo="Los Tiburones"))
    assert "Apodo" not in c.ficha(dict(f, apodo=""))  # sin apodo se omite la línea


def test_ficha_no_muestra_los_colores_del_equipo():
    """Los colores visten la página (estilo_equipo), no son un dato de la ficha."""
    f = _ficha_peligrosa()
    f.update(color1="#112233", color2="#445566", color3="#778899")
    h = c.ficha(f)
    assert "lm-swatch" not in h and "Colores" not in h and "#112233" not in h and "background:" not in h


def test_elo_actual_etiqueta_y_posicion():
    activo = c.elo_actual("Toluca", 1643.6, True, 2, 18)
    assert "Elo actual" in activo and ">1,644<" in activo and "Posición 2 de 18 activos" in activo
    assert "--team-toluca" in activo
    inactivo = c.elo_actual("Chiapas", 1417.2, False, None, 18)
    assert "Elo final" in inactivo and "Elo actual" not in inactivo and "Posición" not in inactivo


def test_grafica_resumen_visible_aria_y_nota_de_cortes():
    geo, ext = _geo_ext()
    h = c.grafica_elo("Atl. San Luis", "Atlético de San Luis", geo, ext)
    assert 'viewBox="0 0 600 220"' in h and 'role="img"' in h and "lm-spark" in h
    assert "--team:var(--team-san-luis)" in h and 'pathLength="1"' in h
    assert 'aria-label="Elo de Atlético de San Luis: de 1,500 en ene 2020 a 1,480 en feb 2023;' in h
    assert "máximo 1,520 (1 feb 2020)" in h and "mínimo 1,480 (1 feb 2023)" in h
    for t in ("Máximo", "Mínimo", "Inicio", "Hoy"):
        assert f"<dt>{t}</dt>" in h
    assert h.count('<circle class="pt"') == 2  # el mínimo es también el último punto
    assert "El trazo se corta donde el equipo no jugó (más de un año)." in h
    assert "<dt>Final</dt>" in c.grafica_elo("X", "X", geo, ext, etiqueta_final="Final")
    # sin cortes no hay nota
    from src.grafica import geometria
    from src.historial import extremos
    s = pd.DataFrame({"fecha": pd.to_datetime(["2020-01-01", "2020-02-01"]), "elo": [1500.0, 1510.0],
                      "tramo_nuevo": [True, False]})
    assert "El trazo se corta" not in c.grafica_elo("X", "X", geometria(s), extremos(s))
    assert "Sin partidos en esta temporada" in c.grafica_elo("X", "X", None, None)


def test_record_equipo_raya_cuando_no_hay_partidos():
    con = c.record_equipo(_rec(10))
    assert "De local" in con and "De visitante" in con and "1.50" in con and "—" not in con
    sin = c.record_equipo(_rec(0))
    assert sin.count("—") == 4 and "nan" not in sin.lower()  # GF y GC, de local y de visitante


def test_rivales_listas_y_avisos():
    ambos = c.rivales([_fila_rival("A")], [_fila_rival("B")])
    assert "Le gana más" in ambos and "Le gana menos" in ambos
    assert "2.10 pts/partido · 20 duelos · 9-3-8" in ambos and 'alt=' not in ambos
    solo_mejores = c.rivales([_fila_rival("A")], [])
    assert "Le gana más" in solo_mejores and "Sin suficientes duelos" in solo_mejores
    vacio = c.rivales([], [])
    assert "Sin suficientes duelos" in vacio and "Le gana más" not in vacio


def test_clasicos_numero_de_duelos_y_nota_de_pocos():
    uno = c.clasicos([_clasico(1, "Clásico X", "11 abr 2026 · Local: A · 2–1")])
    assert "1 duelo desde 2012" in uno and "Pocos duelos: ojo con sacar conclusiones." in uno
    assert "G-E-P 1-2-3" in uno and "11 abr 2026 · Local: A · 2–1" in uno
    assert "Pocos duelos" in c.clasicos([_clasico(5)]) and "5 duelos desde 2012" in c.clasicos([_clasico(5)])
    seis = c.clasicos([_clasico(6)])
    assert "6 duelos desde 2012" in seis and "Pocos duelos" not in seis
    assert "Sin clásicos registrados." in c.clasicos([])
    assert "Último duelo" not in c.clasicos([_clasico(ultimo=None)])


def test_fila_ranking_enlazada_conserva_el_hover():
    h = c.fila_ranking(1, "Toluca", 1643.6, 80, "", enlazada=True)
    assert 'class="lm-elo"' in h and "is-static" not in h and h.startswith("<div")


def test_equipo_de_slug_es_el_inverso_de_slug():
    from interfaz.recursos import equipo_de_slug
    for equipo, slug in c.SLUG.items():
        assert equipo_de_slug(slug) == equipo
    for malo in ("xyz", "", None, "Toluca", ["toluca"], 3):
        assert equipo_de_slug(malo) is None


# ===== Colores del equipo como diseño =====
def _mezcla(c1, c2, pct):
    """Equivalente de color-mix(in srgb, c1 pct%, c2): componentes sRGB mezclados linealmente."""
    a, b = (tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for h in (c1, c2))
    return "#" + "".join(f"{round(x * pct / 100 + y * (100 - pct) / 100):02x}" for x, y in zip(a, b))


def test_estilo_equipo_define_los_dos_colores_de_la_pagina():
    for equipo, slug in c.SLUG.items():
        h = c.estilo_equipo(equipo)
        _sin_sangria(h)
        k = "--page-k:.5;" if equipo in c.BLANCOS else ""
        assert h == (f'<style>.stApp{{--page-team:var(--team-{slug});'
                     f'--page-team-2:var(--team-{slug}-2,var(--team-{slug}));{k}}}</style>')


def test_blancos_son_exactamente_los_equipos_de_color_blanco():
    """El tinte de un equipo blanco sería gris neutro: BLANCOS se calcula de los colores del CSS."""
    from src.formato import luminancia
    blancos = {e for e, s in c.SLUG.items() if luminancia(_var(f"team-{s}")) > 0.9}
    assert blancos == c.BLANCOS == {"Lobos BUAP", "Mazatlan FC"}


def test_estilo_equipo_solo_acepta_equipos_conocidos():
    with pytest.raises(KeyError):
        c.estilo_equipo('x}</style><script>')  # nunca texto libre dentro del <style>


def test_el_tinte_de_la_pagina_deja_el_texto_legible_en_los_25_equipos():
    """El tinte mezcla el color del equipo y su -2 con --bg (los porcentajes se leen del CSS), y
    el resplandor de la esquina también. --ink y --ink-muted deben leerse sobre lo más claro."""
    pcts = [int(x) for x in re.findall(r"calc\((\d+)% \* var\(--page-k, 1\)\)", CSS)]
    assert sorted(pcts) == [12, 18, 20]  # degradado (20 y 12) y resplandor (18)
    bg, ink, muted = _var("bg"), _var("ink"), _var("ink-muted")
    for equipo, slug in c.SLUG.items():
        c1 = _var(f"team-{slug}")
        try:
            c2 = _var(f"team-{slug}-2")
        except AttributeError:  # sin -2 en el CSS: el segundo color es el primero
            c2 = c1
        k = 0.5 if equipo in c.BLANCOS else 1  # --page-k
        # cada color con el mayor porcentaje que el CSS le puede aplicar (estricto)
        for fondo in (_mezcla(c1, bg, max(pcts) * k), _mezcla(c2, bg, max(pcts) * k)):
            assert contraste(ink, fondo) >= 7, (equipo, fondo)  # texto principal: AAA
            assert contraste(muted, fondo) >= 4.5, (equipo, fondo)  # texto secundario: AA


def test_css_del_tinte_usa_has_y_las_variables_de_la_pagina():
    for regla in ('.stApp:has(.lm-hero) [data-testid="stAppViewContainer"]', ".stApp:has(.lm-hero)::after",
                  ".stApp:has(.lm-hero) .lm-section h2"):
        assert regla in CSS, regla
    assert "color-mix(in srgb, var(--page-team) calc(20% * var(--page-k, 1)), var(--bg))" in CSS
    assert "calc(12% * var(--page-k, 1))" in CSS and "calc(18% * var(--page-k, 1))" in CSS
    assert "border-left: 4px solid var(--page-team)" in CSS  # el acento de los títulos es una barra


def test_el_color_del_equipo_nunca_es_texto_chico():
    """Chiapas (contraste 3.0) solo en barras, bordes, brillos y cifras grandes: ninguna regla
    nueva pinta texto con --page-team, y el texto de los títulos sigue en --ink."""
    nueva = CSS[CSS.index("Colores del equipo como diseño"):]
    assert not re.search(r"(?<![-\w])color:\s*var\(--(page-team|team)", nueva)
    assert re.search(r"\.lm-section > h2\s*\{[^}]*font-size", CSS) and "var(--ink)" in CSS
    # la única cifra grande con el color del equipo es el Elo (inline, 64 px)
    assert "lm-eloact__n" in c.elo_actual("Chiapas", 1417.0, False)
    assert re.search(r"\.lm-eloact__n\s*\{[^}]*font-size:\s*64px", CSS)


def test_css_respeta_prefers_reduced_motion():
    assert re.search(r"@media \(prefers-reduced-motion: reduce\)[^{]*\{[^}]*st-key-tarjeta-[^}]*transform: none", CSS)
    assert "transition: none !important" in CSS  # regla global ya existente
    assert re.search(r"@media \(prefers-reduced-motion: reduce\)[^{]*\{ \.lm-spark \.ln", CSS)


def test_diseno_md_documenta_los_colores_del_equipo():
    texto = (RAIZ / "DISENO.md").read_text(encoding="utf-8")
    for clave in ("--page-team", "estilo_equipo", ":has(.lm-hero)", "Chiapas", "prefers-reduced-motion"):
        assert clave in texto, clave


def test_halo_atenuado_en_el_css():
    m = re.search(r"\.lm-crest\.halo\s*\{[^}]*rgba\(245,245,250,([.\d]+)\) 0%, rgba\(245,245,250,[.\d]+\) (\d+)%", CSS)
    assert m and m.group(1) == ".45" and m.group(2) == "60"


# ===== Enlace de volver, ficha en celular y cifra clara de Chiapas =====
def _regla(selector):
    """Cuerpo de la primera regla del CSS cuyo selector es exactamente `selector`."""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert m, selector
    return m.group(1)


def test_enlace_de_volver_16px_y_area_tactil_de_48():
    assert re.search(r"--tap:\s*48px", CSS)
    texto = _regla('[class*="st-key-volver"] a, [class*="st-key-volver"] a *')
    assert "font-size: 16px" in texto and "line-height: 24px" in texto  # 16 px como mínimo
    caja = _regla('[class*="st-key-volver"] a')
    assert "min-height: var(--tap)" in caja and "min-width: var(--tap)" in caja  # 48 px táctiles
    assert 'st-key-volver-abajo' in CSS  # el de abajo comparte las reglas por el prefijo de la clase


def test_ficha_marca_los_valores_largos():
    assert c.FACT_LARGO == 24  # a 390 px no caben más de ~24 caracteres junto a la etiqueta
    f = _ficha_peligrosa()
    f.update(siglas="a" * 24, apodo="a" * 25, ciudad_estado="", estadio="x",
             fundacion="", palmares="p" * 90)
    h = c.ficha(f)
    assert '<div><dt>Siglas</dt>' in h  # justo en el límite: sigue en una fila
    assert '<div class="largo"><dt>Apodo</dt>' in h and '<div class="largo"><dt>Palmarés</dt>' in h
    assert '<div><dt>Estadio</dt>' in h and "Ciudad" not in h
    _sin_sangria(h)


def test_ficha_real_palmares_largo_en_los_25_equipos():
    fichas = _cargar_equipos()
    for equipo, f in fichas.iterrows():
        h = c.ficha(f)
        assert ('<div class="largo"><dt>Palmarés' in h) == (len(f["palmares"]) > 24), equipo
    assert '<div class="largo"><dt>Palmarés' in c.ficha(fichas.loc["Toluca"])


def test_css_apila_la_ficha_en_celular_y_la_deja_en_fila_en_escritorio():
    m = re.search(r"@media \(max-width: 599px\)\s*\{([^@]*?)\}\s*(?:\n|$)", CSS[CSS.index("valores largos"):])
    assert m, "falta la regla para celular"
    celular = m.group(1)
    assert ".lm-facts div.largo { flex-direction: column; gap: 0; }" in celular
    assert ".lm-facts div.largo dd { text-align: left; }" in celular
    # fuera de la media query, la fila sigue siendo etiqueta | valor (a la derecha)
    assert "justify-content: space-between" in _regla(".lm-facts div")
    assert "text-align: right" in _regla(".lm-facts dd")


def test_chiapas_cifra_clara_cumple_el_contraste_medido():
    """--team-chiapas (3.0:1 contra --surface) solo para barras, bordes y brillos; la cifra grande
    usa --team-chiapas-claro: mismo matiz, y contraste de texto sobre --surface, --bg y el tinte."""
    import colorsys
    base, claro = _var("team-chiapas"), _var("team-chiapas-claro")
    assert base == "#256b56"  # el color de acento no cambia
    surface, bg = _var("surface"), _var("bg")
    tinte = _mezcla(base, bg, 20)  # lo más claro que el degradado le puede poner debajo
    assert contraste(base, surface) == pytest.approx(3.0, abs=0.05)  # lo que ya se había medido
    for fondo in (surface, bg, tinte):
        assert contraste(claro, fondo) >= 4.5, fondo
    assert contraste(claro, surface) > contraste(base, surface) + 2
    hue = lambda h: colorsys.rgb_to_hls(*[int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])[0] * 360
    assert abs(hue(claro) - hue(base)) < 8  # sigue siendo el mismo verde


def test_la_cifra_clara_es_solo_para_la_cifra_grande_de_chiapas():
    assert c.color_cifra("Chiapas") == "var(--team-chiapas-claro)"
    for e in c.SLUG:
        if e != "Chiapas":
            assert c.color_cifra(e) == c.color_equipo(e), e
    assert 'style="color:var(--team-chiapas-claro)"' in c.elo_actual("Chiapas", 1417.0, False)
    assert 'style="color:var(--team-toluca)"' in c.elo_actual("Toluca", 1643.6, True, 2, 18)
    # héroe, gráfica y estilo de página siguen con el color de acento original
    geo, ext = _geo_ext()
    for h in (c.heroe("Chiapas", "Chiapas", ""), c.grafica_elo("Chiapas", "Chiapas", geo, ext),
              c.estilo_equipo("Chiapas")):
        assert "team-chiapas-claro" not in h
    assert "--team-chiapas)" in c.heroe("Chiapas", "Chiapas", "")
    assert CSS.count("team-chiapas-claro") == 2  # su definición y el comentario de la regla


# ===== Clic real, padding superior y porcentaje como texto (pruebas estáticas; el clic real está en test_clic_real.py) =====
def test_css_del_overlay_cubre_toda_la_tarjeta_y_no_se_selecciona_el_texto():
    enlace = _regla('[class*="st-key-fila-"] a, [class*="st-key-tarjeta-"] a')
    assert all(t in enlace for t in ("position: absolute", "inset: 0", "margin: 0", "opacity: 0"))
    envoltura = _regla('[class*="st-key-fila-"] [data-testid="stElementContainer"], '
                       '[class*="st-key-tarjeta-"] [data-testid="stElementContainer"]')
    # el contenedor del page_link es relative y trae margin: -6px: sin esto el overlay mide 16 × 0 px
    assert "position: static" in envoltura and "margin: 0" in envoltura
    assert "position: relative" in _regla('[class*="st-key-fila-"], [class*="st-key-tarjeta-"]')
    assert re.search(r'\[class\*="st-key-fila-"\], \[class\*="st-key-tarjeta-"\] \{ -webkit-user-select: none; user-select: none; \}', CSS)


def test_padding_superior_libera_la_barra_fija_de_streamlit_sin_ocultar_nada():
    """La barra de Streamlit (», Fork, GitHub, menú) es fija y mide ~60 px: a 390 px quedaba pegada al
    primer selector. 64 px arriba en móvil y en escritorio, y ningún elemento de la barra se oculta."""
    base = re.search(r'\[data-testid="stMainBlockContainer"\]\s*\{\s*padding:\s*(\d+)px', CSS)
    escritorio = re.search(r'min-width: 992px\)\s*\{\s*\[data-testid="stMainBlockContainer"\]\s*\{\s*padding:\s*(\d+)px', CSS)
    assert base and escritorio and int(base.group(1)) >= 64 and int(escritorio.group(1)) >= 64
    assert "stToolbar" not in CSS and not re.search(r'stHeader"\][^}]*display:\s*none', CSS)
    assert re.search(r'\[data-testid="stDecoration"\], footer \{ display: none !important; \}', CSS)  # lo único que se oculta


def test_css_sin_contadores_ni_property_para_el_porcentaje():
    """Los contadores CSS con @property (--lm-n) no se actualizaban en Safari: el número es texto real."""
    assert "@property" not in CSS and "counter-reset" not in CSS and "counter(" not in CSS
    assert "lm-count" not in CSS and "lm-pct::after" not in CSS


# ===== Fase A: componentes de la gráfica de calibración =====
from src.grafica import geometria_calibracion as _geo_cal  # noqa: E402
from src.resumen_calibracion import (CLASE as _CLASE, FUENTES as _FUENTES, NOMBRE_FUENTE as _NF,  # noqa: E402
                                     filas_detalle as _filas, resumen as _resumen, resumen_serie as _rs, serie as _serie,
                                     texto_aria as _aria_cal)


def _figura_cal(resultado="local", titulo="Gana local", ayuda="Ayuda", aria=None, con_detalle=True):
    t = pd.read_csv(RAIZ / "datos" / "procesados" / "calibracion.csv")
    geo = _geo_cal({f: _serie(t, f, resultado) for f in _FUENTES})
    res = [(_NF[f], _CLASE[f], _rs(_resumen(t, f, resultado))) for f in _FUENTES]
    detalle = c.detalle_calibracion("Cada punto, con su n", [(_NF[f], _CLASE[f], _filas(t, f, resultado))
                                                              for f in _FUENTES]) if con_detalle else ""
    return c.grafica_calibracion(titulo, geo, aria or _aria_cal(t, resultado), res, ayuda, detalle), t


def test_grafica_calibracion_una_linea_con_aria_y_sin_scripts():
    h, _ = _figura_cal()
    _sin_sangria(h)
    assert h.count("<svg") == 1 and 'role="img"' in h and 'aria-label="Gana local. Diagrama de calibración' in h
    assert "<script" not in h and "onclick" not in h and "<title" not in h  # sin tooltips ni JavaScript
    assert 'viewBox="0 0 360 340"' in h and h.startswith('<figure class="lm-cal">') and h.endswith("</figure>")


def test_cada_punto_muestra_su_n_y_las_series_tienen_formas_distintas():
    h, t = _figura_cal()
    assert h.count('class="cal-p l"') == 6 and h.count('class="cal-p m"') == 6
    assert h.count("<circle") == 6 and h.count("<rect") == 6  # logística: círculos; mercado: cuadrados
    ns = re.findall(r'<text class="cal-n ([lm])" x="[\d.]+" y="[\d.]+">(\d+)</text>', h)
    assert len(ns) == 12
    esperado = {f: [int(n) for n in _serie(t, f, "local")["n"]] for f in _FUENTES}
    assert [int(n) for k, n in ns if k == "l"] == esperado["logistica"]
    assert [int(n) for k, n in ns if k == "m"] == esperado["mercado"]
    # la n de la logística queda a la izquierda de su punto y la del mercado a la derecha
    xs_l = [float(x) for x in re.findall(r'<circle class="cal-p l" cx="([\d.]+)"', h)]
    xt_l = [float(x) for x in re.findall(r'<text class="cal-n l" x="([\d.]+)"', h)]
    xs_m = [float(x) + float(w) / 2 for x, w in re.findall(r'<rect class="cal-p m" x="([\d.]+)" y="[\d.]+" width="([\d.]+)"', h)]
    xt_m = [float(x) for x in re.findall(r'<text class="cal-n m" x="([\d.]+)"', h)]
    assert all(a < b for a, b in zip(xt_l, xs_l)) and all(a > b for a, b in zip(xt_m, xs_m))


def test_grafica_calibracion_resumen_visible_y_ayuda_en_texto():
    h, _ = _figura_cal(ayuda="Horizontal: lo que dio el modelo")
    assert "Horizontal: lo que dio el modelo" in h
    assert h.count("<dt") == 2 and "error promedio (ECE) de 1.1 puntos, dentro del ruido esperado" in h
    assert "error promedio (ECE) de 3.2 puntos, por encima del ruido esperado" in h
    assert '<dt class="l">Regresión logística</dt>' in h and '<dt class="m">Mercado (momios)</dt>' in h


def test_grafica_calibracion_escapa_el_texto():
    h, _ = _figura_cal(titulo=PELIGRO, ayuda=PELIGRO, aria=PELIGRO)
    assert PELIGRO not in h and h.count(escape(PELIGRO)) == 3
    t = pd.read_csv(RAIZ / "datos" / "procesados" / "calibracion.csv")
    d = c.detalle_calibracion(PELIGRO, [(PELIGRO, "l", _filas(t, "logistica", "local")[:1])])
    assert PELIGRO not in d and escape(PELIGRO) in d
    _sin_sangria(d)


def test_detalle_calibracion_lista_n_dio_y_paso_de_cada_grupo():
    h, _ = _figura_cal()
    assert h.count("<details") == 1 and "Ver los números" in h
    assert h.count('class="lm-duel"') == 12  # 6 grupos x 2 series
    assert "n = 442 partidos · dio 25.7% · pasó 26.0% (entre 22.1% y 30.3%)" in h
    assert "<table" not in h  # sin tablas anchas
    sin, _ = _figura_cal(con_detalle=False)
    assert "<details" not in sin


def test_leyenda_calibracion_distingue_por_forma_y_color():
    h = c.leyenda_calibracion()
    _sin_sangria(h)
    assert h.count("<svg") == 3 and h.count('aria-hidden="true"') == 3  # decorativos: el texto va al lado
    assert "<circle" in h and "<rect" in h and "<path" in h
    for t in ("Regresión logística", "Mercado (momios)", "Calibración perfecta"):
        assert t in h


def test_colores_de_la_calibracion_se_distinguen_y_se_leen():
    """Logística (--accent) y mercado (--accent-2): ΔE >= 30 entre sí y contraste >= 4.5:1 sobre --surface
    (los usa como texto: la n y el nombre de la serie). Además la forma (círculo / cuadrado) los distingue."""
    from src.formato import delta_e
    a, b, sup = _var("accent"), _var("accent-2"), _var("surface")
    assert delta_e(a, b) >= 30
    assert contraste(a, sup) >= 4.5 and contraste(b, sup) >= 4.5
    assert "--cal: var(--accent)" in CSS and "--cal: var(--accent-2)" in CSS


def test_css_de_la_calibracion_apila_en_celular_no_anima_y_ancla_las_n():
    bloque = CSS[CSS.index("Gráfica de calibración"):]
    assert "animation" not in bloque and "@keyframes" not in bloque and "transition" not in bloque  # sin movimiento
    assert ".lm-calsvg .cal-n.l { text-anchor: end; }" in bloque and ".lm-calsvg .cal-n.m { text-anchor: start; }" in bloque
    # la rejilla de dos columnas solo desde 700 px: en celular las gráficas se apilan
    assert re.search(r"\.lm-twocol \{ display: grid; grid-template-columns: 1fr;", CSS)
    assert re.search(r"@media \(min-width: 700px\) \{ \.lm-twocol \{ grid-template-columns: 1fr 1fr; \} \}", CSS)
    assert ".lm-calsvg { display: block; width: 100%; height: auto; }" in bloque  # el SVG escala sin scroll horizontal


# ===== Fase B: tarjetas de partido y resumen de la temporada =====
def _partido(pred="H", real="H", pct=None, local=("Club America", "Club América", "AME"),
             visita=("Cruz Azul", "Cruz Azul", "CAZ"), goles=(2, 1), fecha="13 sep 2026"):
    return c.tarjeta_partido(fecha, local, visita, goles, pct or {"H": 52, "D": 27, "A": 21}, pred, real)


def test_tarjeta_partido_una_linea_con_fecha_siglas_nombres_y_marcador():
    h = _partido()
    _sin_sangria(h)
    assert h.startswith('<article class="lm-m ok">') and h.endswith("</article>")
    assert "13 sep 2026" in h and ">AME<" in h and ">CAZ<" in h and ">Club América<" in h and ">Cruz Azul<" in h
    assert re.findall(r"<b>(\d+)</b>", h) == ["2", "1"]  # marcador: local y luego visitante
    assert "<img" not in h and "lm-crest" not in h  # sin escudos: la lista no se infla
    assert "<table" not in h and "<script" not in h


def test_tarjeta_partido_acierto_o_fallo_con_texto_e_icono_no_solo_color():
    ok, mal = _partido(pred="H", real="H"), _partido(pred="H", real="D")
    assert 'class="lm-m ok"' in ok and "✓ Acierto" in ok and "Fallo" not in ok.replace("Fallo:", "")
    assert 'class="lm-m fallo"' in mal and "✕ Fallo" in mal and "✓ Acierto" not in mal
    assert "Acierto: el modelo predijo gana local y pasó gana local." in ok
    assert "Fallo: el modelo predijo gana local y pasó empate." in mal
    assert "predijo gana visitante y pasó gana local" in _partido(pred="A", real="H")


def test_tarjeta_partido_muestra_el_modelo_con_el_resultado_predicho_en_negritas():
    h = _partido(pred="D", real="D", pct={"H": 52, "D": 27, "A": 21})
    assert 'Modelo: 52 % L · <b>27 % E</b> · 21 % V' in h.replace("</span><span", "<span")
    assert h.count("<b>") == 3  # los 2 goles y el resultado predicho
    # para lectores de pantalla: el texto completo y lo visual escondido
    assert '<span class="lm-sr">Modelo: local 52 por ciento, empate 27 por ciento, visitante 21 por ciento.' in h
    assert '<span aria-hidden="true">Modelo:' in h


def test_tarjeta_partido_el_color_del_equipo_solo_va_en_el_borde_de_sus_siglas():
    h = _partido()
    assert 'class="lm-sig" style="--team:var(--team-america)">AME<' in h
    assert 'style="--team:var(--team-cruz-azul)">CAZ<' in h
    assert h.count('style="--team:') == 2 and "color:" not in h  # solo las 2 siglas llevan el color; nunca texto (Chiapas 3.0:1)
    # en el CSS, --team solo pinta el borde de la sigla
    regla = _regla(".lm-sig")
    assert "border: 2px solid var(--team" in regla and "color: var(--ink)" in regla
    ch = _partido(local=("Chiapas", "Chiapas", "CHI"))
    assert "--team-chiapas" in ch


def test_tarjeta_partido_escapa_el_texto_de_datos():
    h = c.tarjeta_partido(PELIGRO, (PELIGRO, PELIGRO, PELIGRO), (PELIGRO, PELIGRO, PELIGRO), (1, 0),
                          {"H": 40, "D": 30, "A": 30}, "H", "H")
    assert PELIGRO not in h and escape(PELIGRO) in h
    _sin_sangria(h)


def test_resumen_temporada_con_los_formatos_del_readme():
    res = {"logistica": dict(partidos=336, aciertos=177, accuracy=177 / 336, log_loss=0.99823),
           "mercado": dict(partidos=336, aciertos=179, accuracy=179 / 336, log_loss=0.97741)}
    h = c.resumen_temporada(res, {"logistica": "Regresión logística", "mercado": "Momios (mercado)"})
    _sin_sangria(h)
    assert "<dd>336</dd>" in h and "<dd>177 de 336</dd>" in h and "<dd>52.68%</dd>" in h and "<dd>0.9982</dd>" in h
    assert "<dd>53.27%</dd>" in h and "<dd>0.9774</dd>" in h  # accuracy con 2 decimales y log loss con 4, como el README
    assert h.count('class="lm-record"') == 2 and "Regresión logística" in h and "Momios (mercado)" in h


def test_lista_de_partidos_en_una_rejilla_de_una_columna_y_dos_desde_700px():
    assert c.lista_partidos(["<article></article>"] * 2) == '<div class="lm-ms"><article></article><article></article></div>'
    assert re.search(r"\.lm-ms \{ display: grid; grid-template-columns: 1fr;", CSS)
    assert re.search(r"@media \(min-width: 700px\) \{ \.lm-ms \{ grid-template-columns: 1fr 1fr;", CSS)
    assert "min-width: 0" in _regla(".lm-m")  # las tarjetas no ensanchan la página


def test_css_de_las_tarjetas_y_las_pastillas():
    bloque = CSS[CSS.index("Temporadas (tarjetas de partido)"):]
    assert "animation" not in bloque and "transition" not in bloque  # sin movimiento
    assert "color: var(--team" not in bloque  # el color del equipo nunca pinta texto
    for t in ("--win", "--loss"):
        assert t in _regla(".lm-m.ok") + _regla(".lm-m.fallo") + bloque
    # el texto de la etiqueta se lee sobre su fondo (24 % del color sobre la superficie)
    for var in ("win", "loss"):
        assert contraste(_var("ink"), _mezcla(_var(var), _var("surface"), 24)) >= 7, var
    # pastillas de 48 px de alto táctil
    assert '[data-testid="stButtonGroup"] button { min-height: var(--tap); }' in CSS
    assert re.search(r"\.lm-sr \{[^}]*clip: rect\(0 0 0 0\)", CSS)  # texto solo para lectores de pantalla
