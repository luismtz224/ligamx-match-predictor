"""Imagen vertical (1080x1350) de una predicción, para descargar. Solo Pillow.

Paleta Noche (la de estilos/custom.css). Todo se alinea a un margen de 64 px.
Fuente: Source Sans 3 variable (OFL, licencia en assets/fuentes/OFL.txt). La que trae
Pillow (Aileron) no tiene acentos.
"""
import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.formato import contraste
from src.huella import huella

RUTA_FUENTE = Path(__file__).resolve().parent.parent / "assets" / "fuentes" / "SourceSans3VF-Upright.woff2"

ANCHO, ALTO = 1080, 1350
M = 64  # margen
FONDO = "#07070d"
SUPERFICIE = "#0f0f1a"
LINEA = "#2c2c44"
LINEA_FUERTE = "#6b6b92"
TEXTO = "#f5f5fa"
TENUE = "#a9a9c4"
ACENTO = "#2dd4bf"
EMPATE = "#9a9ab4"
RESULTADO = {"V": "#34d399", "E": "#9a9ab4", "D": "#f87171"}
SOBRE_ESTADO = "#0a0a12"
PIE = ("Predicción del modelo · ligamx.streamlit.app",
       "Proyecto educativo, no es recomendación de apuestas")


@lru_cache(maxsize=64)
def _fuente_cacheada(tam, peso, contenido):
    f = ImageFont.truetype(str(RUTA_FUENTE), tam)
    f.set_variation_by_axes([peso])
    return f


def _fuente(tam, peso):
    """Fuente de ese tamaño y peso; si el archivo de la fuente cambia, se vuelve a cargar."""
    return _fuente_cacheada(tam, peso, huella(RUTA_FUENTE))


def _texto(d, xy, txt, tam, color=TEXTO, peso=400, ancla="ls", ancho_max=None):
    """Dibuja texto; si no cabe en ancho_max, reduce el tamaño."""
    while ancho_max and tam > 12 and d.textlength(txt, font=_fuente(tam, peso)) > ancho_max:
        tam -= 2
    d.text(xy, txt, font=_fuente(tam, peso), fill=color, anchor=ancla)


def _halo(lienzo, x, y, lado):
    """Resplandor claro detrás del escudo (para los que se pierden en fondo oscuro), como
    `.lm-crest.halo` del CSS: blanco (alpha .45) al centro que se desvanece hacia el 60% del radio."""
    capa = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    px = capa.load()
    r = lado / 2
    for j in range(lado):
        for i in range(lado):
            t = ((i - r + 0.5) ** 2 + (j - r + 0.5) ** 2) ** 0.5 / (0.60 * r)
            if t < 1:
                px[i, j] = (245, 245, 250, round(115 * (1 - t)))
    lienzo.alpha_composite(capa, (x, y))


def _escudo(lienzo, ruta, x, y, lado, halo=False):
    if halo:
        _halo(lienzo, x, y, lado)
    with Image.open(ruta) as img:
        img = img.convert("RGBA").resize((lado, lado), Image.Resampling.LANCZOS)
    lienzo.alpha_composite(img, (x, y))


