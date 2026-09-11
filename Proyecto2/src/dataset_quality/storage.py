"""Acceso al almacenamiento de objetos (MinIO en local, S3 en AWS)."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import boto3
from botocore.client import Config

from dataset_quality.settings import Settings, get_settings

if TYPE_CHECKING:  # pragma: no cover - solo para tipado
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


@lru_cache
def get_s3_client() -> S3Client:
    """Cliente S3 apuntando a MinIO (o al S3 real segun `.env`)."""
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint_url,
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password.get_secret_value(),
        config=Config(signature_version="s3v4", retries={"max_attempts": 2}),
        region_name="us-east-1",
    )


def check_object_storage(settings: Settings | None = None) -> None:
    """Lanza una excepcion si falta algun bucket o MinIO no responde."""
    settings = settings or get_settings()
    client = get_s3_client()
    for bucket in settings.buckets:
        client.head_bucket(Bucket=bucket)
