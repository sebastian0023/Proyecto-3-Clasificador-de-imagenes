# Guion de la demo (F11 T33)

Objetivo: seguir **un mismo trabajo** desde la versión del dataset hasta una
predicción en el portal, con los mismos IDs de punta a punta
([trazabilidad.md](trazabilidad.md)). Cada integrante explica su tramo y responde
"¿de dónde sale este número?".

**Duración objetivo:** 15 minutos (el cronómetro va en la tabla del ensayo, al final).

## Antes de empezar (10 min antes, una sola persona)

Mismo orden que el [README](../../README.md), con un perfil de AWS autorizado en `~/.aws`:

```bash
cd Proyecto2
python scripts/up.py                                    # primer arranque: app :8000, MLflow :5000, MinIO, MariaDB, worker, inference
.venv/Scripts/dvc remote modify --local prod profile <perfil>
.venv/Scripts/dvc pull -r prod data/raw.dvc             # imágenes del release 0.1.3
cd ../Proyecto3
../Proyecto2/.venv/Scripts/dvc remote modify --local prod profile <perfil>
../Proyecto2/.venv/Scripts/dvc pull data/manifests/m-0.1.3-s42-1.dvc mlflow_snapshot.dvc
cd ../Proyecto2
PYTHONPATH="../Proyecto3/src;src" .venv/Scripts/python ../Proyecto3/scripts/generate_crops.py --release 0.1.3 --profile <perfil>
python scripts/up.py                                    # otra vez: carga las 12 corridas en MLflow y reinicia MLflow
cd ../Proyecto1 && npm run up                           # cola de anotación en :3000 (tramo 7)
```

Sin los recortes, el trabajo del tramo 3 falla. Comprobar en `http://localhost:5000` que `p3-clasificador` tiene sus 12 corridas antes de empezar.

- `.env` con `P3_AWS_PROFILE=<perfil>` y `P3_AWS_DIR` apuntando a `~/.aws`, para que `p3-inference` lea el modelo de S3.
- Pestañas abiertas: portal `http://localhost:8000`, MLflow `http://localhost:5000`, P1 `http://localhost:3000`.
- Una foto de un perro que **no** esté en el dataset y un archivo inválido (`notas.txt`).

## Tramos

### 1. Dataset y compuerta de calidad — Diego (2 min)

- Portal → **Training** → selector de release: solo aparece lo aprobado. Elegir **0.1.3**.
- Mostrar la procedencia: huella `2200274d…`, compuerta `pass`, reporte de calidad `4d6e64aa…`.
- **¿De dónde sale?** `Proyecto2/reports/versions.json` (lo escribe `dq release`). El archivo en S3 se verifica por SHA-256 (`787742988af1…`) y su COCO por la huella de P2 antes de usarlo. 0.1.0 no pasa la compuerta y no aparece. Los aprobados que no se pueden entrenar aparecen deshabilitados con su motivo (`GET /api/p3/releases`: `trainable` y `blocked_reason`): 0.1.1 "no registra archive_sha256"; 0.1.2, 0.1.4 y 0.1.5 "sin manifiesto congelado". Solo 0.1.3 queda seleccionable.

### 2. Recortes y manifiesto 70/20/10 — Diego (2 min)

- En Training, **Generar manifiesto**: responde `m-0.1.3-s42-1` con su tabla por clase y partición.
- Cifras: 1459 recortes de 1101 originales; train 1022 / val 292 / test 145.
- **¿De dónde sale?** `manifest.meta.json` del manifiesto congelado (tag `p3-manifiesto-congelado`, SHA-256 `45600f29…`). El botón no crea uno nuevo: devuelve el congelado tras comprobar sus bytes. La misma semilla da el mismo archivo byte a byte, y ningún recorte, original ni grupo de casi duplicados cae en dos particiones ([manifiesto.md](manifiesto.md)).

### 3. Entrenamiento — Edith (3 min)

- En Training, mostrar el formulario (7 parámetros + seed, patience, min_delta) y un valor inválido rechazado antes de crear el trabajo (422).
- Lanzar el **trabajo corto del README** y **recargar la página**: el estado, el progreso y los logs siguen ahí.

  | experiment | optimizer | batch_size | max_epochs | learning_rate | image_size | hidden_layers | dropout | seed |
  |---|---|---|---|---|---|---|---|---|
  | `p3-pruebas` | `adamw` | 64 | 1 | 0.001 | 64 | 128 | 0.2 | 42 |

  En CPU tarda ~30 s (medido por Edith: 28 s). La corrida queda en `p3-pruebas`; `p3-clasificador` conserva sus 12 corridas.
