# Decisiones técnicas — Proyecto 4

Se cierran en el kickoff de F1 (miércoles 7 de octubre). Cada líder escribe las suyas; el PR lo abre Edith y lo revisa Bryan. No incluyas contraseñas, claves ni tokens.

Estado: **cerrada** / **pendiente de dato**. Mientras una decisión esté pendiente, la fase que depende de ella no marca sus casillas.

| # | Decisión | Responsable | Fecha | Estado | Desbloquea |
|---|---|---|---|---|---|
| 1 | Formato y runtime del modelo en el dispositivo | Edith y Bryan | 8 oct | cerrada | F2, F3 |
| 2 | Técnica y objetivo de optimización | Edith | 8 oct | cerrada | F2, F7, F8 |
| 3 | Datos de comparación de calidad | Edith | 13 oct | cerrada | F7 |
| 4 | Modo de captura | Bryan | | pendiente | F3, F9 |
| 5 | Servicios de AWS | Emilio | 8 oct | cerrada | F4, F5 |
| 6 | Ubicación de Capturas Edge en el portal | Emilio | 8 oct (URL y acceso: 9 oct) | cerrada | F5 |
| 7 | Hardware y entorno del dispositivo | Bryan | | pendiente | F3, F8 |
| 8 | Qué cabe en Git y qué se distribuye por enlace | Edith y Emilio | 8 oct (pesos) | cerrada para pesos y registros; carpeta de evidencias: pendiente de dato (Emilio, F10) | F2, F10 |

## 1. Formato y runtime

- **Formato del artefacto optimizado:** ONNX (`.onnx`), específicamente cuantizado a INT8.
- **Runtime en el dispositivo y versión:** `onnxruntime` versión 1.31.0 ejecutándose dentro de un entorno virtual (`env`) en Python (Nota: Edith probó previamente con la versión 1.30.0). Dependencias adicionales: `opencv-python-headless`, `requests` y `Pillow`.
- **Por qué es compatible con el hardware de la decisión 7:** El formato ONNX con cuantización a INT8 y ejecutado a través de `onnxruntime` reduce significativamente el consumo de RAM. Esto es vital para la Raspberry Pi 3B. Se ejecuta en un solo hilo para evitar picos en la CPU ARM.

## 2. Técnica y objetivo de optimización

- **Técnica:** cuantización estática post-entrenamiento con onnxruntime: formato QDQ, pesos INT8 **por canal**, activaciones INT8, calibración MinMax. Se aplica a los pesos del modelo 1.0.0 del P3, sin reentrenar ni cambiar la arquitectura. Configuración en [`modelo/conversion.yaml`](../modelo/conversion.yaml); ficha en [`artefacto.md`](artefacto.md).
- **Precisión resultante:** INT8 en pesos y activaciones de las 20 convoluciones, la capa lineal y las sumas residuales; entrada y salida del grafo en float32. En aarch64, onnxruntime ejecuta 20 `QLinearConv`, 1 `QGemm` y 8 `QLinearAdd` (misma salida en la Pi y en la emulación).
- **Objetivo medible y por qué importa en este hardware:**
  - **Tamaño:** reducir unas 4 veces el artefacto. Resultado: 44 783 563 → 11 349 151 bytes, **74.66 % menos**. Importa porque la Raspberry Pi 3B tiene 1 GB de RAM compartida con el SO y el programa de la cámara.
  - **Latencia y memoria en la Pi:** que el INT8 sea más rápido que el ONNX FP32 con el mismo runtime y en el mismo dispositivo. Con INT8 la Cortex-A53 procesa más valores por instrucción NEON y mueve 4 veces menos datos de pesos que en FP32. Lo mide Bryan en F8 (al menos 100 tiempos tras 10 de calentamiento); aquí no se fija un porcentaje.
  - **Calidad:** perder como máximo 2 pp de accuracy en la validación del P3. Resultado de F7: **0.342 pp** ([`calidad.md`](calidad.md)).
- **¿Requiere calibración?** Sí: 200 recortes **solo de `train`** del manifiesto `m-0.1.3-s42-1` (semilla 42), con sus IDs en [`calibracion_manifest.jsonl`](../modelo/registros/calibracion_manifest.jsonl). Validación y test no intervienen.

## 3. Datos de comparación de calidad

