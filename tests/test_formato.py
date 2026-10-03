import itertools
import random

import pytest

from src.formato import (FONDO, color_acento, colores_barra, contraste, delta_e, luminancia,
                         redondear_100, texto_sobre)


def test_redondear_100_casos():
    assert redondear_100([0.3333, 0.3333, 0.3334]) == [33, 33, 34]
    assert redondear_100([0.445, 0.445, 0.11]) == [44, 45, 11] or \
        redondear_100([0.445, 0.445, 0.11]) == [45, 44, 11]
    assert redondear_100([0.2685, 0.2941, 0.4374]) == [27, 29, 44]
    assert redondear_100([1.0, 0.0, 0.0]) == [100, 0, 0]


def test_redondear_100_siempre_suma_100():
    rng = random.Random(42)
    for _ in range(2000):
        p = [rng.random() for _ in range(3)]
        r = redondear_100(p)
        assert sum(r) == 100
        # nadie se aleja más de 1 punto de su valor exacto
        assert all(abs(ri - 100 * pi / sum(p)) < 1 for ri, pi in zip(r, p))


def test_luminancia_y_texto():
    assert luminancia("#000000") == 0 and luminancia("#FFFFFF") == pytest.approx(1)
    assert contraste("#000000", "#FFFFFF") == pytest.approx(21)
    assert texto_sobre("#FFEB00") == "#000000"  # amarillo América
    assert texto_sobre("#001F60") == "#FFFFFF"  # azul Cruz Azul


def test_delta_e():
    assert delta_e("#FFFFFF", "#FFFFFF") == 0
    assert delta_e("#000000", "#FFFFFF") == pytest.approx(100, abs=0.1)


def test_colores_barra_parecidos_usa_color2_visitante():
    assert colores_barra(["#FFFFFF", "#162577"], ["#FFFFFF", "#2B4B75"]) == ("#FFFFFF", "#2B4B75")
    assert colores_barra(["#0A2240", "#FFFFFF"], ["#132347", "#CBAB58"]) == ("#0A2240", "#CBAB58")
    # distintos: cada quien su color1
    assert colores_barra(["#CE0E2D", "#FFFFFF"], ["#FFEB00", "#003055"]) == ("#CE0E2D", "#FFEB00")


def test_color_acento_contrasta_con_fondo():
    assert color_acento(["#001F60", "#FFFFFF"]) == "#FFFFFF"
    assert color_acento(["#00C26F"]) == "#00C26F"
    for c in itertools.product(["#111231", "#0A2240"], ["#5A0000", "#222222"]):
        assert contraste(color_acento(list(c)), FONDO) == max(contraste(x, FONDO) for x in c)


# ===== Fase 5 =====
def test_texto_racha_singular_y_plural():
    from src.formato import texto_racha
    assert texto_racha("V", 1) == "1 victoria" and texto_racha("E", 1) == "1 empate"
    assert texto_racha("D", 1) == "1 derrota"
    assert texto_racha("V", 3) == "3 victorias seguidas"
    assert texto_racha("E", 2) == "2 empates seguidos"
    assert texto_racha("D", 2) == "2 derrotas seguidas"


def test_temporada_corta_y_mes_anio():
    import pandas as pd
    from src.formato import mes_anio, temporada_corta
    assert temporada_corta("2025/2026") == "2025/26" and temporada_corta("2012/2013") == "2012/13"
    assert mes_anio(pd.Timestamp("2026-09-27")) == "sep 2026"


def test_texto_ultimo_duelo_pone_el_marcador_local_primero():
    import pandas as pd
    from src.formato import texto_ultimo_duelo
    f = pd.Timestamp("2026-04-11")
    local = dict(fecha=f, local=True, gf=2, gc=1)
    visita = dict(fecha=f, local=False, gf=2, gc=1)
    assert texto_ultimo_duelo(local, "Juárez", "Tijuana") == "11 abr 2026 · Local: Juárez · 2–1"
    assert texto_ultimo_duelo(visita, "Juárez", "Tijuana") == "11 abr 2026 · Local: Tijuana · 1–2"
