"""Fase D: firma discreta en el pie de la app y en el PNG descargable."""
import io
import re
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

from interfaz import componentes as c
from src.equipos import DIR_ESCUDOS
from src.formato import contraste
from src.imagen import ALTO, ANCHO, FONDO, M, TENUE, URL_DEMO, generar_png

CSS = (Path(__file__).resolve().parent.parent / "estilos" / "custom.css").read_text(encoding="utf-8")


class _Enlaces(HTMLParser):
    def __init__(self):
        super().__init__()
        self.enlaces, self._actual = [], None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._actual = {"attrs": dict(attrs), "texto": ""}
            self.enlaces.append(self._actual)

    def handle_data(self, data):
        if self._actual is not None:
            self._actual["texto"] += data

    def handle_endtag(self, tag):
        if tag == "a":
            self._actual = None


def _enlaces(html):
    p = _Enlaces()
    p.feed(html)
    return p.enlaces


# ---------- pie de la app ----------

def test_pie_tiene_los_dos_enlaces_y_el_nombre_sin_enlace():
    html = c.pie_escudos()
    es = _enlaces(html)
    assert [(e["texto"], e["attrs"]["href"]) for e in es] == [
        ("GitHub @luismtz224", "https://github.com/luismtz224"),
        ("Código", "https://github.com/luismtz224/ligamx-match-predictor"),
    ]
    for e in es:
        assert e["attrs"]["target"] == "_blank"
        assert e["attrs"]["rel"] == "noopener noreferrer"
    assert "Hecho por Luis Fernando Martínez" in html
    assert "Luis Fernando" not in "".join(e["texto"] for e in es)  # el nombre no es enlace
    assert c.AVISO_ESCUDOS in html
    assert "\n" not in html and "> <" not in html


def test_pie_escapa_los_dos_enlaces(monkeypatch):
    malo = 'https://x.test/"><script>alert(1)</script>'
    monkeypatch.setattr(c, "URL_PERFIL", malo)
    monkeypatch.setattr(c, "URL_REPO", malo)
    html = c.pie_escudos()
    assert "<script>" not in html and "&lt;script&gt;" in html
    es = _enlaces(html)
    assert len(es) == 2
    assert all(e["attrs"]["href"] == malo for e in es)  # el parser lo des-escapa: es un solo atributo


def test_pie_enlaces_de_48_px_y_se_acomodan_en_celular():
    regla = re.search(r"\.lm-firma a \{([^}]*)\}", CSS).group(1)
    assert "min-height: var(--tap)" in regla and "inline-flex" in regla
    assert re.search(r"--tap:\s*48px", CSS)
    contenedor = re.search(r"\.lm-firma \{([^}]*)\}", CSS).group(1)
    assert "flex-wrap: wrap" in contenedor  # a 390 px pasan a otra línea, sin scroll horizontal


# ---------- PNG ----------

def _png(**kw):
    datos = generar_png("A", "B", [40, 20, 40], ("#ffd500", "#5b86e8"),
                        DIR_ESCUDOS / "512" / "ame.png", DIR_ESCUDOS / "512" / "caz.png", **kw)
    with Image.open(io.BytesIO(datos)) as img:
        img.load()
        return img.convert("RGB")


def _caja(img, x0, y0, x1, y1):
    """Caja (izq, arr, der, aba) de los píxeles distintos del fondo, o None."""
    fondo = tuple(int(FONDO[i:i + 2], 16) for i in (1, 3, 5))
    px = img.load()
    pts = [(x, y) for y in range(y0, y1) for x in range(x0, x1) if px[x, y] != fondo]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def test_png_conserva_dimensiones_y_la_url_queda_dentro_del_margen():
    img = _png()
    assert img.size == (ANCHO, ALTO) == (1080, 1350)
    assert URL_DEMO == "ligamx.streamlit.app"
    der = ANCHO - M
    # la URL vive a la derecha de la línea de y=1284, separada del texto de la izquierda
    caja = _caja(img, 560, 1250, ANCHO, 1300)
    assert caja is not None, "no se dibujó la URL"
    izq, arr, dr, aba = caja
    assert dr <= der and izq > 560 + 60  # dentro del margen derecho y sin tocar el texto izquierdo
    assert arr > 1242 and aba < ALTO - M + 20  # debajo de la línea separadora, sobre el borde
    assert dr - izq > 120  # es una URL, no un punto suelto
    # nada en los márgenes laterales ni pegado al borde inferior en todo el pie
    assert _caja(img, 0, 1242, M, ALTO) is None
    assert _caja(img, der + 1, 1242, ANCHO, ALTO) is None
    assert _caja(img, 0, ALTO - 12, ANCHO, ALTO) is None
    # no tapa nada: la banda de la URL no invade la segunda línea del pie
    sin = _png()
    assert sin.tobytes() == img.tobytes()  # determinista


def test_url_del_png_conserva_contraste_minimo():
    img = _png()
    izq, arr, dr, aba = _caja(img, 560, 1250, ANCHO, 1300)
    px = img.load()
    mas_claro = max((px[x, y] for y in range(arr, aba + 1) for x in range(izq, dr + 1)), key=sum)
    assert contraste(f"#{mas_claro[0]:02x}{mas_claro[1]:02x}{mas_claro[2]:02x}", FONDO) >= 4.5
    assert contraste(TENUE, FONDO) >= 4.5


def test_url_no_choca_con_la_segunda_linea_del_pie():
    img = _png()
    url = _caja(img, 560, 1250, ANCHO, 1300)
    linea2 = _caja(img, M, 1300, ANCHO, 1345)
    assert linea2 is not None and url[3] < linea2[1]  # la URL termina antes de que empiece la línea 2
