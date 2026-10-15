"""Predicción de un partido con el modelo guardado y conversión de momios.

Misma fórmula que la app anterior: Elo de `est["elo"]` y forma = promedio de `est["hist"]`
(últimos 5 partidos: puntos, goles a favor, goles en contra).
"""
import math
from numbers import Real

import numpy as np
import pandas as pd

from src.features import MAP


def forma(hist, equipo):
    """Promedio de los últimos 5 (puntos, gf, gc); NaN si no hay historial (lo imputa el modelo)."""
    h = hist.get(equipo, [])
    return np.array(h).mean(axis=0) if len(h) else np.array([np.nan] * 3)


def features_partido(est, local, visita):
    """DataFrame de un renglón con las columnas del modelo, en su orden."""
    elo, hist = est["elo"], est["hist"]
    fl, fv = forma(hist, local), forma(hist, visita)
    return pd.DataFrame([dict(elo_diff=elo[local] - elo[visita], elo_h=elo[local], elo_a=elo[visita],
                              pts_h=fl[0], pts_a=fv[0], gf_h=fl[1], gc_h=fl[2],
                              gf_a=fv[1], gc_a=fv[2])])[est["cols"]]


def predecir(est, local, visita):
    """(p_local, p_empate, p_visitante) según el modelo, leyendo el orden de `classes_`."""
    m = est["modelo"]
    p = m.predict_proba(features_partido(est, local, visita))[0]
    clases = list(m[-1].classes_)
    return tuple(float(p[clases.index(MAP[k])]) for k in ("H", "D", "A"))


MOMIO_MIN, MOMIO_MAX = 1.01, 1000.0  # momios decimales: debajo de 1.01 no hay mercado; arriba de 1000 es ruido


def validar_momios(*momios):
    """ValueError con un mensaje claro si algún momio no es un número finito entre MOMIO_MIN y MOMIO_MAX."""
    for m in momios:
        if isinstance(m, bool) or not isinstance(m, Real) or not math.isfinite(m):
            raise ValueError("Los momios deben ser números (por ejemplo 2.10).")
        if not MOMIO_MIN <= m <= MOMIO_MAX:
            raise ValueError(f"Los momios deben estar entre {MOMIO_MIN:g} y {MOMIO_MAX:g}.")


def mercado(momio_local, momio_empate, momio_visita):
    """Probabilidades implícitas sin margen (1/momio normalizado) y margen de la casa.

    Devuelve ((p_local, p_empate, p_visitante), margen), con margen = suma(1/momio) - 1.
    """
    validar_momios(momio_local, momio_empate, momio_visita)
    inv = [1 / momio_local, 1 / momio_empate, 1 / momio_visita]
    total = sum(inv)
    return tuple(i / total for i in inv), total - 1
