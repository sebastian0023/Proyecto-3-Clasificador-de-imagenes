"""API de versiones de modelo para la pagina Models (F7, contratos §4; criterios 5.3 y 6.4).

Corre en el servicio `p3-inference`, que tiene el perfil de AWS; el portal de P2
la reenvia (`p3.registry.proxy`).

- `GET /api/p3/models`: versiones del `registry.json` con su estado REAL en S3
  (`exists` sale de `head-object`, no del registro).
- `GET /api/p3/models/{version}/card`: la `MODEL_CARD.md` de esa version.
- `POST /api/p3/models/{version}/activate`: cambia la version activa solo si su
  `model.pt` existe y su SHA-256 coincide (`p3.registry.publish`). El servicio
  de inferencia lee el registro en cada prediccion, asi que el cambio aplica sin
  reiniciar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Response

from p3.registry.publish import (
    ObjectStore,
    PublishError,
    activate_version,
    list_versions,
    read_registry,
)

router = APIRouter(prefix="/api/p3/models", tags=["p3-models"])
Version = Annotated[str, Path(pattern=r"^\d+\.\d+\.\d+$")]


@dataclass(frozen=True)
class ModelsStore:
    store: ObjectStore
    bucket: str
    prefix: str


def get_models_store() -> ModelsStore:
    from p3.inference.settings import get_settings
    from p3.registry.s3 import S3Store

    settings = get_settings()
    if settings.s3_endpoint:
        import boto3

        secret = settings.s3_secret_key.get_secret_value() if settings.s3_secret_key else None
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=secret,
            region_name=settings.aws_region,
        )
        store = S3Store(client)
    else:
        store = S3Store.from_profile(settings.aws_profile, settings.aws_region)
    return ModelsStore(store=store, bucket=settings.models_bucket, prefix=settings.models_prefix)


StoreDep = Annotated[ModelsStore, Depends(get_models_store)]


@router.get("")
def read_models(models: StoreDep) -> dict[str, Any]:
    return list_versions(models.store, bucket=models.bucket, prefix=models.prefix)


@router.get("/{version}/card")
def read_card(version: Version, models: StoreDep) -> Response:
    registry = read_registry(models.store, bucket=models.bucket, prefix=models.prefix)
    entry = next((e for e in registry.versions if e.version == version), None)
    if entry is None:
        raise HTTPException(404, f"La version de modelo {version} no esta publicada.")
    card_key = entry.model_dump().get("card_key") or f"{models.prefix}/{version}/MODEL_CARD.md"
    data = models.store.get_bytes(models.bucket, card_key)
    return Response(data, media_type="text/markdown; charset=utf-8")


@router.post("/{version}/activate")
def activate(version: Version, models: StoreDep) -> dict[str, Any]:
    registry = read_registry(models.store, bucket=models.bucket, prefix=models.prefix)
    if all(entry.version != version for entry in registry.versions):
        raise HTTPException(404, f"La version de modelo {version} no esta publicada.")
    try:
        activate_version(models.store, bucket=models.bucket, prefix=models.prefix, version=version)
    except PublishError as error:
        raise HTTPException(409, str(error)) from error
    return list_versions(models.store, bucket=models.bucket, prefix=models.prefix)