- **Conjunto:** la partición `val` del manifiesto del P3 con el que se seleccionó el modelo 1.0.0: 292 recortes (cat 67, dog 78, person 147), con las etiquetas del manifiesto. Ambos modelos se evalúan sobre esas mismas 292 muestras ([`calidad.md`](calidad.md)).
- **Manifiesto y hash de origen:** `m-0.1.3-s42-1`, `Proyecto3/data/manifests/m-0.1.3-s42-1/manifest.jsonl`, SHA-256 `45600f297d13f51685e051e0cbc4962beb1f7c6a4e03247cbf61a345e6fa4305` (igual a `manifest_hash` de su `.meta.json` y de `Proyecto3/docs/selection.json`); recortes del release `0.1.3`, índice `crops.jsonl` con SHA-256 `d3d61f35…be1bed`.
- **Dónde se evalúa cada modelo:** el original con PyTorch y su propio preprocesamiento; la variante INT8 en aarch64 con el entorno de la Pi (Debian 13, Python 3.13, onnxruntime 1.31.0, CPU Cortex-A53 emulada). El INT8 no se evalúa en x86: ahí da otras probabilidades ([`artefacto.md`](artefacto.md)).
- **El test no se usa:** ni para calibrar (la calibración de F2 usa 200 recortes de `train`, [`calibracion_manifest.jsonl`](../modelo/registros/calibracion_manifest.jsonl)) ni para elegir la configuración ni para esta comparación. Los scripts de F7 solo leen filas con `split == "val"`.

## 4. Modo de captura

- **Por botón o por intervalo:** Por intervalo (ciclo continuo cada 5 segundos). Si falla la red, el sistema encola la captura localmente en el JSONL y la imagen con nombre `{capture_id}.jpg`, siguiendo con las capturas de forma ininterrumpida y reintentando el envío posteriormente.
- **Un objeto por captura; ¿recorte fijo? (sí/no, y cuál):** Sí, un objeto principal por captura. No hay recorte fijo en la captura; el frame completo se pasa a `preprocess.py` (de la Fase 2), que aplica la transformación y normalización estricta de ImageNet al formato que espera el modelo.
- **Resolución de captura:** Resolución estándar de la cámara web (USB V4L2) manejada por el sistema operativo mediante OpenCV.

## 5. Servicios de AWS

**Decisión:** reutilizar el bucket S3 de releases del P2/P3 con un prefijo nuevo y recibir los eventos en el FastAPI del portal existente. Sin servicios nuevos de AWS (la rúbrica no los exige) y sin recursos con costo fijo.

- **Cuenta y región:** `750702272375`, `us-east-1` (las de `Proyecto3/docs/almacenamiento.md`).
- **Dónde se guarda la imagen y el registro:** `s3://dataset-quality-releases-750702272375/edge-captures/` (versionado, cifrado SSE, sin acceso público, por Terraform en `Proyecto2/terraform/modules/s3`):

  ```
  edge-captures/images/{capture_id}.jpg     fotografía, bytes tal cual llegaron
                                            metadatos S3: sha256, capture-id
  edge-captures/events/{capture_id}.json    registro: evento + campos del servidor
  ```

  El `capture_id` va en la llave porque la idempotencia es una escritura condicional sobre una llave exacta. Nunca se sobrescribe ni se borra; la regla del bucket que expira versiones no actuales a los 90 días no afecta a objetos que no se reemplazan.
- **Cómo recibe el dispositivo:** `POST /api/p4/captures` (multipart, token Bearer) en el FastAPI del portal (`Proyecto2/src/dataset_quality/main.py`), con un router de `Proyecto4/src/p4/` montado igual que los de P3. El contrato completo está en [`contratos.md`](contratos.md). El mismo router sirve el listado, la imagen y la exportación a Capturas Edge (F5).
- **Idempotencia:** `PutObject` con `If-None-Match: *`, primero la imagen y después el registro. Si la llave ya existe (HTTP 412 de S3), se compara lo guardado con lo recibido: igual → `200 duplicate` sin escribir; distinto → `409 conflicto_capture_id` con los campos que difieren. Nunca se sobrescribe ni se responde 2xx a un conflicto. Una falla a la mitad (imagen escrita, registro no) se completa con el reintento del mismo ID; un registro nunca apunta a una imagen inexistente.
- **Listado ordenado:** `ListObjectsV2` de `events/` y `GetObject` en paralelo, ordenado por `captured_at` en UTC (más reciente primero; desempate `received_at`, `capture_id`), con caché en memoria de unos 10 s. Con el volumen esperado (menos de 300 eventos) son centavos y menos de un segundo. Si creciera, se agrega un índice `edge-captures/by-date/{captured_at_utc}_{capture_id}` que S3 lista en orden lexicográfico (no implementado).
- **Credenciales del receptor (sin llaves en Git):**
  - Si `P4_AWS_PROFILE` tiene valor, boto3 usa ese perfil de `~/.aws`. **Solo para desarrollo local:** compose monta `~/.aws` en solo lectura, igual que en `p3-inference`.
  - Si `P4_AWS_PROFILE` está vacío, boto3 usa la cadena estándar de credenciales (variables de entorno, rol de instancia, rol de tarea). Es el modo del despliegue: **en producción, nada de llaves personales**, el permiso viene de un rol.
  - Permisos que necesita el receptor: `s3:PutObject` y `s3:GetObject` sobre `edge-captures/*`, y `s3:ListBucket` con prefijo `edge-captures/`. No necesita `DeleteObject`.
