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

- [x] **Conexión:** unir el envío del dispositivo con el servicio de recepción de F4. — `dispositivo/edge_camera.py` (F3, en `main`) envía al receptor desplegado `https://174-129-84-80.sslip.io/api/p4/captures` con el token del dispositivo: 133 capturas de `edge01` en S3 (lectura del 13 oct).
- [x] **Fallo reversible:** definir cómo se provoca el fallo de envío en la demostración sin dañar el entorno, por ejemplo apuntando a un destino inválido o cortando la red. — Guion en [`docs/demo-f6.md`](../demo-f6.md): ruta *blackhole* en la Pi hacia la IP del portal (ensayada el 12 oct, [`evidencia_f3/ejecucion_offline.txt`](../../evidencia_f3/ejecucion_offline.txt)) y, como alternativa, `--url` a un host inexistente; nada se toca en AWS.
- [x] **Reintento:** mostrar el error en el dispositivo y permitir reintento manual con el mismo ID. El registro local se conserva aunque el envío falle. — El dispositivo muestra `Fallo de conexión`, guarda foto y evento antes de enviar y deja la captura en `pendientes.json` (persistente); la reenvía con el mismo `capture_id` en cada ciclo y al reiniciar. Ensayo: 7 capturas fallaron entre 1 y 7 veces y se reenviaron con un solo `201` cada una; la cola quedó vacía (`pendientes.json` = `[]`).
- [x] **Trazabilidad:** seguir una captura nueva por imagen, ID, fecha y clasificación en dispositivo, AWS y portal. — [`scripts/trazar_captura.py`](../../scripts/trazar_captura.py) (solo lectura; pruebas en [`tests/test_traza.py`](../../tests/test_traza.py)) sobre los 7 IDs del ensayo: las tres fuentes coinciden (tabla abajo).

## Cómo se cierra

- [x] Una fotografía nueva de la cámara visible en Capturas Edge (`bf2e1822-61a7-4439-a1ba-5ee395e3c026` en la galería del portal desplegado: foto de la Pi, person 98.74 %, `edge01`, `1.0.0-int8.1`, fechas iguales a S3; `portal_bf2e1822.jpg`; el portal sirve registro e imagen de los 7 IDs, `GET` `200`/`200` en las trazas)
- [x] Imagen, ID, clase y versión coinciden en dispositivo, AWS y portal (7 trazas: 8 de 8 filas iguales, imagen con el mismo SHA-256 en la foto de la Pi, el evento, S3 y el portal; `trazas/traza_<id>.txt`)
- [x] Un envío fallido y reintentado deja un solo registro (los 7 IDs del ensayo: fallos de conexión y un solo `201` en `ejecucion_offline.txt`; 1 registro por ID en `edge-captures/events/` según las trazas)
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-12 | Emilio | Trazabilidad (herramienta) | `scripts/trazar_captura.py`: dado un `capture_id`, lee la línea del `events.jsonl` y la foto local del dispositivo, el registro y la imagen en S3 (`head-object`/`get-object`, sin escribir) y el registro y la imagen del portal con basic_auth (credenciales desde `P4_PORTAL_USUARIO`/`P4_PORTAL_PASSWORD`; si faltan, se omite y se avisa). Tabla por campo (capture_id, clase, confianza, versión y SHA-256 del modelo, captured_at, image_sha256) y SHA-256 de la imagen en dispositivo, S3 (metadatos y descarga) y portal; salida 1 si algo no coincide, 2 si falta en S3. 25 pruebas sin AWS (121 en P4). Prueba de humo de solo lectura contra S3 con `44e6a9b3-e5dc-4d92-a8e6-9c7e0a0c65b0`: registro y metadatos coinciden. | Traza real con dispositivo y portal (bloque 2). |
| 2026-10-13 | Emilio | Traza real (7 IDs del ensayo sin red) | Archivos de la Pi (7 fotos, `events.jsonl`, `pendientes.json`): `sha256sum -c` contra `sha_f6.txt` de la Pi → 9/9 OK; `pendientes.json` = `[]`; cada ID una sola vez en `events.jsonl`, con la misma línea que en `evidencia_f3/eventos.txt`. Traza con las tres fuentes (portal con basic_auth): los 7 con `TODO COINCIDE`, 8 de 8 filas, imagen igual en 5 fuentes, 1 registro por ID (tabla de abajo). | — (captura de pantalla de `bf2e1822` en la galería guardada: `portal_bf2e1822.jpg`). |
| 2026-10-13 | Emilio | Guion de la demo | [`docs/demo-f6.md`](../demo-f6.md): corte reversible con ruta *blackhole* en la Pi (opción principal, la del ensayo) o `--url` a un host inexistente; quién hace qué; traza y portal después del reintento; `200 duplicate` opcional con `enviar_captura.py --reenviar`; qué no hacer y cómo revertir. Hallazgo: el dispositivo saca de la cola cualquier 4xx, así que el fallo de la demo debe ser de red o 5xx (una ruta inválida en el portal daría `401` y la captura no se reintentaría). | Confirmar con Bryan el comando exacto de la ruta *blackhole*. |
| 2026-10-13 | Emilio | Resumen para F9 | S3 (lectura): 133 capturas de `edge01`: 101 del código nuevo (`{capture_id}.jpg`, preprocess de Edith; cat 23, dog 14, person 64; confianza sin redondear) y 32 del código viejo (`edge01-*.jpg`; cat 7, dog 3, person 22; confianza a 4 decimales). Ninguna con warnings. **Hallazgo:** el `events.jsonl` de la Pi tiene 169 capturas del código nuevo y 68 no están en S3 (67 seguidas del 12 oct 21:59:48 a 22:07:12 UTC y 1 a las 23:16:15), con `pendientes.json` vacío; incluye IDs citados en `evidencia_f3/eventos.txt`. **Hipótesis principal:** en `edge_camera.py`, si `P4_DEVICE_TOKEN` no está definido, `enviar_aws` imprime una advertencia y devuelve `True`, así que la captura no se envía ni entra en la cola; coincide con las 68 y la cola vacía. | Confirmar con Bryan si ese tramo corrió sin el token antes de elegir las 20 de F9 (no se tocó su código). |

