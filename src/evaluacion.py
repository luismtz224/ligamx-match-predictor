"""Validación walk-forward por temporada con intervalos de confianza por bootstrap.

Cada fold prueba una temporada con modelos entrenados con todas las anteriores
(ventana expansiva). Elo y forma se calculan una sola vez sobre toda la historia:
cada feature solo usa partidos anteriores, así que lo único que cambia por fold
es el ajuste del modelo. Hiperparámetros fijos, no se afinan con estos folds.

Uso: python -m src.evaluacion
"""
import numpy as np
import pandas as pd

from src.entrenar import RUTA_CSV, X_MERCADO, logistica, xgboost
from src.features import X_COLS, cargar_partidos, procesar

INICIO = "2013/2014"   # 2012/13 solo calienta el Elo
PRIMERA = "2018/2019"
ULTIMA = "2025/2026"   # 2026/27 está en curso y queda fuera
USADAS_EN_VALIDACION = {"2021/2022", "2022/2023"}  # rejilla del Elo validada aquí
N_BOOT = 10_000
SEMILLA = 42
MODELOS = ["frecuencias", "mercado", "logistica", "logistica + mercado", "xgboost"]


def generar_folds(feat, primera=PRIMERA, ultima=ULTIMA, inicio=INICIO):
    """Lista de (temporada, idx_train, idx_test) con ventana expansiva por temporada."""
    temporadas = sorted(feat["Season"].unique())
    folds = []
    for s in [t for t in temporadas if primera <= t <= ultima]:
        anterior = temporadas[temporadas.index(s) - 1]
        train = feat.index[feat["Season"].between(inicio, anterior)]
        test = feat.index[feat["Season"] == s]
        folds.append((s, train.to_numpy(), test.to_numpy()))
    return folds


def predicciones_oof(feat, folds):
    """Probabilidades fuera de muestra [A, D, H] de cada modelo, en el orden de los folds."""
    probs = {k: [] for k in MODELOS}
    for _, i_tr, i_te in folds:
        train, test = feat.loc[i_tr], feat.loc[i_te]
        prior = train["y"].value_counts(normalize=True).reindex([0, 1, 2], fill_value=0).values
        probs["frecuencias"].append(np.tile(prior, (len(test), 1)))
        probs["mercado"].append(test[["pA", "pD", "pH"]].values)
        probs["logistica"].append(
            logistica().fit(train[X_COLS], train["y"]).predict_proba(test[X_COLS]))
        probs["logistica + mercado"].append(
            logistica().fit(train[X_MERCADO], train["y"]).predict_proba(test[X_MERCADO]))
        probs["xgboost"].append(
            xgboost().fit(train[X_COLS], train["y"]).predict_proba(test[X_COLS]))
    return {k: np.vstack(v) for k, v in probs.items()}


def perdida_por_partido(y, p):
    """Log loss de cada partido; su promedio es el log loss total."""
    return -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1))


def bootstrap_pareado(dif, bloques=None, n=N_BOOT, semilla=SEMILLA):
    """Media de dif e IC 95% por bootstrap de percentiles.

    Remuestrea bloques completos con reemplazo (sin bloques = cada partido es su
    propio bloque, o sea iid). La media de cada réplica pondera por partido.
    """
    dif = np.asarray(dif, dtype=float)
    if bloques is None:
        bloques = np.arange(len(dif))
    _, cod = np.unique(bloques, return_inverse=True)
    suma = np.bincount(cod, weights=dif)
    tam = np.bincount(cod).astype(float)
    g = len(suma)

    rng = np.random.default_rng(semilla)
    medias = np.empty(n)
    for ini in range(0, n, 1000):  # por tandas para no reventar la memoria
        k = min(1000, n - ini)
        conteos = rng.multinomial(g, np.full(g, 1 / g), size=k)
        medias[ini:ini + k] = (conteos @ suma) / (conteos @ tam)
    lo, hi = np.percentile(medias, [2.5, 97.5])
    return dif.mean(), lo, hi


