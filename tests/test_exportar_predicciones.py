"""Fase B de Extras: datos/procesados/predicciones_oof.csv coincide con el walk-forward, con el README y está en git.

La app solo lee el CSV (no importa xgboost); `python -m src.exportar_predicciones` lo genera con `oof_walk_forward()`.
"""
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import exportar_predicciones as exp
from src.evaluacion import perdida_por_partido
from src.resumen_temporada import resumen, temporadas

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "datos" / "procesados" / "predicciones_oof.csv"
REL = "datos/procesados/predicciones_oof.csv"
README = (RAIZ / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(RUTA, parse_dates=["fecha"])


def test_el_csv_tiene_la_forma_esperada(df):
    assert list(df.columns) == exp.COLUMNAS and len(df) == 2651
    assert temporadas(df) == [f"{a}/{a + 1}" for a in range(2018, 2026)]  # 2018/2019 a 2025/2026, sin la 2026/2027
    assert set(df["resultado"]) <= {"H", "D", "A"} and set(df["pred_logistica"]) <= {"H", "D", "A"}
    assert set(df["pred_mercado"]) <= {"H", "D", "A"}
    for pref in ("log", "mer"):
        suma = df[[f"{pref}_local", f"{pref}_empate", f"{pref}_visitante"]].sum(axis=1)
        assert np.allclose(suma, 1.0, atol=1e-5), pref  # cada fila es una distribución de probabilidad
    # el resultado y el marcador cuentan lo mismo
    esperado = np.where(df["goles_local"] > df["goles_visitante"], "H",
                        np.where(df["goles_local"] < df["goles_visitante"], "A", "D"))
    assert (esperado == df["resultado"]).all()
    # en orden de temporada y, dentro de cada una, de fecha
    for _, g in df.groupby("temporada", sort=False):
        assert g["fecha"].is_monotonic_increasing
    assert df["temporada"].is_monotonic_increasing
    assert (df["local"] != df["visitante"]).all()


def test_el_agregado_de_las_8_temporadas_coincide_con_el_readme(df):
    """logística 1.0281 y 49.30 %, momios 1.0037 y 50.85 %, 2,651 partidos (los números del README)."""
    filas = {n: (ll, acc) for n, ll, acc in re.findall(r"\| (Momios[^|]*|Regresión logística[^|]*) \| ([\d.]+) \| ([\d.]+)%", README)}
    assert len(filas) == 2
    r = resumen(df)
    assert r["logistica"]["partidos"] == r["mercado"]["partidos"] == 2651 and "2,651 partidos" in README
    readme_log, acc_log = next(v for k, v in filas.items() if k.startswith("Regresión"))
    readme_mer, acc_mer = next(v for k, v in filas.items() if k.startswith("Momios"))
    assert (acc_log, acc_mer) == ("49.30", "50.85")  # lo que dice el README
    assert (f"{r['logistica']['log_loss']:.4f}", f"{r['logistica']['accuracy'] * 100:.2f}") == ("1.0281", "49.30")
    assert (f"{r['mercado']['log_loss']:.4f}", f"{r['mercado']['accuracy'] * 100:.2f}") == ("1.0037", "50.85")
    assert f"{r['logistica']['log_loss']:.4f}" == readme_log and f"{r['mercado']['log_loss']:.4f}" == readme_mer


def test_cada_temporada_coincide_con_el_walk_forward(oof, df):
    """Log loss y accuracy de cada temporada del CSV = los de oof_walk_forward() (los de evaluacion.py)."""
    folds, y, temp, _, probs = oof
    for modelo, clave in (("logistica", "logistica"), ("mercado", "mercado")):
        perd = perdida_por_partido(y, probs[clave])
        acc = probs[clave].argmax(axis=1) == y
        for s in temporadas(df):
            m = temp == s
            r = resumen(df[df["temporada"] == s])[modelo]
            assert r["partidos"] == int(m.sum())
            assert r["log_loss"] == pytest.approx(perd[m].mean(), abs=1e-5), (modelo, s)
            assert r["accuracy"] == pytest.approx(acc[m].mean(), abs=1e-12), (modelo, s)
            assert r["aciertos"] == int(acc[m].sum())


def test_fecha_equipos_y_goles_son_los_del_csv_crudo(df):
    crudo = pd.read_csv(RAIZ / "datos" / "crudos" / "MEX.csv")
    crudo["Date"] = pd.to_datetime(crudo["Date"], dayfirst=True)
    clave = crudo.set_index(["Date", "Home", "Away"])[["HG", "AG", "Res"]]
    for fila in df.sample(80, random_state=0).itertuples():
        sel = clave.loc[(fila.fecha, fila.local, fila.visitante)]
        if isinstance(sel, pd.DataFrame):  # dos partidos iguales el mismo día: basta con el primero
            sel = sel.iloc[0]
        assert (sel["HG"], sel["AG"], sel["Res"]) == (fila.goles_local, fila.goles_visitante, fila.resultado)


def test_el_csv_versionado_es_igual_a_recalcularlo(oof, df, tmp_path, capsys):
    exp.main(ruta=tmp_path / "p.csv", oof=oof)
    salida = capsys.readouterr().out
    assert "2651 partidos de 8 temporadas" in salida and "acc_logistica" in salida
    nuevo = pd.read_csv(tmp_path / "p.csv", parse_dates=["fecha"])
    pd.testing.assert_frame_equal(nuevo, df, check_exact=False, atol=1e-6)


def test_construir_se_niega_si_los_partidos_no_coinciden_con_las_predicciones(oof):
    from src.entrenar import RUTA_CSV
    from src.features import cargar_partidos, procesar
    folds, y, temp, _, probs = oof
    feat, _, _ = procesar(cargar_partidos(RUTA_CSV), K=20, ventaja=60, regresion=0.0)
    with pytest.raises(ValueError):
        exp.construir(folds, y[::-1].copy(), temp, probs, feat)


def test_el_csv_esta_en_git_o_se_puede_agregar_y_no_lo_ignora_gitignore():
    """Cloud solo ve lo que está en git: `.gitignore` deja pasar este CSV y está versionado o es agregable."""
    git = shutil.which("git")
    if git is None or not (RAIZ / ".git").exists():
        pytest.skip("sin git")
    assert subprocess.run([git, "check-ignore", "-q", REL], cwd=RAIZ).returncode == 1, "está en .gitignore"
    visibles = subprocess.run([git, "ls-files", "--cached", "--others", "--exclude-standard", "datos/procesados/"],
                              cwd=RAIZ, capture_output=True, text=True).stdout.split()
    assert REL in visibles and "datos/procesados/calibracion.csv" in visibles
    assert "datos/procesados/partidos.csv" not in visibles
