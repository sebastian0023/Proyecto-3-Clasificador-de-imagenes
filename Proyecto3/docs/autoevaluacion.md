# Autoevaluación con el prompt de la rúbrica (F11 T29)

## Pasada preliminar — 30 sep 2026, sobre `main` en `f7b5c47`

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

## Pasada final

Pendiente: sobre el commit candidato, en una copia limpia, siguiendo `docs/rubrica.md` completo (Fases 0–4, con el reporte HTML).
