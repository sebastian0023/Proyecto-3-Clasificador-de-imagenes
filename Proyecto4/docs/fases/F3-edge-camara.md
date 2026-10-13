# F3 — Cámara e inferencia local en el dispositivo

| Campo | Valor |
|---|---|
| Responsable | Bryan (Líder de dispositivo edge y cámara) |
| Revisor de PRs | Emilio |
| Fechas | 7 oct → 9 oct de 2026 |
| Rama | `feat/p4-fase-3-edge-camara` |
| Puntos de rúbrica | 20 (2.1, 2.2 y 2.3; requisito M2) |
| Depende de | F1, F2 (variante final) |
| Bloquea a | F6, F8, F9 |
| Control | Control 2 |

> Antes de empezar lee `AGENTS.md`, `docs/decisiones.md` (modo de captura, hardware y runtime) y `docs/contratos.md` (evento). Trabaja los bloques en orden.

## Rúbrica (20 puntos)

- **2.1 Cámara en el dispositivo (5):** capturas nuevas de objetos que elige el evaluador. Una carpeta de imágenes precargadas no sustituye la cámara.
- **2.2 Entrada y clases coherentes (5):** resolución, canales, normalización, cuantización de entrada y recorte coinciden con el paquete del modelo.
- **2.3 Inferencia local con la variante (10):** la predicción cambia con objetos de distintas clases y sigue funcionando sin red. Si depende de AWS, de otra computadora o de un simulador, vale 0.
- **Requisito mínimo M2:** clasificación local en un dispositivo edge físico con cámara.

## Bloques de trabajo

- **Captura:** programa por botón o intervalo, un objeto por captura, con recorte fijo si aplica.
- **Preprocesamiento:** igual al de evaluación: tamaño, normalización, orden RGB/BGR y cuantización de entrada si aplica.
- **Inferencia local:** mostrar clase, confianza y tiempo.
- **Artefacto en uso:** al arrancar, el programa muestra versión y SHA-256 de la variante cargada. La prueba sin red no basta sola para demostrar qué modelo está cargado.
- **Entradas conocidas:** reproducir algunas muestras de validación en el dispositivo y contrastar clase y salida con los registros de F7.
- **Evento local:** registro con ID de captura, fecha con zona horaria, clase, confianza entre 0 y 1, dispositivo, versión del artefacto y referencia a la fotografía.

## Cómo se cierra

- [x] Clasifica objetos nuevos con la variante de F2
- [x] Sigue capturando y clasificando con la red desconectada después de cargar el modelo
- [x] Muestra versión y hash del artefacto cargado
- [x] Entradas conocidas dan la misma clase que en los registros
- [x] Cada captura deja imagen y registro con ID único
- [ ] PR fusionado con review de Emilio
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-08 | Bryan | Captura, preprocesamiento, inferencia y evento local | Se implementó el script base con `onnxruntime` para captura por USB. | Integrar preprocesamiento estricto de ImageNet y contratos de AWS. |
| 2026-10-10 | Bryan | Contratos AWS y Seguridad | Se ajustó el contrato (`schema_version: 1`, campos exactos, omisión segura del token) y cálculo del `image_sha256`. | Añadir resiliencia offline y persistencia en disco. |
| 2026-10-12 | Bryan | Validaciones M2 y Resiliencia | Pruebas físicas exitosas en Raspberry Pi 3B (`aarch64`): integración de `preprocess.py`, cola persistente en disco (`pendientes.json`) para reintentos offline con códigos 201. | Pruebas grupales de Fase 6 y Fase 7. |

**Nota de Ejecución (Importante):** 
Para que el script funcione correctamente y aplique la normalización de ImageNet usando `preprocess.py`, **debe ejecutarse estrictamente desde la raíz del repositorio**. Ejemplo:
`python Proyecto4/dispositivo/edge_camera.py --model Proyecto4/modelo/model_int8.onnx --version "1.0.0-int8.1"`

---

## Casillas de Cierre F3 (Evidencia)

Toda la evidencia auditable se recopiló en formato de texto mediante la salida de la consola con el comando `tee` y se respaldó de forma externa, cumpliendo con la directriz de auditoría.

- [x] **Salida del arranque:** 
  - **Evidencia auditable:** `ejecucion.txt`
  - **Detalle:** Las primeras líneas validan la versión del artefacto (`1.0.0-int8.1`), el hash SHA-256 (`ca689c4e...`), el runtime (`onnxruntime` v1.31.0) y las clases cargadas.

- [x] **Capturas de clases:** 
  - **Evidencia auditable:** `ejecucion.txt`
  - **Detalle:** Registro de inferencia exitosa utilizando objetos reales frente a la cámara web (`dog`, `cat`, `person`), reportando las confianzas sin redondear. Se respalda con `capturas_ls.txt` (UUIDs) y `eventos.txt` (JSONL con `schema_version: 1`).

- [x] **Prueba con el Wi-Fi apagado:** 
  - **Evidencia auditable:** `ping_offline.txt` y `ejecucion.txt`
  - **Detalle:** Simulación de caída de red enrutando tráfico a un `blackhole`. El log registra el fallo, la retención segura en disco de la cola de pendientes sin congelar la cámara, y el posterior reenvío masivo exitoso (código `201`) al retirar el bloqueo, preservando los `capture_id` originales.

- [x] **Entradas conocidas comparadas contra F7:** 
  - **Evidencia auditable:** `arm64_check_output.txt`
  - **Detalle:** Validación exitosa en arquitectura `aarch64` mediante `arm64_check.py` utilizando los recortes conocidos proporcionados por Emilio (`dog`, `cat`, `person`), obteniendo las clases e inferencias exactas esperadas.

---

### Requisito M2 y Seguridad de Credenciales

- **Evidencia de Hardware (M2):** Almacenada en `entorno.txt` (arquitectura 64-bit y versión de `onnxruntime` v1.31.0).
- **Nota de Seguridad:** Ninguno de los archivos de texto de evidencia incluye, expone o imprime variables de entorno sensibles o el token del dispositivo (`P4_DEVICE_TOKEN`).
