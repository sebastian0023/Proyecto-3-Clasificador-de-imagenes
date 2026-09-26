# Contratos entre módulos — Proyecto 3

Esquemas congelados que permiten que datos (Diego), entrenamiento (Edith) y portal (Andrés) avancen en paralelo. **Cualquier cambio de forma** (agregar, quitar o renombrar un campo, cambiar un rango o un código de respuesta) va explícito en el PR y se avisa al equipo (regla 11 de `AGENTS.md`).

Estado de cada pieza: **implementado** (existe en `main` con pruebas) o **contrato** (lo implementa la fase indicada).

## 0. Convenciones

- JSON en UTF-8 con finales de línea LF. Fechas en ISO 8601 UTC (`2026-09-24T22:29:34Z`).
- **Hash canónico:** SHA-256 del JSON serializado con claves ordenadas y sin espacios (`json.dumps(obj, sort_keys=True, separators=(",", ":"))`). Para el manifiesto, de sus filas ordenadas por `crop_id`, una por línea, cada línea terminada en `\n`.
- Toda la validación de entrada usa Pydantic v2 con `extra="forbid"`. Un error responde **422** con el formato de FastAPI, que nombra el campo en `loc`:

  ```json
  {"detail": [{"type": "less_than_equal", "loc": ["body", "config", "dropout"], "msg": "Input should be less than or equal to 0.9", "input": 1.5}]}
  ```

- Los demás errores responden `{"detail": "<mensaje en español>"}` con el código indicado en cada endpoint.
- Rutas bajo `/api/p3/`, servidas por la app de Proyecto2 (`http://localhost:8000`).
- Los valores de los ejemplos son ilustrativos, salvo los hashes del release 0.1.3 y los ids del fixture.

## 1. Mapa de clases

