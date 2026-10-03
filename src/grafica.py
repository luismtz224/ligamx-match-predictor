"""Geometría pura de la gráfica del Elo (SVG de 600×220). Sin HTML ni Streamlit."""
ANCHO, ALTO = 600, 220
IZQ, DER, ARRIBA, ABAJO = 8, 8, 12, 12
REFERENCIA = 1500
HOLGURA = 0.05
RANGO_MIN = 40


def escala_y(valores):
    """(lo, hi): rango de los valores con 5 % de holgura y al menos RANGO_MIN puntos."""
    lo, hi = min(valores), max(valores)
    holgura = (hi - lo) * HOLGURA
    lo, hi = lo - holgura, hi + holgura
    if hi - lo < RANGO_MIN:
        centro = (hi + lo) / 2
        lo, hi = centro - RANGO_MIN / 2, centro + RANGO_MIN / 2
    return lo, hi


def _fmt(x):
    return f"{x:.1f}"


def geometria(serie):
    """Paths y marcadores de la serie de `historial.serie_elo`. None si está vacía.

    dict con: linea, area, rejilla (atributos d), puntos (lista de dict x, y, tipo con
    'min', 'max' y 'final', sin repetir posición en el lienzo), cortes (bool) y rango (lo, hi).
    El eje X es el tiempo: un hueco largo queda en blanco y el trazo lleva un `M` nuevo.
    """
    if serie.empty:
        return None
    lo, hi = escala_y(serie["elo"])
    t0, t1 = serie["fecha"].iloc[0], serie["fecha"].iloc[-1]
    dias = (t1 - t0).days
    ancho_util, alto_util = ANCHO - IZQ - DER, ALTO - ARRIBA - ABAJO
    base = ALTO - ABAJO

    def x(fecha):
        return IZQ + (ancho_util / 2 if dias == 0 else (fecha - t0).days / dias * ancho_util)

    def y(v):
        return ARRIBA + (hi - v) / (hi - lo) * alto_util

    xs = [x(f) for f in serie["fecha"]]
    ys = [y(v) for v in serie["elo"]]
    tramos, actual = [], []
    for xi, yi, nuevo in zip(xs, ys, serie["tramo_nuevo"]):
        if nuevo and actual:
            tramos.append(actual)
            actual = []
        actual.append((xi, yi))
    tramos.append(actual)

    linea = " ".join("M" + " L".join(f"{_fmt(a)} {_fmt(b)}" for a, b in t) for t in tramos)
    area = " ".join(
        f"M{_fmt(t[0][0])} {_fmt(base)} " + " ".join(f"L{_fmt(a)} {_fmt(b)}" for a, b in t)
        + f" L{_fmt(t[-1][0])} {_fmt(base)} Z" for t in tramos)
    niveles = [lo + (hi - lo) * f for f in (0.25, 0.5, 0.75)]
    rejilla = " ".join(f"M{IZQ} {_fmt(y(v))} H{ANCHO - DER}" for v in niveles)
    if lo <= REFERENCIA <= hi:
        rejilla += f" M{IZQ} {_fmt(y(REFERENCIA))} H{ANCHO - DER}"

    i_max = int(serie["elo"].values.argmax())
    i_min = int(serie["elo"].values.argmin())
    puntos, usados = [], set()
    for tipo, i in (("max", i_max), ("min", i_min), ("final", len(serie) - 1)):
        pos = (round(xs[i], 1), round(ys[i], 1))
        if pos not in usados:  # por posición: una serie plana no dibuja marcadores encimados
            usados.add(pos)
            puntos.append(dict(x=pos[0], y=pos[1], tipo=tipo))
    return dict(linea=linea, area=area, rejilla=rejilla, puntos=puntos,
                cortes=len(tramos) > 1, rango=(lo, hi))