## Traza de los 7 IDs del ensayo sin red (13 oct)

Dispositivo (`events.jsonl` y fotos de la Pi), S3 (perfil `p4-emilio`, solo lecturas) y portal desplegado (basic_auth). Todos `person`.

| capture_id | confianza | captured_at (Pi, UTC) | received_at (AWS) | VersionId del registro | Registros | Resultado |
|---|---:|---|---|---|---:|---|
| `bf2e1822-61a7-4439-a1ba-5ee395e3c026` | 0.9874191880226135 | 2026-10-12T22:15:56.034527 | 2026-10-12T22:16:44.351 | `vHGMSuXlom784szP4T0lUD20EJoXoeum` | 1 | coincide (8/8) |
| `ffff74f0-ebc0-4c20-84c0-181ae078a298` | 0.9856405258178711 | 2026-10-12T22:16:02.492260 | 2026-10-12T22:16:47.274 | `Fb32dY3l3PsCT2RurFvN1FVV6WSWIiLZ` | 1 | coincide (8/8) |
| `ff24163f-fc90-4279-b224-6a98b5b406ae` | 0.9876047372817993 | 2026-10-12T22:16:08.868617 | 2026-10-12T22:16:48.281 | `J8ExCdGrxptolBm3l1nbDa8Sxnz4EyHj` | 1 | coincide (8/8) |
| `8a474355-4297-4f70-b93e-83ed83ff7534` | 0.9870089888572693 | 2026-10-12T22:16:15.274061 | 2026-10-12T22:16:52.498 | `SyUJjSeJTP9tjuE4Kn8OqpilhAuaEvkY` | 1 | coincide (8/8) |
| `2d2fb732-b74d-45fa-a66c-e7c36dfd3e36` | 0.983082115650177 | 2026-10-12T22:16:21.671066 | 2026-10-12T22:16:54.516 | `FK3L3HmDHmEvaOmpvFZMFjrb2yGpVTmE` | 1 | coincide (8/8) |
| `b7faabf1-343a-4fba-a34b-f01d112326c6` | 0.9915691018104553 | 2026-10-12T22:16:28.113487 | 2026-10-12T22:16:56.244 | `QL4SMBfWVkU0U.Q5uOb7oQBy1t5NBJpO` | 1 | coincide (8/8) |
| `004325d5-236a-418c-9949-21d21ead4573` | 0.9593096971511841 | 2026-10-12T22:16:34.548778 | 2026-10-12T22:17:04.274 | `MyKL.zvM4_y8L7caAhDhTccXMVKFYRKH` | 1 | coincide (8/8) |

Las 8 filas comparadas: `capture_id`, `predicted_class`, `confidence`, `model_version` (`1.0.0-int8.1`), `model_sha256` (`ca689c4e…69c0`), `captured_at`, `image_sha256` y el SHA-256 de la imagen en la foto de la Pi, el evento, S3 (metadatos y descarga) y el portal. Entre la captura y la recepción hay de 30 a 48 s: el tiempo sin red más el reenvío desde la cola.

## Evidencia para F10

Fuera del repo, en `C:\MLOps_Project_Four\evidencia_f6\` (se copia a la carpeta de evidencias en F10, sin tokens ni contraseñas):

| Archivo | Qué demuestra |
|---|---|
| `<capture_id>.jpg` (7), `events.jsonl`, `pendientes.json` | Fotos y registro local de la Pi (copiados por Bryan) |
| `home/bryan/sha_f6.txt`, `integridad_sha_f6.txt` | SHA-256 calculados en la Pi y verificación 9/9 OK en la laptop |
| `verificacion_eventos_7_ids.txt` | Cada ID una vez en `events.jsonl`, igual que en `evidencia_f3/eventos.txt`; fallos y un solo `201` por ID en `ejecucion_offline.txt` |
| `trazas/sin_portal/traza_<id>.txt` (7) | Traza dispositivo + S3 |
| `trazas/traza_<id>.txt` (7), `resumen_trazas_7_ids.md` | Traza de las tres fuentes y tabla resumen |
| `s3_registros_snapshot.json` | Lectura de los 136 registros de S3 del 13 oct (base del resumen para F9) |
| `resumen_edge01_para_f9.txt`, `analisis_68_sin_s3.txt` | Capturas de `edge01` por código, clase y warnings; las 68 del dispositivo que no están en S3 y la hipótesis del token ausente |
| `portal_bf2e1822.jpg` | La captura `bf2e1822` en Capturas Edge del portal desplegado, con los mismos datos que S3 |
