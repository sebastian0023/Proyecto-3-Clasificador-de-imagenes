import os
import sys
import time
import json
import hashlib
import argparse
import datetime
import uuid
import numpy as np
import cv2
import requests
import onnxruntime as ort

# ==========================================
# CONFIGURACIÓN DEL DISPOSITIVO Y AWS
# ==========================================
API_URL = "https://174-129-84-80.sslip.io/api/p4/captures"
TOKEN = os.environ.get("P4_DEVICE_TOKEN")
CLASES = ["cat", "dog", "person"]  # Clases en inglés (Contrato AWS)

def verificar_hash(ruta_modelo):
    """Verifica que el modelo cargado sea exactamente el autorizado (Seguridad)"""
    hash_esperado = "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0"
    with open(ruta_modelo, "rb") as f:
        hash_calculado = hashlib.sha256(f.read()).hexdigest()
    
    if not hash_calculado.startswith(hash_esperado):
        print("ERROR FATAL: El hash del modelo no coincide. Por seguridad, no se ejecutará.")
        sys.exit(1)
    return hash_calculado

def preprocess_fallback(frame):
    """Fallback si no existe preprocess.py. Transforma la imagen al formato ONNX (1, 3, 224, 224)"""
    # 1. Redimensionar a 224x224
    img = cv2.resize(frame, (224, 224))
    # 2. Convertir BGR a RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # 3. Normalizar a float32 entre 0 y 1
    img = img.astype(np.float32) / 255.0
    # 4. Transponer dimensiones: de (Alto, Ancho, Canales) a (Canales, Alto, Ancho)
    img = np.transpose(img, (2, 0, 1))
    # 5. Agregar dimensión de lote (Batch size = 1)
    img = np.expand_dims(img, axis=0)
    return img

def enviar_aws_con_reintentos(url, token, evento, ruta_imagen):
    """Envía el JSON y la imagen en multipart/form-data. Reintenta si hay fallo de red o 503."""
    if not token:
        print("Advertencia: No hay TOKEN configurado, se omite el envío a AWS.")
        return

    headers = {
        "Authorization": f"Bearer {token}"
        # No poner Content-Type, 'requests' lo hace automático para multipart
    }
    
    while True:
        try:
            with open(ruta_imagen, 'rb') as img_file:
                archivos = {
                    'event': (None, json.dumps(evento), 'application/json'),
                    'image': (os.path.basename(ruta_imagen), img_file, 'image/jpeg')
                }
                
                print(f"Enviando captura {evento['capture_id']} a AWS...")
                response = requests.post(url, headers=headers, files=archivos, timeout=10)
            
            if response.status_code == 201:
                print("¡Envío exitoso (201) a AWS!")
                break
            elif response.status_code in [500, 502, 503, 504]:
                print(f"Error {response.status_code} en servidor. Reintentando en 5 segundos...")
                time.sleep(5)
            else:
                print(f"Rechazado por el servidor {response.status_code}: {response.text}")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"Fallo de conexión ({e}). Reintentando en 5 segundos...")
            time.sleep(5)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Ruta al modelo .onnx")
    parser.add_argument("--version", required=True, help="Versión del modelo")
    args = parser.parse_args()

    # 1. Validación de seguridad
    print("Verificando integridad del modelo...")
    hash_modelo = verificar_hash(args.model)
    print(f"modelo={args.version} sha256={hash_modelo} runtime=onnxruntime-{ort.__version__}")
    print(f"clases={','.join(CLASES)} cámara=/dev/video0; Ctrl+C para salir")
    
    # 2. Intentar cargar módulo de preprocesamiento de Edith
    try:
        from preprocess import preprocess_image
        has_preprocess = True
    except ImportError:
        print("Advertencia: No se encontró preprocess.py, asegúrate de que esté en el directorio.")
        has_preprocess = False

    # 3. Configurar sesión de ONNX a 1 solo hilo (para no saturar la Raspberry Pi)
    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = 1
    session_options.inter_op_num_threads = 1
    session = ort.InferenceSession(args.model, sess_options=session_options)
    input_name = session.get_inputs()[0].name

    # 4. Inicializar cámara y directorios
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara web USB.")
        return

    os.makedirs("Proyecto4/dispositivo/capturas", exist_ok=True)
    ruta_jsonl = "Proyecto4/dispositivo/capturas/events.jsonl"

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                continue
            
            # Preprocesar
            t0 = time.time()
            if has_preprocess:
                input_tensor = preprocess_image(frame)
            else:
                input_tensor = preprocess_fallback(frame)
            
            # Inferencia
            outputs = session.run(None, {input_name: input_tensor})
            t_inferencia_ms = (time.time() - t0) * 1000
            
            # Interpretar resultados con Softmax (para que esté entre 0 y 1)
            predicciones = outputs[0][0]
            exp_preds = np.exp(predicciones - np.max(predicciones))
            probabilidades = exp_preds / exp_preds.sum()
            clase_idx = int(np.argmax(probabilidades))
            confianza = float(probabilidades[clase_idx])
            clase_predicha = CLASES[clase_idx]
            
            # Generar metadatos y hashes
            capture_id = str(uuid.uuid4())
            timestamp_ahora = datetime.datetime.now(datetime.timezone.utc).isoformat()
            nombre_img = f"edge01-{capture_id[:8]}.jpg"
            ruta_img = os.path.join("Proyecto4/dispositivo/capturas", nombre_img)
            
            cv2.imwrite(ruta_img, frame)
            with open(ruta_img, "rb") as f:
                image_sha256 = hashlib.sha256(f.read()).hexdigest()
            
            # Estructurar evento EXACTO como lo pide el servidor (FastAPI)
            evento = {
                "schema_version": 1,
                "capture_id": capture_id,
                "captured_at": timestamp_ahora,
                "device_id": "edge01",
                "model_version": args.version,
                "model_sha256": hash_modelo,
                "image_sha256": image_sha256,
                "image_ref": nombre_img,
                "predicted_class": clase_predicha,
                "confidence": round(confianza, 4)
            }
            
            # Persistir localmente en JSONL
            with open(ruta_jsonl, "a") as f:
                f.write(json.dumps(evento) + "\n")
            
            print(f"{nombre_img} {clase_predicha} confianza={confianza:.4f} tiempo={t_inferencia_ms:.1f}ms")
            
            # Enviar si hay internet / token
            enviar_aws_con_reintentos(API_URL, TOKEN, evento, ruta_img)
            
            # Pausa entre fotos
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nCaptura detenida de forma segura por el usuario.")
    finally:
        cap.release()

if __name__ == "__main__":
    main()
    