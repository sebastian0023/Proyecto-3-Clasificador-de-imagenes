# F3 — Manifiesto 70/20/10 sin fuga

| Campo | Valor |
|---|---|
| Responsable | Diego (PM · datos · evaluación · entrega) |
| Revisor de PRs | Edith |
| Fechas | 25 sep → 28 sep de 2026 |
| Rama | `feat/fase-3-manifiesto` |
| Puntos de rúbrica | 5 (1.3, M3 (compuerta)) |
| Depende de | F2 |
| Bloquea a | F5, F6 |
| Control | Control 2 |

**Nota de calendario:** Congelado el lunes 28 antes de mediodía; sin esto no arranca el barrido.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T08 — Manifiesto 70/20/10 agrupado, reproducible y versionado

**Objetivo:** Generar el manifiesto derivado con split 70/20/10 por grupos, sin fuga y con versión propia vinculada al release de P2. Debe quedar CONGELADO el lunes 28 a mediodía; los experimentos dependen de él.

**Criterios de rúbrica:** 1.3, M3

**Pasos**

1. Pruebas primero: intersección vacía entre particiones por crop_id, source_image_id y dup_group_id; misma semilla -> mismos IDs; cada clase presente en val y test; desviación global <= ±5 pp por partición.
2. Define dup_group_id: reutiliza los grupos de casi-duplicados del P2 si existen; si no, calcula pHash (imagehash) y agrupa distancias de Hamming <= umbral documentado.
3. Asigna particiones por grupo (todos los recortes de un original y de su grupo de duplicados juntos) de forma estratificada por clase, con semilla fija.
4. Versiona el manifiesto con DVC; guarda su hash y el release_id/hash de origen dentro del propio archivo y en docs/manifiesto.md. No sobrescribas el split 70/15/15 del P2.
5. Reporta tabla de conteos por clase x partición (recortes y originales distintos).

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [x] Dos generaciones con la misma semilla producen archivos idénticos (mismo hash) — `generate_manifest.py --check`: `45600f29…`, escrito idéntico ([manifiesto.md](../manifiesto.md#reproducibilidad)); `tests/test_split.py::test_misma_semilla_mismo_manifiesto_y_mismo_hash`
- [x] Intersecciones vacías demostradas por prueba — `tests/test_split.py::test_ningun_identificador_aparece_en_dos_particiones` y 0 en las 9 intersecciones del manifiesto real ([manifiesto.md](../manifiesto.md#evidencia-de-aislamiento-m3))
- [x] Tabla por clase y partición en docs/manifiesto.md — recortes y originales por clase y partición ([manifiesto.md](../manifiesto.md#conteos-por-clase-y-partición))
- [ ] Manifiesto versionado en DVC y etiquetado como congelado — puntero `data/manifests/m-0.1.3-s42-1.dvc` en Git (`65f2d46`); falta `dvc push` al remote y la etiqueta de congelado

**Entregables:** `src/p3/data/split.py`; `manifiesto .dvc`; `docs/manifiesto.md`

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Edith
- [ ] CI en verde en `main`
- [x] Commits red → green visibles en el historial — red `3a9cb14` → green `089ac4b`, prueba reforzada `c248087`

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 26 sep 2026 | Diego | T08 | `src/p3/data/split.py` (red `3a9cb14` → green `089ac4b`; prueba corregida `29d4042`; reforzada `c248087` tras 3 mutaciones sobrevivientes) y `scripts/generate_manifest.py` (`935159c`). Manifiesto real `m-0.1.3-s42-1`: 1459 recortes, 70.05/20.01/9.94 %, 0 en las 9 intersecciones, reproducible byte a byte; 0 grupos de casi duplicados (igual que el reporte de P2). DVC en `Proyecto3/` (`65f2d46`). `docs/manifiesto.md`. | `dvc push`, etiqueta de congelado, PR a Edith; `POST /api/p3/manifests` para Training |
