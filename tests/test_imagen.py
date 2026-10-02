import io

from PIL import Image, ImageDraw, ImageFont

from src.equipos import DIR_ESCUDOS
from src.imagen import ALTO, ANCHO, _fuente, generar_png


def test_png_se_genera_con_tamano_esperado():
    datos = generar_png("Guadalajara Chivas", "Club America", [27, 29, 44],
                        ("#CE0E2D", "#FFEB00"),
                        DIR_ESCUDOS / "512" / "chi.png", DIR_ESCUDOS / "512" / "ame.png")
    assert datos[:8] == b"\x89PNG\r\n\x1a\n"
    with Image.open(io.BytesIO(datos)) as img:
        img.load()
        assert img.size == (ANCHO, ALTO) == (1080, 1350)
        assert img.format == "PNG"


def _dibujo(fuente, c):
    img = Image.new("L", (100, 100))
    ImageDraw.Draw(img).text((10, 10), c, font=fuente, fill=255)
    return img.tobytes()


def _sin_cuadros(fuente):
    tofu = _dibujo(fuente, "\uffff")  # caracter que ninguna fuente tiene
    return all(_dibujo(fuente, c) != tofu for c in "áéíóúñÁÉÍÓÚÑ·")


def test_fuente_tiene_acentos():
    """La fuente por defecto de Pillow dibuja un cuadro en vez de 'ó'; la nuestra no."""
    assert _sin_cuadros(_fuente(60, 400))
    assert not _sin_cuadros(ImageFont.load_default(size=60))  # la prueba sí detecta el problema
