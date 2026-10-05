"""HTML de los componentes de DISENO.md. Funciones puras (sin Streamlit) que devuelven una
sola línea de HTML: sin sangría ni saltos de línea, porque Markdown convierte eso en código.
Todo texto que viene de datos pasa por html.escape."""
from html import escape

from src.formato import con_signo, fecha_corta, mes_anio
from src.grafica import CAL_ALTO, CAL_ANCHO

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


# Chiapas (3.0:1 contra --surface) usa su variante clara solo para la cifra grande del Elo
COLOR_CIFRA = {"Chiapas": "var(--team-chiapas-claro)"}


def color_cifra(equipo):
    """Color de una cifra grande del equipo: su variante clara si el color de acento no alcanza
    contraste de texto (Chiapas); si no, el mismo `color_equipo`. Solo para cifras grandes."""
    return COLOR_CIFRA.get(equipo) or color_equipo(equipo)


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


def fila_ranking(pos, equipo, elo, pct, escudo_html, href=None, seleccionada=False, nombre=None,
                 enlazada=False):
    """Fila del ranking. `pct` es el Elo normalizado (0-100) para la barra; `equipo` es la
    llave (da el color) y `nombre` el texto a mostrar.
    Sin `href` no es clicable (clase is-static: sin efecto hover), salvo `enlazada=True`: la
    fila va dentro de un contenedor con un `st.page_link` encima y conserva el hover."""
    clase = "lm-elo" + (" is-sel" if seleccionada else "") + ("" if href or enlazada else " is-static")
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


# ===== Predictor =====
_ICONO_EMPATE = ('<span style="width:40px;height:40px;display:flex;align-items:center;'
                 'justify-content:center"><i style="width:24px;height:4px;border-radius:2px;'
                 'background:var(--draw)"></i></span>')


def elegido(escudo_html, nombre):
    """Escudo y nombre del equipo elegido, junto al selector (no dentro de la opción)."""
    return (f'<div class="lm-row" style="gap:8px;margin:8px 0 16px">{escudo_html}'
            f'<span style="font-weight:600">{escape(nombre)}</span></div>')


def tarjetas_probabilidad(pct, nombres, colores, escudos):
    """Tres tarjetas Local | Empate | Visitante. `pct` son enteros que suman 100.

    nombres, colores, escudos: (local, visitante). `is-top` va solo en la más probable
    (si hay empate en el máximo, en la primera).
    """
    top = max(range(3), key=lambda i: pct[i])
    datos = [("Local", colores[0], escudos[0], nombres[0]), ("Empate", None, _ICONO_EMPATE, ""),
             ("Visitante", colores[1], escudos[1], nombres[1])]
    out = []
    for i, (tag, color, icono, nombre) in enumerate(datos):
        clase = "lm-pcard is-top" if i == top else "lm-pcard"
        estilo = (f"--team:{color};" if color else "") + f"animation-delay:{i * 80}ms"
        v = int(pct[i])
        out.append(f'<div class="{clase}" style="{estilo}"><div class="lm-pcard__tag">{tag}</div>'
                   f'{icono}<div class="lm-pcard__name">{escape(nombre)}</div>'
                   f'<div class="lm-pcard__pct"><span class="lm-pct">{v}%</span></div></div>')
    return f'<div class="lm-cards">{"".join(out)}</div>'


def barra_apilada(probs, pct, colores):
    """Barra con los valores sin redondear (`probs`, 0-1) y leyenda con los enteros (`pct`).
    colores: (local, visitante); el empate usa --draw."""
    cs = (colores[0], "var(--draw)", colores[1])
    etiquetas = ("Local", "Empate", "Visitante")
    total = sum(probs)
    segs = "".join(f'<i style="--w:{100 * p / total:.1f};--c:{c}"></i>' for p, c in zip(probs, cs))
    leyenda = "".join(f'<span style="--c:{c}">{t} <b>{v}%</b></span>'
                      for t, v, c in zip(etiquetas, pct, cs))
    aria = f"Local {pct[0]}%, empate {pct[1]}%, visitante {pct[2]}%"
    return (f'<div class="lm-stackbar" role="img" aria-label="{aria}">{segs}</div>'
            f'<div class="lm-legend">{leyenda}</div>')