- **¿De dónde sale?** El worker lee el manifiesto congelado por su id y solo acepta los de `p3.data.frozen`. Cada corrida registra en MLflow el commit, el manifiesto, el release y el entorno.

### 4. Experimentos y selección — Edith (2 min)

- Portal → **Experiments**: las corridas del barrido ordenadas por `val_accuracy`, el candidato marcado y ninguna métrica de test.
- Abrir r10 (`9f9b62c2…`): curvas train/val y enlace al mismo run en MLflow.
- **¿De dónde sale?** Regla de [decisiones.md §4](decisiones.md#4-métrica-de-selección-del-candidato): máx `val_accuracy` (0.99658), desempate por mín `val_loss` (0.02425; r08 empató en accuracy y perdió aquí). Queda en [selection.json](selection.json) con el SHA-256 del checkpoint `e4acca42…`.

### 5. Evaluación en test — Diego (2 min)

- Portal → **Evaluation**: matriz de confusión, F1 por clase y baseline.
- Cifras: 142/145 (accuracy 0.9793), F1 macro 0.9744, baseline de la clase mayoritaria 0.5172; la confusión más frecuente es cat→dog (2).
- **¿De dónde sale?** Una sola evaluación del checkpoint `e4acca42…` sobre las 145 imágenes de test, después de cerrar la selección (`scripts/final_evaluation.py`, commit `a7ec1dc`). Métricas calculadas a mano, sin librerías, y guardadas como artefactos del mismo run en MLflow. Descargar `predictions_test.csv` desde la página para auditar muestra por muestra ([analisis_errores.md](analisis_errores.md)).

### 6. Versión del modelo en S3 — Diego (2 min)

- Portal → **Models**: 1.0.0 activa (r10) y 0.9.0 (r08), con `VersionId` y SHA-256. Abrir la tarjeta de 1.0.0.
- **Cambiar a 0.9.0**, hacer una predicción y volver a 1.0.0: cambian las probabilidades.
- **¿De dónde sale?** `registry.json` en `s3://dataset-quality-releases-750702272375/models/clasificador/`. Solo se registra una versión después de comprobar con `head-object` que existe y que el SHA-256 descargado coincide. `VersionId` de 1.0.0: `VtRww5se97lomVTcKJUv6d9mYSL7TXOf` ([publicacion_s3.md](publicacion_s3.md)).

### 7. Inferencia y cola de anotación — Andrés (2 min)

- Portal → **Inference**: subir la foto nueva, elegir el recorte y predecir. Clase y probabilidades (suman 1) con la versión 1.0.0.
- Subir `notas.txt`: se rechaza por tipo.
- **Enviar a la cola de anotación** y mostrar el elemento `pending` en P1 (`:3000`).
- **¿De dónde sale?** `p3-inference` descarga el `model.pt` registrado, exige su SHA-256 y usa el mismo preprocesamiento que la evaluación. Prueba: las 145 imágenes de test dan por el portal la misma clase y las mismas probabilidades que `predictions_test.csv` ([F4 T24](fases/F4-modelo-entrenador.md)).

## Preguntas probables

| Pregunta | Quién | Respuesta corta |
|---|---|---|
| ¿Cómo saben que no hay fuga entre train y test? | Diego | Se reparte por grupo de casi duplicados (pHash de P2), no por recorte; `check_manifest` y la prueba confirman 0 en las 9 intersecciones. |
| ¿Por qué no eligieron por test? | Edith | El test se abrió una sola vez, después de fijar `selection.json`; la API de evaluación responde 409 hasta que la selección está cerrada. |
| ¿La predicción sale del modelo o de reglas? | Andrés | Cambiar de versión cambia las probabilidades; 145/145 coinciden con la evaluación offline del mismo archivo. |
| ¿Qué pasa si falta la credencial de AWS? | Diego | Models e Inference responden 503 con qué configurar (#17, #20); nada da 500. |

## Ensayo cronometrado

| Fecha | Integrantes | Duración | Tramos con problemas | Correcciones |
|---|---|---|---|---|
| 30 sep 2026 | | | | |
