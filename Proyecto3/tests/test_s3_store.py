"""Lectura del modelo publicado por `VersionId` con credenciales de minimo privilegio (F4 T24).

Los usuarios IAM del equipo tienen `s3:GetObject` pero no `s3:GetObjectVersion`
(el del evaluador tiene ambos). Si leer por version da AccessDenied, se lee la
version actual y solo se acepta si su `VersionId` es el registrado.
"""

from __future__ import annotations

import io

import pytest
from botocore.exceptions import ClientError

from p3.inference.service import ModelUnavailableError
from p3.inference.settings import S3ObjectStore


class FakeClient:
    def __init__(self, *, permite_version: bool, version_actual: str) -> None:
        self.permite_version = permite_version
        self.version_actual = version_actual
        self.llamadas: list[dict] = []

    def get_object(self, **kwargs):
        self.llamadas.append(kwargs)
        if "VersionId" in kwargs and not self.permite_version:
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "no"}}, "GetObject")
        return {"Body": io.BytesIO(b"pesos"), "VersionId": self.version_actual}


def test_con_permiso_de_version_lee_esa_version() -> None:
    client = FakeClient(permite_version=True, version_actual="v2")
    store = S3ObjectStore.from_client(client)
    assert store.get_bytes("b", "k", "v1") == b"pesos"
    assert client.llamadas == [{"Bucket": "b", "Key": "k", "VersionId": "v1"}]


def test_sin_permiso_de_version_acepta_la_actual_si_es_la_registrada() -> None:
    client = FakeClient(permite_version=False, version_actual="v1")
    store = S3ObjectStore.from_client(client)
    assert store.get_bytes("b", "k", "v1") == b"pesos"
    assert client.llamadas[-1] == {"Bucket": "b", "Key": "k"}


def test_sin_permiso_de_version_rechaza_si_la_actual_es_otra() -> None:
    client = FakeClient(permite_version=False, version_actual="v9")
    store = S3ObjectStore.from_client(client)
    with pytest.raises(ModelUnavailableError, match="v9"):
        store.get_bytes("b", "k", "v1")


def test_sin_version_registrada_lee_la_actual() -> None:
    client = FakeClient(permite_version=False, version_actual="v1")
    assert S3ObjectStore.from_client(client).get_bytes("b", "k") == b"pesos"
