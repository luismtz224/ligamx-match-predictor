from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.evaluacion import bootstrap_pareado, generar_folds
from src.features import cargar_partidos

RUTA_CSV = Path(__file__).resolve().parent.parent / "datos" / "crudos" / "MEX.csv"
PRUEBA = [f"{a}/{a + 1}" for a in range(2018, 2026)]   # 2018/2019 ... 2025/2026


def _temporadas_sinteticas():
    """3 partidos por temporada de 2012/13 a 2026/27, en agosto, diciembre y abril."""
    filas = []
    for a in range(2012, 2027):
        for fecha in (f"{a}-08-10", f"{a}-12-05", f"{a + 1}-04-20"):
            filas.append({"Season": f"{a}/{a + 1}", "Date": pd.Timestamp(fecha)})
    return pd.DataFrame(filas)


def _verificar_folds(feat, folds):
    assert [s for s, _, _ in folds] == PRUEBA

    # 1) ningún partido de train es posterior o igual en fecha a uno de prueba
    for s, i_tr, i_te in folds:
        assert feat.loc[i_tr, "Date"].max() < feat.loc[i_te, "Date"].min(), f"fuga en {s}"
        assert set(feat.loc[i_tr, "Season"]).isdisjoint({s}), f"{s} está en su propio train"

    # 2) ventanas expansivas: cada train contiene al anterior y crece
    for (_, tr_a, _), (s, tr_b, _) in zip(folds, folds[1:]):
        assert set(tr_a) < set(tr_b), f"el train de {s} no contiene al anterior"
    assert set(feat.loc[folds[0][1], "Season"]) == {f"{a}/{a + 1}" for a in range(2013, 2018)}

    # 3) cada partido de 2018/19 a 2025/26 es prueba exactamente una vez
    i_test = np.concatenate([te for _, _, te in folds])
    assert len(i_test) == len(set(i_test))
    assert set(i_test) == set(feat.index[feat["Season"].isin(PRUEBA)])

    # 2012/13 nunca entrena ni prueba; 2026/27 tampoco
    usados = set(np.concatenate([np.concatenate([tr, te]) for _, tr, te in folds]))
    fuera = set(feat.index[feat["Season"].isin(["2012/2013", "2026/2027"])])
    assert usados.isdisjoint(fuera)


def test_folds_sinteticos():
    feat = _temporadas_sinteticas()
    _verificar_folds(feat, generar_folds(feat))


def test_folds_con_el_csv_real():
    if not RUTA_CSV.exists():
        pytest.skip("falta datos/crudos/MEX.csv")
    feat = cargar_partidos(RUTA_CSV)
    _verificar_folds(feat, generar_folds(feat))


def test_bootstrap_con_diferencia_constante_da_ic_degenerado():
    dif = np.full(50, 0.02)
    for bloques in (None, np.repeat(np.arange(10), 5)):
        media, lo, hi = bootstrap_pareado(dif, bloques=bloques, n=200)
        assert media == pytest.approx(0.02) and lo == pytest.approx(0.02) and hi == pytest.approx(0.02)


def test_bootstrap_por_bloques_es_mas_ancho_si_hay_correlacion_dentro_del_bloque():
    rng = np.random.default_rng(0)
    bloques = np.repeat(np.arange(40), 10)
    dif = rng.normal(0, 1, 40).repeat(10) + rng.normal(0, 0.1, 400)   # choque común por bloque
    _, lo_i, hi_i = bootstrap_pareado(dif, n=2000)
    _, lo_b, hi_b = bootstrap_pareado(dif, bloques=bloques, n=2000)
    assert (hi_b - lo_b) > 2 * (hi_i - lo_i)
