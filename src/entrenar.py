from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.features import X_COLS, cargar_partidos, procesar

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CSV = RAIZ / "datos" / "crudos" / "MEX.csv"
RUTA_MODELO = RAIZ / "modelos" / "modelo.joblib"

X_MERCADO = X_COLS + ["pH", "pD", "pA"]


def logistica():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(max_iter=1000))


def xgboost():
    return XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8,
                         eval_metric="mlogloss", random_state=42)


def metricas(y, p):
    return log_loss(y, p, labels=[0, 1, 2]), accuracy_score(y, p.argmax(axis=1))


def main():
    d = cargar_partidos(RUTA_CSV)
    feat, elo, hist = procesar(d, K=20, ventaja=60, regresion=0.0)

    # split temporal: 2012/13 solo calienta el Elo; 2026/27 (en curso) queda fuera de train y test
    train = feat[feat["Season"].between("2013/2014", "2022/2023")]
    test = feat[feat["Season"].between("2023/2024", "2025/2026")]
    print(len(train), "train |", len(test), "test")
    y_test = test["y"].values

    res = {}

    # frecuencias históricas del train
    prior = train["y"].value_counts(normalize=True).sort_index().values
    res["frecuencias"] = metricas(y_test, np.tile(prior, (len(test), 1)))

    # mercado (columnas en orden A, D, H = 0, 1, 2)
    res["mercado"] = metricas(y_test, test[["pA", "pD", "pH"]].values)

    m = logistica().fit(train[X_COLS], train["y"])
    res["logistica"] = metricas(y_test, m.predict_proba(test[X_COLS]))

    m = logistica().fit(train[X_MERCADO], train["y"])
    res["logistica + mercado"] = metricas(y_test, m.predict_proba(test[X_MERCADO]))

    m = xgboost().fit(train[X_COLS], train["y"])
    res["xgboost"] = metricas(y_test, m.predict_proba(test[X_COLS]))

    print(pd.DataFrame(res, index=["log_loss", "accuracy"]).T.round(4)
            .sort_values("log_loss").to_string())

    # modelo del dashboard: logística ajustada con TODOS los partidos
    final = logistica().fit(feat[X_COLS], feat["y"])
    ultima = feat["Season"].max()
    activos = sorted(set(feat.loc[feat["Season"] == ultima, "Home"])
                     | set(feat.loc[feat["Season"] == ultima, "Away"]))
    RUTA_MODELO.parent.mkdir(exist_ok=True)
    joblib.dump({"modelo": final, "cols": X_COLS,
                 "elo": dict(elo),
                 "hist": {t: list(q) for t, q in hist.items()},  # defaultdict con lambda no se puede guardar
                 "activos": activos},
                RUTA_MODELO)
    print(f"{len(activos)} equipos activos. Modelo guardado en {RUTA_MODELO}")


if __name__ == "__main__":
    main()
