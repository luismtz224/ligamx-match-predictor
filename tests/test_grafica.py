"""Geometría de la gráfica del Elo (src/grafica.py)."""
import joblib
import pandas as pd
import pytest

from src.entrenar import RUTA_CSV
from src.features import cargar_partidos, procesar
from src.grafica import ABAJO, ALTO, ANCHO, ARRIBA, DER, IZQ, RANGO_MIN, escala_y, geometria
from src.historial import partidos_equipo, serie_elo


def _serie(fechas, elos, nuevos=None):
    nuevos = nuevos or [i == 0 for i in range(len(elos))]
    return pd.DataFrame({"fecha": pd.to_datetime(fechas), "elo": elos, "tramo_nuevo": nuevos})


def test_escala_con_holgura_de_5_por_ciento():
    lo, hi = escala_y([1400.0, 1600.0])
    assert lo == pytest.approx(1390.0) and hi == pytest.approx(1610.0)


def test_escala_con_rango_minimo_para_series_planas():
    lo, hi = escala_y([1500.0, 1500.0, 1500.0])
    assert hi - lo == RANGO_MIN and (lo + hi) / 2 == 1500
    lo, hi = escala_y([1500.0, 1510.0])  # rango de 10 + holgura < 40
    assert hi - lo == RANGO_MIN and lo < 1500 and hi > 1510


def test_serie_vacia_no_tiene_geometria():
    assert geometria(_serie([], [])) is None


def test_un_tramo_sin_cortes_y_el_maximo_queda_arriba():
    s = _serie(["2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01"], [1500, 1600, 1400, 1550])
    g = geometria(s)
    assert g["cortes"] is False and g["linea"].count("M") == 1 and g["area"].count("Z") == 1
    por_tipo = {p["tipo"]: p for p in g["puntos"]}
    assert por_tipo["max"]["y"] < por_tipo["final"]["y"] < por_tipo["min"]["y"]  # SVG: y crece hacia abajo
    assert por_tipo["final"]["x"] == ANCHO - DER


def test_cada_tramo_nuevo_abre_un_M_y_un_area():
    s = _serie(["2020-01-01", "2020-02-01", "2023-01-01", "2023-02-01"], [1500, 1510, 1510, 1520],
               [True, False, True, False])
    g = geometria(s)
    assert g["cortes"] is True and g["linea"].count("M") == 2 and g["area"].count("M") == 2
    assert g["area"].count("Z") == 2


def test_la_linea_de_referencia_solo_si_1500_cae_en_el_rango():
    sobre = geometria(_serie(["2020-01-01", "2020-02-01"], [1700, 1800]))
    cerca = geometria(_serie(["2020-01-01", "2020-02-01"], [1450, 1550]))
    assert sobre["rejilla"].count("M") == 3 and cerca["rejilla"].count("M") == 4


def test_marcadores_sin_repetir_posicion():
    g = geometria(_serie(["2020-01-01", "2020-02-01", "2020-03-01"], [1500, 1520, 1540]))
    assert [p["tipo"] for p in g["puntos"]] == ["max", "min"]  # el máximo es también el final
    plano = geometria(_serie(["2020-01-01", "2020-01-01"], [1500, 1500]))
    assert len({(p["x"], p["y"]) for p in plano["puntos"]}) == len(plano["puntos"])


def test_un_solo_dia_centra_el_trazo_sin_dividir_entre_cero():
    g = geometria(_serie(["2020-01-01", "2020-01-01"], [1500, 1510]))
    assert all(p["x"] == (ANCHO) / 2 for p in g["puntos"])
    assert "nan" not in g["linea"].lower()


@pytest.fixture(scope="module")
def datos():
    feat, elo, _ = procesar(cargar_partidos(RUTA_CSV), K=20, ventaja=60, regresion=0.0)
    return feat, elo


def test_los_25_equipos_caben_en_el_lienzo_y_los_cortes_coinciden(datos):
    feat, elo = datos
    for equipo in elo:
        s = serie_elo(partidos_equipo(feat, equipo, elo))
        g = geometria(s)
        assert g["linea"].count("M") == s["tramo_nuevo"].sum(), equipo
        for p in g["puntos"]:
            assert IZQ <= p["x"] <= ANCHO - DER and ARRIBA <= p["y"] <= ALTO - ABAJO, equipo
        lo, hi = g["rango"]
        assert lo <= s["elo"].min() and hi >= s["elo"].max() and hi - lo >= RANGO_MIN


def test_atl_san_luis_y_atlante_cortan_y_toluca_no(datos):
    feat, elo = datos
    cortes = {e: geometria(serie_elo(partidos_equipo(feat, e, elo)))["cortes"]
              for e in ("Atl. San Luis", "Atlante", "Toluca")}
    assert cortes == {"Atl. San Luis": True, "Atlante": True, "Toluca": False}


# ===== Fase A: geometría de la gráfica de calibración =====
from pathlib import Path  # noqa: E402

from src.grafica import (CAL_ALTO, CAL_ANCHO, CAL_ARRIBA, CAL_IZQ, CAL_LADO, CAL_R_MAX, CAL_R_MIN,  # noqa: E402
                         geometria_calibracion, rango_calibracion)

CSV_CAL = Path(__file__).resolve().parent.parent / "datos" / "procesados" / "calibracion.csv"


def _t(pred, freq, lo, hi, n):
    return pd.DataFrame({"pred": pred, "freq": freq, "wilson_lo": lo, "wilson_hi": hi, "n": n})


