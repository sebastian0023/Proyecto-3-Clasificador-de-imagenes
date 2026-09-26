"""Genera el manifiesto 70/20/10 de un release aprobado (F3 T08, criterios 1.3 y M3).

1. Verifica el release de punta a punta (`release_local.load_verified_release`).
2. Exige que `config/classes.yaml` cite ese mismo release y huella.
3. Valida las cajas de las clases fijadas (`p3.data.crops.validate_annotations`).
4. Calcula los grupos de casi duplicados con el codigo de P2
   (`dataset_quality.analyzers.duplicates`) y el umbral de `quality.yaml`.
5. Reparte con `p3.data.split.build_manifest` y exige `check_manifest` vacio.

Salida en `Proyecto3/data/manifests/<manifest_id>/`: `manifest.jsonl` (una fila por
recorte, contratos §2) y `manifest.meta.json` (procedencia y conteos). Se versiona
con DVC; `--check` regenera en memoria y compara con lo escrito, sin tocar nada.

    cd Proyecto2
    PYTHONPATH="../Proyecto3/src;src" .venv/Scripts/python \\
        ../Proyecto3/scripts/generate_manifest.py \\
        --release 0.1.3 --profile <perfil-aws> [--seed 42] [--check]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dataset_quality.analyzers.duplicates import compute_hashes, duplicate_groups
from dataset_quality.models.coco import CocoDataset
from dataset_quality.models.quality import QualityConfig
from release_local import P2, ROOT, add_release_arguments, load_verified_release

from p3.data import classes, crops, split

P3 = ROOT / "Proyecto3"
REVISION = 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_release_arguments(parser)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--classes", type=Path, default=P3 / "config" / "classes.yaml")
    parser.add_argument("--quality", type=Path, default=P2 / "quality.yaml")
    parser.add_argument("--out-dir", type=Path, default=P3 / "data" / "manifests")
    parser.add_argument("--check", action="store_true", help="comparar con lo ya escrito")
    args = parser.parse_args()

    verified = load_verified_release(args)
    release = verified.content.release
    coco = verified.content.coco
    config = classes.load_classes(args.classes)
    if (config.release_id, config.dataset_fingerprint) != (
        release.release_id,
        release.dataset_fingerprint,
    ):
        raise SystemExit(f"{args.classes} no fija clases del release {release.release_id}.")

    included = {entry.category_id: entry for entry in config.classes}
    sizes = crops.read_image_sizes(coco["images"], verified.images_dir)
    result = crops.validate_annotations(coco, set(included), sizes)

    threshold = QualityConfig.from_yaml(args.quality).duplicates.phash_hamming_distance
    hashes = compute_hashes(CocoDataset.model_validate(coco), verified.images_dir)
    groups = duplicate_groups(hashes, threshold)
    dup_groups = split.dup_group_ids({image["id"] for image in coco["images"]}, groups)

    rows = split.build_manifest(
        result.valid,
        release=split.ManifestRelease(release.release_id, release.dataset_fingerprint),
        class_index={cid: entry.class_index for cid, entry in included.items()},
        dup_groups=dup_groups,
        seed=args.seed,
    )
    problems = split.check_manifest(rows)
    if problems:
        raise SystemExit("El manifiesto viola los invariantes:\n- " + "\n- ".join(problems))

    manifest_id = f"m-{release.release_id}-s{args.seed}-{REVISION}"
    manifest_hash = split.manifest_hash(rows)
    out = args.out_dir / manifest_id
    if args.check:
        written = (out / "manifest.jsonl").read_text(encoding="utf-8")
        same = written == split.manifest_jsonl(rows)
        print(f"{manifest_id}: regenerado {manifest_hash}; escrito identico: {same}")
        raise SystemExit(0 if same else 1)

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    entry = next(v for v in registry["versions"] if v["version"] == release.release_id)
    multi = [sorted(g) for g in groups if len(g) > 1]
    meta = {
        "schema_version": 1,
        "manifest_id": manifest_id,
        "manifest_hash": manifest_hash,
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_commit": _git_commit(),
        "release": {
            "release_id": release.release_id,
            "dataset_fingerprint": release.dataset_fingerprint,
            "quality_status": release.quality_status,
            "quality_report_fingerprint": release.quality_report_fingerprint,
            "archive_sha256": release.archive_sha256,
            "p2_splits_fingerprint": entry["splits_fingerprint"],
        },
        "seed": args.seed,
        "ratios": dict(split.DEFAULT_RATIOS),
        "tolerance_pp": split.TOLERANCE_PP,
        "classes": [
            {
                "class_index": c.class_index,
                "category_id": c.category_id,
                "category_name": c.category_name,
            }
            for c in config.classes
        ],
        "excluded_categories": [
            {"category_id": e.category_id, "category_name": e.category_name}
            for e in config.excluded
        ],
        "exclusions": [
            {
                "annotation_id": e.annotation_id,
                "source_image_id": e.source_image_id,
                "reason": e.reason,
            }
            for e in result.exclusions
        ],
        "counts": split.manifest_counts(rows),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.jsonl").write_text(split.manifest_jsonl(rows), encoding="utf-8", newline="\n")
    (out / "manifest.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print(f"manifest_id: {manifest_id}\nmanifest_hash: {manifest_hash}")
    print(f"recortes: {len(rows)}; grupos de casi duplicados con 2+ imagenes: {len(multi)}")
    print(
        f"exclusiones: {len(result.exclusions)} (todas {set(e.reason for e in result.exclusions)})"
    )
    print(json.dumps(meta["counts"], indent=1))


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=ROOT
    ).stdout.strip()


if __name__ == "__main__":
    main()
