"""Prueba de integracion de extremo a extremo (F10 T26).

Recorre el flujo con IDs trazables usando el fixture de 3 clases. Hoy cubre el
tramo que ya esta en `main`: release (F2) -> recortes validos (F2) -> manifiesto
70/20/10 sin fuga (F3), imprimiendo la cadena de IDs.

El tramo entrenamiento -> run MLflow -> seleccion -> evaluacion en test ->
publicacion en MinIO -> inferencia depende de F4-F7, que aun no estan en `main`.
Va en `test_e2e_flujo_completo`, marcado `skip` con motivo explicito, para no dar
ni un falso verde ni un falso rojo; se implementa cuando esas fases aterricen.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from p3.data.crops import read_image_sizes, validate_annotations
from p3.data.split import (
    ManifestRelease,
    build_manifest,
    check_manifest,
    dup_group_ids,
    manifest_counts,
    manifest_hash,
)

FIXTURE = Path(__file__).parent / "fixtures" / "p3"
# contratos section 1: category_id de COCO -> nombre y class_index (alfabetico).
NAMES = {2: "person", 3: "dog", 4: "cat"}
CLASS_INDEX = {4: 0, 3: 1, 2: 2}
RELEASE = ManifestRelease(release_id="0.1.3", dataset_fingerprint="2200274d" + "0" * 56)


def _manifiesto_desde_fixture(seed: int = 42) -> list[dict]:
    """Release -> recortes validos -> manifiesto, con el fixture de P3."""
    coco = json.loads((FIXTURE / "annotations.coco.json").read_text(encoding="utf-8"))
    sizes = read_image_sizes(coco["images"], FIXTURE / "images")
    valid = validate_annotations(coco, set(NAMES), sizes).valid
    dup = dup_group_ids({img["id"] for img in coco["images"]}, [{25, 26}])
    return build_manifest(
        valid, release=RELEASE, class_index=CLASS_INDEX, dup_groups=dup, seed=seed
    )


def test_e2e_release_a_manifiesto_sin_fuga(capsys: pytest.CaptureFixture[str]) -> None:
    rows = _manifiesto_desde_fixture()

    # Manifiesto valido: sin fuga entre particiones, proporciones y clases OK.
    assert check_manifest(rows) == []
    # Recortes validos del fixture: 10 cat + 9 dog + 9 person (contratos section 7).
    assert len(rows) == 28

    counts = manifest_counts(rows)
    cadena = {
        "release_id": RELEASE.release_id,
        "release_hash": RELEASE.dataset_fingerprint[:12] + "...",
        "manifest_hash": manifest_hash(rows),
        "recortes": sum(sum(c.values()) for c in counts["crops"].values()),
        # Tramo pendiente de F4-F7 (aun no en main):
        "run_id": "<pendiente F4/F5>",
        "checkpoint": "<pendiente F5>",
        "model_version": "<pendiente F7>",
        "s3_key": "<pendiente F7>",
        "inference_id": "<pendiente F4/F9>",
    }
    with capsys.disabled():
        print("\nCadena de IDs E2E (release -> manifiesto):")
        for clave, valor in cadena.items():
            print(f"  {clave}: {valor}")

    # Reproducible: misma semilla y mismo release -> mismo hash (M3).
    assert manifest_hash(_manifiesto_desde_fixture()) == cadena["manifest_hash"]


@pytest.mark.skip(reason="Flujo completo E2E: pendiente del stack F4-F7 en main (F10 T26)")
def test_e2e_flujo_completo() -> None:
    """release -> manifiesto -> entrenamiento corto -> run MLflow -> seleccion ->
    evaluacion en test -> publicacion en MinIO -> inferencia, con la cadena de IDs
    completa. Se implementa cuando F4-F7 esten en `main`."""
