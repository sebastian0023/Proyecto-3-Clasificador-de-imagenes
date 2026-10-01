"""API de la evaluacion final para la pagina Evaluation (F6, contratos §4; criterio 6.3).

Todo sale de MLflow: la corrida `selected=true` del barrido y sus artefactos
`evaluation/` (los registra `scripts/log_evaluation_mlflow.py`). Asi portal,
API y MLflow muestran las mismas cifras (4.2).

- `GET /api/p3/evaluation`: metricas, matriz, baseline y procedencia.
- `GET /api/p3/evaluation/predictions`: `predictions_test.csv` por muestra, para auditar.
- `GET /api/p3/evaluation/examples`: aciertos y errores de test (`errors.json`).

Mientras la seleccion no este cerrada responde 409 y no revela nada del test.
Si MLflow no responde (o responde un error que no es 404) responde 503, no 500.
Solo lee: usa el cliente REST de `p3.train.selection`, sin torch ni el cliente
de MLflow, porque se monta en la app de P2.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any

from fastapi import APIRouter, HTTPException, Response

from p3.train.selection import EXPERIMENT, MlflowDep, RunSummary, get_mlflow

router = APIRouter(prefix="/api/p3/evaluation", tags=["p3-evaluation"])

NOT_SELECTED = "La selección del modelo no está cerrada"
FOLDER = "evaluation"
PER_CLASS_FIELDS = ("class", "precision", "recall", "f1", "support")

__all__ = ["get_mlflow", "router"]


def _selected(mlflow: Any) -> RunSummary:
    try:
        runs = mlflow.search_runs(EXPERIMENT)
    except OSError as error:
        raise _mlflow_down(error) from error
    run = next((r for r in runs if r.tags.get("selected") == "true"), None)
    if run is None:
        raise HTTPException(409, NOT_SELECTED)
    return run


def _artifact(mlflow: Any, run: RunSummary, name: str) -> bytes:
    try:
        return mlflow.artifact_bytes(run, f"{FOLDER}/{name}")
    except FileNotFoundError as error:
        raise _no_evaluation(run) from error
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise _no_evaluation(run) from error
        raise _mlflow_down(error) from error
    except OSError as error:
        raise _mlflow_down(error) from error


def _mlflow_down(error: OSError) -> HTTPException:
    return HTTPException(
        503, f"MLflow no esta disponible ({error}); revisa el servicio `mlflow` y P3_MLFLOW_URL."
    )


def _no_evaluation(run: RunSummary) -> HTTPException:
    return HTTPException(
        404, f"La corrida seleccionada {run.run_id} todavía no tiene la evaluación final en test."
    )


@router.get("")
def read_evaluation(mlflow: MlflowDep) -> dict[str, Any]:
    run = _selected(mlflow)
    metrics = json.loads(_artifact(mlflow, run, "metrics.json"))
    return {
        "run_id": run.run_id,
        "manifest_id": metrics["manifest_id"],
        "test_size": metrics["test_size"],
        "accuracy": metrics["accuracy"],
        "passes_threshold": metrics["passes_threshold"],
        "threshold": metrics["threshold"],
        "f1_macro": metrics["f1_macro"],
        "per_class": [{k: row[k] for k in PER_CLASS_FIELDS} for row in metrics["per_class"]],
        "confusion_matrix": metrics["confusion_matrix"],
        "majority_baseline": metrics["majority_baseline"]["accuracy"],
        "majority_class": metrics["majority_baseline"]["class"],
        "most_confused": metrics["most_confused"],
        "evaluated_at": metrics["evaluated_at"],
        "predictions_uri": f"{router.prefix}/predictions",
        "examples_uri": f"{router.prefix}/examples",
    }


@router.get("/predictions")
def read_predictions(mlflow: MlflowDep) -> Response:
    run = _selected(mlflow)
    return Response(
        _artifact(mlflow, run, "predictions_test.csv"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="predictions_test.csv"'},
    )


@router.get("/examples")
def read_examples(mlflow: MlflowDep) -> dict[str, Any]:
    run = _selected(mlflow)
    return json.loads(_artifact(mlflow, run, "errors.json"))
