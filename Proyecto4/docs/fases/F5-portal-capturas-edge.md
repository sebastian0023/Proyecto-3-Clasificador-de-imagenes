# F5 — Portal: sección Capturas Edge

| Campo | Valor |
|---|---|
| Responsable | Emilio (Líder de AWS · portal · integración) |
| Revisor de PRs | Edith |
| Fechas | 8 oct → 9 oct de 2026 |
| Rama | `feat/p4-fase-5-portal-capturas-edge` |
| Puntos de rúbrica | 10 (5.1, 5.2 y 5.3) |
| Depende de | F4 |
| Bloquea a | F6 |
| Control | Control 2 |

**Nota de calendario:** empieza el jueves 8 con la consulta de F4 y queda desplegada el viernes 9, antes del primer recorrido completo.

> Antes de empezar lee `AGENTS.md`, `docs/decisiones.md` (ubicación de Capturas Edge) y `docs/contratos.md`. Trabaja los bloques en orden.

## Rúbrica (10 puntos)

- **5.1 Integración y acceso (3):** sección accesible desde la navegación del portal de los Proyectos 1 a 3, desplegada en AWS. Una galería aislada vale como máximo 1.5.
- **5.2 Imagen y metadatos reales (4):** fotografía, clase, confianza, fecha, ID, dispositivo y versión coinciden con los registros de AWS, de más reciente a más antigua.
- **5.3 Consulta funcional (3):** una captura nueva aparece al refrescar; carga, lista vacía y error tienen mensajes útiles.

## Bloques de trabajo

- **Navegación:** sección accesible desde el menú del portal existente y desplegada en AWS.
- **Galería:** fotografía, clase, confianza, fecha, ID de captura, dispositivo y versión del modelo; recorte si aplica.
- **Orden y actualización:** de más reciente a más antigua, con botón de actualizar o actualización automática.
- **Estados:** mensajes para carga, error y lista vacía.
- **Acceso de evaluación:** si el portal pide inicio de sesión, preparar un acceso limitado para el evaluador.

## Cómo se cierra

- [ ] La sección abre desde la navegación del portal desplegado
- [ ] Muestra los registros reales de F4, no datos fijos
- [ ] Los metadatos coinciden con los de AWS en una captura de prueba
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