def test_rango_cubre_puntos_y_barras_con_holgura_y_se_redondea_hacia_afuera():
    s = {"a": _t([0.25, 0.60], [0.26, 0.58], [0.22, 0.54], [0.30, 0.64], [100, 100])}
    lo, hi = rango_calibracion(s)
    assert lo == 0.15 and hi == 0.70  # 0.22 - 0.03 = 0.19 -> 0.15; 0.64 + 0.03 = 0.67 -> 0.70
    otra = {"b": _t([0.01], [0.02], [0.0], [0.05], [10])}
    assert rango_calibracion(otra)[0] == 0.0  # sin salirse de [0, 1]
    assert rango_calibracion({"b": _t([0.97], [0.98], [0.95], [1.0], [10])})[1] == 1.0


def test_sin_datos_no_hay_geometria():
    assert geometria_calibracion({}) is None
    assert geometria_calibracion({"a": _t([], [], [], [], [])}) is None


def test_un_punto_sobre_la_diagonal_cae_sobre_la_diagonal():
    s = {"otra": _t([0.3, 0.5], [0.3, 0.5], [0.25, 0.45], [0.35, 0.55], [200, 200])}  # sin desplazamiento (dx = 0)
    g = geometria_calibracion(s)
    for p in g["series"]["otra"]["puntos"]:
        fx = (p["x"] - CAL_IZQ) / CAL_LADO
        fy = 1 - (p["y"] - CAL_ARRIBA) / CAL_LADO  # SVG: y crece hacia abajo
        assert fx == pytest.approx(fy, abs=0.002)
    # y los extremos de la diagonal son las esquinas del cuadro (mismo rango en los dos ejes)
    assert g["diagonal"] == f"M{CAL_IZQ:.1f} {CAL_ARRIBA + CAL_LADO:.1f} L{CAL_IZQ + CAL_LADO:.1f} {CAL_ARRIBA:.1f}"


def test_mayor_frecuencia_real_queda_mas_arriba():
    g = geometria_calibracion({"a": _t([0.3, 0.3], [0.2, 0.4], [0.15, 0.35], [0.25, 0.45], [100, 100])})
    bajo, alto = g["series"]["a"]["puntos"]
    assert alto["y"] < bajo["y"]
    for p in (bajo, alto):
        assert p["y_hi"] < p["y"] < p["y_lo"]  # la barra va de abajo (y_lo, mayor y) a arriba (y_hi)


def test_todo_cae_dentro_del_lienzo_y_el_cuadro():
    s = {f: pd.read_csv(CSV_CAL).query("fuente == @f and resultado == 'local'").sort_values("grupo")
         for f in ("logistica", "mercado")}
    g = geometria_calibracion(s)
    lo, hi = g["rango"]
    assert all(lo <= v <= hi for t in s.values() for col in ("pred", "freq", "wilson_lo", "wilson_hi") for v in t[col])
    for serie in g["series"].values():
        for p in serie["puntos"]:
            assert 0 <= p["x"] - p["r"] and p["x"] + p["r"] <= CAL_ANCHO
            assert CAL_ARRIBA <= p["y_hi"] and p["y_lo"] <= CAL_ARRIBA + CAL_LADO  # las barras no se salen del cuadro
    assert CAL_ARRIBA + CAL_LADO <= CAL_ALTO


def test_el_radio_crece_con_n_y_esta_acotado():
    g = geometria_calibracion({"a": _t([0.3, 0.4, 0.5], [0.3, 0.4, 0.5], [0.2, 0.3, 0.4], [0.4, 0.5, 0.6], [100, 400, 900])})
    r = [p["r"] for p in g["series"]["a"]["puntos"]]
    assert r[0] < r[1] < r[2] and r[2] == CAL_R_MAX and all(CAL_R_MIN <= x <= CAL_R_MAX for x in r)
    parejo = geometria_calibracion({"a": _t([0.3, 0.4], [0.3, 0.4], [0.2, 0.3], [0.4, 0.5], [442, 442])})
    assert {p["r"] for p in parejo["series"]["a"]["puntos"]} == {CAL_R_MAX}
    assert [p["n"] for p in g["series"]["a"]["puntos"]] == [100, 400, 900]  # la n viaja con cada punto


def test_las_dos_series_se_separan_a_los_lados_para_no_encimarse():
    mismo = _t([0.4], [0.4], [0.35], [0.45], [442])
    g = geometria_calibracion({"logistica": mismo, "mercado": mismo})
    xl = g["series"]["logistica"]["puntos"][0]["x"]
    xm = g["series"]["mercado"]["puntos"][0]["x"]
    assert xl < xm and xm - xl == pytest.approx(6.0, abs=0.2)


def test_etiquetas_de_los_ejes_en_porcentaje_y_rejilla():
    g = geometria_calibracion({"a": _t([0.3], [0.3], [0.2], [0.4], [100])})
    textos = [e["texto"] for e in g["etiquetas"] if e["eje"] == "x"]
    assert textos == [e["texto"] for e in g["etiquetas"] if e["eje"] == "y"] and textos[0].endswith("%")
    assert g["rejilla"].count("M") == 2 * len(textos)  # una línea horizontal y una vertical por etiqueta


def test_geometria_con_los_datos_reales_da_6_puntos_por_serie_y_4_barras_con_remates():
    t = pd.read_csv(CSV_CAL)
    for resultado in ("local", "visitante"):
        g = geometria_calibracion({f: t.query("fuente == @f and resultado == @resultado").sort_values("grupo")
                                   for f in ("logistica", "mercado")})
        for serie in g["series"].values():
            assert len(serie["puntos"]) == 6 and serie["ic"].count("V") == 6 and serie["ic"].count("h6") == 12
            assert all(p["n"] in (441, 442) for p in serie["puntos"])
