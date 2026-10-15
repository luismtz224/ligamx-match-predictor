"""Fixtures compartidas entre archivos de pruebas."""
import pytest

from src.evaluacion import oof_walk_forward


@pytest.fixture(scope="session")
def oof():
    """Predicciones fuera de muestra del walk-forward (~20 s): se calculan una sola vez para todas las pruebas
    de los exportadores (calibración y predicciones por temporada)."""
    return oof_walk_forward()
