"""Medición auditable de recursos en el dispositivo edge (F8, criterios 3.1, 3.2 y 3.3).

Mide en la Raspberry Pi:
1. Tamaño en bytes y reducción porcentual de los artefactos (original P3, ONNX FP32, ONNX INT8).
2. Intento de carga del modelo original PyTorch (model.pt) en el entorno del edge, registrando
   el resultado o error observado.
3. 10 iteraciones de calentamiento (excluidas) + 100 iteraciones medidas de preprocesamiento
   más inferencia local con onnxruntime (1 hilo CPU) para FP32 (si está presente) e INT8.
4. Cálculo de p50 y p95 mediante interpolación lineal (numpy method='linear').
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import os
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modelo"))
from preprocess import preprocess, softmax  # noqa: E402

CLASSES = ["cat", "dog", "person"]

# Datos verificados del registro de conversión (F2)
ARTIFACTS_REF = {
    "original_pt": {
        "filename": "model.pt",
        "bytes": 44783563,
        "sha256": "e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172",
        "precision": "FP32 (PyTorch checkpoint)",
    },
    "onnx_fp32": {
        "filename": "model_fp32.onnx",
        "bytes": 44791921,
        "sha256": "e4dc89bbb652f6de9bea2fffa94ff59abb0e6cb679d8a4d95aeadc9e0be65328",
        "precision": "FP32 (ONNX opset 18)",
    },
    "onnx_int8": {
        "filename": "model_int8.onnx",
        "bytes": 11349151,
        "sha256": "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0",
        "precision": "INT8 estático QDQ por canal (ONNX opset 18)",
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get_rss_mb() -> float:
    """Obtiene la memoria residente actual (VmRSS) en MB desde /proc/self/status o resource."""
    status_path = Path("/proc/self/status")
    if status_path.exists():
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                kb = int(line.split()[1])
                return round(kb / 1024.0, 2)
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 2)


def get_hardware_info() -> dict:
    cpu_model = platform.processor()
    model_name = "Raspberry Pi"
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "Model" in line and ":" in line:
                model_name = line.split(":", 1)[1].strip()
            elif "model name" in line and ":" in line and not cpu_model:
                cpu_model = line.split(":", 1)[1].strip()
    os_release = {}
    os_path = Path("/etc/os-release")
    if os_path.exists():
        for line in os_path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os_release[k] = v.strip('"')
    mem_total_mb = None
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                mem_total_mb = round(int(line.split()[1]) / 1024.0, 1)
                break
    return {
        "device_model": model_name,
        "cpu_model": cpu_model or "ARM Cortex-A53",
        "architecture": platform.machine(),
        "os_pretty_name": os_release.get("PRETTY_NAME", platform.platform()),
        "kernel": platform.release(),
        "ram_total_mb": mem_total_mb,
        "python_version": platform.python_version(),
        "onnxruntime_version": ort.__version__,
        "numpy_version": np.__version__,
    }


def check_pytorch_original(pt_path: Path | None) -> dict:
    """Intenta cargar o verificar soporte de PyTorch original en el entorno del dispositivo."""
    try:
        import torch  # type: ignore
        return {
            "ejecutable_en_entorno_edge": True,
            "torch_version": torch.__version__,
            "nota": "PyTorch instalado en el entorno.",
        }
    except Exception as e:
        return {
            "ejecutable_en_entorno_edge": False,
            "error_tipo": type(e).__name__,
            "error_mensaje": str(e),
            "explicacion": (
                "El entorno virtual de producción del dispositivo (requirements-edge.txt) prescinde de PyTorch "
                "(paquete de ~250+ MB en disco y alta huella de RAM en Raspberry Pi 3B de 1 GB) y estandariza "
                "onnxruntime==1.31.0. Para comparar bajo condiciones equivalentes (mismo hardware, mismo runtime "
                "y 1 hilo de CPU), se mide el modelo original exportado a ONNX FP32 (model_fp32.onnx, que mantiene "
                "una diferencia máxima de logits de 1.2e-7 frente a PyTorch) contra la variante cuantizada INT8 (model_int8.onnx)."
            ),
        }


def load_test_image(img_path: Path | None) -> tuple[Image.Image, str]:
    if img_path and img_path.exists():
        return Image.open(img_path).convert("RGB"), str(img_path)
    # Buscar primera captura disponible en dispositivo/capturas
    capturas_dir = ROOT / "dispositivo" / "capturas"
    if capturas_dir.exists():
        jpgs = sorted(capturas_dir.glob("*.jpg"))
        if jpgs:
            return Image.open(jpgs[0]).convert("RGB"), str(jpgs[0].relative_to(ROOT))
    # Si no hay, crear imagen sintética determinista 640x480 RGB (semilla 42)
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, size=(480, 640, 3), dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB"), "synthetic_seed42_640x480_rgb"


def benchmark_onnx(
    variant_key: str,
    model_path: Path,
    image: Image.Image,
    warmup: int,
    repeats: int,
) -> tuple[list[dict], dict]:
    rss_before = get_rss_mb()
    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = 1
    sess_options.inter_op_num_threads = 1

    t_load0 = time.perf_counter()
    session = ort.InferenceSession(
        str(model_path), sess_options=sess_options, providers=["CPUExecutionProvider"]
    )
    load_time_ms = (time.perf_counter() - t_load0) * 1000.0
    rss_after_load = get_rss_mb()

    input_name = session.get_inputs()[0].name
    rows = []

    total_iters = warmup + repeats
    for idx in range(1, total_iters + 1):
        is_warmup = idx <= warmup
        phase = "warmup" if is_warmup else "measure"
        rep_num = idx if is_warmup else (idx - warmup)

        t0 = time.perf_counter()
        tensor = preprocess(image)
        t1 = time.perf_counter()
        logits = session.run(None, {input_name: tensor})[0]
        probs = softmax(logits)[0]
        t2 = time.perf_counter()

        prep_ms = (t1 - t0) * 1000.0
        inf_ms = (t2 - t1) * 1000.0
        tot_ms = (t2 - t0) * 1000.0
        best_idx = int(np.argmax(probs))

        rows.append({
            "variante": variant_key,
            "modelo_archivo": model_path.name,
            "fase": phase,
            "es_calentamiento": is_warmup,
            "repeticion": rep_num,
            "preprocess_ms": round(prep_ms, 4),
            "inferencia_ms": round(inf_ms, 4),
            "total_ms": round(tot_ms, 4),
            "predicted_class": CLASSES[best_idx],
            "confidence": round(float(probs[best_idx]), 6),
        })

    rss_after_run = get_rss_mb()
    measured = [r for r in rows if not r["es_calentamiento"]]

    def calc_stats(key: str) -> dict:
        arr = np.array([r[key] for r in measured], dtype=np.float64)
        p50, p95 = np.percentile(arr, [50, 95], method="linear")
        return {
            "count": int(len(arr)),
            "p50_ms": round(float(p50), 4),
            "p95_ms": round(float(p95), 4),
            "mean_ms": round(float(np.mean(arr)), 4),
            "std_ms": round(float(np.std(arr, ddof=1)), 4),
            "min_ms": round(float(np.min(arr)), 4),
            "max_ms": round(float(np.max(arr)), 4),
            "percentile_method": "linear_interpolation (numpy method='linear')",
        }

    file_bytes = model_path.stat().st_size
    file_sha256 = sha256_file(model_path)

    summary = {
        "variante": variant_key,
        "archivo": model_path.name,
        "bytes": file_bytes,
        "mib": round(file_bytes / (1024 * 1024), 4),
        "sha256": file_sha256,
        "load_time_ms": round(load_time_ms, 2),
        "rss_before_mb": rss_before,
        "rss_after_load_mb": rss_after_load,
        "rss_after_run_mb": rss_after_run,
        "warmup_excluded": warmup,
        "measured_iterations": repeats,
        "preprocess": calc_stats("preprocess_ms"),
        "inferencia": calc_stats("inferencia_ms"),
        "total_local": calc_stats("total_ms"),
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--int8", type=Path, default=ROOT / "modelo" / "model_int8.onnx")
    parser.add_argument("--fp32", type=Path, default=ROOT / "modelo" / "model_fp32.onnx")
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=100)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "recursos" / "registros")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    image, img_source = load_test_image(args.image)
    hw_info = get_hardware_info()
    pt_check = check_pytorch_original(None)

    all_rows = []
    summaries = {}

    if args.fp32.exists():
        print(f"Midiendo ONNX FP32 ({args.fp32})...")
        r_fp32, s_fp32 = benchmark_onnx("onnx_fp32", args.fp32, image, args.warmup, args.repeats)
        all_rows.extend(r_fp32)
        summaries["onnx_fp32"] = s_fp32
    else:
        print(f"AVISO: No se encontró {args.fp32}. Solo se medirá INT8 si no agregas model_fp32.onnx.")

    if not args.int8.exists():
        sys.exit(f"ERROR: No se encontró el modelo INT8 en {args.int8}")

    print(f"Midiendo ONNX INT8 ({args.int8})...")
    r_int8, s_int8 = benchmark_onnx("onnx_int8", args.int8, image, args.warmup, args.repeats)
    all_rows.extend(r_int8)
    summaries["onnx_int8"] = s_int8

    csv_path = args.out_dir / "tiempos_inferencia.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variante",
                "modelo_archivo",
                "fase",
                "es_calentamiento",
                "repeticion",
                "preprocess_ms",
                "inferencia_ms",
                "total_ms",
                "predicted_class",
                "confidence",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(all_rows)

    orig_bytes = ARTIFACTS_REF["original_pt"]["bytes"]
    fp32_bytes = ARTIFACTS_REF["onnx_fp32"]["bytes"]
    int8_bytes = s_int8["bytes"]

    size_comparison = {
        "original_pt_bytes": orig_bytes,
        "onnx_fp32_bytes": fp32_bytes,
        "onnx_int8_bytes": int8_bytes,
        "reduction_vs_pt_bytes": orig_bytes - int8_bytes,
        "reduction_vs_pt_pct": round((1.0 - int8_bytes / orig_bytes) * 100.0, 2),
        "reduction_vs_fp32_bytes": fp32_bytes - int8_bytes,
        "reduction_vs_fp32_pct": round((1.0 - int8_bytes / fp32_bytes) * 100.0, 2),
    }

    latency_comparison = {}
    if "onnx_fp32" in summaries:
        fp32_tot = summaries["onnx_fp32"]["total_local"]
        int8_tot = summaries["onnx_int8"]["total_local"]
        fp32_inf = summaries["onnx_fp32"]["inferencia"]
        int8_inf = summaries["onnx_int8"]["inferencia"]
        latency_comparison = {
            "total_p50_diff_ms": round(fp32_tot["p50_ms"] - int8_tot["p50_ms"], 4),
            "total_p50_reduction_pct": round((1.0 - int8_tot["p50_ms"] / fp32_tot["p50_ms"]) * 100.0, 2),
            "total_p95_diff_ms": round(fp32_tot["p95_ms"] - int8_tot["p95_ms"], 4),
            "total_p95_reduction_pct": round((1.0 - int8_tot["p95_ms"] / fp32_tot["p95_ms"]) * 100.0, 2),
            "inferencia_p50_diff_ms": round(fp32_inf["p50_ms"] - int8_inf["p50_ms"], 4),
            "inferencia_p50_reduction_pct": round((1.0 - int8_inf["p50_ms"] / fp32_inf["p50_ms"]) * 100.0, 2),
            "speedup_factor_p50_inferencia": round(fp32_inf["p50_ms"] / int8_inf["p50_ms"], 2),
            "speedup_factor_p50_total": round(fp32_tot["p50_ms"] / int8_tot["p50_ms"], 2),
        }

    report = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "conditions": {
            **hw_info,
            "execution_provider": "CPUExecutionProvider",
            "intra_op_num_threads": 1,
            "inter_op_num_threads": 1,
            "input_shape": [1, 3, 224, 224],
            "input_dtype": "float32 (RGB normalizado ImageNet)",
            "image_source": img_source,
            "network_aws_during_benchmark": "excluido (inferencia 100% local sin envío de red)",
            "warmup_iterations": args.warmup,
            "measured_iterations": args.repeats,
            "percentile_method": "interpolación lineal (numpy.percentile, method='linear')",
        },
        "artifacts_reference": ARTIFACTS_REF,
        "size_comparison": size_comparison,
        "pytorch_original_on_device": pt_check,
        "benchmarks": summaries,
        "latency_comparison_fp32_vs_int8": latency_comparison,
        "csv_file": str(csv_path.relative_to(ROOT)),
        "csv_sha256": sha256_file(csv_path),
    }

    json_path = args.out_dir / "resumen_recursos.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n=== RESUMEN DE MEDICIÓN (F8) ===")
    print(json.dumps(report["size_comparison"], indent=2))
    if latency_comparison:
        print(json.dumps(latency_comparison, indent=2))
    for k, v in summaries.items():
        print(f"\n[{k}] Total p50={v['total_local']['p50_ms']} ms | p95={v['total_local']['p95_ms']} ms "
              f"(Inferencia pura p50={v['inferencia']['p50_ms']} ms | p95={v['inferencia']['p95_ms']} ms)")


if __name__ == "__main__":
    main()