"""Fase E: entradas hostiles (query params, momios, datos con HTML) y limpieza del repo.

Todo corre en local (AppTest o `git` sobre este repo): nada contra el servidor de producción.
"""
import csv
import math
import re
import subprocess
from html import escape
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from interfaz import recursos
from src import prediccion
from src.prediccion import MOMIO_MAX, MOMIO_MIN, mercado, validar_momios

RAIZ = Path(__file__).resolve().parent.parent
MARCA = "ZQXJ7"  # texto único: si aparece en la salida, la página reflejó la entrada

PAYLOADS = {
    "script": f"<script>alert('{MARCA}')</script>",
    "atributo": f"\"'><img src=x onerror=alert('{MARCA}')>",
    "svg": f"<svg/onload=alert('{MARCA}')>",
    "largo": MARCA + "a" * 10000,
    "traversal": f"../../etc/passwd{MARCA}",
    "traversal_codificado": f"..%2f..%2f{MARCA}",
    "unicode": f"‮﻿\U0001F4A9İK{MARCA}",
    "nulo": f"toluca\x00{MARCA}",
    "mayusculas": "TOLUCA",
    "espacios": " toluca ",
    "javascript": f"javascript:alert('{MARCA}')",
    "vacio": "",
}


def _html(at):
    """Todo lo que la página escribió como texto o HTML, sin el <style> global."""
    partes = [m.value for m in at.markdown if not m.value.startswith("<style>/*")]
    partes += [m.value for m in at.caption] + [m.value for m in at.get("alert")]
    return "".join(str(p) for p in partes)


def _pagina(ruta, **params):
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=90).run()
    for k, v in params.items():
        at.query_params[k] = v
    return at.switch_page(ruta).run()


def _es_rejilla(at):
    html = _html(at)
    return ("lm-hero" not in html and not at.selectbox
            and len(re.findall(r'class="lm-team( is-sel)?"', html)) == 25)


# ---------- 1. query params ----------

@pytest.mark.parametrize("ruta", ["paginas/equipos.py", "paginas/equipo.py"])
@pytest.mark.parametrize("clave", list(PAYLOADS))
def test_equipo_hostil_cae_a_la_rejilla_sin_reflejar(ruta, clave):
    valor = PAYLOADS[clave]
    at = _pagina(ruta, equipo=valor)
    assert not at.exception, [e.value for e in at.exception]
    assert _es_rejilla(at), clave  # los slugs son minúsculas exactas: «TOLUCA» o « toluca » tampoco abren
    html = _html(at)
    assert MARCA not in html and "<script" not in html and "onerror" not in html
    assert valor == "" or valor not in html
    assert "equipo" not in dict(at.query_params)  # la URL se limpia: el texto tampoco queda ahí


@pytest.mark.parametrize("ruta", ["paginas/equipos.py", "paginas/equipo.py"])
def test_parametros_repetidos(ruta):
    """Streamlit toma el último valor: solo un slug válido al final abre el equipo."""
    hostil = PAYLOADS["script"]
    at = _pagina(ruta, equipo=["toluca", hostil])
    assert not at.exception and _es_rejilla(at) and MARCA not in _html(at)
    at = _pagina(ruta, equipo=[hostil, "toluca"])
    assert not at.exception and "lm-hero" in _html(at) and MARCA not in _html(at)
    assert at.selectbox[0].value == "Toluca"


@pytest.mark.parametrize("ruta", ["paginas/equipos.py", "paginas/equipo.py", "paginas/ranking.py",
                                  "paginas/temporadas.py", "paginas/sobre_modelo.py", "paginas/predictor.py"])
def test_otros_parametros_no_se_reflejan(ruta):
    at = _pagina(ruta, **{"otro": PAYLOADS["script"], PAYLOADS["svg"]: "1", "temporada": PAYLOADS["atributo"],
                          "filtro": PAYLOADS["largo"]})
    assert not at.exception, [e.value for e in at.exception]
    assert MARCA not in _html(at) and "<script" not in _html(at)


# ---------- 2. momios ----------

MALOS = [0, -1, -2.5, 1.0, 1.0099, 1000.01, 1e308, 1e-320, 5e-324, math.inf, -math.inf, math.nan,
         "2.5", "texto", "", None, True, False, [2.0], 1 + 2j]


