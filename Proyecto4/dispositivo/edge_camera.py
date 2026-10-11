"""Captura USB e inferencia ONNX local para Raspberry Pi OS de 64 bits.

La cámara se invoca como proceso ffmpeg por captura para no retener buffers de
video en Python. Carga el modelo una sola vez, limita ONNX Runtime a un hilo y
persiste foto + evento JSONL antes de continuar. No necesita red.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import onnxruntime as ort
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modelo"))
from preprocess import preprocess, softmax  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture_frame(ffmpeg: str, camera: str, destination: Path, width: int, height: int) -> None:
    """Lee una única imagen JPEG desde una webcam V4L2 (/dev/video0 por defecto)."""
    cmd = [
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "video4linux2",
        "-video_size", f"{width}x{height}", "-i", camera, "-frames:v", "1", "-q:v", "5",
        "-y", str(destination),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode or not destination.is_file() or destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        detail = result.stderr.strip()[-1000:] or f"ffmpeg terminó con código {result.returncode}"
        raise RuntimeError(f"No se pudo capturar {camera}: {detail}")


def enviar_evento_aws(event: dict, endpoint: str, token: str) -> bool:
    """
    Intenta enviar el evento JSON a AWS. 
    Retorna True si fue exitoso o si es un error fatal de cliente (Ej. 400 Bad Request).
    Retorna False SOLO en 503 o errores de red, indicando que se debe reintentar.
    """
    if not endpoint or not token:
        return False

    req = urllib.request.Request(
        endpoint, 
        data=json.dumps(event).encode("utf-8"), 
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status in (200, 201)
    except urllib.error.HTTPError as e:
        if e.code == 503:
            print(f"[*] AWS 503 Service Unavailable. Se retiene ID: {event['capture_id']} para reintento.", file=sys.stderr, flush=True)
            return False
        else:
            print(f"[*] AWS Error {e.code}: {e.reason}. Se descarta reintento para ID: {event['capture_id']}.", file=sys.stderr, flush=True)
            return True  # Retorna True para que no se atore en la cola de reintentos
    except urllib.error.URLError as e:
        print(f"[*] Error de red ({e.reason}). Se retiene ID: {event['capture_id']} para reintento.", file=sys.stderr, flush=True)
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True, help="Ruta al model_int8.onnx local")
    parser.add_argument("--version", required=True, help="Versión exacta del artefacto, p. ej. 1.0.0-int8.1")
    parser.add_argument("--camera", default="/dev/video0", help="Dispositivo V4L2 USB")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--interval", type=float, default=5.0, help="Segundos entre capturas")
    parser.add_argument("--device-id", default="edge01")
    parser.add_argument("--timezone", default="America/Mexico_City", help="Zona IANA para timestamps")
    parser.add_argument("--output", type=Path, default=Path("capturas"))
    parser.add_argument("--ffmpeg", default="ffmpeg", help="Ejecutable ffmpeg con soporte V4L2")
    parser.add_argument("--endpoint", default="", help="URL del endpoint de AWS")
    args = parser.parse_args()
    if args.interval <= 0 or args.width <= 0 or args.height <= 0:
        parser.error("interval, width y height deben ser mayores que cero")
    return args


def main() -> int:
    args = parse_args()
    model = args.model.resolve()
    
    if not model.is_file():
        raise FileNotFoundError("No existe el modelo especificado")
    if shutil.which(args.ffmpeg) is None:
        raise RuntimeError("No se encontró ffmpeg; instálalo con soporte video4linux2")
    
    classes = ["gato", "perro", "persona"]
    model_hash = sha256_file(model)
    
    # Leer el token inyectado en el sistema
    device_token = os.environ.get("P4_DEVICE_TOKEN", "")
    if not device_token:
        print("ADVERTENCIA: Variable de entorno P4_DEVICE_TOKEN no configurada.", flush=True)

    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.enable_mem_pattern = False
    session = ort.InferenceSession(
        str(model), sess_options=options, providers=["CPUExecutionProvider"]
    )
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    args.output.mkdir(parents=True, exist_ok=True)
    tz = ZoneInfo(args.timezone)
    print(f"modelo={args.version} sha256={model_hash} runtime=onnxruntime-{ort.__version__}", flush=True)
    print(f"clases={','.join(classes)} cámara={args.camera}; Ctrl+C para salir", flush=True)

    try:
        while True:
            started = time.perf_counter()
            captured = datetime.now(tz)
            stamp = captured.strftime("%Y%m%dT%H%M%S")
            capture_id = f"{args.device_id}-{stamp}-{uuid.uuid4().hex[:8]}"
            image_path = args.output / f"{capture_id}.jpg"
            try:
                capture_frame(args.ffmpeg, args.camera, image_path, args.width, args.height)
                
                # 1. Hashear el JPEG según contrato de Emilio
                image_hash = sha256_file(image_path)
                
                with Image.open(image_path) as image:
                    tensor = preprocess(image)
                logits = session.run([output_name], {input_name: tensor})[0]
                probabilities = softmax(logits)[0]
                predicted_index = int(np.argmax(probabilities))
                if predicted_index >= len(classes):
                    raise ValueError("La cantidad de salidas no coincide")
                confidence = float(probabilities[predicted_index])
                if not 0.0 <= confidence <= 1.0:
                    raise ValueError("Confianza fuera del rango [0, 1]")
                elapsed_ms = (time.perf_counter() - started) * 1000
                
                # 2. Ensamblar JSON según contrato
                event = {
                    "capture_id": capture_id,
                    "captured_at": captured.isoformat(timespec="milliseconds"),
                    "predicted_class": classes[predicted_index],
                    "confidence": confidence,
                    "device_id": args.device_id,
                    "model_version": args.version,
                    "model_sha256": model_hash,
                    "image_sha256": image_hash,
                    "image_ref": str(image_path),
                }
                
                # 3. Guardar evento local (para cumplir la Fase 3 offline)
                log_path = args.output / "events.jsonl"
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                    log.flush()
                    os.fsync(log.fileno())
                print(
                    f"{capture_id} {event['predicted_class']} confianza={confidence:.4f} "
                    f"tiempo={elapsed_ms:.1f}ms foto={image_path}", flush=True
                )
                
                # 4. Intento de envío a AWS
                if args.endpoint and device_token:
                    enviado = enviar_evento_aws(event, args.endpoint, device_token)
                    # Aquí irá la lógica de reintento con archivo de cola en la Fase 9
                
            except Exception as exc:
                print(f"captura fallida ({capture_id}): {exc}", file=sys.stderr, flush=True)
            remaining = args.interval - (time.perf_counter() - started)
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        print("\ncaptura detenida", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())