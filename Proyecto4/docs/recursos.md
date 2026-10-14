# Medición de recursos en el dispositivo (F8)

Criterios 3.1, 3.2 y 3.3. Comparación auditada entre el modelo original del Proyecto 3 y su variante optimizada cuantizada a INT8 bajo condiciones equivalentes en la Raspberry Pi 3B.

## 1. Ficha de condiciones y hardware

| Parámetro | Valor |
|---|---|
| Dispositivo | Raspberry Pi 3 Model B Rev 1.2 |
| Procesador | ARM Cortex-A53 (4 núcleos a 1.2 GHz) |
| Arquitectura | `aarch64` (Raspberry Pi OS de 64 bits) |
| Memoria RAM total | ~905 MB (1 GB físico) |
| Sistema operativo | Debian 13 (trixie) / Linux 6.18.50+rpt-rpi-v8 |
| Runtime | `onnxruntime` versión **1.31.0** |
| Proveedor de ejecución | `CPUExecutionProvider` (configurado a **1 hilo**: `intra_op_num_threads=1`, `inter_op_num_threads=1`) |
| Tamaño y tipo de entrada | Tensor `[1, 3, 224, 224]`, float32 (RGB normalizado ImageNet) |
| Procedimiento de captura | Imagen real fija de prueba (`Proyecto4/dispositivo/capturas/004325d5-…`). Cámara V4L2 detenida durante la prueba y sin tráfico de red hacia AWS. |

## 2. Justificación de la exclusión del original en PyTorch en el edge

No se evaluó el original en PyTorch porque no se instaló en el entorno de producción por ser inviable en la arquitectura de 1 GB de RAM. Al intentar su importación, el script registra el error exacto: `ModuleNotFoundError: No module named 'torch'`. No se afirma un OOM ya que no se llegó a instanciar en ejecución.

Para cumplir con la comparación bajo condiciones equivalentes (mismo hardware, mismo runtime y 1 hilo de CPU), se comparó el ONNX en precisión completa (`model_fp32.onnx`) frente a la variante cuantizada (`model_int8.onnx`). El archivo `model_fp32.onnx` proviene directamente del checkpoint oficial del Proyecto 3 y mantiene una diferencia máxima de logits de apenas $1.2 \times 10^{-7}$ respecto a PyTorch.

## 3. Tamaños de los artefactos y reducción

| Artefacto | Archivo | Tamaño en bytes | Tamaño en MiB | SHA-256 | Reducción vs Original |
|---|---|---:|---:|---|---:|
| Original P3 (PyTorch) | `model.pt` | 44,783,563 | 42.71 MB | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172` | — |
| ONNX FP32 (Referencia) | `model_fp32.onnx` | 44,791,921 | 42.72 MB | `e4dc89bbb652f6de9bea2fffa94ff59abb0e6cb679d8a4d95aeadc9e0be65328` | -0.02% |
| **ONNX INT8 (Variante)** | **`model_int8.onnx`** | **11,349,151** | **10.82 MB** | **`ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0`** | **74.66 %** |

- **Reducción absoluta:** 33,434,412 bytes menos que el original en PyTorch.
- **Porcentaje de reducción:** **74.66 %**.

## 4. Mediciones auditables de latencia y memoria (100 repeticiones + 10 calentamientos)

Las mediciones se realizaron excluyendo 10 iteraciones de calentamiento (`warmup`) y registrando 100 iteraciones formales de preprocesamiento más inferencia local en un solo hilo. Los percentiles (`p50` y `p95`) se calcularon mediante interpolación lineal (`numpy.percentile` con `method='linear'`).

| Métrica / Percentil | ONNX FP32 (`model_fp32.onnx`) | ONNX INT8 (`model_int8.onnx`) | Mejora / Reducción |
|---|---:|---:|---:|
| **Inferencia pura p50** | 1048.84 ms | 634.70 ms | **1.65× más rápido** |
| **Inferencia pura p95** | 1596.02 ms | 1193.81 ms | **25.20 % menos** |
| **Tiempo total (prep + inf) p50** | 1068.81 ms | 654.68 ms | **1.63× más rápido** |
| **Tiempo total (prep + inf) p95** | 1616.79 ms | 1231.15 ms | **23.85 % menos** |

### Análisis de memoria (según registros JSON)
- **Carga de modelo:** La sobrecarga al cargar el modelo en memoria muestra una diferencia notable: FP32 incrementa el consumo en **+55 MB**, mientras que INT8 solo requiere **+15 MB** adicionales.
- **Consumo final:** Al concluir las corridas, el proceso con FP32 alcanza **123.18 MB** de RSS, frente alos **104.52 MB** de la variante INT8. Representa una optimización de memoria muy superior.

### Variabilidad y comportamiento térmico
Se observa que la variante INT8 alterna en rachas de latencia (57 corridas rápidas a ~630 ms frente a 43 corridas a ~1160 ms). Esto se atribuye probablemente a la modulación de frecuencia de la Pi bajo carga sostenida. El estado térmico y de throttling fue verificado y registrado mediante `vcgencmd` (véase `recursos/registros/throttling.txt`, con temperatura registrada en 39.2 °C).
A pesar de esta alternancia, la mediana (`p50`) mejora 1.63 veces, el promedio global baja de 1135 a 859 ms, y la reducción de tamaño se consolida en el 74.66 %.

*Archivos de respaldo y registros detallados:*
- CSV por repetición: [`recursos/registros/tiempos_inferencia.csv`](../recursos/registros/tiempos_inferencia.csv)
- Resumen JSON: [`recursos/registros/resumen_recursos.json`](../recursos/registros/resumen_recursos.json)
- Registro térmico: [`recursos/registros/throttling.txt`](../recursos/registros/throttling.txt)

## 5. Análisis de mejora y justificación de la decisión (con Edith)

1. **Mejora demostrada en tamaño:** La reducción del **74.66 % en almacenamiento** aligera drásticamente la transferencia al dispositivo.
2. **Mejora demostrada en latencia y memoria:** La variante INT8 reduce el tiempo promedio de inferencia y optimiza fuertemente el consumo de RSS (104.52 MB vs 123.18 MB).
3. **Intercambio recursos vs. calidad (F7):** La caída de *accuracy* de apenas **0.342 pp** (99.66 % a 99.32 %) justifica plenamente la adopción de INT8 para este hardware de 1 GB.