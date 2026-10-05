"""Cargas cacheadas. No importa src.entrenar (arrastra xgboost, que la app no instala).

Todo lo que se cachea y se lee de un archivo recibe la huella (hash del contenido, `src.huella`) como
argumento: en Cloud un push recarga el código pero no vacía las cachés, y sin esto el HTML nuevo se
mostraba con el CSS (o el modelo, o los CSV) viejos. Una función nueva que lea un archivo debe hacer lo mismo."""
import base64
import re
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from interfaz import componentes
from src.equipos import (RUTA_EQUIPOS, RUTA_RIVALIDADES, cargar_equipos, cargar_rivalidades,
                         nombre_mostrado, ordenar_por_nombre)
from src.features import cargar_partidos, procesar
from src.formato import color_distinto
from src.huella import huella
from src.imagen import RUTA_FUENTE

RAIZ = Path(__file__).resolve().parent.parent
RUTA_MODELO = RAIZ / "modelos" / "modelo.joblib"
RUTA_CSV = RAIZ / "datos" / "crudos" / "MEX.csv"
RUTA_CSS = RAIZ / "estilos" / "custom.css"
RUTA_CALIBRACION = RAIZ / "datos" / "procesados" / "calibracion.csv"
RUTA_PREDICCIONES = RAIZ / "datos" / "procesados" / "predicciones_oof.csv"
DIR_ESCUDOS = RAIZ / "assets" / "escudos"
PX_MAX_CHICO = 48  # hasta aquí se usan los escudos de 96 px; arriba, los de 256 px


@st.cache_resource
def _css(contenido):
    return RUTA_CSS.read_text(encoding="utf-8")


def css():
    """Texto de estilos/custom.css; se vuelve a leer si el archivo cambia."""
    return _css(huella(RUTA_CSS))


def inyectar_css():
    st.markdown(f"<style>{css()}</style>", unsafe_allow_html=True)


@st.cache_resource
def _modelo(contenido):
    return joblib.load(RUTA_MODELO)


def modelo():
    """Dict de modelo.joblib: modelo, cols, elo, hist, activos. Solo lectura."""
    return _modelo(huella(RUTA_MODELO))


@st.cache_resource
def _partidos(contenido):
    return procesar(cargar_partidos(RUTA_CSV), K=20, ventaja=60, regresion=0.0)


def partidos():
    """(feat, elo, hist) de procesar() sobre MEX.csv, con los hiperparámetros del modelo.
    Para forma e historial. Solo lectura."""
    return _partidos(huella(RUTA_CSV))


@st.cache_resource
def _calibracion(contenido):
    return pd.read_csv(RUTA_CALIBRACION)


def calibracion():
    """Datos de la gráfica de calibración (datos/procesados/calibracion.csv, que genera
    `python -m src.exportar_calibracion`), o None si el archivo no está. Solo lectura."""
    if not RUTA_CALIBRACION.is_file():
        return None
    return _calibracion(huella(RUTA_CALIBRACION))


@st.cache_resource
def _predicciones(contenido):
    return pd.read_csv(RUTA_PREDICCIONES, parse_dates=["fecha"])


def predicciones():
    """Predicciones fuera de muestra de la logística y los momios (datos/procesados/predicciones_oof.csv, que genera
    `python -m src.exportar_predicciones`), o None si el archivo no está. Solo lectura."""
    if not RUTA_PREDICCIONES.is_file():
        return None
    return _predicciones(huella(RUTA_PREDICCIONES))


@st.cache_resource
def _colores_css(contenido):
    return {k: v.lower() for k, v in re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", css())}


def colores_css():
    """{nombre de variable: hex} de las variables de color de estilos/custom.css."""
    return _colores_css(huella(RUTA_CSS))


def colores_partido(local, visita):
    """Colores de la barra: (css local, css visitante, hex local, hex visitante).

    El local usa --team-<slug>. El visitante, el primero que se distinga del local y del
    empate (delta E >= 30): su color, su -2 o --ink.
    """
    v = colores_css()
    sl, sv = componentes.SLUG[local], componentes.SLUG[visita]
    opciones = [(f"team-{sv}", v.get(f"team-{sv}")), (f"team-{sv}-2", v.get(f"team-{sv}-2")),
                ("ink", v["ink"])]
    clave = color_distinto(v[f"team-{sl}"], v["draw"], opciones)
    return f"var(--team-{sl})", f"var(--{clave})", v[f"team-{sl}"], v[clave]


@st.cache_resource
def _equipos(contenido):
    return cargar_equipos(RUTA_EQUIPOS)


def equipos():
    """Ficha de los 25 equipos (datos/equipos.csv), indexada por nombre. Solo lectura."""
    return _equipos(huella(RUTA_EQUIPOS))


@st.cache_resource
def _rivalidades(contenido):
    return cargar_rivalidades(RUTA_RIVALIDADES)


def rivalidades():
    """Clásicos (datos/rivalidades.csv). Solo lectura."""
    return _rivalidades(huella(RUTA_RIVALIDADES))


_DE_SLUG = {v: k for k, v in componentes.SLUG.items()}


def equipo_de_slug(slug):
    """Llave del equipo (nombre de MEX.csv) para un slug de la URL; None si no existe."""
    return _DE_SLUG.get(slug) if isinstance(slug, str) else None


@st.cache_data
def _escudo_b64(archivo, lado, contenido):
    return base64.b64encode((DIR_ESCUDOS / str(lado) / archivo).read_bytes()).decode("ascii")


def escudo_b64(archivo, lado):
    """PNG del escudo en base64, o None si el archivo no existe. Se vuelve a leer si el archivo cambia."""
    ruta = DIR_ESCUDOS / str(lado) / archivo if archivo else None
    if ruta is None or not ruta.is_file():
        return None
    return _escudo_b64(archivo, lado, huella(ruta))


def huella_png(local, visita):
    """Huella de todo lo que determina la imagen descargable de un partido: modelo, partidos, CSS (colores),
    fichas de equipos, los dos escudos grandes y la fuente. Llave de `_png` en paginas/predictor.py."""
    return huella(RUTA_MODELO, RUTA_CSV, RUTA_CSS, RUTA_EQUIPOS, ruta_escudo(local), ruta_escudo(visita),
                  RUTA_FUENTE)


def ruta_escudo(equipo, lado=512):
    """Ruta del PNG del escudo (para la imagen descargable)."""
    return DIR_ESCUDOS / str(lado) / equipos().loc[equipo, "escudo"]


def nombre(equipo):
    """Nombre para mostrar de un equipo (la llave es el nombre de MEX.csv)."""
    return nombre_mostrado(equipo, equipos())


def ordenados(lista):
    """Llaves ordenadas por nombre mostrado."""
    return ordenar_por_nombre(lista, equipos())


def escudo_html(equipo, px, solo=False):
    """Escudo listo para incrustar: 96 px si se ve chico, 256 px si se ve grande.
    alt con el nombre solo si el escudo va solo (`solo=True`); con el nombre al lado, alt=""."""
    fichas = equipos()
    archivo = fichas.loc[equipo, "escudo"] if equipo in fichas.index else None
    lado = 96 if px <= PX_MAX_CHICO else 256
    return componentes.escudo(escudo_b64(archivo, lado), px, halo=equipo in componentes.HALO,
                              alt=nombre(equipo) if solo else "")
