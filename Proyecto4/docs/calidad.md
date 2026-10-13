# Comparación de calidad: original contra optimizado (F7)

Criterio 1.3. El modelo publicado 1.0.0 del Proyecto 3 contra su variante `1.0.0-int8.1` ([`artefacto.md`](artefacto.md)), sobre **las mismas 292 muestras de validación del Proyecto 3**, con las mismas clases y etiquetas.

## Resultado

| Métrica | Original (P3 1.0.0) | Optimizado (`1.0.0-int8.1`) | Diferencia |
|---|---:|---:|---:|
| Accuracy | 0.9965753424657534 (291/292) | 0.9931506849315068 (290/292) | **caída de 0.3424657534246589 pp** (límite: 2 pp) |
| F1 macro | 0.9953705920853088 | 0.9920902865595105 | −0.003280305525798277 |
| Predicciones iguales | — | — | 291 de 292 |

La caída se calcula sin redondear: `100 × (0.9965753424657534 − 0.9931506849315068)`. **Cumple el límite de 2 puntos porcentuales.** El accuracy del original coincide con el `val_accuracy` con el que el P3 seleccionó la corrida r10 (`Proyecto3/docs/selection.json`: 0.9965753424657534).

### Por clase

| Clase | Soporte | Original: precisión / recall / F1 | Optimizado: precisión / recall / F1 |
|---|---:|---|---|
| cat | 67 | 1.0000 / 0.9851 / 0.9925 | 1.0000 / 0.9851 / 0.9925 |
| dog | 78 | 0.9873 / 1.0000 / 0.9936 | 0.9872 / 0.9872 / 0.9872 |
| person | 147 | 1.0000 / 1.0000 / 1.0000 | 0.9932 / 1.0000 / 0.9966 |

Valores sin redondear en [`metricas.json`](../calidad/registros/metricas.json) (`per_class`).

### Matrices de confusión (filas: clase real; columnas: predicha; orden cat, dog, person)

| | Original | Optimizado |
|---|---|---|
| cat | 66 · 1 · 0 | 66 · 1 · 0 |
| dog | 0 · 78 · 0 | 0 · **77** · **1** |
| person | 0 · 0 · 147 | 0 · 0 · 147 |

## Errores y su explicación

Solo hay dos muestras con error en alguno de los modelos:

| `crop_id` | Real | Original | Optimizado | Explicación |
|---|---|---|---|---|
| `0.1.3:a322` | cat | dog (0.8913) | dog (0.8691) | **No lo causa la optimización:** los dos se equivocan igual. Es un gato hecho bola sobre ropa oscura, sin la cara de frente; el error ya existía en el P3. |
| `0.1.3:a554` | dog | dog (**0.5535**) | person (0.5761; dog 0.4121) | **El único cambio de la optimización.** El original ya dudaba (dog con apenas 0.55): es un recorte de 91×82 px, oscuro y casi monocromo, que se estira a 224×224. Con un margen tan corto, el error de redondeo de la cuantización INT8 basta para invertir dog y person. |

**Clases afectadas:** solo `dog` pierde un acierto (recall 1.0 → 0.9872) y `person` gana un falso positivo (precisión 1.0 → 0.9932). `cat` no cambia. La cuantización afecta a las muestras con margen bajo; las de confianza alta conservan su clase (291 de 292 iguales).

## Cómo se evaluó cada modelo

| | Original | Optimizado |
|---|---|---|
| Archivo y SHA-256 | `model.pt`, `e4acca42…9172` | `model_int8.onnx`, `ca689c4e…69c0` |
| Preprocesamiento | el del P3 (`build_eval_transform`, torchvision) | el del edge ([`modelo/preprocess.py`](../modelo/preprocess.py)) |
| Runtime | PyTorch 2.14.0 (CPU), Python 3.12.10, x86-64 | onnxruntime **1.31.0**, Python 3.13, aarch64 |
| Plataforma | laptop | contenedor `linux/arm64` (Debian 13) con CPU **Cortex-A53** emulada por QEMU (`QEMU_CPU=cortex-a53`, sin `dotprod`): el procesador, SO y runtime de la Raspberry Pi 3 |

**Por qué el INT8 se evalúa en aarch64 y no en la laptop:** en x86 el mismo archivo da otras probabilidades (saturación de INT8 con AVX2; [`artefacto.md`](artefacto.md)). En la laptop el INT8 daría 0.9828767123287672, una caída aparente de 1.37 pp que **no es la del dispositivo**. Se guarda como referencia en [`registros/referencias/pred_int8_x86.csv`](../calidad/registros/aux/pred_int8_x86.csv).

