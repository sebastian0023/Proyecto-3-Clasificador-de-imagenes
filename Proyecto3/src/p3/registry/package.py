"""Paquete de una version de modelo y su tarjeta (F7 T17, criterio 5.1; contratos §6).

`build_package` devuelve los archivos del paquete como `nombre -> bytes`, armados
solo a partir de datos:

- `model.pt`: los MISMOS bytes del checkpoint de `selection.json` (su SHA-256 es
  el seleccionado, el que verifica la inferencia);
- `class_map.json`, `preprocessing.json`, `config.json`: del checkpoint, de
  `config/classes.yaml` y de los parametros de la corrida en MLflow;
- `MODEL_CARD.md`: generada con las cifras de la evaluacion final (F6), no
  escritas a mano;
- `model_version.json`: el resumen del contrato §6.

Logica pura: no lee archivos ni habla con S3 o MLflow; quien llama le pasa todo.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

CARD_TEMPLATE = Path(__file__).with_name("model_card_template.md")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
PRETRAINED_ORIGIN = "torchvision ResNet18_Weights.IMAGENET1K_V1"
INT_PARAMS = ("batch_size", "max_epochs", "image_size", "seed", "patience")
FLOAT_PARAMS = ("learning_rate", "dropout", "min_delta")


class PackageError(ValueError):
    """Los insumos no describen el artefacto seleccionado."""


def build_package(
    *,
    checkpoint: bytes,
    selection: bytes,
    metrics: Mapping[str, Any],
    run_params: Mapping[str, str],
    run_tags: Mapping[str, str],
    classes: Sequence[Mapping[str, Any]],
    version: str,
    requirements: str,
    created_at: str,
) -> dict[str, bytes]:
    if not SEMVER.match(version):
        raise PackageError(f"version {version!r} no es semantica (MAYOR.MENOR.PARCHE).")
    chosen = json.loads(selection)
    checkpoint_sha = hashlib.sha256(checkpoint).hexdigest()
    if checkpoint_sha != chosen["checkpoint_sha256"]:
        raise PackageError(
            f"SHA-256 del checkpoint {checkpoint_sha} no es el seleccionado "
            f"({chosen['checkpoint_sha256']})."
        )
    if metrics["run_id"] != chosen["run_id"]:
        raise PackageError(
            f"Las metricas son del run_id {metrics['run_id']}, no del seleccionado "
            f"{chosen['run_id']}."
        )

    loaded = torch.load(io.BytesIO(checkpoint), map_location="cpu", weights_only=True)
    architecture = dict(loaded["architecture"])
    class_names = list(loaded["class_names"])
    preprocessing = dict(loaded["preprocessing"])
    by_name = {c["category_name"]: c for c in classes}
    class_map = {
        "classes": [
            {
                "class_index": index,
                "category_id": by_name[name]["category_id"],
                "category_name": name,
            }
            for index, name in enumerate(class_names)
        ]
    }
    training = _training_config(run_params)
    config = {"training": training, "architecture": architecture}

    files: dict[str, bytes] = {
        "model.pt": checkpoint,
        "class_map.json": _json(class_map),
        "preprocessing.json": _json(preprocessing),
        "config.json": _json(config),
        "requirements.lock.txt": requirements.encode("utf-8"),
    }
    files["MODEL_CARD.md"] = _card(
        version=version,
        selection=chosen,
        metrics=metrics,
        run_tags=run_tags,
        training=training,
        architecture=architecture,
        class_map=class_map,
        preprocessing=preprocessing,
        checkpoint_sha=checkpoint_sha,
    ).encode("utf-8")
    model_version = {
        "schema_version": 1,
        "version": version,
        "architecture": architecture["name"],
        "pretrained_weights": PRETRAINED_ORIGIN,
        "run_id": chosen["run_id"],
        "manifest_id": chosen["manifest_id"],
        "release_id": run_tags["release_id"],
        "selection_sha256": hashlib.sha256(selection).hexdigest(),
        "test_metrics": {"accuracy": metrics["accuracy"], "f1_macro": metrics["f1_macro"]},
        "preprocessing": preprocessing,
        # `s3_version_id` lo asigna S3 al subir; queda en `registry.json` (T18).
        "files": {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "s3_version_id": None}
            for name, data in sorted(files.items())
        },
        "created_at": created_at,
    }
    files["model_version.json"] = _json(model_version)
    return files


def _training_config(params: Mapping[str, str]) -> dict[str, Any]:
    config: dict[str, Any] = dict(params)
    for key in INT_PARAMS:
        if key in config:
            config[key] = int(config[key])
    for key in FLOAT_PARAMS:
        if key in config:
            config[key] = float(config[key])
    if "hidden_layers" in config:
        config["hidden_layers"] = json.loads(config["hidden_layers"])
    return config


def _json(data: Any) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _card(
    *,
    version: str,
    selection: Mapping[str, Any],
    metrics: Mapping[str, Any],
    run_tags: Mapping[str, str],
    training: Mapping[str, Any],
    architecture: Mapping[str, Any],
    class_map: Mapping[str, Any],
    preprocessing: Mapping[str, Any],
    checkpoint_sha: str,
) -> str:
    matrix = metrics["confusion_matrix"]["rows_true_cols_pred"]
    labels = metrics["confusion_matrix"]["labels"]
    correct = sum(matrix[i][i] for i in range(len(matrix)))
    baseline = metrics["majority_baseline"]
    confused = metrics.get("most_confused")
    rows_class = "\n".join(
        f"| {r['class']} | {r['precision']:.4f} | {r['recall']:.4f} "
        f"| {r['f1']:.4f} | {r['support']} |"
        for r in metrics["per_class"]
    )
    rows_matrix = "\n".join(
        f"| **{label}** | " + " | ".join(str(v) for v in row) + " |"
        for label, row in zip(labels, matrix, strict=True)
    )
    confused_text = (
        f"El par más confundido es `{confused['true']}` → `{confused['predicted']}` "
        f"({confused['count']} casos)."
        if confused
        else "No hubo errores en test."
    )
    values = {
        "version": version,
        "classes": ", ".join(
            f"`{c['category_name']}` (índice {c['class_index']}, category_id {c['category_id']})"
            for c in class_map["classes"]
        ),
        "arch_name": architecture["name"],
        "arch_hidden": architecture["hidden_layers"],
        "arch_dropout": architecture["dropout"],
        "arch_classes": architecture["num_classes"],
        "pretrained": PRETRAINED_ORIGIN,
        "run_id": selection["run_id"],
        "best_epoch": selection.get("best_epoch"),
        "val_accuracy": f"{selection.get('val_accuracy', 0):.4f}",
        "code_commit": run_tags.get("code_commit", ""),
        "checkpoint_sha": checkpoint_sha,
        "training": json.dumps(dict(training), ensure_ascii=False),
        "release_id": run_tags["release_id"],
        "release_hash": run_tags["release_hash"],
        "dvc_md5": run_tags.get("dvc_md5", ""),
        "manifest_id": selection["manifest_id"],
        "manifest_hash": selection["manifest_hash"],
        "crops_sha": selection.get("crops_jsonl_sha256", ""),
        "test_size": metrics["test_size"],
        "evaluated_at": metrics.get("evaluated_at", ""),
        "accuracy": f"{metrics['accuracy']:.4f}",
        "correct": correct,
        "f1_macro": f"{metrics['f1_macro']:.4f}",
        "baseline_class": baseline["class"],
        "baseline_accuracy": f"{baseline['accuracy']:.4f}",
        "rows_class": rows_class,
        "labels": " | ".join(labels),
        "label_rules": "---:|" * len(labels),
        "rows_matrix": rows_matrix,
        "confused_text": confused_text,
        "size": preprocessing["image_size"],
        "resize": preprocessing["resize"],
        "mean": preprocessing["mean"],
        "std": preprocessing["std"],
    }
    return CARD_TEMPLATE.read_text(encoding="utf-8").format(**values)
