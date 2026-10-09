"""`/api/p4/captures`: recepcion de capturas del dispositivo (F4, `docs/contratos.md`).

`POST` multipart con dos partes, `event` (JSON) e `image` (JPEG), y el header
`Authorization: Bearer <P4_DEVICE_TOKEN>`. Cada rechazo responde con
`{error, mensaje, detalles}` y el codigo HTTP del contrato: nada se descarta en
silencio.
"""

from __future__ import annotations

import hmac
from functools import lru_cache
from typing import Annotated

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException

from p4.captures.errors import CaptureError
from p4.captures.event import CaptureEvent, parse_event
from p4.captures.image import ReceivedImage, inspect_image
from p4.captures.s3_store import S3CaptureStore, UnavailableStore
from p4.captures.settings import CaptureSettings, get_settings
from p4.captures.store import CaptureStore
from p4.captures.validation import validate_event

router = APIRouter(prefix="/api/p4/captures", tags=["p4-captures"])


SettingsDep = Annotated[CaptureSettings, Depends(get_settings)]


@lru_cache
def _s3_store(bucket: str, prefix: str, profile: str | None, region: str) -> CaptureStore:
    # Perfil vacio = cadena estandar de boto3 (rol de instancia en el despliegue).
    try:
        session = boto3.Session(profile_name=profile)
    except BotoCoreError as error:
        return UnavailableStore(f"perfil de AWS {profile!r} no disponible ({type(error).__name__})")
    client = session.client(
        "s3", region_name=region, config=Config(retries={"max_attempts": 3, "mode": "standard"})
    )
    return S3CaptureStore(client, bucket, prefix)


def get_store(settings: SettingsDep) -> CaptureStore | None:
    """Almacen de capturas en S3; `None` si no hay bucket configurado."""
    if not settings.bucket.strip():
        return None
    return _s3_store(settings.bucket, settings.prefix, settings.aws_profile, settings.aws_region)


StoreDep = Annotated[CaptureStore | None, Depends(get_store)]


def check_token(header: str | None, settings: CaptureSettings) -> None:
    if settings.device_token is None:
        raise CaptureError(
            503,
            "receptor_no_configurado",
            "El receptor no tiene P4_DEVICE_TOKEN configurado; no acepta envios",
        )
    scheme, _, token = (header or "").partition(" ")
    expected = settings.device_token.get_secret_value()
    if scheme.lower() != "bearer" or not hmac.compare_digest(token.encode(), expected.encode()):
        raise CaptureError(401, "no_autorizado", "Falta el token del dispositivo o no es valido")


async def read_parts(request: Request, max_image_bytes: int) -> tuple[str, bytes]:
    """Partes `event` e `image` del multipart. 400 si falta alguna o el cuerpo no es multipart."""
    try:
        form = await request.form(max_files=2, max_fields=2)
    except MultiPartException as error:
        raise CaptureError(
            400, "solicitud_invalida", f"El cuerpo no es multipart valido: {error.message}"
        ) from error
    event = form.get("event")
    image = form.get("image")
    if event is None:
        raise CaptureError(400, "solicitud_invalida", "Falta la parte 'event'")
    if image is None:
        raise CaptureError(400, "solicitud_invalida", "Falta la parte 'image'")
    if not isinstance(image, UploadFile):
        raise CaptureError(400, "solicitud_invalida", "La parte 'image' debe ser un archivo")
    # Se lee un byte de mas para saber si pasa del tope sin cargar archivos enormes.
    data = await image.read(max_image_bytes + 1)
    if isinstance(event, UploadFile):
        event = (await event.read()).decode("utf-8", errors="replace")
    return event, data


def _created(result_record: dict[str, object], record_key: str, status: str) -> dict[str, object]:
    return {
        "status": status,
        "capture_id": result_record["capture_id"],
        "image_key": result_record.get("image_key"),
        "record_key": record_key,
        "received_at": result_record.get("received_at"),
        "warnings": result_record.get("warnings", []),
    }


@router.post("", status_code=201)
async def receive_capture(request: Request, settings: SettingsDep, store: StoreDep) -> JSONResponse:
    """Recibe una captura: token, partes, imagen, forma y reglas del evento, y almacenamiento."""
    try:
        check_token(request.headers.get("authorization"), settings)
        event_text, data = await read_parts(request, settings.max_image_bytes)
        image: ReceivedImage = inspect_image(data, settings.max_image_bytes)
        event: CaptureEvent = parse_event(event_text)
        validate_event(event, image, settings)
        if store is None:
            raise CaptureError(
                503,
                "receptor_no_configurado",
                "El almacenamiento de capturas no esta configurado; reintenta con el mismo "
                "capture_id",
            )
        result = await run_in_threadpool(store.save, event, image)
    except CaptureError as error:
        return error.response()
    return JSONResponse(
        status_code=201 if result.status == "created" else 200,
        content=_created(result.record, result.record_key, result.status),
    )
