"""Comparacion de calidad original contra optimizado (F7, criterio 1.3).

Une por `crop_id` las predicciones de `predecir.py` y las revisa contra el
manifiesto de validacion del P3 antes de calcular nada:

- ninguna muestra de `val` falta y ninguna sobra;
- sin IDs duplicados;
- la clase real de cada fila es la del manifiesto;
- las tres clases declaradas tienen soporte;
- cada archivo de predicciones viene del modelo esperado (SHA-256 del .meta.json).

Metricas sobre el mapa de clases completo: accuracy, precision, recall y F1 por
clase (F1 = 0 si la clase no tiene predicciones positivas), F1 macro, soporte,
matrices de confusion y caida de accuracy en puntos porcentuales sin redondear.

Escribe `predicciones_validacion.csv` (una fila por muestra con ambas
predicciones) y `metricas.json`.

Uso (desde Proyecto4/): .venv/Scripts/python calidad/comparar.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ["cat", "dog", "person"]
ORIGINAL_SHA256 = "e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172"
OPTIMIZED_SHA256 = "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0"
MANIFEST_SHA256 = "45600f297d13f51685e051e0cbc4962beb1f7c6a4e03247cbf61a345e6fa4305"
MAX_DROP_PP = 2.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(prefix: Path, expected_model: str) -> tuple[dict[str, dict], dict]:
    meta = json.loads(prefix.with_suffix(".meta.json").read_text(encoding="utf-8"))
    csv_path = prefix.with_suffix(".csv")
    problems = []
    if meta["model_sha256"] != expected_model:
        problems.append(f"modelo {meta['model_sha256']} != {expected_model}")
    if meta["manifest_sha256"] != MANIFEST_SHA256:
        problems.append("manifiesto distinto")
    if meta["csv_sha256"] != sha256(csv_path):
        problems.append("el CSV cambio despues de generarse")
    if problems:
        sys.exit(f"{csv_path}: " + "; ".join(problems))
    rows: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["crop_id"] in rows:
                sys.exit(f"{csv_path}: crop_id duplicado {row['crop_id']}")
            rows[row["crop_id"]] = row
    return rows, meta


def check_against_manifest(manifest: Path, *tables: dict[str, dict]) -> dict[str, str]:
    if sha256(manifest) != MANIFEST_SHA256:
        sys.exit(f"{manifest} no es el manifiesto m-0.1.3-s42-1")
    truth: dict[str, str] = {}
    for row in map(json.loads, manifest.open(encoding="utf-8")):
        if row["split"] != "val":
            continue
        if row["crop_id"] in truth:
            sys.exit(f"manifiesto con crop_id duplicado {row['crop_id']}")
        truth[row["crop_id"]] = row["category_name"]
    for table in tables:
        missing = truth.keys() - table.keys()
        extra = table.keys() - truth.keys()
        if missing or extra:
            sys.exit(f"faltan {sorted(missing)[:5]} / sobran {sorted(extra)[:5]}")
        wrong = [k for k, r in table.items() if r["true_class"] != truth[k]]
        if wrong:
            sys.exit(f"etiquetas distintas al manifiesto: {wrong[:5]}")
    absent = set(CLASSES) - set(truth.values())
    if absent:
        sys.exit(f"clases sin soporte en validacion: {absent}")
    return truth


def metrics(truth: dict[str, str], pred: dict[str, str]) -> dict:
    ids = sorted(truth)
    confusion = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    for k in ids:
        confusion[truth[k]][pred[k]] += 1
    per_class = {}
    for c in CLASSES:
        tp = confusion[c][c]
        fp = sum(confusion[t][c] for t in CLASSES if t != c)
        fn = sum(confusion[c][p] for p in CLASSES if p != c)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[c] = {"support": tp + fn, "tp": tp, "fp": fp, "fn": fn,
                        "precision": precision, "recall": recall, "f1": f1}
    correct = sum(truth[k] == pred[k] for k in ids)
    return {
        "samples": len(ids),
        "correct": correct,
        "accuracy": correct / len(ids),
        "f1_macro": sum(v["f1"] for v in per_class.values()) / len(CLASSES),
        "per_class": per_class,
        "confusion_matrix": {"rows_true_cols_pred": CLASSES,
                             "matrix": [[confusion[t][p] for p in CLASSES] for t in CLASSES]},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registros", type=Path, default=ROOT / "calidad/registros")
    parser.add_argument("--manifest", type=Path,
                        default=ROOT.parent / "Proyecto3/data/manifests/m-0.1.3-s42-1/manifest.jsonl")
    args = parser.parse_args()
    reg = args.registros

    original, meta_o = load(reg / "pred_original", ORIGINAL_SHA256)
    optimized, meta_q = load(reg / "pred_optimizado", OPTIMIZED_SHA256)
    if meta_q["machine"] not in ("aarch64", "arm64"):
        sys.exit("la variante optimizada debe evaluarse en aarch64 (el runtime del edge)")
    truth = check_against_manifest(args.manifest, original, optimized)

    pred_o = {k: r["pred_class"] for k, r in original.items()}
    pred_q = {k: r["pred_class"] for k, r in optimized.items()}
    m_o, m_q = metrics(truth, pred_o), metrics(truth, pred_q)
    drop_pp = 100 * (m_o["accuracy"] - m_q["accuracy"])

    out_csv = reg / "predicciones_validacion.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["crop_id", "true_class", "pred_original", "pred_optimizado",
                         "conf_original", "conf_optimizado", "coinciden"])
        for k in sorted(truth):
            writer.writerow([k, truth[k], pred_o[k], pred_q[k], original[k]["confidence"],
                             optimized[k]["confidence"], int(pred_o[k] == pred_q[k])])

    changed = [
        {"crop_id": k, "true_class": truth[k], "pred_original": pred_o[k], "pred_optimizado": pred_q[k],
         "conf_original": float(original[k]["confidence"]), "conf_optimizado": float(optimized[k]["confidence"]),
         **{f"optimizado_p_{c}": float(optimized[k][f"p_{c}"]) for c in CLASSES}}
        for k in sorted(truth) if pred_o[k] != pred_q[k] or truth[k] != pred_o[k] or truth[k] != pred_q[k]
    ]
    report = {
        "manifest_id": "m-0.1.3-s42-1",
        "manifest_sha256": MANIFEST_SHA256,
        "split": "val",
        "classes": CLASSES,
        "checks": {"missing": 0, "extra": 0, "duplicates": 0, "label_mismatches": 0,
                   "classes_with_support": CLASSES},
        "original": {"model_sha256": meta_o["model_sha256"], "run": meta_o, **m_o},
        "optimizado": {"model_sha256": meta_q["model_sha256"], "run": meta_q, **m_q},
        "accuracy_drop_pp": drop_pp,
        "accuracy_drop_within_2pp": drop_pp <= MAX_DROP_PP,
        "f1_macro_drop": m_o["f1_macro"] - m_q["f1_macro"],
        "agreement": sum(pred_o[k] == pred_q[k] for k in truth),
        "errores_y_cambios": changed,
        "predicciones_csv_sha256": sha256(out_csv),
    }
    (reg / "metricas.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for name, m in (("original", m_o), ("optimizado", m_q)):
        f1 = " ".join(f"{c}={m['per_class'][c]['f1']:.4f}" for c in CLASSES)
        print(f"{name:10} acc={m['accuracy']!r} f1_macro={m['f1_macro']!r} {f1}")
    print(f"caida_pp={drop_pp!r} coinciden={report['agreement']}/{len(truth)} filas_revisar={len(changed)}")


if __name__ == "__main__":
    main()
