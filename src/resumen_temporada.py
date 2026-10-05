"""Cálculos de la página «Temporadas» a partir de datos/procesados/predicciones_oof.csv. Sin Streamlit ni xgboost.

El accuracy y el log loss se calculan igual que en src/evaluacion.py (y que la tabla del README):
  accuracy = promedio de (resultado más probable == resultado real);
  log loss = promedio de -log(probabilidad que el modelo dio al resultado real), con la probabilidad recortada a
             [1e-15, 1].
"""
import numpy as np

from src.formato import redondear_100

MODELOS = ("logistica", "mercado")
NOMBRE_MODELO = {"logistica": "Regresión logística", "mercado": "Momios (mercado)"}
FILTROS = ("Todos", "Aciertos", "Fallos")
BLOQUE = 20  # partidos que se muestran de a poco con «Ver más»
RESULTADOS = ("H", "D", "A")  # gana local, empate, gana visitante
COLUMNAS_PROB = {"logistica": {"H": "log_local", "D": "log_empate", "A": "log_visitante"},
                 "mercado": {"H": "mer_local", "D": "mer_empate", "A": "mer_visitante"}}
NOMBRE_RESULTADO = {"H": "local", "D": "empate", "A": "visitante"}


def temporadas(df):
    """Temporadas del CSV, de la más vieja a la más reciente."""
    return sorted(df["temporada"].unique())


def de_temporada(df, temporada):
    """Partidos de una temporada, en orden de fecha (y, a igual fecha, el orden del CSV)."""
    s = df[df["temporada"] == temporada]
    return s.sort_values("fecha", kind="stable")


def acierto(df, modelo="logistica"):
    """Serie booleana: el resultado más probable de ese modelo fue el que pasó."""
    return df[f"pred_{modelo}"] == df["resultado"]


def prob_real(df, modelo):
    """Probabilidad que el modelo dio al resultado que sí pasó, partido por partido."""
    cols = COLUMNAS_PROB[modelo]
    p = np.zeros(len(df))
    for r in RESULTADOS:
        p = np.where(df["resultado"].to_numpy() == r, df[cols[r]].to_numpy(), p)
    return p


def log_loss(df, modelo):
    """Log loss promedio (menor es mejor), con la misma fórmula que src/evaluacion.py."""
    return float(np.mean(-np.log(np.clip(prob_real(df, modelo), 1e-15, 1))))


def accuracy(df, modelo):
    return float(acierto(df, modelo).mean())


def resumen(df):
    """{modelo: {partidos, aciertos, accuracy, log_loss}} de los partidos de `df` (una temporada o todas)."""
    return {m: dict(partidos=len(df), aciertos=int(acierto(df, m).sum()), accuracy=accuracy(df, m),
                    log_loss=log_loss(df, m)) for m in MODELOS}


def filtrar(df, filtro):
    """«Todos», «Aciertos» o «Fallos» según la regresión logística. Otro valor es un error."""
    if filtro == "Todos":
        return df
    if filtro == "Aciertos":
        return df[acierto(df)]
    if filtro == "Fallos":
        return df[~acierto(df)]
    raise ValueError(f"filtro desconocido: {filtro!r}")


def bloque_visible(df, cuantos):
    """Los primeros `cuantos` partidos (la lista crece de a BLOQUE con «Ver más»)."""
    return df.iloc[:cuantos]


def porcentajes(fila):
    """Probabilidades de la logística como enteros que suman 100: {H, D, A}."""
    p = [fila["log_local"], fila["log_empate"], fila["log_visitante"]]
    return dict(zip(RESULTADOS, redondear_100(p)))
