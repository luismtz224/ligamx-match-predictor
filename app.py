import joblib
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Liga MX Match Predictor", page_icon="⚽")
est = joblib.load("modelos/modelo.joblib")
modelo, cols, elo, hist, equipos = est["modelo"], est["cols"], est["elo"], est["hist"], est["activos"]

def forma(t):
    h = hist.get(t, [])
    return np.array(h).mean(axis=0) if h else np.array([np.nan] * 3)

st.title("⚽ Liga MX Match Predictor")
local = st.selectbox("Local", equipos)
visita = st.selectbox("Visitante", [e for e in equipos if e != local])

ph, gfh, gch = forma(local)
pa, gfa, gca = forma(visita)
x = pd.DataFrame([dict(elo_diff=elo[local] - elo[visita], elo_h=elo[local], elo_a=elo[visita],
                       pts_h=ph, pts_a=pa, gf_h=gfh, gc_h=gch, gf_a=gfa, gc_a=gca)])[cols]
pv, pe, pl = modelo.predict_proba(x)[0][[0, 1, 2]]   # orden del modelo: visitante, empate, local

c1, c2, c3 = st.columns(3)
c1.metric("Local", f"{pl:.0%}")
c2.metric("Empate", f"{pe:.0%}")
c3.metric("Visitante", f"{pv:.0%}")

with st.expander("Comparar con los momios (opcional)"):
    mh = st.number_input("Momio local", min_value=1.01, value=2.00)
    md = st.number_input("Momio empate", min_value=1.01, value=3.30)
    ma = st.number_input("Momio visitante", min_value=1.01, value=3.50)
    inv = np.array([1 / mh, 1 / md, 1 / ma])
    mer = inv / inv.sum()
    st.dataframe(pd.DataFrame({"Modelo": [pl, pe, pv], "Mercado": mer},
                              index=["Local", "Empate", "Visitante"]).style.format("{:.1%}"))

st.caption("El modelo usa Elo y forma reciente. Pierde contra el mercado en log loss; ver README.")