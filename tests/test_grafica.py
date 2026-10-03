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
