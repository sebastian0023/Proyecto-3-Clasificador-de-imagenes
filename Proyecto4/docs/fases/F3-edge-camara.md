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

**Nota de calendario:** el miércoles 7 se arma la captura y el preprocesamiento con el modelo original o una entrada conocida, sin esperar a F2. El jueves 8 al mediodía llega la variante y el viernes 9 debe clasificar sin red.

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

- [ ] Clasifica objetos nuevos de varias clases con la variante de F2
- [ ] Sigue capturando y clasificando con la red desconectada después de cargar el modelo
- [ ] Muestra versión y hash del artefacto cargado
- [ ] Entradas conocidas dan la misma clase que en los registros
- [ ] Cada captura deja imagen y registro con ID único
- [ ] PR fusionado con review de Emilio
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-08 | Bryan | Captura, preprocesamiento, inferencia y evento local | Se agregó el script base `edge_camera.py` con `tflite_runtime` para capturar vía USB. | Ajustar el formato del evento al contrato final de AWS. |
| 2026-10-10 | Bryan | Contratos AWS y Seguridad | Se actualizó `edge_camera.py` para cumplir el contrato de Emilio: se añadió cálculo de `image_sha256`, se extrajo el token a la variable de entorno `P4_DEVICE_TOKEN` y se agregó la estructura de reintentos solo para errores 503 o de red. El JSONL final cumple el tope de 16 KiB. | Verificar en Raspberry Pi 3B con cámara USB real y red desconectada para marcar las casillas de cierre. |

## Texto del PR para Emilio

**Título:** `feat(p4): F3 - captura USB e inferencia local optimizada para Raspberry Pi 3B`

**Descripción:**

Hola Emilio. Implementa el flujo local de F3 en `Proyecto4/dispositivo/edge_camera.py`.
- **Memoria:** Se carga el modelo una sola vez y se limita la inferencia a un solo hilo para evitar cuelgues en el 1GB de RAM de nuestra Raspberry Pi 3B.
- **Captura:** Vía USB V4L2 con `ffmpeg` para no retener buffers en memoria.
- **Contrato AWS cumplido:** Ya integré todo lo que me pediste. El evento calcula el `image_sha256`, usa `captured_at` con zona horaria real y el token nunca se imprime (lo jala de `P4_DEVICE_TOKEN`). Además, dejé la estructura lista para que solo reintente ante caídas de red o 503, descartando los 400.
- **Offline:** La inferencia no depende de red y persiste la foto y el JSONL localmente antes de enviar.

**Validación pendiente antes del cierre de F3:** ejecutar físicamente en la Raspberry Pi 3B con la webcam USB, apagar el Wi-Fi para comprobar M2 y contrastar la salida de entradas conocidas contra F7.