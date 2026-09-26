# Decisiones de arranque — Proyecto 3

Las 8 decisiones que la guía del curso pide cerrar antes del primer entrenamiento (F1, bloque T00). Este archivo se commitea antes de cualquier corrida: la fecha del commit es la evidencia de que las clases y la métrica de selección se fijaron antes de ver el test.

| # | Decisión | Responsable | Fecha | Estado |
|---|---|---|---|---|
| 1 | Release de origen | Diego | 24 sep 2026 | Cerrada |
| 2 | Clases incluidas y exclusiones | Diego | 25 sep 2026 | Cerrada ([clases.md](clases.md), `config/classes.yaml`) |
| 3 | Framework y arquitectura | Edith | 24 sep 2026 | Cerrada |
| 4 | Métrica de selección y desempate | Edith | 24 sep 2026 | Cerrada |
| 5 | Servicio de MLflow | Edith | 24 sep 2026 | Cerrada |
| 6 | Destino S3 del modelo y permisos | Diego | 24 sep 2026 | Cerrada |
| 7 | Presupuesto de cómputo | Edith | 24 sep 2026 | Pendiente de dato (medición real, vie 25) |
| 8 | Custodio del test | Diego | 24 sep 2026 | Cerrada |

## 1. Release DVC de origen

**Decisión:** release **0.1.3** del Proyecto 2.

| Campo | Valor |
|---|---|
| Compuerta de calidad | `pass` |
| `dataset_fingerprint` | `2200274dc6bbe6d0bc516e0136ae68651c0040bc6cab64a871794924fa39aa84` |
| `quality_report_fingerprint` | `4d6e64aa13c6f66b15801811c4bb84ebc265b07f538ae27982f79628b170631a` |
| `archive_sha256` | `787742988af1df41d9a58573b81b5c9b4fe7ab24a647b25f2e71d3eb323838b5` |
| Objeto en S3 | `s3://dataset-quality-releases-750702272375/0.1.3/dataset.tar.zst` (`VersionId` `riojb0ulsh1fzPYrMiAicAGps.5f1JBI`) |
| Imágenes (DVC) | `Proyecto2/data/raw.dvc` → `md5 ca56420c9992f8b75fdb10f2ece81704.dir`, 2046 archivos, remote `prod` |
| Conteos | 2045 imágenes, 2120 anotaciones, 5 categorías |

**Evidencia:**
- `Proyecto2/reports/versions.json`: 0.1.3 con `quality_status: pass`.
- SHA-256 recalculado el 24 sep sobre el objeto descargado de S3: coincide con `archive_sha256`.
- `dvc pull -r prod data/raw.dvc` seguido de `dvc status`: "Data and pipelines are up to date".

**Por qué 0.1.3 y no otro:** de 0.1.2 a 0.1.5 comparten `dataset_fingerprint`, pero en el bucket de releases de la cuenta actual (`750702272375`) solo existen 0.1.2 y 0.1.3. El 0.1.5 no está publicado ahí: `reports/prod-promotion.json` registra su promoción como fallida.

**Nota:** `versions.json` aún apunta el `storage_uri` de `prod` del 0.1.3 al bucket de la cuenta anterior (`dataset-quality-releases-prod`). El objeto válido es el de la tabla.

## 2. Clases incluidas y exclusiones

**Decisión:** clasificación de **3 clases: `person`, `dog`, `cat`**. Se excluyen `car` y `bicycle`.

| Clase | Imágenes originales | Cajas | Incluida |
|---|---:|---:|---|
| person | 441 | 751 | Sí |
| dog | 348 | 379 | Sí |
| cat | 312 | 329 | Sí |
| car | 247 | 320 | No: < 300 originales |
| bicycle | 240 | 341 | No: < 300 originales |

**Evidencia:** `Proyecto2/reports/stats.json` (`images_per_class`, `boxes_per_class`) sobre la misma huella del release 0.1.3.

**Regla:** la exclusión se basa solo en el mínimo de 300 originales por clase, no en resultados de modelo. No se agregan ni se quitan clases después de ver el test.

**Riesgo registrado:** `person` aporta cerca del 51% de las cajas. El baseline de clase mayoritaria ronda 51%, así que se reportan F1 macro y recall por clase junto con el accuracy.

