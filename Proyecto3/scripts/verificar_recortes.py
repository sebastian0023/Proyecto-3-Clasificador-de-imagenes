"""Verificacion de recortes contra el COCO original (F2 T07, criterio 1.2).

Dos niveles:

1. Automatico, sobre TODOS los recortes de `crops.jsonl`: la anotacion existe
   en el COCO del release con la misma imagen, categoria y bbox; el PNG es
   pixel a pixel `original.crop(crop_box_xyxy)`.
2. Manual: muestra aleatoria (semilla fija) de N recortes, cada uno en una
   miniatura con el original y su caja dibujada a la izquierda y el recorte a
   la derecha, en `docs/verificacion_recortes/`, para revisarla a ojo.

    python scripts/verificar_recortes.py --release 0.1.3 [--n 10 --seed 7]

Lee el COCO de `Proyecto2/data/raw` (misma huella que el release, la verifica
`generate_crops.py`) y no necesita credenciales.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
P3 = ROOT / "Proyecto3"
THUMB_HEIGHT = 240


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", required=True)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "Proyecto2" / "data" / "raw")
    parser.add_argument("--crops-dir", type=Path, default=P3 / "data" / "crops")
    parser.add_argument("--out-dir", type=Path, default=P3 / "docs" / "verificacion_recortes")
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    crops_dir = args.crops_dir / args.release
    records = [
        json.loads(line)
        for line in (crops_dir / "crops.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    coco = json.loads((args.raw_dir / "annotations.coco.json").read_text(encoding="utf-8"))
    annotations = {a["id"]: a for a in coco["annotations"]}
    images = {i["id"]: i for i in coco["images"]}
    names = {c["id"]: c["name"] for c in coco["categories"]}

    for record in records:
        ann = annotations[record["annotation_id"]]
        assert ann["image_id"] == record["source_image_id"], record["crop_id"]
        assert ann["category_id"] == record["category_id"], record["crop_id"]
        assert names[ann["category_id"]] == record["category_name"], record["crop_id"]
        assert list(ann["bbox"]) == list(record["bbox_xywh"]), record["crop_id"]
        assert images[ann["image_id"]]["file_name"] == record["source_file_name"]
        with (
            Image.open(args.raw_dir / "images" / record["source_file_name"]) as original,
            Image.open(crops_dir / record["crop_path"]) as crop,
        ):
            expected = original.convert("RGB").crop(tuple(record["crop_box_xyxy"]))
            assert ImageChops.difference(expected, crop.convert("RGB")).getbbox() is None, record[
                "crop_id"
            ]
    print(f"{len(records)} recortes verificados contra el COCO y los pixeles del original")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    sample = random.Random(args.seed).sample(sorted(records, key=lambda r: r["crop_id"]), args.n)
    print("crop_id | imagen | clase | bbox_xywh | miniatura")
    for record in sample:
        name = f"{args.release}_a{record['annotation_id']}.jpg"
        with Image.open(args.raw_dir / "images" / record["source_file_name"]) as original:
            left = original.convert("RGB")
        draw = ImageDraw.Draw(left)
        x, y, w, h = record["bbox_xywh"]
        draw.rectangle((x, y, x + w, y + h), outline=(255, 0, 0), width=max(2, left.width // 150))
        with Image.open(crops_dir / record["crop_path"]) as crop:
            right = crop.convert("RGB")
        left = _to_height(left, THUMB_HEIGHT)
        right = _to_height(right, THUMB_HEIGHT)
        canvas = Image.new("RGB", (left.width + 8 + right.width, THUMB_HEIGHT), (255, 255, 255))
        canvas.paste(left, (0, 0))
        canvas.paste(right, (left.width + 8, 0))
        canvas.save(args.out_dir / name, format="JPEG", quality=80)
        print(
            f"{record['crop_id']} | {record['source_image_id']} ({record['source_file_name']}) | "
            f"{record['category_name']} | {record['bbox_xywh']} | {name}"
        )


def _to_height(image: Image.Image, height: int) -> Image.Image:
    width = max(1, round(image.width * height / image.height))
    return image.resize((width, height), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    main()
