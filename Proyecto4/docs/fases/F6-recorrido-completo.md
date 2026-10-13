# F6 — Primer recorrido completo, de la cámara al portal

| Campo | Valor |
|---|---|
| Responsable | Emilio (Líder de AWS · portal · integración); Bryan opera el dispositivo |
| Revisor de PRs | Edith |
| Fechas | 9 oct → 12 oct de 2026 |
| Rama | `feat/p4-fase-6-recorrido-completo` |
| Puntos de rúbrica | 5 (4.3; requisito M3) |
| Depende de | F3, F4, F5 |
| Bloquea a | F9, F11 |
| Control | Control 2 |

**Nota de calendario:** el primer intento es el viernes 9, en cuanto F3 clasifica y F5 está desplegada; se cierra el lunes 12 y es el centro del Control 2. Emilio lidera y Bryan opera el dispositivo.

> Antes de empezar lee `AGENTS.md` y `docs/contratos.md` (comportamiento del dispositivo ante fallos). Trabaja los bloques en orden.

## Rúbrica (5 puntos)

- **4.3 Fallo y reintento controlados (5):** el equipo provoca un envío fallido de forma reversible, muestra el error y reintenta el mismo evento; queda un solo registro del ID con su imagen recuperable. Basta el reintento manual.
- **Requisito mínimo M3:** fotografías nuevas y resultados llegan a AWS y aparecen en Capturas Edge del portal previo. Si no se cumple, la nota queda limitada a 60.

## Bloques de trabajo

- [ ] **Conexión:** unir el envío del dispositivo con el servicio de recepción de F4.
- [ ] **Fallo reversible:** definir cómo se provoca el fallo de envío en la demostración sin dañar el entorno, por ejemplo apuntando a un destino inválido o cortando la red.
- [ ] **Reintento:** mostrar el error en el dispositivo y permitir reintento manual con el mismo ID. El registro local se conserva aunque el envío falle.
- [ ] **Trazabilidad:** seguir una captura nueva por imagen, ID, fecha y clasificación en dispositivo, AWS y portal. — Herramienta lista: [`scripts/trazar_captura.py`](../../scripts/trazar_captura.py) (solo lectura; pruebas en [`tests/test_traza.py`](../../tests/test_traza.py)). Falta la primera traza real con las tres fuentes.

## Cómo se cierra

- [ ] Una fotografía nueva de la cámara visible en Capturas Edge
- [ ] Imagen, ID, clase y versión coinciden en dispositivo, AWS y portal
- [ ] Un envío fallido y reintentado deja un solo registro
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-12 | Emilio | Trazabilidad (herramienta) | `scripts/trazar_captura.py`: dado un `capture_id`, lee la línea del `events.jsonl` y la foto local del dispositivo, el registro y la imagen en S3 (`head-object`/`get-object`, sin escribir) y el registro y la imagen del portal con basic_auth (credenciales desde `P4_PORTAL_USUARIO`/`P4_PORTAL_PASSWORD`; si faltan, se omite y se avisa). Tabla por campo (capture_id, clase, confianza, versión y SHA-256 del modelo, captured_at, image_sha256) y SHA-256 de la imagen en dispositivo, S3 (metadatos y descarga) y portal; salida 1 si algo no coincide, 2 si falta en S3. 25 pruebas sin AWS (121 en P4). Prueba de humo de solo lectura contra S3 con `44e6a9b3-e5dc-4d92-a8e6-9c7e0a0c65b0`: registro y metadatos coinciden. | Traza real con dispositivo y portal (bloque 2). |
