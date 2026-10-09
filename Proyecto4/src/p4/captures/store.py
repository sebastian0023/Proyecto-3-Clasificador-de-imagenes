"""Interfaz del almacenamiento de capturas.

El router solo conoce `CaptureStore`; la implementacion sobre S3 (decision 5)
la entrega el bloque de persistencia. Las pruebas usan un almacen en memoria.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from p4.captures.event import CaptureEvent
from p4.captures.image import ReceivedImage


@dataclass(frozen=True)
class SaveResult:
    status: Literal["created", "duplicate"]
    record: dict[str, object]
    record_key: str


class CaptureStore(Protocol):
    def save(self, event: CaptureEvent, image: ReceivedImage) -> SaveResult: ...
