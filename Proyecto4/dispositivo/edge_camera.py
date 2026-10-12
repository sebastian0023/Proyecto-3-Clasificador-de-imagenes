import argparse
import time
import os
import sys
import json
import uuid
import hashlib
from datetime import datetime, timezone
import requests

import onnxruntime as ort
import numpy as np
import cv2

# Importamos el preprocesamiento de Edith (asegúrate de que esté en la misma carpeta o ruta accesible)
try:
    import preprocess
except ImportError:
    print("Advertencia: No se encontró preprocess.py, asegúrate de que esté en el directorio.")

# 1. Configuración de Clases (Cambio a inglés requerido por el PR)
CLASSES = ["cat", "dog", "person"]

# 2. Configuración de Hash esperado por seguridad
EXPECTED_MODEL_HASH = "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0"
AWS_ENDPOINT = "https://174-129-84-80.sslip.io/api/p4/captures"

def get_file_hash(filepath):
    """Calcula el hash SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def enviar_aws_con_reintentos(evento, ruta_imagen, token):
    """
    Envía los datos a la nube usando multipart/form-data y maneja reintentos 
    si hay errores de red (Ej. Wi-Fi apagado) o errores 503.
    """
    headers = {
        "Authorization": f"Bearer {token}"
        # request.post se encarga automáticamente del Content-Type para multipart
    }
    
    while True:
        try:
            with open(ruta_imagen, 'rb') as img_file:
                # Armamos el multipart con el JSON como string y la imagen binaria
                archivos = {
                    'event': (None, json.dumps(evento), 'application/json'),
                    'image': (os.path.basename(ruta_imagen), img_file, 'image/jpeg')
                }
                
                response = requests.post(AWS_ENDPOINT, headers=headers, files=archivos, timeout=10)
            
            if response.status_code == 201:
                # Envío exitoso
                break 
            elif response.status_code in [500, 502, 503, 504]:
                print(f"  [!] Error de servidor {response.status_code}. Reintentando en 5s...")
                time.sleep(5)
            else:
                print(f"  [x] Error rechazado ({response.status_code}): {response.text}")
                break # Rechazado por formato o token, no reintenta
                
        except requests.exceptions.RequestException as e:
            # Error de red (sin internet o servidor inalcanzable)
            print(f"  [!] Error de red. Reintentando en 5s...")
            time.sleep(5)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Ruta al modelo ONNX")
    parser.add_argument("--version", required=True, help="Versión del modelo")
    args = parser.parse_args()

    token = os.environ.get("P4_DEVICE_TOKEN")
    if not token:
        print("ERROR: La variable de entorno P4_DEVICE_TOKEN no está configurada.")
        sys.exit(1)

    # 3. Validación de seguridad del Hash del modelo
    print("Verificando integridad del modelo...")
    if not os.path.exists(args.model):
        print(f"ERROR: No existe el modelo en {args.model}")
        sys.exit(1)
        
    model_hash = get_file_hash(args.model)
    if not model_hash.startswith(EXPECTED_MODEL_HASH):
        print(f"ERROR FATAL: El hash del modelo ({model_hash[:15]}...) no coincide con el esperado de F2.")
        sys.exit(1)

    # Iniciar ONNX Runtime
    session = ort.InferenceSession(args.model)
    input_name = session.get_inputs()[0].name
    
    print(f"modelo={args.version} sha256={model_hash} runtime=onnxruntime-{ort.__version__}")
    print(f"clases={','.join(CLASSES)} cámara=/dev/video0; Ctrl+C para salir")

    # Crear carpeta de capturas
    capturas_dir = os.path.join(os.path.dirname(__file__), "capturas")
    os.makedirs(capturas_dir, exist_ok=True)
    events_log = os.path.join(capturas_dir, "events.jsonl")

    # Iniciar cámara
    cap = cv2.VideoCapture(0)
    device_id = "edge01"

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # Identificador y timestamp únicos de la captura
            capture_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            short_uuid = capture_id[:8]
            
            # Realizar Inferencia
            start_time = time.time()
            
            # Usamos el preprocesamiento de Edith (ajustar si tu método se llama distinto)
            try:
                input_tensor = preprocess.preprocesar_imagen(frame)
            except NameError:
                # Fallback rápido por si falta la importación (redimensionar genérico)
                img_resized = cv2.resize(frame, (224, 224))
                input_tensor = np.expand_dims(img_resized, axis=0).astype(np.float32)

            outputs = session.run(None, {input_name: input_tensor})
            inference_time_ms = (time.time() - start_time) * 1000
            
            # Determinar clase
            confidences = outputs[0][0]
            class_idx = np.argmax(confidences)
            predicted_class = CLASSES[class_idx]
            confidence = confidences[class_idx]

            # Guardar foto localmente
            filename = f"{device_id}-{timestamp}-{short_uuid}.jpg"
            filepath = os.path.join(capturas_dir, filename)
            cv2.imwrite(filepath, frame)
            
            # Calcular hash de la imagen
            image_hash = get_file_hash(filepath)

            # 4. Estructurar evento JSON (Añadiendo schema_version: 1)
            evento = {
                "schema_version": 1,
                "capture_id": capture_id,
                "device_id": device_id,
                "timestamp": timestamp,
                "model_version": args.version,
                "predicted_class": predicted_class,
                "confidence": float(confidence),
                "inference_time_ms": float(inference_time_ms),
                "image_hash": image_hash
            }

            # Guardar en events.jsonl localmente
            with open(events_log, "a") as f:
                f.write(json.dumps(evento) + "\n")

            # Imprimir en consola con formato
            print(f"{device_id}-{timestamp}-{short_uuid} {predicted_class} confianza={confidence:.4f} tiempo={inference_time_ms:.1f}ms foto=capturas/{filename}")

            # Enviar a AWS (bloqueante, reintentará si no hay red)
            enviar_aws_con_reintentos(evento, filepath, token)

            # Pausa de 5 segundos antes de la siguiente captura
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nSaliendo del programa...")
    finally:
        cap.release()

if __name__ == "__main__":
    main()
