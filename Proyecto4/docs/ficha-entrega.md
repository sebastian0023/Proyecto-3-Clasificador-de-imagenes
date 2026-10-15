# Ficha de entrega — Proyecto 4: modelo en edge

Recorrido: **modelo 1.0.0 del Proyecto 3 → variante INT8 `1.0.0-int8.1` (ONNX) → clasificación local en una Raspberry Pi 3B con cámara, sin red → fotografía y evento a AWS S3 → sección Capturas Edge del portal de los Proyectos 1 a 3.**

Cómo instalar, arrancar y verificar: [`README.md`](../README.md). Índice de evidencias: [`evidencias/INDICE.md`](../evidencias/INDICE.md). Comprobaciones repetibles: [`comprobaciones.md`](comprobaciones.md).

## Equipo y roles

| Persona | Rol | Fases |
|---|---|---|
| Sebastián | PM: coordina, valida casillas con evidencia, envía la entrega | F1, F11 |
| Edith | Modelo y optimización | F2, F7 |
| Bryan | Dispositivo edge y cámara | F3, F8, F9 |
| Emilio | AWS, portal e integración | F4, F5, F6, F10 |

Detalle en [`PLAN.md`](PLAN.md).

## Dispositivo, cámara y entorno (valores de la Pi física)

| Dato | Valor | Fuente |
|---|---|---|
| Dispositivo | Raspberry Pi 3 Model B Rev 1.2, ARM Cortex-A53 (4 núcleos), 905 MB de RAM útil, `aarch64` | [`recursos/registros/resumen_recursos.json`](../recursos/registros/resumen_recursos.json) |
| Cámara | Cámara web USB (V4L2, `/dev/video0`), resolución estándar; capturas de 640×480. El modelo comercial de la cámara no está registrado | [`decisiones.md`](decisiones.md) §7, [`evidencias/capturas_20/`](../evidencias/capturas_20/) |
| Sistema operativo | Debian GNU/Linux 13 (trixie) de 64 bits, kernel `6.18.50+rpt-rpi-v8` | [`evidencia_f3/entorno.txt`](../evidencia_f3/entorno.txt), `resumen_recursos.json` |
| Runtime | Python 3.13.5; **onnxruntime 1.31.0** (`CPUExecutionProvider`, 1 hilo); **numpy 2.5.4**; opencv-python-headless 4.13.0.92; pillow 12.2.0; requests 2.33.1 | `resumen_recursos.json`, [`evidencia_f3/arm64_check_output.txt`](../evidencia_f3/arm64_check_output.txt), [`decisiones.md`](decisiones.md) §7 |
| Programa | [`dispositivo/edge_camera.py`](../dispositivo/edge_camera.py): captura por intervalo (~5 s), clasifica, guarda foto y evento y envía; cola persistente de pendientes | [`fases/F3-edge-camara.md`](fases/F3-edge-camara.md), [`demo-f6.md`](demo-f6.md) |

## Modelo de origen (Proyecto 3)

| Dato | Valor |
|---|---|
| Versión publicada | `1.0.0` (activa en el registro del P3) |
| Run ID de MLflow | `9f9b62c202f0446a8a4b411a10321eff` (r10, mejor época 6) |
| Pesos | `s3://dataset-quality-releases-750702272375/models/clasificador/1.0.0/model.pt`, SHA-256 `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172`, 44 783 563 bytes |
| Arquitectura y clases | ResNet-18; salida en orden 0 `cat`, 1 `dog`, 2 `person` |
| Preprocesamiento | RGB, 224×224 sin recorte (bilineal con antialias), escala a [0, 1], normalización ImageNet |

Fuente: [`artefacto.md`](artefacto.md) y [`decisiones.md`](decisiones.md) (tabla de referencia del P3).

## Variante optimizada y técnica

| Dato | Valor |
|---|---|
| Versión | **`1.0.0-int8.1`** |
| Formato | ONNX opset 18 |
| Técnica | Cuantización estática post-entrenamiento con onnxruntime: QDQ, pesos INT8 por canal, activaciones INT8, calibración MinMax con 200 recortes **solo de train** |
| Archivo | `model_int8.onnx`, **11 349 151 bytes**, SHA-256 **`ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0`** |
| Dónde está | `s3://dataset-quality-releases-750702272375/models/clasificador-edge/1.0.0-int8.1/` (VersionId de cada objeto en [`modelo/registros/publicacion.json`](../modelo/registros/publicacion.json)) |
| Conversión reproducible | [`modelo/convert.py`](../modelo/convert.py), [`modelo/conversion.yaml`](../modelo/conversion.yaml), registro con entrada y salida en [`modelo/registros/conversion_log.json`](../modelo/registros/conversion_log.json) |

## Resultados clave

