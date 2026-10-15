"""Recalcula, solo leyendo archivos del repositorio, las cifras de calidad (F7) y recursos (F8).

    python evidencias/comprobaciones/recalcular.py        (desde Proyecto4/, con numpy)

- Calidad: une original y optimizado por `crop_id` en
  `calidad/registros/predicciones_validacion.csv`,
  comprueba IDs unicos y clases declaradas, y calcula accuracy, F1 por clase y macro (F1 = 0 si una
  clase no tiene predicciones positivas) y la caida en puntos porcentuales sin redondear.
- Recursos: p50 y p95 por variante desde `recursos/registros/tiempos_inferencia.csv`, excluyendo el
  calentamiento, con interpolacion lineal (`numpy.percentile`, method="linear").
- Compara cada cifra con la que declaran `metricas.json` y `resumen_recursos.json`.
Sale con 0 si todo coincide y 1 si algo no.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
CLASES = ("cat", "dog", "person")
diferencias: list[str] = []


def leer_csv(ruta: str) -> list[dict[str, str]]:
    with open(RAIZ / ruta, encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def comparar(nombre: str, calculado: float, declarado: float, tolerancia: float = 1e-9) -> None:
    ok = abs(calculado - declarado) <= tolerancia
    estado = "OK" if ok else "NO"
    print(f"  {nombre:42} calculado={calculado!r:24} declarado={declarado!r:24} {estado}")
    if not ok:
        diferencias.append(nombre)


def f1_por_clase(reales: list[str], predichas: list[str]) -> dict[str, float]:
    f1 = {}
    for clase in CLASES:
        tp = sum(r == clase and p == clase for r, p in zip(reales, predichas, strict=True))
        fp = sum(r != clase and p == clase for r, p in zip(reales, predichas, strict=True))
        fn = sum(r == clase and p != clase for r, p in zip(reales, predichas, strict=True))
        f1[clase] = 0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn)
    return f1


def calidad() -> None:
    filas = leer_csv("calidad/registros/predicciones_validacion.csv")
    metricas = json.loads((RAIZ / "calidad/registros/metricas.json").read_text(encoding="utf-8"))
    ids = [f["crop_id"] for f in filas]
    print(
        f"Calidad: {len(filas)} muestras, IDs unicos: {len(set(ids)) == len(ids)}, "
        f"clases reales: {dict(Counter(f['true_class'] for f in filas))}"
    )
    if len(set(ids)) != len(ids):
        diferencias.append("IDs duplicados")
    reales = [f["true_class"] for f in filas]
    acc = {}
    for modelo, columna in (("original", "pred_original"), ("optimizado", "pred_optimizado")):
        predichas = [f[columna] for f in filas]
        acc[modelo] = sum(r == p for r, p in zip(reales, predichas, strict=True)) / len(filas)
        f1 = f1_por_clase(reales, predichas)
        comparar(f"accuracy {modelo}", acc[modelo], metricas[modelo]["accuracy"])
        comparar(f"f1_macro {modelo}", sum(f1.values()) / len(CLASES), metricas[modelo]["f1_macro"])
    comparar(
        "caida de accuracy (pp)",
        100 * (acc["original"] - acc["optimizado"]),
        metricas["accuracy_drop_pp"],
    )


def recursos() -> None:
    filas = leer_csv("recursos/registros/tiempos_inferencia.csv")
    resumen = json.loads(
        (RAIZ / "recursos/registros/resumen_recursos.json").read_text(encoding="utf-8")
    )
    print(
        f"Recursos: {len(filas)} filas; por variante y fase: "
        f"{dict(Counter((f['variante'], f['es_calentamiento']) for f in filas))}"
    )
    for variante in ("onnx_fp32", "onnx_int8"):
        validas = [
            float(f["total_ms"])
            for f in filas
            if f["variante"] == variante and f["es_calentamiento"] == "False"
        ]
        declarado = resumen["benchmarks"][variante]["total_local"]
        if len(validas) != 100:
            diferencias.append(f"{variante}: {len(validas)} medidas")
        comparar(
            f"{variante} p50 total (ms)",
            float(np.percentile(validas, 50, method="linear")),
            declarado["p50_ms"],
            1e-3,
        )
        comparar(
            f"{variante} p95 total (ms)",
            float(np.percentile(validas, 95, method="linear")),
            declarado["p95_ms"],
            1e-3,
        )


if __name__ == "__main__":
    calidad()
    recursos()
    print("RESULTADO:", "todo coincide" if not diferencias else f"diferencias en {diferencias}")
    sys.exit(1 if diferencias else 0)