- **Identidad del dispositivo:** `device_id` en el evento y un token compartido (`P4_DEVICE_TOKEN`) en el header `Authorization`. El token vive en `Proyecto2/.env` y en una variable de entorno de la Pi, nunca en Git. El dispositivo **no** tiene credenciales de AWS: solo habla con el receptor.
- **Consulta de solo lectura para la demostración:** el equipo la ejecuta en vivo con `aws s3api head-object` y `get-object` sobre `edge-captures/events/{id}.json` e `edge-captures/images/{id}.jpg` (llave, `VersionId`, `LastModified`, `sha256` y contenido). Alternativa: el usuario `dataset-quality-evaluator`, que ya tiene solo lectura sobre el bucket. Nunca se entregan llaves. Los comandos exactos se documentan en F4 (bloque de consulta de solo lectura).

## 6. Ubicación de Capturas Edge

- **Entrada del menú y ruta:** entrada `Capturas Edge` (`id: 'edge-captures'`) en la lista `PAGES` de `Proyecto2/web/src/App.tsx`, después de `Inference` y antes de `Settings`; ruta `#/edge-captures`. Es el mismo portal de P2 y P3 (la app web de P2 con las páginas de P3).
- **Imágenes:** las sirve `GET /api/p4/captures/{id}/image`, que las lee de S3 del lado del servidor. El navegador no recibe URLs públicas ni credenciales.
- **Dónde está desplegado el portal (URL) y quién lo administra:** **`https://174-129-84-80.sslip.io`** (Capturas Edge en `#/edge-captures`; MLflow en `https://mlflow.174-129-84-80.sslip.io`). EC2 `i-0348c123c4c126267` (t3.medium, us-east-1) con IP elástica `174.129.84.80`, Docker Compose (`Proyecto2/docker-compose.prod.yml`) y Caddy con HTTPS de Let's Encrypt; rol de instancia `p4-portal-ec2`, sin llaves personales. Lo administra Emilio; los permisos los gestiona el PM (Sebastián). Guía: [`despliegue.md`](despliegue.md). P1 **no** se despliega (confirmado con el PM el 9 oct): solo el portal de P2 y P3 con Capturas Edge.
- **Acceso limitado para el evaluador:** usuario y contraseña de Caddy (`basic_auth`) en **todo** el portal (web, API, imágenes, exportación y MLflow), **excepto** `POST /api/p4/captures`, que usa el dispositivo y está protegido por su token (`P4_DEVICE_TOKEN`). Confirmado con el PM el 9 oct. El usuario es `evaluador`; la contraseña se entrega por un canal privado y solo su hash bcrypt vive en la EC2 (`/opt/p4/secretos/caddy.env`, 600, root). El evaluador no recibe llaves de AWS.

## 7. Hardware y entorno del dispositivo

- **Dispositivo y cámara (modelo):** Raspberry Pi 3 Model B Rev 1.2 (ARM Cortex-A53 de 4 núcleos a 1.2 GHz, ~905 MB de RAM útil / 1 GB físico, arquitectura `aarch64`) conectada a una cámara web estándar vía USB V4L2.
- **Sistema operativo y versión:** Debian GNU/Linux 13 (trixie) de 64 bits (`aarch64`), kernel `Linux 6.18.50+rpt-rpi-v8` (registrado en [`evidencia_f3/entorno.txt`](../evidencia_f3/entorno.txt)).
- **Runtime y versiones:** Python 3.13.5 (entorno virtual `env`) utilizando `onnxruntime==1.31.0`, `opencv-python-headless==4.13.0.92`, `pillow==12.2.0`, `numpy==2.2.4` y `requests==2.33.1`.
- **Prueba realizada el 8 de oct (cámara captura, el runtime carga el modelo original o una entrada conocida):** Sí. La cámara capturó las imágenes, calculó el hash SHA-256 que validó la identidad del modelo cuantizado (`ca689c4e…fbd69c0`), importando correctamente el preprocesamiento base (`modelo/preprocess.py`). Las inferencias mostraron la clase y la confianza sin redondeo ([`evidencia_f3/arm64_check_output.txt`](../evidencia_f3/arm64_check_output.txt)). La prueba de resiliencia (Wi-Fi apagado) demostró la captura y guardado offline sin interrupciones, con éxito en reintentos posteriores ([`evidencia_f3/ejecucion_offline.txt`](../evidencia_f3/ejecucion_offline.txt)).