def forma(partidos, nombre, escudo_html, sm=False):
    """Últimos partidos como círculos V/E/D, el más reciente a la derecha.

    `partidos`: lista de dicts con resultado ('V'/'E'/'D'), fecha, rival, marcador y
    condicion ('Local'/'Visita'), del más viejo al más reciente. El detalle va en <details>
    (los tooltips no funcionan con el dedo); `title` queda para el mouse.
    """
    encabezado_ = (f'<div class="lm-row" style="gap:8px;margin-bottom:8px">{escudo_html}'
                   f'<span style="font-weight:600">{escape(nombre)}</span></div>')
    if not partidos:
        return (f'<div class="lm-forma">{encabezado_}'
                f'<p class="lm-muted" style="font-size:14px">Sin partidos registrados.</p></div>')
    clase = "lm-form sm" if sm else "lm-form"
    puntos, filas = [], []
    for i, p in enumerate(partidos):
        r = p["resultado"]
        extra = " is-latest" if i == len(partidos) - 1 else ""
        titulo_ = escape(f"{r} · vs {p['rival']} {p['marcador']} ({p['condicion'].lower()})")
        puntos.append(f'<span class="lm-dot {r.lower()}{extra}" title="{titulo_}">{escape(r)}</span>')
        filas.append(f'<div class="lm-duel"><div>{escape(p["fecha"])}<small>vs {escape(p["rival"])}'
                     f' · {escape(p["condicion"])}</small></div><b>{escape(p["marcador"])}</b></div>')
    filas.reverse()  # en el detalle, el más reciente arriba
    return (f'<div class="lm-forma">{encabezado_}'
            f'<details class="lm-detail"><summary><div class="{clase}">{"".join(puntos)}</div>'
            f'<span class="lm-detail__hint">Ver partidos</span></summary>'
            f'<div style="margin-top:8px">{"".join(filas)}</div></details></div>')


def h2h(nombres, colores, gep_local, duelos):
    """Historial entre los dos desde 2012. `gep_local`: (G, E, P) desde la óptica del local.
    `duelos`: lista de (fecha, nombre del local, goles local, goles visita), el más reciente primero."""
    g, e, p = gep_local
    n = g + e + p
    if n == 0:
        return aviso("Sin duelos entre estos equipos desde 2012.", suave=True)
    nums = (f'<div class="lm-h2h__nums"><div><b style="color:{colores[0]}">{g}</b>'
            f'<span>Gana {escape(nombres[0])}</span></div><div><b style="color:var(--ink-muted)">{e}</b>'
            f'<span>Empates</span></div><div><b style="color:{colores[1]}">{p}</b>'
            f'<span>Gana {escape(nombres[1])}</span></div></div>')
    texto_n = "1 duelo desde 2012" if n == 1 else f"{n} duelos desde 2012"
    filas = "".join(f'<div class="lm-duel"><div>{escape(f)}<small>Local: {escape(loc)}</small></div>'
                    f'<b>{int(gl)} – {int(gv)}</b></div>' for f, loc, gl, gv in duelos)
    return (f'<div class="lm-h2h">{nums}<p class="lm-muted" style="margin:8px 0 16px;font-size:14px">'
            f'{texto_n}</p>{filas}</div>')


def factores(lista, colores):
    """Barras de factor: centro neutro, visitante a la izquierda, local a la derecha.
    `lista`: [(nombre, valor)] con valor > 0 = empuja a local. colores: (local, visitante).
    `--p` se normaliza al factor de mayor magnitud."""
    mayor = max((abs(v) for _, v in lista), default=0) or 1
    out = []
    for nombre, v in lista:
        if v > 0:
            lado, cls, c = "Local", "local", colores[0]
        elif v < 0:
            lado, cls, c = "Visitante", "visita", colores[1]
        else:
            lado, cls, c = "Neutro", "", ""
        barra = (f'<i class="lm-factor__fill {cls}" style="--p:{abs(v) / mayor:.2f};--c:{c}"></i>'
                 if cls else "")
        out.append(f'<div class="lm-factor"><div class="lm-factor__head"><span>{escape(nombre)}</span>'
                   f'<b>{abs(v):.2f} · {lado}</b></div><div class="lm-factor__track">{barra}</div></div>')
    return (f'<div class="lm-stack" style="gap:16px">{"".join(out)}<div class="lm-factor__ends">'
            f'<span>← Empuja a Visitante</span><span>Empuja a Local →</span></div></div>')