def _barra(lienzo, caja, pct, colores):
    """Barra apilada con esquinas redondeadas. Los segmentos que casi no se distinguen del
    fondo (contraste < 3:1) llevan borde."""
    x0, y0, x1, y1 = caja
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    x, segmentos = x0, []
    for i, (p, c) in enumerate(zip(pct, colores)):
        fin = x1 if i == len(pct) - 1 else x + round((x1 - x0) * p / 100)
        d.rectangle((x, y0, fin, y1), fill=c)
        segmentos.append((x, fin, c))
        x = fin
    for xa, xb, c in segmentos:
        if xb > xa and contraste(c, FONDO) < 3:
            d.rectangle((xa + 1, y0 + 1, xb - 1, y1 - 1), outline=LINEA_FUERTE, width=2)
    radio = (y1 - y0) // 2
    mascara = Image.new("L", lienzo.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(caja, radius=radio, fill=255)
    lienzo.paste(capa, (0, 0), mascara)


def _circulos(d, resultados, x_fin, y_centro, lado=52, hueco=12):
    """Círculos V/E/D alineados a la derecha en x_fin; el más reciente a la derecha."""
    x = x_fin - len(resultados) * lado - (len(resultados) - 1) * hueco
    for i, r in enumerate(resultados):
        caja = (x, y_centro - lado // 2, x + lado, y_centro + lado // 2)
        if i == len(resultados) - 1:
            d.ellipse((caja[0] - 6, caja[1] - 6, caja[2] + 6, caja[3] + 6), outline=TEXTO, width=3)
        d.ellipse(caja, fill=RESULTADO[r])
        _texto(d, (x + lado // 2, y_centro), r, 26, SOBRE_ESTADO, peso=700, ancla="mm")
        x += lado + hueco


def generar_png(local, visita, pct, colores, escudo_local, escudo_visita, forma=None, h2h=None,
                halos=(False, False)):
    """PNG en bytes.

    local, visita: nombres para mostrar.
    pct: porcentajes enteros (local, empate, visitante) que suman 100.
    colores: (hex local, hex visitante), los mismos de la barra de la página.
    escudo_*: rutas a los PNG de 512 px.
    forma: opcional, (resultados local, resultados visitante), listas de 'V'/'E'/'D' del más
        viejo al más reciente.
    h2h: opcional, dict con g, e, p (óptica del local) y `ultimo` (texto del último duelo).
    halos: (local, visitante), True para los escudos que se pierden en fondo oscuro.
    """
    img = Image.new("RGBA", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(img)
    der = ANCHO - M

    _texto(d, (M, 96), "LIGA MX · PREDICCIÓN DEL MODELO", 30, ACENTO, peso=700)

    # equipos
    _escudo(img, escudo_local, M, 136, 200, halo=halos[0])
    _escudo(img, escudo_visita, der - 200, 136, 200, halo=halos[1])
    _texto(d, (ANCHO // 2, 236), "vs", 40, TENUE, ancla="mm")
    _texto(d, (M, 392), local, 48, peso=700, ancho_max=440)
    _texto(d, (der, 392), visita, 48, peso=700, ancla="rs", ancho_max=440)
    _texto(d, (M, 436), "LOCAL", 24, TENUE, peso=600)
    _texto(d, (der, 436), "VISITANTE", 24, TENUE, peso=600, ancla="rs")

    # tarjetas
    ancho_t, hueco = (der - M - 2 * 24) // 3, 24
    mayor = max(range(3), key=lambda i: pct[i])
    acentos = (colores[0], ACENTO, colores[1])
    for i, etiqueta in enumerate(("LOCAL", "EMPATE", "VISITANTE")):
        x0 = M + i * (ancho_t + hueco)
        top = i == mayor
        d.rounded_rectangle((x0, 488, x0 + ancho_t, 688), radius=24, fill=SUPERFICIE,
                            outline=acentos[i] if top else LINEA, width=5 if top else 2)
        _texto(d, (x0 + 24, 536), etiqueta, 24, acentos[i] if top else TENUE, peso=700)
        _texto(d, (x0 + 24, 648), f"{pct[i]}%", 96, TEXTO, peso=700)

    _barra(img, (M, 720, der, 760), pct, (colores[0], EMPATE, colores[1]))

    # forma
    if forma:
        _texto(d, (M, 840), "ÚLTIMOS 5 PARTIDOS · EL MÁS RECIENTE A LA DERECHA", 24, TENUE, peso=700)
        for y, nombre, res in ((896, local, forma[0]), (968, visita, forma[1])):
            _texto(d, (M, y + 12), nombre, 34, peso=600, ancho_max=440)
            if res:
                _circulos(d, list(res)[-5:], der - 6, y)  # 6 px: el anillo del más reciente

    # historial
    if h2h is not None:
        _texto(d, (M, 1056), "HISTORIAL DESDE 2012", 24, TENUE, peso=700)
        n = h2h["g"] + h2h["e"] + h2h["p"]
        if n:
            col = (der - M) // 3
            for i, (v, etiqueta, c) in enumerate(((h2h["g"], f"Gana {local}", colores[0]),
                                                  (h2h["e"], "Empates", TENUE),
                                                  (h2h["p"], f"Gana {visita}", colores[1]))):
                _texto(d, (M + i * col, 1118), str(v), 56, c, peso=700)
                _texto(d, (M + i * col, 1152), etiqueta, 24, TENUE, ancho_max=col - 24)
            ultimo = f" · último: {h2h['ultimo']}" if h2h.get("ultimo") else ""
            _texto(d, (M, 1196), f"{n} duelo{'s' if n != 1 else ''}{ultimo}", 24, TENUE,
                   ancho_max=der - M)
        else:
            _texto(d, (M, 1110), "Sin duelos entre estos equipos desde 2012", 28, TENUE)

    d.line((M, 1240, der, 1240), fill=LINEA, width=2)
    _texto(d, (M, 1284), PIE[0], 28, TENUE)
    _texto(d, (M, 1320), PIE[1], 28, TENUE)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
