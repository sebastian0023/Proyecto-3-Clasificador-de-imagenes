# F1 — Kickoff, arranque del stack y contratos

| Campo | Valor |
|---|---|
| Responsable | Edith (Líder de ML y MLOps) |
| Revisor de PRs | Andrés |
| Fechas | 24 sep de 2026 |
| Rama | `feat/fase-1-arranque-contratos` |
| Puntos de rúbrica | 0 (M1 (compuerta)) |
| Depende de | — |
| Bloquea a | F2–F10 |
| Control | Control 1 |

**Nota de calendario:** Kickoff de decisiones a primera hora, dirigido por Diego (PM); los contratos se publican antes de mediodía. Todo el equipo depende de esta fase.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T00 — Hoja de decisiones de arranque (kickoff)

**Objetivo:** Cerrar en un kickoff de los tres, dirigido por Diego (PM), las 8 decisiones que la guía del curso pide antes del primer entrenamiento, y dejarlas versionadas.

**Criterios de rúbrica:** Todas (evita retrabajo en 1.2, 3.3, 3.2, 5.2)

**Pasos**

1. Crea docs/decisiones.md con una sección por decisión: (1) release DVC de origen y hash, con compuerta aprobada; (2) clases incluidas y exclusiones (se confirman con los conteos de F2 el viernes 25); (3) framework y arquitectura inicial, con origen de pesos preentrenados; (4) métrica de selección del candidato y desempate, p. ej. mayor val_accuracy y luego menor val_loss; (5) servicio de MLflow y dónde persisten registros y artefactos; (6) destino S3 del modelo (bucket y prefijo) y cómo se gestionan permisos sin claves en Git; (7) presupuesto de cómputo: máquina, CPU/GPU y horas reservadas para ≥10 corridas y una prueba final (se actualiza el viernes con la medición real); (8) custodio del test: Diego.
2. Cada decisión lleva responsable, fecha y estado (cerrada / pendiente de dato). No incluyas contraseñas ni claves.
3. Haz commit antes de cualquier corrida de entrenamiento; la fecha del commit es evidencia de que la métrica y las clases se decidieron antes de ver el test.
4. Opcional: exporta las mismas decisiones al formulario de la guía del PM (HTML del curso) y guarda el JSON exportado en docs/guia-pm-plan.json.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [x] docs/decisiones.md con las 8 decisiones y su responsable → [decisiones.md](../decisiones.md)
- [x] La métrica de selección está fijada antes de la primera corrida → [decisiones.md §4](../decisiones.md#4-métrica-de-selección-del-candidato); aún no existe ninguna corrida de MLflow
- [ ] Commit fechado el jueves 24

**Entregables:** `docs/decisiones.md`

## Bloque T01 — Inventario del repo y línea base

**Objetivo:** Documentar el estado actual del repositorio para que el equipo y los agentes sepan dónde está cada pieza de P1/P2 que P3 va a consumir.

**Criterios de rúbrica:** Fase 0, M1

**Pasos**

1. Ejecuta: git rev-parse --short HEAD; git status --short; git log --oneline --graph --all | head -60; git branch -a; dvc remote list -v; dvc status.
2. Localiza y anota con ruta: comando de arranque (docker-compose/Makefile), servicio que sirve COCO e imágenes, dónde se registran los releases DVC y su estado de quality gate, stack del backend y del frontend, router de páginas, y dónde se leen las credenciales (sin imprimir valores).
3. Copia el archivo de rúbrica del proyecto a docs/rubrica.md.
4. Verifica que el portal actual arranca siguiendo el README desde un clon limpio y anota cualquier paso faltante.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] docs/inventario.md existe con rutas concretas (archivo:línea) para cada elemento listado
- [ ] docs/rubrica.md está en el repo
- [ ] Hay una lista de pasos del README que fallan o faltan (o 'ninguno')

**Entregables:** `docs/inventario.md`; `docs/rubrica.md`

## Bloque T02 — Worker de entrenamiento + servidor MLflow en el stack

**Objetivo:** Que el stack que arranca con el README incluya un worker de entrenamiento asíncrono y un servidor MLflow con almacenamiento persistente.

**Criterios de rúbrica:** M1, 6.1 (entrenamiento fuera del request), 3.2

**Pasos**

1. Agrega al docker-compose (o equivalente del repo) un servicio mlflow con backend store persistente (Postgres o SQLite en volumen) y artifact store (bucket/MinIO o volumen).
2. Agrega un worker (Celery/RQ/cola que ya use el proyecto) que tome trabajos de entrenamiento; el endpoint HTTP solo encola y devuelve job_id.
3. Persiste en BD estado, progreso, logs y error de cada trabajo para que sobrevivan a recargar la página.
4. Prueba: encolar un trabajo 'dummy' y consultar su estado tras reiniciar el backend.
5. Prueba de persistencia de MLflow: registra un run de prueba con un artefacto, reinicia todo el stack (docker compose down && up) y verifica que el run_id, sus métricas y el artefacto siguen disponibles.
6. Actualiza el README con los pasos exactos de arranque (sin pasos implícitos).

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] docker compose up levanta portal, worker y MLflow desde clon limpio
- [ ] Estado de un trabajo persiste tras reinicio
- [ ] Run IDs y artefactos de MLflow sobreviven al reinicio del stack
- [ ] README actualizado

**Entregables:** docker-compose actualizado; `src/p3/worker/`; README

## Bloque T04 — Contratos entre módulos (manifiesto, API, config)

**Objetivo:** Definir los contratos que permiten a Diego (datos), Edith (entrenamiento) y Andrés (portal) trabajar en paralelo sin bloquearse.

**Criterios de rúbrica:** Habilita trabajo en paralelo (1.3, 2.2, 6.x)

**Pasos**

1. Define el esquema del manifiesto de recortes (JSONL o Parquet): crop_id, source_image_id, annotation_id, category_id, category_name, bbox_xywh original, dup_group_id, split (train/val/test), release_id, release_hash.
2. Define el esquema de TrainingConfig: optimizer (sgd|adam|adamw), batch_size, max_epochs, learning_rate, image_size, hidden_layers (lista de enteros), dropout, seed, patience, min_delta, monitor_metric (val_accuracy por defecto), rangos válidos de cada uno.
3. Define los endpoints REST: GET /api/p3/releases?approved=true, POST /api/p3/manifests, GET /api/p3/manifests/{id}, POST /api/p3/training/jobs, GET /api/p3/training/jobs/{id} (estado, progreso, logs), GET /api/p3/runs, GET /api/p3/runs/{id}, POST /api/p3/selection, GET /api/p3/evaluation, GET /api/p3/models, POST /api/p3/models/{version}/activate, POST /api/p3/inference, POST /api/p3/inference/{id}/send-to-annotation. Incluye ejemplos de request/response JSON.
4. Crea un fixture pequeño (tests/fixtures/p3/) con un COCO de 3 clases y ~30 imágenes sintéticas para pruebas.
5. Pide revisión a Edith y Andrés en el PR antes de fusionar.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] docs/contratos.md con esquemas y ejemplos JSON
- [ ] Fixture de pruebas disponible
- [ ] PR aprobado por los otros dos integrantes

**Entregables:** `docs/contratos.md`; `tests/fixtures/p3/`

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Andrés
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 24 sep | Edith | T00 | `docs/decisiones.md` con las 8 decisiones; release 0.1.3 verificado por SHA-256 en S3 | Confirmar clases (2) y cómputo (7) el vie 25; marcar "commit fechado" con su hash; review de Andrés en el PR |