def datos_modelo(nombres, filas):
    """Lista (sin tabla) de los datos de entrada: [(etiqueta, valor local, valor visitante)]."""
    dl = "".join(f'<dt>{escape(t)}</dt><dd>{escape(a)} · {escape(b)}</dd>' for t, a, b in filas)
    return (f'<div class="lm-record"><div class="lm-caption">{escape(nombres[0])} · '
            f'{escape(nombres[1])}</div><dl>{dl}</dl></div>')


def modelo_vs_mercado(filas):
    """`filas`: [(etiqueta, p_modelo, p_mercado)] con probabilidades 0-1. Un decimal; la
    diferencia en puntos porcentuales con signo."""
    h = ('<div class="lm-odds__r h"><span>Resultado</span><span>Modelo</span>'
         '<span>Mercado</span><span>Dif.</span></div>')
    out = []
    for etiqueta, pm, pk in filas:
        d = (pm - pk) * 100
        cls = " up" if d > 0 else " down" if d < 0 else ""
        out.append(f'<div class="lm-odds__r"><span>{escape(etiqueta)}</span><span>{100 * pm:.1f}%</span>'
                   f'<span>{100 * pk:.1f}%</span><span class="lm-odds__d{cls}">{con_signo(d)} pp</span></div>')
    return f'<div class="lm-odds">{h}{"".join(out)}</div>'


# ===== Equipos =====
def heroe(equipo, nombre, escudo_html):
    """Escudo grande con el nombre mostrado y borde del color del equipo."""
    return (f'<div class="lm-hero" style="--team:{color_equipo(equipo)}">{escudo_html}'
            f'<h1 class="lm-h1">{escape(nombre)}</h1></div>')


FACT_LARGO = 24  # caracteres: más que esto no cabe junto a la etiqueta a 390 px


def ficha(f):
    """Ficha del equipo (fila de equipos.csv). Los campos vacíos se omiten. Los colores del
    equipo no se muestran como dato: visten la página (`estilo_equipo`)."""
    campos = (("Siglas", f["siglas"]), ("Apodo", f["apodo"]), ("Ciudad", f["ciudad_estado"]),
              ("Estadio", f["estadio"]), ("Fundación", f["fundacion"]), ("Palmarés", f["palmares"]))
    # los valores largos (palmarés, estadio...) llevan `largo`: en celular van con la etiqueta arriba
    filas = "".join(f'<div{" class=\"largo\"" if len(v) > FACT_LARGO else ""}><dt>{escape(k)}</dt>'
                    f'<dd>{escape(v)}</dd></div>' for k, v in campos if v)
    return f'<div class="lm-record"><dl class="lm-facts">{filas}</dl></div>'


# equipos cuyo color es blanco: su tinte sería gris neutro, así que se atenúa a la mitad (--page-k)
BLANCOS = {"Lobos BUAP", "Mazatlan FC"}


def estilo_equipo(equipo):
    """<style> con los colores de la página del equipo (`--page-team` y `--page-team-2`) sobre
    `.stApp`. Sin JavaScript; desaparece al salir de la página. Las reglas que los usan viven en
    estilos/custom.css (`.stApp:has(.lm-hero)`). Sin -2 en el CSS, el segundo color es el primero.
    Los equipos de `BLANCOS` llevan además `--page-k:.5` (mitad de intensidad)."""
    slug = SLUG[equipo]  # solo slugs conocidos: nunca texto de datos dentro del <style>
    k = "--page-k:.5;" if equipo in BLANCOS else ""
    return (f'<style>.stApp{{--page-team:var(--team-{slug});'
            f'--page-team-2:var(--team-{slug}-2,var(--team-{slug}));{k}}}</style>')


