import numpy as np
import pytest

from src.calibracion import (asignar_bins, bootstrap_ece, brier_total_por_partido, ece,
                             ece_esperado)
from src.evaluacion import bootstrap_pareado


def _probs_y_resultados(n, semilla=0, deformar=False):
    """Probabilidades aleatorias y resultados sorteados con ellas (calibrado por construcción)."""
    rng = np.random.default_rng(semilla)
    p = rng.dirichlet([4, 3, 3], size=n)
    y = (rng.random(n)[:, None] > p.cumsum(axis=1)).sum(axis=1).clip(max=2)
    if deformar:  # el modelo reporta algo distinto de lo que pasa: p^2 renormalizada
        p = p**2 / (p**2).sum(axis=1, keepdims=True)
    return p, y


@pytest.mark.parametrize("n_bins", [4, 6, 10])
def test_bins_cubren_cada_prediccion_exactamente_una_vez(n_bins):
    rng = np.random.default_rng(1)
    p = rng.random(1000)
    bins = asignar_bins(p, n_bins)
    assert len(bins) == len(p)
    assert bins.min() == 0 and bins.max() == n_bins - 1
    assert np.bincount(bins, minlength=n_bins).sum() == len(p)
    # bins de tamaño casi igual (cuantiles)
    assert np.bincount(bins, minlength=n_bins).std() < 0.05 * len(p) / n_bins


def test_bins_con_valores_repetidos_siguen_cubriendo_todo_una_vez():
    p = np.array([0.3] * 50 + [0.1] * 20 + [0.5] * 30)   # bordes de cuantil que coinciden
    bins = asignar_bins(p, 6)
    assert len(bins) == 100
    assert bins.min() >= 0 and bins.max() <= 5
    assert np.bincount(bins, minlength=6).sum() == 100
    # un mismo valor nunca queda en dos bins distintos
    for v in (0.1, 0.3, 0.5):
        assert len(set(bins[p == v])) == 1


def test_modelo_perfectamente_calibrado_da_ece_cercano_a_cero():
    p, y = _probs_y_resultados(200_000)
    for k in range(3):
        assert ece(p[:, k], y == k) < 0.01


def test_modelo_descalibrado_da_ece_claramente_mayor():
    p, y = _probs_y_resultados(200_000, deformar=True)
    perfecto, y2 = _probs_y_resultados(200_000)
    for k in range(3):
        assert ece(p[:, k], y == k) > 3 * ece(perfecto[:, k], y2 == k)


def test_ece_con_ejemplo_calculado_a_mano():
    # 2 bins de 4 partidos: bajo (p=0.2, 1 de 4 pasó -> real 0.25), alto (p=0.8, 2 de 4 -> real 0.5)
    p = np.array([0.2] * 4 + [0.8] * 4)
    o = np.array([1, 0, 0, 0, 1, 1, 0, 0])
    esperado = (4 * abs(0.2 - 0.25) + 4 * abs(0.8 - 0.5)) / 8
    assert ece(p, o, n_bins=2) == pytest.approx(esperado)


def test_ece_esperado_se_parece_al_ece_de_un_modelo_calibrado_y_es_positivo():
    p, y = _probs_y_resultados(2000)
    esp = ece_esperado(p, n_sim=200)
    for k in range(3):
        media, lo, hi = esp[k]
        assert 0 < lo <= media <= hi
        assert lo <= ece(p[:, k], y == k) <= hi * 1.5   # el calibrado real cae en el rango del ruido


def test_bootstrap_ece_con_modelo_perfecto_constante_es_degenerado():
    # p constante y frecuencia real igual en todos los bloques: sin ruido, ECE = 0 en todas las réplicas
    p = np.full(60, 0.5)
    o = np.tile([1, 0], 30)
    bloques = np.repeat(np.arange(10), 6)
    lo, hi = bootstrap_ece(p, o, bloques, n_bins=3, n=200)
    assert lo == pytest.approx(0.0) and hi == pytest.approx(0.0)


def test_brier_total_por_partido_con_ejemplo_a_mano():
    p = np.array([[0.2, 0.3, 0.5], [0.6, 0.2, 0.2]])
    y = np.array([2, 0])   # gana local en el primero, visitante en el segundo
    esperado = [0.2**2 + 0.3**2 + 0.5**2, 0.4**2 + 0.2**2 + 0.2**2]
    assert brier_total_por_partido(p, y) == pytest.approx(esperado)


def test_comparacion_pareada_de_brier_detecta_al_modelo_mejor_y_no_inventa_diferencias():
    rng = np.random.default_rng(0)
    p, y = _probs_y_resultados(3000)
    semana = rng.integers(0, 150, size=3000)
    ruido = rng.dirichlet([2, 2, 2], size=3000)
    peor = 0.5 * p + 0.5 * ruido                       # mezcla con ruido: peor que el calibrado

    # el modelo con ruido es peor: la diferencia peor - bueno es positiva y su IC no cruza 0
    dif = brier_total_por_partido(peor, y) - brier_total_por_partido(p, y)
    media, lo, hi = bootstrap_pareado(dif, bloques=semana, n=2000)
    assert media > 0 and lo > 0

    # un modelo contra sí mismo: diferencia exactamente 0 e IC degenerado en 0
    cero = brier_total_por_partido(p, y) - brier_total_por_partido(p, y)
    media, lo, hi = bootstrap_pareado(cero, bloques=semana, n=2000)
    assert media == 0 and lo == 0 and hi == 0
