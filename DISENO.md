# Diseño del frontend · Dirección A · Noche

Referencia para implementar el frontend en Streamlit. El CSS está en `estilos/custom.css` (ya trae tokens y componentes). Solo CSS y HTML con `st.markdown(..., unsafe_allow_html=True)`, sin JavaScript propio.

## Cargar el CSS

```python
# interfaz/recursos.py
import streamlit as st
from src.huella import huella

@st.cache_resource
def _css(contenido: str) -> str:  # `contenido` = huella del archivo: es la llave de la caché
    return RUTA_CSS.read_text(encoding="utf-8")

def css() -> str:
    return _css(huella(RUTA_CSS))

def inyectar_css() -> None:
    st.markdown(f"<style>{css()}</style>", unsafe_allow_html=True)
```

Llamar `inyectar_css()` una vez por página, al inicio. Si `st.navigation` repinta, llamarlo en `app.py` antes de `pg.run()`.

**Cachés y despliegues.** En Cloud un `git push` recarga el código de las páginas pero no vacía `st.cache_resource` ni `st.cache_data`: con `css()` sin argumentos se veía HTML nuevo con CSS viejo. Toda función cacheada que lea un archivo (CSS, `modelo.joblib`, los CSV, los escudos, la fuente) recibe como argumento la huella del archivo (`src.huella.huella`, hash del contenido; el argumento no debe llevar guion bajo porque esos no entran a la llave). Lo hacen `css`, `colores_css`, `modelo`, `partidos`, `equipos`, `rivalidades`, `escudo_b64`, la fuente del PNG y `_png` (su llave es `huella_png`: modelo, partidos, CSS, fichas, escudos y fuente). Una prueba (`tests/test_cache_archivos.py`) recorre el código y falla si una función con `@st.cache_*` no recibe `contenido` o `recursos`. No se cubre `.streamlit/config.toml` (lo lee Streamlit al arrancar: requiere reinicio de la app).

## Reglas

- Mobile-first (390 px), después escritorio (1280 px). Sin tablas anchas ni scroll horizontal de página.
- Todo margen, relleno y hueco es múltiplo de 8. Objetivo táctil de 48 px.
- Alinear a la izquierda; el hero nunca va centrado.
- Padding superior del contenido: 64 px en móvil y en escritorio. La barra fija de Streamlit (», y en Cloud Fork, GitHub y el menú) mide 60 px y no se oculta; con 40 px, a 390 px quedaba pegada a la etiqueta «Local».
- Las cifras son texto real, nunca un contador CSS ni `@property`. Streamlit reutiliza el nodo y solo cambia el atributo `style`: una animación cuyo valor final dependa de una variable CSS que cambia con el elemento ya montado puede quedarse con el valor viejo en Safari. Las animaciones usan valores fijos en sus keyframes (`lm-grow`, `lm-rise`, `lm-draw`) y lo que varía (`--w`, `--p`) va en propiedades normales.
- Una palabra del título del Predictor lleva `class="lm-grad-text"`.
- Cifras que se comparan con `font-variant-numeric: tabular-nums` (ya está en las clases).
- Usar `team-<club>` (colores listos para fondo oscuro), nunca el color crudo del escudo. Si los dos equipos son del mismo tono, el visitante usa su `-2`.
- Colores de equipo disponibles solo para 18 clubes. Faltan Chiapas, Dorados, Leones Negros, Lobos BUAP, Mazatlán, Monarcas y Veracruz: usar el primer color de `datos/equipos.csv` con contraste ≥ 3:1 contra `--surface` y definirlo en el CSS como `--team-<slug>`.
- Escudos dentro de HTML: `<img>` en base64 (cacheado). Si falta el archivo, círculo vacío `lm-crest`. Atlas y Lobos BUAP llevan `halo` (se pierden en fondo oscuro): resplandor claro discreto, alpha .45 y radio 60 % (`.lm-crest.halo` en el CSS y `_halo` en `src/imagen.py`, mismos valores).
- Avisos obligatorios: «Proyecto educativo, no es recomendación de apuestas» (Predictor y Sobre el modelo) y, al pie de toda pantalla con escudos: «Los escudos son propiedad de sus respectivos clubes y se usan con fines ilustrativos, sin fines de lucro.»
- En «Por qué da este resultado»: «Es la lectura del modelo, no una causa real.»
- No mostrar datos inventados: los previews del design system traen datos de ejemplo (por ejemplo «Estadio Banorte», «41 títulos», el 17-15-11). Todo sale de los CSV y del modelo.
- HTML sin sangría ni líneas en blanco dentro de un bloque: Markdown convierte 4 espacios en bloque de código.
- Escapar con `html.escape` todo texto que venga de datos.
- Animaciones solo CSS; `prefers-reduced-motion` ya las apaga (también el desplazamiento al pasar el mouse sobre tarjetas y filas, y la línea de la gráfica queda dibujada).
- Los colores del equipo visten la página del equipo; no son un dato de la ficha (sin muestras ni hex). Ver «Colores del equipo como diseño».

