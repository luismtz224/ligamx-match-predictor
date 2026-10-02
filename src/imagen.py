"""Imagen vertical (1080x1350) de una predicción, para descargar. Solo Pillow.

Fuente: Source Sans 3 variable (OFL, licencia en assets/fuentes/OFL.txt). La que trae
Pillow (Aileron) no tiene acentos.
"""
import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.formato import FONDO, GRIS_EMPATE

RUTA_FUENTE = Path(__file__).resolve().parent.parent / "assets" / "fuentes" / "SourceSans3VF-Upright.woff2"

ANCHO, ALTO = 1080, 1350
ACENTO = "#00C26F"
TEXTO = "#FAFAFA"
TENUE = "#9CA3AF"
TARJETA = "#1A1F2B"
PIE = ("Predicción del modelo · ligamx.streamlit.app",
       "Proyecto educativo, no es recomendación de apuestas")


@lru_cache(maxsize=64)
def _fuente(tam, peso):
    f = ImageFont.truetype(str(RUTA_FUENTE), tam)
    f.set_variation_by_axes([peso])
    return f


def _texto(d, xy, txt, tam, color=TEXTO, peso=400, ancla="mm", ancho_max=None):
    """Dibuja texto centrado; si no cabe en ancho_max, reduce el tamaño."""
    while ancho_max and tam > 12 and d.textlength(txt, font=_fuente(tam, peso)) > ancho_max:
        tam -= 2
    d.text(xy, txt, font=_fuente(tam, peso), fill=color, anchor=ancla)


def _escudo(lienzo, ruta, centro, lado):
    with Image.open(ruta) as img:
        img = img.convert("RGBA").resize((lado, lado), Image.Resampling.LANCZOS)
    lienzo.alpha_composite(img, (centro[0] - lado // 2, centro[1] - lado // 2))


def _barra(lienzo, caja, pct, colores):
    """Barra apilada con esquinas redondeadas; segmentos proporcionales a pct."""
    x0, y0, x1, y1 = caja
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    x = x0
    for i, (p, c) in enumerate(zip(pct, colores)):
        fin = x1 if i == len(pct) - 1 else x + round((x1 - x0) * p / 100)
        d.rectangle((x, y0, fin, y1), fill=c)
        x = fin
    mascara = Image.new("L", lienzo.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(caja, radius=(y1 - y0) // 2, fill=255)
    lienzo.paste(capa, (0, 0), mascara)


def generar_png(local, visita, pct, colores, escudo_local, escudo_visita):
    """PNG en bytes.

    pct: porcentajes enteros (local, empate, visitante) que suman 100.
    colores: (color local, color visitante) para la barra.
    escudo_*: rutas a los PNG de 512 px.
    """
    img = Image.new("RGBA", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(img)

    _texto(d, (ANCHO // 2, 90), "LIGA MX · PREDICCIÓN", 42, ACENTO, peso=700)

    for cx, ruta, nombre, rol in ((270, escudo_local, local, "LOCAL"),
                                  (810, escudo_visita, visita, "VISITANTE")):
        _escudo(img, ruta, (cx, 340), 320)
        _texto(d, (cx, 560), nombre, 54, peso=700, ancho_max=470)
        _texto(d, (cx, 615), rol, 32, TENUE, peso=600)
    _texto(d, (ANCHO // 2, 340), "vs", 44, TENUE)

    mayor = max(range(3), key=lambda i: pct[i])
    for i, (cx, etiqueta) in enumerate(((190, "Local"), (540, "Empate"), (890, "Visitante"))):
        caja = (cx - 160, 690, cx + 160, 930)
        d.rounded_rectangle(caja, radius=28, fill=TARJETA,
                            outline=ACENTO if i == mayor else None, width=5)
        _texto(d, (cx, 790), f"{pct[i]}%", 112, TEXTO, peso=800)
        _texto(d, (cx, 885), etiqueta, 38, ACENTO if i == mayor else TENUE, peso=600)

    _barra(img, (90, 990, 990, 1060), pct, (colores[0], GRIS_EMPATE, colores[1]))

    _texto(d, (ANCHO // 2, 1220), PIE[0], 34, TENUE)
    _texto(d, (ANCHO // 2, 1270), PIE[1], 34, TENUE)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
