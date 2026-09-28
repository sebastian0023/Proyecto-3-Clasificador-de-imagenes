"""Configuracion del servicio de inferencia, leida del entorno (F4 T24).

- Paquetes de modelo: bucket y prefijo del registro (`registry.json`, contratos
  §6). Por defecto, el bucket del equipo en AWS S3 con el perfil de `~/.aws`
  montado en el contenedor; `P3_S3_ENDPOINT` apunta a MinIO para probar.
- Cola de anotacion: URL de la API de P1.
- Inferencias: la MariaDB del stack (mismas variables `DB_*` que el worker).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session, sessionmaker

from p3.inference.annotation import P1Annotation
from p3.inference.service import InferenceService, ModelUnavailableError


class InferenceSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    models_bucket: str = Field(
        default="dataset-quality-releases-750702272375", alias="P3_MODELS_BUCKET"
    )
    models_prefix: str = Field(default="models/clasificador", alias="P3_MODELS_PREFIX")
    aws_profile: str | None = Field(default=None, alias="P3_AWS_PROFILE")
    aws_region: str = Field(default="us-east-1", alias="P3_AWS_REGION")
    # Solo para probar contra MinIO antes de que F7 publique en S3.
    s3_endpoint: str | None = Field(default=None, alias="P3_S3_ENDPOINT")
    s3_access_key: str | None = Field(default=None, alias="P3_S3_ACCESS_KEY")
    s3_secret_key: SecretStr | None = Field(default=None, alias="P3_S3_SECRET_KEY")
    annotation_url: str = Field(
        default="http://host.docker.internal:3000", alias="P3_ANNOTATION_URL"
    )


@lru_cache
def get_settings() -> InferenceSettings:
    return InferenceSettings()


class S3ObjectStore:
    """`ObjectStore` sobre boto3 (AWS S3 o MinIO), solo lectura.

    Los usuarios IAM del equipo tienen `s3:GetObject` pero no
    `s3:GetObjectVersion`. Si leer por `VersionId` da AccessDenied, se lee la
    version actual y solo se acepta si su `VersionId` es el registrado; el
    servicio ademas exige el SHA-256 del registro.
    """

    def __init__(self, settings: InferenceSettings) -> None:
        import boto3

        if settings.s3_endpoint:
            secret = settings.s3_secret_key.get_secret_value() if settings.s3_secret_key else None
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=secret,
                region_name=settings.aws_region,
            )
        else:
            session = boto3.Session(profile_name=settings.aws_profile or None)
            self._client = session.client("s3", region_name=settings.aws_region)

    @classmethod
    def from_client(cls, client: Any) -> S3ObjectStore:
        store = cls.__new__(cls)
        store._client = client
        return store

    def get_bytes(self, bucket: str, key: str, version_id: str | None = None) -> bytes:
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            if version_id:
                try:
                    return self._client.get_object(Bucket=bucket, Key=key, VersionId=version_id)[
                        "Body"
                    ].read()
                except ClientError as error:
                    if error.response.get("Error", {}).get("Code") not in ("AccessDenied", "403"):
                        raise
            obj = self._client.get_object(Bucket=bucket, Key=key)
        except (ClientError, BotoCoreError) as error:
            raise ModelUnavailableError(f"No se pudo leer s3://{bucket}/{key}: {error}") from error
        current = obj.get("VersionId")
        if version_id and current != version_id:
            raise ModelUnavailableError(
                f"s3://{bucket}/{key} esta en la version {current}; el registro dice {version_id} "
                "y estas credenciales no pueden leer versiones anteriores."
            )
        return obj["Body"].read()


@lru_cache
def get_inference_service() -> InferenceService:
    settings = get_settings()
    return InferenceService(
        S3ObjectStore(settings), bucket=settings.models_bucket, prefix=settings.models_prefix
    )


@lru_cache
def get_annotation_queue() -> P1Annotation:
    return P1Annotation(get_settings().annotation_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    from p3.inference.records import create_schema
    from p3.worker.settings import get_engine

    engine = get_engine()
    create_schema(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
