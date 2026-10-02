"""HTML de los componentes de DISENO.md. Funciones puras (sin Streamlit) que devuelven una
sola línea de HTML: sin sangría ni saltos de línea, porque Markdown convierte eso en código.
Todo texto que viene de datos pasa por html.escape."""
from html import escape

AVISO_ESCUDOS = ("Los escudos son propiedad de sus respectivos clubes y se usan con fines "
                 "ilustrativos, sin fines de lucro.")
AVISO_EDUCATIVO = "Proyecto educativo, no es recomendación de apuestas."

# nombre en MEX.csv -> sufijo de --team-<slug> en estilos/custom.css
SLUG = {
    "Atl. San Luis": "san-luis", "Atlante": "atlante", "Atlas": "atlas", "Chiapas": "chiapas",
    "Club America": "america", "Club Leon": "leon", "Club Tijuana": "tijuana",
    "Cruz Azul": "cruz-azul", "Dorados de Sinaloa": "dorados", "Guadalajara Chivas": "chivas",
    "Juarez": "juarez", "Leones Negros": "leones-negros", "Lobos BUAP": "lobos-buap",
    "Mazatlan FC": "mazatlan", "Monarcas": "monarcas", "Monterrey": "monterrey",
    "Necaxa": "necaxa", "Pachuca": "pachuca", "Puebla": "puebla", "Queretaro": "queretaro",
    "Santos Laguna": "santos", "Tigres UANL": "tigres", "Toluca": "toluca",
    "UNAM Pumas": "pumas", "Veracruz": "veracruz",
}
# escudos que se pierden sobre fondo oscuro
HALO = {"Atlas", "Lobos BUAP"}

# Resultados walk-forward (8 folds, 2,651 partidos). Los mismos que mostraba la app y que
# están en el README; tests/test_interfaz.py los compara contra él.
RESULTADOS_MODELOS = [
    ("Mercado", "1.0037", "50.85%"),
    ("Logística + momios", "1.0115", "50.74%"),
    ("Logística", "1.0281", "49.30%"),
    ("XGBoost", "1.0474", "47.98%"),
    ("Frecuencias", "1.0670", "45.61%"),
]


def color_equipo(equipo):
    """Valor CSS del color de acento del equipo (cae al acento de la app si no se conoce).

    --team-chiapas tiene contraste 3.0 contra la superficie: solo para barras, bordes y
    cifras grandes, nunca para texto chico.
    """
    slug = SLUG.get(equipo)
    return f"var(--team-{slug})" if slug else "var(--accent)"


def escudo(b64, px, halo=False, alt=""):
    """Escudo en base64 dentro de un círculo. Sin imagen: el círculo vacío `lm-crest`.
    `alt` es el nombre mostrado del equipo."""
    if not b64:
        return f'<span class="lm-crest" style="--s:{int(px)}px"></span>'
    clase = "lm-crest has-img halo" if halo else "lm-crest has-img"
    return (f'<span class="{clase}" style="--s:{int(px)}px">'
            f'<img src="data:image/png;base64,{b64}" alt="{escape(alt)}"></span>')


def titulo(texto, grad=None):
    """h1 alineado a la izquierda; `grad` (subcadena de `texto`) lleva el degradado."""
    t = escape(texto)
    if grad and grad in texto:
        g = escape(grad)
        t = t.replace(g, f'<span class="lm-grad-text">{g}</span>', 1)
    return f'<h1 class="lm-h1">{t}</h1>'


def encabezado(texto):
    return f'<div class="lm-section"><h2>{escape(texto)}</h2></div>'


def aviso(texto, suave=False):
    t = escape(texto)
    if suave:
        return f'<div class="lm-notice soft">{t}</div>'
    return f'<div class="lm-notice"><b>{t}</b></div>'


def pie_escudos():
    return f'<div class="lm-footer">{escape(AVISO_ESCUDOS)}</div>'


def tarjeta_equipo(equipo, elo, escudo_html, seleccionada=False, nombre=None):
    """`equipo` es la llave (da el color); `nombre` es el texto a mostrar."""
    clase = "lm-team is-sel" if seleccionada else "lm-team"
    return (f'<div class="{clase}" style="--team:{color_equipo(equipo)}">{escudo_html}'
            f'<div><div style="font-weight:600">{escape(nombre or equipo)}</div>'
            f'<div class="lm-team__elo">Elo {elo:.0f}</div></div></div>')


def fila_ranking(pos, equipo, elo, pct, escudo_html, href=None, seleccionada=False, nombre=None):
    """Fila del ranking. `pct` es el Elo normalizado (0-100) para la barra; `equipo` es la
    llave (da el color) y `nombre` el texto a mostrar.
    Sin `href` no es clicable (clase is-static: sin efecto hover)."""
    clase = "lm-elo" + (" is-sel" if seleccionada else "") + ("" if href else " is-static")
    cuerpo = (f'<span class="lm-elo__n">{int(pos)}</span>{escudo_html}'
              f'<span style="font-weight:600">{escape(nombre or equipo)}</span>'
              f'<span class="lm-elo__v">{elo:.0f}</span>'
              f'<span class="lm-elo__bar"><i></i></span>')
    estilo = f'--team:{color_equipo(equipo)};--p:{pct:.1f}%'
    if href:
        return f'<a href="{escape(href)}" class="{clase}" style="{estilo}">{cuerpo}</a>'
    return f'<div class="{clase}" style="{estilo}">{cuerpo}</div>'


def lista_modelos(filas=RESULTADOS_MODELOS):
    """Resultados como lista (sin tabla ancha). La fila con menor log loss lleva `best`."""
    mejor = min(range(len(filas)), key=lambda i: float(filas[i][1]))
    h = ('<span class="h">Modelo</span><span class="h r">Log loss</span>'
         '<span class="h r">Accuracy</span>')
    out = []
    for i, (nombre, ll, acc) in enumerate(filas):
        c1, c2 = ('class="best"', 'class="r best"') if i == mejor else ("", 'class="r"')
        out.append(f'<span {c1}>{escape(nombre)}</span>'.replace("<span >", "<span>")
                   + f'<span {c2}>{escape(ll)}</span><span {c2}>{escape(acc)}</span>')
    return f'<div class="lm-model">{h}{"".join(out)}</div>'
