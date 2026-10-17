# Proyecto 4 — Modelo en edge

El clasificador del Proyecto 3 (`cat`, `dog`, `person`), optimizado a INT8 y ejecutado en una Raspberry Pi 3B con cámara. La Pi clasifica **sin red**, guarda cada foto y su evento, y los envía a AWS S3; el portal de los Proyectos 1 a 3 los muestra en la sección **Capturas Edge**.

| Para… | Ver |
|---|---|
| Resumen de la entrega (equipo, hardware, versiones, resultados, URL) | [`docs/ficha-entrega.md`](docs/ficha-entrega.md) |
| Índice de evidencias | [`evidencias/INDICE.md`](evidencias/INDICE.md) |
| Comprobaciones repetibles con resultados | [`docs/comprobaciones.md`](docs/comprobaciones.md) |
| Contrato del evento | [`docs/contratos.md`](docs/contratos.md) |

```
Proyecto4/
├── modelo/       conversión a INT8, preprocesamiento compartido, registros de F2
├── dispositivo/  programa de la Pi (edge_camera.py)
├── calidad/      comparación de calidad (F7) y sus registros
├── recursos/     medición de recursos en la Pi (F8) y sus registros
├── src/p4/       receptor de capturas del portal (/api/p4/captures)
├── scripts/      enviar, inferir y trazar capturas (herramientas del portal)
├── deploy/       despliegue del portal en AWS (Caddy y scripts de la EC2)
├── docs/         decisiones, contratos, guías y fases
├── evidencia_f3/, evidencia_f9/, evidencias/   evidencias
└── tests/        pruebas del receptor y de la traza (pytest)
```

## 1. Requisitos

| Dónde | Qué |
|---|---|
| Raspberry Pi | Raspberry Pi OS / Debian 13 de **64 bits** (`aarch64`; onnxruntime no tiene wheels para armv7), Python 3.13, cámara web USB en `/dev/video0`, red para enviar a AWS |
| Laptop (portal y verificaciones) | Python 3.12, Docker Desktop (Compose v2). Solo el equipo: AWS CLI v2 con un perfil del equipo con lectura del bucket (para bajar el modelo y las lecturas de S3). El evaluador no necesita AWS: usa el portal y un enlace temporal del modelo (pasos 2 y 5). Las llaves nunca van al repositorio |

En la laptop con Windows, antes de clonar, activa las rutas largas en Git para que el clon no falle con archivos cuya ruta completa supera el límite de 260 caracteres de Windows:

```bash
git config --global core.longpaths true
```

Clonar el repositorio en las dos máquinas:

```bash
git clone https://github.com/sebastian0023/Proyecto-3-Clasificador-de-imagenes.git
cd Proyecto-3-Clasificador-de-imagenes
```

## 2. Recuperar el modelo desde S3 y verificar su SHA-256

Los pesos no están en Git (decisión 8). **La Pi no tiene credenciales de AWS** y el evaluador tampoco recibe llaves de AWS (decisión del equipo del 16 oct; decisiones 5 y 6).

**Evaluador.** El equipo le entrega por canal privado, igual que la contraseña de `basic_auth`, un **enlace de descarga temporal** de `model_int8.onnx`. El enlace vence en 7 días como máximo; si venció, se pide otro. Después de descargarlo, el evaluador verifica el archivo con su SHA-256, que debe ser exactamente `ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0`:

```powershell
# Windows (PowerShell)
(Get-FileHash .\model_int8.onnx -Algorithm SHA256).Hash.ToLower()
```

```bash
# Linux
echo "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0  model_int8.onnx" | sha256sum -c
```

Tamaño, SHA-256 y VersionId de los 3 objetos, comprobados contra S3: [`evidencias/comprobaciones/hashes_modelos_s3.txt`](evidencias/comprobaciones/hashes_modelos_s3.txt).

**Equipo** (opción con un perfil del equipo con lectura del bucket). Se baja de S3 en la laptop y se copia a la Pi:

| Archivo | Llave en `s3://dataset-quality-releases-750702272375/` | Bytes | SHA-256 |
|---|---|---:|---|
| Variante INT8 (la de la Pi) | `models/clasificador-edge/1.0.0-int8.1/model_int8.onnx` | 11 349 151 | `ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0` |
| ONNX FP32 (referencia de F8) | `models/clasificador-edge/1.0.0-int8.1/model_fp32.onnx` | 44 791 921 | `e4dc89bbb652f6de9bea2fffa94ff59abb0e6cb679d8a4d95aeadc9e0be65328` |
| Original del P3 | `models/clasificador/1.0.0/model.pt` | 44 783 563 | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172` |

VersionId de cada objeto: [`modelo/registros/publicacion.json`](modelo/registros/publicacion.json).

En la laptop (PowerShell, desde la raíz del repositorio):

```powershell
aws s3 cp s3://dataset-quality-releases-750702272375/models/clasificador-edge/1.0.0-int8.1/model_int8.onnx Proyecto4/modelo/model_int8.onnx --profile <perfil>
aws s3api head-object --bucket dataset-quality-releases-750702272375 --key models/clasificador-edge/1.0.0-int8.1/model_int8.onnx --profile <perfil> --query "{VersionId:VersionId,Bytes:ContentLength}"
(Get-FileHash Proyecto4/modelo/model_int8.onnx -Algorithm SHA256).Hash.ToLower()
scp Proyecto4/modelo/model_int8.onnx <usuario>@<ip-de-la-pi>:~/Proyecto-3-Clasificador-de-imagenes/Proyecto4/modelo/
```

En la Pi, comprobar el archivo copiado (debe decir `OK`):

```bash
echo "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0  Proyecto4/modelo/model_int8.onnx" | sha256sum -c
```

El programa del dispositivo vuelve a verificar este SHA-256 al arrancar y se detiene si no coincide. Cómo se generó la variante (conversión reproducible): [`docs/artefacto.md`](docs/artefacto.md).

## 3. Dispositivo (Raspberry Pi)

### Instalación (una vez)

Desde la raíz del repositorio en la Pi:

```bash
python3 -m venv env
source env/bin/activate
pip install -r Proyecto4/modelo/requirements-edge.txt opencv-python-headless==4.13.0.92 requests==2.33.1
python -c "import onnxruntime, numpy; print(onnxruntime.__version__, numpy.__version__)"   # 1.31.0 2.5.4
```

`requirements-edge.txt` fija `onnxruntime==1.31.0`, `numpy>=2.2,<2.6` y `pillow>=11,<13`; OpenCV y requests son los del programa de la cámara. Versiones exactas de la Pi de la entrega: [`docs/ficha-entrega.md`](docs/ficha-entrega.md).

### Arranque

Siempre **desde la raíz del repositorio** (el programa usa rutas relativas a ella):

```bash
source env/bin/activate
read -rs -p "Token del dispositivo: " P4_DEVICE_TOKEN && export P4_DEVICE_TOKEN && echo
export P4_API_URL=https://174-129-84-80.sslip.io/api/p4/captures
python Proyecto4/dispositivo/edge_camera.py --model Proyecto4/modelo/model_int8.onnx --version 1.0.0-int8.1
```

- El token lo entrega Emilio por canal privado; se escribe sin eco y vive solo en esa sesión.
- Al arrancar imprime `modelo=1.0.0-int8.1 sha256=ca689c4e… runtime=onnxruntime-1.31.0` y `dispositivo=<device_id>`. Para usar otra identidad: `export P4_DEVICE_ID=<id>` o `--device-id <id>` (por defecto `edge01`).
- Toma una foto cada ~5 s; por cada una imprime `<capture_id>.jpg <clase> confianza=<valor> tiempo=<ms>` y, si el envío funciona, `¡Envío exitoso (201) a AWS!`.
- Guarda la foto y el evento **antes** de enviar: `Proyecto4/dispositivo/capturas/<capture_id>.jpg` y `capturas/events.jsonl`. Si el envío falla (sin red, error 5xx o sin token), la captura queda en `capturas/pendientes.json` y se reenvía con el **mismo `capture_id`** en los ciclos siguientes, también después de reiniciar.
- Sin red sigue capturando y clasificando. `Ctrl+C` lo detiene.

Demostración del fallo y reintento: [`docs/demo-f6.md`](docs/demo-f6.md).

## 4. Portal

### Desplegado en AWS (el de la evaluación)

- URL: **https://174-129-84-80.sslip.io** → menú lateral → **Capturas Edge** (entre Inference y Settings).
- Acceso: usuario `evaluador` con `basic_auth`; la contraseña se entrega por canal privado.
- Cómo se desplegó, se apaga y se reanuda: [`docs/despliegue.md`](docs/despliegue.md).

### En local (desarrollo)

Desde `Proyecto2/` (requiere Docker Desktop corriendo):

```bash
cd Proyecto2
python scripts/up.py
```

`up.py` crea `Proyecto2/.env` desde [`Proyecto2/.env.example`](../Proyecto2/.env.example) si no existe. Para que el receptor local guarde en S3, edita en `.env`: `P4_AWS_PROFILE=<perfil>` y un `P4_DEVICE_TOKEN` de desarrollo (por ejemplo `python -c "import secrets; print(secrets.token_urlsafe(32))"`). Para no mezclar pruebas con las capturas reales, usa otro prefijo: `P4_CAPTURES_PREFIX=edge-captures-dev/`. Después de editar `.env`, **vuelve a correr `python scripts/up.py`** para que el contenedor tome los cambios. Si no, sigue con el `.env` anterior y el portal responde `503` con `NoCredentialsError`. Portal local: `http://localhost:8000/#/edge-captures`. Apagar: `python scripts/down.py`.

