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
from PIL import Image

# ==========================================
# CONFIGURACIÓN DEL DISPOSITIVO Y AWS
# ==========================================
# Permite sobreescribir la URL mediante argumento o variable de entorno para F6
API_URL = os.environ.get("P4_API_URL", "https://174-129-84-80.sslip.io/api/p4/captures")
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

def enviar_aws(url, token, evento, ruta_imagen):
    """
    Intenta enviar a AWS una sola vez. 
    Devuelve True si tuvo éxito o fue rechazado permanentemente (400s).
    Devuelve False si es un error de red o de servidor (500s) para reintentarlo luego.
    """
    if not token:
        print("Advertencia: No hay TOKEN configurado, se omite el envío a AWS.")
        return True # Se asume manejado para no encolar infinitamente

    headers = {
        "Authorization": f"Bearer {token}"
    }
    
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
            return True
        elif response.status_code in [500, 502, 503, 504]:
            print(f"Error {response.status_code} en servidor. Se guardará para reintento.")
            return False
        else:
            print(f"Rechazado por el servidor {response.status_code}: {response.text}")
            return True # Rechazo firme, no se reintenta
            
    except requests.exceptions.RequestException as e:
        print(f"Fallo de conexión ({e}). Se guardará para reintento offline.")
        return False

def reintentar_pendientes(cola_pendientes, url):
    """Intenta enviar los eventos que se quedaron encolados por falta de red."""
    if not cola_pendientes:
        return []
    
    pendientes_restantes = []
    print(f"\n--- Intentando reenviar {len(cola_pendientes)} capturas pendientes ---")
    for evento, ruta_img in cola_pendientes:
        exito = enviar_aws(url, TOKEN, evento, ruta_img)
        if not exito:
            pendientes_restantes.append((evento, ruta_img))
            print(f"Fallo el reintento de {evento['capture_id']}, sigue en cola.")
    
    return pendientes_restantes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Ruta al modelo .onnx")
    parser.add_argument("--version", required=True, help="Versión del modelo")
    parser.add_argument("--url", default=API_URL, help="URL del servidor (sobreescribe P4_API_URL)")
    args = parser.parse_args()

    # 1. Validación de seguridad
    print("Verificando integridad del modelo...")
    hash_modelo = verificar_hash(args.model)
    print(f"modelo={args.version} sha256={hash_modelo} runtime=onnxruntime-{ort.__version__}")
    print(f"clases={','.join(CLASES)} cámara=/dev/video0; Ctrl+C para salir")
    
    # 2. Cargar módulo de preprocesamiento EXACTO (Eliminando fallback)
    # Agrega Proyecto4/modelo a la ruta del sistema
    sys.path.append(os.path.abspath("Proyecto4/modelo"))
    try:
        from preprocess import preprocess
    except ImportError as e:
        print(f"ERROR FATAL: {e}. No se encontró 'preprocess.py' en Proyecto4/modelo/")
        print("El preprocesamiento original de ImageNet es obligatorio.")
        sys.exit(1)

    # 3. Configurar sesión de ONNX a 1 solo hilo
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
    
    cola_pendientes = [] # Lista para almacenar eventos que no se pudieron enviar

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                continue
            
            # Preprocesar usando el módulo original: (Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            t0 = time.time()
            input_tensor = preprocess(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            
            # Inferencia
            outputs = session.run(None, {input_name: input_tensor})
            t_inferencia_ms = (time.time() - t0) * 1000
            
            # Interpretar resultados con Softmax
            predicciones = outputs[0][0]
            exp_preds = np.exp(predicciones - np.max(predicciones))
            probabilidades = exp_preds / exp_preds.sum()
            clase_idx = int(np.argmax(probabilidades))
            
            # Sin redondear la confianza (Regla 9)
            confianza = float(probabilidades[clase_idx]) 
            clase_predicha = CLASES[clase_idx]
            
            # Generar metadatos y hashes
            capture_id = str(uuid.uuid4())
            timestamp_ahora = datetime.datetime.now(datetime.timezone.utc).isoformat()
            nombre_img = f"{capture_id}.jpg" # Mismo nombre que capture_id
            ruta_img = os.path.join("Proyecto4/dispositivo/capturas", nombre_img)
            
            cv2.imwrite(ruta_img, frame)
            with open(ruta_img, "rb") as f:
                image_sha256 = hashlib.sha256(f.read()).hexdigest()
            
            # Estructurar evento (Contrato AWS)
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
                "confidence": confianza 
            }
            
            # Persistir localmente en JSONL
            with open(ruta_jsonl, "a") as f:
                f.write(json.dumps(evento) + "\n")
            
            print(f"{nombre_img} {clase_predicha} confianza={confianza} tiempo={t_inferencia_ms:.1f}ms")
            
            # Intentar reintentar los viejos primero
            cola_pendientes = reintentar_pendientes(cola_pendientes, args.url)
            
            # Enviar el nuevo
            exito_envio = enviar_aws(args.url, TOKEN, evento, ruta_img)
            if not exito_envio:
                cola_pendientes.append((evento, ruta_img))
            
            # Pausa entre fotos
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nCaptura detenida de forma segura por el usuario.")
    finally:
        cap.release()

if __name__ == "__main__":
    main()
    