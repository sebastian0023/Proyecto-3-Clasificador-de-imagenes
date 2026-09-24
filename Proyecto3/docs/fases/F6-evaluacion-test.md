# F6 — Evaluación final en test

| Campo | Valor |
|---|---|
| Responsable | Diego (PM · datos · evaluación · entrega) |
| Revisor de PRs | Edith |
| Fechas | 28 sep → 29 sep de 2026 |
| Rama | `feat/fase-6-evaluacion-test` |
| Puntos de rúbrica | 18 (4.1–4.4) |
| Depende de | F3, F5 (selección) |
| Bloquea a | F7, F9 |
| Control | Control 3 |

**Nota de calendario:** Diego es el custodio del test. Se implementa el lunes con el fixture; se ejecuta UNA vez el martes, después de la selección.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/p3/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T15 — Evaluación final en test congelado

**Objetivo:** Implementar (lunes, con el fixture) y ejecutar UNA vez (martes, tras T14) la evaluación del candidato elegido sobre el 10% de test.

**Criterios de rúbrica:** 4.1, 4.2, 4.3

**Pasos**

1. Pruebas primero: la evaluación se niega a correr si no existe docs/p3/selection.json con run_id y checkpoint; matriz con filas=real y columnas=predicho, todas las clases, suma = total de test; accuracy = diagonal/total sin redondear; F1 macro y precision/recall/support por clase coinciden con sklearn.
2. Implementa evaluate.py: carga checkpoint y mapa de clases del run elegido, usa el preprocesamiento determinista compartido, infiere todos los crop_id de test.
3. Guarda predictions_test.csv (crop_id, clase_real, clase_predicha, probabilidades), la matriz y las métricas; regístralo todo como artefactos en el run de MLflow elegido junto con timestamp, hash del manifiesto y hash del checkpoint.
4. Ejecuta la evaluación final solo después de la selección; compara accuracy con 0.85 sin redondear.
5. Diego es el custodio del test (ver docs/p3/decisiones.md): nadie más ejecuta inferencia ni calcula métricas sobre el test antes de este paso, y la evaluación final se corre una sola vez.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] La evaluación registra fecha posterior a selection.json
- [ ] Matriz recalculada desde predictions_test.csv coincide con MLflow
- [ ] Métricas por clase disponibles

**Entregables:** `src/p3/eval/evaluate.py`; `predictions_test.csv`; Artefactos en MLflow

## Bloque T16 — Análisis de errores y baseline

**Objetivo:** Explicar la calidad real del clasificador más allá del accuracy.

**Criterios de rúbrica:** 4.4

**Pasos**

1. Calcula el baseline de clase mayoritaria sobre el MISMO test.
2. Identifica la clase más confundida (par real->predicho con más errores) y el recall por clase; indica si el 85% oculta bajo recall de alguna clase.
3. Genera errors.json con N aciertos y N errores del test (crop_id, ruta del recorte, real, predicho, probabilidad) para que la página Evaluation los muestre.
4. Documenta en docs/p3/analisis_errores.md.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Baseline calculado y comparado
- [ ] Ejemplos provienen solo de test (verificable por crop_id en el manifiesto)

**Entregables:** `errors.json`; `docs/p3/analisis_errores.md`

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Edith
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
