# Comprobaciones repetibles (rúbrica 6.2)

Cada fila dice qué se comprueba, cómo repetirlo, qué se espera, qué se obtuvo, quién y cuándo, y dónde está el registro. Solo se anotan resultados observados: lo que corre en la Pi lo ejecutó Bryan y se cita su registro.

Comandos desde `Proyecto4/` en la laptop (PowerShell), salvo que diga otra cosa. Los que leen AWS usan un perfil del equipo con solo lectura sobre el bucket.

## 1. Carga y conversión del modelo

| # | Comprobación | Comando o paso | Esperado | Obtenido | Quién / cuándo | Registro |
|---|---|---|---|---|---|---|
| 1.1 | Los 3 artefactos en S3 son los del registro de conversión (tamaño, SHA-256 y VersionId) | Descargar y calcular SHA-256 de `model.pt`, `model_fp32.onnx` y `model_int8.onnx` ([`README.md`](../README.md#2-recuperar-el-modelo-desde-s3-y-verificar-su-sha-256)); `aws s3api head-object` para el VersionId | `e4acca42…9172`, `e4dc89bb…5328` y `ca689c4e…69c0`, con los bytes y VersionId de [`conversion_log.json`](../modelo/registros/conversion_log.json) y [`publicacion.json`](../modelo/registros/publicacion.json) | **Los 3 coinciden** (bytes, SHA-256 y VersionId) | Emilio, 2026-10-15T04:51Z | [`evidencias/comprobaciones/hashes_modelos_s3.txt`](../evidencias/comprobaciones/hashes_modelos_s3.txt) |
| 1.2 | La conversión es reproducible | `python modelo/convert.py` dos veces y [`modelo/huella.py`](../modelo/huella.py) sobre `model_fp32.onnx` y `model_int8.onnx` ([`artefacto.md`](artefacto.md#reproducir)) | **Misma máquina:** mismos SHA-256 de archivo de FP32 e INT8 en dos corridas. **Otra máquina** (clon limpio en otra ruta): misma huella sin metadatos de nodo que el artefacto publicado | **Misma máquina:** mismos SHA-256 en dos corridas (8 oct). **Clon limpio** (16 oct): huella FP32 `5f96543286a354aa282337d3c320b8caca5ca99c66ebe48ea1f75e76c21be398` e INT8 `9b590301e802ed652e267628ae9526bb8cff9cae851ec33708e86488de03338a`, **iguales** a las del artefacto publicado; el SHA-256 del archivo cambia por la ruta absoluta que el exportador guarda en cada nodo | Edith, F2 (8 oct) y clon limpio (16 oct) | [`artefacto.md`](artefacto.md) (validaciones de F2 y [Reproducir](artefacto.md#reproducir)), [`modelo/huella.py`](../modelo/huella.py), [`conversion_log.json`](../modelo/registros/conversion_log.json) |
| 1.3 | ONNX FP32 equivale al PyTorch original | Incluido en `convert.py` | Diferencia de logits ≈ 0 | 1.2e-7 | Edith, F2 | `conversion_log.json` → `checks.fp32_vs_torch_max_abs_logit_diff` |
| 1.4 | La Pi carga la variante, verifica su SHA-256 y ejecuta aritmética entera | En la Pi: `python modelo/arm64_check.py --model … --crops …` | `sha256=ca689c4e…69c0`; operadores `QLinearConv:20`, `QGemm:1`, `QLinearAdd:8` | Lo esperado (onnxruntime 1.31.0, numpy 2.5.4, Python 3.13.5) | **Ejecutado por Bryan** en la Pi física | [`evidencia_f3/arm64_check_output.txt`](../evidencia_f3/arm64_check_output.txt) |
| 1.5 | El programa del dispositivo se niega a cargar otro modelo | Arranque de `dispositivo/edge_camera.py` | Verifica `ca689c4e…69c0` antes de cargar; si no coincide, se detiene | Imprime `modelo=1.0.0-int8.1 sha256=ca689c4e…` al arrancar | **Ejecutado por Bryan** | [`evidencia_f3/ejecucion.txt`](../evidencia_f3/ejecucion.txt) |

## 2. Inferencia sobre entradas conocidas

| # | Comprobación | Comando o paso | Esperado | Obtenido | Quién / cuándo | Registro |
|---|---|---|---|---|---|---|
| 2.1 | La Pi clasifica 3 recortes de validación del P3 con la clase correcta | `arm64_check.py` en la Pi | `a1330` dog, `a1528` cat, `a1022` person | dog 0.930898, cat 0.999977, person 0.992791 | **Ejecutado por Bryan** | [`evidencia_f3/arm64_check_output.txt`](../evidencia_f3/arm64_check_output.txt) |
| 2.2 | La Pi y la evaluación de calidad (F7) dan lo mismo en esas entradas | Contraste de archivos: salida de la Pi contra las filas de [`pred_optimizado.csv`](../calidad/registros/pred_optimizado.csv) | Misma clase y mismas probabilidades | **Iguales** en las 3 (diferencia máxima < 5e-7) | Emilio, 2026-10-15 | [`evidencias/comprobaciones/entradas_conocidas.txt`](../evidencias/comprobaciones/entradas_conocidas.txt) |
| 2.3 | Original, FP32 e INT8 dan la clase esperada (prueba de humo en x86) | `python modelo/smoke_test.py` | 3/3 con la clase esperada en los tres modelos | 3/3 | Edith, F2 | [`modelo/registros/smoke_test.json`](../modelo/registros/smoke_test.json) |

En x86 el INT8 da otras probabilidades (no otra clase en estas 3 entradas); la comparación formal de calidad se hace en aarch64 ([`artefacto.md`](artefacto.md), [`calidad.md`](calidad.md)).

## 3. Evento enviado y recuperado

| # | Comprobación | Comando o paso | Esperado | Obtenido | Quién / cuándo | Registro |
|---|---|---|---|---|---|---|
| 3.1 | Una captura de las 20 está en S3 con su imagen | `python scripts/trazar_captura.py --capture-id fbf85a5e-9be6-4e8b-a716-38f4ee8873e8 --sin-portal` | 1 registro con ese ID; SHA-256 de la imagen igual en metadatos y descarga | 1 registro (VersionId `a4Pw2pfZ…`); imagen coincide | Emilio, 2026-10-15 | [`evidencias/comprobaciones/traza_fbf85a5e_s3.txt`](../evidencias/comprobaciones/traza_fbf85a5e_s3.txt) |
| 3.2 | La misma captura, también en el portal desplegado | Cargar `P4_PORTAL_USUARIO` y `P4_PORTAL_PASSWORD` con `Read-Host -AsSecureString` y repetir 3.1 sin `--sin-portal` | Registro e imagen del portal iguales a S3 | **TODO COINCIDE** (código de salida 0): 8 de 8 filas comparadas entre S3 y portal; HTTP 200 en registro e imagen; SHA-256 de la imagen igual en metadatos, descarga de S3 y descarga del portal | Emilio, 2026-10-15T05:09Z | [`evidencias/comprobaciones/traza_fbf85a5e_portal.txt`](../evidencias/comprobaciones/traza_fbf85a5e_portal.txt) |
| 3.3 | Las 20 capturas: foto de S3 con el `image_sha256` del evento | Descarga de S3 al generar [`evidencias/capturas_20/`](../evidencias/capturas_20/) | SHA-256 de la foto = `image_sha256` del registro = metadato `sha256` | **20/20** coinciden (columna `sha256_foto_verificado`); en las 6 `person` también coincide la foto entregada por Bryan | Emilio: 14 cat y dog el 2026-10-15T04:42Z, 6 person el 2026-10-15T22:18Z | [`capturas_20.csv`](../evidencias/capturas_20/capturas_20.csv) |
| 3.4 | Dispositivo, S3 y portal coinciden en una captura con fallo y reintento | `trazar_captura.py` con el `events.jsonl` y las fotos de la Pi | Mismos 7 campos e imagen igual en 5 fuentes; 1 registro por ID | 7/7 capturas del ensayo sin red, todo coincide | Emilio, 13 oct | [`fases/F6-recorrido-completo.md`](fases/F6-recorrido-completo.md) (tabla de los 7 IDs) |
| 3.5 | Un reintento con el mismo ID no duplica | Reenvío del mismo evento (`scripts/enviar_captura.py --reenviar`) | `200 duplicate`, VersionId del registro sin cambio | `200 duplicate`, VersionId sin cambio | Emilio, F4 (8 oct) | [`fases/F4-aws-recepcion.md`](fases/F4-aws-recepcion.md) (Registro de avance) |

## 4. Pruebas automatizadas

| # | Comprobación | Comando | Esperado | Obtenido | Quién / cuándo | Registro |
|---|---|---|---|---|---|---|
| 4.1 | Receptor, validación, persistencia, idempotencia, consulta y traza (Proyecto 4) | `.\.venv\Scripts\python -m pytest` (`pyproject.toml` ya agrega `-q`) | Todas pasan | **121 passed** (2 advertencias de deprecación de `starlette`/`anyio`, no son fallos) | Emilio, 2026-10-15T04:52Z; repetido el 2026-10-16T04:09Z con `main` y el PR #50 en la rama | [`evidencias/comprobaciones/pytest_proyecto4.txt`](../evidencias/comprobaciones/pytest_proyecto4.txt) |
| 4.2 | Portal de P2 y P3 con el router de P4 montado | Desde `Proyecto2/` con el stack arriba: `docker compose exec -T app pytest` | Todas pasan | **278 passed** (1 advertencia de deprecación de `starlette`/`anyio`) | Emilio, 2026-10-15T04:52Z; repetido el 2026-10-16T04:07Z con `main` y el PR #50 en la rama | [`evidencias/comprobaciones/pytest_proyecto2_contenedor.txt`](../evidencias/comprobaciones/pytest_proyecto2_contenedor.txt) |

## 5. Recálculo de las cifras declaradas

| # | Comprobación | Comando | Esperado | Obtenido | Quién / cuándo | Registro |
|---|---|---|---|---|---|---|
| 5.1 | Accuracy, F1 macro y caída en pp desde las predicciones por muestra (292, IDs únicos, 3 clases) | `python evidencias/comprobaciones/recalcular.py` | Lo declarado en [`metricas.json`](../calidad/registros/metricas.json) | **Coincide**: 0.9965753424657534 → 0.9931506849315068, caída 0.3424657534246589 pp; F1 macro 0.99537 → 0.99209 | Emilio, 2026-10-15 | [`evidencias/comprobaciones/recalcular_salida.txt`](../evidencias/comprobaciones/recalcular_salida.txt) |
| 5.2 | p50 y p95 (preprocesamiento + inferencia) desde los tiempos por repetición, sin las 10 de calentamiento | El mismo script (`numpy.percentile`, interpolación lineal) | Lo declarado en [`resumen_recursos.json`](../recursos/registros/resumen_recursos.json) | **Coincide**: FP32 p50 1068.81 / p95 1616.79 ms; INT8 p50 654.68 / p95 1231.15 ms (100 medidas por variante) | Emilio, 2026-10-15 | ídem |

## 6. Operación en el dispositivo

| # | Comprobación | Esperado | Obtenido | Quién | Registro |
|---|---|---|---|---|---|
| 6.1 | Cinco minutos de operación, reinicio y captura nueva | Sin caídas; tras reiniciar, captura nueva enviada | Lo esperado | **Ejecutado por Bryan** (14 oct) | [`evidencia_f9/`](../evidencia_f9/), [`fases/F9-operacion-capturas.md`](fases/F9-operacion-capturas.md) |
| 6.2 | Sin red sigue clasificando; al volver la red reenvía con el mismo ID | `Fallo de conexión`, cola en `pendientes.json`, después un solo `201` por ID | Lo esperado (7 IDs el 12 oct; 4 IDs el 14 oct) | **Ejecutado por Bryan** | [`evidencia_f3/ejecucion_offline.txt`](../evidencia_f3/ejecucion_offline.txt), [`evidencia_f9/`](../evidencia_f9/) |
