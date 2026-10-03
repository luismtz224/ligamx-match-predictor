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
    """Puntos por partido contra cada rival con al menos `min_duelos` duelos, mejor primero.
    Columnas: n (duelos), ppp (puntos por partido), g, e, p."""
    g = pe.groupby("rival").agg(
        n=("puntos", "size"), ppp=("puntos", "mean"),
        g=("resultado", lambda s: int((s == "V").sum())),
        e=("resultado", lambda s: int((s == "E").sum())),
        p=("resultado", lambda s: int((s == "D").sum())))
    g = g[g["n"] >= min_duelos]
    return g.sort_values(["ppp", "n"], ascending=[False, False])


def mejores_peores(riv, max_k=3):
    """(mejores, peores) de la tabla de `rivales`, sin que las listas se solapen.

    Con n rivales calificados, k = min(max_k, n // 2). Con n = 1 el único rival va en
    `mejores` y `peores` queda vacío; con n = 0 ambos quedan vacíos. `peores` empieza por
    el peor (menos puntos por partido y, a igualdad, más duelos).
    """
    n = len(riv)
    k = min(max_k, n // 2)
    mejores = riv.head(1 if n == 1 else k)
    peores = riv.iloc[n - k:].sort_values(["ppp", "n"], ascending=[True, False]) if k else riv.iloc[0:0]
    return mejores, peores


def clasico(feat, equipo, rival):
    """Duelos de `equipo` contra `rival` desde 2012: dict con n, g, e, p (óptica de
    `equipo`) y `ultimo` (dict con fecha, local, gf, gc; None si no hubo duelos)."""
    duelos = partidos_equipo(feat, equipo)
    duelos = duelos[duelos["rival"] == rival]
    g, e, p = gep(duelos)
    ultimo = None
    if len(duelos):
        u = duelos.iloc[-1]
        ultimo = dict(fecha=u["fecha"], local=bool(u["local"]), gf=int(u["gf"]), gc=int(u["gc"]))
    return dict(n=len(duelos), g=g, e=e, p=p, ultimo=ultimo)


def temporadas(pe):
    """Temporadas que jugó el equipo, de la más vieja a la más reciente."""
    return list(dict.fromkeys(pe["temporada"]))


DIAS_CORTE = 365  # más de un año sin jugar: el trazo de la gráfica se corta


def serie_elo(pe):
    """Puntos de la gráfica del Elo: DataFrame con fecha, elo y `tramo_nuevo`.

    Un punto inicial con `elo_antes` del primer partido y, por partido, `elo_despues`.
    Si pasan más de DIAS_CORTE días entre dos partidos, el siguiente tramo arranca con un
    punto (`tramo_nuevo` = True) con el `elo_antes` de ese partido. Vacío si no hay partidos.
    """
    filas = []
    previa = None
    for t in pe.itertuples():
        if previa is None or (t.fecha - previa).days > DIAS_CORTE:
            filas.append((t.fecha, t.elo_antes, True))
        filas.append((t.fecha, t.elo_despues, False))
        previa = t.fecha
    return pd.DataFrame(filas, columns=["fecha", "elo", "tramo_nuevo"])


def extremos(serie):
    """Máximo, mínimo, inicio y final de la serie: dict de (fecha, elo). None si está vacía.
    En empates, el primer punto."""
    if serie.empty:
        return None
    def par(i):
        return serie["fecha"].iloc[i], float(serie["elo"].iloc[i])
    pos = lambda idx: serie.index.get_loc(idx)
    return dict(maximo=par(pos(serie["elo"].idxmax())), minimo=par(pos(serie["elo"].idxmin())),
                inicio=par(0), final=par(len(serie) - 1))


def ranking(elo, activos):
    """Elo de los equipos activos, de mayor a menor."""
    return pd.Series({e: elo[e] for e in activos}).sort_values(ascending=False)


def posicion(equipo, elo, activos):
    """Lugar (1 = mejor) del equipo en el ranking de activos, o None si no está activo."""
    if equipo not in activos:
        return None
    return list(ranking(elo, activos).index).index(equipo) + 1
