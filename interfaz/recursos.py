"""Cargas cacheadas. No importa src.entrenar (arrastra xgboost, que la app no instala)."""
import base64
from pathlib import Path

import joblib
import streamlit as st

from interfaz import componentes
from src.equipos import cargar_equipos

RAIZ = Path(__file__).resolve().parent.parent
RUTA_MODELO = RAIZ / "modelos" / "modelo.joblib"
RUTA_CSS = RAIZ / "estilos" / "custom.css"
DIR_ESCUDOS = RAIZ / "assets" / "escudos"
PX_MAX_CHICO = 48  # hasta aquí se usan los escudos de 96 px; arriba, los de 256 px


@st.cache_resource
def css():
    return RUTA_CSS.read_text(encoding="utf-8")


def inyectar_css():
    st.markdown(f"<style>{css()}</style>", unsafe_allow_html=True)


@st.cache_resource
def modelo():
    """Dict de modelo.joblib: modelo, cols, elo, hist, activos. Solo lectura."""
    return joblib.load(RUTA_MODELO)


@st.cache_resource
def equipos():
    """Ficha de los 25 equipos (datos/equipos.csv), indexada por nombre. Solo lectura."""
    return cargar_equipos()


@st.cache_data
def escudo_b64(archivo, lado):
    """PNG del escudo en base64, o None si el archivo no existe."""
    ruta = DIR_ESCUDOS / str(lado) / archivo
    if not archivo or not ruta.is_file():
        return None
    return base64.b64encode(ruta.read_bytes()).decode("ascii")


def escudo_html(equipo, px):
    """Escudo listo para incrustar: 96 px si se ve chico, 256 px si se ve grande."""
    fichas = equipos()
    archivo = fichas.loc[equipo, "escudo"] if equipo in fichas.index else None
    lado = 96 if px <= PX_MAX_CHICO else 256
    return componentes.escudo(escudo_b64(archivo, lado), px, halo=equipo in componentes.HALO)
