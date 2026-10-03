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


def _abrir(datos):
    with Image.open(io.BytesIO(datos)) as img:
        img.load()
        return img.size, img.format, img.convert("RGB")


def test_png_completo_con_forma_h2h_y_nombres_largos():
    datos = generar_png("Atlético de San Luis", "Dorados de Sinaloa", [34, 33, 33],
                        ("#f16070", "#aa8317"),
                        DIR_ESCUDOS / "512" / "adsl.png", DIR_ESCUDOS / "512" / "dor.png",
                        forma=(list("VEDVV"), list("DD")),
                        h2h=dict(g=3, e=2, p=1, ultimo="13 sep 2026, Atlético de San Luis 4–3 Dorados"))
    assert _abrir(datos)[:2] == ((ANCHO, ALTO), "PNG")


def test_png_sin_duelos_y_sin_forma():
    datos = generar_png("A", "B", [50, 25, 25], ("#ffd500", "#5b86e8"),
                        DIR_ESCUDOS / "512" / "ame.png", DIR_ESCUDOS / "512" / "caz.png",
                        forma=([], []), h2h=dict(g=0, e=0, p=0, ultimo=None))
    assert _abrir(datos)[:2] == ((ANCHO, ALTO), "PNG")


def test_segmento_oscuro_lleva_borde():
    """Un color que casi no contrasta con el fondo lleva borde gris en la barra."""
    oscuro = "#101020"
    _, _, img = _abrir(generar_png("A", "B", [40, 20, 40], ("#ffd500", oscuro),
                                   DIR_ESCUDOS / "512" / "ame.png", DIR_ESCUDOS / "512" / "caz.png"))
    # dentro del segmento visitante (derecha de la barra, y=720..760): borde arriba, relleno al centro
    x = 850
    assert img.getpixel((x, 722)) == (0x6B, 0x6B, 0x92)  # LINEA_FUERTE
    assert img.getpixel((x, 740)) == (0x10, 0x10, 0x20)
    # el amarillo (contraste alto) no lleva borde
    assert img.getpixel((200, 722)) == (0xFF, 0xD5, 0x00)


def test_halo_aclara_el_fondo_detras_del_escudo():
    """Atlas y Lobos BUAP llevan halo: el fondo detrás del escudo deja de ser el color base."""
    args = ("A", "B", [40, 20, 40], ("#ffd500", "#5b86e8"),
            DIR_ESCUDOS / "512" / "ame.png", DIR_ESCUDOS / "512" / "ats.png")
    _, _, sin = _abrir(generar_png(*args))
    _, _, con = _abrir(generar_png(*args, halos=(False, True)))
    # esquina del cuadro del escudo visitante, dentro del halo pero fuera del escudo
    x, y = 1080 - 64 - 200 + 60, 136 + 60
    assert sin.getpixel((x, y)) == (7, 7, 13)
    assert sum(con.getpixel((x, y))) > sum(sin.getpixel((x, y))) + 60
