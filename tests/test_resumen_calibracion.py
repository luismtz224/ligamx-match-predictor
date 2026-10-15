"""Textos de la gráfica de calibración (src/resumen_calibracion.py): salen del CSV, no están escritos a mano."""
from pathlib import Path

import pandas as pd
import pytest

from src.resumen_calibracion import (CLASE, conclusiones, filas_detalle, frase_n, pp, resumen, resumen_serie,
                                     serie, texto_aria)

RUTA = Path(__file__).resolve().parent.parent / "datos" / "procesados" / "calibracion.csv"


@pytest.fixture()
def tabla():
    return pd.read_csv(RUTA)


def _con(tabla, fuente, resultado, sobre):
    t = tabla.copy()
    t.loc[(t["fuente"] == fuente) & (t["resultado"] == resultado), "sobre_ruido"] = sobre
    return t


def test_pp_en_puntos_porcentuales():
    assert pp(0.0324) == "3.2" and pp(0.0108) == "1.1" and pp(0.5, 0) == "50"


def test_resumen_trae_los_numeros_del_csv(tabla):
    r = resumen(tabla, "mercado", "local")
    fila = serie(tabla, "mercado", "local").iloc[0]
    assert r["ece"] == pp(fila["ece"]) == "3.2" and r["sobre_ruido"] is True
    assert (r["ruido_lo"], r["ruido_hi"]) == (pp(fila["esperado_lo"]), pp(fila["esperado_hi"]))
    assert r["ns"] == list(serie(tabla, "mercado", "local")["n"]) and sum(r["ns"]) == r["n_total"] == 2651
    assert resumen(tabla, "logistica", "visitante")["sobre_ruido"] is False


def test_resumen_serie_dice_si_esta_dentro_o_por_encima_del_ruido(tabla):
    assert "por encima del ruido esperado" in resumen_serie(resumen(tabla, "mercado", "local"))
    assert "dentro del ruido esperado" in resumen_serie(resumen(tabla, "logistica", "local"))
    assert "(0.9 a 2.9 puntos)" in resumen_serie(resumen(tabla, "logistica", "local"))


def test_frase_n_explica_n_y_da_el_tamano_real_de_los_grupos(tabla):
    f = frase_n(tabla)
    assert "n es cuántos partidos son" in f and "pura suerte" in f and "barra de incertidumbre" in f
    assert "unos 441 a 442 partidos" in f
    parejo = tabla.copy()
    parejo["n"] = 400
    assert "unos 400 partidos" in frase_n(parejo)


def test_la_conclusion_honesta_con_los_datos_reales(tabla):
    """La logística no muestra descalibración en local ni visitante; el mercado sí en «gana local» (hipótesis)."""
    log, mer, cierre = conclusiones(tabla)
    assert "regresión logística no muestra descalibración ni en «gana local» ni en «gana visitante»" in log
    assert "queda descalibrado en «gana local»" in mer and "En «gana visitante» queda dentro del ruido" in mer
    assert "conversión de momios" in mer and "Probablemente la conversión influya" in mer
    assert "es una hipótesis, no un hecho" in mer  # no se afirma como hecho
    assert "no prueba que algo esté perfectamente calibrado" in cierre and "2,651 partidos" in cierre


def test_la_conclusion_sigue_a_las_banderas_del_csv(tabla):
    # si el mercado dejara de estar por encima del ruido, ya no se dice que está descalibrado
    sin = conclusiones(_con(tabla, "mercado", "local", False))[1]
    assert "no muestra descalibración ni en «gana local» ni en «gana visitante»" in sin and "hipótesis" not in sin
    # si la logística se saliera del ruido en local, se dice
    assert "queda descalibrada en «gana local»" in conclusiones(_con(tabla, "logistica", "local", True))[0]
    both = _con(_con(tabla, "logistica", "local", True), "logistica", "visitante", True)
    assert "«gana local» y «gana visitante»" in conclusiones(both)[0]
    # el mercado en los dos resultados
    ambos = _con(tabla, "mercado", "visitante", True)
    assert "descalibrado en «gana local» y «gana visitante»" in conclusiones(ambos)[1]
    assert "queda dentro del ruido" not in conclusiones(ambos)[1]


def test_filas_detalle_y_clases(tabla):
    filas = filas_detalle(tabla, "logistica", "local")
    assert len(filas) == 6 and filas[0]["n"] == 442 and filas[0]["pred"] == "25.7%" and filas[0]["freq"] == "26.0%"
    assert filas[0]["lo"] == "22.1%" and filas[0]["hi"] == "30.3%"
    assert CLASE == {"logistica": "l", "mercado": "m"}


def test_texto_aria_describe_ejes_series_y_numeros(tabla):
    t = texto_aria(tabla, "local")
    for pedazo in ("Gana local", "eje horizontal", "eje vertical", "diagonal", "Regresión logística: 6 grupos de 441 a 442",
                   "Mercado (momios): 6 grupos", "error promedio (ECE) de 3.2 puntos, por encima del ruido"):
        assert pedazo in t, pedazo
