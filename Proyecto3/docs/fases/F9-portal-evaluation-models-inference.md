# F9 — Portal: Evaluation, Models e Inference

| Campo | Valor |
|---|---|
| Responsable | Andrés (Líder de portal y calidad) |
| Revisor de PRs | Diego |
| Fechas | 28 sep → 30 sep de 2026 |
| Rama | `feat/fase-9-portal-evaluation-models-inference` |
| Puntos de rúbrica | 11 (6.3, 6.4, 6.5) |
| Depende de | F4, F6, F7 |
| Bloquea a | F10 |
| Control | Control 3 |

**Nota de calendario:** Evaluation debe bloquearse hasta que exista la selección.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T21 — Página Evaluation

**Objetivo:** Mostrar la evaluación final real, bloqueada hasta que exista la selección del modelo.

**Criterios de rúbrica:** 6.3, 4.2, 4.4

**Pasos**

1. Backend: GET /api/p3/evaluation devuelve 423 (bloqueado) si no hay selection.json; si existe, devuelve candidato, versión de datos, métricas, matriz y errors.json.
2. Matriz de confusión (filas=real, columnas=predicho) con todas las clases; métricas globales y por clase; baseline.
3. Galería de aciertos y errores del test (recorte, real, predicho, probabilidad).
4. Botón para exportar predictions_test.csv para auditoría.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Antes de la selección la página no revela métricas de test
- [ ] Las cifras coinciden con MLflow

**Entregables:** Página Evaluation

## Bloque T22 — Página Models

**Objetivo:** Listar versiones publicadas con su tarjeta, trazabilidad y estado en S3, y elegir la versión activa para inferencia.

**Criterios de rúbrica:** 6.4, 5.3

**Pasos**

1. Lista de versiones (semántica del MODELO, claramente separada de la versión del dataset) con run_id, manifiesto, bucket/key, SHA-256 y estado de publicación.
2. Vista de la tarjeta (model_card.md renderizada) y botón de descarga.
3. Acción 'Usar para inferencia' que llama POST /models/{version}/activate; el backend verifica con head-object antes de aceptar.
4. Prueba: intentar activar una versión cuyo objeto no existe muestra error.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Cambiar la versión activa cambia la predicción/hash del modelo en Inference
- [ ] No se puede marcar publicado un objeto inexistente

**Entregables:** Página Models

## Bloque T23 — Página Inference

**Objetivo:** Subir una imagen nueva o elegir una del portal, recortar, inferir con la versión activa y enviar a la cola de anotación.

**Criterios de rúbrica:** 6.5

**Pasos**

1. Carga de archivo con validación de tipo y tamaño en cliente (el servidor valida también).
2. Herramienta para dibujar/elegir la caja de recorte o usar una anotación existente del portal.
3. Muestra clase, barra de probabilidades por clase y versión de modelo usada.
4. Botón 'Enviar a cola de anotación' que llama al endpoint y muestra enlace al elemento creado.
5. Prueba: archivo inválido muestra error claro.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Predicción proviene del endpoint real
- [ ] El elemento enviado es consultable en el flujo de anotación

**Entregables:** Página Inference

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Diego
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
