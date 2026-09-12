"""`splits.json`: el contrato de salida congelado de los splits estratificados.

Lo produce el Frente 5 (splits con semilla y sin fuga entre train/val/test);
aqui solo se fija su forma exacta para que los frentes que lo consumen
(Frente 7 y 8) puedan escribirse contra un ejemplo de oro desde hoy.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from dataset_quality.models import StrictModel

SplitName = Literal["train", "val", "test"]


class SplitRatios(StrictModel):
    """Proporciones objetivo de cada split. Deben sumar 1.0."""

    train: float = Field(gt=0.0, lt=1.0)
    val: float = Field(gt=0.0, lt=1.0)
    test: float = Field(gt=0.0, lt=1.0)

    @model_validator(mode="after")
    def _suman_uno(self) -> SplitRatios:
        total = self.train + self.val + self.test
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"train + val + test debe sumar 1.0 (suma: {total})")
        return self


class SplitAssignment(StrictModel):
    """La asignacion de una imagen a un split."""

    image_id: int = Field(ge=1)
    split: SplitName


class SplitsManifest(StrictModel):
    """Contrato congelado de `splits.json`."""

    schema_version: Literal[1] = 1
    generated_at: datetime
    seed: int
    ratios: SplitRatios
    counts: dict[SplitName, int]
    stratified_by: str = "category_id"
    assignments: list[SplitAssignment]

    @model_validator(mode="after")
    def _sin_fuga_y_conteos_coherentes(self) -> SplitsManifest:
        ids = [assignment.image_id for assignment in self.assignments]
        duplicados = {value for value, count in Counter(ids).items() if count > 1}
        if duplicados:
            raise ValueError(
                f"image_id asignado a mas de un split (fuga entre splits): {sorted(duplicados)}"
            )

        conteo_real = Counter(assignment.split for assignment in self.assignments)
        for split_name in ("train", "val", "test"):
            esperado = self.counts.get(split_name, 0)
            observado = conteo_real.get(split_name, 0)
            if esperado != observado:
                raise ValueError(
                    f"counts.{split_name}={esperado} no coincide con las asignaciones reales "
                    f"({observado})"
                )
        return self
