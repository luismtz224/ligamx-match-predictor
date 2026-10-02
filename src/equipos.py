"""Ficha de equipos y rivalidades. `python -m src.equipos` regenera datos/equipos.csv."""
import csv
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RUTA_FUENTE = RAIZ / "datos" / "datos_fuente.txt"
RUTA_EQUIPOS = RAIZ / "datos" / "equipos.csv"
RUTA_RIVALIDADES = RAIZ / "datos" / "rivalidades.csv"
DIR_ESCUDOS = RAIZ / "assets" / "escudos"

COLUMNAS = ["equipo", "nombre", "siglas", "apodo", "ciudad_estado", "estadio", "fundacion",
            "color1", "color2", "color3", "palmares", "escudo"]

# etiqueta en la fuente -> columna del CSV
CAMPOS = {"Siglas": "siglas", "Apodo": "apodo", "Ciudad y estado": "ciudad_estado",
          "Estadio": "estadio", "Fundación": "fundacion", "Palmarés": "palmares"}

# Nombre para mostrar cuando difiere de la llave (el nombre de MEX.csv). El resto, igual.
NOMBRES_MOSTRADOS = {
    "Guadalajara Chivas": "CD Guadalajara", "Atl. San Luis": "Atlético de San Luis",
    "UNAM Pumas": "Pumas UNAM", "Club America": "Club América", "Club Leon": "Club León",
    "Queretaro": "Querétaro", "Juarez": "Juárez", "Mazatlan FC": "Mazatlán FC",
}

# chi.png es Chivas y jag.png es Chiapas: no coinciden con las siglas
ESCUDOS = {
    "Atl. San Luis": "adsl.png", "Club America": "ame.png", "Atlante": "atl.png",
    "Atlas": "ats.png", "Juarez": "bra.png", "Lobos BUAP": "buap.png",
    "Cruz Azul": "caz.png", "Guadalajara Chivas": "chi.png", "Dorados de Sinaloa": "dor.png",
    "Chiapas": "jag.png", "Club Leon": "leo.png", "Mazatlan FC": "maz.png",
    "Monarcas": "mor.png", "Monterrey": "mty.png", "Necaxa": "nec.png", "Pachuca": "pac.png",
    "Puebla": "pue.png", "Queretaro": "qro.png", "Santos Laguna": "san.png",
    "Club Tijuana": "tij.png", "Toluca": "tol.png", "Tigres UANL": "uanl.png",
    "Leones Negros": "udg.png", "UNAM Pumas": "unam.png", "Veracruz": "ver.png",
}


def parsear_fuente(texto):
    """Convierte la ficha en texto (bloques que empiezan con '•') en una lista de dicts.

    Solo estructura: los valores se dejan tal cual vienen después de 'Etiqueta: '.
    """
    filas, actual = [], None
    for linea in texto.splitlines():
        if linea.startswith("•"):
            actual = {c: "" for c in COLUMNAS}
            actual["equipo"] = linea[1:].strip()
            actual["nombre"] = NOMBRES_MOSTRADOS.get(actual["equipo"], actual["equipo"])
            actual["escudo"] = ESCUDOS[actual["equipo"]]
            filas.append(actual)
        elif linea.strip():
            etiqueta, valor = linea.split(": ", 1)
            if etiqueta == "Colores principales":
                for i, color in enumerate(valor.split(", "), start=1):
                    actual[f"color{i}"] = color
            else:
                actual[CAMPOS[etiqueta]] = valor
    return filas


def convertir_fuente(ruta_fuente=RUTA_FUENTE, ruta_csv=RUTA_EQUIPOS):
    filas = parsear_fuente(Path(ruta_fuente).read_text(encoding="utf-8"))
    with open(ruta_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    return filas


def cargar_equipos(ruta=RUTA_EQUIPOS):
    """Ficha indexada por equipo. Los campos vacíos quedan como cadena vacía."""
    return pd.read_csv(ruta, dtype=str, keep_default_na=False).set_index("equipo")


def nombre_mostrado(equipo, fichas=None):
    """Nombre para mostrar en la UI. La llave sigue siendo el nombre de MEX.csv.
    Si el equipo no está en las fichas, devuelve la llave tal cual."""
    fichas = cargar_equipos() if fichas is None else fichas
    return fichas.loc[equipo, "nombre"] if equipo in fichas.index else equipo


def _clave_orden(texto):
    """Ordena sin acentos ni mayúsculas ('Querétaro' junto a 'Puebla', no al final)."""
    sin_acentos = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c)).casefold()


def ordenar_por_nombre(equipos, fichas=None):
    """Llaves ordenadas alfabéticamente por su nombre mostrado."""
    fichas = cargar_equipos() if fichas is None else fichas
    return sorted(equipos, key=lambda e: _clave_orden(nombre_mostrado(e, fichas)))


def cargar_rivalidades(ruta=RUTA_RIVALIDADES):
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


def rivalidades_de(equipo, rivalidades):
    """Lista de (rival, nombre) donde aparece el equipo, de cualquier lado del par."""
    out = []
    for r in rivalidades.itertuples():
        if r.equipo_a == equipo:
            out.append((r.equipo_b, r.nombre))
        elif r.equipo_b == equipo:
            out.append((r.equipo_a, r.nombre))
    return out


def main():
    filas = convertir_fuente()
    print(f"{len(filas)} equipos escritos en {RUTA_EQUIPOS}")


if __name__ == "__main__":
    main()