def elo_actual(equipo, elo, activo, posicion=None, n_activos=None):
    """Cifra grande del Elo. Equipos sin partidos en la temporada actual: «Elo final»."""
    etiqueta = "Elo actual" if activo else "Elo final"
    pos = (f'<p class="lm-muted" style="margin:0">Posición {int(posicion)} de {int(n_activos)} activos</p>'
           if activo and posicion else "")
    return (f'<div class="lm-eloact"><div class="lm-caption">{etiqueta}</div>'
            f'<div class="lm-eloact__n" style="color:{color_cifra(equipo)}">{elo:,.0f}</div>{pos}</div>')


def resumen_elo(nombre, ext):
    """Texto de la gráfica (aria-label): inicio, final, máximo y mínimo con fechas."""
    (f0, e0), (f1, e1) = ext["inicio"], ext["final"]
    (fx, ex), (fn, en) = ext["maximo"], ext["minimo"]
    return (f"Elo de {nombre}: de {e0:,.0f} en {mes_anio(f0)} a {e1:,.0f} en {mes_anio(f1)}; "
            f"máximo {ex:,.0f} ({fecha_corta(fx)}); mínimo {en:,.0f} ({fecha_corta(fn)})")


def grafica_elo(equipo, nombre, geo, ext, etiqueta_final="Hoy"):
    """Gráfica del Elo a partir de `src.grafica.geometria` y `historial.extremos`.
    Sin geometría (sin partidos en el filtro): aviso. El resumen visible repite el aria-label."""
    if geo is None:
        return aviso("Sin partidos en esta temporada.", suave=True)
    marcas = "".join(f'<circle class="pt" cx="{p["x"]}" cy="{p["y"]}" r="5"></circle>'
                     for p in geo["puntos"])
    svg = (f'<svg class="lm-spark" style="--team:{color_equipo(equipo)}" viewBox="0 0 600 220" '
           f'role="img" aria-label="{escape(resumen_elo(nombre, ext))}">'
           f'<path class="gr" d="{geo["rejilla"]}"></path><path class="ar" d="{geo["area"]}"></path>'
           f'<path class="ln" pathLength="1" d="{geo["linea"]}"></path>{marcas}</svg>')
    items = (("Máximo", ext["maximo"]), ("Mínimo", ext["minimo"]), ("Inicio", ext["inicio"]),
             (etiqueta_final, ext["final"]))
    resumen = "".join(f'<div><dt>{escape(t)}</dt><dd>{e:,.0f}<small>{escape(fecha_corta(f))}</small></dd></div>'
                      for t, (f, e) in items)
    nota = ('<p class="lm-muted" style="margin:8px 0 0;font-size:14px">El trazo se corta donde el '
            'equipo no jugó (más de un año).</p>' if geo["cortes"] else "")
    return f'<div class="lm-chart">{svg}<dl class="lm-chartsum">{resumen}</dl>{nota}</div>'


def _num(x):
    return f"{x:.2f}" if x == x else "—"  # NaN (PJ = 0) -> raya


def record_equipo(rec):
    """Récord de local y de visitante (tabla de `historial.record`) en dos tarjetas."""
    tarjetas = []
    for lado, titulo_ in (("Local", "De local"), ("Visitante", "De visitante")):
        f = rec.loc[lado]
        dl = "".join(f'<dt>{escape(k)}</dt><dd>{escape(v)}</dd>' for k, v in (
            ("Partidos", str(int(f["PJ"]))), ("Ganados", str(int(f["G"]))),
            ("Empatados", str(int(f["E"]))), ("Perdidos", str(int(f["P"]))),
            ("GF/partido", _num(f["GF_pp"])), ("GC/partido", _num(f["GC_pp"]))))
        tarjetas.append(f'<div class="lm-record"><div class="lm-caption">{titulo_}</div><dl>{dl}</dl></div>')
    return (f'<div class="lm-twocol keep">{"".join(tarjetas)}</div>'
            '<p class="lm-muted" style="margin:8px 0 0;font-size:12px;line-height:16px">GF y GC: '
            'goles a favor y en contra por partido.</p>')


