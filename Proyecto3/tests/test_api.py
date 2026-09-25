"""El endpoint solo encola y devuelve job_id; el estado se consulta aparte (F1 T02)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from p3.worker import api, jobs


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> TestClient:
    app = FastAPI()
    app.include_router(api.router)

    def override() -> Iterator[Session]:
        with session_factory.begin() as session:
            yield session

    app.dependency_overrides[api.get_session] = override
    return TestClient(app)


def test_post_encola_sin_ejecutar(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    response = client.post("/api/p3/training/jobs", json={"kind": "dummy", "config": {}})

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    with session_factory() as session:
        stored = jobs.get_job(session, body["job_id"])
        assert stored is not None
        assert stored.status == jobs.JobStatus.QUEUED


def test_get_devuelve_estado_progreso_logs_y_error(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    job_id = client.post("/api/p3/training/jobs", json={"kind": "dummy"}).json()["job_id"]
    with session_factory.begin() as session:
        jobs.claim_next(session, worker_id="w1")
    with session_factory.begin() as session:
        jobs.report_progress(session, job_id, 0.5, "mitad")

    response = client.get(f"/api/p3/training/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "running"
    assert body["progress"] == 0.5
    assert any("mitad" in linea for linea in body["logs"])
    assert body["error"] is None


def test_get_de_un_id_inexistente_es_404(client: TestClient) -> None:
    response = client.get("/api/p3/training/jobs/no-existe")

    assert response.status_code == 404


def test_kind_invalido_se_rechaza_nombrando_el_campo(client: TestClient) -> None:
    response = client.post("/api/p3/training/jobs", json={"kind": "minar-bitcoin"})

    assert response.status_code == 422
    assert "kind" in str(response.json()["detail"])


def test_campos_extra_se_rechazan(client: TestClient) -> None:
    response = client.post("/api/p3/training/jobs", json={"kind": "dummy", "prioridad": 9})

    assert response.status_code == 422
