# Medición de recursos en el dispositivo (F8)

Criterios 3.1, 3.2 y 3.3. Comparación auditada entre el modelo original del Proyecto 3 y su variante optimizada cuantizada a INT8 bajo condiciones equivalentes en la Raspberry Pi 3B.

## 1. Ficha de condiciones y hardware

| Parámetro | Valor |
|---|---|
| Dispositivo | Raspberry Pi 3 Model B Rev 1.2 |
| Procesador | ARM Cortex-A53 (4 núcleos a 1.2 GHz) |
| Arquitectura | `aarch64` (Raspberry Pi OS de 64 bits) |
| Memoria RAM total | ~926 MB (1 GB físico) |
| Sistema operativo | Debian 13 (trixie) / Linux 6.6.20+rpt-rpi-v8 |
| Runtime | `onnxruntime` versión **1.31.0** |
| Proveedor de ejecución | `CPUExecutionProvider` (configurado a **1 hilo**: `intra_op_num_threads=1`, `inter_op_num_threads=1`) |
| Tamaño y tipo de entrada | Tensor `[1, 3, 224, 224]`, float32 (RGB normalizado ImageNet) |
| Procedimiento de captura | Imagen real fija de prueba (`Proyecto4/dispositivo/capturas/`); cámara V4L2 detenida durante la prueba y sin tráfico de red hacia AWS. |

## 2. Justificación de la exclusión del original en PyTorch en el edge

Se intentó evaluar el modelo original en PyTorch (`model.pt`) en el dispositivo. Sin embargo, **no se instaló ni se ejecutó en el entorno del edge** debido a que la huella de PyTorch es inviable para una arquitectura de 1 GB de RAM (la instalación supera los 250 MB en disco y su motor dinámico consume demasiados recursos). El script registra el error de importación (`ImportError` / entorno sin torch). 

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

Las mediciones se realizaron excluyendo 10 iteraciones de calentamiento (`warmup`) y registrando 100 iteraciones formales de preprocesamiento más inferencia local en un solo hilo. Los percentiles (`p50` y `p95`) se calcularon mediante **interpolación lineal** (`numpy.percentile` con `method='linear'`).

| Métrica / Percentil | ONNX FP32 (`model_fp32.onnx`) | ONNX INT8 (`model_int8.onnx`) | Mejora / Reducción |
|---|---:|---:|---:|
| **Inferencia pura p50** | ~1,048.84 ms | ~634.70 ms | **Speedup 1.65x** |
| **Inferencia pura p95** | ~1,596.02 ms | ~1,193.81 ms | — |
| **Tiempo total (prep + inf) p50** | ~1,068.81 ms | ~654.68 ms | **Speedup 1.63x** |
| **Tiempo total (prep + inf) p95** | ~1,616.79 ms | ~1,231.15 ms | — |

### Notas de rendimiento y memoria (según registros JSON)
- **Variación p50 vs p95:** Se observa que los valores de `p95` son notablemente mayores que la mediana (`p50`). Esto se debe a la variabilidad inherente del sistema operativo en la Raspberry Pi 3B (procesos de fondo del kernel, gestión de memoria virtual y ligeras fluctuaciones térmicas o micro-pausas del recolector de basura de Python bajo carga sostenida de 110 ejecuciones secuenciales).
- **Consumo de Memoria Residente (RSS):** 
  - *Antes de cargar modelo:* ~55.2 MB
  - *RSS post-carga (FP32):* ~68.4 MB / *post-ejecución:* ~70.1 MB
  - *RSS post-carga (INT8):* ~61.5 MB / *post-ejecución:* ~64.2 MB (demostrando una huella de memoria RAM más ligera con la variante cuantizada).

*Archivos de respaldo y registros detallados:*
- CSV por repetición (para recálculo auditable): [`recursos/registros/tiempos_inferencia.csv`](../recursos/registros/tiempos_inferencia.csv)
- Resumen JSON: [`recursos/registros/resumen_recursos.json`](../recursos/registros/resumen_recursos.json)

## 5. Análisis de mejora y justificación de la decisión (con Edith)

1. **Mejora demostrada en tamaño:** La reducción del **74.66 % en almacenamiento** (de ~44.8 MB a 11.3 MB) aligera de forma radical los artefactos para el dispositivo.
2. **Mejora demostrada en latencia y memoria:** La variante INT8 reduce el tiempo total de procesamiento en más de un 38% y disminuye la huella de memoria residente en la Pi 3B.
3. **Intercambio recursos vs. calidad (F7):** La caída de *accuracy* de apenas **0.342 pp** (99.66 % a 99.32 %) frente al gran ahorro de recursos justifica por completo la adopción de INT8 en este hardware.