| Medida | Original | Optimizado | Resultado | Registro |
|---|---|---|---|---|
| Tamaño | 44 783 563 B (`model.pt`); 44 791 921 B (ONNX FP32) | 11 349 151 B | **74.66 % menos** | [`recursos.md`](recursos.md), `resumen_recursos.json` |
| Latencia local p50 (preprocesamiento + inferencia, Pi, 1 hilo, 100 medidas tras 10 de calentamiento) | 1068.81 ms (ONNX FP32) | 654.68 ms | **38.75 % menos** | [`recursos/registros/tiempos_inferencia.csv`](../recursos/registros/tiempos_inferencia.csv) |
| Latencia local p95 | 1616.79 ms | 1231.15 ms | 23.85 % menos | ídem |
| Memoria RSS tras ejecutar | 123.18 MB | 104.52 MB | — | `resumen_recursos.json` |
| Accuracy en validación del P3 (292 muestras, manifiesto `m-0.1.3-s42-1`) | 0.9965753424657534 (291/292) | 0.9931506849315068 (290/292) | **caída de 0.342 pp** (límite 2 pp) | [`calidad.md`](calidad.md), [`calidad/registros/metricas.json`](../calidad/registros/metricas.json) |
| F1 macro | 0.9953705920853088 | 0.9920902865595105 | −0.00328 | ídem |

Notas de método, ya documentadas en cada fuente:

- PyTorch no se instala en la Pi (`ModuleNotFoundError: torch`); la latencia del original se mide con su exportación ONNX FP32, que difiere de PyTorch en menos de 1.2e-7 en los logits ([`recursos.md`](recursos.md)).
- El INT8 de la comparación de calidad se evaluó en un contenedor `linux/arm64` con CPU Cortex-A53 emulada (QEMU), no en la Pi física; en las 3 entradas conocidas da exactamente las mismas probabilidades que la Pi ([`calidad.md`](calidad.md)). En x86 el INT8 da otras probabilidades y no se usa para la calidad ([`artefacto.md`](artefacto.md)).

## AWS y portal

| Dato | Valor |
|---|---|
| Servicio | Amazon S3, bucket `dataset-quality-releases-750702272375` (us-east-1), prefijo `edge-captures/` (`events/{id}.json` e `images/{id}.jpg`) |
| Registros en S3 | **285** registros y 285 imágenes en `edge-captures/` (consulta de solo lectura del 2026-10-15T04:36:12Z = 14 oct 22:36 −06:00) |
| Receptor | `POST https://174-129-84-80.sslip.io/api/p4/captures` con token Bearer del dispositivo ([`contratos.md`](contratos.md)) |
| Portal | **`https://174-129-84-80.sslip.io`**, sección **Capturas Edge** (`#/edge-captures`) en el menú lateral, entre Inference y Settings |
| Acceso de evaluación | Usuario **`evaluador`** de Caddy (`basic_auth`); la contraseña se entrega por canal privado y **no está en este paquete** |
| Consulta de solo lectura | [`consulta-aws.md`](consulta-aws.md) |
| Despliegue | EC2 `i-0348c123c4c126267` (t3.medium) con IP elástica `174.129.84.80`, Docker Compose y Caddy; rol de instancia sin llaves ([`despliegue.md`](despliegue.md)) |

La galería muestra las **100 capturas más recientes** («Mostrando 100 de 285»). Una captura anterior se consulta con `GET /api/p4/captures/{id}` (con `basic_auth`), con la exportación completa (`/api/p4/captures/export?format=csv|json`) o con [`scripts/trazar_captura.py`](../scripts/trazar_captura.py) ([`README.md`](../README.md#consultar-capturas-anteriores)).

## Capturas de operación

[`evidencias/capturas_20/`](../evidencias/capturas_20/): capturas de `edge01` hechas con el programa final, entre las 100 visibles en la galería, con foto, registro, SHA-256 verificado y VersionId. Reparto: 7 `cat`, 7 `dog` y 6 `person` (**las 6 `person` están pendientes**: Bryan toma fotos nuevas de una persona sin cara, por privacidad).

Observaciones honestas sobre las capturas recientes (no cambian la calidad medida, que sale de la validación etiquetada de F7; la rúbrica aclara que las 20 capturas verifican operación y no tienen un umbral de accuracy):

- La mayoría de las capturas del 12 al 14 oct son fotos de un **monitor** que muestra imágenes; es la cámara de la Pi, pero en la demostración se usarán objetos físicos.
- Errores del modelo visibles en esas capturas: un golden retriever en pantalla clasificado como `cat` (`5fbc3570…`, 0.885; `50930285…`, 0.914) y perros en pantalla clasificados como `person` (4 capturas, confianza 0.59–0.72). Quedan fuera de las 20 y se listan en [`evidencias/INDICE.md`](../evidencias/INDICE.md).

Operación estable, reinicio y reintentos: [`fases/F9-operacion-capturas.md`](fases/F9-operacion-capturas.md) y [`evidencia_f9/`](../evidencia_f9/). Fallo y reintento con el mismo ID: [`demo-f6.md`](demo-f6.md) y [`fases/F6-recorrido-completo.md`](fases/F6-recorrido-completo.md).

## Configuración (6.3)

Tabla de dónde se cambian el destino de AWS, la identidad del dispositivo y el artefacto: [`README.md`](../README.md#configuración).

## Pendientes y observaciones para la evaluación

- 6 capturas `person` de las 20 (fotos nuevas sin cara).
- Video: lo agrega F11.
- En [`decisiones.md`](decisiones.md), la tabla resumen marca las decisiones 4 (modo de captura) y 7 (hardware) como «pendiente» aunque sus secciones ya están llenas; las cierra Bryan en un PR aparte.
- El `device_id` del dispositivo (`edge01`) y el SHA-256 del modelo esperado están fijos en `dispositivo/edge_camera.py` (código congelado); el artefacto se elige con `--model`/`--version` y el destino con `--url`/`P4_API_URL`.
- El modelo comercial de la cámara web no está registrado.
