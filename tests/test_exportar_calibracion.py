"""Fase A de Extras: datos/procesados/calibracion.csv coincide con src/calibracion.py y está en git.

La app solo lee el CSV (no importa matplotlib ni xgboost); `python -m src.exportar_calibracion` lo genera con las
predicciones fuera de muestra del walk-forward. Estas pruebas recalculan todo desde `oof_walk_forward()` (~20 s).
"""
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import calibracion as cal
from src import exportar_calibracion as exp

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "datos" / "procesados" / "calibracion.csv"
REL = "datos/procesados/calibracion.csv"


@pytest.fixture(scope="module")
def csv():
    return pd.read_csv(RUTA)


def test_el_csv_tiene_la_forma_esperada(csv):
    assert list(csv.columns) == exp.COLUMNAS
    assert len(csv) == 2 * 2 * cal.N_BINS  # 2 fuentes x 2 resultados x 6 grupos
    assert set(csv["fuente"]) == {"logistica", "mercado"} and set(csv["resultado"]) == {"local", "visitante"}
    for (fuente, resultado), g in csv.groupby(["fuente", "resultado"]):
        assert list(g["grupo"]) == list(range(1, cal.N_BINS + 1)), (fuente, resultado)
        assert g["n"].sum() == g["n_total"].iloc[0] == 2651  # cada partido cae en un solo grupo
        assert g["n"].min() >= 400  # grupos grandes: con pocos partidos la gráfica engaña
        assert g["pred"].is_monotonic_increasing  # los grupos van de menor a mayor probabilidad
        assert ((g["wilson_lo"] <= g["freq"]) & (g["freq"] <= g["wilson_hi"])).all()
        assert g[["ece", "ece_lo", "ece_hi", "ece_esperado", "esperado_lo", "esperado_hi", "sobre_ruido"]].nunique().max() == 1


def test_los_numeros_coinciden_con_src_calibracion(oof, csv):
    """Cada fila del CSV sale de las funciones de src/calibracion.py con las mismas predicciones."""
    _, y, _, semana, probs = oof
    esperado = {f: cal.ece_esperado(probs[f]) for f in cal.FUENTES}
    for fuente in cal.FUENTES:
        for resultado, k in exp.RESULTADOS:
            p, o = probs[fuente][:, k], (y == k).astype(float)
            g = csv[(csv["fuente"] == fuente) & (csv["resultado"] == resultado)].sort_values("grupo")
            t = cal.tabla_bins(p, o, cal.N_BINS)
            assert list(g["n"]) == list(t["n"])
            for col in ("pred", "freq", "wilson_lo", "wilson_hi"):
                np.testing.assert_allclose(g[col], t[col], atol=1e-6, err_msg=f"{fuente} {resultado} {col}")
            e = cal.ece(p, o)
            e_lo, e_hi = cal.bootstrap_ece(p, o, semana)
            esp, esp_lo, esp_hi = esperado[fuente][k]
            fila = g.iloc[0]
            for col, valor in (("ece", e), ("ece_lo", e_lo), ("ece_hi", e_hi), ("ece_esperado", esp),
                               ("esperado_lo", esp_lo), ("esperado_hi", esp_hi)):
                assert fila[col] == pytest.approx(valor, abs=1e-6), (fuente, resultado, col)
            assert bool(fila["sobre_ruido"]) == bool(e > esp_hi)
            assert fila["n_total"] == len(y)


def test_los_numeros_de_los_dos_resultados_no_se_confunden(oof, csv):
    """«local» usa la columna H de predict_proba y «visitante» la A: no pueden coincidir en los datos reales."""
    _, y, _, _, probs = oof
    loc = csv[(csv["fuente"] == "logistica") & (csv["resultado"] == "local")]["freq"]
    vis = csv[(csv["fuente"] == "logistica") & (csv["resultado"] == "visitante")]["freq"]
    assert not np.allclose(loc.values, vis.values)
    assert abs(loc.mean() - (y == 2).mean()) < 0.02 and abs(vis.mean() - (y == 0).mean()) < 0.02  # ~ la frecuencia global


def test_el_csv_versionado_es_igual_a_recalcularlo(oof, csv, tmp_path, capsys):
    """El script offline, corrido de verdad, reproduce el CSV de git (no quedó viejo)."""
    exp.main(ruta=tmp_path / "calibracion.csv", oof=oof)
    salida = capsys.readouterr().out
    assert "24 filas" in salida and "2651 partidos" in salida and "sobre_ruido" in salida
    nuevo = pd.read_csv(tmp_path / "calibracion.csv")
    pd.testing.assert_frame_equal(nuevo, csv, check_exact=False, atol=1e-6)


def test_el_csv_esta_en_git_o_se_puede_agregar_y_no_lo_ignora_gitignore():
    """Cloud solo ve lo que está en git. `.gitignore` deja pasar este CSV (y solo los dos de la app) y el archivo
    está versionado (`git ls-files`) o, mientras Luis no haga commit, es agregable (untracked y no ignorado)."""
    git = shutil.which("git")
    if git is None or not (RAIZ / ".git").exists():
        pytest.skip("sin git")
    ignorado = subprocess.run([git, "check-ignore", "-q", REL], cwd=RAIZ).returncode
    assert ignorado == 1, "calibracion.csv está en .gitignore"
    visibles = subprocess.run([git, "ls-files", "--cached", "--others", "--exclude-standard", "datos/procesados/"],
                              cwd=RAIZ, capture_output=True, text=True).stdout.split()
    assert REL in visibles
    assert "datos/procesados/partidos.csv" not in visibles  # el resto de datos/procesados sigue fuera
    assert subprocess.run([git, "check-ignore", "-q", "datos/procesados/predicciones_oof.csv"], cwd=RAIZ).returncode == 1
    assert subprocess.run([git, "check-ignore", "-q", "datos/procesados/otro.csv"], cwd=RAIZ).returncode == 0
