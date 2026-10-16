# F2 — Variante optimizada y conversión reproducible

| Campo | Valor |
|---|---|
| Responsable | Edith (Líder de modelo y optimización) |
| Revisor de PRs | Bryan |
| Fechas | 7 oct → 8 oct de 2026 |
| Rama | `feat/p4-fase-2-optimizacion` |
| Puntos de rúbrica | 15 (1.1 y 1.2; requisito M1) |
| Depende de | F1 |
| Bloquea a | F3, F7, F8 |
| Control | Control 2 |

**Nota de calendario:** la conversión se intenta el miércoles 7 para detectar pronto operadores no soportados. La variante final se entrega a Bryan el jueves 8 al mediodía.

> Antes de empezar lee `AGENTS.md`, `docs/decisiones.md` (formato, runtime y técnica) y `docs/contratos.md`. Trabaja los bloques en orden.

## Rúbrica (15 puntos)

- **1.1 Continuidad con el modelo existente (5):** original identificado contra el Proyecto 3, con clases y preprocesamiento conservados.
- **1.2 Optimización real y variante ejecutable (10):** técnica respaldada por artefacto y configuración, conversión reproducible y variante cargada en el edge. Exportar o cambiar de formato sin un efecto comprobable limita el criterio a 5; sustituir el modelo por uno ajeno lo deja en 0.

## Bloques de trabajo

- **Conversión:** aplicar la técnica elegida a los pesos del Proyecto 3, sin sustituir el modelo.
- **Registro de conversión:** guardar la salida del proceso identificando archivo de entrada y de salida, con sus hashes SHA-256. Los hashes solos no prueban el parentesco entre modelos.
- **Técnica y efecto:** documentar qué técnica se aplicó, formato y precisión resultantes, y la evidencia de su efecto en el artefacto o en el runtime.
- **Reproducibilidad:** guardar script de conversión, configuración, dependencias y versiones.
- **Calibración:** si la técnica la requiere, usar solo muestras de entrenamiento y guardar un manifiesto con sus IDs.
- **Prueba de humo:** inferir una entrada conocida y comparar la clase con la del original.
- **Ficha del artefacto:** enlaces de descarga, versión, formato, precisión, runtime y hashes.

## Cómo se cierra

- [x] Variante cargable en el runtime del dispositivo: en la Raspberry Pi física (Debian 13, Python 3.13.5, onnxruntime 1.31.0) carga `model_int8.onnx` con SHA-256 `ca689c4e…` y da en las 3 entradas conocidas las mismas probabilidades que aarch64 emulado ([`evidencia_f3/arm64_check_output.txt`](../../evidencia_f3/arm64_check_output.txt), [`arm64_check.txt`](../../modelo/registros/arm64_check.txt)); el programa de la cámara la carga al arrancar ([`evidencia_f3/ejecucion_offline.txt`](../../evidencia_f3/ejecucion_offline.txt))
- [x] Registro de conversión que une el original del Proyecto 3 con la variante: [`conversion_log.json`](../../modelo/registros/conversion_log.json) (entrada `e4acca42…` run `9f9b62c2…` → salida `ca689c4e…`)
- [x] Técnica explicada con evidencia de su efecto: INT8 estática QDQ por canal, 74.66 % menos bytes, 20 `QLinearConv` en el runtime ([`artefacto.md`](../artefacto.md#efecto-de-la-técnica))
- [x] Orden de clases y preprocesamiento idénticos al original: salen del checkpoint (`model_package.json`); 3/3 entradas conocidas iguales ([`smoke_test.json`](../../modelo/registros/smoke_test.json))
- [x] Conversión reproducible desde el repositorio: [`modelo/convert.py`](../../modelo/convert.py) + [`conversion.yaml`](../../modelo/conversion.yaml) + lockfile; dos corridas dan los mismos SHA-256
- [x] Ficha del artefacto con enlaces de descarga y hashes: [`docs/artefacto.md`](../artefacto.md), objetos en S3 en [`publicacion.json`](../../modelo/registros/publicacion.json)
- [x] PR fusionado: sebastian0023/Proyecto-3-Clasificador-de-imagenes#37, fusionado por Emilio el 9 oct (revisado por Emilio, sin review registrada en GitHub; el revisor asignado era Bryan)
- [x] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-08 | Edith | Conversión, registro, técnica, reproducibilidad, calibración, prueba de humo y ficha | Variante `1.0.0-int8.1` publicada en `s3://…/models/clasificador-edge/1.0.0-int8.1/`; PR de F2 | Carga en la Pi física (Bryan, F3). La calidad INT8 se mide en aarch64, no en x86 (ver aviso en `artefacto.md`) |
| 2026-10-13 | Edith | Cierre | Carga en la Pi física confirmada con la salida de Bryan (`evidencia_f3/arm64_check_output.txt`): mismas clases y probabilidades que aarch64 emulado. La Pi usa onnxruntime 1.31.0; `modelo/requirements-edge.txt` pasa de 1.30.0 a 1.31.0 | — |
| 2026-10-16 | Edith | Reproducción en clon limpio | Siguiendo `artefacto.md` § Reproducir en un clon limpio: datos del P3 con DVC y `generate_crops.py` (`crops.jsonl` `d3d61f35…`, el mismo), dos conversiones con los mismos bytes y `smoke_test.py` 3/3. El SHA-256 del archivo difiere del publicado porque el exportador guarda la ruta absoluta en `pkg.torch.onnx.stack_trace`; el modelo es el mismo (huella sin metadatos: FP32 `5f965432…`, INT8 `9b590301…`). Se agrega `modelo/huella.py` y se documentan los pasos exactos | — |
