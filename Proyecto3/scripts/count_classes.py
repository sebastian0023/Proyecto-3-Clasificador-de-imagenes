"""Cuenta originales validos por clase en un release aprobado y fija las clases (F2 T06).

Recorrido, todo verificado contra el registro de P2 (`versions.json`):

1. El release debe tener compuerta `pass` (`get_approved_release`).
2. Su `dataset.tar.zst` se descarga del bucket de releases y se acepta solo si
   el SHA-256 y la huella de P2 del COCO coinciden con el registro.
3. Las imagenes vienen de DVC (`Proyecto2/data/raw`, `dvc pull -r prod`): el
   COCO local debe tener la MISMA huella, o las imagenes no son de ese release.
4. Se validan TODAS las cajas (`validate_annotations`) y se cuentan originales
   distintos con al menos una caja valida por categoria.
5. `select_classes` aplica el umbral de 300; con `--write` se escribe
   `config/classes.yaml`.

Corre con el entorno de Proyecto2 (tiene `boto3` y `dataset_quality`, que da
la huella de P2) y `Proyecto3/src` en el path:

    cd Proyecto2
    PYTHONPATH=../Proyecto3/src .venv/Scripts/python ../Proyecto3/scripts/count_classes.py \\
        --release 0.1.3 --profile <perfil-aws> [--write]

Solo LEE de S3. Las credenciales salen del perfil de `~/.aws`, nunca del repo.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import boto3

from p3.data import classes, crops, releases

ROOT = Path(__file__).resolve().parents[2]
P2 = ROOT / "Proyecto2"
DEFAULT_BUCKET = "dataset-quality-releases-750702272375"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", required=True)
    parser.add_argument("--profile", required=True, help="perfil de ~/.aws (solo lectura basta)")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--raw-dir", type=Path, default=P2 / "data" / "raw")
    parser.add_argument("--registry", type=Path, default=P2 / "reports" / "versions.json")
    parser.add_argument("--min-originals", type=int, default=classes.MIN_ORIGINALS)
    parser.add_argument(
        "--write", type=Path, nargs="?", const=ROOT / "Proyecto3" / "config" / "classes.yaml"
    )
    args = parser.parse_args()

    release = releases.get_approved_release(releases.load_releases(args.registry), args.release)
    key = releases.archive_key(release.release_id)
    s3 = boto3.Session(profile_name=args.profile).client("s3", region_name=args.region)
    obj = s3.get_object(Bucket=args.bucket, Key=key)
    archive = obj["Body"].read()
    content = releases.open_release_archive(
        release, archive, fingerprint=releases.p2_dataset_fingerprint
    )

    local_coco = (args.raw_dir / "annotations.coco.json").read_bytes()
    local_fingerprint = releases.p2_dataset_fingerprint(local_coco)
    if local_fingerprint != release.dataset_fingerprint:
        raise SystemExit(
            f"El COCO de {args.raw_dir} (huella {local_fingerprint}) no es el del release "
            f"{release.release_id} ({release.dataset_fingerprint}): corre `dvc pull -r prod`."
        )

    coco = content.coco
    names = {c["id"]: c["name"] for c in coco["categories"]}
    sizes = crops.read_image_sizes(coco["images"], args.raw_dir / "images")
    result = crops.validate_annotations(coco, set(names), sizes)
    originals = classes.originals_per_category(result.valid)
    decisions = classes.select_classes(originals, names, min_originals=args.min_originals)

    reasons: dict[str, int] = {}
    for exclusion in result.exclusions:
        reasons[exclusion.reason] = reasons.get(exclusion.reason, 0) + 1
    report = {
        "release_id": release.release_id,
        "dataset_fingerprint": release.dataset_fingerprint,
        "quality_status": release.quality_status,
        "quality_report_fingerprint": release.quality_report_fingerprint,
        "archive": {
            "uri": releases.archive_uri(args.bucket, release.release_id),
            "version_id": obj.get("VersionId"),
            "sha256": release.archive_sha256,
        },
        "local_coco_fingerprint_matches": True,
        "images_in_coco": len(coco["images"]),
        "images_readable": len(sizes),
        "annotations": len(coco["annotations"]),
        "valid_boxes": len(result.valid),
        "exclusions_by_reason": dict(sorted(reasons.items())),
        "min_originals": args.min_originals,
        "classes": [
            {
                "category_id": d.category_id,
                "category_name": d.category_name,
                "originals_with_valid_box": d.originals,
                "valid_boxes": sum(1 for c in result.valid if c.category_id == d.category_id),
                "included": d.included,
                "reason": d.reason,
            }
            for d in decisions
        ],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.write:
        config = classes.build_config(
            decisions,
            release_id=release.release_id,
            dataset_fingerprint=release.dataset_fingerprint,
            decided_at=datetime.now(UTC).date(),
            min_originals=args.min_originals,
        )
        args.write.parent.mkdir(parents=True, exist_ok=True)
        classes.dump_classes(config, args.write)
        print(f"Escrito {args.write}")


if __name__ == "__main__":
    main()
