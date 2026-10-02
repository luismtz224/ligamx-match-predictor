# Diseño del frontend · Dirección A · Noche

Referencia para implementar el frontend en Streamlit. El CSS está en `estilos/custom.css` (ya trae tokens y componentes). Solo CSS y HTML con `st.markdown(..., unsafe_allow_html=True)`, sin JavaScript propio.

## Cargar el CSS

```python
# interfaz/recursos.py
from pathlib import Path
import streamlit as st

@st.cache_resource
def css() -> str:
    return (Path(__file__).resolve().parent.parent / "estilos" / "custom.css").read_text(encoding="utf-8")

def inyectar_css() -> None:
    st.markdown(f"<style>{css()}</style>", unsafe_allow_html=True)
```

Llamar `inyectar_css()` una vez por página, al inicio. Si `st.navigation` repinta, llamarlo en `app.py` antes de `pg.run()`.

## Reglas

- Mobile-first (390 px), después escritorio (1280 px). Sin tablas anchas ni scroll horizontal de página.
- Todo margen, relleno y hueco es múltiplo de 8. Objetivo táctil de 48 px.
- Alinear a la izquierda; el hero nunca va centrado.
- Una palabra del título del Predictor lleva `class="lm-grad-text"`.
- Cifras que se comparan con `font-variant-numeric: tabular-nums` (ya está en las clases).
- Usar `team-<club>` (colores listos para fondo oscuro), nunca el color crudo del escudo. Si los dos equipos son del mismo tono, el visitante usa su `-2`.
- Colores de equipo disponibles solo para 18 clubes. Faltan Chiapas, Dorados, Leones Negros, Lobos BUAP, Mazatlán, Monarcas y Veracruz: usar el primer color de `datos/equipos.csv` con contraste ≥ 3:1 contra `--surface` y definirlo en el CSS como `--team-<slug>`.
- Escudos dentro de HTML: `<img>` en base64 (cacheado). Si falta el archivo, círculo vacío `lm-crest`. Atlas y Lobos BUAP llevan `halo` (se pierden en fondo oscuro).
- Avisos obligatorios: «Proyecto educativo, no es recomendación de apuestas» (Predictor y Sobre el modelo) y, al pie de toda pantalla con escudos: «Los escudos son propiedad de sus respectivos clubes y se usan con fines ilustrativos, sin fines de lucro.»
- En «Por qué da este resultado»: «Es la lectura del modelo, no una causa real.»
- No mostrar datos inventados: los previews del design system traen datos de ejemplo (por ejemplo «Estadio Banorte», «41 títulos», el 17-15-11). Todo sale de los CSV y del modelo.
- HTML sin sangría ni líneas en blanco dentro de un bloque: Markdown convierte 4 espacios en bloque de código.
- Escapar con `html.escape` todo texto que venga de datos.
- Animaciones solo CSS; `prefers-reduced-motion` ya las apaga.

## Marcado de cada componente

Probabilidad (3 en una fila; `is-top` solo en la más probable; porcentajes enteros que suman 100):
```html
<div class="lm-cards">
  <div class="lm-pcard is-top" style="--team:var(--team-america);animation-delay:0ms">
    <div class="lm-pcard__tag">Local</div>
    <span class="lm-crest has-img" style="--s:40px"><img src="data:image/png;base64,..." alt=""></span>
    <div class="lm-pcard__name">Club America</div>
    <div class="lm-pcard__pct"><span class="lm-pct" style="--v:44" aria-label="44 por ciento"></span></div>
  </div>
  <!-- Empate: sin --team; en vez del escudo -->
  <span style="width:40px;height:40px;display:flex;align-items:center;justify-content:center"><i style="width:24px;height:4px;border-radius:2px;background:var(--draw)"></i></span>
</div>
```

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

## Streamlit: qué es frágil

- Selectores `[data-testid]` y `[data-baseweb]` del bloque «Adaptación a Streamlit» del CSS cambian entre versiones. Probar al actualizar.
- Barra de navegación inferior fija en celular: no se hace. `st.navigation` en barra lateral (menú en celular).
- Selector de equipo: el escudo va al lado, no dentro de la opción.
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
