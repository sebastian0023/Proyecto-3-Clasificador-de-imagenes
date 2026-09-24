# F5 — Experimentos MLflow y selección

| Campo | Valor |
|---|---|
| Responsable | Edith (Líder de ML y MLOps) |
| Revisor de PRs | Andrés |
| Fechas | 28 sep → 29 sep de 2026 |
| Rama | `feat/fase-5-experimentos-seleccion` |
| Puntos de rúbrica | 14 (3.1, 3.2, 3.3) |
| Depende de | F3, F4 |
| Bloquea a | F6, F7, F8 |
| Control | Control 3 |

**Nota de calendario:** Barrido la noche del lunes; selection.json con commit el martes antes de mediodía.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/p3/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T13 — Barrido de ≥10 corridas válidas

**Objetivo:** Ejecutar al menos 10 corridas completas sobre el MISMO manifiesto congelado y la MISMA definición de clases, variando los 7 parámetros.

**Criterios de rúbrica:** 3.1

**Pasos**

1. Define en config/p3/sweep.yaml ≥12 combinaciones (margen por si alguna falla) donde optimizer, batch_size, max_epochs, learning_rate, image_size, hidden_layers y dropout aparecen cada uno con ≥2 valores. Ejemplo: optimizer {adam, sgd, adamw}, batch_size {32, 64}, max_epochs {15, 30}, lr {1e-3, 3e-4, 1e-2 para sgd}, image_size {128, 224}, hidden_layers {[256], [512,128]}, dropout {0.2, 0.5}.
2. Lanza las corridas por el worker (se pueden ejecutar de noche); ninguna corrida de un solo batch ni duplicada.
3. Al terminar, lista con mlflow.search_runs los run_id FINISHED con su mejor val_accuracy y guárdalo en docs/p3/corridas.md.
4. NO mires ninguna métrica de test en este paso.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] ≥10 runs FINISHED con resultados distintos
- [ ] Cada uno de los 7 parámetros tiene ≥2 valores
- [ ] Todos con el mismo hash de manifiesto

**Entregables:** `config/p3/sweep.yaml`; `docs/p3/corridas.md`

## Bloque T14 — Selección del candidato por validación

**Objetivo:** Elegir el modelo con una métrica de validación predeclarada, dejando evidencia fechada ANTES de evaluar en test.

**Criterios de rúbrica:** 3.3

**Pasos**

1. Implementa POST /api/p3/selection que toma el run con mayor val_accuracy (desempate: menor val_loss), escribe docs/p3/selection.json con run_id, ruta del checkpoint, métrica, valor y timestamp, y etiqueta el run en MLflow (selected=true).
2. Haz commit de selection.json antes de que Diego ejecute T15.
3. Avisa a Diego en la tarjeta cuando esté listo.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] selection.json commiteado con fecha anterior a la evaluación
- [ ] El run seleccionado tiene la mejor val_accuracy de docs/p3/corridas.md

**Entregables:** `docs/p3/selection.json`; Endpoint de selección

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Andrés
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
