"""Huella de un ONNX sin los metadatos de nodo que dependen de la máquina (F2).

El exportador de PyTorch (dynamo) guarda en cada nodo `metadata_props` de
depuración; `pkg.torch.onnx.stack_trace` incluye la ruta absoluta del código en
la máquina que convirtió. Por eso `convert.py` da el mismo modelo en cualquier
máquina, pero el SHA-256 del archivo cambia con la ruta del repositorio.

Esta huella es el SHA-256 del modelo serializado sin esos metadatos de nodo:
pesos, grafo, opset y atributos quedan incluidos. Sirve para comprobar que una
reconversión en otra máquina produce el mismo modelo que el publicado. El
SHA-256 del archivo sigue siendo el que identifica el artefacto publicado.

Uso (desde Proyecto4/): python modelo/huella.py artifacts/1.0.0-int8.1/model_int8.onnx
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import onnx


def huella(path: Path) -> str:
    model = onnx.load(str(path))
    for node in model.graph.node:
        del node.metadata_props[:]
    return hashlib.sha256(model.SerializeToString()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("modelos", type=Path, nargs="+")
    args = parser.parse_args()
    for path in args.modelos:
        archivo = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"{path.name}  archivo={archivo}  huella={huella(path)}")


if __name__ == "__main__":
    main()
