"""Exporta los datos de la gráfica de calibración de «Sobre el modelo» a datos/procesados/calibracion.csv.

Es un script OFFLINE: usa las predicciones fuera de muestra del walk-forward (src/evaluacion.py, que importa
xgboost) y las funciones de src/calibracion.py (que importa matplotlib), sin duplicar su lógica. La app no
importa ninguno de los dos: solo lee el CSV, que se versiona en git (Cloud solo ve lo que está en git).

Una fila por (fuente, resultado, grupo): 2 fuentes (logistica, mercado) x 2 resultados (local, visitante) x
N_BINS grupos de igual cantidad de partidos. Columnas:
  n, pred, freq, wilson_lo, wilson_hi  del grupo (tabla_bins);
  ece, ece_lo, ece_hi                    de la serie (ECE con IC 95% por bootstrap de semanas);
  ece_esperado, esperado_lo, esperado_hi ECE que daría un modelo perfecto solo por ruido (simulado);
  sobre_ruido                            True si el ECE observado supera el p97.5 del ruido;
  n_total                                partidos de la serie.

Uso: python -m src.exportar_calibracion
"""
from pathlib import Path

import pandas as pd

from src.calibracion import FUENTES, N_BINS, bootstrap_ece, ece, ece_esperado, tabla_bins
from src.evaluacion import oof_walk_forward

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CSV = RAIZ / "datos" / "procesados" / "calibracion.csv"
RESULTADOS = [("local", 2), ("visitante", 0)]  # nombre, columna de predict_proba [A, D, H]
COLUMNAS = ["fuente", "resultado", "grupo", "n", "pred", "freq", "wilson_lo", "wilson_hi",
            "ece", "ece_lo", "ece_hi", "ece_esperado", "esperado_lo", "esperado_hi", "sobre_ruido", "n_total"]
DECIMALES = 6


def construir(probs, y, semana):
    """DataFrame con los datos de la gráfica a partir de las predicciones fuera de muestra."""
    esperado = {f: ece_esperado(probs[f]) for f in FUENTES}  # por fuente: {columna: (media, p2.5, p97.5)}
    filas = []
    for fuente in FUENTES:
        for nombre, k in RESULTADOS:
            p, o = probs[fuente][:, k], (y == k).astype(float)
            e = float(ece(p, o))
            e_lo, e_hi = bootstrap_ece(p, o, semana)
            esp, esp_lo, esp_hi = esperado[fuente][k]
            tabla = tabla_bins(p, o, N_BINS)
            for grupo, t in enumerate(tabla.itertuples(), start=1):
                filas.append(dict(fuente=fuente, resultado=nombre, grupo=grupo, n=int(t.n), pred=t.pred, freq=t.freq,
                                  wilson_lo=t.wilson_lo, wilson_hi=t.wilson_hi, ece=e, ece_lo=e_lo, ece_hi=e_hi,
                                  ece_esperado=esp, esperado_lo=esp_lo, esperado_hi=esp_hi,
                                  sobre_ruido=bool(e > esp_hi), n_total=len(y)))
    return pd.DataFrame(filas, columns=COLUMNAS).round(DECIMALES)


def main(ruta=RUTA_CSV, oof=None):
    """Calcula y guarda el CSV. `oof` = salida de oof_walk_forward() si ya se calculó (las pruebas)."""
    _, y, _, semana, probs = oof if oof is not None else oof_walk_forward()
    df = construir(probs, y, semana)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, lineterminator="\n")
    print(f"{len(df)} filas ({len(y)} partidos fuera de muestra, {N_BINS} grupos por serie) escritas en {ruta}")
    resumen = df.groupby(["fuente", "resultado"], sort=False).agg(
        n_min=("n", "min"), n_max=("n", "max"), ece=("ece", "first"), ruido_lo=("esperado_lo", "first"),
        ruido_hi=("esperado_hi", "first"), sobre_ruido=("sobre_ruido", "first"))
    print(resumen.to_string())
    return df


if __name__ == "__main__":
    main()
