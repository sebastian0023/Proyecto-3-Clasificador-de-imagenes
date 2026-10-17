# F10 — README, pruebas y carpeta de evidencias

| Campo | Valor |
|---|---|
| Responsable | Emilio (Líder de AWS · portal · integración) |
| Revisor de PRs | Edith |
| Fechas | 13 oct → 14 oct de 2026 |
| Rama | `feat/p4-fase-10-readme-evidencias` |
| Puntos de rúbrica | 10 (6.1, 6.2 y 6.3) |
| Depende de | F7, F8 |
| Bloquea a | F11 |
| Control | Control 3 |

**Nota de calendario:** empieza el martes 13 con los reportes de F7 y F8, y se cierra el miércoles 14 por la mañana, antes del simulacro de F11. El código se congela el martes 13 por la noche.

> Antes de empezar lee `AGENTS.md`, `docs/rubrica.md` y `docs/decisiones.md`. Trabaja los bloques en orden.

## Rúbrica (10 puntos)

- **6.1 Instrucciones suficientes (4):** ficha y README permiten instalar, arrancar, recuperar artefactos y ejecutar el recorrido, con hardware y versiones documentados.
- **6.2 Comprobaciones repetibles (4):** pasos para comprobar carga y conversión, respuesta a entradas conocidas y evento enviado y recuperado. Valen pruebas automatizadas o una lista manual con resultados; no se exige TDD, CI nuevo ni cobertura.
- **6.3 Configuración operable y acceso controlado (2):** destino de AWS, identidad del dispositivo y artefacto configurables y documentados; plantilla sin secretos y acceso de evaluación limitado.

## Bloques de trabajo

- **Ficha de entrega:** equipo, dispositivo y cámara, sistema operativo, runtime, técnica, comandos de instalación y arranque, URL del portal y referencias a cada evidencia.
- **README:** instalación, configuración, recuperación del modelo, arranque de dispositivo y portal, y pasos de verificación.
- **Comprobaciones repetibles:** lista con comando o paso, resultado esperado y registro, para carga y conversión, inferencia sobre entradas conocidas y evento enviado y recuperado.
- **Configuración:** plantilla sin secretos donde se cambian destino de AWS, identidad del dispositivo y artefacto.
- **Carpeta de evidencias:** directorio o ZIP (la rúbrica acepta nombres y formatos equivalentes) con la lista de abajo.
  - Ficha de entrega y README breve.
  - Identificación del modelo existente: versión y referencia del P3, run ID si existe, pesos originales, clases y preprocesamiento.
  - Variante optimizada: archivo recuperable, formato y precisión, versión, SHA-256 y registro de conversión con entrada y salida.
  - Comparación de calidad: manifiesto de validación del P3, etiquetas, predicciones de original y optimizado por muestra, métricas y exclusiones si hubo.
  - Comparación de recursos: tamaño de ambos artefactos, al menos 100 tiempos de la variante tras 10 calentamientos, hardware y condiciones; tiempos del original si corre en ese dispositivo.
  - Exportación de las 20 capturas con sus fotografías.
  - Evidencia de AWS: registros persistidos, referencia del servicio o recurso y consulta de solo lectura.
  - Acceso al portal: URL de Capturas Edge, acceso de evaluación si pide inicio de sesión y cómo llegar desde la navegación del portal previo.
  - Enlace al video, si se entrega.
- **Acceso de evaluación:** acceso limitado al portal y consulta de solo lectura de AWS; ninguna credencial dentro del paquete. La rúbrica prohíbe pedir claves de AWS, contraseñas personales o acceso administrativo.

## Cómo se cierra

- [x] Edith o Bryan siguen el README de principio a fin sin ayuda

  > README seguido por Edith (con su agente) el 16 oct en un clon limpio de 49e318f, con los comandos tal como están escritos, salvo dos desviaciones indicadas:
  >
  > Paso 1: core.longpaths y clon.
  >
  > Paso 2: AWS CLI 2.38.1 con un perfil del equipo; SHA-256 del INT8 correcto, y tamaño y VersionId de los 3 modelos iguales a los publicados.
  >
  > Paso 3, en un contenedor linux/arm64 con CPU Cortex-A53 emulada (desviación: no hay Pi): instalación, sha256sum -c y arranque de edge_camera.py con el modelo y edge01; sin cámara, no se capturó.
  >
  > Paso 4, portal local (desviación: COMPOSE_PROJECT_NAME aparte para no tocar volúmenes existentes): up.py healthy; con el .env editado y up.py de nuevo, una captura de prueba enviada con scripts/enviar_captura.py da 201 y su reenvío 200 duplicate, con el registro y la imagen en S3, visible en Capturas Edge; 278 passed en el contenedor.
  >
  > Portal desplegado: 401 sin credenciales; no se probó el login de evaluador.
  >
  > Paso 5: 121 passed, traza de fbf85a5e TODO COINCIDE contra S3 y recalcular.py idéntico a lo registrado.
  >
  > Pendiente de corregir en el README: volver a correr up.py después de editar .env, e indicar el perfil de solo lectura del evaluador en los pasos 2 y 5.

  Las dos correcciones pendientes se aplicaron: volver a correr up.py después de editar .env, y credenciales del evaluador en los pasos 2 y 5 (portal con el usuario evaluador y enlace temporal del modelo, sin llaves de AWS, decisión del equipo del 16 oct).
