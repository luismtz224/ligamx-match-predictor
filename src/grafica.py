"""Geometría pura de las gráficas SVG (Elo de 600×220 y calibración de 360×340). Sin HTML ni Streamlit."""
import math

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


# ===== Gráfica de calibración (SVG de 360 × 340, cuadro de 300 × 300 con el mismo rango en los dos ejes) =====
CAL_ANCHO, CAL_ALTO = 360, 340
CAL_IZQ, CAL_ARRIBA, CAL_LADO = 40, 16, 300  # el cuadro mide CAL_LADO x CAL_LADO; abajo queda lugar para las etiquetas
CAL_R_MIN, CAL_R_MAX = 3.0, 6.0  # radio del punto: crece con la raíz de n (partidos del grupo)
CAL_DX = {"logistica": -3.0, "mercado": 3.0}  # separa las dos series cuando caen casi en el mismo lugar
CAL_PASO_ETIQUETA = 0.1
CAL_HOLGURA = 0.03
CAL_REDONDEO = 0.05  # los extremos del rango se redondean hacia afuera a múltiplos de 5 %


def rango_calibracion(series):
    """(lo, hi) común a los dos ejes: cubre puntos y barras de todas las series con 3 puntos de holgura,
    redondeado hacia afuera a múltiplos de 5 %, sin salirse de [0, 1]."""
    valores = []
    for tabla in series.values():
        for col in ("pred", "freq", "wilson_lo", "wilson_hi"):
            valores += list(tabla[col])
    lo = max(0.0, math.floor((min(valores) - CAL_HOLGURA) / CAL_REDONDEO) * CAL_REDONDEO)
    hi = min(1.0, math.ceil((max(valores) + CAL_HOLGURA) / CAL_REDONDEO) * CAL_REDONDEO)
    return round(lo, 4), round(hi, 4)


def geometria_calibracion(series):
    """Geometría del diagrama de confiabilidad. `series` = {nombre: DataFrame con pred, freq, wilson_lo,
    wilson_hi y n}, un renglón por grupo. Devuelve None si no hay datos.

    Eje X = probabilidad que dio el modelo; eje Y = frecuencia con que sí pasó (SVG: y crece hacia abajo).
    dict con: rango, etiquetas (lista de {texto, x, y, eje}), rejilla y diagonal (atributos d) y
    series: {nombre: {puntos: [{x, y, r, n, y_lo, y_hi}], ic: d de las barras con sus remates}}.
    """
    series = {k: v for k, v in series.items() if len(v)}
    if not series:
        return None
    lo, hi = rango_calibracion(series)

    def x_de(v):
        return CAL_IZQ + (v - lo) / (hi - lo) * CAL_LADO

    def y_de(v):
        return CAL_ARRIBA + (hi - v) / (hi - lo) * CAL_LADO

    n_max = max(int(t["n"].max()) for t in series.values())
    valores = []
    v = math.ceil(lo / CAL_PASO_ETIQUETA - 1e-9) * CAL_PASO_ETIQUETA
    while v <= hi + 1e-9:
        valores.append(round(v, 4))
        v += CAL_PASO_ETIQUETA
    etiquetas, rejilla = [], []
    for v in valores:
        texto = f"{v * 100:.0f}%"
        etiquetas.append(dict(texto=texto, x=_fmt(CAL_IZQ - 6), y=_fmt(y_de(v) + 4), eje="y"))
        etiquetas.append(dict(texto=texto, x=_fmt(x_de(v)), y=_fmt(CAL_ARRIBA + CAL_LADO + 16), eje="x"))
        rejilla.append(f"M{CAL_IZQ} {_fmt(y_de(v))} H{CAL_IZQ + CAL_LADO}")
        rejilla.append(f"M{_fmt(x_de(v))} {CAL_ARRIBA} V{CAL_ARRIBA + CAL_LADO}")
    diagonal = f"M{_fmt(x_de(lo))} {_fmt(y_de(lo))} L{_fmt(x_de(hi))} {_fmt(y_de(hi))}"

    salida = {}
    for nombre, tabla in series.items():
        dx = CAL_DX.get(nombre, 0.0)
        puntos, ic = [], []
        for t in tabla.itertuples():
            x = x_de(t.pred) + dx
            r = CAL_R_MIN + (CAL_R_MAX - CAL_R_MIN) * math.sqrt(t.n / n_max)
            y_lo, y_hi = y_de(t.wilson_lo), y_de(t.wilson_hi)  # y_lo es el extremo de ABAJO (mayor y en SVG)
            puntos.append(dict(x=round(x, 1), y=round(y_de(t.freq), 1), r=round(r, 1), n=int(t.n),
                               y_lo=round(y_lo, 1), y_hi=round(y_hi, 1)))
            ic.append(f"M{_fmt(x)} {_fmt(y_lo)} V{_fmt(y_hi)} M{_fmt(x - 3)} {_fmt(y_lo)} h6 M{_fmt(x - 3)} {_fmt(y_hi)} h6")
        salida[nombre] = dict(puntos=puntos, ic=" ".join(ic))
    return dict(rango=(lo, hi), etiquetas=etiquetas, rejilla=" ".join(rejilla), diagonal=diagonal, series=salida)
