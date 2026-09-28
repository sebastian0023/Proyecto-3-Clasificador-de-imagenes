"""API de versiones de modelo para la pagina Models (F7, contratos §4; criterios 5.3 y 6.4).

Vive en el servicio `p3-inference` (el que tiene acceso a S3) y el portal de P2
la reenvia. Contra el almacen falso de `test_publish`: nada toca S3 real.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from p3.registry import api
from p3.registry.publish import read_registry
from test_publish import BUCKET, PREFIX, FakeStore, checkpoint_bytes, publish


@pytest.fixture(scope="module")
def checkpoints() -> tuple[bytes, bytes]:
    return checkpoint_bytes(0), checkpoint_bytes(1)


@pytest.fixture
def store(checkpoints) -> FakeStore:
    fake = FakeStore()
    publish(fake, "0.9.0", checkpoints[1])
    publish(fake, "1.0.0", checkpoints[0], activate=True)
    return fake


def client_with(store: Any) -> TestClient:
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_models_store] = lambda: api.ModelsStore(
        store=store, bucket=BUCKET, prefix=PREFIX
    )
    return TestClient(app)


def test_lista_versiones_con_la_forma_del_contrato(store) -> None:
    body = client_with(store).get("/api/p3/models").json()
    assert body["active_version"] == "1.0.0"
    assert [m["version"] for m in body["models"]] == ["0.9.0", "1.0.0"]
    first = body["models"][0]
    assert set(first) >= {"version", "run_id", "manifest_id", "release_id", "s3", "card_uri"}
    assert set(first["s3"]) == {"uri", "version_id", "sha256", "exists"}
    assert first["s3"]["exists"] is True


def test_version_de_modelo_distinta_de_la_del_dataset(store) -> None:
    model = client_with(store).get("/api/p3/models").json()["models"][1]
    assert model["version"] == "1.0.0"
    assert model["release_id"] == "0.1.3"


def test_tarjeta_de_una_version(store) -> None:
    response = client_with(store).get("/api/p3/models/1.0.0/card")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text == "# Tarjeta 1.0.0\n"


def test_tarjeta_de_version_desconocida_404(store) -> None:
    assert client_with(store).get("/api/p3/models/7.7.7/card").status_code == 404


def test_activar_cambia_la_version_activa(store) -> None:
    response = client_with(store).post("/api/p3/models/0.9.0/activate")
    assert response.status_code == 200
    assert response.json()["active_version"] == "0.9.0"
    assert read_registry(store, bucket=BUCKET, prefix=PREFIX).active_version == "0.9.0"


def test_activar_version_desconocida_404(store) -> None:
    response = client_with(store).post("/api/p3/models/7.7.7/activate")
    assert response.status_code == 404
    assert read_registry(store, bucket=BUCKET, prefix=PREFIX).active_version == "1.0.0"


def test_no_se_activa_un_objeto_inexistente_409(store) -> None:
    store.delete(BUCKET, f"{PREFIX}/0.9.0/model.pt")
    response = client_with(store).post("/api/p3/models/0.9.0/activate")
    assert response.status_code == 409
    assert "no existe" in response.json()["detail"]
    assert read_registry(store, bucket=BUCKET, prefix=PREFIX).active_version == "1.0.0"


@pytest.mark.parametrize("version", ["1.0", "../1.0.0", "1.0.0;rm"])
def test_version_con_formato_invalido_422(store, version: str) -> None:
    response = client_with(store).post(f"/api/p3/models/{version}/activate")
    assert response.status_code in (404, 422)
    assert read_registry(store, bucket=BUCKET, prefix=PREFIX).active_version == "1.0.0"
