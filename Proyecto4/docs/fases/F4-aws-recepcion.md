# F4 — Recepción y persistencia en AWS

| Campo | Valor |
|---|---|
| Responsable | Emilio (Líder de AWS · portal · integración) |
| Revisor de PRs | Edith |
| Fechas | 7 oct → 8 oct de 2026 |
| Rama | `feat/p4-fase-4-aws-recepcion` |
| Puntos de rúbrica | 10 (4.1 y 4.2) |
| Depende de | F1 (contrato) |
| Bloquea a | F5, F6 |
| Control | Control 2 |

**Nota de calendario:** arranca el miércoles 7 en cuanto el contrato del evento está escrito, en paralelo a la optimización. El jueves 8 debe haber una imagen de prueba persistida.

> Antes de empezar lee `AGENTS.md`, `docs/decisiones.md` (servicios de AWS) y `docs/contratos.md` (evento y reglas de recepción). Trabaja los bloques en orden.

## Rúbrica (10 puntos)

- **4.1 Evento completo y vinculado (5):** fotografía, ID, fecha con zona horaria, clase, confianza válida, dispositivo, versión optimizada y recorte si aplica; los metadatos locales coinciden con el registro recibido.
- **4.2 Persistencia real en AWS (5):** captura recuperable en el servicio usado, respaldada por una consulta de lectura o un recurso identificado. Una URL pública sola no demuestra AWS.

## Bloques de trabajo

- **Recepción:** recibir fotografía y metadatos según el contrato, reutilizando los servicios existentes.
- **Validación del evento:** rechazar o señalar eventos sin zona horaria, con confianza fuera de 0 a 1 o sin versión del artefacto.
- **Persistencia:** guardar imagen y registro; agregar fecha de recepción y clave de la imagen.
- **Idempotencia:** un reintento con el mismo ID de captura no crea un duplicado.
- **Consulta de solo lectura:** dejar lista la consulta que el equipo ejecutará en la demostración para mostrar un registro y el recurso de AWS donde vive, sin entregar credenciales.
- **Consulta y exportación:** listado ordenado por fecha para el portal y exportación de eventos en CSV o JSON.

## Cómo se cierra

- [ ] Una imagen de prueba enviada, guardada y recuperable
- [ ] El registro recibido coincide con los metadatos enviados
- [ ] El mismo ID enviado dos veces aparece una sola vez
- [ ] Consulta de lectura documentada y probada
- [ ] Configuración sin credenciales reales en Git
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
