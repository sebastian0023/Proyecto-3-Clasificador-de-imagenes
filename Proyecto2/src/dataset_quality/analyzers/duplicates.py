"""Duplicados por hash perceptual.

El hash lo calcula `imagehash`, no este modulo. Implementar un pHash a mano
(escala de grises, DCT 2D, mediana de las bajas frecuencias) es media tarde de
trabajo y una fuente de errores sutiles que solo se notan cuando el analizador
deja pasar una copia — justo lo que no se puede permitir. La libreria esta
probada por mucha gente; lo que si es nuestro es la politica: que distancia
cuenta como duplicado y como se reporta.

Por que pHash y no un md5: un md5 cambia por completo si se recomprime el JPEG
o se reescala la foto, asi que no ve la copia. El pHash compara COMO SE VE la
imagen y sobrevive a ambas cosas. Ese es exactamente el duplicado que infla el
conteo de imagenes por clase sin aportar variedad.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import imagehash
from PIL import Image, UnidentifiedImageError

from dataset_quality.models.coco import CocoDataset
from dataset_quality.models.quality import CheckResult as Result
from dataset_quality.models.quality import DuplicatesCheck


def perceptual_hash(path: Path) -> int:
    """pHash de 64 bits como entero, para comparar con operaciones de bits."""
    with Image.open(path) as handle:
        return int(str(imagehash.phash(handle)), 16)


def hamming(a: int, b: int) -> int:
    """Numero de bits en que difieren dos hashes."""
    return (a ^ b).bit_count()


def compute_hashes(dataset: CocoDataset, images_dir: Path) -> dict[int, int]:
    """pHash de cada imagen que este en disco, indexado por id.

    Una imagen ausente o ilegible se omite en lugar de romper el analisis: que
    la descarga este incompleta es problema del Tier 1, no de este analizador.
    """
    hashes: dict[int, int] = {}
    for image in dataset.images:
        path = images_dir / image.file_name
        if not path.is_file():
            continue
        try:
            hashes[image.id] = perceptual_hash(path)
        except (UnidentifiedImageError, OSError):
            continue
    return hashes


def find_pairs(hashes: dict[int, int], max_distance: int) -> list[tuple[int, int, int]]:
    """Pares `(id_menor, id_mayor, distancia)` por debajo del umbral."""
    return [
        (a, b, distance)
        for a, b in combinations(sorted(hashes), 2)
        if (distance := hamming(hashes[a], hashes[b])) <= max_distance
    ]


def analyze_duplicates(dataset: CocoDataset, config: DuplicatesCheck, images_dir: Path) -> Result:
    """Marca como infractora la copia, no el original.

    De cada par se reporta el id mayor: el primero en aparecer se considera el
    original y el segundo, la copia. Asi el conteo de infractoras equivale a
    "cuantas imagenes sobran".
    """
    if not config.enabled:
        return _skipped(config)

    hashes = compute_hashes(dataset, images_dir)
    pairs = find_pairs(hashes, config.phash_hamming_distance)
    offenders = sorted({mayor for _, mayor, _ in pairs})

    total = len(dataset.images)
    observed = len(offenders) / total if total else 0.0

    return Result(
        name="duplicates",
        status="fail" if observed > config.max_ratio else "pass",
        severity=config.severity,
        observed=observed,
        threshold=config.max_ratio,
        message=(
            f"{len(pairs)} par(es) de imagenes casi identicas a distancia "
            f"<= {config.phash_hamming_distance} de 64 bits; "
            f"{len(offenders)} de {total} imagenes sobran "
            f"({observed:.1%}; maximo permitido {config.max_ratio:.1%})"
        ),
        offenders=offenders,
    )


def _skipped(config: DuplicatesCheck) -> Result:
    return Result(
        name="duplicates",
        status="skipped",
        severity=config.severity,
        observed=0.0,
        threshold=config.max_ratio,
        message="desactivado en quality.yaml",
    )
