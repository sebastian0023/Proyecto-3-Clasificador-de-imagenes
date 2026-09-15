"""Estadistica descriptiva del dataset.

Va aparte de `QualityReport` porque no es una compuerta: no tiene umbral ni
puede fallar. Es el contexto que la app web necesita para dibujar el resumen y
que un humano necesita para entender contra que se esta comparando un umbral.
"""

from __future__ import annotations

from pydantic import Field

from dataset_quality.models import StrictModel
from dataset_quality.models.quality import QualityTotals


class DatasetStats(StrictModel):
    """Resumen descriptivo. Sin juicio: solo describe lo que hay."""

    totals: QualityTotals

    # Imagenes DISTINTAS que contienen al menos una caja de cada clase. Es la
    # metrica que exige el curso, y no es lo mismo que contar cajas.
    images_per_class: dict[str, int] = Field(default_factory=dict)
    boxes_per_class: dict[str, int] = Field(default_factory=dict)

    annotations_per_image: float = Field(ge=0.0)
    images_without_annotations: int = Field(ge=0)

    # Area de la caja relativa a su imagen. Da la escala en la que hay que leer
    # el umbral de `small_objects`.
    median_box_area_ratio: float = Field(ge=0.0, le=1.0)
