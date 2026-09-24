# F11 — Autoevaluación y congelación

| Campo | Valor |
|---|---|
| Responsable | Diego (Líder de datos, evaluación y entrega) |
| Revisor de PRs | Edith |
| Fechas | 30 sep de 2026 |
| Rama | `feat/fase-11-autoevaluacion-cierre` |
| Puntos de rúbrica | 0 (Todas) |
| Depende de | F1–F10 |
| Bloquea a | — |
| Control | Control 3 |

**Nota de calendario:** Miércoles 30 en la tarde; todo lo inyectado se revierte antes de etiquetar.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/p3/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T29 — Autoevaluación con el prompt de rúbrica

**Objetivo:** Ejecutar el prompt de evaluación (docs/p3/rubrica.md) sobre el repo como lo haría el docente y corregir lo que falle.

**Criterios de rúbrica:** Todas

**Pasos**

1. Corre el prompt completo con un agente sobre una copia limpia del repo en el commit candidato.
2. Registra la tabla de puntos obtenida y los criterios con puntuación < máximo.
3. Crea tarjetas de corrección en Notion para cada hueco y asígnalas al dueño del área; prioriza compuerta M1–M4 y 4.3.
4. Repite solo las secciones afectadas tras las correcciones.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Compuerta M1–M4 en CUMPLE
- [ ] Lista de pérdidas de puntos atendida o justificada

**Entregables:** `docs/p3/autoevaluacion.md`; reporte HTML de ensayo

## Bloque T30 — Congelamiento, etiqueta de entrega y checklist final

**Objetivo:** Cerrar la entrega con un commit identificable y trazabilidad completa.

**Criterios de rúbrica:** Todas

**Pasos**

1. Rellena docs/p3/trazabilidad.md: release DVC y hash -> manifiesto y hash -> run MLflow elegido -> checkpoint -> versión -> S3 bucket/key y SHA-256 -> predicción de prueba desde el portal.
2. Confirma git status limpio, CI en verde en main y que no hay secretos (gitleaks o similar sobre el historial de P3).
3. Crea el tag git 'p3-entrega' y compártelo con el equipo.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Tabla de trazabilidad sin celdas vacías
- [ ] Tag creado sobre commit con CI verde

**Entregables:** `docs/p3/trazabilidad.md`; Tag p3-entrega

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Edith
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