## Marcado de cada componente

Probabilidad (3 en una fila; `is-top` solo en la más probable; porcentajes enteros que suman 100):
```html
<div class="lm-cards">
  <div class="lm-pcard is-top" style="--team:var(--team-america);animation-delay:0ms">
    <div class="lm-pcard__tag">Local</div>
    <span class="lm-crest has-img" style="--s:40px"><img src="data:image/png;base64,..." alt=""></span>
    <div class="lm-pcard__name">Club America</div>
    <div class="lm-pcard__pct"><span class="lm-pct">44%</span></div>
  </div>
  <!-- Empate: sin --team; en vez del escudo -->
  <span style="width:40px;height:40px;display:flex;align-items:center;justify-content:center"><i style="width:24px;height:4px;border-radius:2px;background:var(--draw)"></i></span>
</div>
```

El porcentaje de la tarjeta es **texto real** en el HTML: siempre es el valor correcto en el DOM y lo lee un lector de pantalla. No se usa un contador CSS (`@property` + `counter()`): en Safari las tarjetas no se actualizaban al cambiar de equipo, mientras la barra y la leyenda sí.

Barra apilada (`--w` = porcentaje sin redondear, `--c` = color):
```html
<div class="lm-stackbar" role="img" aria-label="Local 44%, empate 29%, visitante 27%">
  <i style="--w:43.7;--c:var(--team-america)"></i><i style="--w:29.4;--c:var(--draw)"></i><i style="--w:26.9;--c:var(--team-cruz-azul)"></i>
</div>
<div class="lm-legend"><span style="--c:var(--team-america)">Local <b>44%</b></span><span style="--c:var(--draw)">Empate <b>29%</b></span><span style="--c:var(--team-cruz-azul)">Visitante <b>27%</b></span></div>
```

Forma (más reciente a la derecha, con `is-latest`; `sm` para los últimos 10):
```html
<div class="lm-form"><span class="lm-dot v">V</span><span class="lm-dot e">E</span><span class="lm-dot d">D</span><span class="lm-dot v is-latest">V</span></div>
```

Historial (H2H):
```html
<div class="lm-h2h">
  <div class="lm-h2h__nums"><div><b style="color:var(--team-america)">17</b><span>Gana Club America</span></div><div><b style="color:var(--ink-muted)">15</b><span>Empates</span></div><div><b style="color:var(--team-cruz-azul)">11</b><span>Gana Cruz Azul</span></div></div>
  <p class="lm-muted" style="margin:8px 0 16px;font-size:14px">43 duelos desde 2012</p>
  <div class="lm-duel"><div>13 sep 2026<small>Local: Cruz Azul</small></div><b>4 – 3</b></div>
</div>
```

Factor (centro = neutro; `visita` crece a la izquierda, `local` a la derecha; `--p` entre 0 y 1 normalizado al factor más grande):
```html
<div class="lm-factor"><div class="lm-factor__head"><span>Elo</span><b>0.08 · Visitante</b></div>
  <div class="lm-factor__track"><i class="lm-factor__fill visita" style="--p:0.48;--c:var(--team-cruz-azul)"></i></div></div>
<div class="lm-factor__ends"><span>← Empuja a Visitante</span><span>Empuja a Local →</span></div>
```

Modelo contra mercado (un decimal, diferencias en pp con signo «−» y «+»):
```html
<div class="lm-odds">
  <div class="lm-odds__r h"><span>Resultado</span><span>Modelo</span><span>Mercado</span><span>Dif.</span></div>
  <div class="lm-odds__r"><span>Gana Club America</span><span>43.7%</span><span>45.9%</span><span class="lm-odds__d">−2.2 pp</span></div>
</div>
```

Fila de ranking (`--p` = Elo normalizado en %):
```html
<a href="?equipo=club-america" class="lm-elo" style="--team:var(--team-america);--p:83.7%">
  <span class="lm-elo__n">3</span><span class="lm-crest has-img" style="--s:32px"><img src="..." alt=""></span>
  <span style="font-weight:600">Club America</span><span class="lm-elo__v">1643</span><span class="lm-elo__bar"><i></i></span>
</a>
```

