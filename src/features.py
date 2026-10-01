from collections import defaultdict, deque

import numpy as np
import pandas as pd

X_COLS = ["elo_diff", "elo_h", "elo_a", "pts_h", "pts_a", "gf_h", "gc_h", "gf_a", "gc_a"]
MAP = {"A": 0, "D": 1, "H": 2}

COLS_UTILES = ["Season", "Date", "Home", "Away", "HG", "AG", "Res", "AvgCH", "AvgCD", "AvgCA"]


def cargar_partidos(ruta):
    """Lee el CSV crudo, ordena por fecha y agrega probabilidades del mercado sin margen."""
    df = pd.read_csv(ruta)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)  # viene dd/mm/yyyy
    d = df[COLS_UTILES].copy().sort_values("Date").reset_index(drop=True)

    inv = 1 / d[["AvgCH", "AvgCD", "AvgCA"]]
    prob = inv.div(inv.sum(axis=1), axis=0)
    prob.columns = ["pH", "pD", "pA"]
    d = pd.concat([d, prob], axis=1)

    # predicción del mercado = el resultado con mayor probabilidad
    d["mercado"] = prob.idxmax(axis=1).map({"pH": "H", "pD": "D", "pA": "A"})
    return d


def _resumen(q):
    return np.array(q).mean(axis=0) if len(q) else np.array([np.nan] * 3)


def procesar(d, K=20, ventaja=60, regresion=0.0):
    """Calcula Elo y forma (últimos 5) por partido. Devuelve (feat, elo, hist)."""
    elo = defaultdict(lambda: 1500.0)
    hist = defaultdict(lambda: deque(maxlen=5))  # (puntos, goles a favor, goles en contra)
    filas, temp = [], None
    for r in d.itertuples():
        if r.Season != temp:
            # nueva temporada: regresión a la media (solo si regresion > 0)
            if temp is not None and regresion > 0:
                for t in list(elo):
                    elo[t] = 1500 + (1 - regresion) * (elo[t] - 1500)
            temp = r.Season
        h, a = r.Home, r.Away
        ph, gfh, gch = _resumen(hist[h])
        pa, gfa, gca = _resumen(hist[a])
        # features con lo que se sabía ANTES del partido
        filas.append(dict(elo_h=elo[h], elo_a=elo[a], pts_h=ph, gf_h=gfh, gc_h=gch,
                          pts_a=pa, gf_a=gfa, gc_a=gca))
        # actualizar DESPUÉS de guardar las features
        s = {"H": 1.0, "D": 0.5, "A": 0.0}[r.Res]
        esp = 1 / (1 + 10 ** ((elo[a] - (elo[h] + ventaja)) / 400))
        elo[h] += K * (s - esp)
        elo[a] -= K * (s - esp)
        hist[h].append(({"H": 3, "D": 1, "A": 0}[r.Res], r.HG, r.AG))
        hist[a].append(({"H": 0, "D": 1, "A": 3}[r.Res], r.AG, r.HG))
    out = pd.concat([d.reset_index(drop=True), pd.DataFrame(filas)], axis=1)
    out["elo_diff"] = out["elo_h"] - out["elo_a"]
    out["y"] = out["Res"].map(MAP)
    return out, elo, hist
