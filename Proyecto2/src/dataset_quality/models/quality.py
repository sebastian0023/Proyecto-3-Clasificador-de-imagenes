"""Configuracion de calidad (`quality.yaml`) y su reporte de salida (`quality.json`).

`QualityConfig` es la entrada que ajusta los cinco analizadores del Frente 3
(objetos pequenos, desbalance de clases, duplicados por pHash, cajas
degeneradas, sesgo espacial). `QualityReport` es el contrato de salida que
escribe la compuerta del Frente 4 y que este modulo congela: su forma exacta
(`schema_version=1`) es lo que permite que los Frentes 7 y 8 arranquen contra
ejemplos escritos a mano sin esperar a que la compuerta exista.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, ValidationError, model_validator
from yaml import YAMLError

from dataset_quality.models import StrictModel
from dataset_quality.models.errors import from_pydantic, single_issue

Severity = Literal["error", "warning"]


class MinImagesPerClassCheck(StrictModel):
    """Exige volumen suficiente: N imagenes distintas en al menos M clases.

    Es el requisito del curso (compuerta M3) y el unico check que mide si hay
    dataset con el que entrenar algo. Nace en `error` a proposito: sin volumen
    no hay nada que publicar, por bien que salgan los demas analizadores.

    Se cuentan IMAGENES distintas que contienen al menos una caja de la clase,
    no cajas: una foto con siete coches aporta una imagen a `car`, no siete.
    """

    enabled: bool = True
    severity: Severity = "error"
    min_images: int = Field(ge=1)
    min_classes: int = Field(ge=1)


class SmallObjectsCheck(StrictModel):
    """Marca anotaciones cuya area relativa a la imagen es demasiado chica."""

    enabled: bool = True
    severity: Severity = "warning"
    area_ratio_threshold: float = Field(ge=0.0, le=1.0)
    max_ratio: float = Field(ge=0.0, le=1.0)


class ClassImbalanceCheck(StrictModel):
    """Marca un desbalance excesivo entre la clase mas y menos frecuente."""

    enabled: bool = True
    severity: Severity = "warning"
    max_ratio_max_min: float = Field(gt=1.0)


class DuplicatesCheck(StrictModel):
    """Marca imagenes casi identicas via distancia de Hamming entre pHash."""

    enabled: bool = True
    severity: Severity = "error"
    phash_hamming_distance: int = Field(ge=0, le=64)
    max_ratio: float = Field(ge=0.0, le=1.0)


class DegenerateBoxesCheck(StrictModel):
    """Marca cajas con area nula o negativa que se colaron en el dataset."""

    enabled: bool = True
    severity: Severity = "error"
    max_ratio: float = Field(ge=0.0, le=1.0)


class SpatialBiasCheck(StrictModel):
    """Marca concentracion espacial anomala de las anotaciones en la imagen."""

    enabled: bool = True
    severity: Severity = "warning"
    grid_size: int = Field(ge=2)
    max_cell_share: float = Field(gt=0.0, le=1.0)


class QualityConfig(StrictModel):
    """Umbrales de calidad. Se carga desde `quality.yaml`."""

    version: int = Field(default=1, ge=1)
    min_images_per_class: MinImagesPerClassCheck
    small_objects: SmallObjectsCheck
    class_imbalance: ClassImbalanceCheck
    duplicates: DuplicatesCheck
    degenerate_boxes: DegenerateBoxesCheck
    spatial_bias: SpatialBiasCheck

    def enabled_checks(self) -> tuple[str, ...]:
        """Nombres de los analizadores activos, en el orden declarado arriba."""
        names = (
            "min_images_per_class",
            "small_objects",
            "class_imbalance",
            "duplicates",
            "degenerate_boxes",
            "spatial_bias",
        )
        return tuple(name for name in names if getattr(self, name).enabled)

    @classmethod
    def from_yaml(cls, path: Path) -> QualityConfig:
        """Carga y valida `quality.yaml`. Nunca usa `yaml.load` sin loader seguro."""
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except YAMLError as error:
            problem_mark = getattr(error, "problem_mark", None)
            location = f"linea {problem_mark.line + 1}" if problem_mark else "<root>"
            raise single_issue(str(path), location, f"YAML malformado: {error}") from error

        if raw is None:
            raise single_issue(str(path), "<root>", "el archivo esta vacio")

        try:
            return cls.model_validate(raw)
        except ValidationError as error:
            raise from_pydantic(str(path), error) from error


class QualityTotals(StrictModel):
    """Conteos globales del dataset evaluado, para contexto en el reporte."""

    images: int = Field(ge=0)
    annotations: int = Field(ge=0)
    categories: int = Field(ge=0)


class CheckResult(StrictModel):
    """Resultado de un analizador individual."""

    name: str = Field(min_length=1)
    status: Literal["pass", "fail", "skipped"]
    severity: Severity
    observed: float
    threshold: float
    message: str
    offenders: list[int] = Field(default_factory=list)


class QualityReport(StrictModel):
    """Contrato congelado de `quality.json`."""

    schema_version: Literal[1] = 1
    generated_at: datetime
    dataset_fingerprint: str = Field(min_length=1)
    config_version: int = Field(ge=1)
    status: Literal["pass", "fail"]
    exit_code: Literal[0, 1]
    totals: QualityTotals
    checks: list[CheckResult]

    @model_validator(mode="after")
    def _status_y_exit_code_coherentes(self) -> QualityReport:
        esperado = 0 if self.status == "pass" else 1
        if self.exit_code != esperado:
            raise ValueError(
                f"exit_code={self.exit_code} no es coherente con status={self.status!r} "
                f"(se esperaba {esperado})"
            )
        return self