### Consultar capturas anteriores

La galería muestra las **100 capturas más recientes** («Mostrando 100 de N»). Para cualquier otra:

| Cómo | Comando |
|---|---|
| Un registro por ID (portal desplegado, con `basic_auth`) | `curl.exe -u evaluador https://174-129-84-80.sslip.io/api/p4/captures/<capture_id>` (y `/image` para la foto) |
| Exportación completa | `https://174-129-84-80.sslip.io/api/p4/captures/export?format=csv` (o `json`) |
| Traza dispositivo / S3 / portal | `python scripts/trazar_captura.py --capture-id <id>` desde `Proyecto4/` (ver [`docs/comprobaciones.md`](docs/comprobaciones.md)) |
| Solo S3 (lectura) | [`docs/consulta-aws.md`](docs/consulta-aws.md) |

## Configuración

Dónde se cambia cada cosa (rúbrica 6.3). No hay archivos con valores reales en el repositorio: solo plantillas.

| Qué | Dónde | Valor actual / plantilla |
|---|---|---|
| Destino AWS del dispositivo (URL del receptor) | `P4_API_URL` o `--url` de `edge_camera.py` | `https://174-129-84-80.sslip.io/api/p4/captures` (valor por defecto en el código) |
| Token del dispositivo | `P4_DEVICE_TOKEN` en el entorno de la Pi y en el `.env` del portal | sin valor en el repositorio; plantilla vacía en [`Proyecto2/.env.example`](../Proyecto2/.env.example) |
| Bucket y prefijo de las capturas (portal) | `P4_CAPTURES_BUCKET`, `P4_CAPTURES_PREFIX`, `P4_AWS_REGION` en `Proyecto2/.env` | `dataset-quality-releases-750702272375`, `edge-captures/`, `us-east-1` ([`Proyecto2/.env.example`](../Proyecto2/.env.example)) |
| Credenciales de AWS del portal | `P4_AWS_PROFILE` (solo desarrollo); en producción, vacío = rol de instancia | [`docs/decisiones.md`](docs/decisiones.md) §5, [`docs/despliegue.md`](docs/despliegue.md) |
| Artefacto que carga el dispositivo | `--model` y `--version` de `edge_camera.py` | `Proyecto4/modelo/model_int8.onnx`, `1.0.0-int8.1` |
| Versiones aceptadas por el receptor | `P4_ACCEPTED_MODELS` (`version=sha256`) en `Proyecto2/.env` | `1.0.0-int8.1=ca689c4e…69c0` |
| Identidad del dispositivo | `P4_DEVICE_ID` o `--device-id` de [`edge_camera.py`](dispositivo/edge_camera.py) (`--device-id` tiene prioridad) | `edge01` por defecto. Se valida al arrancar: 1 a 64 caracteres, solo letras, números, `.`, `_` y `-`; si no cumple, el programa se detiene con `ERROR FATAL: device_id inválido`. Probado en la Pi con `edge01-demo` (captura `2fc25b54…`, `device_id` `edge01-demo` en S3) y con `'mi pi'` rechazado: [`evidencia_f3/device_id_configurable.txt`](evidencia_f3/device_id_configurable.txt) |
| Acceso de evaluación al portal | `basic_auth` de Caddy: usuario y hash en `/opt/p4/secretos/caddy.env` de la EC2 | usuario `evaluador`; plantilla y proceso en [`deploy/preparar_secretos.sh`](deploy/preparar_secretos.sh) |

