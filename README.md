# ⚽ ligamx-match-predictor

![Dashboard](docs/app.png)

Realicé este modelo que calcula la probabilidad de los resultados de los partidos de la Liga MX y lo comparé con los pronósticos de las casas de apuestas para ver qué tan bueno es en realidad.

**Demo:** [ligamx.streamlit.app](https://ligamx.streamlit.app)

## Resultado

Probé el modelo en 8 temporadas (de la 2018/19 a la 2025/26, con 2,651 partidos en total). Es mejor que adivinar a ciegas, aunque los momios de las casas de apuestas siguen siendo más efectivos. Agregarle mis datos a los momios tampoco ayuda: de hecho, los empeora un poco.

Log loss (pérdida logarítmica):

| Modelo | Log loss | Accuracy |
|---|---|---|
| Momios (casas de apuestas) | 1.0037 | 50.85% |
| Regresión logística (mi modelo) | 1.0281 | 49.30% |
| XGBoost | 1.0474 | 47.98% |
| Sin modelo (siempre el mismo porcentaje) | 1.0670 | 45.61% |

> La fila "Sin modelo" dice siempre los mismos porcentajes en todos los partidos (los promedios históricos de local, empate y visitante). Sirve de piso: si un modelo no le gana a eso, no aprendió nada.

El log loss es básicamente la calificación de mi modelo: entre más bajo, mejor. Si el modelo dice 90% y falla, el castigo es grande y el log loss sube mucho; si dice 50% y falla, el castigo es mucho menor porque el error es leve.

## Aprendizajes y limitaciones

- El modelo sencillo de regresión logística le ganó al complicado XGBoost: quedó mejor en 6 de las 8 temporadas. Mi teoría es que fue por lo aleatorio que pueden llegar a ser los partidos de fútbol, ya que influye mucho la suerte, combinado con los pocos partidos que hay para entrenar al modelo.
- Los momios probablemente incluyen datos de lesiones, alineaciones, goles esperados (xG), tácticas, criterios arbitrales, condiciones climáticas, qué tanto se juegan los equipos, etc. Probablemente por eso este modelo no es tan efectivo como las casas de apuestas, ya que solo usa goles y puntos.
- Probar un modelo en una sola temporada puede engañar por la suerte que hay en el fútbol, por eso lo probé en 8 temporadas.

> __Es un proyecto educativo, no una recomendación de apuestas.__

## Cómo funciona

- **Elo:** cada equipo empieza en 1500 y sube o baja según gana o pierde, como en ajedrez. Ganarle a uno fuerte da más puntos.
- **Forma reciente:** puntos y goles de los últimos 5 partidos de cada equipo.
- **Sin ver el futuro:** para predecir cada temporada, el modelo solo se entrena con las anteriores. Hay pruebas automáticas que verifican que no se cuele información del futuro.

## Cómo correrlo

```bash
git clone https://github.com/luismtz224/ligamx-match-predictor.git
cd ligamx-match-predictor
python -m venv .venv
source .venv/Scripts/activate   # Windows con Git Bash. En Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Para reentrenar el modelo, correr la evaluación y las pruebas:

```bash
pip install -r requirements-dev.txt
python -m src.entrenar
python -m src.evaluacion
python -m pytest -q
```

## Más detalle

Los intervalos de confianza, la calibración de probabilidades y la metodología completa están en [docs/metodologia.md](docs/metodologia.md).

## Stack

Python, pandas, scikit-learn, XGBoost, Streamlit.

## Autor

Luis Fernando Martínez ([@luismtz224](https://github.com/luismtz224)). Licencia MIT.
