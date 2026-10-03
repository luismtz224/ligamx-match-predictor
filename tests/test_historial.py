import joblib
import numpy as np
import pandas as pd
import pytest

from src.entrenar import RUTA_CSV, RUTA_MODELO
from src.features import cargar_partidos, procesar
from src.equipos import cargar_rivalidades
from src.historial import (clasico, extremos, filtrar_temporada, gep, h2h, mejores_peores,
                           partidos_equipo, posicion, racha, ranking, record, rivales,
                           serie_elo, temporadas, ultimos)


@pytest.fixture(scope="module")
def datos():
    feat, elo, hist = procesar(cargar_partidos(RUTA_CSV), K=20, ventaja=60, regresion=0.0)
    return feat, elo, hist, joblib.load(RUTA_MODELO)


def test_elo_despues_es_elo_antes_del_siguiente(datos):
    feat, elo, _, est = datos
    for equipo in ["Club America", "Leones Negros", "Atlante"]:
        pe = partidos_equipo(feat, equipo, elo)
        assert np.allclose(pe["elo_despues"].iloc[:-1], pe["elo_antes"].iloc[1:])
        assert pe["elo_despues"].iloc[-1] == elo[equipo] == est["elo"][equipo]
        assert pe["fecha"].is_monotonic_increasing


def test_ultimo_elo_y_forma_cuadran_con_el_modelo(datos):
    """Lo que muestra la app sale del CSV y debe coincidir con lo guardado en modelo.joblib."""
    feat, elo, _, est = datos
    assert set(est["elo"]) == set(feat["Home"]) | set(feat["Away"])
    for equipo, elo_modelo in est["elo"].items():
        pe = partidos_equipo(feat, equipo, elo)
        assert pe["elo_despues"].iloc[-1] == pytest.approx(elo_modelo, abs=1e-9)
        u = ultimos(pe, 5)
        assert [tuple(r) for r in u[["puntos", "gf", "gc"]].values] == \
            [tuple(map(int, h)) for h in est["hist"][equipo]]


def test_cambio_de_elo_se_conserva_por_partido(datos):
    feat, elo, _, _ = datos
    deltas = {}
    for equipo in set(feat["Home"]) | set(feat["Away"]):
        pe = partidos_equipo(feat, equipo, elo)
        idx = feat.index[(feat["Home"] == equipo) | (feat["Away"] == equipo)]
        for i, dlt in zip(idx, pe["elo_despues"] - pe["elo_antes"]):
            deltas[i] = deltas.get(i, 0.0) + dlt
    assert len(deltas) == len(feat)
    assert max(abs(v) for v in deltas.values()) < 1e-9


def test_partidos_equipo_perspectiva(datos):
    feat, elo, _, _ = datos
    pe = partidos_equipo(feat, "Club America", elo)
    r = feat[(feat["Home"] == "Club America") | (feat["Away"] == "Club America")].iloc[0]
    p = pe.iloc[0]
    local = r["Home"] == "Club America"
    assert p["local"] == local
    assert p["gf"] == (r["HG"] if local else r["AG"])
    esperado = {"H": "V", "D": "E", "A": "D"}[r["Res"]] if local else {"H": "D", "D": "E", "A": "V"}[r["Res"]]
    assert p["resultado"] == esperado


def test_record_suma(datos):
    feat, elo, _, _ = datos
    pe = partidos_equipo(feat, "Toluca", elo)
    rec = record(pe)
    assert rec["PJ"].sum() == len(pe)
    assert (rec["G"] + rec["E"] + rec["P"] == rec["PJ"]).all()
    loc = pe[pe["local"]]
    assert rec.loc["Local", "GF_pp"] == pytest.approx(loc["gf"].mean())
    t = filtrar_temporada(pe, "2024/2025")
    assert set(t["temporada"]) == {"2024/2025"} and record(t)["PJ"].sum() == len(t)


def test_h2h_simetrico(datos):
    feat, _, _, _ = datos
    (g, e, p), ult = h2h(feat, "Club America", "Guadalajara Chivas", n=5)
    (g2, e2, p2), _ = h2h(feat, "Guadalajara Chivas", "Club America")
    assert (g, e, p) == (p2, e2, g2)
    m = feat[((feat["Home"] == "Club America") & (feat["Away"] == "Guadalajara Chivas"))
             | ((feat["Home"] == "Guadalajara Chivas") & (feat["Away"] == "Club America"))]
    assert g + e + p == len(m)
    assert len(ult) == 5 and ult["fecha"].iloc[-1] == m["Date"].max()


def _pe(resultados, rivales_=None):
    n = len(resultados)
    return pd.DataFrame({"resultado": resultados,
                         "puntos": [{"V": 3, "E": 1, "D": 0}[r] for r in resultados],
                         "rival": rivales_ or ["X"] * n})


def test_racha():
    assert racha(_pe(list("VDEEE"))) == ("E", 3)
    assert racha(_pe(list("EV"))) == ("V", 1)
    assert racha(_pe([])) == (None, 0)
    assert gep(_pe(list("VVED"))) == (2, 1, 1)


