"""Cálculos de la página «Temporadas» (src/resumen_temporada.py): sin Streamlit ni xgboost."""
import ast
import math
from pathlib import Path

import pandas as pd
import pytest

from src.resumen_temporada import (BLOQUE, FILTROS, accuracy, acierto, bloque_visible, de_temporada, filtrar, log_loss,
                                   porcentajes, prob_real, resumen, temporadas)

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "datos" / "procesados" / "predicciones_oof.csv"


def _df(filas):
    """filas = (temporada, fecha, resultado, pred_log, [pH, pD, pA], pred_mer, [pH, pD, pA])"""
    return pd.DataFrame([dict(temporada=t, fecha=pd.Timestamp(f), resultado=r, pred_logistica=pl,
                              log_local=a[0], log_empate=a[1], log_visitante=a[2], pred_mercado=pm,
                              mer_local=b[0], mer_empate=b[1], mer_visitante=b[2])
                         for t, f, r, pl, a, pm, b in filas])


EJEMPLO = _df([
    ("2020/2021", "2020-08-02", "H", "H", [0.5, 0.3, 0.2], "D", [0.3, 0.4, 0.3]),   # logística acierta, momios fallan
    ("2020/2021", "2020-08-01", "D", "H", [0.5, 0.25, 0.25], "D", [0.3, 0.4, 0.3]),  # logística falla, momios aciertan
    ("2019/2020", "2019-09-01", "A", "A", [0.2, 0.2, 0.6], "A", [0.1, 0.2, 0.7]),    # los dos aciertan
])


def test_acierto_compara_el_resultado_mas_probable_con_el_que_paso():
    assert list(acierto(EJEMPLO, "logistica")) == [True, False, True]
    assert list(acierto(EJEMPLO, "mercado")) == [False, True, True]


def test_log_loss_y_accuracy_con_un_ejemplo_calculado_a_mano():
    assert list(prob_real(EJEMPLO, "logistica")) == [0.5, 0.25, 0.6]
    esperado = -(math.log(0.5) + math.log(0.25) + math.log(0.6)) / 3
    assert log_loss(EJEMPLO, "logistica") == pytest.approx(esperado)
    assert accuracy(EJEMPLO, "logistica") == pytest.approx(2 / 3)
    assert log_loss(EJEMPLO, "mercado") == pytest.approx(-(math.log(0.3) + math.log(0.4) + math.log(0.7)) / 3)
    # probabilidad cero: el recorte a 1e-15 evita el infinito, como en evaluacion.py
    cero = _df([("2020/2021", "2020-08-01", "H", "A", [0.0, 0.5, 0.5], "A", [0.0, 0.5, 0.5])])
    assert log_loss(cero, "logistica") == pytest.approx(-math.log(1e-15)) and accuracy(cero, "logistica") == 0


def test_resumen_cuenta_partidos_y_aciertos():
    r = resumen(EJEMPLO)
    assert r["logistica"]["partidos"] == 3 and r["logistica"]["aciertos"] == 2
    assert r["mercado"]["aciertos"] == 2 and r["logistica"]["accuracy"] == pytest.approx(2 / 3)
    assert set(r) == {"logistica", "mercado"}


def test_de_temporada_filtra_y_ordena_por_fecha():
    t = de_temporada(EJEMPLO, "2020/2021")
    assert len(t) == 2 and list(t["fecha"]) == sorted(t["fecha"])
    assert list(t["resultado"]) == ["D", "H"]  # el partido del 1 de agosto va antes que el del 2
    assert len(de_temporada(EJEMPLO, "2019/2020")) == 1 and de_temporada(EJEMPLO, "2030/2031").empty
    assert temporadas(EJEMPLO) == ["2019/2020", "2020/2021"]


def test_filtrar_aciertos_fallos_y_todos():
    assert FILTROS == ("Todos", "Aciertos", "Fallos")
    assert len(filtrar(EJEMPLO, "Todos")) == 3
    assert list(filtrar(EJEMPLO, "Aciertos")["resultado"]) == ["H", "A"]
    assert list(filtrar(EJEMPLO, "Fallos")["resultado"]) == ["D"]
    assert len(filtrar(EJEMPLO, "Aciertos")) + len(filtrar(EJEMPLO, "Fallos")) == len(EJEMPLO)
    with pytest.raises(ValueError):
        filtrar(EJEMPLO, "Otro")


def test_bloque_visible_muestra_de_a_bloque():
    df = pd.DataFrame({"x": range(55)})
    assert BLOQUE == 20 and len(bloque_visible(df, BLOQUE)) == 20 and len(bloque_visible(df, 2 * BLOQUE)) == 40
    assert len(bloque_visible(df, 100)) == 55 and list(bloque_visible(df, 3)["x"]) == [0, 1, 2]


def test_porcentajes_siempre_suman_100_en_los_2651_partidos():
    df = pd.read_csv(RUTA)
    for fila in df.to_dict("records"):
        p = porcentajes(fila)
        assert sum(p.values()) == 100 and set(p) == {"H", "D", "A"}
    assert porcentajes(dict(log_local=0.52, log_empate=0.27, log_visitante=0.21)) == {"H": 52, "D": 27, "A": 21}


def test_la_app_no_importa_xgboost_ni_los_scripts_offline():
    """Cloud solo instala requirements.txt: nada de lo que carga la app puede depender de xgboost, matplotlib ni de los
    scripts que los usan (evaluacion, entrenar, calibracion, exportadores)."""
    prohibidos = ("xgboost", "matplotlib", "src.entrenar", "src.evaluacion", "src.calibracion", "src.exportar_calibracion",
                  "src.exportar_predicciones")
    archivos = [RAIZ / "app.py", *sorted((RAIZ / "interfaz").glob("*.py")), *sorted((RAIZ / "paginas").glob("*.py")),
                RAIZ / "src" / "resumen_temporada.py", RAIZ / "src" / "resumen_calibracion.py",
                RAIZ / "src" / "grafica.py", RAIZ / "src" / "huella.py", RAIZ / "src" / "formato.py",
                RAIZ / "src" / "historial.py", RAIZ / "src" / "imagen.py", RAIZ / "src" / "equipos.py",
                RAIZ / "src" / "features.py", RAIZ / "src" / "prediccion.py", RAIZ / "src" / "explicacion.py"]
    for ruta in archivos:
        for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Import):
                nombres = [a.name for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nombres = [nodo.module or ""] + [f"{nodo.module}.{a.name}" for a in nodo.names]
            else:
                continue
            for n in nombres:
                assert not any(n == p or n.startswith(p + ".") for p in prohibidos), f"{ruta.name} importa {n}"
