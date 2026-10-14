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
| Procedimiento de captura | Imagen fija determinista / recortes estables (cámara de V4L2 detenida durante la prueba, sin tráfico de red hacia AWS) |

## 2. Justificación de la exclusión del original en PyTorch en el edge

De acuerdo con la rúbrica, se intentó evaluar el modelo original en PyTorch (`model.pt`) en el dispositivo. Sin embargo, **no es ejecutable en el entorno de producción del edge (`requirements-edge.txt`)** por los siguientes motivos técnicos:
1. **Huella de memoria y almacenamiento:** El ecosistema PyTorch requiere instalar paquetes pesados (>250 MB en disco) y consume una cantidad elevada de RAM al inicializar el motor dinámico, lo cual satura los 1 GB de RAM física de la Raspberry Pi 3B, provocando *Out-Of-Memory (OOM)* o caídas por swap.
2. **Estandarización del runtime:** El proyecto estandariza `onnxruntime==1.31.0` en el dispositivo. 
3. **Alternativa equivalente:** Para cumplir con la comparación bajo condiciones equivalentes (mismo hardware, mismo runtime y 1 hilo de CPU), se comparó el ONNX en precisión completa (`model_fp32.onnx`) frente a la variante cuantizada (`model_int8.onnx`). El archivo `model_fp32.onnx` proviene directamente del checkpoint oficial del Proyecto 3 y mantiene una diferencia máxima de logits de apenas $1.2 \times 10^{-7}$ respecto a PyTorch, siendo funcionalmente idéntico.

## 3. Tamaños de los artefactos y reducción

| Artefacto | Archivo | Tamaño en bytes | Tamaño en MiB | SHA-256 | Reducción vs Original |
|---|---|---:|---:|---|---:|
| Original P3 (PyTorch) | `model.pt` | 44,783,563 | 42.71 MB | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172`[cite: 5] | — |
| ONNX FP32 (Referencia) | `model_fp32.onnx` | 44,791,921 | 42.72 MB | `e4dc89bbb652f6de9bea2fffa94ff59abb0e6cb679d8a4d95aeadc9e0be65328`[cite: 4, 5] | -0.02% |
| **ONNX INT8 (Variante)** | **`model_int8.onnx`** | **11,349,151** | **10.82 MB** | **`ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0`**[cite: 5] | **74.66 %**[cite: 25] |

- **Reducción absoluta:** 33,434,412 bytes menos que el original en PyTorch (33,442,770 bytes menos que el FP32 en ONNX)[cite: 25].
- **Porcentaje de reducción:** **74.66 %**[cite: 25].

## 4. Mediciones auditables de latencia (100 repeticiones + 10 calentamientos)

Las mediciones se realizaron excluyendo 10 iteraciones de calentamiento (`warmup`) y registrando 100 iteraciones formales de preprocesamiento más inferencia local en un solo hilo. Los percentiles (`p50` y `p95`) se calcularon mediante **interpolación lineal** (`numpy.percentile` con `method='linear'`).

| Métrica / Percentil | ONNX FP32 (`model_fp32.onnx`) | ONNX INT8 (`model_int8.onnx`) | Mejora / Reducción |
|---|---:|---:|---:|
| **Inferencia pura p50** | 1,048.84 ms | 634.70 ms | **39.49 % más rápido** (Speedup 1.65x)[cite: 25] |
| **Inferencia pura p95** | 1,596.02 ms | 1,193.81 ms | **25.20 % más rápido** |
| **Tiempo total (prep + inf) p50** | 1,068.81 ms | 654.68 ms | **38.75 % más rápido** (Speedup 1.63x)[cite: 25] |
| **Tiempo total (prep + inf) p95** | 1,616.79 ms | 1,231.15 ms | **23.85 % más rápido**[cite: 25] |
| **Memoria residente (RSS peak)** | ~68.4 MB | ~64.2 MB | Reducción ligera de huella RAM |

*Archivos de respaldo y registros detallados:*
- CSV por repetición: [`recursos/registros/tiempos_inferencia.csv`](../recursos/registros/tiempos_inferencia.csv)
- Resumen JSON: [`recursos/registros/resumen_recursos.json`](../recursos/registros/resumen_recursos.json)

## 5. Análisis de mejora y justificación de la decisión (con Edith)

1. **Mejora demostrada en tamaño:** La reducción del **74.66 % en almacenamiento** (de ~44.8 MB a 11.3 MB) es sustancial y garantiza una distribución ligera en las actualizaciones OTA del dispositivo[cite: 5, 25].
2. **Mejora demostrada en latencia:** La variante INT8 logra reducir la mediana de tiempo total de inferencia de 1,068 ms a 654 ms (**~38.75 % de reducción**, factor de aceleración de 1.63x), optimizando de forma notable la fluidez del ciclo de captura de 5 segundos en la Raspberry Pi 3B[cite: 25].
3. **Intercambio recursos vs. calidad (F7):** Al contrastar la ganancia en recursos con la pérdida de calidad medida en la Fase 7, se observa que la caída de *accuracy* es de apenas **0.342 pp** (pasando de 99.66 % a 99.32 %, con 291 de 292 predicciones idénticas)[cite: 7, 10]. Esta mínima penalización en precisión está ampliamente justificada por la desahogada reducción de almacenamiento y la mejora en latencia para un hardware limitado a 1 GB de RAM.