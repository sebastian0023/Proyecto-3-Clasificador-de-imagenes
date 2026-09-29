"""API de manifiestos para la pagina Training (F3, contratos §4; criterios 3.1, 6.1 y M3).

Se monta en la app de Proyecto2, igual que `p3.data.api`.

- `POST /api/p3/manifests`: el manifiesto de un release aprobado y una semilla.
  No genera uno nuevo: el worker solo entrena con los congelados
  (`p3.data.frozen`), asi que devuelve el congelado de ese release y esa semilla
  despues de comprobar que sus bytes son los congelados. Es idempotente y no
  escribe nada. Generar un manifiesto nuevo es `scripts/generate_manifest.py`
  (reproducible byte a byte) y congelarlo entra por PR.
- `GET /api/p3/manifests/{manifest_id}`: el `manifest.meta.json`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Path as PathParam
from pydantic import BaseModel, ConfigDict, StrictInt

from p3.data import releases
from p3.data.api import ReleasesDep
from p3.data.frozen import FROZEN_MANIFESTS, ManifestNotFrozenError, verify_frozen

router = APIRouter(prefix="/api/p3/manifests", tags=["p3-manifests"])

# `m-<release_id>-s<seed>-<n>` (docs/manifiesto.md). Tambien impide salir de la carpeta.
MANIFEST_ID = r"^m-(?P<release>\d+\.\d+\.\d+)-s(?P<seed>\d+)-(?P<n>\d+)$"


def get_manifests_dir() -> Path:
    from p3.data.settings import get_settings

    return get_settings().manifests_dir


def get_frozen() -> Mapping[str, str]:
    return FROZEN_MANIFESTS


ManifestsDirDep = Annotated[Path, Depends(get_manifests_dir)]
FrozenDep = Annotated[Mapping[str, str], Depends(get_frozen)]
ManifestId = Annotated[str, PathParam(pattern=MANIFEST_ID)]


class ManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release_id: str
    seed: StrictInt


class ManifestCreated(BaseModel):
    manifest_id: str
    manifest_hash: str
    counts: dict[str, Any]


def _frozen_for(frozen: Mapping[str, str], release_id: str, seed: int) -> str | None:
    """El congelado de ese release y esa semilla (el de mayor `n` si hubiera varios)."""
    found = []
    for manifest_id in frozen:
        match = re.match(MANIFEST_ID, manifest_id)
        if match and match["release"] == release_id and int(match["seed"]) == seed:
            found.append((int(match["n"]), manifest_id))
    return max(found)[1] if found else None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_manifest(
    body: ManifestRequest, all_releases: ReleasesDep, folder: ManifestsDirDep, frozen: FrozenDep
) -> ManifestCreated:
    try:
        releases.get_approved_release(all_releases, body.release_id)
    except releases.ReleaseNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except releases.ReleaseNotApprovedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    manifest_id = _frozen_for(frozen, body.release_id, body.seed)
    if manifest_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"No hay manifiesto congelado para el release {body.release_id} con seed "
            f"{body.seed}; solo se entrena con {sorted(frozen)}. Uno nuevo se genera con "
            "scripts/generate_manifest.py y se congela por PR (p3.data.frozen).",
        )
    manifest_dir = folder / manifest_id
    if not (manifest_dir / "manifest.jsonl").is_file():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"El manifiesto congelado {manifest_id} no esta descargado; corre "
            f"`dvc pull data/manifests/{manifest_id}.dvc` en Proyecto3.",
        )
    try:
        meta = verify_frozen(manifest_dir, frozen)
    except ManifestNotFrozenError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    meta_release = meta.get("release", {}).get("release_id")
    if meta_release != body.release_id or meta.get("seed") != body.seed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El meta de {manifest_id} no corresponde al release {body.release_id} "
            f"con seed {body.seed}.",
        )
    return ManifestCreated(
        manifest_id=manifest_id, manifest_hash=meta["manifest_hash"], counts=meta["counts"]
    )


@router.get("/{manifest_id}")
def read_manifest(manifest_id: ManifestId, folder: ManifestsDirDep) -> dict[str, Any]:
    meta_path = folder / manifest_id / "manifest.meta.json"
    if not meta_path.is_file():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No existe el manifiesto {manifest_id} (o falta `dvc pull`).",
        )
    return json.loads(meta_path.read_text(encoding="utf-8"))