def test_rivales_minimo_y_orden():
    pe = _pe(list("VVVVVVDDDDDDE"), ["A"] * 6 + ["B"] * 6 + ["C"])
    r = rivales(pe, min_duelos=6)
    assert list(r.index) == ["A", "B"]
    assert r.loc["A", "ppp"] == 3 and r.loc["B", "n"] == 6


def test_ranking_y_posicion():
    elo = {"A": 1600, "B": 1500, "C": 1550, "Z": 1700}
    activos = ["A", "B", "C"]
    assert list(ranking(elo, activos).index) == ["A", "C", "B"]
    assert posicion("C", elo, activos) == 2
    assert posicion("Z", elo, activos) is None


# ===== Fase 5: serie del Elo, rivales, clásicos =====


def _pe_serie(fechas, antes, despues):
    return pd.DataFrame({"fecha": pd.to_datetime(fechas), "elo_antes": antes, "elo_despues": despues})


def test_serie_elo_puntos_y_corte():
    pe = _pe_serie(["2020-01-01", "2020-01-08", "2021-06-01"], [1500, 1510, 1520], [1510, 1520, 1530])
    s = serie_elo(pe)
    assert list(s["elo"]) == [1500, 1510, 1520, 1520, 1530]
    assert list(s["tramo_nuevo"]) == [True, False, False, True, False]  # 510 días sin jugar
    assert s["fecha"].iloc[3] == pd.Timestamp("2021-06-01")


def test_serie_elo_el_corte_es_mayor_a_365_dias():
    base = pd.Timestamp("2020-01-01")
    for dias, cortes in ((365, 1), (366, 2)):
        pe = _pe_serie([base, base + pd.Timedelta(days=dias)], [1500, 1510], [1510, 1520])
        assert serie_elo(pe)["tramo_nuevo"].sum() == cortes, dias


def test_serie_elo_vacia_y_extremos_vacios():
    pe = _pe_serie([], [], [])
    s = serie_elo(pe)
    assert s.empty and extremos(s) is None


def test_extremos_y_empates_toman_el_primero():
    pe = _pe_serie(["2020-01-01", "2020-01-08", "2020-01-15", "2020-01-22"],
                   [1500, 1540, 1500, 1540], [1540, 1500, 1540, 1500])
    e = extremos(serie_elo(pe))
    assert e["maximo"] == (pd.Timestamp("2020-01-01"), 1540.0)
    assert e["minimo"] == (pd.Timestamp("2020-01-01"), 1500.0)  # el punto inicial
    assert e["inicio"] == (pd.Timestamp("2020-01-01"), 1500.0)
    assert e["final"] == (pd.Timestamp("2020-01-22"), 1500.0)


def test_serie_elo_ultimo_punto_es_el_elo_del_modelo_de_los_25(datos):
    feat, elo, _, est = datos
    for equipo in est["elo"]:
        pe = partidos_equipo(feat, equipo, elo)
        s = serie_elo(pe)
        assert s["elo"].iloc[-1] == pytest.approx(est["elo"][equipo], abs=1e-9), equipo
        assert s["elo"].iloc[0] == pe["elo_antes"].iloc[0]
        assert s["fecha"].iloc[-1] == pe["fecha"].iloc[-1]


def test_serie_elo_corta_solo_atl_san_luis_y_atlante(datos):
    feat, elo, _, est = datos
    con_cortes = {}
    for equipo in est["elo"]:
        s = serie_elo(partidos_equipo(feat, equipo, elo))
        if s["tramo_nuevo"].sum() > 1:
            con_cortes[equipo] = s
    assert set(con_cortes) == {"Atl. San Luis", "Atlante"}
    for s in con_cortes.values():
        assert s["tramo_nuevo"].sum() == 2
    # el hueco de Atl. San Luis es de 2,267 días y el de Atlante de 4,464
    for equipo, dias in (("Atl. San Luis", 2267), ("Atlante", 4464)):
        pe = partidos_equipo(feat, equipo, elo)
        assert (pe["fecha"].diff().dt.days.max()) == dias


def test_serie_elo_filtrada_por_temporada(datos):
    feat, elo, _, _ = datos
    pe = partidos_equipo(feat, "Toluca", elo)
    pf = filtrar_temporada(pe, "2025/2026")
    s = serie_elo(pf)
    assert s["elo"].iloc[0] == pf["elo_antes"].iloc[0]
    assert s["elo"].iloc[-1] == pf["elo_despues"].iloc[-1]
    assert len(s) == len(pf) + 1 and s["tramo_nuevo"].sum() == 1


def test_temporadas_en_orden_y_sin_repetir(datos):
    feat, elo, _, _ = datos
    t = temporadas(partidos_equipo(feat, "Toluca", elo))
    assert t[0] == "2012/2013" and t[-1] == "2026/2027" and t == sorted(set(t))
    assert temporadas(partidos_equipo(feat, "Chiapas", elo))[-1] == "2016/2017"


