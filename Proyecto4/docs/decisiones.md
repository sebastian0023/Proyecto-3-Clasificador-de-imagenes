# Decisiones técnicas — Proyecto 4

Se cierran en el kickoff de F1 (miércoles 7 de octubre). Cada líder escribe las suyas; el PR lo abre Edith y lo revisa Bryan. No incluyas contraseñas, claves ni tokens.

Estado: **cerrada** / **pendiente de dato**. Mientras una decisión esté pendiente, la fase que depende de ella no marca sus casillas.

| # | Decisión | Responsable | Fecha | Estado | Desbloquea |
|---|---|---|---|---|---|
| 1 | Formato y runtime del modelo en el dispositivo | Edith y Bryan | | pendiente | F2, F3 |
| 2 | Técnica y objetivo de optimización | Edith | | pendiente | F2, F7, F8 |
| 3 | Datos de comparación de calidad | Edith | | pendiente | F7 |
| 4 | Modo de captura | Bryan | | pendiente | F3, F9 |
| 5 | Servicios de AWS | Emilio | | pendiente | F4, F5 |
| 6 | Ubicación de Capturas Edge en el portal | Emilio | | pendiente | F5 |
| 7 | Hardware y entorno del dispositivo | Bryan | | pendiente | F3, F8 |
| 8 | Qué cabe en Git y qué se distribuye por enlace | Edith y Emilio | | pendiente | F2, F10 |

## 1. Formato y runtime

- Formato del artefacto optimizado (por ejemplo ONNX, TFLite, TorchScript u otro):
- Runtime en el dispositivo y versión:
- Por qué es compatible con el hardware de la decisión 7:

## 2. Técnica y objetivo de optimización

- Técnica (cuantización, poda, destilación u otra):
- Precisión resultante:
- Objetivo medible (tamaño, latencia o memoria) y por qué importa en este hardware:
- ¿Requiere calibración? Si sí, solo con muestras de entrenamiento del P3; el manifiesto de IDs se guarda en F2.

## 3. Datos de comparación de calidad

- Conjunto (validación del Proyecto 3, con el manifiesto y las etiquetas del P3):
- Manifiesto y hash de origen:
- Confirmación de que el test no se usa para calibrar ni ajustar:

## 4. Modo de captura

- Por botón o por intervalo:
- Un objeto por captura; ¿recorte fijo? (sí/no, y cuál):
- Resolución de captura:

## 5. Servicios de AWS

- Cuenta y región:
- Dónde se guarda la imagen y dónde el registro del evento:
- Cómo recibe el dispositivo (endpoint, función o servicio):
- Identidad del dispositivo y permisos mínimos (sin claves en Git):
- Consulta de solo lectura para la demostración:

## 6. Ubicación de Capturas Edge

- Entrada del menú y ruta en el portal de los Proyectos 1 a 3:
- Dónde está desplegado el portal (URL) y quién lo administra:
- Acceso limitado para el evaluador:

## 7. Hardware y entorno del dispositivo

- Dispositivo y cámara (modelo):
- Sistema operativo y versión:
- Runtime y versiones:
- Prueba realizada el 7 de oct (cámara captura, el runtime carga el modelo original o una entrada conocida):

## 8. Qué cabe en Git

- Pesos del original del P3 y de la variante: enlace de descarga y SHA-256, o en el repositorio:
- Dónde se alojan los artefactos grandes:
- Dónde queda la carpeta de evidencias (F10):

## Referencia del modelo del Proyecto 3

Se llena en F1 (Edith). Sin esto no hay continuidad demostrable (M1, 1.1).

| Dato | Valor |
|---|---|
| Versión del modelo publicada | |
| Run ID de MLflow | |
| Ubicación de los pesos y SHA-256 | |
| Clases y orden | |
| Preprocesamiento (tamaño, normalización, orden de canales) | |
| Entrada conocida con clase esperada | |
