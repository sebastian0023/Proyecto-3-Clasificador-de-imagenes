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
| Laptop (portal y verificaciones) | Python 3.12, Docker Desktop (Compose v2), AWS CLI v2 con un perfil del equipo con lectura del bucket (para bajar el modelo y verificar). Las llaves nunca van al repositorio |

Clonar el repositorio en las dos máquinas:

```bash
git clone https://github.com/sebastian0023/Proyecto-3-Clasificador-de-imagenes.git
cd Proyecto-3-Clasificador-de-imagenes
```

## 2. Recuperar el modelo desde S3 y verificar su SHA-256

Los pesos no están en Git (decisión 8). Se bajan de S3 en la laptop, con un perfil del equipo, y se copian a la Pi: **la Pi no tiene credenciales de AWS**.

| Archivo | Llave en `s3://dataset-quality-releases-750702272375/` | Bytes | SHA-256 |
|---|---|---:|---|
| Variante INT8 (la de la Pi) | `models/clasificador-edge/1.0.0-int8.1/model_int8.onnx` | 11 349 151 | `ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0` |
| ONNX FP32 (referencia de F8) | `models/clasificador-edge/1.0.0-int8.1/model_fp32.onnx` | 44 791 921 | `e4dc89bbb652f6de9bea2fffa94ff59abb0e6cb679d8a4d95aeadc9e0be65328` |
| Original del P3 | `models/clasificador/1.0.0/model.pt` | 44 783 563 | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172` |

VersionId de cada objeto: [`modelo/registros/publicacion.json`](modelo/registros/publicacion.json).

En la laptop (PowerShell, desde la raíz del repositorio):

```powershell
aws s3 cp s3://dataset-quality-releases-750702272375/models/clasificador-edge/1.0.0-int8.1/model_int8.onnx Proyecto4/modelo/model_int8.onnx --profile <perfil>
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
- Al arrancar imprime `modelo=1.0.0-int8.1 sha256=ca689c4e… runtime=onnxruntime-1.31.0`.
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

`up.py` crea `Proyecto2/.env` desde [`Proyecto2/.env.example`](../Proyecto2/.env.example) si no existe. Para que el receptor local guarde en S3, edita en `.env`: `P4_AWS_PROFILE=<perfil>` y un `P4_DEVICE_TOKEN` de desarrollo (por ejemplo `python -c "import secrets; print(secrets.token_urlsafe(32))"`). Para no mezclar pruebas con las capturas reales, usa otro prefijo: `P4_CAPTURES_PREFIX=edge-captures-dev/`. Portal local: `http://localhost:8000/#/edge-captures`. Apagar: `python scripts/down.py`.

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
| Identidad del dispositivo | Fija en el código: `device_id: "edge01"` en [`dispositivo/edge_camera.py`](dispositivo/edge_camera.py) | `edge01` (no configurable por entorno; código congelado) |
| Acceso de evaluación al portal | `basic_auth` de Caddy: usuario y hash en `/opt/p4/secretos/caddy.env` de la EC2 | usuario `evaluador`; plantilla y proceso en [`deploy/preparar_secretos.sh`](deploy/preparar_secretos.sh) |

El programa del dispositivo además exige el SHA-256 de `1.0.0-int8.1` al arrancar (fijo en el código): otro artefacto requiere cambiar ese valor.

## 5. Verificar

Lista con comandos, resultado esperado y resultado obtenido: [`docs/comprobaciones.md`](docs/comprobaciones.md). Los más rápidos, desde `Proyecto4/` en la laptop:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install fastapi==0.141.1 pydantic==2.13.5 pydantic-settings==2.15.0 boto3==1.43.75 pillow==12.3.0 python-multipart==0.0.32 httpx==0.28.1 pytest==9.1.1
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python scripts\trazar_captura.py --capture-id fbf85a5e-9be6-4e8b-a716-38f4ee8873e8 --perfil <perfil>
```

`trazar_captura.py` solo lee S3 y, si cargas `P4_PORTAL_USUARIO` y `P4_PORTAL_PASSWORD` (con `Read-Host -AsSecureString`), también el portal.
