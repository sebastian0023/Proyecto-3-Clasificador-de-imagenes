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

- [ ] **Navegación:** sección accesible desde el menú del portal existente y desplegada en AWS. — Entrada `Capturas Edge` (`#/edge-captures`) en `PAGES` de `Proyecto2/web/src/App.tsx`, entre Inference y Settings (decisión 6); probada en local. Falta: desplegada en AWS.
- [x] **Galería:** fotografía, clase, confianza, fecha, ID de captura, dispositivo y versión del modelo; recorte si aplica. — [`Proyecto2/web/src/pages/EdgeCaptures.tsx`](../../../Proyecto2/web/src/pages/EdgeCaptures.tsx): foto de `GET /api/p4/captures/{id}/image`, `captured_at` con su zona explícita, `received_at` en UTC, confianza en % y exacta, recorte dibujado sobre la foto y warnings.
- [x] **Orden y actualización:** de más reciente a más antigua, con botón de actualizar o actualización automática. — Orden del backend; botón «Actualizar» y auto-actualización cada 30 s (desactivable, solo con la pestaña visible).
- [x] **Estados:** mensajes para carga, error y lista vacía. — Carga, lista vacía, error con código y mensaje del receptor (si falla una actualización se conserva la última lista y se avisa), `errores` del listado e imagen que no carga. Pruebas en [`Proyecto2/web/tests/edge-captures.test.tsx`](../../../Proyecto2/web/tests/edge-captures.test.tsx).
- [ ] **Acceso de evaluación:** si el portal pide inicio de sesión, preparar un acceso limitado para el evaluador. — Decidido con el PM: usuario y contraseña de Caddy (`basic_auth`) en todo el portal excepto `POST /api/p4/captures`. Pendiente del despliegue.

## Cómo se cierra

- [ ] La sección abre desde la navegación del portal desplegado
- [ ] Muestra los registros reales de F4, no datos fijos
- [ ] Los metadatos coinciden con los de AWS en una captura de prueba
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-09 | Emilio | Galería, orden y estados (local) | Página Capturas Edge en el portal (React, solo endpoints de F4, sin datos fijos). `api.ts` lee también `mensaje` de los errores del receptor de P4. Pruebas web: Vitest 71 (13 nuevas de la página y 1 de navegación), `npm test` 5, `npm run build` OK; P4 96; Proyecto2 278 en el contenedor. Verificado en local (Vite contra el portal en Docker, que lee S3 con `p4-emilio`): aparece `f4-prueba-20261008-0001` con dog, 0.8859987854957581, `f4-prueba`, `1.0.0-int8.1`, 2026-10-08 23:35:54 (UTC-06:00), igual que en S3. | Captura nueva al pulsar Actualizar (falta foto e ID aprobados); despliegue en AWS (Parte 2). |
| 2026-10-09 | Emilio | Despliegue (preparación, sin recursos creados) | Lecturas con `p4-emilio`: perfil de instancia `p4-portal-ec2` existe; VPC por defecto `vpc-0d050a1c3a92dcdb8`, subnet `subnet-0b1edac74e6b7aada`; AMI AL2023 `ami-0d27e0fb3bac4d724`; repo público. Archivos: `docker-compose.prod.yml` (sin volúmenes de código, solo Caddy publica 80/443, topes de memoria), etapa `prod` del Dockerfile (P3 y P4 dentro de la imagen; base compose fija `target: app`), `Caddyfile` (validado con `caddy validate`), `instalar_instancia.sh` y `preparar_secretos.sh` (ShellCheck sin advertencias) y [`docs/despliegue.md`](../despliegue.md). MLflow sin jobs y con 1 worker: 2 294 → 351 MiB (medido): el stack cabe en t3.medium (≈ 1.5 GiB en reposo). | Crear SG, instancia e IP elástica (cada paso con visto bueno); verificar el rol en S3; captura por HTTPS. |
