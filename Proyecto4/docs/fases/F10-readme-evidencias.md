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

- [ ] Edith o Bryan siguen el README de principio a fin sin ayuda
- [x] Lista de comprobaciones ejecutada con resultados registrados → [`docs/comprobaciones.md`](../comprobaciones.md) (todas las filas con resultado, incluida la 3.2 con el portal: 8 de 8)
- [ ] Carpeta de evidencias completa, con todos los enlaces abriendo → enlaces: los 174 enlaces relativos de [`evidencias/INDICE.md`](../../evidencias/INDICE.md) (80), README de `Proyecto4/` (19), ficha (39), comprobaciones (30) y README raíz (6) abren, con sus anclas, y sus destinos están en Git. **Abierta** hasta tener las 6 capturas `person` de las 20 (Bryan)
- [x] Sin credenciales reales en el repositorio ni en el paquete → gitleaks v8.30.1 con `.gitleaks.toml` sobre `Proyecto4/` (156 archivos versionados o nuevos) y `origin/main..HEAD`: sin hallazgos; búsqueda manual (`AKIA`, `Bearer` con valor, `$2a$`, `C:\Users`, `P4_DEVICE_TOKEN=` con valor, llaves privadas) sin valores reales
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-15 | Emilio | Comprobaciones repetibles | [`docs/comprobaciones.md`](../comprobaciones.md): hashes, tamaño y VersionId de los 3 artefactos en S3 (coinciden con `conversion_log.json` y `publicacion.json`); entradas conocidas de la Pi iguales a F7 (diferencia < 5e-7); traza de `fbf85a5e` en S3; 14/14 fotos de las 20 con su `image_sha256`; pytest Proyecto4 121 y Proyecto2 278 en el contenedor; recálculo de accuracy, F1 y p50/p95 con [`evidencias/comprobaciones/recalcular.py`](../../evidencias/comprobaciones/recalcular.py): todo coincide. Lo de la Pi se cita como ejecutado por Bryan. | Traza de `fbf85a5e` con el portal (credenciales de Emilio). |
| 2026-10-15 | Emilio | Carpeta de evidencias | [`evidencias/INDICE.md`](../../evidencias/INDICE.md) según la tabla de la rúbrica; traza de `fbf85a5e` con el portal: TODO COINCIDE, 8 de 8 ([`traza_fbf85a5e_portal.txt`](../../evidencias/comprobaciones/traza_fbf85a5e_portal.txt)); evidencia de F4–F6 copiada sin secretos; `head-object` de 3 de las 20; exportación completa (285 en CSV y JSON, igual a S3 en IDs y 9 campos: [`verificacion_export.txt`](../../evidencias/exportacion/verificacion_export.txt)); hallazgos del modelo con su confianza real leída de S3; decisión 8 cerrada. | 6 capturas `person` de las 20 (Bryan); `device_id` configurable, aprobado por el PM (PR de Bryan); seguimiento del README por Edith o Bryan; video (F11). |
| 2026-10-15 | Emilio | Secretos y enlaces | gitleaks v8.30.1 sobre `Proyecto4/` y `origin/main..HEAD` sin hallazgos; búsqueda manual sin valores reales; 174 enlaces relativos y anclas verificados. Casillas marcadas solo con evidencia. | Casilla de carpeta completa abierta hasta las 6 `person`. |
