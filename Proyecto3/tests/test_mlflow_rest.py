"""Robustez del cliente REST de MLflow ante un stack recien levantado (F10).

Cuando nadie ha entrenado, el experimento `p3-clasificador` no existe y MLflow
responde 404 a `experiments/get-by-name`. `search_runs` debe tomarlo como "no hay
corridas" (lista vacia), no como un fallo: asi `GET /api/p3/runs` responde `[]`,
la seleccion responde 404 y la evaluacion 409, en vez de 500. Un fallo real de
MLflow (otro codigo / sin respuesta) si debe propagarse como MlflowUnavailableError.
"""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from p3.train import selection


def _raise(code: int):
    def boom(*_args, **_kwargs):
        raise urllib.error.HTTPError("http://mlflow:5000", code, "boom", {}, None)  # type: ignore[arg-type]

    return boom


def test_search_runs_vacio_si_el_experimento_no_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _raise(404))
    assert selection.MlflowRest("http://mlflow:5000").search_runs("p3-clasificador") == []


def test_search_runs_502_si_mlflow_falla_de_verdad(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _raise(500))
    with pytest.raises(selection.MlflowUnavailableError):
        selection.MlflowRest("http://mlflow:5000").search_runs("p3-clasificador")
