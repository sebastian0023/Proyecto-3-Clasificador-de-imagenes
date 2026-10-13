"""Predicciones por muestra sobre la validacion del Proyecto 3 (F7, criterio 1.3).

Un backend por corrida, para poder ejecutar cada modelo en su plataforma:

- `torch`: el original del P3 (`model.pt`) con su propio preprocesamiento
  (`build_eval_transform`) y su `load_checkpoint`. Necesita torch y el codigo del P3.
- `onnx`: una variante ONNX con el preprocesamiento del edge (`modelo/preprocess.py`).
  Solo necesita onnxruntime, numpy y Pillow: corre en la Pi o en un contenedor aarch64.

Solo lee la particion `val` del manifiesto `m-0.1.3-s42-1`; train y test no se tocan.
Exige el SHA-256 del manifiesto, del indice de recortes y del modelo. Escribe:

- `<out>.csv`: una fila por muestra (crop_id, clase real, clase predicha, confianza y
  las tres probabilidades sin redondear).
- `<out>.meta.json`: modelo y su SHA-256, manifiesto, plataforma y versiones.

Uso (desde Proyecto4/):
    .venv/Scripts/python calidad/predecir.py --backend torch \
        --model ../Proyecto3/mlflow_snapshot/artifacts/3/9f9b62c2.../checkpoint/model.pt \
        --manifest ../Proyecto3/data/manifests/m-0.1.3-s42-1/manifest.jsonl \
        --crops ../Proyecto3/data/crops/0.1.3 --out calidad/registros/pred_original
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "modelo"))
from preprocess import preprocess, softmax  # noqa: E402

CLASSES = ["cat", "dog", "person"]
MANIFEST_SHA256 = "45600f297d13f51685e051e0cbc4962beb1f7c6a4e03247cbf61a345e6fa4305"
CROPS_JSONL_SHA256 = "d3d61f35a3efb60e665ac16c95a18f1602df44f3df7c22b86e1c949fadbe1bed"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validation_rows(manifest: Path, crops: Path) -> list[dict]:
    if sha256(manifest) != MANIFEST_SHA256:
        sys.exit(f"{manifest} no es el manifiesto m-0.1.3-s42-1")
    index = crops / "crops.jsonl"
    if sha256(index) != CROPS_JSONL_SHA256:
        sys.exit(f"{index} no es el indice de recortes del P3")
    paths = {r["crop_id"]: r["crop_path"] for r in map(json.loads, index.open(encoding="utf-8"))}
    rows = [r for r in map(json.loads, manifest.open(encoding="utf-8")) if r["split"] == "val"]
    for row in rows:
        row["crop_path"] = paths[row["crop_id"]]
    return sorted(rows, key=lambda r: r["crop_id"])


def torch_predictor(model_path: Path):
    import torch

    sys.path.insert(0, str(HERE.parents[1] / "Proyecto3" / "src"))
    from p3.data.transforms import build_eval_transform
    from p3.model.build import load_checkpoint

    model, meta = load_checkpoint(model_path)
    if meta["class_names"] != CLASSES:
        sys.exit(f"Clases del checkpoint {meta['class_names']} != {CLASSES}")
    transform = build_eval_transform(meta["preprocessing"]["image_size"])

    def predict(image: Image.Image) -> np.ndarray:
        with torch.no_grad():
            return torch.softmax(model(transform(image).unsqueeze(0)), 1)[0].numpy()

    versions = {"torch": torch.__version__, "preprocessing": "p3.data.transforms.build_eval_transform"}
    return predict, versions


def onnx_predictor(model_path: Path):
    import onnxruntime as ort

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    name = session.get_inputs()[0].name

    def predict(image: Image.Image) -> np.ndarray:
        return softmax(session.run(None, {name: preprocess(image)})[0])[0]

    versions = {"onnxruntime": ort.__version__, "preprocessing": "modelo/preprocess.py"}
    return predict, versions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", choices=["torch", "onnx"], required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--crops", type=Path, required=True, help="carpeta Proyecto3/data/crops/0.1.3")
    parser.add_argument("--out", type=Path, required=True, help="ruta sin extension")
    parser.add_argument("--label", default="", help="descripcion de la corrida para el .meta.json")
    args = parser.parse_args()

    rows = validation_rows(args.manifest, args.crops)
    make = torch_predictor if args.backend == "torch" else onnx_predictor
    predict, versions = make(args.model)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["crop_id", "true_class", "pred_class", "confidence", *(f"p_{c}" for c in CLASSES)])
        for i, row in enumerate(rows, 1):
            with Image.open(args.crops / row["crop_path"]) as image:
                probs = predict(image.convert("RGB"))
            best = int(np.argmax(probs))
            writer.writerow(
                [row["crop_id"], row["category_name"], CLASSES[best], repr(float(probs[best])),
                 *(repr(float(p)) for p in probs)]
            )
            if i % 50 == 0:
                print(f"{i}/{len(rows)}", flush=True)

    meta = {
        "label": args.label,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "backend": args.backend,
        "model": args.model.name,
        "model_sha256": sha256(args.model),
        "manifest_id": "m-0.1.3-s42-1",
        "manifest_sha256": MANIFEST_SHA256,
        "split": "val",
        "samples": len(rows),
        "classes": CLASSES,
        "machine": platform.machine(),
        "python": platform.python_version(),
        "qemu_cpu": os.environ.get("QEMU_CPU"),
        "numpy": np.__version__,
        **versions,
        "csv_sha256": sha256(args.out.with_suffix(".csv")),
    }
    args.out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("backend", "model_sha256", "machine", "samples")}))


if __name__ == "__main__":
    main()