**Decisión de seguridad:** el programa del dispositivo exige al arrancar el SHA-256 de `1.0.0-int8.1` (fijo en el código) y se detiene si el archivo no coincide, para que no se cargue otro modelo por error. El artefacto se elige con `--model` y `--version`; publicar otra variante implica actualizar ese SHA-256 junto con `P4_ACCEPTED_MODELS` del receptor.

## 5. Verificar

Lista con comandos, resultado esperado y resultado obtenido: [`docs/comprobaciones.md`](docs/comprobaciones.md). Los más rápidos, desde `Proyecto4/` en la laptop:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install fastapi==0.141.1 pydantic==2.13.5 pydantic-settings==2.15.0 boto3==1.43.75 pillow==12.3.0 python-multipart==0.0.32 httpx==0.28.1 pytest==9.1.1 numpy==2.5.3
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python evidencias\comprobaciones\recalcular.py
```

`numpy==2.5.3` lo necesita `recalcular.py` (recálculo de accuracy, F1 y p50/p95) y es la versión del entorno de la laptop ([`modelo/requirements-conversion.lock.txt`](modelo/requirements-conversion.lock.txt)). La Pi usa numpy 2.5.4 ([`docs/ficha-entrega.md`](docs/ficha-entrega.md)). `pyproject.toml` ya agrega `-q` a pytest. Ninguno de estos dos comandos necesita AWS.

**Evaluador: una captura, por el portal desplegado** (usuario `evaluador`; `curl.exe` pide la contraseña, entregada por canal privado). Ejemplo con `fbf85a5e-9be6-4e8b-a716-38f4ee8873e8`, una de las 20:

```powershell
curl.exe -u evaluador https://174-129-84-80.sslip.io/api/p4/captures/fbf85a5e-9be6-4e8b-a716-38f4ee8873e8
curl.exe -u evaluador -o fbf85a5e.jpg https://174-129-84-80.sslip.io/api/p4/captures/fbf85a5e-9be6-4e8b-a716-38f4ee8873e8/image
(Get-FileHash .\fbf85a5e.jpg -Algorithm SHA256).Hash.ToLower()
curl.exe -u evaluador -o export.csv "https://174-129-84-80.sslip.io/api/p4/captures/export?format=csv"
```

`GET /api/p4/captures/<id>` devuelve el registro guardado en S3 (JSON con clase, confianza, fechas, dispositivo, versión y `image_sha256`). `/image` devuelve la foto, y su SHA-256 debe ser igual al `image_sha256` del registro. `/export?format=csv` (o `json`) baja todos los eventos; también lo enlazan **CSV** y **JSON** en la galería. Se compara con la evidencia registrada: [`evidencias/capturas_20/capturas_20.csv`](evidencias/capturas_20/capturas_20.csv), [`evidencias/comprobaciones/traza_fbf85a5e_s3.txt`](evidencias/comprobaciones/traza_fbf85a5e_s3.txt) y la exportación del 15 oct en [`evidencias/exportacion/`](evidencias/exportacion/).

**Equipo: la traza con S3** (necesita un perfil de AWS del equipo; `--perfil` vale `p4-emilio` por defecto). La corre el equipo, también en vivo durante la demostración ([`docs/consulta-aws.md`](docs/consulta-aws.md)):

```powershell
.\.venv\Scripts\python scripts\trazar_captura.py --capture-id fbf85a5e-9be6-4e8b-a716-38f4ee8873e8 --perfil <perfil>
```

Su salida registrada: [`evidencias/comprobaciones/traza_fbf85a5e_s3.txt`](evidencias/comprobaciones/traza_fbf85a5e_s3.txt) (solo S3) y [`traza_fbf85a5e_portal.txt`](evidencias/comprobaciones/traza_fbf85a5e_portal.txt) (S3 y portal). `trazar_captura.py` solo lee S3 y, si cargas `P4_PORTAL_USUARIO` y `P4_PORTAL_PASSWORD` (con `Read-Host -AsSecureString`), también el portal.
