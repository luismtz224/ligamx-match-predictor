import numpy as np
import pandas as pd
import pytest

from src.features import X_COLS, cargar_partidos, procesar


def _partidos(filas, temporada="2023/2024"):
    """DataFrame sintético ya ordenado, con Res derivado de los goles."""
    d = pd.DataFrame(filas, columns=["Date", "Home", "Away", "HG", "AG"])
    d["Date"] = pd.to_datetime(d["Date"])
    d["Season"] = temporada
    d["Res"] = np.where(d["HG"] > d["AG"], "H", np.where(d["HG"] < d["AG"], "A", "D"))
    return d


def _con_resultado(d, i, hg, ag):
    """Copia de d con el marcador (y Res) del partido i cambiado."""
    d2 = d.copy()
    d2.loc[i, ["HG", "AG"]] = [hg, ag]
    d2.loc[i, "Res"] = "H" if hg > ag else "A" if hg < ag else "D"
    return d2


def _x(feat, i):
    return feat.loc[i, X_COLS].to_numpy(dtype=float)


def _igual(a, b):
    return np.allclose(a, b, equal_nan=True)


# E y F nunca juegan contra A, B, C ni D: son un grupo aparte.
CALENDARIO = _partidos([
    ("2024-01-06", "A", "B", 1, 0),   # 0
    ("2024-01-06", "E", "F", 2, 2),   # 1
    ("2024-01-13", "C", "D", 2, 0),   # 2  <- el que se modifica en la prueba de fuga
    ("2024-01-20", "A", "B", 0, 1),   # 3  posterior, pero A y B no se han cruzado con C ni D
    ("2024-01-20", "E", "F", 1, 0),   # 4  posterior, grupo aparte
    ("2024-01-27", "C", "A", 1, 1),   # 5  C ya jugó el partido modificado
    ("2024-02-03", "D", "B", 3, 1),   # 6  D ya jugó el partido modificado
    ("2024-02-10", "A", "B", 2, 1),   # 7
    ("2024-02-17", "E", "F", 0, 1),   # 8  posterior, grupo aparte
])


def test_primer_partido_de_cada_equipo_tiene_elo_1500_y_forma_nan():
    feat, _, _ = procesar(CALENDARIO)
    d = CALENDARIO
    equipos = set(d["Home"]) | set(d["Away"])
    for t in sorted(equipos):
        i = next(i for i in d.index if t in (d.at[i, "Home"], d.at[i, "Away"]))
        previos = ((d.loc[:i - 1, "Home"] == t) | (d.loc[:i - 1, "Away"] == t)).sum() if i else 0
        assert previos == 0
        lado = "h" if d.at[i, "Home"] == t else "a"
        assert feat.at[i, f"elo_{lado}"] == 1500.0
        for c in ("pts", "gf", "gc"):
            assert np.isnan(feat.at[i, f"{c}_{lado}"])

    # ya con un partido previo, la forma deja de ser NaN
    assert not np.isnan(feat.at[3, "pts_h"]) and not np.isnan(feat.at[3, "pts_a"])


def test_sin_fuga_cambiar_un_resultado_solo_afecta_partidos_posteriores():
    base, _, _ = procesar(CALENDARIO)
    mod, _, _ = procesar(_con_resultado(CALENDARIO, 2, 0, 3))

    # el partido modificado y los anteriores conservan sus features
    for i in (0, 1, 2):
        assert _igual(_x(base, i), _x(mod, i)), f"fuga en el partido {i}"

    # posteriores entre equipos que no se cruzan con C ni D: no cambian
    for i in (3, 4, 8):
        assert _igual(_x(base, i), _x(mod, i)), f"el partido {i} no debería cambiar"

    # posteriores de los equipos del partido modificado: sí cambian
    for i in (5, 6):
        assert not _igual(_x(base, i), _x(mod, i)), f"el partido {i} debería cambiar"


def test_elo_se_conserva_con_regresion_cero():
    d = CALENDARIO.copy()
    d.loc[5:, "Season"] = "2024/2025"   # cruza de temporada: con regresion=0 no debe tocar el Elo
    _, elo, _ = procesar(d, regresion=0.0)
    equipos = set(d["Home"]) | set(d["Away"])
    assert len(elo) == len(equipos) == 6
    assert sum(elo.values()) == pytest.approx(1500 * len(equipos))


def test_orden_temporal_features_solo_dependen_de_partidos_anteriores():
    # a) con el calendario completo: el partido i procesado solo con d[:i+1] da lo mismo
    full, _, _ = procesar(CALENDARIO)
    for i in CALENDARIO.index:
        corto, _, _ = procesar(CALENDARIO.iloc[: i + 1])
        assert _igual(_x(full, i), _x(corto, i)), f"el partido {i} depende de partidos posteriores"

    # b) mismo día con equipo en común: cuenta el orden del DataFrame
    d = _partidos([
        ("2024-01-06", "A", "B", 1, 0),   # 0
        ("2024-01-06", "B", "C", 2, 0),   # 1  mismo día, después del 0
        ("2024-01-13", "A", "C", 1, 1),   # 2
    ])
    base, _, _ = procesar(d)

    mod0, _, _ = procesar(_con_resultado(d, 0, 0, 4))
    assert _igual(_x(base, 0), _x(mod0, 0))
    assert not _igual(_x(base, 1), _x(mod0, 1))   # el 1 sí ve el resultado del 0

    mod1, _, _ = procesar(_con_resultado(d, 1, 0, 4))
    assert _igual(_x(base, 0), _x(mod1, 0))        # el 0 no ve al 1, aunque sea el mismo día
    assert _igual(_x(base, 1), _x(mod1, 1))


def test_cargar_partidos_ordena_por_fecha_y_probabilidades_suman_1(tmp_path):
    ruta = tmp_path / "mini.csv"
    pd.DataFrame({
        "Season": ["2023/2024"] * 3,
        "Date": ["20/01/2024", "06/01/2024", "13/01/2024"],   # dd/mm/yyyy y en desorden
        "Home": ["A", "B", "C"], "Away": ["B", "C", "A"],
        "HG": [1, 0, 2], "AG": [0, 0, 2], "Res": ["H", "D", "D"],
        "AvgCH": [2.0, 2.5, 1.8], "AvgCD": [3.3, 3.2, 3.6], "AvgCA": [3.5, 2.9, 4.5],
        "extra": [9, 9, 9],
    }).to_csv(ruta, index=False)

    d = cargar_partidos(ruta)
    assert list(d["Date"]) == sorted(d["Date"])
    assert d["Date"].iloc[0] == pd.Timestamp("2024-01-06")   # dayfirst: 06/01 es 6 de enero
    assert list(d["Home"]) == ["B", "C", "A"]
    assert "extra" not in d.columns
    assert np.allclose(d[["pH", "pD", "pA"]].sum(axis=1), 1.0)
    assert set(d["mercado"]) <= {"H", "D", "A"}
