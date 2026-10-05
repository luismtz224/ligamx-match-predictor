"""Fase 0 de Extras: las cachés que leen archivos se invalidan cuando el archivo cambia.

En Cloud un `git push` recarga el código de las páginas pero no vacía `st.cache_resource`/`st.cache_data`:
se veía HTML nuevo con CSS viejo. Cada carga cacheada recibe la huella (hash del contenido, `src.huella`)
como argumento. Cambiar el archivo debe cambiar lo que devuelve la función y lo que se inyecta en la página.
"""
import ast
import shutil
from pathlib import Path

import joblib
import pytest
from streamlit.testing.v1 import AppTest

from interfaz import recursos
from src import imagen
from src.huella import huella

RAIZ = Path(__file__).resolve().parent.parent
CSS_REAL = (RAIZ / "estilos" / "custom.css").read_text(encoding="utf-8")


# ---------- huella ----------
def test_huella_depende_del_contenido_del_nombre_y_de_la_ausencia(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("uno")
    h1 = huella(a)
    assert huella(a) == h1 and len(h1) == 16  # estable
    a.write_text("dos")  # mismo tamaño, otro contenido
    assert huella(a) != h1
    b = tmp_path / "b.txt"
    b.write_text("dos")
    assert huella(b) != huella(a)  # mismo contenido, otro nombre
    falta = tmp_path / "falta.txt"
    ausente = huella(falta)
    assert ausente == huella(falta) != huella(a)
    falta.write_text("ya existe")
    assert huella(falta) != ausente  # cambia cuando el archivo aparece
    assert huella(a, b) != huella(b, a)  # el orden cuenta
    assert huella(a) != huella(a, b)


# ---------- cada carga cacheada ----------
def test_css_se_vuelve_a_leer_si_el_archivo_cambia(tmp_path, monkeypatch):
    ruta = tmp_path / "custom.css"
    ruta.write_text("a{color:red}")
    monkeypatch.setattr(recursos, "RUTA_CSS", ruta)
    assert recursos.css() == "a{color:red}"
    ruta.write_text("a{color:blue}")  # mismo tamaño: lo que cambia es el contenido
    assert recursos.css() == "a{color:blue}"
    ruta.write_text("a{color:red}")
    assert recursos.css() == "a{color:red}"  # volver al contenido anterior también se nota


def test_colores_css_siguen_al_archivo(tmp_path, monkeypatch):
    ruta = tmp_path / "custom.css"
    ruta.write_text(":root { --team-x: #112233; }")
    monkeypatch.setattr(recursos, "RUTA_CSS", ruta)
    assert recursos.colores_css() == {"team-x": "#112233"}
    ruta.write_text(":root { --team-x: #445566; --team-y: #AABBCC; }")
    assert recursos.colores_css() == {"team-x": "#445566", "team-y": "#aabbcc"}


def test_modelo_se_vuelve_a_cargar_si_el_archivo_cambia(tmp_path, monkeypatch):
    ruta = tmp_path / "modelo.joblib"
    joblib.dump({"v": 1}, ruta)
    monkeypatch.setattr(recursos, "RUTA_MODELO", ruta)
    assert recursos.modelo() == {"v": 1}
    joblib.dump({"v": 2}, ruta)
    assert recursos.modelo() == {"v": 2}


def test_partidos_se_vuelven_a_procesar_si_el_csv_cambia(tmp_path, monkeypatch):
    lineas = (RAIZ / "datos" / "crudos" / "MEX.csv").read_text(encoding="utf-8").splitlines(True)
    ruta = tmp_path / "MEX.csv"
    monkeypatch.setattr(recursos, "RUTA_CSV", ruta)
    ruta.write_text("".join(lineas[:301]), encoding="utf-8")
    n1 = len(recursos.partidos()[0])
    ruta.write_text("".join(lineas[:401]), encoding="utf-8")
    n2 = len(recursos.partidos()[0])
    assert n2 > n1


def test_equipos_y_rivalidades_siguen_a_sus_csv(tmp_path, monkeypatch):
    eq = tmp_path / "equipos.csv"
    shutil.copy(RAIZ / "datos" / "equipos.csv", eq)
    monkeypatch.setattr(recursos, "RUTA_EQUIPOS", eq)
    assert recursos.equipos().loc["Club America", "nombre"] == "Club América"
    eq.write_text(eq.read_text(encoding="utf-8").replace("Club América", "Club X"), encoding="utf-8")
    assert recursos.equipos().loc["Club America", "nombre"] == "Club X"

    rv = tmp_path / "rivalidades.csv"
    shutil.copy(RAIZ / "datos" / "rivalidades.csv", rv)
    monkeypatch.setattr(recursos, "RUTA_RIVALIDADES", rv)
    n = len(recursos.rivalidades())
    rv.write_text("".join(rv.read_text(encoding="utf-8").splitlines(True)[:-1]), encoding="utf-8")
    assert len(recursos.rivalidades()) == n - 1


def test_escudos_se_vuelven_a_leer_si_el_png_cambia(tmp_path, monkeypatch):
    (tmp_path / "96").mkdir()
    monkeypatch.setattr(recursos, "DIR_ESCUDOS", tmp_path)
    assert recursos.escudo_b64("ame.png", 96) is None and recursos.escudo_b64(None, 96) is None
    (tmp_path / "96" / "ame.png").write_bytes(b"AAA")
    assert recursos.escudo_b64("ame.png", 96) == "QUFB"  # base64 de AAA: el archivo aparece
    (tmp_path / "96" / "ame.png").write_bytes(b"BBB")
    assert recursos.escudo_b64("ame.png", 96) == "QkJC"  # y cambia


def test_la_fuente_del_png_depende_del_archivo(tmp_path, monkeypatch):
    imagen._fuente(40, 400)  # calienta la caché con la fuente real
    monkeypatch.setattr(imagen, "RUTA_FUENTE", tmp_path / "no_existe.woff2")
    with pytest.raises(OSError):  # sin huella, la caché devolvería la fuente vieja
        imagen._fuente(40, 400)


# ---------- de punta a punta: lo que se inyecta y la imagen descargable ----------
def _css_inyectado(at):
    return next(m.value for m in at.markdown if m.value.startswith("<style>") and "MARCA-" in m.value)


def test_app_inyecta_el_css_nuevo_sin_reiniciar_nada(tmp_path, monkeypatch):
    ruta = tmp_path / "custom.css"
    ruta.write_text("/* MARCA-1 */\n" + CSS_REAL, encoding="utf-8")  # el CSS real: el Predictor lee sus colores
    monkeypatch.setattr(recursos, "RUTA_CSS", ruta)
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=120).run()
    assert not at.exception and "MARCA-1" in _css_inyectado(at)
    ruta.write_text("/* MARCA-2 */\n" + CSS_REAL, encoding="utf-8")  # «push»: el archivo cambia, el proceso sigue vivo
    at.run()
    html = _css_inyectado(at)
    assert not at.exception and "MARCA-2" in html and "MARCA-1" not in html


