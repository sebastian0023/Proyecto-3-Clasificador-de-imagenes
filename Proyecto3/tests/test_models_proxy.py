"""Reenvio de `/api/p3/models` desde el portal de P2 al servicio `p3-inference` (F7).

La app de P2 no tiene acceso de escritura a S3 ni PyTorch: pasa la peticion tal
cual y devuelve el codigo y el cuerpo del servicio.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from p3.registry import proxy


def client_with(calls: list, answer: tuple[int, bytes, str]) -> TestClient:
    def fake_send(method: str, url: str, body: bytes, headers: dict[str, str]):
        calls.append((method, url, body))
        status, data, media = answer
        return proxy.Response(data, status, media_type=media)

    app = FastAPI()
    app.include_router(proxy.router)
    app.dependency_overrides[proxy.get_upstream] = lambda: "http://servicio:8010"
    proxy_send = proxy.send
    proxy.send = fake_send  # type: ignore[assignment]
    client = TestClient(app)
    client.restore = lambda: setattr(proxy, "send", proxy_send)  # type: ignore[attr-defined]
    return client


def test_get_models_se_reenvia() -> None:
    calls: list = []
    client = client_with(
        calls, (200, b'{"active_version": "1.0.0", "models": []}', "application/json")
    )
    try:
        response = client.get("/api/p3/models")
    finally:
        client.restore()
    assert response.status_code == 200
    assert response.json()["active_version"] == "1.0.0"
    assert calls == [("GET", "http://servicio:8010/api/p3/models", b"")]


def test_activate_se_reenvia_con_su_codigo() -> None:
    calls: list = []
    client = client_with(calls, (409, b'{"detail": "no existe"}', "application/json"))
    try:
        response = client.post("/api/p3/models/0.9.0/activate")
    finally:
        client.restore()
    assert response.status_code == 409
    assert calls[0][:2] == ("POST", "http://servicio:8010/api/p3/models/0.9.0/activate")


def test_tarjeta_se_reenvia_como_markdown() -> None:
    calls: list = []
    client = client_with(calls, (200, b"# Tarjeta\n", "text/markdown"))
    try:
        response = client.get("/api/p3/models/1.0.0/card")
    finally:
        client.restore()
    assert response.text == "# Tarjeta\n"
    assert calls[0][:2] == ("GET", "http://servicio:8010/api/p3/models/1.0.0/card")


def test_pesos_se_reenvian_como_binario() -> None:
    calls: list = []
    client = client_with(calls, (200, b"BINARIO-DE-PESOS", "application/octet-stream"))
    try:
        response = client.get("/api/p3/models/1.0.0/weights")
    finally:
        client.restore()
    assert response.status_code == 200
    assert response.content == b"BINARIO-DE-PESOS"
    assert calls[0][:2] == ("GET", "http://servicio:8010/api/p3/models/1.0.0/weights")


def test_version_con_caracteres_raros_no_se_reenvia() -> None:
    calls: list = []
    client = client_with(calls, (200, b"{}", "application/json"))
    try:
        response = client.post("/api/p3/models/1.0.0;rm/activate")
    finally:
        client.restore()
    assert response.status_code == 422
    assert calls == []


def test_servicio_caido_responde_503(monkeypatch) -> None:
    import urllib.request

    def boom(*args, **kwargs):
        raise OSError("sin conexion")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    app = FastAPI()
    app.include_router(proxy.router)
    app.dependency_overrides[proxy.get_upstream] = lambda: "http://servicio:8010"
    response = TestClient(app).get("/api/p3/models")
    assert response.status_code == 503
