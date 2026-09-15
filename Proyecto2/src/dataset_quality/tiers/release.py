"""Tier 5 — publicar una version del dataset.

Empaqueta el dataset validado junto con sus dos reportes (`quality.json`,
`splits.json`) en un artefacto inmutable y content-addressed, lo sube al
almacen de objetos y añade la entrada a `versions.json` — el tercer y ultimo
contrato congelado que quedaba sin productor (Frente 6, `dvc`).

Tres propiedades que exige la tarjeta:

  - **Pipeline por etapas**: este modulo es la ultima etapa del grafo de DVC
    (`analyze -> gate -> split -> release`); `dq ingest` queda fuera porque
    escribe en MinIO/MariaDB y no es una funcion pura de archivo a archivo.
  - **Datos fuera de Git**: el `.tar.zst` va al bucket de releases, nunca al
    repositorio; lo que se versiona en Git es `dvc.lock` (el hash) y este
    `versions.json` (el registro).
  - **El mismo content hash en cualquier remote**: el archivo se arma con
    metadata determinista (mtime fijo, orden fijo de miembros), asi que el
    mismo contenido da siempre el mismo `dataset_fingerprint` sin importar a
    que remote (`dev` o `prod`) se suba despues.

Salida: `reports/versions.json` + `s3://<bucket-releases>/<version>/dataset.tar.zst`.
"""

from __future__ import annotations

import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import zstandard

from dataset_quality.models.quality import QualityReport
from dataset_quality.models.splits import SplitsManifest
from dataset_quality.models.versions import DatasetCounts, DatasetVersion, VersionsManifest
from dataset_quality.storage import ensure_bucket, file_sha256, get_s3_client

DEFAULT_VERSIONS_PATH = Path("reports") / "versions.json"
ARCHIVE_NAME = "dataset.tar.zst"

Bump = str  # "patch" | "minor" | "major"


def load_manifest(path: Path = DEFAULT_VERSIONS_PATH) -> VersionsManifest:
    """Lee `versions.json`, o un registro vacio si nunca se publico nada."""
    if not path.is_file():
        return VersionsManifest(versions=[])
    return VersionsManifest.model_validate_json(path.read_text(encoding="utf-8"))


def next_version(manifest: VersionsManifest, bump: Bump = "patch") -> str:
    """Siguiente semver a partir de la ultima entrada del registro.

    Sin historial, arranca en `0.1.0`. El orden cronologico ya lo garantiza
    `VersionsManifest`, asi que la ultima entrada de la lista es la mas
    reciente por construccion — no hace falta volver a ordenar aqui.
    """
    if not manifest.versions:
        return "0.1.0"

    major, minor, patch = (int(part) for part in manifest.versions[-1].version.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def build_archive(
    *,
    coco_path: Path,
    quality_path: Path,
    splits_path: Path,
    dest: Path,
) -> Path:
    """Empaqueta los tres artefactos en un `.tar.zst` deterministico.

    Determinista quiere decir: mismo contenido -> mismos bytes de archivo,
    sin importar cuando ni donde se corra. Dos cosas lo rompen si no se
    controlan explicitamente: el orden de iteracion del filesystem (se fija
    ordenando los miembros por nombre) y el mtime de cada entrada (tar lo
    incluye en la cabecera; se fija a época 0). Sin esto, el "mismo content
    hash entre remotes" de la tarjeta seria falso en la practica aunque el
    dataset no hubiera cambiado ni un byte.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    members = sorted(
        [
            (coco_path, "annotations.coco.json"),
            (quality_path, "quality.json"),
            (splits_path, "splits.json"),
        ],
        key=lambda pair: pair[1],
    )

    compressor = zstandard.ZstdCompressor(level=19)
    with (
        dest.open("wb") as raw,
        compressor.stream_writer(raw) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as archive,
    ):
        for source, arcname in members:
            info = archive.gettarinfo(source, arcname=arcname)
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with source.open("rb") as handle:
                archive.addfile(info, handle)

    return dest


def storage_uri(bucket: str, version: str) -> str:
    return f"s3://{bucket}/{version}/{ARCHIVE_NAME}"


def build_entry(
    *,
    version: str,
    dataset_fingerprint: str,
    quality_report: QualityReport,
    quality_report_fingerprint: str,
    splits_fingerprint: str,
    bucket: str,
    notes: str | None,
) -> DatasetVersion:
    """Ensambla la entrada de `versions.json`. Funcion pura: sin disco ni red."""
    return DatasetVersion(
        version=version,
        created_at=datetime.now(UTC),
        dataset_fingerprint=dataset_fingerprint,
        quality_report_fingerprint=quality_report_fingerprint,
        splits_fingerprint=splits_fingerprint,
        storage_uri=storage_uri(bucket, version),
        quality_status=quality_report.status,
        counts=DatasetCounts(
            images=quality_report.totals.images,
            annotations=quality_report.totals.annotations,
            categories=quality_report.totals.categories,
        ),
        notes=notes,
    )


def append_entry(manifest: VersionsManifest, entry: DatasetVersion) -> VersionsManifest:
    """Añade una entrada al registro. El validador exige orden cronologico."""
    return VersionsManifest(versions=[*manifest.versions, entry])


def write_manifest(manifest: VersionsManifest, path: Path = DEFAULT_VERSIONS_PATH) -> Path:
    """Escribe `versions.json`. El archivo se puede releer con su propio modelo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def upload_archive(archive_path: Path, bucket: str, version: str) -> None:
    """Sube el `.tar.zst` al bucket de releases."""
    ensure_bucket(bucket)
    key = f"{version}/{ARCHIVE_NAME}"
    get_s3_client().upload_file(str(archive_path), bucket, key)


@dataclass
class ReleaseResult:
    entry: DatasetVersion
    manifest: VersionsManifest
    archive_path: Path


def run(
    *,
    coco_path: Path,
    quality_report_path: Path,
    splits_path: Path,
    dataset_fingerprint: str,
    bucket: str,
    bump: Bump = "patch",
    version: str | None = None,
    notes: str | None = None,
    out: Path = DEFAULT_VERSIONS_PATH,
    archive_dir: Path = Path("reports") / "releases",
    upload: bool = True,
) -> ReleaseResult:
    """Empaqueta, sube y registra una version. `upload=False` es `--dry-run`."""
    quality_report = QualityReport.model_validate_json(
        quality_report_path.read_text(encoding="utf-8")
    )
    # Solo se valida la forma antes de empaquetar: un splits.json corrupto no
    # debe terminar dentro de un release inmutable.
    SplitsManifest.model_validate_json(splits_path.read_text(encoding="utf-8"))

    manifest = load_manifest(out)
    resolved_version = version or next_version(manifest, bump)

    archive_path = build_archive(
        coco_path=coco_path,
        quality_path=quality_report_path,
        splits_path=splits_path,
        dest=archive_dir / resolved_version / ARCHIVE_NAME,
    )

    entry = build_entry(
        version=resolved_version,
        dataset_fingerprint=dataset_fingerprint,
        quality_report=quality_report,
        quality_report_fingerprint=file_sha256(quality_report_path),
        splits_fingerprint=file_sha256(splits_path),
        bucket=bucket,
        notes=notes,
    )

    if upload:
        upload_archive(archive_path, bucket, resolved_version)
        new_manifest = append_entry(manifest, entry)
        write_manifest(new_manifest, out)
    else:
        new_manifest = append_entry(manifest, entry)

    return ReleaseResult(entry=entry, manifest=new_manifest, archive_path=archive_path)