## 8. Qué cabe en Git

- **Pesos del original y de la variante: por enlace con SHA-256, no en Git.** `Proyecto4/.gitignore` excluye `*.pt`, `*.onnx` y `artifacts/`. Cada archivo se identifica por su SHA-256 en [`artefacto.md`](artefacto.md) y [`publicacion.json`](../modelo/registros/publicacion.json):
  - Original: `s3://dataset-quality-releases-750702272375/models/clasificador/1.0.0/model.pt` (VersionId `VtRww5se97lomVTcKJUv6d9mYSL7TXOf`), SHA-256 `e4acca42…9172`; copia en MLflow del P3 (`dvc pull mlflow_snapshot.dvc`).
  - Variante y FP32 de referencia: `s3://dataset-quality-releases-750702272375/models/clasificador-edge/1.0.0-int8.1/`, versiones inmutables (`modelo/publish.py` no sobrescribe).
- **Dónde se alojan los artefactos grandes:** en el mismo bucket S3 del P2/P3 (versionado, sin acceso público). El evaluador los descarga con su usuario de solo lectura o los recibe por un enlace temporal; nunca con llaves del equipo.
- **Qué sí va en Git:** código de conversión y de evaluación, configuración, lockfiles y los registros pequeños que respaldan las cifras: registro de conversión, manifiesto de calibración, prueba de humo, predicciones por muestra y métricas (`modelo/registros/`, `calidad/registros/`, guardados byte por byte para que su SHA-256 no cambie).
- **Dónde queda la carpeta de evidencias (F10):** **pendiente de dato (Emilio, F10).** Hoy la evidencia de F3 está en `Proyecto4/evidencia_f3/`, y la de F4–F6 está fuera del repo, en la laptop de Emilio, a la espera de copiarse en F10 sin secretos.

## Referencia del modelo del Proyecto 3

Se llena en F1 (Edith). Sin esto no hay continuidad demostrable (M1, 1.1).

| Dato | Valor |
|---|---|
| Versión del modelo publicada | `1.0.0`, la versión activa en `registry.json` del P3 ([`Proyecto3/docs/publicacion_s3.md`](../../Proyecto3/docs/publicacion_s3.md)) |
| Run ID de MLflow | `9f9b62c202f0446a8a4b411a10321eff` (corrida r10, mejor época 6, `val_accuracy` 0.9965753424657534; [`Proyecto3/docs/selection.json`](../../Proyecto3/docs/selection.json)) |
| Ubicación de los pesos y SHA-256 | `s3://dataset-quality-releases-750702272375/models/clasificador/1.0.0/model.pt`, VersionId `VtRww5se97lomVTcKJUv6d9mYSL7TXOf`, 44 783 563 bytes, SHA-256 `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172`. El mismo hash en la copia de MLflow y en `selection.json` (verificado el 8 oct) |
| Arquitectura | ResNet-18 con cabeza `Dropout(0.5) → Linear(512, 3)` (`hidden_layers: []`, leído del checkpoint) |
| Clases y orden | 0 `cat`, 1 `dog`, 2 `person` |
| Preprocesamiento (tamaño, normalización, orden de canales) | RGB; se estira a 224×224 sin recortar bordes (bilineal con antialias); escala a [0, 1]; media `[0.485, 0.456, 0.406]` y desviación `[0.229, 0.224, 0.225]` de ImageNet; tensor NCHW |
| Entrada conocida con clase esperada | `0.1.3:a1330` (validación, `dog`): cat 0.051366, **dog 0.943828**, person 0.004807 con el original, igual que en `Proyecto3/docs/publicacion_s3.md`. Con la variante INT8 en la Pi: dog 0.930898 ([`evidencia_f3/arm64_check_output.txt`](../evidencia_f3/arm64_check_output.txt)) |
