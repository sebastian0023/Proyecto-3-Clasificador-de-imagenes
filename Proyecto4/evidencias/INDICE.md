# Índice de evidencias — Proyecto 4: modelo en edge

Paquete de evidencias para la evaluación. Sigue la tabla «Evidencia que se pide» de [`docs/rubrica.md`](../docs/rubrica.md): por cada evidencia, qué demuestra, a qué criterio sirve y dónde está. Las rutas son relativas a esta carpeta (`Proyecto4/evidencias/`).

Empieza por la [ficha de entrega](../docs/ficha-entrega.md) (resumen de una página) y el [README](../README.md) (instalar, arrancar y verificar). Las comprobaciones repetibles, con resultados, están en [`docs/comprobaciones.md`](../docs/comprobaciones.md).

**Ninguna credencial está en este paquete.** El acceso al portal es un usuario de evaluación cuya contraseña se entrega por canal privado; la consulta de AWS es de solo lectura.

## 1. Ficha de entrega y README

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| Equipo, dispositivo y cámara, SO, runtime, técnica, URL del portal y referencias a cada evidencia | 6.1 | [`docs/ficha-entrega.md`](../docs/ficha-entrega.md) |
| Instalación, recuperación del modelo desde S3 con SHA-256, arranque de la Pi y del portal, verificación | 6.1 | [`README.md`](../README.md) |
| Dónde se cambian destino de AWS, identidad del dispositivo y artefacto; plantilla sin secretos | 6.3 | [`README.md` → Configuración](../README.md#configuración) |
| Decisiones técnicas (formato, runtime, técnica, hardware, AWS, acceso) | 1.2, 6.3 | [`docs/decisiones.md`](../docs/decisiones.md) |
| Contrato del evento entre el dispositivo y AWS | 4.1 | [`docs/contratos.md`](../docs/contratos.md) |

## 2. Identificación del modelo existente (Proyecto 3)

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| Versión `1.0.0`, run ID de MLflow `9f9b62c202f0446a8a4b411a10321eff`, pesos `model.pt` en S3 con SHA-256 `e4acca42…9172`, clases (`cat`, `dog`, `person`) y preprocesamiento | 1.1 | [`docs/artefacto.md` → Origen](../docs/artefacto.md#origen-proyecto-3), [`docs/decisiones.md`](../docs/decisiones.md) (tabla de referencia del P3) |
| Selección del modelo en el P3 (corrida r10, mejor época 6) | 1.1 | [`Proyecto3/docs/selection.json`](../../Proyecto3/docs/selection.json), [`Proyecto3/docs/modelo.md`](../../Proyecto3/docs/modelo.md) |
| Clases y publicación del P3 | 1.1 | [`Proyecto3/docs/clases.md`](../../Proyecto3/docs/clases.md), [`Proyecto3/docs/publicacion_s3.md`](../../Proyecto3/docs/publicacion_s3.md) |
| Los pesos en S3 son los del registro (bytes, SHA-256 y VersionId), consulta del 15 oct | 1.1, 6.2 | [`comprobaciones/hashes_modelos_s3.txt`](comprobaciones/hashes_modelos_s3.txt) |

## 3. Variante optimizada

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| `model_int8.onnx` `1.0.0-int8.1`, ONNX opset 18, cuantización estática INT8 (QDQ, por canal), SHA-256 `ca689c4e…69c0`, 11 349 151 bytes | 1.2 | [`docs/artefacto.md`](../docs/artefacto.md) |
| Registro de conversión con archivo de entrada, de salida y SHA-256 de ambos | 1.2 | [`modelo/registros/conversion_log.json`](../modelo/registros/conversion_log.json) |
| Script y configuración de la conversión | 1.2 | [`modelo/convert.py`](../modelo/convert.py), [`modelo/conversion.yaml`](../modelo/conversion.yaml), [`modelo/requirements-conversion.lock.txt`](../modelo/requirements-conversion.lock.txt) |
| Publicación en S3 con VersionId de cada objeto | 1.2 | [`modelo/registros/publicacion.json`](../modelo/registros/publicacion.json) |
| Calibración con 200 recortes **solo de train** (manifiesto de IDs) | 1.3 | [`modelo/registros/calibracion_manifest.jsonl`](../modelo/registros/calibracion_manifest.jsonl) |
| La Pi carga la variante, verifica su SHA-256 y ejecuta operadores enteros (`QLinearConv`, `QGemm`, `QLinearAdd`) | 1.2, 2.3 | [`evidencia_f3/arm64_check_output.txt`](../evidencia_f3/arm64_check_output.txt), [`evidencia_f3/ejecucion.txt`](../evidencia_f3/ejecucion.txt) |
| Prueba de humo: original, FP32 e INT8 dan la clase esperada | 1.2 | [`modelo/registros/smoke_test.json`](../modelo/registros/smoke_test.json) |

## 4. Comparación de calidad

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| Resultado, por clase, matrices de confusión, errores explicados, método y separación de datos | 1.3 | [`docs/calidad.md`](../docs/calidad.md) |
| Manifiesto de validación del P3: partición `val` de `m-0.1.3-s42-1` (292 recortes; SHA-256 `45600f29…4305`; se recupera con `dvc pull` en `Proyecto3`) | 1.3 | [`docs/calidad.md` → Separación de datos](../docs/calidad.md#separación-de-datos), [`docs/decisiones.md`](../docs/decisiones.md) |
| Etiquetas y predicciones por muestra, original y optimizado | 1.3 | [`calidad/registros/pred_original.csv`](../calidad/registros/pred_original.csv), [`calidad/registros/pred_optimizado.csv`](../calidad/registros/pred_optimizado.csv), [`calidad/registros/predicciones_validacion.csv`](../calidad/registros/predicciones_validacion.csv) |
| Métricas: accuracy 0.9965753424657534 → 0.9931506849315068 (caída 0.342 pp), F1 macro 0.99537 → 0.99209 | 1.3 | [`calidad/registros/metricas.json`](../calidad/registros/metricas.json) |
| Recálculo independiente de esas métricas | 1.3, 6.2 | [`comprobaciones/recalcular.py`](comprobaciones/recalcular.py), [`comprobaciones/recalcular_salida.txt`](comprobaciones/recalcular_salida.txt) |

## 5. Comparación de recursos

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| Hardware y condiciones, exclusión justificada de PyTorch en la Pi, tamaños (−74.66 %), latencia y memoria, decisión | 3.1, 3.2, 3.3 | [`docs/recursos.md`](../docs/recursos.md) |
| 100 tiempos por variante tras 10 calentamientos (preprocesamiento + inferencia, sin envío) | 3.2 | [`recursos/registros/tiempos_inferencia.csv`](../recursos/registros/tiempos_inferencia.csv) |
| Resumen: p50 1068.81 → 654.68 ms, p95 1616.79 → 1231.15 ms, RSS, hardware | 3.2 | [`recursos/registros/resumen_recursos.json`](../recursos/registros/resumen_recursos.json), [`recursos/registros/throttling.txt`](../recursos/registros/throttling.txt) |
| Recálculo de p50 y p95 | 3.2, 6.2 | [`comprobaciones/recalcular_salida.txt`](comprobaciones/recalcular_salida.txt) |

## 6. Capturas de operación (las 20)

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| Capturas de `edge01` con el programa final: registro, foto, SHA-256 verificado y VersionId | 2.4, 4.1, 5.2 | [`capturas_20/capturas_20.csv`](capturas_20/capturas_20.csv), [`capturas_20/capturas_20.json`](capturas_20/capturas_20.json), [`capturas_20/fotos/`](capturas_20/fotos/) |
| Operación de cinco minutos, reinicio con captura nueva, corte de red y reintento | 2.4, 4.3 | [`evidencia_f9/`](../evidencia_f9/), [`docs/fases/F9-operacion-capturas.md`](../docs/fases/F9-operacion-capturas.md) |
| Las 100 capturas más recientes del portal en el momento de F9 | 2.4, 5.2 | [`evidencia_f9/export.json`](../evidencia_f9/export.json) |

Estado: **14 de 20** (7 `cat`, 7 `dog`). **Las 6 `person` están pendientes**: Bryan toma fotos nuevas de una persona sin cara, por privacidad. Al recibirlas se regeneran `capturas_20.csv` y `capturas_20.json` con las 20.

`evidencia_f9/resumen_f9.json` dice «más de 300» eventos en AWS. La consulta de solo lectura del 2026-10-15T04:36:12Z da **285** registros y 285 imágenes en `edge-captures/`; esa es la cifra que usa este paquete. El archivo de F9 se conserva tal cual.

### Hallazgos del modelo en las capturas recientes

Se documentan con honestidad y quedan **fuera de las 20**. No cambian la calidad medida, que sale de la validación etiquetada de F7 (sección 4); las 20 capturas verifican operación. Valores leídos de los registros en S3 el 2026-10-15:

| capture_id | Qué había | Clase predicha | Confianza | Capturada (UTC) |
|---|---|---|---|---|
| `5fbc3570-16d9-4c9a-a054-ad3c4c73cc03` | golden retriever en pantalla | `cat` | 0.885033905506134 | 2026-10-14T20:41:25 |
| `50930285-cb63-43df-8b89-adf142b38f77` | golden retriever en pantalla | `cat` | 0.914362370967865 | 2026-10-14T20:41:18 |
| `84b67e89-567a-42d2-bf54-5d789899c1ff` | perro en pantalla | `person` | 0.7050720453262329 | 2026-10-14T20:41:11 |
| `7fca5e39-71d2-4df0-8915-836b31da8229` | perro en pantalla | `person` | 0.7225131988525391 | 2026-10-14T20:40:58 |
| `471606a3-b0da-418f-ab59-3367145b8f6a` | perro en pantalla | `person` | 0.5949792861938477 | 2026-10-14T20:40:51 |
| `bfcb6daa-199d-40b5-865c-71a59485ad14` | perro borroso | `person` | 0.994139552116394 | 2026-10-12T23:34:39 |

La mayoría de las capturas del 12 al 14 oct son fotos de un **monitor** que muestra imágenes (con la cámara de la Pi). En la demostración se usarán objetos físicos.

## 7. Evidencia de AWS

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| Recurso: bucket S3 `dataset-quality-releases-750702272375` (us-east-1), prefijo `edge-captures/`; consulta de solo lectura lista para la demo | 4.2 | [`docs/consulta-aws.md`](../docs/consulta-aws.md) |
| `head-object` actual de 3 de las 20 (registro e imagen): VersionId y SHA-256 iguales a `capturas_20.csv` | 4.2 | [`aws/head_object_3_de_20.txt`](aws/head_object_3_de_20.txt) |
| Traza de `fbf85a5e` en S3 y en el portal: 8 de 8 campos coinciden, imagen igual en 3 fuentes | 4.1, 4.2, 5.2 | [`comprobaciones/traza_fbf85a5e_s3.txt`](comprobaciones/traza_fbf85a5e_s3.txt), [`comprobaciones/traza_fbf85a5e_portal.txt`](comprobaciones/traza_fbf85a5e_portal.txt) |
| Primer evento persistido (F4): identidad, `head-object`, SHA-256 descargado | 4.2 | [`aws/f4/consulta_demo.txt`](aws/f4/consulta_demo.txt), [`aws/f4/head_registro.json`](aws/f4/head_registro.json), [`aws/f4/head_imagen.json`](aws/f4/head_imagen.json) |
| Reenvío del mismo ID sin duplicar: el VersionId del registro no cambia | 4.3 | [`aws/f4/head_registro_tras_reenvio.txt`](aws/f4/head_registro_tras_reenvio.txt), [`docs/fases/F4-aws-recepcion.md`](../docs/fases/F4-aws-recepcion.md) |
| Eventos de prueba recibidos por el portal desplegado (HTTP y HTTPS) | 4.2 | [`aws/f5/head_object_f5.txt`](aws/f5/head_object_f5.txt), [`aws/f5/head_object_f5_https.txt`](aws/f5/head_object_f5_https.txt) |
| Recorrido completo F6: 7 capturas sin red seguidas del dispositivo a S3 y portal, un registro por ID | 4.1, 4.3, 5.2 | [`recorrido_f6/resumen_trazas_7_ids.md`](recorrido_f6/resumen_trazas_7_ids.md), [`recorrido_f6/trazas/`](recorrido_f6/trazas/), [`recorrido_f6/verificacion_eventos_7_ids.txt`](recorrido_f6/verificacion_eventos_7_ids.txt), [`recorrido_f6/integridad_sha_f6.txt`](recorrido_f6/integridad_sha_f6.txt) |
| Reenvío de 68 pendientes: 227 = 136 + 91 registros, ninguno duplicado, fallos de red reales y reintento con el mismo ID | 4.3 | [`recorrido_f6/reenvio_68_verificacion.txt`](recorrido_f6/reenvio_68_verificacion.txt) |
| Despliegue del portal en EC2 con rol de instancia, sin llaves | 4.2, 5.1 | [`docs/despliegue.md`](../docs/despliegue.md) |

### Exportación completa

La API del portal exporta todos los eventos: `GET https://174-129-84-80.sslip.io/api/p4/captures/export?format=csv` (o `format=json`), con el usuario de evaluación.

*Pendiente: Emilio la descarga a `exportacion/` y aquí se anota la hora de la consulta y el número de registros.*

## 8. Acceso al portal

| Dato | Valor |
|---|---|
| URL de Capturas Edge | **https://174-129-84-80.sslip.io/#/edge-captures** |
| Cómo llegar desde el portal previo | Abrir `https://174-129-84-80.sslip.io` (el portal de los Proyectos 1 a 3, «Dataset Quality») y elegir **Capturas Edge** en el menú lateral, entre **Inference** y **Settings** |
| Acceso de evaluación | Usuario **`evaluador`** (`basic_auth` de Caddy en todo el portal, API, imágenes y exportación). La contraseña se entrega por canal privado y **no está en este paquete** |
| Qué muestra | Las **100 capturas más recientes**, de más reciente a más antigua, con foto, clase, confianza, ID, fechas, dispositivo y versión del modelo; botón **Actualizar** y refresco automático cada 30 s; enlaces a CSV y JSON |

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| Galería el 14 oct: «Mostrando 100 de 285», sección en el menú del portal previo. La primera tarjeta (`cd4abdf7…`, `person` 64.78 %) es una toma borrosa; no forma parte de las 20 | 5.1, 5.2, 5.3 | [`portal/portal_galeria_hoy.jpeg`](portal/portal_galeria_hoy.jpeg) |
| Portal en HTTPS con las primeras capturas de prueba (F5), URL visible | 5.1 | [`portal/navegador_prueba_recortada.jpeg`](portal/navegador_prueba_recortada.jpeg) |
| Tarjeta de una captura de F6 (torso sin cara) con sus metadatos | 5.2 | [`portal/portal_bf2e1822.jpg`](portal/portal_bf2e1822.jpg) |
| Sin credenciales todo responde 401 (web, API, imágenes, exportación, MLflow); el POST del dispositivo exige su token; certificado de Let's Encrypt | 6.3 | [`portal/https_verificacion.txt`](portal/https_verificacion.txt) |

**Limitación de la galería:** solo muestra las 100 más recientes. Una captura anterior se consulta así (todas con el usuario de evaluación):

- un registro: `GET /api/p4/captures/{id}` y su foto en `GET /api/p4/captures/{id}/image`;
- todas: la exportación completa (sección 7);
- comparada entre dispositivo, S3 y portal: [`scripts/trazar_captura.py`](../scripts/trazar_captura.py) ([`README.md` → Consultar capturas anteriores](../README.md#consultar-capturas-anteriores)).

## 9. Comprobaciones repetibles

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| Carga y conversión, entradas conocidas, evento enviado y recuperado, pruebas automatizadas y recálculos: comando, esperado, obtenido, quién y cuándo | 6.2 | [`docs/comprobaciones.md`](../docs/comprobaciones.md) |
| Entradas conocidas: la Pi y F7 dan las mismas probabilidades | 2.2, 6.2 | [`comprobaciones/entradas_conocidas.txt`](comprobaciones/entradas_conocidas.txt) |
| Pruebas automatizadas: 121 (Proyecto 4) y 278 (portal P2/P3 con el router de P4) | 6.2 | [`comprobaciones/pytest_proyecto4.txt`](comprobaciones/pytest_proyecto4.txt), [`comprobaciones/pytest_proyecto2_contenedor.txt`](comprobaciones/pytest_proyecto2_contenedor.txt) |

## 10. Demostración funcional

| Qué demuestra | Criterio | Ruta |
|---|---|---|
| Guion de la demo: fallo reversible, reintento con el mismo ID y trazabilidad | 2.3, 4.3 | [`docs/demo-f6.md`](../docs/demo-f6.md) |
| Clasificación sin red en la Pi y reenvío al volver la red | 2.3, 4.3 | [`evidencia_f3/ejecucion_offline.txt`](../evidencia_f3/ejecucion_offline.txt), [`evidencia_f3/ping_offline.txt`](../evidencia_f3/ping_offline.txt) |
| Consulta de AWS de solo lectura durante la demo | 4.2 | [`docs/consulta-aws.md`](../docs/consulta-aws.md) |

## 11. Video (pendiente, lo agrega F11)

El video opcional (V1–V3) se graba en F11. Cuando exista, aquí va su enlace.

## Pendientes de este paquete

- 6 capturas `person` de las 20 (fotos nuevas sin cara, Bryan).
- Exportación completa en `exportacion/` (Emilio).
- `device_id` configurable (`P4_DEVICE_ID` y `--device-id`, `edge01` por defecto): **aprobado por el PM**; Bryan prepara el PR. Al fusionarse se actualizan la tabla de configuración del README y la ficha.
- Modelo comercial de la cámara web (salida de `lsusb`, Bryan).
- Video (F11).
