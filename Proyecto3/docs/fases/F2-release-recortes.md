# F2 — Almacenamiento, release y recortes COCO

| Campo | Valor |
|---|---|
| Responsable | Diego (PM · datos · evaluación · entrega) |
| Revisor de PRs | Edith |
| Fechas | 24 sep → 25 sep de 2026 |
| Rama | `feat/fase-2-release-recortes` |
| Puntos de rúbrica | 9 (1.1, 1.2, M2 (compuerta)) |
| Depende de | F1 (contratos y decisiones) |
| Bloquea a | F3, F7 |
| Control | Control 2 |

**Nota de calendario:** El bucket propio y la copia de los datos de DVC van primero (jueves); las clases se fijan y se hace commit antes de cualquier corrida.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T31 — Almacenamiento propio en S3 (DVC, MLflow y modelos)

**Objetivo:** Tener, desde el inicio, un bucket del equipo con permisos listos para los datos de DVC, los artefactos de MLflow y los modelos publicados, sin depender del almacenamiento del equipo anterior.

**Criterios de rúbrica:** M2, 1.1, 1.3, 3.2, 5.2

**Pasos**

1. Crea (o confirma) un bucket de AWS S3 con versionado habilitado y prefijos dvc/, mlflow/ y models/.
2. Crea credenciales con el mínimo privilegio sobre ese bucket; guárdalas en .env y .dvc/config.local (ignorados por git) y en los Secrets de GitHub Actions si la CI las necesita. Nunca en el repo.
3. Copia los datos del release aprobado del P2: dvc pull desde el remoto original, dvc remote add -d p3storage s3://<bucket>/dvc, dvc push -r p3storage. Los hashes no cambian.
4. Verifica desde un clon limpio que dvc pull del release funciona solo con el remoto nuevo.
5. Apunta el artifact store de MLflow (T02) a s3://<bucket>/mlflow/ o confirma el volumen persistente elegido en decisiones.md.
6. Documenta bucket, prefijos, región y variables de entorno necesarias (solo nombres) en docs/almacenamiento.md.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] dvc pull del release funciona desde un clon limpio con el remoto propio
- [ ] Versionado del bucket habilitado
- [ ] gitleaks sin hallazgos tras el cambio

**Entregables:** `docs/almacenamiento.md`; `.dvc/config actualizado (sin credenciales)`

## Bloque T05 — Selector de release DVC aprobado y consumo de COCO

**Objetivo:** Que P3 consuma de forma real y trazable un release aprobado del Proyecto 2, a través del servicio existente, y no una copia en data/.

**Criterios de rúbrica:** 1.1, M2, 6.1 (rechazo de gate fallido)

**Pasos**

1. Escribe primero pruebas: listar solo releases con quality gate aprobado; rechazar (HTTP 409 con mensaje claro) un release con gate fallido; conservar release_id, hash DVC y referencia al reporte de calidad.
2. Implementa GET /api/p3/releases?approved=true reutilizando el registro de releases del P2 (ver docs/inventario.md).
3. Implementa la carga del COCO e imágenes del release elegido mediante el servicio existente (dvc get/dvc api o el servicio del portal), nunca desde una ruta fija.
4. Agrega un script de comprobación que cambie de versión de release en entorno de prueba y muestre que los conteos cambian.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Con dos releases distintos los conteos de imágenes/anotaciones difieren
- [ ] Un release con gate fallido no puede usarse
- [ ] El release_id y hash quedan disponibles para el manifiesto

**Entregables:** Endpoint de releases; Módulo de carga de release; Pruebas unitarias

## Bloque T06 — Selección y documentación de clases (antes de experimentar)

**Objetivo:** Fijar las clases incluidas y excluidas ANTES de cualquier experimento, con evidencia de conteos del release aprobado.

**Criterios de rúbrica:** 1.2 (≥2 clases con ≥300 originales), 3.1 (misma definición de clases)

**Pasos**

1. Escribe un script que cuente, por categoría del release aprobado, imágenes ORIGINALES distintas (no recortes) con al menos una caja válida.
2. Elige al menos 2 clases con ≥300 originales distintos cada una; documenta criterios de exclusión del resto (por conteo, ambigüedad, etc.).
3. Guarda la lista en config/p3/classes.yaml (id, nombre, conteo) y la justificación en docs/clases.md, con fecha y hash del release.
4. Haz commit antes de que exista cualquier corrida de entrenamiento: la fecha del commit es evidencia de que se decidió antes del test.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] classes.yaml y clases.md existen y citan el release
- [ ] Cada clase incluida tiene ≥300 originales distintos según el script
- [ ] Commit fechado antes de la primera corrida en MLflow

**Entregables:** `config/p3/classes.yaml`; `docs/clases.md`; `scripts/p3/count_classes.py`

## Bloque T07 — Generador de recortes COCO con validación y exclusiones

**Objetivo:** Convertir cada caja COCO válida de las clases elegidas en un recorte etiquetado, trazable al original, rechazando cajas inválidas.

**Criterios de rúbrica:** 1.2

**Pasos**

1. Pruebas primero: caja con w o h <= 0 se rechaza; caja fuera de los límites de la imagen se rechaza (o se recorta al borde con regla documentada); imagen faltante se rechaza; categoría no incluida se excluye; cada exclusión queda registrada con motivo.
2. Implementa el recorte (Pillow) conservando image_id, annotation_id, category_id y bbox original; un original puede producir varios recortes.
3. Genera exclusions.csv con annotation_id, image_id y motivo.
4. Verifica manualmente 10 recortes al azar contra el COCO original y guarda la evidencia (ids + miniaturas) en docs/verificacion_recortes.md.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Una caja degenerada inyectada no aparece en el manifiesto
- [ ] Cada recorte conserva los 4 identificadores de origen
- [ ] exclusions.csv con motivos

**Entregables:** `src/p3/data/crops.py`; `exclusions.csv`; Pruebas; `docs/verificacion_recortes.md`

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Edith
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
