# F8 — Portal: Training y Experiments

| Campo | Valor |
|---|---|
| Responsable | Andrés (Líder de portal y calidad) |
| Revisor de PRs | Diego |
| Fechas | 24 sep → 28 sep de 2026 |
| Rama | `feat/fase-8-portal-training-experiments` |
| Puntos de rúbrica | 7 (6.1, 6.2) |
| Depende de | F1 (contratos) |
| Bloquea a | F9 |
| Control | Control 2 |

**Nota de calendario:** Se construye contra el contrato y se conecta al backend real el lunes.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T03 — Rutas y navegación de las 5 páginas + cliente API

**Objetivo:** Agregar Training, Experiments, Evaluation, Models e Inference a la navegación EXISTENTE del portal de P1/P2, con un cliente API tipado.

**Criterios de rúbrica:** 6.x (misma aplicación)

**Pasos**

1. Crea las 5 rutas en el router actual y enlázalas desde el menú existente.
2. Crea un cliente API tipado (tipos generados o escritos a partir de docs/contratos.md) con manejo de errores común.
3. Mientras el backend no exista, usa MSW o similar SOLO en desarrollo/pruebas; nada de datos fijos en el build de producción.
4. Prueba de componente: cada ruta renderiza y la navegación funciona.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [x] Las 5 páginas accesibles desde la navegación existente → Training, Experiments, Evaluation, Models e Inference agregadas a `PAGES` del router por hash en `Proyecto2/web/src/App.tsx` (commit `9a7beb0`). Prueba de componente `Proyecto2/web/tests/app-nav.test.tsx` (rojo `ef28491` → verde `9a7beb0`): las 5 aparecen en el menú y cada ruta renderiza su encabezado; `npm run test:unit` en verde (9/9).
- [x] Build y chequeo de tipos limpios → `npm run build` (`tsc --noEmit && vite build`) en verde. Cliente API tipado en `Proyecto2/web/src/lib/api.ts` (`api.p3`, commit `ba7d9bf`) con tipos espejando `contratos.md`. Mock backend solo dev/pruebas (`VITE_P3_MOCK=1`), verificado ausente del bundle de producción (commit `a3d1d2a`).

**Entregables:** Rutas y layout; Cliente API

## Bloque T19 — Página Training

**Objetivo:** Pantalla para elegir release aprobado, ver procedencia y split, configurar todos los parámetros y lanzar/seguir un trabajo real.

**Criterios de rúbrica:** 6.1, 2.2 (validación por portal)

**Pasos**

1. Selector de release (solo aprobados) mostrando versión, hash y reporte de calidad; botón para generar/ver el manifiesto 70/20/10 con tabla de conteos por clase y partición.
2. Formulario con los 7 parámetros + seed, patience, min_delta; validación en cliente con los mismos rangos de contratos.md y mostrando el error 422 del servidor.
3. Lanzar trabajo -> muestra job_id; vista de estado, progreso por época, logs y error que persisten al recargar (consultando GET /training/jobs/{id}).
4. Bloquea el lanzamiento si el gate está fallido o el manifiesto no está congelado, mostrando el motivo.
5. Pruebas de componente para validación y estados.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Recargar durante un trabajo conserva estado y logs
- [ ] Valor inválido rechazado antes de crear trabajo
- [ ] Datos 100% del backend

**Entregables:** Página Training; Pruebas

## Bloque T20 — Página Experiments

**Objetivo:** Tabla de corridas reales de MLflow con filtros, comparación y curvas.

**Criterios de rúbrica:** 6.2, 3.3

**Pasos**

1. Backend (si no existe): GET /api/p3/runs y /runs/{id} que consultan la API de MLflow (no archivos locales).
2. Tabla ordenable/filtrable por parámetros y métricas de validación; selección de 2+ corridas para comparar parámetros.
3. Curvas train/val de loss y accuracy por época desde las métricas de MLflow; enlace al run en MLflow con el mismo run_id.
4. Muestra el candidato seleccionado (selection.json) sin mostrar métricas de test.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Cambiar un tag/métrica en un MLflow de prueba se refleja en la UI
- [ ] Abrir un run lleva al mismo id y artefactos

**Entregables:** Página Experiments; Endpoints de runs

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Diego
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 27 sep 2026 | Andrés | T03 | Rama `feat/fase-8-portal-training-experiments`. Tooling de pruebas de componente (Vitest + Testing Library + jsdom, `0c5ea6c`). 5 páginas de P3 en el router por hash existente de `Proyecto2/web` (`ef28491`→`9a7beb0`). Cliente API tipado `api.p3` espejando `contratos.md` (`a147395`→`ba7d9bf`). Mock backend de fetch solo dev/pruebas, fuera del build de prod (`2b6d17d`→`a3d1d2a`). `npm run test:unit` 9/9, `npm test` 5/5, `npm run build` en verde. | Conectar al backend real el lunes 28 (hoy corre contra mock/contrato). PR para revisión de Diego. |