def racha_actual(rotulo, texto):
    return (f'<div class="lm-record" style="margin-bottom:16px"><div class="lm-caption">{escape(rotulo)}</div>'
            f'<div style="font-size:24px;line-height:32px;font-weight:600">{escape(texto)}</div></div>')


def _lista_rivales(titulo_, filas, vacio):
    if filas:
        cuerpo = "".join(
            f'<div class="lm-duel"><div class="lm-row" style="gap:8px">{f["escudo_html"]}<div>'
            f'{escape(f["nombre"])}<small>{f["ppp"]:.2f} pts/partido · {int(f["n"])} duelos · '
            f'{int(f["g"])}-{int(f["e"])}-{int(f["p"])}</small></div></div></div>' for f in filas)
    else:
        cuerpo = f'<p class="lm-muted" style="margin:0;font-size:14px">{escape(vacio)}</p>'
    return f'<div class="lm-record"><div class="lm-caption">{escape(titulo_)}</div>{cuerpo}</div>'


def rivales(mejores, peores):
    """«Le gana más» y «Le gana menos». Cada fila: dict con escudo_html, nombre, ppp, n, g, e, p.
    G-E-P desde la óptica del equipo. Si ambas listas están vacías, un solo aviso."""
    if not mejores and not peores:
        return aviso("Sin suficientes duelos (se piden al menos 6 por rival).", suave=True)
    return (f'<div class="lm-twocol">{_lista_rivales("Le gana más", mejores, "Sin suficientes duelos")}'
            f'{_lista_rivales("Le gana menos", peores, "Sin suficientes duelos")}</div>')


POCOS_DUELOS = 6


def clasicos(lista):
    """Clásicos del equipo. Cada uno: dict con nombre, escudo_html, rival (nombre mostrado), n,
    g, e, p y ultimo (texto o None). El número de duelos va siempre; con pocos, una nota."""
    if not lista:
        return aviso("Sin clásicos registrados.", suave=True)
    out = []
    for k in lista:
        n = int(k["n"])
        texto_n = "1 duelo desde 2012" if n == 1 else f"{n} duelos desde 2012"
        nota = ('<p class="lm-muted" style="margin:8px 0 0;font-size:14px">Pocos duelos: ojo con '
                'sacar conclusiones.</p>' if n < POCOS_DUELOS else "")
        ultimo = (f'<div class="lm-duel"><div>Último duelo<small>{escape(k["ultimo"])}</small></div></div>'
                  if k["ultimo"] else "")
        out.append(
            f'<div class="lm-record"><div class="lm-caption">{escape(k["nombre"])}</div>'
            f'<div class="lm-row" style="gap:8px">{k["escudo_html"]}<div><b>{escape(k["rival"])}</b>'
            f'<div class="lm-muted" style="font-size:14px">{texto_n} · G-E-P {int(k["g"])}-{int(k["e"])}-{int(k["p"])}'
            f'</div></div></div>{ultimo}{nota}</div>')
    return f'<div class="lm-twocol">{"".join(out)}</div>'


# ===== Gráfica de calibración =====
def leyenda_calibracion():
    """Qué es cada marca: forma y color (la forma distingue las series sin depender del color)."""
    def marca(clase, forma):
        return f'<svg class="cal-clave {clase}" viewBox="0 0 16 16" aria-hidden="true">{forma}</svg>'
    items = [(marca("l", '<circle cx="8" cy="8" r="5"></circle>'), "Regresión logística"),
             (marca("m", '<rect x="3" y="3" width="10" height="10"></rect>'), "Mercado (momios)"),
             (marca("d", '<path d="M1 15 L15 1"></path>'), "Calibración perfecta")]
    return ('<div class="lm-cal-leyenda">' + "".join(f"<span>{svg}{escape(t)}</span>" for svg, t in items) + "</div>")


