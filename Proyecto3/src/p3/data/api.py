"""API de releases de P2 para la pagina Training (F2 T05, criterios 1.1 y 6.1).

Se monta en la app de Proyecto2, igual que `p3.worker.api`. Solo lee el
registro de releases; generar el manifiesto es de F3 (`POST /api/p3/manifests`),
que usa `get_approved_release` y hereda el mismo 409.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from p3.data import releases
from p3.data.frozen import FROZEN_MANIFESTS, TRAINING_SEED, frozen_for
from p3.data.releases import Release, ReleaseCounts

router = APIRouter(prefix="/api/p3/releases", tags=["p3-releases"])


def get_releases() -> list[Release]:
    from p3.data.settings import get_settings

    return releases.load_releases(get_settings().versions_path)


def get_releases_bucket() -> str:
    from p3.data.settings import get_settings

    return get_settings().releases_bucket


def get_releases_remote() -> str:
    from p3.data.settings import get_settings

    return get_settings().releases_remote


def get_frozen() -> Mapping[str, str]:
    return FROZEN_MANIFESTS


ReleasesDep = Annotated[list[Release], Depends(get_releases)]
FrozenDep = Annotated[Mapping[str, str], Depends(get_frozen)]
BucketDep = Annotated[str, Depends(get_releases_bucket)]
RemoteDep = Annotated[str, Depends(get_releases_remote)]


def training_block(release: Release, frozen: Mapping[str, str]) -> str | None:
    """Por que no se puede entrenar con este release, o `None` si se puede.

    Sin `archive_sha256` su archivo no se puede verificar; sin manifiesto
    congelado con la semilla de entrenamiento el worker lo rechaza.
    """
    if not release.archive_sha256:
        return "no registra archive_sha256"
    if frozen_for(release.release_id, TRAINING_SEED, frozen) is None:
        return "sin manifiesto congelado"
    return None


class ReleaseView(BaseModel):
    release_id: str
    dataset_fingerprint: str
    quality_status: str
    created_at: datetime
    counts: ReleaseCounts
    # `None` si el release no esta en el bucket del equipo: solo existe en el
    # MinIO local de quien lo genero y desde un clon limpio no se recupera.
    storage_uri: str | None
    published_in: list[str]
    # Training deshabilita los que no se pueden entrenar y muestra el motivo.
    trainable: bool
    blocked_reason: str | None

    @classmethod
    def build(
        cls, release: Release, bucket: str, remote: str, frozen: Mapping[str, str]
    ) -> ReleaseView:
        in_bucket = remote in release.published_in
        blocked = training_block(release, frozen)
        return cls(
            release_id=release.release_id,
            dataset_fingerprint=release.dataset_fingerprint,
            quality_status=release.quality_status,
            created_at=release.created_at,
            counts=release.counts,
            storage_uri=releases.archive_uri(bucket, release.release_id) if in_bucket else None,
            published_in=list(release.published_in),
            trainable=blocked is None,
            blocked_reason=blocked,
        )


class ReleaseDetail(ReleaseView):
    quality_report_fingerprint: str
    archive_sha256: str | None


class ReleaseList(BaseModel):
    releases: list[ReleaseView]


@router.get("")
def list_releases(
    all_releases: ReleasesDep,
    bucket: BucketDep,
    remote: RemoteDep,
    frozen: FrozenDep,
    approved: Annotated[bool, Query()] = False,
) -> ReleaseList:
    selected = releases.approved_releases(all_releases) if approved else all_releases
    return ReleaseList(releases=[ReleaseView.build(r, bucket, remote, frozen) for r in selected])


@router.get("/{release_id}")
def read_release(
    release_id: str,
    all_releases: ReleasesDep,
    bucket: BucketDep,
    remote: RemoteDep,
    frozen: FrozenDep,
) -> ReleaseDetail:
    try:
        release = releases.get_approved_release(all_releases, release_id)
    except releases.ReleaseNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except releases.ReleaseNotApprovedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    view = ReleaseView.build(release, bucket, remote, frozen)
    return ReleaseDetail(
        **view.model_dump(),
        quality_report_fingerprint=release.quality_report_fingerprint,
        archive_sha256=release.archive_sha256,
    )
