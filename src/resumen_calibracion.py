"""Textos de la gráfica de calibración, calculados a partir de datos/procesados/calibracion.csv.

Sin Streamlit ni matplotlib (la app los importa). Las frases dependen de las banderas `sobre_ruido` del
CSV: si los datos cambian, la conclusión cambia con ellos (no hay una conclusión escrita a mano).
"""

NOMBRE_FUENTE = {"logistica": "Regresión logística", "mercado": "Mercado (momios)"}
NOMBRE_RESULTADO = {"local": "Gana local", "visitante": "Gana visitante"}
RESULTADOS = ("local", "visitante")
FUENTES = ("logistica", "mercado")


def pp(x, decimales=1):
    """0.0324 -> '3.2' (puntos porcentuales)."""
    return f"{x * 100:.{decimales}f}"


def serie(tabla, fuente, resultado):
    """Renglones de una serie, en orden de grupo."""
    s = tabla[(tabla["fuente"] == fuente) & (tabla["resultado"] == resultado)]
    return s.sort_values("grupo")


def resumen(tabla, fuente, resultado):
    """Números de una serie para el texto: ECE, ruido esperado, si lo supera y los n de cada grupo."""
    s = serie(tabla, fuente, resultado)
    p = s.iloc[0]
    return dict(fuente=fuente, resultado=resultado, ece=pp(p["ece"]), ruido_lo=pp(p["esperado_lo"]),
                ruido_hi=pp(p["esperado_hi"]), sobre_ruido=bool(p["sobre_ruido"]), ns=[int(n) for n in s["n"]],
                n_total=int(p["n_total"]))


def frase_n(tabla):
    """Qué es n y por qué importa, con el tamaño real de los grupos."""
    n = tabla["n"]
    tam = f"{int(n.min())}" if n.min() == n.max() else f"{int(n.min())} a {int(n.max())}"
    return (f"Cada punto agrupa los partidos en que el modelo dio una probabilidad parecida, y n es cuántos partidos "
            f"son. Con pocos partidos en un grupo, la frecuencia real salta por pura suerte (por eso cada punto lleva "
            f"su barra de incertidumbre): un punto lejos de la diagonal con n chico dice poco. Aquí cada grupo tiene "
            f"unos {tam} partidos.")


def resumen_serie(r):
    """Una línea de texto por serie: ECE y si cae dentro del ruido esperado."""
    lugar = "por encima del" if r["sobre_ruido"] else "dentro del"
    return (f"error promedio (ECE) de {r['ece']} puntos, {lugar} ruido esperado "
            f"({r['ruido_lo']} a {r['ruido_hi']} puntos)")


def _lista(resultados):
    nombres = [f"«{NOMBRE_RESULTADO[r].lower()}»" for r in resultados]
    return " y ".join(nombres)


def conclusiones(tabla):
    """Conclusión honesta como lista de frases, según las banderas del CSV."""
    marca = {(f, r): bool(serie(tabla, f, r).iloc[0]["sobre_ruido"]) for f in FUENTES for r in RESULTADOS}
    frases = []
    mal = [r for r in RESULTADOS if marca[("logistica", r)]]
    if not mal:
        frases.append("La regresión logística no muestra descalibración ni en «gana local» ni en «gana visitante»: su "
                      "error promedio queda dentro de lo que daría un modelo perfecto solo por ruido.")
    else:
        frases.append(f"La regresión logística queda descalibrada en {_lista(mal)}: su error promedio sale mayor que "
                      "el ruido esperado.")
    mal = [r for r in RESULTADOS if marca[("mercado", r)]]
    bien = [r for r in RESULTADOS if not marca[("mercado", r)]]
    if not mal:
        frases.append("Con esta conversión de momios (dividir cada momio entre la suma), el mercado no muestra "
                      "descalibración ni en «gana local» ni en «gana visitante».")
    else:
        resto = f" En {_lista(bien)} queda dentro del ruido." if bien else ""
        frases.append(f"Con esta conversión de momios (dividir cada momio entre la suma), el mercado queda descalibrado "
                      f"en {_lista(mal)}: su error promedio sale mayor que el ruido esperado.{resto} Probablemente la "
                      "conversión influya (los momios traen un margen de la casa que aquí se reparte parejo), pero no "
                      "lo medimos: es una hipótesis, no un hecho.")
    n_total = int(tabla["n_total"].iloc[0])
    frases.append(f"Estar dentro del ruido no prueba que algo esté perfectamente calibrado: con {n_total:,} partidos y "
                  "pocos grupos, una descalibración pequeña se confunde con la suerte.")
    return frases


def texto_aria(tabla, resultado):
    """Descripción de una gráfica para lectores de pantalla (aria-label)."""
    partes = [f"{NOMBRE_RESULTADO[resultado]}. Diagrama de calibración: eje horizontal, probabilidad que dio el modelo; "
              "eje vertical, frecuencia con que sí pasó; la diagonal es la calibración perfecta."]
    for f in FUENTES:
        r = resumen(tabla, f, resultado)
        n = r["ns"]
        partes.append(f"{NOMBRE_FUENTE[f]}: {len(n)} grupos de {min(n)} a {max(n)} partidos, {resumen_serie(r)}.")
    return " ".join(partes)


CLASE = {"logistica": "l", "mercado": "m"}  # clase CSS de cada serie (color y forma)


def filas_detalle(tabla, fuente, resultado):
    """Un dict de texto por grupo (n, lo que dio el modelo, lo que pasó y su intervalo), para el <details>."""
    return [dict(n=int(t.n), pred=f"{pp(t.pred)}%", freq=f"{pp(t.freq)}%", lo=f"{pp(t.wilson_lo)}%",
                 hi=f"{pp(t.wilson_hi)}%") for t in serie(tabla, fuente, resultado).itertuples()]
