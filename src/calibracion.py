"""Calibración de probabilidades con las predicciones fuera de muestra del walk-forward.

Solo MIDE: no aplica ninguna recalibración. Reutiliza las predicciones de
src/evaluacion.py (8 folds, cada partido predicho con un modelo que solo vio
temporadas anteriores). Compara la regresión logística (Elo + forma) contra el
mercado como referencia.

Uso: python -m src.calibracion
"""
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from src.evaluacion import N_BOOT, SEMILLA, bootstrap_pareado, oof_walk_forward

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RUTA_PNG = RAIZ / "docs" / "calibracion.png"

# Con ~2,650 partidos, 6 bins por cuantiles dejan ~440 partidos por bin: error estándar de
# la frecuencia real ~2.4 pp. Con 10 bins serían ~265 y ~3.1 pp (curva ruidosa).
N_BINS = 6
BINS_SENSIBILIDAD = (4, 6, 10)
N_SIM = 1000
# (nombre, columna en predict_proba [A, D, H])
RESULTADOS = [("Gana local", 2), ("Empate", 1), ("Gana visitante", 0)]
FUENTES = ["logistica", "mercado"]


def asignar_bins(p, n_bins=N_BINS):
    """Bin (0..n_bins-1) de cada predicción, con bordes en los cuantiles de p.

    Cada predicción cae en exactamente un bin. Con valores repetidos algunos bordes
    coinciden y el bin intermedio queda vacío.
    """
    p = np.asarray(p, dtype=float)
    bordes = np.quantile(p, np.linspace(0, 1, n_bins + 1)[1:-1])
    return np.searchsorted(bordes, p, side="right")


def _sumas_por_bin(p, o, bins, n_bins):
    n = np.bincount(bins, minlength=n_bins).astype(float)
    sp = np.bincount(bins, weights=p, minlength=n_bins)
    so = np.bincount(bins, weights=o, minlength=n_bins)
    return n, sp, so


def ece(p, o, n_bins=N_BINS, bins=None):
    """Error de calibración esperado: media ponderada de |predicha media - frecuencia real|."""
    p, o = np.asarray(p, dtype=float), np.asarray(o, dtype=float)
    if bins is None:
        bins = asignar_bins(p, n_bins)
    _, sp, so = _sumas_por_bin(p, o, bins, n_bins)
    return np.abs(sp - so).sum() / len(p)


def brier(p, o):
    return float(np.mean((np.asarray(p, dtype=float) - np.asarray(o, dtype=float)) ** 2))


