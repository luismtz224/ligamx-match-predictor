"""Utilidades de presentación sin Streamlit: redondeo de porcentajes y colores."""
import math

FONDO = "#0E1117"
GRIS_EMPATE = "#6B7280"
UMBRAL_PARECIDOS = 30.0  # delta E (CIE76); abajo de esto dos colores se confunden en la barra


def redondear_100(probs):
    """Porcentajes enteros que suman 100 (método del mayor residuo)."""
    total = sum(probs)
    crudos = [100 * p / total for p in probs]
    enteros = [math.floor(c) for c in crudos]
    faltan = 100 - sum(enteros)
    orden = sorted(range(len(crudos)), key=lambda i: crudos[i] - enteros[i], reverse=True)
    for i in orden[:faltan]:
        enteros[i] += 1
    return enteros


def hex_a_rgb(color):
    c = color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _lineal(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(color):
    """Luminancia relativa (WCAG 2.x), de 0 (negro) a 1 (blanco)."""
    r, g, b = (_lineal(c) for c in hex_a_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(c1, c2):
    l1, l2 = sorted((luminancia(c1), luminancia(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def texto_sobre(color):
    """Blanco o negro, el que tenga más contraste sobre el color de fondo dado."""
    return "#000000" if contraste(color, "#000000") >= contraste(color, "#FFFFFF") else "#FFFFFF"


def _lab(color):
    r, g, b = (_lineal(c) for c in hex_a_rgb(color))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def delta_e(c1, c2):
    """Distancia perceptual CIE76 entre dos colores hex."""
    return math.dist(_lab(c1), _lab(c2))


def colores_barra(colores_local, colores_visita):
    """Color del local y del visitante para la barra apilada.

    El local usa su color1. El visitante usa su color1, salvo que se parezca demasiado
    al del local; entonces usa su color2 (o el color3 si el color2 también se parece).
    """
    c_local = colores_local[0]
    for c in colores_visita:
        if c and delta_e(c_local, c) >= UMBRAL_PARECIDOS:
            return c_local, c
    return c_local, colores_visita[1] if len(colores_visita) > 1 else colores_visita[0]


def color_acento(colores, fondo=FONDO, minimo=3.0):
    """Primer color del equipo que se distingue del fondo (contraste >= 3:1)."""
    for c in colores:
        if c and contraste(c, fondo) >= minimo:
            return c
    return max((c for c in colores if c), key=lambda c: contraste(c, fondo))
