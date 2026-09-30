"""Robustez del `S3Store` de modelos ante un arranque sin credenciales (F10).

Sin `~/.aws` ni MinIO configurado, boto3 lanza `NoCredentialsError` al leer el
registro. `head` debe tomarlo como "registro no accesible" (None), para que
`GET /api/p3/models` responda una lista vacia en vez de 500. Un `NoSuchKey`
tambien es None; cualquier otro `ClientError` sigue propagando.
"""

from __future__ import annotations

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from p3.registry.s3 import S3Store


class _Client:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def head_object(self, **_kwargs: object) -> dict[str, object]:
        raise self._error


def test_head_none_sin_credenciales() -> None:
    assert S3Store(_Client(NoCredentialsError())).head("bucket", "registry.json") is None


def test_head_none_si_no_existe() -> None:
    no_such = ClientError({"Error": {"Code": "NoSuchKey"}}, "HeadObject")
    assert S3Store(_Client(no_such)).head("bucket", "registry.json") is None


def test_head_propaga_otros_errores() -> None:
    denied = ClientError({"Error": {"Code": "AccessDenied"}}, "HeadObject")
    with pytest.raises(ClientError):
        S3Store(_Client(denied)).head("bucket", "registry.json")