**La emulación reproduce la Pi:** en las 3 entradas conocidas, el contenedor da exactamente las mismas probabilidades que la Raspberry Pi física ([`evidencia_f3/arm64_check_output.txt`](../evidencia_f3/arm64_check_output.txt)): `a1330` dog 0.930898, `a1528` cat 0.999977, `a1022` person 0.992791. Las filas de esas muestras en [`pred_optimizado.csv`](../calidad/registros/pred_optimizado.csv) tienen los mismos valores.

**Efecto de la exportación contra el de la cuantización:** el ONNX FP32 exportado da 0.9965753424657534, igual que el original ([`referencias/pred_fp32_x86.csv`](../calidad/registros/referencias/pred_fp32_x86.csv)). Toda la diferencia viene de la cuantización, no de la exportación ni del preprocesamiento del edge.

## Separación de datos

- **Validación:** la partición `val` del manifiesto `m-0.1.3-s42-1` (SHA-256 `45600f29…4305`): cat 67, dog 78, person 147. `comparar.py` comprueba que no falta ni sobra ninguna muestra, que no hay IDs duplicados, que las etiquetas son las del manifiesto y que las tres clases tienen soporte. Además verifica que cada archivo de predicciones venga del modelo esperado (SHA-256 en su `.meta.json`).
- **Calibración:** 200 recortes **solo de `train`** del mismo manifiesto, semilla 42 (48 cat, 54 dog, 98 person), en [`calibracion_manifest.jsonl`](../modelo/registros/calibracion_manifest.jsonl). Ninguno está en validación ni en test.
- **Test:** no se usó en ningún paso, ni para calibrar, ni para elegir la configuración de cuantización, ni para esta comparación. `predecir.py` solo lee filas con `split == "val"`. La configuración de F2 (QDQ, por canal, MinMax) se fijó antes de medir y no se cambió después.

## Archivos

| Archivo | Contenido |
|---|---|
| [`calidad/registros/predicciones_validacion.csv`](../calidad/registros/predicciones_validacion.csv) | **Una fila por muestra:** `crop_id`, clase real, clase del original, clase del optimizado, confianzas y si coinciden. SHA-256 `d5a08f1b…c754` |
| [`calidad/registros/pred_original.csv`](../calidad/registros/pred_original.csv) + `.meta.json` | Original: clase y las tres probabilidades sin redondear, más el entorno de la corrida |
| [`calidad/registros/pred_optimizado.csv`](../calidad/registros/pred_optimizado.csv) + `.meta.json` | Optimizado en aarch64: lo mismo |
| [`calidad/registros/metricas.json`](../calidad/registros/metricas.json) | Métricas, matrices, comprobaciones del manifiesto, caída en pp y filas con error o cambio |
| `calidad/registros/referencias/` | Referencias: ONNX FP32 y el INT8 en x86 (no cuentan como resultado del edge) |

## Reproducir

Requiere los recortes y el manifiesto del P3 (`dvc pull` en `Proyecto3`) y la variante de F2 en `Proyecto4/artifacts/1.0.0-int8.1/` (descarga desde S3 en [`artefacto.md`](artefacto.md)). Desde `Proyecto4/`:

```bash
.venv/Scripts/python calidad/predecir.py --backend torch --model ../Proyecto3/mlflow_snapshot/artifacts/3/9f9b62c202f0446a8a4b411a10321eff/artifacts/checkpoint/model.pt --manifest ../Proyecto3/data/manifests/m-0.1.3-s42-1/manifest.jsonl --crops ../Proyecto3/data/crops/0.1.3 --out calidad/registros/pred_original
```

El optimizado, en aarch64. Desde la raíz del repositorio (en la Pi basta el `python …` de adentro, con rutas locales):

```bash
docker run --rm --platform linux/arm64 -e QEMU_CPU=cortex-a53 -v "$PWD/Proyecto4:/p4" -v "$PWD/Proyecto3/data:/p3data:ro" python:3.13-slim-trixie sh -c "pip install -q onnxruntime==1.31.0 'numpy>=2.2,<2.6' 'pillow>=11,<13' && python /p4/calidad/predecir.py --backend onnx --model /p4/artifacts/1.0.0-int8.1/model_int8.onnx --manifest /p3data/manifests/m-0.1.3-s42-1/manifest.jsonl --crops /p3data/crops/0.1.3 --out /p4/calidad/registros/pred_optimizado"
```

```bash
.venv/Scripts/python calidad/comparar.py
```

Para recalcular sin los scripts: en `predicciones_validacion.csv`, el accuracy es la fracción de filas con `true_class == pred_original` (o `pred_optimizado`), y el F1 por clase sale de contar TP, FP y FN por columna.
