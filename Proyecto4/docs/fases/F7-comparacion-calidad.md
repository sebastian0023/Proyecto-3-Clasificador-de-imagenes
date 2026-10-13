# F7 — Comparación de calidad, original contra optimizado

| Campo | Valor |
|---|---|
| Responsable | Edith (Líder de modelo y optimización) |
| Revisor de PRs | Bryan |
| Fechas | 8 oct → 9 oct de 2026 |
| Rama | `feat/p4-fase-7-comparacion-calidad` |
| Puntos de rúbrica | 10 (1.3) |
| Depende de | F2 |
| Bloquea a | F10 |
| Control | Control 2 |

**Nota de calendario:** empieza el jueves 8 en cuanto la variante de F2 está lista y el reporte se cierra el viernes 9. Si la caída de accuracy supera 2 puntos porcentuales, se regresa a F2 ese mismo viernes para probar otra configuración antes del lunes 12.

> Antes de empezar lee `AGENTS.md` y `docs/decisiones.md` (datos de comparación). El test del Proyecto 3 no se toca. Trabaja los bloques en orden.

## Rúbrica (10 puntos)

**1.3 Calidad comparada correctamente**, desglosada así:

- **3 puntos:** mismas muestras y clases, con predicciones individuales verificables.
- **3 puntos:** accuracy y F1 macro recalculables, resultados por clase y explicación de errores.
- **2 puntos:** calibración solo con entrenamiento, si aplica, y test fuera de cualquier ajuste.
- **2 puntos:** caída de accuracy de hasta 2 puntos porcentuales respecto al original. No se exige volver a obtener 85%.

## Bloques de trabajo

- **Evaluación común:** ambos modelos sobre la misma validación del Proyecto 3, con el mismo manifiesto y etiquetas.
- **Predicciones por muestra:** CSV o JSON con una fila por muestra: identificador, clase real, clase predicha por el original y clase predicha por el optimizado.
- **Revisión del manifiesto:** sin muestras faltantes, sin IDs duplicados, etiquetas coincidentes y todas las clases declaradas incluidas.
- **Métricas:** accuracy, F1 por clase y macro sobre el mapa de clases completo (F1 = 0 para una clase sin predicciones positivas), soporte por clase y caída en puntos porcentuales sin redondear.
- **Explicación de errores:** qué clases se ven afectadas por la optimización y por qué.
- **Separación de datos:** dejar constancia de la procedencia de los datos de calibración y de que el test no se usó. Si la técnica no necesitó calibración, los 2 puntos se verifican con el procedimiento de conversión y la procedencia de los datos comparados; no hace falta un manifiesto de calibración inexistente.

## Cómo se cierra

- [x] Predicciones por muestra entregadas y recalculables: [`predicciones_validacion.csv`](../../calidad/registros/predicciones_validacion.csv), 292 filas (una por muestra de `val`), con las probabilidades completas de cada modelo en `pred_original.csv` y `pred_optimizado.csv`
- [x] Reporte antes y después con métricas por clase y errores explicados: [`docs/calidad.md`](../calidad.md) y [`metricas.json`](../../calidad/registros/metricas.json). Solo `0.1.3:a554` cambia (dog → person; el original ya dudaba, con 0.55)
- [x] Caída de accuracy de hasta 2 puntos porcentuales: 0.9965753424657534 → 0.9931506849315068, **0.3424657534246589 pp**, con el INT8 evaluado en aarch64 (entorno de la Pi)
- [x] Procedencia de calibración y exclusión del test anotadas: [`calidad.md` § Separación de datos](../calidad.md#separación-de-datos) y decisión 3 en [`decisiones.md`](../decisiones.md)
- [ ] PR fusionado con review de Bryan
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-13 | Edith | Evaluación común, predicciones, revisión del manifiesto, métricas, errores y separación | `calidad/predecir.py` (original en PyTorch; INT8 en aarch64 con CPU Cortex-A53 emulada, Debian 13 y onnxruntime 1.31.0, igual que la Pi) y `calidad/comparar.py`. Accuracy 0.99658 → 0.99315 (caída de 0.342 pp), F1 macro 0.99537 → 0.99209; 291/292 iguales. Decisión 3 cerrada. PR de F7 | Review de Bryan |
