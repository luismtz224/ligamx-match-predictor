"""Exporta las predicciones fuera de muestra del walk-forward a datos/procesados/predicciones_oof.csv.

Es un script OFFLINE: usa `oof_walk_forward()` (src/evaluacion.py, que importa xgboost) para las probabilidades y
recalcula `feat` con `procesar()` solo para pegar fecha, equipos y goles de cada partido. La app no importa
xgboost: solo lee el CSV, que se versiona en git (Cloud solo ve lo que está en git).

Una fila por partido de prueba (8 temporadas, 2018/19 a 2025/26: 2,651 partidos; la 2026/27 está en curso y no
entra), en orden de temporada y fecha. Columnas:
  temporada, fecha (AAAA-MM-DD), local, visitante, goles_local, goles_visitante,
  resultado (H gana local, D empate, A gana visitante),
  log_local, log_empate, log_visitante    probabilidades de la regresión logística,
  mer_local, mer_empate, mer_visitante    probabilidades de los momios (sin margen),
  pred_logistica, pred_mercado            resultado más probable de cada una (H, D o A), calculado con las
                                          probabilidades SIN redondear (como el accuracy del README).

Uso: python -m src.exportar_predicciones
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.entrenar import RUTA_CSV
from src.evaluacion import oof_walk_forward
from src.features import cargar_partidos, procesar

RAIZ = Path(__file__).resolve().parent.parent
RUTA_SALIDA = RAIZ / "datos" / "procesados" / "predicciones_oof.csv"
COLUMNAS = ["temporada", "fecha", "local", "visitante", "goles_local", "goles_visitante", "resultado",
            "log_local", "log_empate", "log_visitante", "mer_local", "mer_empate", "mer_visitante",
            "pred_logistica", "pred_mercado"]
LETRA = np.array(["A", "D", "H"])  # columna de predict_proba -> resultado
DECIMALES = 6


def construir(folds, y, temp, probs, feat):
    """DataFrame con una fila por partido de prueba. `feat` = procesar(...) sobre el mismo CSV."""
    indice = np.concatenate([te for _, _, te in folds])
    test = feat.loc[indice]
    # los partidos de `feat` deben ser exactamente los que predijo el walk-forward, en el mismo orden
    if not (np.array_equal(test["y"].to_numpy(), y) and np.array_equal(test["Season"].to_numpy(), temp)):
        raise ValueError("los partidos de feat no coinciden con las predicciones del walk-forward")
    pl, pm = probs["logistica"], probs["mercado"]  # columnas [A, D, H]
    df = pd.DataFrame({
        "temporada": test["Season"].to_numpy(),
        "fecha": test["Date"].dt.strftime("%Y-%m-%d").to_numpy(),
        "local": test["Home"].to_numpy(), "visitante": test["Away"].to_numpy(),
        "goles_local": test["HG"].astype(int).to_numpy(), "goles_visitante": test["AG"].astype(int).to_numpy(),
        "resultado": test["Res"].to_numpy(),
        "log_local": pl[:, 2], "log_empate": pl[:, 1], "log_visitante": pl[:, 0],
        "mer_local": pm[:, 2], "mer_empate": pm[:, 1], "mer_visitante": pm[:, 0],
        "pred_logistica": LETRA[pl.argmax(axis=1)], "pred_mercado": LETRA[pm.argmax(axis=1)],
    }, columns=COLUMNAS)
    return df.round(DECIMALES)


def main(ruta=RUTA_SALIDA, oof=None):
    """Calcula y guarda el CSV. `oof` = salida de oof_walk_forward() si ya se calculó (las pruebas)."""
    folds, y, temp, _, probs = oof if oof is not None else oof_walk_forward()
    feat, _, _ = procesar(cargar_partidos(RUTA_CSV), K=20, ventaja=60, regresion=0.0)
    df = construir(folds, y, temp, probs, feat)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, lineterminator="\n")
    print(f"{len(df)} partidos de {df['temporada'].nunique()} temporadas escritos en {ruta}")
    por_temp = df.groupby("temporada").agg(
        partidos=("resultado", "size"),
        acc_logistica=("pred_logistica", lambda s: (s == df.loc[s.index, "resultado"]).mean()),
        acc_mercado=("pred_mercado", lambda s: (s == df.loc[s.index, "resultado"]).mean()))
    print(por_temp.round(4).to_string())
    return df


if __name__ == "__main__":
    main()
