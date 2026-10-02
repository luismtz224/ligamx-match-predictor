"""Lectura de la regresión logística: qué empuja la predicción hacia local o visitante.

Con features escaladas z, el logit de cada clase k es b_k + coef_k · z. La diferencia
local - visitante se reparte en contribuciones w_j * z_j con w = coef_local - coef_visitante.
z = 0 es el partido promedio del entrenamiento, así que cada contribución se mide contra él.
No dice nada del empate, y es la lectura del modelo, no una causa real.
"""
import numpy as np
import pandas as pd

from src.features import MAP

# Elo va junto: elo_diff es colineal con elo_h y elo_a, por separado no se puede leer
FACTORES = {
    "Elo": ["elo_diff", "elo_h", "elo_a"],
    "Puntos recientes": ["pts_h", "pts_a"],
    "Goles a favor": ["gf_h", "gf_a"],
    "Goles en contra": ["gc_h", "gc_a"],
}


def _partes(pipeline):
    lr = pipeline[-1]
    clases = list(lr.classes_)
    return pipeline[:-1], lr, clases.index(MAP["H"]), clases.index(MAP["A"])


def contribuciones(pipeline, x):
    """Contribución de cada feature y factor al logit local - visitante para un partido.

    `x` es un DataFrame de un renglón con las columnas del modelo.
    """
    pre, lr, iH, iA = _partes(pipeline)
    z = pre.transform(x)[0]
    w = lr.coef_[iH] - lr.coef_[iA]
    por_feature = pd.Series(w * z, index=x.columns)
    por_factor = pd.Series({f: por_feature[cols].sum() for f, cols in FACTORES.items()})
    intercepto = float(lr.intercept_[iH] - lr.intercept_[iA])
    return {
        "intercepto": intercepto,
        "por_feature": por_feature,
        "por_factor": por_factor,
        "total": intercepto + por_feature.sum(),
        "imputadas": [c for c in x.columns if pd.isna(x.iloc[0][c])],
    }


def probabilidades(pipeline, x):
    """predict_proba reconstruido a mano con los coeficientes (softmax de los logits)."""
    pre, lr, _, _ = _partes(pipeline)
    logits = pre.transform(x) @ lr.coef_.T + lr.intercept_
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)
