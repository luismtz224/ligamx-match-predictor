import streamlit as st

from interfaz import componentes, recursos

st.set_page_config(page_title="Liga MX Match Predictor", page_icon="⚽", layout="wide")

paginas = [
    st.Page("paginas/predictor.py", title="Predictor", icon=":material/sports_soccer:", default=True),
    st.Page("paginas/equipos.py", title="Equipos", icon=":material/shield:"),
    st.Page("paginas/ranking.py", title="Ranking", icon=":material/leaderboard:"),
    st.Page("paginas/sobre_modelo.py", title="Sobre el modelo", icon=":material/info:"),
]
pg = st.navigation(paginas)
recursos.inyectar_css()
pg.run()
st.markdown(componentes.pie_escudos(), unsafe_allow_html=True)