def _url_png():
    at = AppTest.from_file(str(RAIZ / "paginas" / "predictor.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    return at.get("download_button")[0].proto.url  # /mock/media/<hash del contenido>.png


def test_imagen_descargable_cambia_si_cambia_el_modelo(tmp_path, monkeypatch):
    original = _url_png()
    est = joblib.load(RAIZ / "modelos" / "modelo.joblib")
    est["elo"] = dict(est["elo"])
    est["elo"]["Club America"] += 300  # otro modelo: otras probabilidades en la imagen
    ruta = tmp_path / "modelo.joblib"
    joblib.dump(est, ruta)
    monkeypatch.setattr(recursos, "RUTA_MODELO", ruta)
    assert _url_png() != original
    monkeypatch.setattr(recursos, "RUTA_MODELO", RAIZ / "modelos" / "modelo.joblib")
    assert _url_png() == original  # con el modelo original vuelve la misma imagen


def test_huella_png_incluye_todo_lo_que_la_determina(tmp_path, monkeypatch):
    base = recursos.huella_png("Club America", "Cruz Azul")
    assert base == recursos.huella_png("Club America", "Cruz Azul")
    assert base != recursos.huella_png("Cruz Azul", "Club America")  # escudos en otro orden
    for nombre in ("RUTA_MODELO", "RUTA_CSV", "RUTA_CSS", "RUTA_EQUIPOS", "RUTA_FUENTE"):
        real = getattr(recursos, nombre)
        otro = tmp_path / real.name  # copia del archivo real con un salto de línea de más
        otro.write_bytes(real.read_bytes() + b"\n")
        monkeypatch.setattr(recursos, nombre, otro)
        assert recursos.huella_png("Club America", "Cruz Azul") != base, nombre
        monkeypatch.undo()
    assert recursos.huella_png("Club America", "Cruz Azul") == base


# ---------- guarda: toda función cacheada nueva debe llevar su huella ----------
def test_toda_funcion_cacheada_recibe_una_huella_como_argumento():
    """Una función con @st.cache_* en recursos.py o en las páginas debe tener el parámetro `contenido` o
    `recursos` (la huella). Sin él, el siguiente push dejaría el contenido viejo en la caché."""
    archivos = [RAIZ / "interfaz" / "recursos.py", *sorted((RAIZ / "paginas").glob("*.py"))]
    vistas = []
    for ruta in archivos:
        for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.FunctionDef):
                decoradores = [ast.unparse(d) for d in nodo.decorator_list]
                if any(d.startswith("st.cache_resource") or d.startswith("st.cache_data") for d in decoradores):
                    vistas.append(nodo.name)
                    parametros = [a.arg for a in nodo.args.args]
                    assert {"contenido", "recursos"} & set(parametros), f"{ruta.name}:{nodo.name} {parametros}"
    assert {"_css", "_modelo", "_partidos", "_colores_css", "_equipos", "_rivalidades", "_escudo_b64", "_png"} <= set(vistas)