def main():
    d = cargar_partidos(RUTA_CSV)
    feat, _, _ = procesar(d, K=20, ventaja=60, regresion=0.0)
    folds = generar_folds(feat)
    probs = predicciones_oof(feat, folds)

    i_test = np.concatenate([te for _, _, te in folds])
    y = feat.loc[i_test, "y"].to_numpy()
    temp = feat.loc[i_test, "Season"].to_numpy()
    semana = feat.loc[i_test, "Date"].dt.to_period("W-SUN").astype(str).to_numpy()  # lunes a domingo
    perd = {k: perdida_por_partido(y, p) for k, p in probs.items()}

    pd.set_option("display.width", 200)
    print(f"Walk-forward: {len(folds)} folds, {len(y)} partidos de prueba, "
          f"{len(np.unique(semana))} semanas\n")

    print("(1) Log loss por fold")
    filas = []
    for s, i_tr, i_te in folds:
        m = temp == s
        filas.append({"fold": s + ("*" if s in USADAS_EN_VALIDACION else ""),
                      "n_train": len(i_tr), "n_test": len(i_te),
                      **{k: perd[k][m].mean() for k in MODELOS}})
    print(pd.DataFrame(filas).set_index("fold").round(4).to_string())
    print("* temporada usada para validar la rejilla del Elo (ganaron los valores "
          "originales, dif ~0.0004): fold no 100% limpio.\n")

    print("(2) Agregado fuera de muestra")
    agg = pd.DataFrame({k: {"log_loss": perd[k].mean(),
                            "accuracy": (probs[k].argmax(axis=1) == y).mean()}
                        for k in MODELOS}).T.sort_values("log_loss")
    print(agg.round(4).to_string(), "\n")

    print(f"(3) Log loss del modelo - log loss del mercado, por partido "
          f"(positivo = peor que el mercado). IC 95%, {N_BOOT:,} remuestreos pareados")
    filas = []
    for k in MODELOS:
        if k == "mercado":
            continue
        dif = perd[k] - perd["mercado"]
        media, lo_i, hi_i = bootstrap_pareado(dif)
        _, lo_b, hi_b = bootstrap_pareado(dif, bloques=semana)
        filas.append({"modelo": k, "dif_media": media,
                      "iid_lo": lo_i, "iid_hi": hi_i,
                      "bloques_lo": lo_b, "bloques_hi": hi_b,
                      "bloques_cruza_0": lo_b <= 0 <= hi_b})
    print(pd.DataFrame(filas).set_index("modelo").round(4).to_string())
    print("Bloques = semana calendario (lunes a domingo), aproximación de jornada. "
          "Es el IC principal.\n")

    print("(4) Log loss de la logística - log loss del otro modelo, por partido "
          "(negativo = la logística es mejor). Mismo bootstrap pareado")
    filas = []
    for k in ["xgboost", "frecuencias"]:
        dif = perd["logistica"] - perd[k]
        media, lo_i, hi_i = bootstrap_pareado(dif)
        _, lo_b, hi_b = bootstrap_pareado(dif, bloques=semana)
        gana = sum(perd["logistica"][temp == s].mean() < perd[k][temp == s].mean()
                   for s, _, _ in folds)
        filas.append({"comparacion": f"logistica vs {k}", "dif_media": media,
                      "iid_lo": lo_i, "iid_hi": hi_i,
                      "bloques_lo": lo_b, "bloques_hi": hi_b,
                      "bloques_cruza_0": lo_b <= 0 <= hi_b,
                      "folds_gana_logistica": f"{gana}/{len(folds)}",
                      "folds_gana_otro": f"{len(folds) - gana}/{len(folds)}"})
    print(pd.DataFrame(filas).set_index("comparacion").round(4).to_string())


if __name__ == "__main__":
    main()
