"""`GET /api/p3/runs` y `/runs/{id}`: corridas reales de MLflow para Experiments (contratos §4, F5).

El MLflow es un falso con la misma interfaz que `MlflowRest`.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from p3.train import runs_api
from p3.train.selection import RunSummary

HASH = "45600f297d13f51685e051e0cbc4962beb1f7c6a4e03247cbf61a345e6fa4305"


def _run(run_id: str, acc: float, loss: float, **kw) -> RunSummary:
    return RunSummary(
        run_id=run_id,
        experiment_id="3",
        status=kw.get("status", "FINISHED"),
        end_time=kw.get("end", 1_790_000_000_000),
        best_val_accuracy=acc,
        best_val_loss=loss,
        best_epoch=3,
        stopped_epoch=8,
        manifest_id=kw.get("manifest_id", "m-0.1.3-s42-1"),
        manifest_hash=HASH,
        artifact_uri=f"mlflow-artifacts:/3/{run_id}/artifacts",
        params={"optimizer": "sgd", "batch_size": "32"},
        tags={"code_commit": "250bedc" + "0" * 33, **kw.get("tags", {})},
        start_time=kw.get("start", 1_789_999_000_000),
    )


class FakeMlflow:
    def __init__(self) -> None:
        self.runs = [
            _run("a", 0.95, 0.20, start=1),
            _run("b", 0.99, 0.10, start=2, tags={"selected": "true"}),
            _run("c", 0.97, 0.05, start=3),
            _run("fallida", 0.0, 9.0, status="FAILED", start=4),
            _run("otro", 0.91, 0.3, manifest_id="m-otro", start=5),
        ]

    def search_runs(self, experiment: str) -> list[RunSummary]:
        assert experiment == "p3-clasificador"
        return list(self.runs)

    def get_run(self, run_id: str) -> RunSummary:
        for run in self.runs:
            if run.run_id == run_id:
                return run
        raise LookupError(run_id)

    def metric_history(self, run_id: str, key: str) -> list[tuple[int, float]]:
        base = {"train_loss": 1.0, "val_loss": 0.9, "train_accuracy": 0.5, "val_accuracy": 0.4}[key]
        return [(3, base + 0.3), (1, base + 0.1), (2, base + 0.2)]  # desordenado a proposito


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(runs_api.router)
    fake = FakeMlflow()
    app.dependency_overrides[runs_api.get_mlflow] = lambda: fake
    return TestClient(app)


def test_lista_las_corridas_con_los_campos_del_contrato(client: TestClient) -> None:
    body = client.get("/api/p3/runs").json()
    assert {r["run_id"] for r in body["runs"]} == {"a", "b", "c", "fallida", "otro"}
    b = next(r for r in body["runs"] if r["run_id"] == "b")
    assert b["status"] == "FINISHED"
    assert b["manifest_id"] == "m-0.1.3-s42-1"
    assert b["params"] == {"optimizer": "sgd", "batch_size": "32"}
    assert (b["best_epoch"], b["stopped_epoch"]) == (3, 8)
    assert (b["best_val_accuracy"], b["best_val_loss"]) == (0.99, 0.10)
    assert b["commit"].startswith("250bedc")
    assert b["experiment_id"] == "3"
    assert b["selected"] is True
    assert b["start_time"].endswith("Z") and b["end_time"].endswith("Z")


def test_filtra_por_manifiesto_y_estado(client: TestClient) -> None:
    body = client.get("/api/p3/runs?manifest_id=m-0.1.3-s42-1&status=FINISHED").json()
    assert {r["run_id"] for r in body["runs"]} == {"a", "b", "c"}


@pytest.mark.parametrize(
    ("order_by", "desc", "esperado"),
    [
        ("val_accuracy", "true", ["b", "c", "a"]),
        ("val_accuracy", "false", ["a", "c", "b"]),
        ("val_loss", "false", ["c", "b", "a"]),
        ("start_time", "true", ["c", "b", "a"]),
    ],
)
def test_ordena(client: TestClient, order_by: str, desc: str, esperado: list[str]) -> None:
    url = f"/api/p3/runs?status=FINISHED&manifest_id=m-0.1.3-s42-1&order_by={order_by}&desc={desc}"
    assert [r["run_id"] for r in client.get(url).json()["runs"]] == esperado


def test_un_orden_desconocido_da_422(client: TestClient) -> None:
    assert client.get("/api/p3/runs?order_by=test_accuracy").status_code == 422


def test_el_detalle_trae_la_historia_por_epoca_ordenada_y_los_artefactos(
    client: TestClient,
) -> None:
    body = client.get("/api/p3/runs/b").json()
    assert body["run_id"] == "b"
    assert [h["epoch"] for h in body["history"]] == [1, 2, 3]
    assert body["history"][0] == {
        "epoch": 1,
        "train_loss": 1.1,
        "train_accuracy": 0.6,
        "val_loss": 1.0,
        "val_accuracy": 0.5,
    }
    assert body["artifacts"]["checkpoint"] == "mlflow-artifacts:/3/b/artifacts/checkpoint/model.pt"
    assert body["artifacts"]["curves"] == "mlflow-artifacts:/3/b/artifacts/curves.png"


def test_un_run_inexistente_da_404(client: TestClient) -> None:
    assert client.get("/api/p3/runs/no-existe").status_code == 404


def test_no_importa_torch_ni_mlflow() -> None:
    from pathlib import Path

    texto = Path(runs_api.__file__).read_text(encoding="utf-8")
    assert "import torch" not in texto and "import mlflow" not in texto
