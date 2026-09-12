"""`versions.json`: el contrato de salida congelado del registro de versiones.

Cada entrada representa una publicacion inmutable y content-addressed del
dataset (Frente 6, `dvc`) hacia el almacenamiento de objetos. Como en
`splits.py`, aqui solo se fija la forma exacta para desbloquear a los frentes
que la consumen (7 y 8).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from dataset_quality.models import StrictModel

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class DatasetCounts(StrictModel):
    """Conteos del dataset en esta version."""

    images: int = Field(ge=0)
    annotations: int = Field(ge=0)
    categories: int = Field(ge=0)


class DatasetVersion(StrictModel):
    """Una version publicada e inmutable del dataset."""

    schema_version: Literal[1] = 1
    version: str
    created_at: datetime
    dataset_fingerprint: str
    quality_report_fingerprint: str
    splits_fingerprint: str
    storage_uri: str = Field(min_length=1)
    quality_status: Literal["pass", "fail"]
    counts: DatasetCounts
    notes: str | None = None

    @field_validator("version")
    @classmethod
    def _version_semver(cls, value: str) -> str:
        if not _SEMVER.match(value):
            raise ValueError(f"debe tener forma semver X.Y.Z (recibido: {value!r})")
        return value

    @field_validator("dataset_fingerprint", "quality_report_fingerprint", "splits_fingerprint")
    @classmethod
    def _fingerprint_sha256(cls, value: str) -> str:
        if not _SHA256_HEX.match(value):
            mensaje = "debe ser un sha256 hexadecimal de 64 caracteres"
            raise ValueError(f"{mensaje} (recibido: {value!r})")
        return value

    @field_validator("storage_uri")
    @classmethod
    def _storage_uri_es_s3(cls, value: str) -> str:
        if not value.startswith("s3://"):
            raise ValueError(f"debe empezar con 's3://' (recibido: {value!r})")
        return value


class VersionsManifest(StrictModel):
    """Contrato congelado de `versions.json`: el registro completo de versiones."""

    schema_version: Literal[1] = 1
    versions: list[DatasetVersion]

    @model_validator(mode="after")
    def _versiones_unicas_y_en_orden(self) -> VersionsManifest:
        nombres = [entry.version for entry in self.versions]
        if len(nombres) != len(set(nombres)):
            duplicadas = sorted({name for name in nombres if nombres.count(name) > 1})
            raise ValueError(f"version duplicada en el registro: {duplicadas}")

        fechas = [entry.created_at for entry in self.versions]
        if fechas != sorted(fechas):
            raise ValueError("versions debe estar en orden cronologico por created_at")
        return self
