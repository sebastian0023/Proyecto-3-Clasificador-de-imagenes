# F7 — Paquete, tarjeta y publicación en S3

| Campo | Valor |
|---|---|
| Responsable | Diego (PM · datos · evaluación · entrega) |
| Revisor de PRs | Edith |
| Fechas | 29 sep → 30 sep de 2026 |
| Rama | `feat/fase-7-paquete-s3` |
| Puntos de rúbrica | 10 (5.1, 5.2, 5.3) |
| Depende de | F5, F6 |
| Bloquea a | F9, F11 |
| Control | Control 3 |

**Nota de calendario:** El bucket ya existe desde F2; aquí solo se empaqueta, se publica y se verifica la descarga. Debe estar en S3 el miércoles 30 a mediodía para que Models e Inference funcionen.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T17 — Paquete del modelo y tarjeta

**Objetivo:** Empaquetar el artefacto seleccionado con todo lo necesario para reproducir su inferencia y documentarlo en una tarjeta fiel.

**Criterios de rúbrica:** 5.1

**Pasos**

1. Arma el paquete: model.pt (state_dict), config de arquitectura, classes.json, preprocess.json (image_size, mean, std), requirements con versiones fijadas.
2. Escribe model_card.md con: propósito; clases incluidas y exclusiones; release DVC de origen con hash; manifiesto y split; run_id de MLflow y configuración; desempeño global y POR CLASE en test (tomado de T15, no reescrito a mano) y baseline; preprocesamiento exacto (image_size, mean, std); limitaciones; origen de pesos preentrenados; modo de cargarla (código mínimo de carga e inferencia); versión semántica 1.0.0.
3. Prueba: cargar el paquete en un proceso limpio e inferir una imagen.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] La tarjeta describe exactamente el run de selection.json
- [ ] La tarjeta incluye desempeño por clase, preprocesamiento y modo de carga
- [ ] El paquete carga en venv limpio siguiendo solo la tarjeta

**Entregables:** `models/p3/<version>/ (ignorado en git salvo metadatos)`; `model_card.md`

## Bloque T18 — Publicación en AWS S3 real y registro de versiones

**Objetivo:** Subir pesos y tarjeta a un bucket S3 real, recuperables y verificables, y registrar la versión para que el portal la resuelva.

**Criterios de rúbrica:** 5.2, 5.3, 6.4 (no marcar publicado un objeto inexistente)

**Pasos**

1. Pruebas primero (con moto o MinIO): publicar calcula SHA-256 local, sube, hace head-object y solo marca 'publicado' si el objeto existe; activar una versión cambia el artefacto cargado.
2. Habilita versionado en el bucket; sube model.pt, model_card.md y el paquete a s3://<bucket>/models/<nombre>/<version>/ usando credenciales de entorno (nunca en el repo).
3. Guarda en el registro de modelos: versión semántica, run_id, manifiesto, bucket/key, VersionId, SHA-256. Si usan MLflow Model Registry, backend persistente.
4. Descarga en un entorno limpio (venv nuevo), verifica SHA-256 e infiere una imagen; guarda la salida como evidencia.
5. Publica al menos dos versiones (p. ej. 1.0.0 y 1.0.1) para demostrar que una anterior sigue recuperable.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] head-object muestra ambos objetos con VersionId
- [ ] SHA-256 local coincide tras descargar
- [ ] Inferencia exitosa con el modelo descargado

**Entregables:** `src/p3/registry/publish.py`; `docs/publicacion_s3.md (sin secretos)`

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Edith
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