- [x] Lista de comprobaciones ejecutada con resultados registrados → [`docs/comprobaciones.md`](../comprobaciones.md) (todas las filas con resultado, incluida la 3.2 con el portal: 8 de 8)
- [x] Carpeta de evidencias completa, con todos los enlaces abriendo → [`evidencias/INDICE.md`](../../evidencias/INDICE.md) cubre la tabla de la rúbrica, con las **20 de 20** capturas (7 cat, 7 dog, 6 person) en [`capturas_20/`](../../evidencias/capturas_20/) y sus fotos verificadas contra S3. Los enlaces relativos del INDICE, el README de `Proyecto4/`, la ficha, las comprobaciones y el README raíz abren, con sus anclas, y sus destinos están en Git. El video lo agrega F11 (opcional)
- [x] Sin credenciales reales en el repositorio ni en el paquete → gitleaks v8.30.1 con `.gitleaks.toml` sobre `Proyecto4/` (156 archivos versionados o nuevos) y `origin/main..HEAD`: sin hallazgos; búsqueda manual (`AKIA`, `Bearer` con valor, `$2a$`, `C:\Users`, `P4_DEVICE_TOKEN=` con valor, llaves privadas) sin valores reales
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-15 | Emilio | Comprobaciones repetibles | [`docs/comprobaciones.md`](../comprobaciones.md): hashes, tamaño y VersionId de los 3 artefactos en S3 (coinciden con `conversion_log.json` y `publicacion.json`); entradas conocidas de la Pi iguales a F7 (diferencia < 5e-7); traza de `fbf85a5e` en S3; 14/14 fotos de las 20 con su `image_sha256`; pytest Proyecto4 121 y Proyecto2 278 en el contenedor; recálculo de accuracy, F1 y p50/p95 con [`evidencias/comprobaciones/recalcular.py`](../../evidencias/comprobaciones/recalcular.py): todo coincide. Lo de la Pi se cita como ejecutado por Bryan. | Traza de `fbf85a5e` con el portal (credenciales de Emilio). |
| 2026-10-15 | Emilio | Carpeta de evidencias | [`evidencias/INDICE.md`](../../evidencias/INDICE.md) según la tabla de la rúbrica; traza de `fbf85a5e` con el portal: TODO COINCIDE, 8 de 8 ([`traza_fbf85a5e_portal.txt`](../../evidencias/comprobaciones/traza_fbf85a5e_portal.txt)); evidencia de F4–F6 copiada sin secretos; `head-object` de 3 de las 20; exportación completa (285 en CSV y JSON, igual a S3 en IDs y 9 campos: [`verificacion_export.txt`](../../evidencias/exportacion/verificacion_export.txt)); hallazgos del modelo con su confianza real leída de S3; decisión 8 cerrada. | 6 capturas `person` de las 20 (Bryan); `device_id` configurable, aprobado por el PM (PR de Bryan); seguimiento del README por Edith o Bryan; video (F11). |
| 2026-10-15 | Emilio | Secretos y enlaces | gitleaks v8.30.1 sobre `Proyecto4/` y `origin/main..HEAD` sin hallazgos; búsqueda manual sin valores reales; 174 enlaces relativos y anclas verificados. Casillas marcadas solo con evidencia. | Casilla de carpeta completa abierta hasta las 6 `person`. |
| 2026-10-15 | Emilio | Las 20 capturas | 6 `person` de la sesión de Bryan del 15 oct, sin cara y revisadas a la vista; en cada una coinciden el SHA-256 de la foto de S3, el `image_sha256`, el metadato de S3 y la foto de Bryan; `capturas_20.csv/json` con las 20 (7/7/6). Hallazgo nuevo en el [INDICE](../../evidencias/INDICE.md#hallazgos-del-modelo-en-las-capturas-recientes): 12 fotos de la pared de ladrillo sin nadie dieron `person` (0.9467–0.9697); recomendación de evitar ese fondo en la demo. Casilla de carpeta completa marcada. | `device_id` configurable (PR de Bryan); seguimiento del README por Edith o Bryan; video (F11). |
| 2026-10-15 | Emilio | Configuración y cámara | Con el PR #50 de Bryan ya en la rama: tabla de configuración del README (`P4_DEVICE_ID`/`--device-id`, validación), ficha (cámara `32e6:9221` y `device_id`) e INDICE (captura `2fc25b54…` con `edge01-demo`, comprobada en S3, como evidencia de 6.3; log de la Pi como fuente del lado del dispositivo de las 6 `person`, con clase y confianza iguales a S3). | Seguimiento del README por Edith o Bryan; video (F11). |
| 2026-10-16 | Emilio | Seguimiento del README | Edith siguió el README en un clon limpio de `49e318f` (texto en la casilla). Correcciones aplicadas en el README: volver a correr `up.py` después de editar `.env` (sección 4); credenciales del evaluador sin llaves de AWS, por decisión del equipo del 16 oct: enlace temporal de `model_int8.onnx` con verificación de SHA-256 (paso 2) y comprobación por el portal con el usuario `evaluador` (`GET /api/p4/captures/{id}`, `/image` y `/export`, rutas confirmadas en `src/p4/captures/api.py`), con la traza de S3 a cargo del equipo (paso 5). Casilla marcada. | Video (F11). |
