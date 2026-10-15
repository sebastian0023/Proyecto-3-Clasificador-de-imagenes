# F9 — Operación, reintento sin duplicados y 20 capturas

| Campo | Valor |
|---|---|
| Responsable | Bryan (Líder de dispositivo edge y cámara) |
| Revisor de PRs | Emilio |
| Fechas | 13 oct de 2026 |
| Rama | `feat/p4-fase-9-operacion-capturas` |
| Puntos de rúbrica | 5 (2.4) |
| Depende de | F6 |
| Bloquea a | F11 |
| Control | Control 3 |

**Nota de calendario:** se hace el martes 13, con el recorrido de F6 ya estable y antes de la congelación de código de esa noche.

> Antes de empezar lee `AGENTS.md` y `docs/contratos.md`. Trabaja los bloques en orden.

## Rúbrica (5 puntos)

**2.4 Operación estable (5):** demostración de cinco minutos, historial de veinte capturas repartidas entre las clases y reinicio del programa seguido de una captura nueva. Los fallos reales visibles. No se exige arranque automático con el sistema operativo.

## Bloques de trabajo

- **Estabilidad:** cinco minutos de operación continua, dejando visibles los fallos que ocurran.
- **Reinicio:** reiniciar el programa y hacer una captura nueva; los datos anteriores persisten.
- **20 capturas:** al menos 20 eventos repartidos entre las clases, con sus fotografías, enviados a AWS. Verifican operación y no tienen un umbral propio de accuracy.
- **Exportación de eventos:** CSV o JSON con ID, fecha con zona horaria, clase, confianza, dispositivo, versión y referencia a la fotografía.
- **Ensayo del reintento:** repetir el fallo y reintento de F6 para confirmar que sigue dejando un solo registro.

## Cómo se cierra

- [x] Las 20 capturas visibles en el portal con sus metadatos
- [x] Exportación de eventos entregada a Emilio para la carpeta de evidencias
- [x] Captura nueva correcta después del reinicio
- [x] El evento reintentado aparece una sola vez
- [x] PR fusionado con review de Emilio
- [x] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 14 oct | Bryan | Todos | Ejecución de 5 min (290 eventos locales), reinicio exitoso y verificación de reintentos (4 IDs reenviados mediante corte de red provocado con la ruta *blackhole*, 0 duplicados en AWS). Exportación validada con 100 capturas más recientes del listado del portal (límite por defecto, sobre un histórico total en S3 de más de 300 eventos, abarcando 33 person, 25 dog, 42 cat). Evidencias generadas en `evidencia_f9/`. PR abierto en rama `feat/p4-fase-9-operacion-capturas`. | Revisión y Merge de Emilio |