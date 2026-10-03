import joblib
import numpy as np
import pandas as pd
import pytest

from src.entrenar import RUTA_MODELO
from src.explicacion import FACTORES, contribuciones, probabilidades
from src.features import MAP, X_COLS


@pytest.fixture(scope="module")
def est():
    return joblib.load(RUTA_MODELO)


def _x(est, local, visita):
    f = lambda t: np.array(est["hist"][t]).mean(axis=0)
    fl, fv, e = f(local), f(visita), est["elo"]
    return pd.DataFrame([dict(elo_diff=e[local] - e[visita], elo_h=e[local], elo_a=e[visita],
                              pts_h=fl[0], pts_a=fv[0], gf_h=fl[1], gc_h=fl[2],
                              gf_a=fv[1], gc_a=fv[2])])[est["cols"]]


PARES = [("Club America", "Cruz Azul"), ("Atlante", "Toluca"), ("Puebla", "Monterrey")]


def test_factores_cubren_todas_las_columnas():
    cols = [c for cs in FACTORES.values() for c in cs]
    assert sorted(cols) == sorted(X_COLS) and len(cols) == len(set(cols))


@pytest.mark.parametrize("local,visita", PARES)
def test_suma_igual_a_decision_function(est, local, visita):
    m = est["modelo"]
    x = _x(est, local, visita)
    c = contribuciones(m, x)
    clases = list(m[-1].classes_)
    df = m.decision_function(x)[0]
    esperado = df[clases.index(MAP["H"])] - df[clases.index(MAP["A"])]
    assert c["intercepto"] + c["por_feature"].sum() == pytest.approx(esperado, abs=1e-10)
    assert c["intercepto"] + c["por_factor"].sum() == pytest.approx(esperado, abs=1e-10)
    assert c["total"] == pytest.approx(esperado, abs=1e-10)
    assert c["imputadas"] == []


@pytest.mark.parametrize("local,visita", PARES)
def test_probabilidades_reconstruidas(est, local, visita):
    m = est["modelo"]
    x = _x(est, local, visita)
    assert np.allclose(probabilidades(m, x), m.predict_proba(x), atol=1e-12)


def test_feature_faltante_se_reporta_y_cuadra(est):
    m = est["modelo"]
    x = _x(est, "Club America", "Cruz Azul")
    x.loc[0, ["pts_h", "gf_h", "gc_h"]] = np.nan  # equipo sin historial: el imputer usa la mediana
    c = contribuciones(m, x)
    assert c["imputadas"] == ["pts_h", "gf_h", "gc_h"]
    df = m.decision_function(x)[0]
    assert c["total"] == pytest.approx(df[2] - df[0], abs=1e-10)
    assert np.allclose(probabilidades(m, x), m.predict_proba(x), atol=1e-12)


def test_partido_promedio_solo_intercepto(est):
    """Con las features en la media del entrenamiento (z = 0) no hay contribuciones."""
    m = est["modelo"]
    media = pd.DataFrame([m[1].mean_], columns=est["cols"])
    c = contribuciones(m, media)
    assert np.allclose(c["por_feature"], 0, atol=1e-10)