@pytest.mark.parametrize("malo", MALOS, ids=repr)
@pytest.mark.parametrize("posicion", [0, 1, 2])
def test_mercado_rechaza_momios_malos_con_mensaje_claro(malo, posicion):
    momios = [2.0, 3.3, 3.5]
    momios[posicion] = malo
    with pytest.raises(ValueError, match="momios"):
        mercado(*momios)


def test_mercado_nunca_divide_entre_cero():
    for malo in (0, math.inf, 5e-324):
        with pytest.raises(ValueError):
            mercado(malo, malo, malo)


def test_mercado_acepta_los_limites_y_conserva_sus_resultados():
    for m in (MOMIO_MIN, 2.0, MOMIO_MAX):
        probs, margen = mercado(m, m, m)
        assert sum(probs) == pytest.approx(1) and all(math.isfinite(p) for p in probs) and math.isfinite(margen)
    probs, margen = mercado(2.00, 3.30, 3.50)
    assert margen == pytest.approx(1 / 2 + 1 / 3.3 + 1 / 3.5 - 1)
    validar_momios(MOMIO_MIN, MOMIO_MAX)


def test_campos_de_momios_acotados_en_la_pagina():
    at = AppTest.from_file(str(RAIZ / "paginas" / "predictor.py"), default_timeout=90).run()
    assert [(n.min, n.max) for n in at.number_input] == [(MOMIO_MIN, MOMIO_MAX)] * 3
    for valor in (0, -5, math.inf, math.nan, 1e308, None):
        at.number_input[0].set_value(valor).run()
        assert not at.exception, valor
        assert MOMIO_MIN <= at.number_input[0].value <= MOMIO_MAX  # el campo no deja pasar nada fuera de rango


def test_pagina_avisa_si_los_momios_no_son_validos(monkeypatch):
    """Si llegara un valor que el campo no frena, la página muestra un aviso en vez de una excepción."""
    def falla(*_):
        raise ValueError("Los momios deben estar entre 1.01 y 1000.")
    monkeypatch.setattr(prediccion, "mercado", falla)
    at = AppTest.from_file(str(RAIZ / "paginas" / "predictor.py"), default_timeout=90).run()
    assert not at.exception
    assert [w.value for w in at.warning] == ["Los momios deben estar entre 1.01 y 1000."]
    assert "Margen de la casa" not in _html(at)


# ---------- 3. XSS: datos con HTML en todo lo que sale por unsafe_allow_html ----------

COLUMNAS_TEXTO = ["nombre", "siglas", "apodo", "ciudad_estado", "estadio", "fundacion", "palmares"]


def _atacar(col):
    return f'<script>alert("{MARCA}{col}")</script>'


