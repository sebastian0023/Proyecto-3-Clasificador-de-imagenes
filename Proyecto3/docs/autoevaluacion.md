# Autoevaluación con el prompt de la rúbrica (F11 T29)

## Pasada preliminar — 30 sep 2026, sobre `main` en `f7b5c47` (superada por la pasada sobre `3e423c4`, abajo)

Pasada **estática y con datos primarios**, sin levantar el stack, para encontrar
huecos con tiempo. La pasada final se repite sobre el commit candidato (con F9 y
#17 fusionados) en una copia limpia, siguiendo `docs/rubrica.md` completo.

**Qué se recalculó con datos primarios** (no se tomó ninguna cifra de la documentación):

- **Manifiesto** (`manifest.jsonl` de `m-0.1.3-s42-1`): 0 elementos compartidos entre particiones en las 9 intersecciones (`crop_id`, `source_image_id`, `dup_group_id` × 3 pares). Train 1022 (70.05 %), val 292 (20.01 %), test 145 (9.94 %). Originales distintos por clase: person 441, dog 348, cat 312 (todas ≥ 300). Las tres clases están en val y test.
- **MLflow** (`mlflow_snapshot/mlflow.db`): 14 corridas en `p3-clasificador`, 2 `FAILED`, **12 válidas** (`FINISHED`, mismo `manifest_hash`, commit `250bedc` limpio). Los 7 parámetros varían: optimizer {adam, adamw, sgd}, batch {32, 64}, épocas {15, 30}, lr {1e-4, 3e-4, 1e-3, 3e-3, 1e-2}, image_size {128, 160, 224}, capas ocultas {[], [256], [512, 128]}, dropout {0.2, 0.3, 0.5}. Sin duplicados exactos.
- **Test** (`predictions_test.csv`): los 145 `crop_id` son exactamente el test congelado. Matriz propia `[[30, 2, 0], [0, 38, 0], [0, 1, 74]]`, total 145; accuracy 142/145 = 0.97931 ≥ 0.85; F1 macro 0.9744; baseline (person) 0.5172; las probabilidades suman 1. Coincide con `metrics.json` y MLflow.
- **Cronología:** `selection.json` en `6bd9101` (26 sep 21:40 −06), script de evaluación en `a7ec1dc` (27 sep 20:22 −06), evaluación a las 02:25Z del 28 sep. La selección es anterior al test.

### A. Requisitos mínimos

| Estado | Requisito | Evidencia |
|---|---|---|
| CUMPLE* | M1 Arranque desde el README | `docs/ensayo_arranque.md`: `up.py` levantó 13 servicios `Healthy` desde un clon limpio (27 sep). *Repetir en el ensayo final con las 5 páginas; hoy el build tarda ~92 min por torch con CUDA. |
| CUMPLE | M2 Release aprobado y versionado | release `0.1.3` (`pass`) → `raw.dvc` md5 `ca56420c…` → `open_release_archive` (SHA-256 + huella) → manifiesto con `dvc_pointer`; tags `release_id`, `release_hash` y `dvc_md5` en cada corrida |
| CUMPLE | M3 Aislamiento | 0 en las 9 intersecciones (recalculado); aumentación solo en train (`p3.data.transforms`); selección por validación antes del test |
| CUMPLE | M4 Modelo recargable | `model.pt` de 1.0.0 descargado de S3 → venv limpio → `dog` 0.9438 ([publicacion_s3.md](publicacion_s3.md)); 145/145 predicciones del portal = `predictions_test.csv` |

**Compuerta:** NO ACTIVADA (pendiente de reconfirmar M1 en el ensayo).

### B. Tabla de calificación (estimada)

| Puntos | Requisito | Lo que falta |
|---|---|---|
| 3.5 / 4 | 1.1 Traspaso desde P2 | En el portal, elegir otro release aprobado da 409 (solo 0.1.3 tiene manifiesto congelado), así que no se ve "cambiar de release cambia los conteos". Está demostrado en código (`tests/test_releases.py::test_cambiar_de_release_cambia_los_conteos`); mostrarlo en la demo con el script. |
| 5 / 5 | 1.2 Recortes y clases | — |
| 5 / 5 | 1.3 Manifiesto 70/20/10 | — |
| **13.5 / 14** | **Subtotal Integración y datos** | |
| 5 / 5 | 2.1 Clasificador entrenado | — (ResNet-18 ImageNet declarado; no re-verificado aquí) |
| 4 / 4 | 2.2 Minibatches y parámetros | — (422 por API y validación en el portal) |
| 4 / 4 | 2.3 Semillas y aumentación | — (semilla y entorno en tags; no re-verificado aquí) |
| 5 / 5 | 2.4 Curvas y early stopping | — (pruebas de F4; no re-verificado aquí) |
| **18 / 18** | **Subtotal Modelo** | |
| 6 / 6 | 3.1 Diez experimentos | — (12 válidas, recalculado) |
| 5 / 5 | 3.2 Registro en MLflow | — |
| 3 / 3 | 3.3 Comparación y elección | — (Experiments con datos reales; cronología verificada) |
| **14 / 14** | **Subtotal Experimentos** | |
| 5 / 5 | 4.1 Protocolo congelado | — |
| 3 / 4 | 4.2 Matriz y métricas | Recalculadas y coinciden con MLflow y API, pero **la página Evaluation está "En construcción"**: falta el contraste con el portal (F9). |
| 6 / 6 | 4.3 Umbral de 85 % | — (0.97931, recalculado) |
| 1.5 / 3 | 4.4 Errores | Hay `errors.json`, `/api/p3/evaluation/examples` y [analisis_errores.md](analisis_errores.md), pero **no hay ejemplos navegables en el portal** (F9). |
| **15.5 / 18** | **Subtotal Evaluación** | |
| 4 / 4 | 5.1 Paquete | — |
| 4 / 4 | 5.2 S3 real | — (`head-object`, SHA-256 local, inferencia en venv limpio) |
| 1 / 2 | 5.3 Registro navegable | La API `/api/p3/models` resuelve versiones y activa, pero **la página Models no existe todavía** (F9). |
| **9 / 10** | **Subtotal S3** | |
| 4 / 4 | 6.1 Training | — (repetir recarga real en el ensayo) |
| 3 / 3 | 6.2 Experiments | — (con #12 en `main`) |
| **0 / 3** | 6.3 Evaluation | **Página "En construcción"** en `Proyecto2/web/src/pages/Evaluation.tsx` (F9). |
| **0 / 4** | 6.4 Models | **Página "En construcción"** en `Models.tsx` (F9). |
| **0 / 4** | 6.5 Inference | **Página "En construcción"** en `Inference.tsx` (F9). El backend y el envío a la cola ya funcionan (F4 T24). |
| **7 / 18** | **Subtotal Portal** | |
| 4 / 4 | 7.1 Pruebas y TDD | — (red → green y mutaciones documentadas en cada fase) |
| 1.5 / 2 | 7.2 Integración | `tests/test_e2e.py` escribe `registry.json` a mano en vez de usar `p3.registry.publish` y no pasa por el portal (comentario del #14). |
| 2 / 2 | 7.3 CI y secretos | — (Ruff, pytest, E2E, build del web y gitleaks en verde) |
| **7.5 / 8** | **Subtotal Pruebas** | |

### E. Resultado estimado

```text
Suma de secciones:      84.5 / 100
Compuerta aplicada:     no (M1 por reconfirmar)
CALIFICACIÓN FINAL:     84.5  → Bueno
Meta de 85% en test:    alcanzada (0.97931, recalculado)
Con F9 en main:         hasta ~99 (+11 de 6.3–6.5, +1 de 4.2, +1.5 de 4.4, +1 de 5.3)
```

### F. Qué hacer antes del tag, por impacto

1. **F9 (Andrés): Evaluation, Models e Inference en el portal** → hasta +14.5. Sin rama en GitHub al momento de esta pasada. Los endpoints ya están en `main` y documentados en `contratos.md`.
2. **#17 en `main`**: sin 500 en un arranque limpio (MLflow sin experimento, S3 sin credenciales). Protege M1 y 6.x.
3. **torch CPU en las imágenes (Edith, F4)**: el build de ~92 min es un riesgo para M1 si el evaluador levanta el stack.
4. **E2E con `p3.registry.publish`** (Andrés, F10) → +0.5 en 7.2.
5. En la demo, mostrar que cambiar de release cambia los conteos (1.1) con la prueba que lo cubre (`pytest tests/test_releases.py -k cambiar_de_release`): `generate_manifest.py` hoy solo genera el release fijado en el script, sin opción para elegir otro.

## Pasada sobre `main` en `3e423c4` — 30 sep 2026, corregida el 1 oct: **no válida para la entrega**

> **Corrección (1 oct, revisión de Edith en el #22).** Esta pasada no levantó el stack y aun así calificó M1 como CUMPLE y dio puntos a la sección 6 y a 2.2. Eso contradice la regla 1 de la rúbrica ("sin evidencia, no hay puntos"). Edith levantó el stack sobre este mismo commit y **Training sale en blanco**: el registro real incluye 0.1.1 con `archive_sha256` nulo y la página lo recortaba. Por lo tanto **M1 no se cumple y la compuerta se activa (máximo 60)**. Abajo están las puntuaciones corregidas; la pasada válida se repite **con el stack levantado** después de integrar #23, #25 y #26 (`fix/m1-training`).

Sobre el commit candidato, con F9 (#19), los 503 (#17, #20) y torch de CPU (#21)
ya en `main`. CI de `main` en verde (`CI` y `P3 CI` sobre `3e423c4`). Repite los
recálculos de la pasada preliminar (mismos resultados) y agrega la verificación
de S3, la recarga del modelo y las mutaciones.

**Límite de esta pasada:** el stack no se levantó aquí. M1 y el recorrido de las
5 páginas (recargar durante un trabajo, cambiar de versión, archivo inválido,
envío a la cola) se confirman en el ensayo de la demo ([demo.md](demo.md)); las
puntuaciones de 6.x se basan en el código, las pruebas de componente en CI y la
verificación contra el backend real que registra cada fase.

### A. Requisitos mínimos

| Estado | Requisito | Evidencia |
|---|---|---|
| NO CUMPLE | M1 Arranque desde el README | Con el stack levantado sobre `3e423c4` (Edith, 1 oct), **Training sale en blanco** con el registro real (0.1.1 sin `archive_sha256`). Además, con el orden del README MLflow no cargaba las 12 corridas. Lo corrigen #23, #25 y #26. |
| CUMPLE | M2 Release aprobado y versionado | `0.1.3` (`pass`) → `Proyecto2/data/raw.dvc` md5 `ca56420c…` → `p3.data.releases.open_release_archive` (SHA-256 `787742988af1…` y huella `2200274d…`) → `manifest.meta.json` con `dvc_pointer`; cada corrida guarda `release_id`, `release_hash` y `dvc_md5` |
| CUMPLE | M3 Aislamiento | Recalculado: 0 en las 9 intersecciones (`crop_id`, `source_image_id`, `dup_group_id`); aumentación solo en train (`src/p3/data/transforms.py`); `selection.json` (`6bd9101`, 26 sep) antes de la evaluación (28 sep) |
| CUMPLE | M4 Modelo recargable | `get-object` de `models/clasificador/1.0.0/model.pt` → SHA-256 `e4acca42…` = registro = `selection.json`; cargado en un proceso nuevo con su mapa de clases y preprocesamiento: `0.1.3:a1057` → person 0.997828 y `0.1.3:a1574` → dog 0.676567, iguales a `predictions_test.csv` |

**Compuerta:** ACTIVADA (máximo 60).

### B. Tabla de calificación

| Puntos | Requisito | Lo que falta |
|---|---|---|
| 3.5 / 4 | 1.1 Traspaso desde P2 | En el portal solo 0.1.3 tiene manifiesto congelado: elegir otro release aprobado responde 409, así que el cambio de conteos se demuestra con `tests/test_releases.py::test_cambiar_de_release_cambia_los_conteos`, no en la UI. |
| 5 / 5 | 1.2 Recortes y clases | — |
| 5 / 5 | 1.3 Manifiesto 70/20/10 | — |
| **13.5 / 14** | **Subtotal Integración y datos** | |
| 5 / 5 | 2.1 Clasificador entrenado | — |
| 2 / 4 | 2.2 Minibatches y parámetros | Por API el valor inválido se rechaza con 422 (pruebas de `TrainingConfig`). **Por portal no hay evidencia:** Training no carga en este commit. |
| 4 / 4 | 2.3 Semillas y aumentación | — |
| 5 / 5 | 2.4 Curvas y early stopping | — |
| **16 / 18** | **Subtotal Modelo** | |
| 6 / 6 | 3.1 Diez experimentos | — (12 válidas, tabla abajo) |
| 5 / 5 | 3.2 Registro en MLflow | — |
| 3 / 3 | 3.3 Comparación y elección | — |
| **14 / 14** | **Subtotal Experimentos** | |
| 5 / 5 | 4.1 Protocolo congelado | — |
| 4 / 4 | 4.2 Matriz y métricas | — (recalculadas desde `predictions_test.csv`; iguales en `metrics.json`, MLflow, API y página Evaluation) |
| 6 / 6 | 4.3 Umbral de 85 % | — (142/145 = 0.97931) |
| 2 / 3 | 4.4 Errores | La galería de Evaluation lista aciertos y errores del test sin la **imagen del recorte** (el backend no la sirve) y la página no muestra la **clase más confundida**, aunque viene en la respuesta (`most_confused`: cat→dog, 2). Ambas cosas están en [analisis_errores.md](analisis_errores.md). |
| **17 / 18** | **Subtotal Evaluación** | |
| 4 / 4 | 5.1 Paquete | — |
| 4 / 4 | 5.2 S3 real | — (`head-object` y `get-object` de pesos y tarjeta, `VersionId` y SHA-256 local, inferencia en proceso nuevo) |
| 1 / 2 | 5.3 Registro navegable | `GET /api/p3/models` resuelve 1.0.0 y 0.9.0 con run, release y SHA-256, y las dos versiones dan probabilidades distintas en un venv limpio (`publicacion_s3.md`). **Falta evidencia de que activar desde Models cambia el artefacto que carga Inference.** Probarlo escribe `registry.json` en el bucket de producción: hacerlo una sola vez en el ensayo, volviendo a 1.0.0, y anotarlo. |
| **9 / 10** | **Subtotal S3** | |
| 0 / 4 | 6.1 Training | **La página sale en blanco** con el registro real (Edith, stack sobre `3e423c4`). |
| 0 / 3 | 6.2 Experiments | Sin evidencia con el stack en esta pasada. |
| 0 / 3 | 6.3 Evaluation | Sin evidencia con el stack en esta pasada (hay pruebas de componente en CI). |
| 0 / 4 | 6.4 Models | Sin evidencia con el stack en esta pasada. Además falta una **acción de descarga** del modelo. |
| 0 / 4 | 6.5 Inference | Sin evidencia con el stack en esta pasada (el backend tiene la verificación 145/145 de F4 T24). |
| **0 / 18** | **Subtotal Portal** | |
| 4 / 4 | 7.1 Pruebas y TDD | — (dos mutaciones en copia aislada hacen fallar la suite; ver G) |
| 1.5 / 2 | 7.2 Integración | `tests/test_e2e.py` escribe `registry.json` a mano en vez de usar `p3.registry.publish` y no pasa por la API del portal. |
| 2 / 2 | 7.3 CI y secretos | — |
| **7.5 / 8** | **Subtotal Pruebas** | |

### C. Trazabilidad de extremo a extremo

| Release DVC y hash | Manifiesto 70/20/10 y hash | Run MLflow elegido | Checkpoint | Versión de modelo | S3 bucket/key y hash | Predicción de prueba |
|---|---|---|---|---|---|---|
| `0.1.3`, huella `2200274d…`, `raw.dvc` md5 `ca56420c…` | `m-0.1.3-s42-1`, `45600f29…` | `9f9b62c202f0446a8a4b411a10321eff` | SHA-256 `e4acca42…` | `1.0.0` | `dataset-quality-releases-750702272375/models/clasificador/1.0.0/model.pt`, `VersionId` `VtRww5se…`, SHA-256 `e4acca42…` | `0.1.3:a1574` → dog 0.676567 (= `predictions_test.csv`); 145/145 por el portal (F4 T24) |

Detalle completo en [trazabilidad.md](trazabilidad.md).

### D. Contraste de métricas

| Métrica | Reportado por el equipo | Verificado | ¿Coincide? |
|---|---:|---:|---|
| Corridas válidas de MLflow | 12 | 12 (14 − 2 `FAILED`) | Sí |
| Train / val / test (recortes) | 1022 / 292 / 145 | 1022 / 292 / 145 | Sí |
| Train / val / test (originales) | 763 / 229 / 109 | 763 / 229 / 109 | Sí |
| Accuracy top-1 en test | 0.9793 | 142/145 = 0.979310 | Sí |
| F1 macro en test | 0.9744 | 0.974352 | Sí |
| Total de la matriz de confusión | 145 | 145 | Sí |

Las 12 corridas válidas (experimento `p3-clasificador`, manifiesto `45600f29…`, commit `250bedc`):

| Run | Optimizador | Batch | Épocas máx. | LR | Imagen | Capas ocultas | Dropout | Mejor val_acc | val_loss | Época | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `c15c8edf` | adamw | 32 | 30 | 0.0003 | 224 | [256] | 0.3 | 0.9726 | 0.0745 | 5 | FINISHED |
| `eab49735` | adamw | 64 | 30 | 0.001 | 224 | [512, 128] | 0.5 | 0.9384 | 0.1641 | 7 | FINISHED |
| `46cb41fb` | adam | 64 | 30 | 0.0003 | 128 | [] | 0.2 | 0.9829 | 0.0331 | 11 | FINISHED |
| `ba8aac02` | sgd | 64 | 15 | 0.003 | 128 | [512, 128] | 0.2 | 0.9897 | 0.0473 | 6 | FINISHED |
| `cb72f7db` | adamw | 32 | 15 | 0.0003 | 128 | [512, 128] | 0.5 | 0.9623 | 0.1078 | 3 | FINISHED |
| `5ebc2c9f` | sgd | 32 | 30 | 0.001 | 224 | [] | 0.3 | 0.9966 | 0.0435 | 3 | FINISHED |
| `76dc45e2` | adam | 32 | 30 | 0.001 | 224 | [512, 128] | 0.3 | 0.9418 | 0.1702 | 7 | FINISHED |
| `9f9b62c2` **(seleccionada)** | adamw | 64 | 15 | 0.0001 | 224 | [] | 0.5 | 0.9966 | 0.0243 | 6 | FINISHED |
| `75d6bbb9` | sgd | 64 | 30 | 0.01 | 128 | [256] | 0.3 | 0.9760 | 0.1131 | 4 | FINISHED |
| `26afad93` | adamw | 32 | 30 | 0.0001 | 160 | [256] | 0.2 | 0.9897 | 0.0412 | 2 | FINISHED |
| `16c09c8e` | adam | 32 | 15 | 0.0001 | 224 | [256] | 0.2 | 0.9932 | 0.0292 | 7 | FINISHED |
| `981df1d9` | sgd | 32 | 30 | 0.01 | 224 | [256] | 0.5 | 0.9760 | 0.0724 | 5 | FINISHED |

### E. Resultado final

```text
Suma de secciones:      77 / 100   (solo lo que tiene evidencia)
Compuerta aplicada:     sí (M1 no cumple)
CALIFICACIÓN FINAL:     60
Meta de 85% en test:    alcanzada (0.979310)
Escala:                 Suficiente (60-74)
```

### F. Comentario para el equipo

Aciertos: (1) la cadena release → manifiesto → run → checkpoint → S3 → predicción se sostiene con hashes en cada eslabón y se reproduce desde datos primarios; (2) aislamiento demostrado (0 en las 9 intersecciones) y test abierto una sola vez después de `selection.json`; (3) 12 corridas válidas que varían los 7 parámetros, todas trazables en MLflow.

Pérdidas: (1) **M1: Training en blanco → compuerta, máximo 60** (lo corrigen #23, #25 y #26); (2) **sección 6 sin evidencia con el stack** (−18); (3) 2.2 por portal y 5.3 sin evidencia (−3); (4) imagen del recorte y clase más confundida en Evaluation (4.4, −1); (5) la E2E no usa `p3.registry.publish` (7.2, −0.5); (6) en el portal no se ve que cambiar de release cambie los conteos (1.1, −0.5).

### G. Anexo de verificación

| Acción | Resultado |
|---|---|
| `ruff check .` / `ruff format --check .` (Proyecto3) | sin hallazgos / 127 archivos formateados |
| `pytest` (Proyecto3 y Proyecto2) | todo en verde |
| Pruebas del portal (`npm run test:unit`) | no se corrieron localmente (sin `node_modules`); en verde en la CI de `main` (`3e423c4`) |
| Intersecciones del manifiesto | 0 en las 9 |
| Recálculo de la matriz desde `predictions_test.csv` | `[[30,2,0],[0,38,0],[0,1,74]]`, 142/145 |
| `aws s3api head-object` y `get-object` (solo lectura, perfil del equipo) | `model.pt` `VtRww5se…` 44 783 563 bytes, SHA-256 `e4acca42…`; `MODEL_CARD.md` `7LNRNnVo…`, menciona el run `9f9b62c2…` |
| Carga del modelo en un proceso nuevo | iguales a `predictions_test.csv` en los dos recortes probados |
| Mutación: matriz con filas y columnas invertidas (`metrics.py`) | 3 pruebas fallan en `tests/test_metrics.py` |
| Mutación: los casi duplicados dejan de agruparse (`split.py`) | 3 pruebas fallan en `tests/test_split.py` |
| Estado de la copia | mutaciones en una copia aislada de `main`, restauradas y eliminadas; `git status` limpio |

**No verificado en esta pasada:** el arranque con `up.py` y el recorrido de las 5 páginas con el stack, y el escaneo de secretos sobre el historial (la CI corre gitleaks sobre el árbol). **Por eso esta pasada no puede dar puntos a M1 ni a la sección 6.**

## Pasada válida (pendiente)

Después de integrar #23, #25 y #26 en `fix/m1-training`, en una copia limpia y **con el stack levantado** siguiendo el README: arranque (M1), las 5 páginas (recargar durante un trabajo, archivo inválido, envío a la cola), el valor inválido por el portal (2.2), y cambiar de versión en Models comprobando el `model_sha256` de una predicción (5.3, una sola escritura en `registry.json` y vuelta a 1.0.0). Solo se puntúa lo que se observe.
