import re

import pandas as pd
from PIL import Image

from src.equipos import (COLUMNAS, DIR_ESCUDOS, NOMBRES_MOSTRADOS, RUTA_FUENTE, cargar_equipos,
                         cargar_rivalidades, nombre_mostrado, ordenar_por_nombre,
                         parsear_fuente, rivalidades_de)
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


def test_escudos_existen_en_todos_los_tamanos():
    assert LADOS == (96, 256, 512)
    for archivo in cargar_equipos()["escudo"]:
        for lado in LADOS:
            ruta = DIR_ESCUDOS / str(lado) / archivo
            assert ruta.exists(), ruta
            with Image.open(ruta) as img:
                assert img.size == (lado, lado) and img.mode == "RGBA", ruta
                assert img.getchannel("A").getextrema()[0] == 0, f"sin transparencia: {ruta}"


def test_csv_fiel_a_la_fuente():
    """El CSV es la fuente estructurada sin cambiar ningún valor. `nombre` no viene de la
    fuente (lo agrega NOMBRES_MOSTRADOS), así que se compara aparte."""
    texto = RUTA_FUENTE.read_text(encoding="utf-8")
    eq = cargar_equipos().reset_index()
    assert eq.to_dict("records") == parsear_fuente(texto)
    sin_nombre = lambda filas: [{k: v for k, v in f.items() if k != "nombre"} for f in filas]
    assert sin_nombre(eq.to_dict("records")) == sin_nombre(parsear_fuente(texto))
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


def test_nombre_mostrado():
    eq = cargar_equipos()
    esperado = {
        "Guadalajara Chivas": "CD Guadalajara", "Atl. San Luis": "Atlético de San Luis",
        "UNAM Pumas": "Pumas UNAM", "Club America": "Club América", "Club Leon": "Club León",
        "Queretaro": "Querétaro", "Juarez": "Juárez", "Mazatlan FC": "Mazatlán FC"}
    assert NOMBRES_MOSTRADOS == esperado
    for equipo in eq.index:  # el resto, igual que la llave
        assert eq.loc[equipo, "nombre"] == esperado.get(equipo, equipo), equipo
        assert nombre_mostrado(equipo, eq) == eq.loc[equipo, "nombre"]
        assert nombre_mostrado(equipo) == eq.loc[equipo, "nombre"]
    assert nombre_mostrado("Equipo Desconocido", eq) == "Equipo Desconocido"
    assert not (eq["nombre"] == "").any()


def test_ordenar_por_nombre_ignora_acentos():
    eq = cargar_equipos()
    orden = ordenar_por_nombre(eq.index, eq)
    assert sorted(orden) == sorted(eq.index) and len(orden) == 25
    nombres = [eq.loc[e, "nombre"] for e in orden]
    # 'Querétaro' va entre Puebla y Santos Laguna, no al final por la tilde
    assert nombres.index("Puebla") < nombres.index("Querétaro") < nombres.index("Santos Laguna")
    assert nombres[0] == "Atlante" and nombres[-1] == "Veracruz"
    assert nombres.index("Pachuca") < nombres.index("Puebla") < nombres.index("Pumas UNAM")


def test_orden_el_acento_no_cambia_la_posicion():
    """Con datos reales la primera letra ya decide; aquí el acento sí importaría."""
    fichas = pd.DataFrame({"nombre": ["Ab", "Áa", "aC", "Zeta"]},
                          index=["k1", "k2", "k3", "k4"])
    assert ordenar_por_nombre(fichas.index, fichas) == ["k2", "k1", "k3", "k4"]  # Áa, Ab, aC, Zeta
    assert ordenar_por_nombre(["k4", "k1"], fichas) == ["k1", "k4"]
