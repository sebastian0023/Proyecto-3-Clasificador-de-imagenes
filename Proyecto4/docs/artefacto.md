# Ficha del artefacto optimizado — F2

Variante **`1.0.0-int8.1`**: el modelo publicado 1.0.0 del Proyecto 3, exportado a ONNX y cuantizado estáticamente a INT8. Es el artefacto que carga el dispositivo (F3) y el que se compara en calidad (F7) y recursos (F8).

## Origen (Proyecto 3)

| Dato | Valor |
|---|---|
| Versión publicada | `1.0.0` (activa en `registry.json` del P3) |
| Run ID de MLflow | `9f9b62c202f0446a8a4b411a10321eff` (r10, mejor época 6, `selection.json`) |
| Pesos | `s3://dataset-quality-releases-750702272375/models/clasificador/1.0.0/model.pt`, VersionId `VtRww5se97lomVTcKJUv6d9mYSL7TXOf`; copia local en `Proyecto3/mlflow_snapshot/artifacts/3/9f9b62c2…/checkpoint/model.pt` (`dvc pull mlflow_snapshot.dvc`) |
| SHA-256 | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172` (44 783 563 bytes); el mismo en S3, en local y en `selection.json` |
| Arquitectura | ResNet-18, cabeza `Dropout(0.5) → Linear(512, 3)` (`hidden_layers: []`, leído del checkpoint) |
| Clases (orden de salida) | 0 `cat`, 1 `dog`, 2 `person` |
| Preprocesamiento | RGB, estirado a 224×224 sin recortar bordes (bilineal con antialias), escala a [0, 1], media `[0.485, 0.456, 0.406]`, desviación `[0.229, 0.224, 0.225]` |
| Entrada conocida | `0.1.3:a1330` (val, `dog`): cat 0.051366, **dog 0.943828**, person 0.004807, igual que `Proyecto3/docs/publicacion_s3.md` |

`convert.py` carga el checkpoint con el `load_checkpoint` del propio P3 y exige su SHA-256 antes de convertir: arquitectura, clases y preprocesamiento salen del checkpoint, no se redefinen.

## Variante

| Dato | Valor |
|---|---|
| Versión | `1.0.0-int8.1` |
| Formato | ONNX, opset 18 |
| Runtime | onnxruntime, `CPUExecutionProvider`: 1.31.0 en la Raspberry Pi (Debian 13, Python 3.13.5, [`entorno.txt`](../evidencia_f3/entorno.txt)); la conversión y la prueba emulada usaron 1.30.0 y dan las mismas salidas |
| Técnica | Cuantización estática post-entrenamiento: formato QDQ, pesos INT8 **por canal**, activaciones INT8, calibración MinMax |
| Calibración | 200 recortes **solo de train** del manifiesto `m-0.1.3-s42-1` (semilla 42: 48 cat, 54 dog, 98 person); IDs en [`calibracion_manifest.jsonl`](../modelo/registros/calibracion_manifest.jsonl). Validación y test no intervienen |
| Entrada | `input`, float32, NCHW `[1, 3, 224, 224]`, RGB normalizado; la cuantización de la entrada ocurre dentro del grafo (`QuantizeLinear`), el dispositivo no cuantiza a mano |
| Salida | `logits` `[1, 3]`; confianza = softmax |
| Preprocesamiento en el edge | [`modelo/preprocess.py`](../modelo/preprocess.py) (numpy + Pillow, sin torch). En una revisión interna sobre las 292 muestras de validación, el original da el mismo accuracy (0.9966) con este preprocesamiento que con el de torchvision; la comparación formal por muestra es de F7 |

### Archivos

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `model.pt` (original P3) | 44 783 563 | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172` |
| `model_fp32.onnx` (exportación intermedia, referencia para F8) | 44 791 921 | `e4dc89bbb652f6de9bea2fffa94ff59abb0e6cb679d8a4d95aeadc9e0be65328` |
| **`model_int8.onnx` (variante)** | **11 349 151** | **`ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0`** |
| `model_package.json` | ver [`conversion_log.json`](../modelo/registros/conversion_log.json) | |

Descarga: `s3://dataset-quality-releases-750702272375/models/clasificador-edge/1.0.0-int8.1/`. Llaves, SHA-256 y VersionId de cada objeto en [`publicacion.json`](../modelo/registros/publicacion.json).

El bloque `source_model` de `publicacion.json` (llave, bytes, SHA-256 y VersionId `VtRww5se97lomVTcKJUv6d9mYSL7TXOf` del `model.pt` del P3) se agregó a mano en F10, a pedido de la revisión de Edith. El VersionId se verificó con `aws s3api head-object` en S3 el 2026-10-16 (UTC; 15 oct en hora local −06:00). `publish.py` no genera ese bloque: si se vuelve a correr, hay que reponerlo.

