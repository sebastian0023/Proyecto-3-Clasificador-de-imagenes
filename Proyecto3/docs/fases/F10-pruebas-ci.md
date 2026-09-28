# F10 — Pruebas, CI y ensayo de arranque

| Campo | Valor |
|---|---|
| Responsable | Andrés (Líder de portal y calidad) |
| Revisor de PRs | Diego |
| Fechas | 24 sep → 30 sep de 2026 |
| Rama | `feat/fase-10-pruebas-ci` |
| Puntos de rúbrica | 8 (7.1, 7.2, 7.3, M1) |
| Depende de | F1 (CI arranca el jueves 24) |
| Bloquea a | F11 |
| Control | Control 1 y 3 |

**Nota de calendario:** La CI se monta el jueves 24 y corre en cada PR; la prueba E2E y el ensayo desde clon limpio son el miércoles 30.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T25 — CI en GitHub Actions, lint y secretos

**Objetivo:** Pipeline que falla ante errores reales de lint, tipos, build o pruebas, y repo protegido contra secretos y archivos pesados.

**Criterios de rúbrica:** 7.3

**Pasos**

1. Workflow: ruff check + ruff format --check, pytest, build y typecheck del frontend, Biome si el portal ya lo usa. Sin continue-on-error.
2. Agrega gitleaks (o equivalente) sobre el diff/historial.
3. Actualiza .gitignore: pesos (*.pt, *.pth, *.onnx), mlruns/, datos, .env; asegura lockfiles commiteados.
4. Demuestra que falla: un PR de prueba con un error de ruff debe quedar en rojo.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [x] Workflow en rojo ante un error inyectado y verde tras corregir → `.github/workflows/p3-ci.yml` corre `ruff check`, `ruff format --check` y `pytest` sin `continue-on-error` (commit `f8def1a`). Evidencia local del gate: un `import os` sin usar pone `ruff check` en **exit 1** (`F401`) y al revertir vuelve a **exit 0**; `pytest` local 143 passed / 1 skipped. _Confirmación de rojo→verde en la propia CI: en la primera corrida del PR de F10._
- [ ] gitleaks corre en CI → job `secrets` cableado en `p3-ci.yml` (gitleaks sobre el historial del PR). _Pendiente: evidencia de la primera corrida en CI (no ejecutable localmente)._

Además, atendiendo el feedback del equipo en el PR #10, la CI del portal (`ci.yml`, job `web`) ahora corre `npm run test:unit` junto a `npm test` y `build` (rama F8, commit `ee53384`).

**Entregables:** `.github/workflows/p3-ci.yml`; `.gitignore`

## Bloque T26 — Prueba de integración de extremo a extremo

**Objetivo:** Una prueba automatizada que recorra el flujo completo con IDs trazables, usando el fixture y MinIO/bucket de prueba.

**Criterios de rúbrica:** 7.2, 7.1

**Pasos**

1. Test (pytest o Playwright) que: selecciona release aprobado del fixture -> genera manifiesto -> lanza trabajo corto (1–2 épocas, imagen pequeña) -> verifica run en MLflow -> selección -> evaluación -> publicación en MinIO -> inferencia vía API/portal.
2. Imprime al final la cadena de IDs (release, manifiesto, run, checkpoint, versión, key, id de inferencia).
3. Prueba de mutación manual en rama aparte: permite un grupo duplicado en train y test, o altera una predicción en la matriz; confirma que la suite falla y documenta en docs/mutaciones.md; revierte.
4. Agrega el test al CI como job separado (puede marcarse como lento).

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] La prueba E2E pasa en CI
- [ ] Las mutaciones documentadas hacen fallar la suite

**Entregables:** `tests/p3/test_e2e.py`; `docs/mutaciones.md`

## Bloque T28 — Ensayo de arranque desde clon limpio (M1)

**Objetivo:** Garantizar que el docente puede levantar todo siguiendo el README literalmente.

**Criterios de rúbrica:** M1, M4

**Pasos**

1. En una máquina/directorio limpio: git clone, seguir el README paso a paso sin conocimiento previo.
2. Recorre las 5 páginas desde la navegación existente, recarga durante un trabajo corto, cambia la versión del modelo y prueba un archivo inválido.
3. Anota cada paso faltante o ambiguo y corrige el README en el momento.
4. Carga el checkpoint publicado en un proceso limpio e infiere una imagen (M4).

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Arranque completo sin pasos inventados
- [ ] Las 5 páginas funcionan con datos reales

**Entregables:** README corregido; `docs/ensayo_arranque.md`

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Diego
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 27 sep 2026 | Andrés | T25 | Rama `feat/fase-10-pruebas-ci`. Nuevo `.github/workflows/p3-ci.yml`: job `p3-python` (instala el lockfile de Proyecto3 + `ruff check`/`ruff format --check`/`pytest`, sin `continue-on-error`) y job `secrets` (gitleaks sobre el historial del PR). `.gitignore` de P3 agrega `*.onnx`. Verificado local: ruff limpio, pytest 143/1, y un error de ruff inyectado pone el gate en rojo (exit 1). Aparte, en la rama F8 se añadió `npm run test:unit` a `ci.yml` (feedback del PR #10). Commit `f8def1a`. | Confirmar rojo→verde y gitleaks en la primera corrida de CI del PR. |
| 27 sep 2026 | Andrés | T26/T28 | **Bloqueados por dependencias.** La E2E (release→manifiesto→train→MLflow→selección→evaluación→S3→inferencia) y el ensayo desde clon limpio necesitan el stack completo (F4–F7: entrenador, MLflow, evaluación, publicación en S3), que aún no está en `main`. Por calendario ambos son del miércoles 30. | Retomar T26 y T28 cuando F4–F7 estén en `main`. |