**Confirmado (F2 T06, 25 sep):** después de validar todas las cajas del release, los originales con caja válida son cat 312, dog 348 y person 441 (car 247, bicycle 239). Las tres clases se mantienen. Detalle y procedencia en [clases.md](clases.md).

## 3. Framework y arquitectura inicial

**Decisión:** **PyTorch + torchvision**, arquitectura **ResNet-18**.

- **Pesos iniciales:** preentrenados en ImageNet (`torchvision.models.ResNet18_Weights.IMAGENET1K_V1`). El origen se declara en la tarjeta del modelo.
- **Adaptación:** se reemplaza la capa `fc` por una cabeza configurable (`hidden_layers` + `dropout`) con 3 salidas.
- **Capas entrenables:** todas (fine-tuning completo).
- **Versiones:** `torch` y `torchvision` se fijan en el lockfile del Proyecto 3 (F4), con Python 3.12.

**Por qué:** hay pocos datos (≈1,460 recortes en 3 clases) y la meta es 85% de accuracy en test. Partir de pesos preentrenados es la forma más segura de llegar, y la rúbrica lo permite si se declara.

## 4. Métrica de selección del candidato

**Decisión:**
1. Mayor **`val_accuracy`** de la mejor época (checkpoint restaurado por early stopping).
2. Desempate: menor **`val_loss`** en esa misma época.
3. Segundo desempate: la corrida que terminó primero (`end_time` de MLflow).

- Early stopping vigila `val_accuracy`, con `patience` y `min_delta` definidos por `TrainingConfig`.
- Solo cuentan corridas `FINISHED` sobre la misma versión de manifiesto y las mismas clases.
- El test no interviene en ningún paso. `selection.json` se commitea antes de correr la evaluación final.

## 5. Servicio de MLflow

**Decisión:** servidor MLflow como servicio del docker compose del stack, en `http://localhost:5000`.

- **Registros (backend store):** SQLite dentro de un volumen Docker con nombre.
- **Artefactos:** directorio en un volumen Docker con nombre, servido por el propio servidor (`--serve-artifacts`).
- **Persistencia:** ambos sobreviven a `docker compose down` / `up`. Solo `down -v` los borra, y no se usa en el flujo normal.

**Por qué:** no depende de MinIO, cuyas imágenes fijadas en `Proyecto2/docker-compose.yml` dejaron de publicarse (hallazgo del 24 sep, se documenta en T01), y se prueba la persistencia en T02.

## 6. Destino S3 del modelo y permisos

**Decisión:** `s3://dataset-quality-releases-750702272375/models/clasificador/<version-semver>/`, con pesos, tarjeta, mapa de clases y configuración.

- El bucket ya existe en la cuenta del equipo y tiene versionado activo: los objetos devuelven `VersionId`.
- **Permisos locales:** un usuario IAM por integrante (`Proyecto2/terraform/modules/team_access`), configurado como perfil en `~/.aws` de cada quien.
- **Permisos en CI:** rol OIDC de GitHub Actions, sin llaves de larga vida.
- **Evaluador:** usuario de solo lectura del mismo módulo.
- **Nunca** se guardan llaves en Git, `.env` versionado, código ni MLflow.

## 7. Presupuesto de cómputo

**Decisión (estimada):** entrenamiento en la máquina de Edith.

| Recurso | Valor |
|---|---|
| GPU | NVIDIA GeForce RTX 4060, 8 GB |
| CPU | AMD Ryzen 5 5500, 6 núcleos / 12 hilos |
| RAM | 32 GB |
| Reserva | 4 h de GPU entre el lun 28 y el mar 29: 12 a 15 corridas + 1 evaluación final en test |

**Estimación:** menos de 5 minutos por corrida (≈1,000 recortes de entrenamiento a 224 px con ResNet-18).

**Pendiente:** se actualiza el vie 25 con el tiempo real de una corrida medida.

## 8. Custodio del test

**Decisión:** **Diego**. Guarda el orden "selección → evaluación": no se corre la evaluación final hasta que `selection.json` esté commiteado, y el test no se consulta para aumentación, early stopping ni hiperparámetros.
