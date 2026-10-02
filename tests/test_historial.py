import joblib
import numpy as np
import pandas as pd
import pytest

from src.entrenar import RUTA_CSV, RUTA_MODELO
from src.features import cargar_partidos, procesar
from src.historial import (filtrar_temporada, gep, h2h, partidos_equipo, posicion, racha,
                           ranking, record, rivales, ultimos)


@pytest.fixture(scope="module")
def datos():
    feat, elo, hist = procesar(cargar_partidos(RUTA_CSV), K=20, ventaja=60, regresion=0.0)
    return feat, elo, hist, joblib.load(RUTA_MODELO)


def test_elo_despues_es_elo_antes_del_siguiente(datos):
    feat, elo, _, est = datos
    for equipo in ["Club America", "Leones Negros", "Atlante"]:
        pe = partidos_equipo(feat, equipo, elo)
        assert np.allclose(pe["elo_despues"].iloc[:-1], pe["elo_antes"].iloc[1:])
        assert pe["elo_despues"].iloc[-1] == elo[equipo] == est["elo"][equipo]
        assert pe["fecha"].is_monotonic_increasing


def test_ultimo_elo_y_forma_cuadran_con_el_modelo(datos):
    """Lo que muestra la app sale del CSV y debe coincidir con lo guardado en modelo.joblib."""
    feat, elo, _, est = datos
    assert set(est["elo"]) == set(feat["Home"]) | set(feat["Away"])
    for equipo, elo_modelo in est["elo"].items():
        pe = partidos_equipo(feat, equipo, elo)
        assert pe["elo_despues"].iloc[-1] == pytest.approx(elo_modelo, abs=1e-9)
        u = ultimos(pe, 5)
        assert [tuple(r) for r in u[["puntos", "gf", "gc"]].values] == \
            [tuple(map(int, h)) for h in est["hist"][equipo]]


def test_cambio_de_elo_se_conserva_por_partido(datos):
    feat, elo, _, _ = datos
    deltas = {}
    for equipo in set(feat["Home"]) | set(feat["Away"]):
        pe = partidos_equipo(feat, equipo, elo)
        idx = feat.index[(feat["Home"] == equipo) | (feat["Away"] == equipo)]
        for i, dlt in zip(idx, pe["elo_despues"] - pe["elo_antes"]):
            deltas[i] = deltas.get(i, 0.0) + dlt
    assert len(deltas) == len(feat)
    assert max(abs(v) for v in deltas.values()) < 1e-9


def test_partidos_equipo_perspectiva(datos):
    feat, elo, _, _ = datos
    pe = partidos_equipo(feat, "Club America", elo)
    r = feat[(feat["Home"] == "Club America") | (feat["Away"] == "Club America")].iloc[0]
    p = pe.iloc[0]
    local = r["Home"] == "Club America"
    assert p["local"] == local
    assert p["gf"] == (r["HG"] if local else r["AG"])
    esperado = {"H": "V", "D": "E", "A": "D"}[r["Res"]] if local else {"H": "D", "D": "E", "A": "V"}[r["Res"]]
    assert p["resultado"] == esperado


def test_record_suma(datos):
    feat, elo, _, _ = datos
    pe = partidos_equipo(feat, "Toluca", elo)
    rec = record(pe)
    assert rec["PJ"].sum() == len(pe)
    assert (rec["G"] + rec["E"] + rec["P"] == rec["PJ"]).all()
    loc = pe[pe["local"]]
    assert rec.loc["Local", "GF_pp"] == pytest.approx(loc["gf"].mean())
    t = filtrar_temporada(pe, "2024/2025")
    assert set(t["temporada"]) == {"2024/2025"} and record(t)["PJ"].sum() == len(t)


def test_h2h_simetrico(datos):
    feat, _, _, _ = datos
    (g, e, p), ult = h2h(feat, "Club America", "Guadalajara Chivas", n=5)
    (g2, e2, p2), _ = h2h(feat, "Guadalajara Chivas", "Club America")
    assert (g, e, p) == (p2, e2, g2)
    m = feat[((feat["Home"] == "Club America") & (feat["Away"] == "Guadalajara Chivas"))
             | ((feat["Home"] == "Guadalajara Chivas") & (feat["Away"] == "Club America"))]
    assert g + e + p == len(m)
    assert len(ult) == 5 and ult["fecha"].iloc[-1] == m["Date"].max()


def _pe(resultados, rivales_=None):
    n = len(resultados)
    return pd.DataFrame({"resultado": resultados,
                         "puntos": [{"V": 3, "E": 1, "D": 0}[r] for r in resultados],
                         "rival": rivales_ or ["X"] * n})


def test_racha():
    assert racha(_pe(list("VDEEE"))) == ("E", 3)
    assert racha(_pe(list("EV"))) == ("V", 1)
    assert racha(_pe([])) == (None, 0)
    assert gep(_pe(list("VVED"))) == (2, 1, 1)


def test_rivales_minimo_y_orden():
    pe = _pe(list("VVVVVVDDDDDDE"), ["A"] * 6 + ["B"] * 6 + ["C"])
    r = rivales(pe, min_duelos=6)
    assert list(r.index) == ["A", "B"]
    assert r.loc["A", "ppp"] == 3 and r.loc["B", "n"] == 6


def test_ranking_y_posicion():
    elo = {"A": 1600, "B": 1500, "C": 1550, "Z": 1700}
    activos = ["A", "B", "C"]
    assert list(ranking(elo, activos).index) == ["A", "C", "B"]
    assert posicion("C", elo, activos) == 2
    assert posicion("Z", elo, activos) is None
