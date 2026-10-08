# F2 — Variante optimizada y conversión reproducible

| Campo | Valor |
|---|---|
| Responsable | Edith (Líder de modelo y optimización) |
| Revisor de PRs | Bryan |
| Fechas | 7 oct → 8 oct de 2026 |
| Rama | `feat/p4-fase-2-optimizacion` |
| Puntos de rúbrica | 15 (1.1 y 1.2; requisito M1) |
| Depende de | F1 |
| Bloquea a | F3, F7, F8 |
| Control | Control 2 |

**Nota de calendario:** la conversión se intenta el miércoles 7 para detectar pronto operadores no soportados. La variante final se entrega a Bryan el jueves 8 al mediodía.

> Antes de empezar lee `AGENTS.md`, `docs/decisiones.md` (formato, runtime y técnica) y `docs/contratos.md`. Trabaja los bloques en orden.

## Rúbrica (15 puntos)

- **1.1 Continuidad con el modelo existente (5):** original identificado contra el Proyecto 3, con clases y preprocesamiento conservados.
- **1.2 Optimización real y variante ejecutable (10):** técnica respaldada por artefacto y configuración, conversión reproducible y variante cargada en el edge. Exportar o cambiar de formato sin un efecto comprobable limita el criterio a 5; sustituir el modelo por uno ajeno lo deja en 0.

## Bloques de trabajo

- **Conversión:** aplicar la técnica elegida a los pesos del Proyecto 3, sin sustituir el modelo.
- **Registro de conversión:** guardar la salida del proceso identificando archivo de entrada y de salida, con sus hashes SHA-256. Los hashes solos no prueban el parentesco entre modelos.
- **Técnica y efecto:** documentar qué técnica se aplicó, formato y precisión resultantes, y la evidencia de su efecto en el artefacto o en el runtime.
- **Reproducibilidad:** guardar script de conversión, configuración, dependencias y versiones.
- **Calibración:** si la técnica la requiere, usar solo muestras de entrenamiento y guardar un manifiesto con sus IDs.
- **Prueba de humo:** inferir una entrada conocida y comparar la clase con la del original.
- **Ficha del artefacto:** enlaces de descarga, versión, formato, precisión, runtime y hashes.

## Cómo se cierra

- [ ] Variante cargable en el runtime del dispositivo
- [ ] Registro de conversión que une el original del Proyecto 3 con la variante
- [ ] Técnica explicada con evidencia de su efecto
- [ ] Orden de clases y preprocesamiento idénticos al original
- [ ] Conversión reproducible desde el repositorio
- [ ] Ficha del artefacto con enlaces de descarga y hashes
- [ ] PR fusionado con review de Bryan
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
