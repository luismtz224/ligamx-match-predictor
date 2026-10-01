import joblib
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Liga MX Match Predictor", page_icon="⚽")


@st.cache_resource
def cargar():
    return joblib.load("modelos/modelo.joblib")


est = cargar()
modelo, cols, elo, hist, equipos = est["modelo"], est["cols"], est["elo"], est["hist"], est["activos"]


def forma(t):
    h = hist.get(t, [])
    return np.array(h).mean(axis=0) if h else np.array([np.nan] * 3)


st.title("⚽ Liga MX Match Predictor")
st.caption("Probabilidad de victoria local, empate o victoria visitante, con Elo y forma reciente.")

tab1, tab2, tab3 = st.tabs(["🔮 Predictor", "📊 Ranking Elo", "ℹ️ Sobre el modelo"])

with tab1:
    c1, c2 = st.columns(2)
    idx = equipos.index("Club America") if "Club America" in equipos else 0
    local = c1.selectbox("Local", equipos, index=idx)
    opciones = [e for e in equipos if e != local]
    idv = opciones.index("Cruz Azul") if "Cruz Azul" in opciones else 0
    visita = c2.selectbox("Visitante", opciones, index=idv)

    fl, fv = forma(local), forma(visita)
    x = pd.DataFrame([dict(elo_diff=elo[local] - elo[visita], elo_h=elo[local], elo_a=elo[visita],
                           pts_h=fl[0], pts_a=fv[0], gf_h=fl[1], gc_h=fl[2],
                           gf_a=fv[1], gc_a=fv[2])])[cols]
    pv, pe, pl = modelo.predict_proba(x)[0]   # orden del modelo: visitante, empate, local

    st.subheader("Probabilidades del modelo")
    for nombre, p in [(f"Gana {local}", pl), ("Empate", pe), (f"Gana {visita}", pv)]:
        st.write(f"**{nombre}**: {p:.1%}")
        st.progress(float(p))

    st.subheader("Comparativa de equipos")
    comp = pd.DataFrame(
        {local: [elo[local], fl[0], fl[1], fl[2]], visita: [elo[visita], fv[0], fv[1], fv[2]]},
        index=["Elo", "Puntos/partido (últ. 5)", "Goles a favor (últ. 5)", "Goles en contra (últ. 5)"])
    st.dataframe(comp.style.format("{:.2f}"))

    with st.expander("Comparar con los momios (opcional)"):
        m1, m2, m3 = st.columns(3)
        mh = m1.number_input("Local", min_value=1.01, value=2.00)
        md = m2.number_input("Empate", min_value=1.01, value=3.30)
        ma = m3.number_input("Visitante", min_value=1.01, value=3.50)
        inv = np.array([1 / mh, 1 / md, 1 / ma])
        mer = inv / inv.sum()
        dm = pd.DataFrame({"Modelo": [pl, pe, pv], "Mercado": mer},
                          index=[f"Gana {local}", "Empate", f"Gana {visita}"])
        dm["Diferencia (pp)"] = (dm["Modelo"] - dm["Mercado"]) * 100
        st.dataframe(dm.style.format({"Modelo": "{:.1%}", "Mercado": "{:.1%}", "Diferencia (pp)": "{:+.1f}"}))

with tab2:
    st.subheader("Ranking Elo de equipos activos")
    rank = pd.Series({e: elo[e] for e in equipos}).sort_values(ascending=False).rename("Elo").to_frame()
    rank.index.name = "Equipo"
    lo, hi = int(rank["Elo"].min() // 50 * 50), int(rank["Elo"].max() // 50 * 50 + 50)
    st.dataframe(rank, column_config={"Elo": st.column_config.ProgressColumn(
        "Elo", min_value=lo, max_value=hi, format="%.0f")})
    st.caption("Todos los equipos empiezan en 1500. Gana puntos quien vence a rivales fuertes.")

with tab3:
    st.subheader("Qué tan bueno es")
    st.write("Evaluación en 1,016 partidos que el modelo no vio (2023/24 a 2025/26). "
             "Menor log loss es mejor.")
    st.table(pd.DataFrame({
        "Modelo": ["Mercado", "Logística + momios", "Logística", "XGBoost", "Frecuencias"],
        "Log loss": [0.9809, 0.9879, 1.0090, 1.0213, 1.0599],
        "Accuracy": [0.529, 0.520, 0.505, 0.502, 0.471],
    }).set_index("Modelo"))
    st.write("El modelo supera a las frecuencias históricas pero **no al mercado**: los momios ya "
             "incluyen lesiones y alineaciones, que este modelo no ve. Proyecto educativo, no es "
             "recomendación de apuestas.")
    st.markdown("[Código y metodología en GitHub](https://github.com/luismtz224/ligamx-match-predictor)")