Tarjeta de equipo (`is-sel` la resalta): `<div class="lm-team" style="--team:var(--team-toluca)"><span class="lm-crest" style="--s:48px"></span><div><div style="font-weight:600">Toluca</div><div class="lm-team__elo">Elo 1644</div></div></div>`

Récord y ficha: `.lm-record` con `<dl>`; ficha del club con `<dl class="lm-facts"><div><dt>Estadio</dt><dd>…</dd></div></dl>`.

Avisos: `<div class="lm-notice"><b>…</b></div>` y `<div class="lm-notice soft">…</div>`.

Resultados del modelo como lista (sin tabla): `.lm-model` con `<span class="h">`, `<span class="h r">`, y `best` en la mejor fila. Las cifras salen de las tablas reales de `src/`, no de los ejemplos.

Gráfica de Elo: SVG en `st.markdown` con `<svg class="lm-spark" viewBox="0 0 W H" style="--team:var(--team-x)"><path class="gr" …/><path class="ar" …/><path class="ln" pathLength="1" …/></svg>`; selector de temporada con `st.pills`.

Botón de descarga: `st.download_button` (ya está estilizado).

## Colores del equipo como diseño

La página de un equipo (`paginas/equipo.py`) se viste con sus colores, sin JavaScript:

1. `interfaz.componentes.estilo_equipo(equipo)` devuelve un `<style>` de una línea que define `--page-team` (su color) y `--page-team-2` (su `-2`; si no existe, el mismo color) sobre `.stApp`. Va al final de la página: no deja hueco arriba y desaparece al cambiar de página. Solo recibe llaves conocidas (`SLUG`), nunca texto libre.
2. Las reglas que los usan viven en `estilos/custom.css` (bloque «Colores del equipo como diseño») y se activan con `.stApp:has(.lm-hero)`: el héroe solo existe en esa página. Sin `:has()` (navegadores muy viejos) la página queda en Noche, sin tinte.
3. Qué se tiñe:
   - Fondo: degradado de `--page-team` (≤ 20 %) y `--page-team-2` (≤ 12 %) mezclados con `--bg`, más un resplandor en la esquina (≤ 18 %). Sigue siendo Noche. `--page-k` (1; `.5` en Lobos BUAP y Mazatlán, que son blancos y teñirían de gris neutro) escala la intensidad.
   - Héroe: borde del color y brillo (`box-shadow`).
   - Títulos de sección: barra de 4 px a la izquierda; el texto sigue en `--ink`.
   - Tarjetas del Ranking y de la rejilla de entrada: borde y brillo al pasar el mouse (`--team` de cada tarjeta); con `prefers-reduced-motion` no se desplazan.
4. Reglas: el texto siempre va en `--ink` o `--ink-muted`; el color del equipo nunca pinta texto chico (Chiapas tiene contraste 3.0: solo barras, bordes y brillos; la cifra grande del Elo usa `--team-chiapas-claro`, `#3aa786`: mismo matiz y luminosidad .44, con 6.4:1 contra `--surface`, 6.8:1 contra `--bg` y 5.9:1 contra el tinte más claro; `componentes.color_cifra`, solo para cifras grandes). Una prueba mezcla cada uno de los 25 colores con `--bg` y comprueba contraste ≥ 7:1 para `--ink` y ≥ 4.5:1 para `--ink-muted` sobre lo más claro del degradado.
5. Selectores frágiles: `.stApp` (clase usada desde la Fase 3), los hooks documentados `st-key-*` y `[data-testid="stAppViewContainer"]`, que el CSS ya usaba para el fondo: tiene fondo opaco `!important` y tapa el `::before` de `.stApp`, así que el degradado va directo en él. Se verifica en las capturas al actualizar Streamlit. `:has()` y `color-mix()` requieren navegadores de 2023 en adelante.

## Equipos: rejilla y página oculta

