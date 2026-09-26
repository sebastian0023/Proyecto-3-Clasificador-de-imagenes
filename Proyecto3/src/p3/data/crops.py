"""Recortes COCO: que cajas del release se convierten en muestras (F2 T07, criterio 1.2).

Cada anotacion termina en exactamente uno de dos lados:

- `CropSource`: caja valida, lista para recortar. Conserva `annotation_id`,
  `source_image_id`, `source_file_name`, `category_id`/`category_name` y la
  bbox original del COCO sin redondear. Un original puede producir varios.
- `Exclusion`: caja descartada con su motivo (`docs/contratos.md` §2).

Si una anotacion cumple varios motivos se registra el primero de este orden:
`excluded_category` (la caja no es de una clase fijada, lo demas no importa),
`missing_image`, `degenerate_bbox`, `bbox_out_of_bounds`.

Se trabaja sobre el COCO como `dict` y no con `dataset_quality.models.coco` de
P2 a proposito: ese modelo rechaza el dataset COMPLETO ante una sola caja
degenerada, y aqui hace falta lo contrario: descartar esa caja, registrar por
que y seguir con las demas.

Despues, `generate_crops` corta cada caja valida en un PNG y devuelve un
`CropRecord` por recorte; `write_exclusions_csv` deja las exclusiones en CSV.

Aqui no se leen variables de entorno ni se crean clientes de S3 o BD: las
rutas de imagenes y de salida las pasa quien llama.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from PIL import Image, UnidentifiedImageError

ExclusionReason = Literal[
    "degenerate_bbox",
    "bbox_out_of_bounds",
    "missing_image",
    "excluded_category",
]

BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class CropSource:
    """Caja valida de una clase incluida: una fila futura del manifiesto."""

    annotation_id: int
    source_image_id: int
    source_file_name: str
    category_id: int
    category_name: str
    bbox_xywh: BBox


@dataclass(frozen=True)
class Exclusion:
    """Anotacion descartada; va a `exclusions.csv` y a `manifest.meta.json`."""

    annotation_id: int
    source_image_id: int
    reason: ExclusionReason


@dataclass(frozen=True)
class ValidationResult:
    """Ambas tuplas ordenadas por `annotation_id`."""

    valid: tuple[CropSource, ...]
    exclusions: tuple[Exclusion, ...]


def read_image_sizes(
    images: Iterable[Mapping[str, Any]], images_dir: Path
) -> dict[int, tuple[int, int]]:
    """`(ancho, alto)` REAL de cada imagen del COCO que existe y se puede abrir.

    Una imagen ausente o ilegible no aparece en el resultado; para la
    validacion eso es `missing_image`. Se usan las dimensiones del archivo y no
    las del COCO: si difieren, recortar con las del COCO podria salirse de la
    imagen sin que nadie lo note.
    """
    sizes: dict[int, tuple[int, int]] = {}
    for image in images:
        path = images_dir / image["file_name"]
        try:
            with Image.open(path) as handle:
                sizes[image["id"]] = handle.size
        except (FileNotFoundError, IsADirectoryError, UnidentifiedImageError):
            continue
    return sizes


def validate_annotations(
    coco: Mapping[str, Any],
    included_category_ids: Collection[int],
    image_sizes: Mapping[int, tuple[int, int]],
) -> ValidationResult:
    """Separa las anotaciones del COCO en cajas validas y exclusiones con motivo.

    `image_sizes` viene de `read_image_sizes`: una imagen sin entrada es una
    imagen faltante. No modifica `coco`.
    """
    images = {image["id"]: image for image in coco["images"]}
    category_names = {category["id"]: category["name"] for category in coco["categories"]}

    valid: list[CropSource] = []
    exclusions: list[Exclusion] = []
    for ann in sorted(coco["annotations"], key=lambda a: a["id"]):
        image_id = ann["image_id"]
        reason = _exclusion_reason(ann, images, included_category_ids, image_sizes)
        if reason is not None:
            exclusions.append(Exclusion(ann["id"], image_id, reason))
            continue
        bbox = _as_bbox(ann.get("bbox"))
        assert bbox is not None  # _exclusion_reason ya descarto las malformadas
        valid.append(
            CropSource(
                annotation_id=ann["id"],
                source_image_id=image_id,
                source_file_name=images[image_id]["file_name"],
                category_id=ann["category_id"],
                category_name=category_names[ann["category_id"]],
                bbox_xywh=bbox,
            )
        )
    return ValidationResult(tuple(valid), tuple(exclusions))


def _exclusion_reason(
    ann: Mapping[str, Any],
    images: Mapping[int, Mapping[str, Any]],
    included_category_ids: Collection[int],
    image_sizes: Mapping[int, tuple[int, int]],
) -> ExclusionReason | None:
    if ann["category_id"] not in included_category_ids:
        return "excluded_category"
    image_id = ann["image_id"]
    if image_id not in images or image_id not in image_sizes:
        return "missing_image"
    bbox = _as_bbox(ann.get("bbox"))
    if bbox is None or bbox[2] <= 0 or bbox[3] <= 0:
        return "degenerate_bbox"
    x, y, w, h = bbox
    width, height = image_sizes[image_id]
    if x < 0 or y < 0 or x + w > width or y + h > height:
        return "bbox_out_of_bounds"
    return None


def _as_bbox(value: Any) -> BBox | None:
    """La bbox como 4 floats finitos, o `None` si esta malformada."""
    if not isinstance(value, list | tuple) or len(value) != 4:
        return None
    if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in value):
        return None
    x, y, w, h = (float(v) for v in value)
    if not all(math.isfinite(v) for v in (x, y, w, h)):
        return None
    return (x, y, w, h)


# --- Recortes ------------------------------------------------------------------------------

EXCLUSIONS_HEADER = ("annotation_id", "image_id", "reason")


@dataclass(frozen=True)
class CropRecord:
    """Un recorte generado: la fila base del manifiesto (F3 agrega grupo y particion)."""

    crop_id: str
    annotation_id: int
    source_image_id: int
    source_file_name: str
    category_id: int
    category_name: str
    bbox_xywh: BBox
    crop_box_xyxy: tuple[int, int, int, int]
    crop_path: str
    width: int
    height: int


def crop_id(release_id: str, annotation_id: int) -> str:
    """`"<release_id>:a<annotation_id>"`, unico y estable entre generaciones (contratos §2)."""
    return f"{release_id}:a{annotation_id}"


def crop_box(bbox: BBox, image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    """Caja en pixeles enteros `(left, top, right, bottom)` para `Image.crop`.

    Regla: piso a la izquierda y arriba, techo a la derecha y abajo, para cubrir
    todo pixel que la caja toca; se limita al lienzo (la validacion ya descarto
    las cajas fuera de la imagen) y se garantiza al menos un pixel.
    """
    x, y, w, h = bbox
    width, height = image_size
    left = min(max(math.floor(x), 0), width - 1)
    top = min(max(math.floor(y), 0), height - 1)
    right = min(max(math.ceil(x + w), left + 1), width)
    bottom = min(max(math.ceil(y + h), top + 1), height)
    return (left, top, right, bottom)


def generate_crops(
    valid: Iterable[CropSource], images_dir: Path, out_dir: Path, *, release_id: str
) -> list[CropRecord]:
    """Corta cada caja valida en `out_dir/<clase>/<release>_a<annotation_id>.png`.

    PNG sin perdida y en RGB: el recorte conserva los pixeles del original sin
    una segunda compresion JPEG. Cada original se abre una sola vez. El
    resultado va ordenado por `annotation_id` y es determinista.
    """
    by_image: dict[str, list[CropSource]] = defaultdict(list)
    for source in valid:
        by_image[source.source_file_name].append(source)

    records: list[CropRecord] = []
    for file_name in sorted(by_image):
        with Image.open(images_dir / file_name) as original:
            image = original.convert("RGB")
        for source in by_image[file_name]:
            box = crop_box(source.bbox_xywh, image.size)
            relative = f"{source.category_name}/{release_id}_a{source.annotation_id}.png"
            path = out_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            image.crop(box).save(path, format="PNG", optimize=False)
            records.append(
                CropRecord(
                    crop_id=crop_id(release_id, source.annotation_id),
                    annotation_id=source.annotation_id,
                    source_image_id=source.source_image_id,
                    source_file_name=source.source_file_name,
                    category_id=source.category_id,
                    category_name=source.category_name,
                    bbox_xywh=source.bbox_xywh,
                    crop_box_xyxy=box,
                    crop_path=relative,
                    width=box[2] - box[0],
                    height=box[3] - box[1],
                )
            )
    return sorted(records, key=lambda record: record.annotation_id)


def write_exclusions_csv(exclusions: Iterable[Exclusion], path: Path) -> None:
    """`annotation_id,image_id,reason`, ordenado por `annotation_id`, con fin de linea LF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(EXCLUSIONS_HEADER)
        for exclusion in sorted(exclusions, key=lambda e: e.annotation_id):
            writer.writerow((exclusion.annotation_id, exclusion.source_image_id, exclusion.reason))
