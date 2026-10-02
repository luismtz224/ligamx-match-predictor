import re

from PIL import Image

from src.equipos import (COLUMNAS, DIR_ESCUDOS, RUTA_FUENTE, cargar_equipos,
                         cargar_rivalidades, parsear_fuente, rivalidades_de)
from src.entrenar import RUTA_CSV
from src.escudos import LADOS, cuadrado
from src.features import cargar_partidos

HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def _equipos_mex():
    d = cargar_partidos(RUTA_CSV)
    return set(d["Home"]) | set(d["Away"])


def test_equipos_iguales_a_mex():
    eq = cargar_equipos()
    assert list(eq.reset_index().columns) == COLUMNAS
    assert eq.index.is_unique
    assert set(eq.index) == _equipos_mex()
    assert len(eq) == 25


def test_colores_hex_validos():
    eq = cargar_equipos()
    for equipo, f in eq.iterrows():
        assert HEX.fullmatch(f["color1"]) and HEX.fullmatch(f["color2"]), equipo
        assert f["color3"] == "" or HEX.fullmatch(f["color3"]), equipo


def test_escudos_existen_en_ambos_tamanos():
    for archivo in cargar_equipos()["escudo"]:
        for lado in LADOS:
            ruta = DIR_ESCUDOS / str(lado) / archivo
            assert ruta.exists(), ruta
            with Image.open(ruta) as img:
                assert img.size == (lado, lado) and img.mode == "RGBA"


def test_csv_fiel_a_la_fuente():
    """El CSV es la fuente estructurada sin cambiar ningún valor."""
    texto = RUTA_FUENTE.read_text(encoding="utf-8")
    eq = cargar_equipos().reset_index()
    assert eq.to_dict("records") == parsear_fuente(texto)
    lineas = set(texto.splitlines())
    for f in eq.to_dict("records"):
        assert f"Siglas: {f['siglas']}" in lineas
        assert f"Palmarés: {f['palmares']}" in lineas
        colores = ", ".join(c for c in (f["color1"], f["color2"], f["color3"]) if c)
        assert f"Colores principales: {colores}" in lineas
        if f["apodo"]:
            assert f"Apodo: {f['apodo']}" in lineas
    sin_apodo = set(eq.loc[eq["apodo"] == "", "equipo"])
    assert sin_apodo == {"Leones Negros", "Lobos BUAP"}


def test_rivalidades_simetricas_y_validas():
    riv = cargar_rivalidades()
    equipos = _equipos_mex()
    assert set(riv["equipo_a"]) | set(riv["equipo_b"]) <= equipos
    assert len(riv) == 11
    for r in riv.itertuples():
        assert (r.equipo_b, r.nombre) in rivalidades_de(r.equipo_a, riv)
        assert (r.equipo_a, r.nombre) in rivalidades_de(r.equipo_b, riv)
    assert {n for _, n in rivalidades_de("Club America", riv)} == {
        "Clásico Nacional", "Clásico Joven", "Clásico Capitalino"}


def test_cuadrado_conserva_transparencia_y_proporcion():
    img = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    img.paste((255, 0, 0, 255), (50, 20, 250, 80))  # rectángulo 200x60 con margen transparente
    out = cuadrado(img, 256)
    assert out.size == (256, 256) and out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0
    x0, y0, x1, y1 = out.getchannel("A").getbbox()
    assert x1 - x0 == 256  # se recortó el margen y ocupa todo el ancho
    assert abs((y1 - y0) - 256 * 60 / 200) <= 2