Fijado en [decisiones.md §2](decisiones.md#2-clases-incluidas-y-exclusiones). El `class_index` es el orden alfabético del nombre y es el índice de la salida del modelo:

| `class_index` | `category_name` | `category_id` (COCO del release) |
|---:|---|---:|
| 0 | cat | 4 |
| 1 | dog | 3 |
| 2 | person | 2 |

## 2. Manifiesto de recortes 70/20/10 — contrato (F2, F3)

Un manifiesto se deriva de **un** release aprobado y no se sobrescribe: cada generación produce un `manifest_id` nuevo. Se guarda como dos archivos versionados con DVC:

### `manifest.jsonl`: una fila por recorte

| Campo | Tipo | Regla |
|---|---|---|
| `crop_id` | string | `"<release_id>:a<annotation_id>"`, p. ej. `"0.1.3:a1234"`. Único y estable entre generaciones. |
| `source_image_id` | int | `id` de la imagen en el COCO del release |
| `source_file_name` | string | `file_name` de la imagen en el COCO |
| `annotation_id` | int | `id` de la anotación de la que sale el recorte |
| `category_id` | int | categoría COCO de la caja |
| `category_name` | string | nombre de la categoría |
| `class_index` | int | según la sección 1 |
| `bbox_xywh` | [float, float, float, float] | caja **original** del COCO, en píxeles, sin redondear |
| `dup_group_id` | string | `"g<menor image_id del grupo>"`; grupos por pHash con distancia ≤ `duplicates.phash_hamming_distance` de `Proyecto2/quality.yaml` (5), con el mismo criterio que `dataset_quality.analyzers.duplicates.duplicate_groups` de P2. Una imagen sin duplicados forma su propio grupo. |
| `split` | `"train"` \| `"val"` \| `"test"` | la unidad que se asigna es el **grupo de duplicados**: todos sus recortes van a la misma partición |
| `release_id` | string | versión del release, p. ej. `"0.1.3"` |
| `release_hash` | string | `dataset_fingerprint` del release |

```json
{"annotation_id":1234,"bbox_xywh":[461.0,346.0,300.0,200.0],"category_id":3,"category_name":"dog","class_index":1,"crop_id":"0.1.3:a1234","dup_group_id":"g1187","release_hash":"2200274dc6bbe6d0bc516e0136ae68651c0040bc6cab64a871794924fa39aa84","release_id":"0.1.3","source_file_name":"img_auto_1187.jpg","source_image_id":1187,"split":"train"}
```

### `manifest.meta.json`: procedencia y conteos

```json
{
  "schema_version": 1,
  "manifest_id": "m-0.1.3-s42-1",
  "manifest_hash": "<sha256 canónico de manifest.jsonl>",
  "created_at": "2026-09-25T18:00:00Z",
  "code_commit": "<git rev-parse HEAD>",
  "release": {
    "release_id": "0.1.3",
    "dataset_fingerprint": "2200274dc6bbe6d0bc516e0136ae68651c0040bc6cab64a871794924fa39aa84",
    "quality_status": "pass",
    "quality_report_fingerprint": "4d6e64aa13c6f66b15801811c4bb84ebc265b07f538ae27982f79628b170631a",
    "archive_sha256": "787742988af1df41d9a58573b81b5c9b4fe7ab24a647b25f2e71d3eb323838b5",
    "p2_splits_fingerprint": "9a87e0de3fb3069f06686065f149d64787593c04d90265a3e0f667a170d66279"
  },
  "seed": 42,
  "ratios": {"train": 0.7, "val": 0.2, "test": 0.1},
  "tolerance_pp": 5,
  "classes": [
    {"class_index": 0, "category_id": 4, "category_name": "cat"},
    {"class_index": 1, "category_id": 3, "category_name": "dog"},
    {"class_index": 2, "category_id": 2, "category_name": "person"}
  ],
  "excluded_categories": [{"category_id": 1, "category_name": "car"}, {"category_id": 5, "category_name": "bicycle"}],
  "exclusions": [
    {"annotation_id": 77, "source_image_id": 40, "reason": "degenerate_bbox"},
    {"annotation_id": 91, "source_image_id": 52, "reason": "bbox_out_of_bounds"},
    {"annotation_id": 12, "source_image_id": 9, "reason": "missing_image"},
    {"annotation_id": 5, "source_image_id": 3, "reason": "excluded_category"}
  ],
  "counts": {
    "crops": {"train": {"cat": 0, "dog": 0, "person": 0}, "val": {"cat": 0, "dog": 0, "person": 0}, "test": {"cat": 0, "dog": 0, "person": 0}},
    "originals": {"train": {"cat": 0, "dog": 0, "person": 0}, "val": {"cat": 0, "dog": 0, "person": 0}, "test": {"cat": 0, "dog": 0, "person": 0}}
  }
}
```

`reason` ∈ `degenerate_bbox` (ancho o alto ≤ 0), `bbox_out_of_bounds` (la caja sale de la imagen, en coordenadas del COCO), `missing_image` (el archivo no existe o no se puede abrir), `excluded_category`, `size_mismatch` (la proporción del archivo difiere más de 10 % de la del COCO).

**Coordenadas de las cajas (cambio F2, revisión del PR #3).** Las cajas se dibujaron en P1 sobre la foto que mostraba el navegador: con la rotación EXIF aplicada y con el `width`/`height` del COCO. Por eso:

- los límites se revisan contra el tamaño del COCO; si la foto gira por EXIF (orientación 5–8) y el COCO guarda el tamaño de la cabecera sin girar, ese tamaño se intercambia;
- para recortar, la foto se abre con la rotación EXIF aplicada y la caja se escala por eje al tamaño real del archivo (`pixel_scale` en `crops.jsonl`);
- `bbox_xywh` del manifiesto sigue siendo la caja **original del COCO**, sin escalar.

Nuevo motivo `size_mismatch` (aditivo). En el release 0.1.3 ninguna caja lo usa: la mayor deformación es de 5.7 % (imagen 8).

### Invariantes (las prueba F3)

1. Ningún `source_image_id` ni `dup_group_id` aparece en dos particiones.
2. La proporción de recortes por partición queda a ±5 puntos porcentuales de 70/20/10.
3. Cada clase tiene al menos un recorte en `val` y en `test`.
4. Misma semilla y mismo release → mismos `crop_id` en cada partición y mismo `manifest_hash`.
5. La aumentación nunca produce filas: se aplica en memoria y solo a `train`.

## 3. `TrainingConfig` — contrato (F4)

Todos los campos son obligatorios, salvo los que tienen valor por defecto. Un valor fuera de rango se rechaza con 422 **antes** de crear el trabajo, por API y por portal (criterio 2.2).

| Campo | Tipo | Rango válido | Por defecto |
|---|---|---|---|
| `optimizer` | string | `sgd` \| `adam` \| `adamw` | — |
| `batch_size` | int | 1 – 256 | — |
| `max_epochs` | int | 1 – 200 | — |
| `learning_rate` | float | > 0 y ≤ 1 | — |
| `image_size` | int | 32 – 512, múltiplo de 32 | — |
| `hidden_layers` | list[int] | 0 a 4 elementos, cada uno 8 – 4096 (`[]` = capa lineal directa) | — |
| `dropout` | float | 0 – 0.9 | — |
| `seed` | int | 0 – 2³²−1 | 42 |
| `patience` | int | 1 – 50 | 5 |
| `min_delta` | float | 0 – 0.1 | 0.001 |
| `monitor_metric` | string | `val_accuracy` \| `val_loss` | `val_accuracy` |

```json
{"optimizer": "adamw", "batch_size": 32, "max_epochs": 30, "learning_rate": 0.0003, "image_size": 224, "hidden_layers": [256], "dropout": 0.3, "seed": 42, "patience": 5, "min_delta": 0.001, "monitor_metric": "val_accuracy"}
```

## 4. API REST

| Método y ruta | Responde | Estado |
|---|---|---|
| `GET /api/p3/releases?approved=true` | releases de P2 | **implementado** (F2 T05) |
| `GET /api/p3/releases/{release_id}` | procedencia de un release aprobado | **implementado** (F2 T05) |
| `POST /api/p3/manifests` | genera un manifiesto | contrato (F3) |
| `GET /api/p3/manifests/{manifest_id}` | meta de un manifiesto | contrato (F3) |
| `POST /api/p3/training/jobs` | encola un trabajo | **implementado** para `kind: "dummy"` (T02); `kind: "train"` en F4 |
| `GET /api/p3/training/jobs/{job_id}` | estado, progreso, logs y error | **implementado** (T02); `mlflow_run_id` en F4 |
| `GET /api/p3/runs` | corridas de MLflow | contrato (F5) |
| `GET /api/p3/runs/{run_id}` | una corrida con curvas | contrato (F5) |
| `POST /api/p3/selection` | fija el candidato | contrato (F5) |
| `GET /api/p3/evaluation` | evaluación final en test | contrato (F6) |
| `GET /api/p3/models` | versiones de modelo | contrato (F7) |
| `POST /api/p3/models/{version}/activate` | elige la versión para inferencia | contrato (F7) |
| `POST /api/p3/inference` | predice una imagen | contrato (F4, F9) |
| `POST /api/p3/inference/{inference_id}/send-to-annotation` | crea el elemento en la cola de anotación | contrato (F9) |

### `GET /api/p3/releases?approved=true`

Lee `Proyecto2/reports/versions.json`. Con `approved=true` solo devuelve `quality_status: "pass"`.

```json
{"releases": [{"release_id": "0.1.3", "dataset_fingerprint": "2200274d…", "quality_status": "pass", "created_at": "2026-09-18T04:17:13Z", "counts": {"images": 2045, "annotations": 2120, "categories": 5}, "storage_uri": "s3://dataset-quality-releases-750702272375/0.1.3/dataset.tar.zst", "published_in": ["dev", "prod"]}]}
```

- **Cambio F2 T05 (aditivo):** campo `published_in`, con los remotes donde P2 publicó el release.
- `storage_uri` se arma con el bucket configurado (`P3_RELEASES_BUCKET`) si el release está en el remote `prod` (`P3_RELEASES_REMOTE`); si no, es `null`: el release solo existe en el MinIO local de quien lo generó y no se recupera desde un clon limpio. No se usa la URI que guarda P2, porque la del 0.1.3 apunta al bucket de la cuenta anterior ([decisiones.md §1](decisiones.md#1-release-dvc-de-origen)).
- Sin `approved` (o con `approved=false`) devuelve todos, incluidos los de compuerta fallida.

### `GET /api/p3/releases/{release_id}` (nuevo en F2 T05)

Procedencia de un release para la vista de Training. **200** con los campos de la lista más `quality_report_fingerprint` y `archive_sha256`; **409** si la compuerta no pasó (`{"detail": "El release 0.1.0 no paso la compuerta de calidad (quality_status=fail); …"}`); **404** si no existe. `POST /api/p3/manifests` (F3) usa la misma regla.

Leer el COCO del release (`p3.data.releases.open_release_archive`) exige que el SHA-256 del `dataset.tar.zst` sea el `archive_sha256` registrado y que la huella de P2 del COCO sea el `dataset_fingerprint`; si no, `ReleaseIntegrityError`.

### `POST /api/p3/manifests`

```json
// request
{"release_id": "0.1.3", "seed": 42}
// 201
{"manifest_id": "m-0.1.3-s42-1", "manifest_hash": "…", "counts": {"…": "igual que manifest.meta.json"}}
```

- **409** si el release no tiene `quality_status: "pass"`.
- **404** si el release no existe.

### `GET /api/p3/manifests/{manifest_id}`

**200** con el contenido de `manifest.meta.json`, o **404**.

### `POST /api/p3/training/jobs`

```json
// request (F4)
{"kind": "train", "manifest_id": "m-0.1.3-s42-1", "config": {"…": "TrainingConfig"}}
// request (T02, disponible hoy)
{"kind": "dummy", "config": {"steps": 5, "seconds": 1, "fail": false}}
// 202
{"job_id": "02b40a98db684455b93dce8c89c107ee", "status": "queued"}
```

- **422** si `kind`, `config` o un campo extra no son válidos.
- **409** (F4) si el manifiesto no existe, su release no está aprobado o su test se mezcla con train o val.

### `GET /api/p3/training/jobs/{job_id}`

```json
{
  "job_id": "02b40a98db684455b93dce8c89c107ee",
  "kind": "dummy",
  "status": "succeeded",
  "progress": 1.0,
  "config": {"steps": 4, "seconds": 2},
  "logs": ["2026-09-25T04:54:54+00:00 encolado (dummy)", "…", "2026-09-25T04:55:03+00:00 terminado"],
  "error": null,
  "worker_id": "bd1a1827e2a6",
  "created_at": "2026-09-25T04:54:54",
  "started_at": "2026-09-25T04:54:55",
  "finished_at": "2026-09-25T04:55:03"
}
```

- `status` ∈ `queued`, `running`, `succeeded`, `failed`.
- En F4 se agrega `mlflow_run_id` (string o `null`).
- **404** si el trabajo no existe.

### `GET /api/p3/runs` y `GET /api/p3/runs/{run_id}`

`GET /api/p3/runs` acepta `?manifest_id=&status=FINISHED&order_by=val_accuracy&desc=true`.

```json
{"runs": [{"run_id": "01b222d3…", "status": "FINISHED", "manifest_id": "m-0.1.3-s42-1", "params": {"…": "TrainingConfig efectiva"}, "best_epoch": 12, "stopped_epoch": 17, "best_val_accuracy": 0.9, "best_val_loss": 0.31, "commit": "…", "start_time": "…", "end_time": "…"}]}
```

`GET /api/p3/runs/{run_id}` devuelve lo mismo más `history` (por época: `train_loss`, `train_accuracy`, `val_loss`, `val_accuracy`) y `artifacts` (rutas de curvas y checkpoint). **404** si el run no existe.

### `POST /api/p3/selection`

Aplica la regla de [decisiones.md §4](decisiones.md#4-métrica-de-selección-del-candidato) y escribe `selection.json` (sección 5).

- Request: `{"manifest_id": "m-0.1.3-s42-1"}`.
- **201** con el contenido de `selection.json`.
- **409** si hay menos de 10 corridas `FINISHED` sobre ese manifiesto, o si ya existe una selección para él.

### `GET /api/p3/evaluation`

- **409** `{"detail": "La selección del modelo no está cerrada"}` mientras no exista `selection.json` commiteado. El test no se revela antes (criterio 6.3).
- Después:

```json
{"run_id": "…", "manifest_id": "…", "test_size": 0, "accuracy": 0.0, "f1_macro": 0.0, "per_class": [{"class": "cat", "precision": 0.0, "recall": 0.0, "support": 0}], "confusion_matrix": {"labels": ["cat", "dog", "person"], "rows_true_cols_pred": [[0, 0, 0], [0, 0, 0], [0, 0, 0]]}, "majority_baseline": 0.0, "predictions_uri": "…/predictions.jsonl"}
```

### `GET /api/p3/models` y `POST /api/p3/models/{version}/activate`

```json
{"active_version": "1.0.0", "models": [{"version": "1.0.0", "run_id": "…", "manifest_id": "…", "release_id": "0.1.3", "s3": {"uri": "s3://…/models/clasificador/1.0.0/model.pt", "version_id": "…", "sha256": "…", "exists": true}, "card_uri": "…/MODEL_CARD.md"}]}
```

`activate` responde **200** con `{"active_version": "1.0.0"}`, o **409** si el objeto de S3 no existe o su SHA-256 no coincide.

### `POST /api/p3/inference`

- Request: `multipart/form-data` con `file` (JPEG o PNG de hasta 10 MB) y, opcionalmente, `bbox_xywh` para recortar antes de predecir.
- Responde **200**:

```json
{"inference_id": "…", "model_version": "1.0.0", "predicted_class": "dog", "probabilities": {"cat": 0.05, "dog": 0.9, "person": 0.05}}
```

- Las probabilidades suman 1 (±1e-6).
- **415** si el tipo no es válido; **413** si el archivo pasa de 10 MB; **409** si no hay una versión activa.

### `POST /api/p3/inference/{inference_id}/send-to-annotation`

- **201** `{"annotation_queue_item": {"image_id": 0, "status": "pending"}}`: crea la imagen en el flujo de P1 (`POST /api/images/upload`).
- **404** si la inferencia no existe.

## 5. `selection.json` — contrato (F5)

Se commitea **antes** de correr la evaluación final (regla 8 de `AGENTS.md`).

```json
{
  "schema_version": 1,
  "selected_at": "2026-09-29T18:00:00Z",
  "manifest_id": "m-0.1.3-s42-1",
  "manifest_hash": "…",
  "rule": "max val_accuracy; desempate min val_loss; luego end_time mas temprano",
  "candidates": 10,
  "run_id": "…",
  "checkpoint_uri": "mlflow-artifacts:/…/checkpoints/best.pt",
  "checkpoint_sha256": "…",
  "best_epoch": 12,
  "val_accuracy": 0.9,
  "val_loss": 0.31
}
```

## 6. Versión de modelo — contrato (F7)

Carpeta `s3://dataset-quality-releases-750702272375/models/clasificador/<version>/` con `model.pt`, `class_map.json` (sección 1), `preprocessing.json`, `config.json` (TrainingConfig y arquitectura), `requirements.lock.txt`, `MODEL_CARD.md` y `model_version.json`:

```json
{
  "schema_version": 1,
  "version": "1.0.0",
  "architecture": "resnet18",
  "pretrained_weights": "torchvision ResNet18_Weights.IMAGENET1K_V1",
  "run_id": "…",
  "manifest_id": "m-0.1.3-s42-1",
  "release_id": "0.1.3",
  "selection_sha256": "<sha256 de selection.json>",
  "test_metrics": {"accuracy": 0.0, "f1_macro": 0.0},
  "preprocessing": {"image_size": 224, "resize": "shorter_side_then_center_crop", "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
  "files": {"model.pt": {"sha256": "…", "s3_version_id": "…"}},
  "created_at": "…"
}
```

La versión es semántica y propia del modelo; no se confunde con la versión del dataset (`release_id`).

## 7. Fixture de pruebas — implementado

[`tests/fixtures/p3/`](../tests/fixtures/p3/) contiene un COCO de 3 clases (ids reales: 2 `person`, 3 `dog`, 4 `cat`) y 30 imágenes sintéticas de 128×96, donde cada clase es una figura distinta (elipse, rectángulo, triángulo). Tiene a propósito un caso de cada tipo:

| Caso | Dónde |
|---|---|
| Imagen con dos clases (dos recortes de un original) | imagen 28 |
| Casi duplicados (pHash a distancia 2; el resto a ≥ 22) | imágenes 25 y 26 |
| Imagen que falta en disco | imagen 27 |
| Caja degenerada (ancho 0) | imagen 29 |
| Caja fuera de la imagen | imagen 30 |

Recortes válidos: 10 `cat`, 9 `dog`, 9 `person`. `tests/test_fixture_p3.py` protege estas propiedades.
