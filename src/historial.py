"""Historial por equipo a partir de la salida de `procesar()`. No recalcula el Elo."""
import pandas as pd

RESULTADO = {"H": ("V", "D"), "D": ("E", "E"), "A": ("D", "V")}  # (local, visitante)
PUNTOS = {"V": 3, "E": 1, "D": 0}


def partidos_equipo(feat, equipo, elo_final=None):
    """Un renglón por partido del equipo, en orden cronológico.

    `elo_despues` es el Elo con el que el equipo llega a su siguiente partido en
    `procesar()`; para el último partido es su Elo final (`elo_final[equipo]`), o NaN si
    no se pasa `elo_final`.
    """
    m = feat[(feat["Home"] == equipo) | (feat["Away"] == equipo)].sort_index()
    local = m["Home"] == equipo
    pe = pd.DataFrame({
        "fecha": m["Date"],
        "temporada": m["Season"],
        "local": local,
        "rival": m["Away"].where(local, m["Home"]),
        "gf": m["HG"].where(local, m["AG"]).astype(int),
        "gc": m["AG"].where(local, m["HG"]).astype(int),
        "goles_local": m["HG"].astype(int),
        "goles_visita": m["AG"].astype(int),
        "resultado": [RESULTADO[r][0 if l else 1] for r, l in zip(m["Res"], local)],
        "elo_antes": m["elo_h"].where(local, m["elo_a"]),
    }).reset_index(drop=True)
    pe["puntos"] = pe["resultado"].map(PUNTOS)
    pe["elo_despues"] = pe["elo_antes"].shift(-1)
    if len(pe) and elo_final is not None:
        pe.loc[pe.index[-1], "elo_despues"] = elo_final[equipo]
    return pe


def filtrar_temporada(pe, temporada=None):
    """None = todas las temporadas."""
    return pe if temporada is None else pe[pe["temporada"] == temporada].reset_index(drop=True)


def record(pe):
    """PJ, G, E, P y goles por partido, de local y de visitante."""
    filas = {}
    for nombre, sub in (("Local", pe[pe["local"]]), ("Visitante", pe[~pe["local"]])):
        pj = len(sub)
        filas[nombre] = {
            "PJ": pj,
            "G": int((sub["resultado"] == "V").sum()),
            "E": int((sub["resultado"] == "E").sum()),
            "P": int((sub["resultado"] == "D").sum()),
            "GF_pp": sub["gf"].mean() if pj else float("nan"),
            "GC_pp": sub["gc"].mean() if pj else float("nan"),
        }
    return pd.DataFrame(filas).T


def racha(pe):
    """(resultado, n): mismo resultado consecutivo en los partidos más recientes."""
    if pe.empty:
        return None, 0
    res = pe["resultado"].tolist()
    ultimo, n = res[-1], 0
    for r in reversed(res):
        if r != ultimo:
            break
        n += 1
    return ultimo, n


def ultimos(pe, n):
    """Últimos n partidos, el más reciente al final."""
    return pe.tail(n).reset_index(drop=True)


def gep(pe):
    """Ganados, empatados y perdidos."""
    return tuple(int((pe["resultado"] == r).sum()) for r in ("V", "E", "D"))


def h2h(feat, equipo, rival, n=5):
    """Duelos de `equipo` contra `rival`: (G, E, P) desde la óptica de `equipo` y últimos n."""
    pe = partidos_equipo(feat, equipo)
    duelos = pe[pe["rival"] == rival].reset_index(drop=True)
    return gep(duelos), duelos.tail(n).reset_index(drop=True)


def rivales(pe, min_duelos=6):
    """Puntos por partido contra cada rival con al menos `min_duelos` duelos, mejor primero."""
    g = pe.groupby("rival").agg(n=("puntos", "size"), ppp=("puntos", "mean"))
    g = g[g["n"] >= min_duelos]
    return g.sort_values(["ppp", "n"], ascending=[False, False])


def ranking(elo, activos):
    """Elo de los equipos activos, de mayor a menor."""
    return pd.Series({e: elo[e] for e in activos}).sort_values(ascending=False)


def posicion(equipo, elo, activos):
    """Lugar (1 = mejor) del equipo en el ranking de activos, o None si no está activo."""
    if equipo not in activos:
        return None
    return list(ranking(elo, activos).index).index(equipo) + 1
