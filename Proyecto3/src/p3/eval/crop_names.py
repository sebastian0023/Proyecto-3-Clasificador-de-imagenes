"""Nombre de archivo seguro para el recorte de un ejemplo de evaluacion.

El `crop_id` del manifiesto (p. ej. `0.1.3:a1`) trae `:` y puede traer `/`, que
no sirven como nombre de artefacto. Esta funcion la comparten quien LOGUEA los
recortes a MLflow (`p3.eval.evaluate`) y quien los SIRVE por HTTP
(`p3.eval.api`), para que ambos coincidan en el mismo nombre. Solo usa `re`, asi
que `p3.eval.api` la puede importar sin arrastrar torch (criterio 4.2).
"""

from __future__ import annotations

import re

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def safe_crop_name(crop_id: str) -> str:
    """`crop_id` saneado a un nombre de archivo (sin extension)."""
    return _UNSAFE.sub("_", crop_id)