def test_rivales_incluye_g_e_p():
    pe = _pe(list("VVDEDDVV"), ["A"] * 8)
    r = rivales(pe, min_duelos=6)
    assert (r.loc["A", "g"], r.loc["A", "e"], r.loc["A", "p"]) == (4, 1, 3)
    assert r.loc["A", "g"] + r.loc["A", "e"] + r.loc["A", "p"] == r.loc["A", "n"]


def _tabla(n):
    """n rivales con ppp decreciente (r0 el mejor)."""
    return pd.DataFrame({"n": [10 + i for i in range(n)], "ppp": [3 - i * 0.25 for i in range(n)],
                         "g": 0, "e": 0, "p": 0}, index=[f"r{i}" for i in range(n)])


@pytest.mark.parametrize("n,k_mejores,k_peores", [(0, 0, 0), (1, 1, 0), (2, 1, 1), (3, 1, 1),
                                                   (4, 2, 2), (6, 3, 3), (9, 3, 3)])
def test_mejores_peores_tamanos_y_sin_solape(n, k_mejores, k_peores):
    riv = _tabla(n)
    mejores, peores = mejores_peores(riv)
    assert (len(mejores), len(peores)) == (k_mejores, k_peores)
    assert not set(mejores.index) & set(peores.index)
    if len(mejores) and len(peores):
        assert mejores["ppp"].min() >= peores["ppp"].max()


def test_mejores_peores_orden():
    mejores, peores = mejores_peores(_tabla(9))
    assert list(mejores.index) == ["r0", "r1", "r2"]  # el mejor primero
    assert list(peores.index) == ["r8", "r7", "r6"]  # el peor primero


def test_mejores_peores_empate_de_ppp_desempata_por_duelos():
    riv = pd.DataFrame({"n": [8, 20, 9, 12], "ppp": [2.0, 2.0, 1.0, 1.0], "g": 0, "e": 0, "p": 0},
                       index=["a", "b", "c", "d"]).sort_values(["ppp", "n"], ascending=[False, False])
    mejores, peores = mejores_peores(riv, max_k=2)
    assert list(mejores.index) == ["b", "a"]  # a igual ppp, más duelos primero
    assert list(peores.index) == ["d", "c"]


def test_equipos_sin_rivales_con_6_duelos_hoy(datos):
    feat, elo, _, _ = datos
    for equipo in ("Atlante", "Dorados de Sinaloa", "Leones Negros", "Lobos BUAP"):
        assert rivales(partidos_equipo(feat, equipo, elo)).empty, equipo


def test_clasico_cuenta_gep_y_ultimo_duelo(datos):
    feat, _, _, _ = datos
    k = clasico(feat, "Club Tijuana", "Juarez")
    assert k["n"] == 14 and k["g"] + k["e"] + k["p"] == 14
    duelos = partidos_equipo(feat, "Club Tijuana")
    duelos = duelos[duelos["rival"] == "Juarez"]
    u = duelos.iloc[-1]
    assert k["ultimo"] == dict(fecha=u["fecha"], local=bool(u["local"]), gf=int(u["gf"]), gc=int(u["gc"]))
    assert (k["g"], k["e"], k["p"]) == gep(duelos)


def test_clasico_sin_duelos():
    feat = pd.DataFrame({"Home": ["A"], "Away": ["B"], "Date": [pd.Timestamp("2020-01-01")],
                         "Season": ["2019/2020"], "HG": [1], "AG": [0], "Res": ["H"],
                         "elo_h": [1500.0], "elo_a": [1500.0]})
    assert clasico(feat, "A", "C") == dict(n=0, g=0, e=0, p=0, ultimo=None)


def test_clasicos_de_rivalidades_csv_duelos_reales_y_simetria(datos):
    feat, _, _, _ = datos
    esperados = {frozenset(("UNAM Pumas", "Leones Negros")): 2,
                 frozenset(("Puebla", "Lobos BUAP")): 4,
                 frozenset(("Necaxa", "Atlante")): 1,
                 frozenset(("Club Tijuana", "Juarez")): 14,
                 frozenset(("Atl. San Luis", "Queretaro")): 16}
    riv = cargar_rivalidades()
    assert len(riv) == 11
    for r in riv.itertuples():
        a, b = clasico(feat, r.equipo_a, r.equipo_b), clasico(feat, r.equipo_b, r.equipo_a)
        assert a["n"] == b["n"]
        assert (a["g"], a["e"], a["p"]) == (b["p"], b["e"], b["g"])  # simetría
        if a["ultimo"]:
            assert a["ultimo"]["fecha"] == b["ultimo"]["fecha"]
            assert a["ultimo"]["local"] != b["ultimo"]["local"]
            assert (a["ultimo"]["gf"], a["ultimo"]["gc"]) == (b["ultimo"]["gc"], b["ultimo"]["gf"])
        par = frozenset((r.equipo_a, r.equipo_b))
        if par in esperados:
            assert a["n"] == esperados[par], par
        else:
            assert 30 <= a["n"] <= 43, par
