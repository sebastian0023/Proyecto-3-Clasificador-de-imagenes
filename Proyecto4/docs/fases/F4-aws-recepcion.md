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

- [x] **Recepción:** recibir fotografía y metadatos según el contrato, reutilizando los servicios existentes. — `POST /api/p4/captures` en el FastAPI del portal ([`src/p4/captures/api.py`](../../src/p4/captures/api.py)); pruebas en [`tests/test_recepcion.py`](../../tests/test_recepcion.py) (16 pasan).
- [x] **Validación del evento:** rechazar o señalar eventos sin zona horaria, con confianza fuera de 0 a 1 o sin versión del artefacto. — [`src/p4/captures/validation.py`](../../src/p4/captures/validation.py): 422 `evento_invalido` con todos los problemas juntos; reloj adelantado más de 5 min se señala (`captured_at_en_el_futuro`) sin rechazar. Pruebas en [`tests/test_validacion.py`](../../tests/test_validacion.py).
- [x] **Persistencia:** guardar imagen y registro; agregar fecha de recepción y clave de la imagen. — [`src/p4/captures/s3_store.py`](../../src/p4/captures/s3_store.py) en `s3://dataset-quality-releases-750702272375/edge-captures/`; registro con `received_at`, `image_key`, `image_bytes`, dimensiones, `delivery_delay_s` y `warnings`. Pruebas en [`tests/test_persistencia.py`](../../tests/test_persistencia.py); captura real `f4-prueba-20261008-0001` (ver Registro de avance).
- [x] **Idempotencia:** un reintento con el mismo ID de captura no crea un duplicado. — `PutObject` con `If-None-Match: *`; reintento idéntico → `200 duplicate` sin escribir; mismo ID con otros datos → `409 conflicto_capture_id`. Pruebas en [`tests/test_idempotencia.py`](../../tests/test_idempotencia.py); reenvío real de `f4-prueba-20261008-0001` → 200 y un solo registro.
- [ ] **Consulta de solo lectura:** dejar lista la consulta que el equipo ejecutará en la demostración para mostrar un registro y el recurso de AWS donde vive, sin entregar credenciales.
- [ ] **Consulta y exportación:** listado ordenado por fecha para el portal y exportación de eventos en CSV o JSON.

## Cómo se cierra

- [x] Una imagen de prueba enviada, guardada y recuperable (`f4-prueba-20261008-0001`: `get-object` devuelve 238 034 bytes con el mismo SHA-256 que la foto)
- [x] El registro recibido coincide con los metadatos enviados (11 de 11 campos, comparación campo por campo)
- [x] El mismo ID enviado dos veces aparece una sola vez (reenvío → `200 duplicate`; `s3 ls` muestra un registro y una imagen; `VersionId` del registro sin cambio)
- [ ] Consulta de lectura documentada y probada
- [ ] Configuración sin credenciales reales en Git
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-08 | Emilio | Recepción | Router `POST /api/p4/captures` (multipart `event` + `image`, token Bearer, JPEG ≤ 5 MB, forma del evento con campos desconocidos rechazados) montado en el portal; compose monta `Proyecto4/src` y `~/.aws` (solo lectura); variables `P4_*` en `.env.example`. 16 pruebas. | Validación semántica (bloque 2); escritura en S3 (bloque 3): hasta entonces responde 503 `receptor_no_configurado`. |
| 2026-10-08 | Emilio | Validación del evento | Reglas del contrato antes de guardar: zona horaria obligatoria, confianza finita en [0, 1], versión aceptada y SHA-256 del modelo que le corresponde, clase `cat`/`dog`/`person`, `image_sha256` igual al de la imagen recibida, formato de `capture_id` y `device_id`, región dentro de la imagen. Aviso `captured_at_en_el_futuro` (sin rechazo) y `delivery_delay_s` informativo. 52 pruebas en total. | Escritura en S3 (bloque 3). |
| 2026-10-08 | Emilio | Persistencia | `S3CaptureStore`: imagen byte por byte con metadatos `sha256` y `capture-id`, después el registro JSON con los campos del receptor; errores de S3 → 503 visible con el código de S3. Receptor real en Docker Compose (`p4-emilio`). Captura `f4-prueba-20261008-0001` enviada el 8 oct 23:53 (-06:00): imagen `edge-captures/images/f4-prueba-20261008-0001.jpg` (VersionId `icZio54eDr2va6q3uSInCXuBD1UWlThQ`, 238 034 bytes, SHA-256 `c898dd12…2f7a` en metadatos e igual al de la foto descargada) y registro `edge-captures/events/f4-prueba-20261008-0001.json` (VersionId `Ti1VGCMyvBfeilNL8XS0Siut6LiSBsgS`, `received_at` `2026-10-09T05:53:22.210+00:00`). 11/11 campos enviados iguales en el registro. **Notas:** la clase y la confianza (dog 0.8859987854957581) salen de la variante `1.0.0-int8.1` corrida en **x86 (laptop), no en la Pi**: en aarch64 las probabilidades pueden variar (`docs/artefacto.md`); `captured_at` es la **hora de guardado del archivo** (la foto no trae EXIF), no la hora real de la toma. Suite de Proyecto2 en el contenedor: 278 pasan. | F10: copiar la evidencia de `C:\MLOps_Project_Four\evidencia_f4\` a la carpeta de evidencias del repo, sin tokens ni rutas sensibles. |
| 2026-10-08 | Emilio | Idempotencia | Escritura condicional `If-None-Match: *` en imagen y registro; comparación de los campos del dispositivo ante un 412 (igual → `200 duplicate`, distinto → `409` con los campos). Reenvío real del mismo evento → `HTTP 200 duplicate` con el `received_at` original; `s3 ls edge-captures/` muestra 1 registro y 1 imagen; el `VersionId` del registro no cambió. 68 pruebas de P4 en total. | Ningún workflow de `.github/` corre todavía `Proyecto4/tests`. |