## Efecto de la técnica

- **Tamaño:** 44 783 563 → 11 349 151 bytes, **74.66 % menos** que el original (`size_reduction_pct` en el registro).
- **Artefacto:** los 20 `Conv` y el `Gemm` guardan sus pesos en 73 inicializadores `INT8` (con sesgos `INT32`); el grafo agrega 32 `QuantizeLinear` y 74 `DequantizeLinear` (`outputs.*.graph` en el registro).
- **Runtime:** en aarch64, onnxruntime funde los pares QDQ y ejecuta aritmética entera: el grafo optimizado queda con 20 `QLinearConv`, 1 `QGemm` y 8 `QLinearAdd`, y solo 2 `QuantizeLinear`/`DequantizeLinear` en los bordes. Lo imprime [`arm64_check.py`](../modelo/arm64_check.py) (salida en [`arm64_check.txt`](../modelo/registros/arm64_check.txt)).
- **Latencia:** no se reporta aquí. Se mide en la Raspberry Pi en F8, FP32 contra INT8 con el mismo runtime; la laptop no cuenta para la rúbrica (3.1).

## Validaciones de F2

| Comprobación | Resultado | Evidencia |
|---|---|---|
| SHA-256 del original igual al publicado | sí | `conversion_log.json` → `input.sha256` |
| ONNX FP32 igual a PyTorch | diferencia máxima de logits 1.2e-7 | `checks.fp32_vs_torch_max_abs_logit_diff` |
| Calibración solo con train | 200/200 de `train` | `calibration.splits_used`, `calibracion_manifest.jsonl` |
| Conversión reproducible | en la misma máquina, dos corridas dan el mismo SHA-256 de archivo. En otra máquina (clon limpio en otra ruta, 16 oct) el **modelo es el mismo**: misma huella sin metadatos de nodo (FP32 `5f965432…`, INT8 `9b590301…`), aunque el SHA-256 del archivo cambia por la ruta absoluta que el exportador guarda en cada nodo (ver [Reproducir](#reproducir)) | [`modelo/huella.py`](../modelo/huella.py) |
| Entradas conocidas (x86) | original, FP32 e INT8 dan la clase esperada en 3/3 | [`smoke_test.json`](../modelo/registros/smoke_test.json) |
| Carga en aarch64 (Docker con QEMU, Python 3.11, onnxruntime 1.30.0) | carga; SHA-256 coincide; 3/3 entradas conocidas con la clase esperada (`a1330` dog 0.930898); el runtime ejecuta 20 `QLinearConv`, 1 `QGemm` y 8 `QLinearAdd` | [`arm64_check.txt`](../modelo/registros/arm64_check.txt) |
| Carga en la Raspberry Pi física (Debian 13, Python 3.13.5, onnxruntime 1.31.0) | carga; SHA-256 coincide; 3/3 entradas conocidas con **las mismas probabilidades** que aarch64 emulado (`a1330` dog 0.930898); mismos operadores en el runtime | [`evidencia_f3/arm64_check_output.txt`](../evidencia_f3/arm64_check_output.txt) |

### Aviso para F7 y F8: medir INT8 en ARM, no en la laptop

El mismo `model_int8.onnx` da probabilidades distintas en x86 y en aarch64 (por ejemplo, `a1330`: dog 0.562 en la laptop, 0.931 en aarch64). La causa probable es la saturación conocida de onnxruntime al ejecutar INT8×INT8 con AVX2 en x86 (sin VNNI); en ARM las instrucciones enteras no saturan. La comparación formal de F7, con predicciones por muestra y el INT8 evaluado en aarch64, da una caída de 0.342 pp (0.99658 → 0.99315); en x86 la caída aparente sería de 1.37 pp ([`calidad.md`](calidad.md)). La comparación de calidad formal (F7) y las mediciones (F8) se hacen con el runtime de aarch64.

## Reproducir

Probado tal cual en un clon limpio, en Windows con PowerShell y Python 3.12, el 16 oct de 2026. Los comandos se corren desde la raíz del repositorio, salvo que se indique otra carpeta. `<perfil>` es un perfil de AWS con lectura sobre los buckets del proyecto. La prueba se hizo con el perfil de un integrante; el usuario de solo lectura del evaluador (`dataset-quality-evaluator`) tiene, según Terraform (`Proyecto2/terraform/modules/team_access/main.tf`), lectura sobre los mismos buckets, pero no se probó con sus credenciales.

### 1. Datos del Proyecto 3 que no están en Git

La conversión usa el checkpoint del P3, el manifiesto de validación y los recortes. Los dos primeros vienen de DVC; los recortes se regeneran desde el release aprobado.

```powershell
cd Proyecto2
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt
.\.venv\Scripts\python -m pip install --no-deps -e .
.\.venv\Scripts\dvc remote modify --local prod profile <perfil>
.\.venv\Scripts\dvc pull -r prod data/raw.dvc                     # release 0.1.3: 2047 archivos
cd ..\Proyecto3
..\Proyecto2\.venv\Scripts\dvc remote modify --local prod profile <perfil>
..\Proyecto2\.venv\Scripts\dvc pull data/manifests/m-0.1.3-s42-1.dvc mlflow_snapshot.dvc
cd ..\Proyecto2
$env:PYTHONPATH = "..\Proyecto3\src"
.\.venv\Scripts\python ..\Proyecto3\scripts\generate_crops.py --release 0.1.3 --profile <perfil>
cd ..
```

Comprobación: SHA-256 del manifiesto `45600f29…4305`, del checkpoint `e4acca42…9172` y de `Proyecto3/data/crops/0.1.3/crops.jsonl` `d3d61f35…be1bed` (`generate_crops.py` lo imprime al terminar). El `dvc remote modify --local` se guarda en `.dvc/config.local`, que Git ignora.

### 2. Conversión y prueba de humo

```powershell
cd Proyecto4
python -m venv .venv
.\.venv\Scripts\python -m pip install -r modelo/requirements-conversion.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python modelo/convert.py                  # o: modelo/convert.py --from-s3 --profile <perfil>
.\.venv\Scripts\python modelo/smoke_test.py               # 3/3 OK
.\.venv\Scripts\python modelo/huella.py artifacts/1.0.0-int8.1/model_fp32.onnx artifacts/1.0.0-int8.1/model_int8.onnx
```

**Qué comparar.** La `huella` debe ser `5f96543286a354aa282337d3c320b8caca5ca99c66ebe48ea1f75e76c21be398` (FP32) y `9b590301e802ed652e267628ae9526bb8cff9cae851ec33708e86488de03338a` (INT8), las mismas del artefacto publicado (`huella.py` sobre el `model_int8.onnx` de S3 da `9b590301…`).

El SHA-256 del **archivo** solo coincide con el publicado (`e4dc89bb…` y `ca689c4e…`) si se convierte desde la misma ruta. El exportador de PyTorch guarda en cada nodo un `pkg.torch.onnx.stack_trace` con la ruta absoluta del código, y esos metadatos de depuración no cambian pesos, grafo ni resultados. En el clon limpio del 16 oct, el archivo dio `f9e57bc4…` (FP32) y `0c0f8724…` (INT8); dos corridas seguidas dieron los mismos bytes, y la huella fue igual a la publicada. El dispositivo, el receptor y F7 usan siempre el archivo publicado (`ca689c4e…`), no una reconversión.

`convert.py` y `smoke_test.py` reescriben `modelo/registros/conversion_log.json` y `smoke_test.json` con la fecha y los hashes de la corrida. Para volver a la evidencia versionada: `git checkout -- modelo/registros`.

Para publicar una versión nueva (no para reproducir): `.\.venv\Scripts\python modelo/publish.py --profile <perfil>`. Configuración en [`modelo/conversion.yaml`](../modelo/conversion.yaml); cualquier cambio sube `variant.version`.

### 3. Carga en ARM64 sin la Pi

Con Docker y emulación QEMU (CPU Cortex-A53, Debian 13 y Python 3.13, como la Pi), desde la raíz del repo y con el `model_int8.onnx` publicado, descargado como indica el paso 2 del [README](../README.md#2-recuperar-el-modelo-desde-s3-y-verificar-su-sha-256):

```bash
docker run --rm --platform linux/arm64 -e QEMU_CPU=cortex-a53 -v "$PWD/Proyecto4:/p4:ro" -v "$PWD/Proyecto3/data/crops/0.1.3:/crops:ro" python:3.13-slim-trixie sh -c "pip install -q -r /p4/modelo/requirements-edge.txt && python /p4/modelo/arm64_check.py --model /p4/modelo/model_int8.onnx --crops /crops"
```

En la Raspberry Pi (Raspberry Pi OS de **64 bits**; onnxruntime no tiene wheels para armv7):

```bash
pip install -r Proyecto4/modelo/requirements-edge.txt
python Proyecto4/modelo/arm64_check.py --model Proyecto4/modelo/model_int8.onnx --crops <recortes>
```