def grafica_calibracion(titulo, geo, aria, resumenes, ayuda, detalle=""):
    """Un diagrama de confiabilidad. `geo` = src.grafica.geometria_calibracion; `aria` = descripción para lectores de
    pantalla; `resumenes` = [(nombre de la serie, clase, texto del resumen)] visible debajo; `ayuda` = el texto de
    los ejes; `detalle` = HTML del <details> con los números de cada punto. Cada punto lleva su n escrito (la de la logística a su izquierda, la del mercado a su derecha)."""
    ejes = "".join(f'<text class="cal-t {e["eje"]}" x="{e["x"]}" y="{e["y"]}">{escape(e["texto"])}</text>'
                   for e in geo["etiquetas"])
    capas = ""
    for nombre, clase, forma in (("logistica", "l", "circulo"), ("mercado", "m", "cuadrado")):
        serie = geo["series"].get(nombre)
        if not serie:
            continue
        marcas = ""
        for p in serie["puntos"]:
            if forma == "circulo":
                marcas += f'<circle class="cal-p {clase}" cx="{p["x"]}" cy="{p["y"]}" r="{p["r"]}"></circle>'
                x_n = round(p["x"] - p["r"] - 3, 1)  # la n de la logística, a la izquierda del punto
            else:
                marcas += (f'<rect class="cal-p {clase}" x="{round(p["x"] - p["r"], 1)}" y="{round(p["y"] - p["r"], 1)}" '
                           f'width="{round(2 * p["r"], 1)}" height="{round(2 * p["r"], 1)}"></rect>')
                x_n = round(p["x"] + p["r"] + 3, 1)  # la del mercado, a la derecha: no se encima con la otra serie
            marcas += f'<text class="cal-n {clase}" x="{x_n}" y="{round(p["y"] + 4, 1)}">{p["n"]}</text>'
        capas += f'<path class="cal-ic {clase}" d="{serie["ic"]}"></path>{marcas}'
    svg = (f'<svg class="lm-calsvg" viewBox="0 0 {CAL_ANCHO} {CAL_ALTO}" role="img" aria-label="{escape(aria)}">'
           f'<path class="gr" d="{geo["rejilla"]}"></path><path class="cal-diag" d="{geo["diagonal"]}"></path>'
           f'{ejes}{capas}</svg>')
    filas = "".join(f'<div><dt class="{escape(clase)}">{escape(nombre)}</dt><dd>{escape(texto)}</dd></div>'
                    for nombre, clase, texto in resumenes)
    return (f'<figure class="lm-cal"><div class="lm-caption">{escape(titulo)}</div>{svg}'
            f'<p class="lm-muted lm-cal-ayuda" style="margin:0;font-size:12px;line-height:16px">{escape(ayuda)}</p><dl class="lm-cal-res">{filas}</dl>{detalle}</figure>')


def detalle_calibracion(titulo, grupos):
    """Detalle de cada punto (n, predicha, real e intervalo) en un <details>, sin tabla ancha.
    `grupos` = [(nombre de la serie, clase, [dict n, pred, freq, lo, hi])] con porcentajes ya redondeados (texto)."""
    cuerpo = ""
    for nombre, clase, filas in grupos:
        lineas = "".join(
            f'<div class="lm-duel"><div>Grupo {i}<small>n = {escape(str(f["n"]))} partidos · dio {escape(f["pred"])} · '
            f'pasó {escape(f["freq"])} (entre {escape(f["lo"])} y {escape(f["hi"])})</small></div></div>'
            for i, f in enumerate(filas, start=1))
        cuerpo += f'<div class="lm-cal-grupo"><div class="lm-caption {escape(clase)}">{escape(nombre)}</div>{lineas}</div>'
    return (f'<details class="lm-detail lm-cal-detalle"><summary><span style="font-size:14px;line-height:24px;font-weight:600">{escape(titulo)}</span>'
            f'<span class="lm-detail__hint">Ver los números</span></summary>{cuerpo}</details>')