@pytest.fixture
def datos_hostiles(tmp_path, monkeypatch):
    """equipos.csv (los 25 equipos) y rivalidades.csv con HTML en cada columna de texto."""
    eq = tmp_path / "equipos.csv"
    with open(RAIZ / "datos" / "equipos.csv", encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    campos = list(filas[0])
    for fila in filas:
        for col in COLUMNAS_TEXTO:
            fila[col] = _atacar(col)
    with open(eq, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, campos)
        w.writeheader()
        w.writerows(filas)
    rv = tmp_path / "rivalidades.csv"
    with open(RAIZ / "datos" / "rivalidades.csv", encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    for fila in filas:
        fila["nombre"] = _atacar("rivalidad")
    with open(rv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    monkeypatch.setattr(recursos, "RUTA_EQUIPOS", eq)
    monkeypatch.setattr(recursos, "RUTA_RIVALIDADES", rv)


@pytest.mark.parametrize("ruta,params", [
    ("paginas/predictor.py", {}),
    ("paginas/equipos.py", {}),
    ("paginas/equipo.py", {"equipo": "america"}),
    ("paginas/equipo.py", {"equipo": "san-luis"}),  # la ficha con nota de fundación
    ("paginas/ranking.py", {}),
    ("paginas/temporadas.py", {}),
    ("paginas/sobre_modelo.py", {}),
])
def test_datos_con_html_salen_escapados(datos_hostiles, ruta, params):
    at = _pagina(ruta, **params)
    assert not at.exception, [e.value for e in at.exception]
    html = _html(at)
    assert "<script" not in html and "onerror" not in html
    assert f'alert("{MARCA}' not in html  # las comillas también salen escapadas (&quot;)
    if ruta == "paginas/equipos.py":
        assert escape(_atacar("nombre")) in html  # el texto sigue ahí, pero inerte
    if ruta == "paginas/equipo.py":
        for col in ("nombre", "apodo", "ciudad_estado", "estadio", "palmares"):
            assert escape(_atacar(col)) in html, col


# ---------- 5. repo e historial ----------

def _git(*args):
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")
    return r.stdout if r.returncode == 0 else None


hay_git = pytest.mark.skipif(_git("rev-parse", "--git-dir") is None, reason="sin repositorio git")
PROHIBIDO = re.compile("|".join(["cl" + "aude", "anth" + "ropic", "co-?authored"]), re.I)
SECRETOS = re.compile("|".join([
    r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{20,}", r"sk-[A-Za-z0-9]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"(?i:(api[_-]?key|passw(or)?d|secret|token)\s*[:=]\s*['\"][^'\"\s]{8,}['\"])"]))
ARCHIVOS_SECRETOS = re.compile(r"(^|/)(\.env[^/]*|secrets\.toml|.*\.pem|.*\.key|.*\.p12|id_rsa.*|credentials.*)$", re.I)
TEXTO = {".py", ".md", ".toml", ".txt", ".csv", ".css", ".json", ".yml", ".yaml", ".ipynb"}


@hay_git
def test_sin_secretos_en_archivos_versionados_ni_en_nombres_del_historial():
    versionados = _git("ls-files").splitlines()
    assert not [f for f in versionados if ARCHIVOS_SECRETOS.search(f)]
    historial = set(_git("log", "--all", "--name-only", "--format=").splitlines())
    assert not [f for f in historial if f and ARCHIVOS_SECRETOS.search(f)]
    for f in versionados:
        ruta = RAIZ / f
        if ruta.suffix in TEXTO and ruta.is_file():
            assert not SECRETOS.search(ruta.read_text(encoding="utf-8", errors="ignore")), f


@hay_git
def test_secretos_no_aparecen_en_el_historial_completo():
    parches = _git("log", "--all", "-p", "--format=", "-G", SECRETOS.pattern) or ""
    lineas = [ln for ln in parches.splitlines() if ln[:1] in "+-" and SECRETOS.search(ln)]
    assert not lineas, lineas[:3]


@hay_git
def test_sin_menciones_de_herramientas_de_ia_en_archivos_ni_en_el_historial():
    assert not [f for f in _git("ls-files").splitlines() if PROHIBIDO.search(f)]
    r = subprocess.run(["git", "grep", "-n", "-i", "-I", "-E", PROHIBIDO.pattern, "--", ".",
                        ":!tests/test_seguridad.py"], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")
    assert r.stdout == "", r.stdout[:300]
    mensajes = _git("log", "--all", "--format=%an%n%ae%n%cn%n%ce%n%B") or ""
    assert not PROHIBIDO.search(mensajes)


@hay_git
def test_gitignore_cubre_lo_sensible():
    texto = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    for patron in (".env", ".venv", ".streamlit/secrets.toml"):
        assert re.search(rf"^{re.escape(patron)}\s*$", texto, re.M), patron


def test_los_detectores_de_secretos_y_menciones_funcionan():
    """Los detectores de arriba no sirven si no detectan: se prueban con ejemplos buenos y malos."""
    for malo in ("AKIA" + "ABCDEFGHIJKLMNOP", "ghp_" + "a" * 36, "sk-" + "b" * 30,
                 "-----BEGIN RSA PRIVATE KEY-----", 'API_KEY = "abcd1234efgh"', "password: 'hunter2hunter2'"):
        assert SECRETOS.search(malo), malo
    for bueno in ("asttokens==3.0.2", "--ink-muted: #a9a9c4", "token = 3", "password = ''", "AKIA corto"):
        assert not SECRETOS.search(bueno), bueno
    for malo in (".env", "datos/.env.local", ".streamlit/secrets.toml", "x/llave.pem", "a/b/id_rsa"):
        assert ARCHIVOS_SECRETOS.search(malo), malo
    for bueno in ("app.py", "datos/equipos.csv", "docs/environment.md"):
        assert not ARCHIVOS_SECRETOS.search(bueno), bueno
    for malo in ("Co-Authored-By: alguien", "co authored".replace(" ", "-"), "Cl" + "aude", "ANTH" + "ROPIC"):
        assert PROHIBIDO.search(malo), malo
    assert not PROHIBIDO.search("Luis Martínez <correo@ejemplo.com>")
