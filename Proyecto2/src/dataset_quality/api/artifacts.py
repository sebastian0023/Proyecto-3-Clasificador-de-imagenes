"""Endpoints que sirven los artefactos del pipeline a la app web.

Cada artefacto se lee de `reports/`, se **valida contra su contrato** y se
devuelve envuelto en un sobre que dice de donde salio:

    {"source": "pipeline", "produced_by": "dq gate", "data": {...}}

Validar antes de servir no es ceremonia: si un archivo en disco dejo de cumplir
su contrato — porque alguien cambio un modelo y no regenero el artefacto — es
mejor un 500 que lo diga que una pantalla pintando basura en silencio.

Ningun endpoint recalcula nada. La app web dibuja lo que el pipeline decidio, y
esa separacion es la que permite construir la UI contra los contratos sin
esperar a que el pipeline termine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from dataset_quality.models.exploration import ExplorationManifest
from dataset_quality.models.quality import QualityReport
from dataset_quality.models.splits import SplitsManifest
from dataset_quality.models.stats import AnalysisArtifact
from dataset_quality.models.versions import VersionsManifest, backfill_remotes

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "reports"

router = APIRouter(prefix="/api", tags=["artefactos"])


@dataclass(frozen=True)
class Artifact:
    """Un artefacto del pipeline: donde vive, que contrato cumple y quien lo crea."""

    name: str
    path: Path
    model: type
    produced_by: str


ARTIFACTS: dict[str, Artifact] = {
    "quality": Artifact("quality", REPORTS / "quality.json", QualityReport, "dq gate"),
    "splits": Artifact("splits", REPORTS / "splits.json", SplitsManifest, "dq split"),
    "versions": Artifact("versions", REPORTS / "versions.json", VersionsManifest, "dq release"),
    "exploration": Artifact(
        "exploration", REPORTS / "exploration.json", ExplorationManifest, "dq analyze"
    ),
    "stats": Artifact("stats", REPORTS / "stats.json", AnalysisArtifact, "dq analyze --json"),
}


@dataclass(frozen=True)
class LoadedArtifact:
    """Artefacto validado y su revision inmutable para consumidores internos."""

    artifact: Artifact
    data: Any
    revision: str

    def source(self) -> dict[str, str | None]:
        generated_at = getattr(self.data, "generated_at", None)
        dataset_fingerprint = getattr(self.data, "dataset_fingerprint", None)
        return {
            "artifact": self.artifact.path.name,
            "artifact_revision": self.revision,
            "generated_at": generated_at.isoformat() if generated_at is not None else None,
            "dataset_fingerprint": dataset_fingerprint,
        }


def read(artifact: Artifact) -> LoadedArtifact:
    """Lee y valida un artefacto; nunca entrega JSON no validado al Copilot."""
    if not artifact.path.is_file():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Todavia no existe `{artifact.path.name}`. "
                f"Corre `{artifact.produced_by}` para generarlo."
            ),
        )

    try:
        raw = artifact.path.read_bytes()
        validado = artifact.model.model_validate_json(raw)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"`{artifact.path.name}` ya no cumple el contrato de "
                f"{artifact.model.__name__}: {error}"
            ),
        ) from error

    return LoadedArtifact(artifact=artifact, data=validado, revision=sha256(raw).hexdigest())


def load(artifact: Artifact) -> dict[str, Any]:
    """Envuelve un artefacto validado para los endpoints de la SPA."""
    loaded = read(artifact)
    return {
        "source": "pipeline",
        "produced_by": artifact.produced_by,
        "data": json.loads(loaded.data.model_dump_json()),
    }


@router.get("/status")
def status() -> dict[str, Any]:
    """Que artefactos existen. La app lo consulta al arrancar para orientarse."""
    return {
        name: {"available": artifact.path.is_file(), "produced_by": artifact.produced_by}
        for name, artifact in ARTIFACTS.items()
    }


@router.get("/quality")
def quality() -> dict[str, Any]:
    """Overview y Analyzers: el veredicto de la compuerta, valor contra umbral."""
    return load(ARTIFACTS["quality"])


@router.get("/splits")
def splits() -> dict[str, Any]:
    """Splits: reparto train/val/test, su semilla y sus conteos."""
    return load(ARTIFACTS["splits"])


@router.get("/versions")
def versions() -> dict[str, Any]:
    """Versions: historial de releases, sus tres huellas y donde esta cada una.

    Las entradas anteriores a `published_in` pasan por `backfill_remotes`: sin
    eso la pantalla mostraria como "sin publicar" versiones que llevan meses en
    el remote. La migracion se aplica al leer, nunca al escribir.
    """
    loaded = read(ARTIFACTS["versions"])
    migrado = backfill_remotes(loaded.data)
    return {
        "source": "pipeline",
        "produced_by": ARTIFACTS["versions"].produced_by,
        "data": json.loads(migrado.model_dump_json()),
    }


@router.get("/exploration")
def exploration() -> dict[str, Any]:
    """Exploracion: la proyeccion 2D precomputada."""
    return load(ARTIFACTS["exploration"])



@router.get("/stats")
def stats() -> dict[str, Any]:
    """Descriptiva del Tier 2: el contexto sin el cual un umbral no dice nada."""
    return load(ARTIFACTS["stats"])
