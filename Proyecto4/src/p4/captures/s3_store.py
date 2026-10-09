"""Almacen de capturas en S3 (decision 5): imagen y registro por `capture_id`.

```
{prefix}images/{capture_id}.jpg     metadatos S3: sha256, capture-id
{prefix}events/{capture_id}.json    evento + campos del receptor
```

Idempotencia (contrato, regla 3): las dos escrituras usan `If-None-Match: *`,
primero la imagen y despues el registro, asi que un registro nunca apunta a una
imagen inexistente. Si la llave ya existe (412), se compara lo guardado con lo
recibido: igual → `duplicate` sin escribir; distinto → 409 con los campos que
difieren. Nunca se sobrescribe ni se borra.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from p4.captures.errors import CaptureError
from p4.captures.event import CaptureEvent
from p4.captures.image import ReceivedImage
from p4.captures.store import SaveResult
from p4.captures.validation import assess_timing

# Campos que envia el dispositivo: los que deciden si un reintento es identico.
DEVICE_FIELDS = tuple(CaptureEvent.model_fields)
# S3 responde 412 cuando `If-None-Match: *` encuentra la llave.
EXISTS = {"PreconditionFailed", "412"}
RETRY = "Reintenta con el mismo capture_id"


def build_record(
    event: CaptureEvent, image: ReceivedImage, image_key: str, received_at: datetime
) -> dict[str, Any]:
    """Registro que se guarda: el evento tal cual mas los campos del receptor."""
    delay, warnings = assess_timing(event, received_at)
    record: dict[str, Any] = event.model_dump(mode="json")
    record.update(
        received_at=received_at.astimezone(UTC).isoformat(timespec="milliseconds"),
        image_key=image_key,
        image_bytes=image.size,
        image_width=image.width,
        image_height=image.height,
        delivery_delay_s=round(delay, 3),
        warnings=warnings,
    )
    return record


def _code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


def unavailable(error: Exception) -> CaptureError:
    reason = _code(error) if isinstance(error, ClientError) else type(error).__name__
    return CaptureError(
        503,
        "almacenamiento_no_disponible",
        f"S3 no aceptó la operación ({reason}). {RETRY}",
    )


def conflict(differences: list[dict[str, object]]) -> CaptureError:
    return CaptureError(
        409,
        "conflicto_capture_id",
        "El capture_id ya existe con otros datos; no se sobrescribe",
        differences,
    )


class S3CaptureStore:
    def __init__(
        self,
        client: Any,
        bucket: str,
        prefix: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.client = client
        self.bucket = bucket
        self.prefix = prefix
        self.clock = clock

    def image_key(self, capture_id: str) -> str:
        return f"{self.prefix}images/{capture_id}.jpg"

    def record_key(self, capture_id: str) -> str:
        return f"{self.prefix}events/{capture_id}.json"

    def save(self, event: CaptureEvent, image: ReceivedImage) -> SaveResult:
        received_at = self.clock()
        image_key = self.image_key(event.capture_id)
        record_key = self.record_key(event.capture_id)
        try:
            self._put_image(image_key, event.capture_id, image)
            record = build_record(event, image, image_key, received_at)
            if self._put_new(record_key, _dump(record), "application/json", {}):
                return SaveResult("created", record, record_key)
            stored = json.loads(self._get(record_key))
        except (ClientError, BotoCoreError) as error:
            raise unavailable(error) from error
        differences = _differences(stored, event)
        if differences:
            raise conflict(differences)
        return SaveResult("duplicate", stored, record_key)

    def _put_image(self, key: str, capture_id: str, image: ReceivedImage) -> None:
        metadata = {"sha256": image.sha256, "capture-id": capture_id}
        if self._put_new(key, image.data, "image/jpeg", metadata):
            return
        # Ya existe: es un reintento (quizas tras una falla a la mitad) solo si es la misma foto.
        stored_sha = self.client.head_object(Bucket=self.bucket, Key=key)["Metadata"].get("sha256")
        if stored_sha != image.sha256:
            raise conflict(
                [{"campo": "image_sha256", "guardado": stored_sha, "recibido": image.sha256}]
            )

    def _put_new(self, key: str, body: bytes, content_type: str, metadata: dict[str, str]) -> bool:
        """`True` si se escribio; `False` si la llave ya existia (no se toca)."""
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                Metadata=metadata,
                IfNoneMatch="*",
            )
        except ClientError as error:
            if _code(error) in EXISTS:
                return False
            raise
        return True

    def _get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


def _dump(record: dict[str, Any]) -> bytes:
    return json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")


def _differences(stored: dict[str, Any], event: CaptureEvent) -> list[dict[str, object]]:
    received = event.model_dump(mode="json")
    return [
        {"campo": name, "guardado": stored.get(name), "recibido": received[name]}
        for name in DEVICE_FIELDS
        if stored.get(name) != received[name]
    ]


class UnavailableStore:
    """Almacen que no se pudo construir (perfil inexistente, sin bucket): 503 con el motivo."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def save(self, event: CaptureEvent, image: ReceivedImage) -> SaveResult:
        raise CaptureError(
            503, "receptor_no_configurado", f"Almacenamiento no disponible: {self.reason}. {RETRY}"
        )
