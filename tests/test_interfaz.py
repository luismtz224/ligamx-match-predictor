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
    assert re.findall(r"--v:(\d+)", h) == ["44", "29", "27"]
    assert 'aria-label="44 por ciento"' in h
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


def test_ficha_solo_acepta_colores_hex_y_muestra_el_hex():
    f = _ficha_peligrosa()
    f.update(color1="#112233", color2="red;position:fixed", color3="#GGGGGG")
    h = c.ficha(f)
    assert 'style="background:#112233"></i>#112233</span>' in h  # muestra con su hex visible
    assert "position:fixed" not in h and "GGGGGG" not in h


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
