"""Clic REAL de ratón (Input.dispatchMouseEvent por CDP, en Edge) sobre las tarjetas de la rejilla de
Equipos y sobre las filas del Ranking, a 390 y 1280 px.

No usa `element.click()`: ese atajo ignora la geometría y dejó pasar un overlay de 16 × 0 px (el enlace
transparente no cubría la tarjeta y el clic solo seleccionaba el texto). Aquí, en 7 puntos de la tarjeta
(centro, texto, escudo y las 4 esquinas) `document.elementFromPoint` debe quedar dentro del enlace, y un
clic real en la esquina inferior (donde fallaba) debe abrir el equipo desde arriba y sin recargar.

Necesita Microsoft Edge y `websocket-client` (requirements-dev.txt); si no están, se omite. Arranca su
propio Streamlit en un puerto libre y un perfil temporal de Edge que se borra al terminar.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

websocket = pytest.importorskip("websocket")

RAIZ = Path(__file__).resolve().parent.parent
EDGE = os.environ.get("EDGE_PATH") or next(
    (p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if os.path.exists(p)), None)
pytestmark = pytest.mark.skipif(EDGE is None, reason="requiere Microsoft Edge (clic real por CDP)")


def _puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _matar(proc):
    if os.name == "nt":  # terminate() no cierra a los hijos
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    else:
        proc.kill()


@pytest.fixture(scope="module")
def servidor():
    puerto = _puerto_libre()
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true",
                             "--server.port", str(puerto), "--browser.gatherUsageStats", "false"],
                            cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{puerto}"
    try:
        for _ in range(240):
            try:
                if urllib.request.urlopen(url + "/_stcore/health", timeout=2).read() == b"ok":
                    break
            except Exception:
                time.sleep(0.5)
        else:
            pytest.fail("Streamlit no arrancó")
        yield url
    finally:
        _matar(proc)


class Navegador:
    def __init__(self, ws):
        self.ws, self.n = ws, 0

    def cdp(self, metodo, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": metodo, "params": params}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.n:
                return r.get("result", {})

    def ev(self, expr):
        return self.cdp("Runtime.evaluate", expression=expr, returnByValue=True).get("result", {}).get("value")

    def abrir(self, url, ancho, esperar):
        self.cdp("Emulation.setDeviceMetricsOverride", width=ancho, height=900, deviceScaleFactor=1, mobile=ancho < 600)
        self.cdp("Page.navigate", url=url)
        for _ in range(480):  # la primera carga en frío tarda
            if self.ev(f"!!document.querySelector({json.dumps(esperar)})"):
                break
            time.sleep(0.5)
        else:
            pytest.fail(f"no apareció {esperar}")
        time.sleep(1.5)

    def clic(self, x, y):
        self.cdp("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
        self.cdp("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1, buttons=1)
        self.cdp("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", clickCount=1)


@pytest.fixture(scope="module")
def edge():
    perfil = tempfile.mkdtemp(prefix="edge_test_")
    puerto = _puerto_libre()
    proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                             f"--remote-debugging-port={puerto}", "--remote-allow-origins=*",
                             f"--user-data-dir={perfil}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    try:
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{puerto}/json"))
                ws = websocket.create_connection(
                    next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page"), timeout=120)
                break
            except Exception:
                time.sleep(0.5)
        assert ws, "no se pudo conectar con Edge"
        yield Navegador(ws)
    finally:
        if ws:
            ws.close()
        _matar(proc)
        time.sleep(1)
        shutil.rmtree(perfil, ignore_errors=True)


def _js_puntos(contenedor, caja, texto, escudo):
    return f"""(() => {{
      const c = document.querySelector({json.dumps(contenedor)}); if (!c) return null;
      c.scrollIntoView({{block: 'center'}});
      const R = e => {{ const b = e.getBoundingClientRect(); return {{x: b.left, y: b.top, w: b.width, h: b.height}}; }};
      const k = R(c.querySelector({json.dumps(caja)})), t = R(c.querySelector({json.dumps(texto)})), s = R(c.querySelector({json.dumps(escudo)})), m = 6;
      const centro = r => [Math.round(r.x + r.w / 2), Math.round(r.y + r.h / 2)];
      const a = c.querySelector('a').getBoundingClientRect();
      return {{
        puntos: {{ centro: centro(k), texto: centro(t), escudo: centro(s),
          sup_izq: [Math.round(k.x + m), Math.round(k.y + m)], sup_der: [Math.round(k.x + k.w - m), Math.round(k.y + m)],
          inf_izq: [Math.round(k.x + m), Math.round(k.y + k.h - m)], inf_der: [Math.round(k.x + k.w - m), Math.round(k.y + k.h - m)] }},
        caja: k, enlace: {{x: a.left, y: a.top, w: a.width, h: a.height}},
        user_select: getComputedStyle(c.querySelector({json.dumps(caja)})).userSelect + '|' + getComputedStyle(c).userSelect
      }};
    }})()"""


def _js_arriba(contenedor, x, y):
    """True si el elemento que queda arriba en (x, y) está dentro del enlace de ese contenedor."""
    return f"""(() => {{ const e = document.elementFromPoint({x}, {y}); const c = document.querySelector({json.dumps(contenedor)});
      const a = e && e.closest('a'); return !!(a && c.contains(a)) ; }})()"""


CASOS = [
    pytest.param("equipos", '[class*="st-key-tarjeta-america"]', ".lm-team", ".lm-team div[style*='font-weight']", id="rejilla"),
    pytest.param("ranking", '[class*="st-key-fila-america"]', ".lm-elo", ".lm-elo span[style*='font-weight']", id="ranking"),
]


@pytest.mark.parametrize("ancho", [390, 1280])
@pytest.mark.parametrize("pagina,contenedor,caja,texto", CASOS)
def test_clic_real_en_cualquier_punto_de_la_tarjeta_abre_el_equipo(servidor, edge, pagina, contenedor, caja, texto, ancho):
    edge.abrir(f"{servidor}/{pagina}", ancho, f"{contenedor} a")
    datos = edge.ev(_js_puntos(contenedor, caja, texto, ".lm-crest"))
    assert datos, f"no se encontró {contenedor}"
    time.sleep(0.6)
    # 1) el enlace transparente cubre toda la tarjeta (no 16 × 0 px)
    k, a = datos["caja"], datos["enlace"]
    assert a["x"] <= k["x"] + 1 and a["y"] <= k["y"] + 1, (a, k)
    assert a["x"] + a["w"] >= k["x"] + k["w"] - 1 and a["y"] + a["h"] >= k["y"] + k["h"] - 1, (a, k)
    # 2) en los 7 puntos, lo que queda arriba es el enlace
    for nombre, (x, y) in datos["puntos"].items():
        assert edge.ev(_js_arriba(contenedor, x, y)) is True, f"{nombre} {x},{y}: no queda el enlace arriba"
    # 3) el texto no se puede seleccionar
    assert datos["user_select"].split("|") == ["none", "none"], datos["user_select"]
    # 4) clic real en la esquina inferior derecha (la que fallaba): abre el equipo desde arriba y sin recargar
    x, y = datos["puntos"]["inf_der"]
    edge.ev("window.__marca = 1; getSelection().removeAllRanges();")
    edge.clic(x, y)
    for _ in range(100):
        if edge.ev("location.pathname") == "/equipo":
            break
        time.sleep(0.1)
    assert edge.ev("location.pathname") == "/equipo" and edge.ev("location.search") == "?equipo=america"
    assert edge.ev("window.__marca === 1"), "hubo recarga completa de la página"
    for _ in range(100):
        if edge.ev("!!document.querySelector('.lm-hero')"):
            break
        time.sleep(0.1)
    time.sleep(0.5)
    assert edge.ev("(document.querySelector('[data-testid=stMain]') || {}).scrollTop") == 0  # desde arriba
    assert edge.ev("getSelection().toString()") == ""  # no quedó texto seleccionado
