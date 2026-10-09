"""Bloque 3 de F4 (persistencia): imagen y registro en S3 con los campos del receptor."""

from __future__ import annotations

import hashlib
import json

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.stub import ANY, Stubber
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import BUCKET, CID, PREFIX, RECEIVED, make_jpeg, post, valid_event
from fake_s3 import client_error
from p4.captures import api
from p4.captures.event import CaptureEvent
from p4.captures.image import inspect_image
from p4.captures.s3_store import S3CaptureStore, UnavailableStore


def test_guarda_imagen_y_registro_con_campos_del_receptor(s3_client, s3):
    image = make_jpeg(64, 48)
    sent = valid_event(image)
    answer = post(s3_client, sent, image)

    assert answer.status_code == 201, answer.text
    assert answer.json() == {
        "status": "created",
        "capture_id": CID,
        "image_key": f"edge-captures/images/{CID}.jpg",
        "record_key": f"edge-captures/events/{CID}.json",
        "received_at": "2026-10-08T23:00:00.123+00:00",
        "warnings": [],
    }
    assert s3.keys() == [f"edge-captures/events/{CID}.json", f"edge-captures/images/{CID}.jpg"]

    photo = s3.objects[f"edge-captures/images/{CID}.jpg"]
    assert photo.body == image, "la imagen se guarda byte por byte"
    assert photo.content_type == "image/jpeg"
    assert photo.metadata == {"sha256": hashlib.sha256(image).hexdigest(), "capture-id": CID}

    stored = json.loads(s3.objects[f"edge-captures/events/{CID}.json"].body)
    for name, value in sent.items():
        assert stored[name] == value, f"{name} no coincide con lo enviado"
    assert stored["received_at"] == "2026-10-08T23:00:00.123+00:00"
    assert stored["image_key"] == f"edge-captures/images/{CID}.jpg"
    assert (stored["image_bytes"], stored["image_width"], stored["image_height"]) == (
        len(image),
        64,
        48,
    )
    # Capturada 2026-10-08T15:30:12-06:00 = 21:30:12Z; recibida 23:00:00.123Z.
    assert stored["delivery_delay_s"] == 5388.123
    assert stored["warnings"] == []


def test_reloj_adelantado_queda_senalado_en_el_registro(s3_client, s3):
    image = make_jpeg()
    answer = post(s3_client, valid_event(image, captured_at="2026-10-08T17:10:00-06:00"), image)
    assert answer.status_code == 201
    assert answer.json()["warnings"] == ["captured_at_en_el_futuro"]
    stored = json.loads(s3.objects[f"edge-captures/events/{CID}.json"].body)
    assert stored["warnings"] == ["captured_at_en_el_futuro"]


def test_region_se_guarda(s3_client, s3):
    image = make_jpeg(64, 48)
    region = {"x": 4, "y": 2, "width": 40, "height": 30}
    assert post(s3_client, valid_event(image, region=region), image).status_code == 201
    assert json.loads(s3.objects[f"edge-captures/events/{CID}.json"].body)["region"] == region


def test_error_de_s3_responde_503_visible(s3_client, s3):
    s3.fail_next["put_object"] = client_error("AccessDenied", 403, "PutObject")
    image = make_jpeg()
    answer = post(s3_client, valid_event(image), image)
    assert answer.status_code == 503
    body = answer.json()
    assert body["error"] == "almacenamiento_no_disponible"
    assert "AccessDenied" in body["mensaje"]
    assert "mismo capture_id" in body["mensaje"]
    assert s3.keys() == []


def test_falla_a_la_mitad_se_completa_con_el_reintento(s3_client, s3):
    """La imagen se guardo pero el registro no: el reintento lo completa sin duplicar."""
    image = make_jpeg()
    s3.calls.clear()
    # Primera llamada de put_object (imagen) pasa; la segunda (registro) falla.
    original = s3.put_object
    state = {"n": 0}

    def flaky(**kwargs):
        state["n"] += 1
        if state["n"] == 2:
            raise client_error("InternalError", 500, "PutObject")
        return original(**kwargs)

    s3.put_object = flaky  # type: ignore[method-assign]
    first = post(s3_client, valid_event(image), image)
    assert first.status_code == 503
    assert s3.keys() == [f"edge-captures/images/{CID}.jpg"]

    retry = post(s3_client, valid_event(image), image)
    assert retry.status_code == 201, retry.text
    assert s3.keys() == [f"edge-captures/events/{CID}.json", f"edge-captures/images/{CID}.jpg"]


def test_perfil_inexistente_responde_503(settings):
    store = UnavailableStore("perfil de AWS 'no-existe' no disponible (ProfileNotFound)")
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_settings] = lambda: settings
    app.dependency_overrides[api.get_store] = lambda: store
    image = make_jpeg()
    answer = post(TestClient(app), valid_event(image), image)
    assert answer.status_code == 503
    assert "no-existe" in answer.json()["mensaje"]


def test_perfil_inexistente_no_rompe_el_arranque():
    api._s3_store.cache_clear()
    store = api._s3_store(BUCKET, PREFIX, "perfil-que-no-existe-en-ninguna-maquina", "us-east-1")
    assert isinstance(store, UnavailableStore)


def test_llamadas_reales_a_s3_con_los_parametros_del_contrato():
    """Stubber valida los nombres y tipos contra el modelo de la API de S3 (p. ej. IfNoneMatch)."""
    client = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))
    image_bytes = make_jpeg()
    image = inspect_image(image_bytes, 1_000_000)
    event = CaptureEvent.model_validate(valid_event(image_bytes))
    with Stubber(client) as stub:
        stub.add_response(
            "put_object",
            {"VersionId": "v1"},
            {
                "Bucket": BUCKET,
                "Key": f"edge-captures/images/{CID}.jpg",
                "Body": image_bytes,
                "ContentType": "image/jpeg",
                "Metadata": {"sha256": image.sha256, "capture-id": CID},
                "IfNoneMatch": "*",
            },
        )
        stub.add_response(
            "put_object",
            {"VersionId": "v2"},
            {
                "Bucket": BUCKET,
                "Key": f"edge-captures/events/{CID}.json",
                "Body": ANY,
                "ContentType": "application/json",
                "Metadata": {},
                "IfNoneMatch": "*",
            },
        )
        result = S3CaptureStore(client, BUCKET, PREFIX, clock=lambda: RECEIVED).save(event, image)
        stub.assert_no_pending_responses()
    assert result.status == "created"