- `paginas/equipos.py` es la entrada: título corto y la rejilla de 25 tarjetas (**sin selector**: la rejilla es el selector). `/equipos?equipo=<slug>` **redirige** con `st.switch_page` a `paginas/equipo.py`; sin parámetro o con un slug inválido muestra la rejilla y limpia la URL. Los enlaces del Ranking siguen yendo a `?equipo=<slug>`.
- `paginas/equipo.py` es una `st.Page(..., url_path="equipo", visibility="hidden")`: arriba «← Todos los equipos», el selector, la página del equipo y, al final, otro «← Todos los equipos» (`st-key-volver` y `st-key-volver-abajo`, 48 px de alto). **No lleva rejilla**: se quitó porque al tocar otra tarjeta desde el final de la página no se abría desde arriba (reportado en el dispositivo de Luis). Cambiar de equipo es con el selector, que ya está arriba, o volviendo a la rejilla con cualquiera de los dos enlaces. Sin equipo o con slug inválido vuelve a la rejilla.
- Enlace «← Todos los equipos» (arriba y abajo): 16 px como mínimo (el `a` y todo lo que lleva dentro: Streamlit pinta el texto de `page_link` más chico por defecto, por eso la regla incluye `a *`) y 48 × 48 px de área táctil (`--tap`).
- Ficha: los valores de más de 24 caracteres (`componentes.FACT_LARGO`: palmarés, estadio, ciudad...) llevan `class="largo"`. A 599 px o menos van en columna, con la etiqueta arriba y el texto abajo alineado a la izquierda; en escritorio quedan en fila (etiqueta a la izquierda, valor a la derecha). Los valores cortos (siglas, apodo, fundación) siempre van en fila.
- **Por qué dos páginas:** al cambiar solo los query params de una misma página, el navegador mantiene anclado el viewport a la tarjeta tocada (cuando la página del equipo llevaba la rejilla al final, esa tarjeta quedaba abajo) y se cae al fondo; con `overflow-anchor: none` el scroll se queda donde estaba. Streamlit solo reinicia el scroll a 0 al cambiar de *página* (medido). Cada tarjeta enlaza a Equipos y este redirige: el cambio de página abre el equipo desde arriba sin JavaScript.
- Cada tarjeta y fila: `st.container(key="tarjeta-<slug>" / "fila-<slug>")` con el HTML y un `st.page_link` transparente encima (`st-key-*` y la etiqueta `a`).
- **El overlay debe cubrir toda la tarjeta o fila.** Streamlit pone `position: relative` y `margin: -6px` (arriba y abajo) al contenedor (`stElementContainer`) del `page_link`, que mide 16 × 0 px. Ese contenedor era el bloque contenedor del overlay `inset: 0`: el enlace medía 16 × 0 px, el clic caía en el texto y solo lo seleccionaba (se vio en producción). Con solo `position: static` quedaban sin enlace las esquinas de abajo (−12 px de márgenes). En `custom.css` el contenedor del enlace es `position: static; margin: 0`, el `a` lleva `margin: 0` (Streamlit le pone 2 px) y tarjetas y filas llevan `user-select: none`. Se prueba con clics de ratón reales (`tests/test_clic_real.py`: `document.elementFromPoint` en 7 puntos y un clic real en la esquina inferior, a 390 y 1280 px), no con `element.click()`, que ignora la geometría.
- Costo conocido: dentro de un equipo el menú lateral no resalta «Equipos» (la página oculta no está en la lista).

## Streamlit: qué es frágil

- Selectores `[data-testid]` y `[data-baseweb]` del bloque «Adaptación a Streamlit» del CSS cambian entre versiones. Probar al actualizar.
- Barra de navegación inferior fija en celular: no se hace. `st.navigation` en barra lateral (menú en celular).
- Selector de equipo: el escudo va al lado, no dentro de la opción.
- Un overlay `position: absolute` dentro de un elemento de Streamlit depende del contenedor posicionado más cercano, y los contenedores de elemento traen `position: relative` y márgenes negativos: medir con `getBoundingClientRect` y `document.elementFromPoint`.
- En Streamlit 1.64 no existe `[data-baseweb="select"]` en el DOM del selectbox (las reglas del CSS que lo usan no empatan); para automatizarlo, `role="combobox"`.
- `st.page_link` a la misma página no actualiza la URL del navegador (solo los query params del servidor): por eso la navegación entre equipos pasa por un cambio de página.
- Streamlit resta 16 px (`margin-bottom: -1rem`) al contenedor de markdown: en tarjetas y filas con enlace se anula en `custom.css`.
- La barra del ranking con color por equipo no existe como columna: se pinta la lista en HTML.
- Sin cursor propio, botones magnéticos, parallax ni scroll suave (requieren JavaScript).
- Las animaciones se repiten en cada recarga por cambio de selector; no animar bloques grandes que no cambian.

## `.streamlit/config.toml`

```toml
[theme]
base = "dark"
primaryColor = "#2dd4bf"
backgroundColor = "#07070d"
secondaryBackgroundColor = "#0f0f1a"
textColor = "#f5f5fa"
```