def tabla_bins(p, o, n_bins=N_BINS):
    """DataFrame por bin: n, probabilidad predicha media, frecuencia real e IC Wilson 95%."""
    p, o = np.asarray(p, dtype=float), np.asarray(o, dtype=float)
    n, sp, so = _sumas_por_bin(p, o, asignar_bins(p, n_bins), n_bins)
    ok = n > 0
    n, pred, freq = n[ok], sp[ok] / n[ok], so[ok] / n[ok]
    z = 1.96
    centro = (freq + z**2 / (2 * n)) / (1 + z**2 / n)
    mitad = z * np.sqrt(freq * (1 - freq) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return pd.DataFrame({"n": n.astype(int), "pred": pred, "freq": freq,
                         "dif_pp": (pred - freq) * 100,
                         "wilson_lo": centro - mitad, "wilson_hi": centro + mitad})


def bootstrap_ece(p, o, bloques, n_bins=N_BINS, n=N_BOOT, semilla=SEMILLA):
    """IC 95% del ECE remuestreando bloques (semanas) con reemplazo.

    Los bordes de los bins se fijan con la muestra completa y no se recalculan por réplica.
    """
    p, o = np.asarray(p, dtype=float), np.asarray(o, dtype=float)
    bins = asignar_bins(p, n_bins)
    _, cod = np.unique(bloques, return_inverse=True)
    g = cod.max() + 1
    # por semana y bin: partidos, suma de p y suma de o
    cnt = np.zeros((g, n_bins))
    dif = np.zeros((g, n_bins))
    np.add.at(cnt, (cod, bins), 1.0)
    np.add.at(dif, (cod, bins), p - o)

    rng = np.random.default_rng(semilla)
    ece_b = np.empty(n)
    for ini in range(0, n, 1000):
        k = min(1000, n - ini)
        conteos = rng.multinomial(g, np.full(g, 1 / g), size=k)
        ece_b[ini:ini + k] = np.abs(conteos @ dif).sum(axis=1) / (conteos @ cnt).sum(axis=1)
    return tuple(np.percentile(ece_b, [2.5, 97.5]))


def ece_esperado(p3, n_bins=N_BINS, n_sim=N_SIM, semilla=SEMILLA):
    """ECE por resultado si el modelo estuviera perfectamente calibrado.

    Simula el resultado de cada partido a partir de las propias probabilidades predichas.
    El ECE tiene sesgo positivo por ruido de muestra: un modelo perfecto no da 0.
    Devuelve {columna: (media, p2.5, p97.5)}.
    """
    p3 = np.asarray(p3, dtype=float)
    rng = np.random.default_rng(semilla)
    cum = p3.cumsum(axis=1)
    cum[:, -1] = 1.0
    bins = {k: asignar_bins(p3[:, k], n_bins) for k in range(3)}
    sims = {k: np.empty(n_sim) for k in range(3)}
    for s in range(n_sim):
        clase = (rng.random(len(p3))[:, None] > cum).sum(axis=1)
        for k in range(3):
            sims[k][s] = ece(p3[:, k], clase == k, n_bins, bins[k])
    return {k: (v.mean(), *np.percentile(v, [2.5, 97.5])) for k, v in sims.items()}


def graficar(probs, y, ruta=RUTA_PNG):
    """Diagrama de confiabilidad: 3 paneles apilados (legible en pantalla chica)."""
    azul, naranja = "#2a78d6", "#eb6834"      # validados (CVD y contraste), ver skill dataviz
    tinta, tenue, rejilla = "#0b0b0b", "#52514e", "#e1e0d9"
    plt.rcParams.update({"font.size": 13, "axes.edgecolor": "#c3c2b7"})
    fig, axes = plt.subplots(3, 1, figsize=(6.4, 15.5), facecolor="#fcfcfb")
    estilo = {"logistica": dict(color=azul, marker="o", label="Regresión logística", dx=-0.0035),
              "mercado": dict(color=naranja, marker="s", label="Mercado (momios)", dx=0.0035)}
    for ax, (nombre, k) in zip(axes, RESULTADOS):
        ax.set_facecolor("#fcfcfb")
        o = (y == k).astype(float)
        valores = []
        for fuente in FUENTES:
            t = tabla_bins(probs[fuente][:, k], o)
            e = estilo[fuente]
            valores += [t["pred"].min(), t["pred"].max(), t["wilson_lo"].min(), t["wilson_hi"].max()]
            ax.errorbar(t["pred"] + e["dx"], t["freq"],
                        yerr=[t["freq"] - t["wilson_lo"], t["wilson_hi"] - t["freq"]],
                        color=e["color"], marker=e["marker"], markersize=9, linestyle="none",
                        elinewidth=1.4, capsize=4, markeredgecolor="#fcfcfb", markeredgewidth=1.5,
                        label=e["label"], zorder=3)
        lo, hi = min(valores) - 0.03, max(valores) + 0.03
        ax.plot([lo, hi], [lo, hi], color=tenue, linestyle="--", linewidth=1.5,
                label="Calibración perfecta", zorder=2)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_aspect("equal")
        ax.grid(color=rejilla, linewidth=0.8)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        pct = matplotlib.ticker.PercentFormatter(1.0, decimals=0)
        ax.xaxis.set_major_formatter(pct)
        ax.yaxis.set_major_formatter(pct)
        ax.tick_params(colors=tenue, labelsize=12)
        ax.set_xlabel("Probabilidad que dio el modelo", color=tinta, fontsize=13)
        ax.set_ylabel("Frecuencia con que sí pasó", color=tinta, fontsize=13)
        ece_l = ece(probs["logistica"][:, k], o)
        ece_m = ece(probs["mercado"][:, k], o)
        ax.set_title(f"{nombre}\nECE: logística {ece_l:.3f} · mercado {ece_m:.3f}",
                     color=tinta, fontsize=14, fontweight="bold", loc="left")
    axes[0].legend(loc="upper left", fontsize=11.5, frameon=False)
    fig.suptitle("¿Las probabilidades se parecen a la realidad?\n"
                 f"{len(y):,} partidos fuera de muestra, 8 temporadas",
                 color=tinta, fontsize=15, fontweight="bold", x=0.02, ha="left", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.975), h_pad=2.0)
    ruta.parent.mkdir(exist_ok=True)
    fig.savefig(ruta, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    _, y, _, semana, probs = oof_walk_forward()
    pd.set_option("display.width", 200)
    print(f"Calibración con {len(y)} predicciones fuera de muestra del walk-forward, "
          f"{len(np.unique(semana))} semanas, {N_BINS} bins por cuantiles\n")

    print(f"(1) Curva de calibración por bin ({N_BINS} bins de igual cantidad de partidos). "
          "dif_pp = predicha - real; Wilson = IC 95% de la frecuencia real")
    for fuente in FUENTES:
        for nombre, k in RESULTADOS:
            t = tabla_bins(probs[fuente][:, k], (y == k).astype(float))
            t.index = range(1, len(t) + 1)
            t.index.name = "bin"
            print(f"\n{fuente} - {nombre}")
            print(t.round(4).to_string())

    print(f"\n(2) Brier y ECE por resultado ({N_BINS} bins), IC 95% por bootstrap de bloques de "
          f"semana ({N_BOOT:,} remuestreos, semilla {SEMILLA})")
    esperado = {f: ece_esperado(probs[f]) for f in FUENTES}
    filas = []
    for fuente in FUENTES:
        total = np.zeros(len(y))
        for nombre, k in RESULTADOS:
            p, o = probs[fuente][:, k], (y == k).astype(float)
            err2 = (p - o) ** 2
            total += err2
            b, b_lo, b_hi = bootstrap_pareado(err2, bloques=semana)
            e = ece(p, o)
            e_lo, e_hi = bootstrap_ece(p, o, semana)
            filas.append({"fuente": fuente, "resultado": nombre,
                          "brier": b, "brier_lo": b_lo, "brier_hi": b_hi,
                          "ece": e, "ece_lo": e_lo, "ece_hi": e_hi,
                          "ece_esperado_si_perfecto": esperado[fuente][k][0],
                          "esp_lo": esperado[fuente][k][1], "esp_hi": esperado[fuente][k][2]})
        b, b_lo, b_hi = bootstrap_pareado(total, bloques=semana)
        filas.append({"fuente": fuente, "resultado": "Brier total (suma de 3)",
                      "brier": b, "brier_lo": b_lo, "brier_hi": b_hi})
    print(pd.DataFrame(filas).set_index(["fuente", "resultado"]).round(4).to_string())
    print("ece_esperado_si_perfecto: ECE promedio de simular los resultados con las propias "
          f"probabilidades ({N_SIM} simulaciones); esp_lo/esp_hi = percentiles 2.5 y 97.5. "
          "Un ECE dentro de ese rango es indistinguible de ruido.")

    print("\n(3) Sensibilidad al número de bins: ECE observado / ECE esperado si fuera perfecto")
    filas = []
    for fuente in FUENTES:
        for nombre, k in RESULTADOS:
            fila = {"fuente": fuente, "resultado": nombre}
            for nb in BINS_SENSIBILIDAD:
                obs = ece(probs[fuente][:, k], (y == k).astype(float), nb)
                esp = ece_esperado(probs[fuente], nb)[k]
                fila[f"{nb} bins: ECE"] = obs
                fila[f"{nb} bins: esperado"] = esp[0]
                fila[f"{nb} bins: sobre p97.5?"] = bool(obs > esp[2])
            filas.append(fila)
    print(pd.DataFrame(filas).set_index(["fuente", "resultado"]).round(4).to_string())

    graficar(probs, y)
    print(f"\nGráfica guardada en {RUTA_PNG}")


if __name__ == "__main__":
    main()
