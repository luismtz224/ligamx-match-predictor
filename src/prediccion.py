"""Predicción de un partido con el modelo guardado y conversión de momios.

Misma fórmula que la app anterior: Elo de `est["elo"]` y forma = promedio de `est["hist"]`
(últimos 5 partidos: puntos, goles a favor, goles en contra).
"""
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


def mercado(momio_local, momio_empate, momio_visita):
    """Probabilidades implícitas sin margen (1/momio normalizado) y margen de la casa.

    Devuelve ((p_local, p_empate, p_visitante), margen), con margen = suma(1/momio) - 1.
    """
    inv = [1 / momio_local, 1 / momio_empate, 1 / momio_visita]
    total = sum(inv)
    return tuple(i / total for i in inv), total - 1
