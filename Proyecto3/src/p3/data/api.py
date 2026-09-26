"""API de releases de P2 para la pagina Training (F2 T05, criterios 1.1 y 6.1).

Se monta en la app de Proyecto2, igual que `p3.worker.api`. Solo lee el
registro de releases; generar el manifiesto es de F3 (`POST /api/p3/manifests`),
que usa `get_approved_release` y hereda el mismo 409.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from p3.data import releases
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


ReleasesDep = Annotated[list[Release], Depends(get_releases)]
BucketDep = Annotated[str, Depends(get_releases_bucket)]
RemoteDep = Annotated[str, Depends(get_releases_remote)]


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

    @classmethod
    def build(cls, release: Release, bucket: str, remote: str) -> ReleaseView:
        in_bucket = remote in release.published_in
        return cls(
            release_id=release.release_id,
            dataset_fingerprint=release.dataset_fingerprint,
            quality_status=release.quality_status,
            created_at=release.created_at,
            counts=release.counts,
            storage_uri=releases.archive_uri(bucket, release.release_id) if in_bucket else None,
            published_in=list(release.published_in),
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
    approved: Annotated[bool, Query()] = False,
) -> ReleaseList:
    selected = releases.approved_releases(all_releases) if approved else all_releases
    return ReleaseList(releases=[ReleaseView.build(r, bucket, remote) for r in selected])


@router.get("/{release_id}")
def read_release(
    release_id: str, all_releases: ReleasesDep, bucket: BucketDep, remote: RemoteDep
) -> ReleaseDetail:
    try:
        release = releases.get_approved_release(all_releases, release_id)
    except releases.ReleaseNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except releases.ReleaseNotApprovedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    view = ReleaseView.build(release, bucket, remote)
    return ReleaseDetail(
        **view.model_dump(),
        quality_report_fingerprint=release.quality_report_fingerprint,
        archive_sha256=release.archive_sha256,
    )
