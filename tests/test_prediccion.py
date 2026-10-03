import itertools

import joblib
import numpy as np
import pandas as pd
import pytest

from src.entrenar import RUTA_MODELO
from src.features import MAP
from src.formato import color_distinto, con_signo, fecha_corta, redondear_100
from src.prediccion import features_partido, forma, mercado, predecir


@pytest.fixture(scope="module")
def est():
    return joblib.load(RUTA_MODELO)


def _app_anterior(est, local, visita):
    """Fórmula copiada tal cual de main:app.py (pestaña Predictor)."""
    modelo, cols, elo, hist = est["modelo"], est["cols"], est["elo"], est["hist"]

    def forma(t):
        h = hist.get(t, [])
        return np.array(h).mean(axis=0) if h else np.array([np.nan] * 3)

    fl, fv = forma(local), forma(visita)
    x = pd.DataFrame([dict(elo_diff=elo[local] - elo[visita], elo_h=elo[local], elo_a=elo[visita],
                           pts_h=fl[0], pts_a=fv[0], gf_h=fl[1], gc_h=fl[2],
                           gf_a=fv[1], gc_a=fv[2])])[cols]
    pv, pe, pl = modelo.predict_proba(x)[0]   # orden del modelo: visitante, empate, local
    return pl, pe, pv


def test_regresion_america_vs_cruz_azul(est):
    nuevo = predecir(est, "Club America", "Cruz Azul")
    assert nuevo == tuple(float(p) for p in _app_anterior(est, "Club America", "Cruz Azul"))
    # valores literales de la app anterior (local, empate, visitante)
    assert np.allclose(nuevo, [0.4374229223608867, 0.2940747774452089, 0.2685023001939045],
                       atol=1e-9)


def test_igual_a_la_app_anterior_en_todos_los_pares(est):
    for local, visita in itertools.permutations(est["activos"], 2):
        assert predecir(est, local, visita) == tuple(
            float(p) for p in _app_anterior(est, local, visita)), (local, visita)


def test_orden_de_probabilidades_A_D_H(est):
    """predict_proba viene en [visitante, empate, local] = clases [A, D, H] = [0, 1, 2]."""
    m = est["modelo"]
    assert list(m[-1].classes_) == [MAP["A"], MAP["D"], MAP["H"]] == [0, 1, 2]
    x = features_partido(est, "Toluca", "Necaxa")
    pa, pd_, ph = m.predict_proba(x)[0]
    assert predecir(est, "Toluca", "Necaxa") == (ph, pd_, pa)
    assert list(x.columns) == est["cols"]


def test_suma_100_en_todos_los_pares(est):
    for local, visita in itertools.permutations(est["activos"], 2):
        p = predecir(est, local, visita)
        assert sum(p) == pytest.approx(1)
        assert sum(redondear_100(p)) == 100


def test_forma_sin_historial_es_nan():
    assert np.isnan(forma({}, "Nuevo")).all()
    assert forma({"A": [(3, 2, 0), (0, 1, 2)]}, "A").tolist() == [1.5, 1.5, 1.0]


def test_mercado_sin_margen_y_margen():
    probs, margen = mercado(2.00, 3.30, 3.50)
    inv = [1 / 2.00, 1 / 3.30, 1 / 3.50]
    assert sum(probs) == pytest.approx(1)
    assert margen == pytest.approx(sum(inv) - 1)
    assert probs[0] == pytest.approx(0.5 / sum(inv))
    justo, cero = mercado(3.0, 3.0, 3.0)
    assert justo == pytest.approx((1 / 3,) * 3) and cero == pytest.approx(0)


def test_color_distinto_cadena():
    rojo, rojo2, blanco, gris, tinta = "#f0525c", "#f16070", "#ffffff", "#9a9ab4", "#f5f5fa"
    # el color del visitante se distingue: lo usa
    assert color_distinto(rojo, gris, [("v", "#5b86e8"), ("v2", blanco), ("ink", tinta)]) == "v"
    # mismo tono que el local: usa su -2
    assert color_distinto(rojo, gris, [("v", rojo2), ("v2", blanco), ("ink", tinta)]) == "v2"
    # el -2 es el gris del empate: cae a ink
    assert color_distinto(rojo, gris, [("v", rojo2), ("v2", gris), ("ink", tinta)]) == "ink"
    # sin -2 (equipos que no traen -2 en el CSS): directo a ink
    assert color_distinto(rojo, gris, [("v", rojo2), ("v2", None), ("ink", tinta)]) == "ink"


def test_fecha_corta_y_signo():
    assert fecha_corta(pd.Timestamp("2026-09-13")) == "13 sep 2026"
    assert fecha_corta(pd.Timestamp("2025-01-05")) == "5 ene 2025"
    assert con_signo(2.24) == "+2.2" and con_signo(-2.24) == "−2.2"
    assert con_signo(0.04) == "0.0" and con_signo(-0.04) == "0.0"
